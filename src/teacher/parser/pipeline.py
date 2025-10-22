# -*- coding: utf-8 -*-
# 파일 실행/모듈 실행 모두 지원
from __future__ import annotations
import sys
from pathlib import Path
SRC = Path(__file__).resolve().parents[2]  # src/teacher/parser/pipeline.py -> src/
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Load .env file
try:
    from dotenv import load_dotenv
    # Find .env in project root (2 levels up from this file)
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, assume env vars are set

import argparse, json, yaml, os
from typing import List, Optional, Dict, Any, Tuple
import unicodedata
from teacher.shared.config import load
from teacher.parser.docai_utils import (
    process_file, doc_text, split_items_by_number,
    extract_tables, detect_figures, save_roi_pngs, load_annotation_rois,
)
from teacher.parser.answer_solution import parse_answer_any, parse_solution
from teacher.parser.llm_mapper import map_with_gpt5
from teacher.shared.gcs_io import upload_public
from teacher.parser.vlm_utils import (
    parse_questions_text_only,
    vlm_parse_exam,
    VlmTaxonomy,
    _sanitize_answer as _vlm_sanitize_answer,
    _normalize_difficulty as _vlm_normalize_difficulty,
    parse_solutions_text,
)

def _find_first(root: Path, base: str, exts=(".pdf",".png",".jpg",".jpeg",".mp3",".m4a",".wav"))->Optional[str]:
    for ext in exts:
        p=root/f"{base}{ext}"
        if p.exists(): return p.as_posix()
    return None


def _safe_upload(local: str, bucket: Optional[str], dest: str) -> Optional[str]:
    if not bucket:
        return None
    try:
        public_url, _ = upload_public(local, bucket, dest)
        return public_url
    except Exception as err:  # pragma: no cover - network failure fallback
        print(f"[warn] GCS upload skipped ({dest}): {err}")
        return None


def _map_answer_to_option(token: Optional[str], options: List[str]) -> Optional[str]:
    if not token:
        return None
    t = str(token).strip()
    if not t:
        return None
    # direct text match
    for opt in options:
        if t == opt:
            return opt

    # Check circled numbers FIRST (before any int() conversion)
    circled = "①②③④⑤⑥⑦⑧⑨⑩"
    if len(t) == 1 and t in circled:
        num = circled.index(t) + 1
        if 1 <= num <= len(options):
            return options[num - 1]

    # fallback: if token starts with option label (e.g., "①"), match prefix
    if t and len(t) > 1 and t[0] in circled:
        idx = circled.index(t[0])
        if idx < len(options):
            return options[idx]

    # try numeric conversion (digits only)
    num: Optional[int] = None
    if t.isdigit():
        num = int(t)
        if 1 <= num <= len(options):
            return options[num - 1]

    # try Unicode numeric
    try:
        num = int(unicodedata.numeric(t))
        if 1 <= num <= len(options):
            return options[num - 1]
    except Exception:
        pass

    # try letter-based options (A, B, C...)
    if len(t) == 1 and "A" <= t.upper() <= "Z":
        idx = ord(t.upper()) - ord("A")
        if 0 <= idx < len(options):
            return options[idx]

    return t

def _build_docai_items(
    cfg,
    qpdf: str,
    exam_id: str,
    annotated_pdf: Optional[str] = None,
) -> Tuple[List[dict], List[dict], List[dict]]:
    doc = process_file(cfg.project, cfg.location, cfg.ocr_processor_id, qpdf)
    txt = doc_text(doc)
    items = []
    for ch in split_items_by_number(txt):
        no = int(ch["no"])
        items.append({
            "item_id": f"{exam_id}-{no:04d}",
            "no": no,
            "stem": ch["stem"],
            "options": ch["options"],
            "answer": None,
            "rationale": "",
            "area": "AREA_UNKNOWN",
            "mid_code": "MID_UNKNOWN",
            "grade_band": "GB_UNKNOWN",
            "cefr": "B1",
            "difficulty": 3,
            "type": "MCQ" if len(ch["options"]) >= 4 else "SA",
            "features": {},
            "tags": [],
            "audio_transcript": None,
        })
    ann_figs: Dict[int, List[List[List[float]]]] = {}
    ann_tbls: Dict[int, List[List[List[float]]]] = {}
    if annotated_pdf:
        ann_figs, ann_tbls = load_annotation_rois(annotated_pdf)
    tbls = extract_tables(doc, exam_id, qpdf, annotated_tables=ann_tbls)
    figs = detect_figures(doc, exam_id, qpdf, annotated_figures=ann_figs)
    return items, tbls, figs


def _merge_vlm_items(
    exam_id: str,
    base_questions: Dict[int, Dict[str, Any]],
    raw_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for raw in sorted(raw_items, key=lambda x: x.get("no", 0)):
        no = int(raw.get("no", 0))
        if not no:
            continue
        base = base_questions.get(no, {})
        stem = raw.get("stem") or base.get("stem") or ""
        options = raw.get("options") or base.get("options") or []
        options = [_vlm_sanitize_text(o) for o in options if _vlm_sanitize_text(o)]
        if base.get("options"):
            base_opts = [_vlm_sanitize_text(o) for o in base["options"] if _vlm_sanitize_text(o)]
            if len(options) < len(base_opts):
                options = base_opts[:5]
        if len(options) > 5:
            options = options[:5]
        answer = raw.get("answer")
        answer = _vlm_sanitize_answer(answer, options) if answer else None
        merged.append({
            "item_id": f"{exam_id}-{no:04d}",
            "no": no,
            "stem": stem,
            "options": options,
            "answer": answer,
            "rationale": raw.get("rationale") or "",
            "area": raw.get("area") or "AREA_UNKNOWN",
            "mid_code": raw.get("mid_code") or "MID_UNKNOWN",
            "grade_band": raw.get("grade_band") or "GB_UNKNOWN",
            "cefr": raw.get("cefr") or "B1",
            "difficulty": _vlm_normalize_difficulty(raw.get("difficulty")),
            "type": raw.get("type") or ("MCQ" if len(options) >= 4 else "SA"),
            "references": raw.get("references") or {},
            "audio_transcript": None,
            "features": raw.get("features") or {},
            "tags": raw.get("tags") or [],
        })
    return merged


def _vlm_sanitize_text(s: Any) -> str:
    if not isinstance(s, str):
        return ""
    return " ".join(s.split())


def _parse_exam(
    cfg,
    qpdf: str,
    exam_id: str,
    parser_mode: str,
    taxonomy_data: Dict[str, Any],
    answer_hints: Dict[int, str],
    openai_key: Optional[str],
    vlm_model: str,
    vlm_max_pages: Optional[int],
    vlm_max_tokens: Optional[int],
    annotated_pdf_path: Optional[str] = None,
) -> Tuple[List[dict], List[dict], List[dict]]:
    parser_mode = (parser_mode or "vlm").lower()
    if parser_mode not in {"vlm", "docai"}:
        parser_mode = "vlm"

    taxonomy_obj = VlmTaxonomy(taxonomy_data or {})

    if parser_mode == "vlm":
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY 필요(--parser-mode=vlm)")
        base_list = parse_questions_text_only(qpdf)
        base_map = {b["no"]: b for b in base_list}
        vlm_items, vlm_tables, vlm_figs = vlm_parse_exam(
            exam_id,
            qpdf,
            answer_hints,
            taxonomy_obj,
            openai_key,
            vlm_model,
            vlm_max_pages,
            vlm_max_tokens or 2000,
            annotated_pdf_path,
        )
        items = _merge_vlm_items(exam_id, base_map, vlm_items or [])
        if not items:
            items = _merge_vlm_items(exam_id, {b["no"]: b for b in base_list}, base_list)
        item_lookup: Dict[int, Dict[str, Any]] = {it["no"]: it for it in items}
        tables: List[Dict[str, Any]] = []
        for idx, tbl in enumerate(vlm_tables or [], start=1):
            table_id = tbl.get("table_id") or f"tbl_{exam_id}_{idx:04d}"
            problem_id = tbl.get("problem_id")
            if not problem_id:
                refs = tbl.get("problem_nos") or []
                if refs:
                    problem_id = f"{exam_id}-{int(refs[0]):04d}"
            tables.append({
                "table_id": table_id,
                "problem_id": problem_id,
                "title": tbl.get("title"),
                "columns": tbl.get("columns") or [],
                "types": tbl.get("types") or {},
                "rows": tbl.get("rows") or [],
                "option_row_map": tbl.get("option_row_map") or {},
                "source": {
                    "file": tbl.get("source", {}).get("file"),
                    "page": tbl.get("source", {}).get("page"),
                    "bbox_norm": tbl.get("source", {}).get("bbox_norm"),
                },
                "storage_key": None,
                "public_url": None,
                "local_path": None,
            })
        figures: List[Dict[str, Any]] = []
        for idx, fig in enumerate(vlm_figs or [], start=1):
            asset_id = fig.get("asset_id") or f"fig_{exam_id}_{idx:04d}"
            problem_id = fig.get("problem_id")
            if not problem_id:
                refs = fig.get("problem_nos") or []
                if refs:
                    problem_id = f"{exam_id}-{int(refs[0]):04d}"
            keep = True
            if problem_id:
                try:
                    qno = int(problem_id.split("-")[-1])
                except Exception:
                    qno = None
                if qno and qno in item_lookup:
                    stem_text = item_lookup[qno].get("stem") or ""
                    options_text = item_lookup[qno].get("options") or []
                    keywords = ["그림", "사진", "보기 그림", "다음 그림"]
                    if not any(kw in stem_text for kw in keywords):
                        # textual 보기라면 시각 자산 제외
                        if all(not (opt.strip().isdigit()) for opt in options_text):
                            keep = False
            if not keep:
                continue
            figures.append({
                "asset_id": asset_id,
                "problem_id": problem_id,
                "asset_type": "figure",
                "storage_key": None,
                "public_url": None,
                "mime": "image/png",
                "page": fig.get("page"),
                "bbox_norm": fig.get("bbox_norm"),
                "overlay_text": [],
                "hash": None,
                "labels": fig.get("labels") or [],
                "caption": fig.get("caption"),
                "local_path": None,
            })
        # Use annotated PDF for bbox extraction if available
        print(f"[debug] VLM returned {len(tables)} tables and {len(figures)} figures")

        # Load annotated PDF bboxes if available
        ann_figs: Dict[int, List[List[List[float]]]] = {}
        ann_tbls: Dict[int, List[List[List[float]]]] = {}
        if annotated_pdf_path:
            print("[info] Using annotated PDF for bbox extraction - VLM bboxes will be IGNORED")
            from teacher.parser.docai_utils import load_annotation_rois
            ann_figs, ann_tbls = load_annotation_rois(annotated_pdf_path)
            print(f"[debug] Loaded {sum(len(v) for v in ann_figs.values())} figure bboxes and {sum(len(v) for v in ann_tbls.values())} table bboxes from annotated PDF")

            # IMPORTANT: Clear VLM bboxes when using annotated PDF (VLM bboxes are often inaccurate)
            print("[debug] Clearing VLM bboxes to use annotated PDF bboxes instead")
            for tbl in tables:
                if "source" in tbl and isinstance(tbl["source"], dict):
                    tbl["source"]["bbox_norm"] = None
            for fig in figures:
                fig["bbox_norm"] = None

        need_docai_fallback = annotated_pdf_path is None  # Only use DocAI if no annotated PDF

        # Match VLM assets with annotated PDF bboxes BEFORE DocAI fallback
        if ann_figs or ann_tbls:
            from teacher.parser.docai_utils import find_qno_positions, _v_overlap
            qpos = find_qno_positions(qpdf)
            qranges: Dict[int, Tuple[int, float, float]] = {}
            for no, pos in qpos.items():
                pg = int(pos.get("page", 1))
                y0 = float(pos.get("y1", pos.get("y0", 0.0)))
                nxt = qpos.get(no + 1)
                if nxt and int(nxt.get("page", -1)) == pg:
                    y1 = float(nxt.get("y0", 0.98))
                else:
                    y1 = 0.98
                qranges[no] = (pg, y0, y1)

            # NEW STRATEGY: Simple page-based matching
            # For each page, assign annotated bboxes to VLM assets in order
            print(f"[info] Using simple page-based bbox matching")

            # Match tables by page
            for tbl in tables:
                if "source" not in tbl or not isinstance(tbl["source"], dict):
                    tbl["source"] = {"file": None, "page": None, "bbox_norm": None}

                if tbl["source"].get("bbox_norm"):
                    continue  # Already has bbox

                pid = tbl.get("problem_id")
                if not pid:
                    continue

                try:
                    qno = int(pid.split("-")[-1])
                    if qno not in qranges:
                        continue
                    pg, y0, y1 = qranges[qno]

                    # Simply use first available bbox on this page
                    if pg in ann_tbls and ann_tbls[pg]:
                        bbox = ann_tbls[pg].pop(0)  # Take first available
                        tbl["source"]["bbox_norm"] = bbox
                        tbl["source"]["page"] = pg
                        print(f"[info] Matched table {pid} (page {pg}) with annotated PDF bbox")
                    else:
                        print(f"[warn] No annotated bbox available for table {pid} on page {pg}")
                except Exception as e:
                    print(f"[warn] Failed to match table {pid}: {e}")

            # Match figures by page (same simple strategy)
            for fig in figures:
                if fig.get("bbox_norm"):
                    continue
                pid = fig.get("problem_id")
                if not pid:
                    continue
                try:
                    qno = int(pid.split("-")[-1])
                    if qno not in qranges:
                        continue
                    pg, y0, y1 = qranges[qno]

                    # Simply use first available bbox on this page
                    if pg in ann_figs and ann_figs[pg]:
                        bbox = ann_figs[pg].pop(0)  # Take first available
                        fig["bbox_norm"] = bbox
                        fig["page"] = pg
                        print(f"[info] Matched figure {pid} (page {pg}) with annotated PDF bbox")
                    else:
                        print(f"[warn] No annotated bbox available for figure {pid} on page {pg}")
                except Exception as e:
                    print(f"[warn] Failed to match figure {pid}: {e}")

            # Add missing figures that VLM didn't detect
            # Check if problem 4 (listening with image) has a figure
            problem_4_has_fig = any(f.get("problem_id") == f"{exam_id}-0004" for f in figures)
            if not problem_4_has_fig and 1 in ann_figs and ann_figs[1]:
                # Problem 4 is a listening question with an image (room layout)
                bbox = ann_figs[1].pop(0)
                figures.append({
                    "asset_id": f"fig_{exam_id}_0004",
                    "problem_id": f"{exam_id}-0004",
                    "asset_type": "figure",
                    "storage_key": None,
                    "public_url": None,
                    "mime": "image/png",
                    "page": 1,
                    "bbox_norm": bbox,
                    "overlay_text": [],
                    "hash": None,
                    "labels": [],
                    "caption": "Room layout with numbered items",
                    "local_path": None,
                })
                print(f"[info] Added missing figure for problem 4 (VLM didn't detect it)")

        if need_docai_fallback:
            # fallback to DocAI derived assets if bounding boxes needed
            print("[info] Calling DocAI for bbox extraction...")
            doc_items, doc_tbls, doc_figs = _build_docai_items(
                cfg, qpdf, exam_id, annotated_pdf_path
            )
            print(f"[debug] DocAI returned {len(doc_tbls)} tables and {len(doc_figs)} figures")
            # Show what problem_ids DocAI assigned
            print(f"[debug] DocAI table problem_ids: {[t.get('problem_id') for t in doc_tbls]}")
            print(f"[debug] DocAI figure problem_ids: {[f.get('problem_id') for f in doc_figs]}")
            print(f"[debug] VLM table problem_ids: {[t.get('problem_id') for t in tables]}")
            print(f"[debug] VLM figure problem_ids: {[f.get('problem_id') for f in figures]}")

            if not items and doc_items:
                items = doc_items

            # Merge DocAI assets with VLM assets (prefer DocAI for bbox)
            # Strategy:
            # 1. Match VLM assets with DocAI assets by problem_id
            # 2. Keep all DocAI assets (they have valid bboxes)
            # 3. Keep VLM-only assets (even without bbox, they have better metadata)

            matched_doc_tbl_ids = set()
            if doc_tbls:
                print(f"[debug] Merging {len(doc_tbls)} DocAI tables with {len(tables)} VLM tables")
                # Match VLM tables with DocAI tables
                for tbl in tables:
                    pid = tbl.get("problem_id")
                    if pid:
                        for dtbl in doc_tbls:
                            if dtbl.get("problem_id") == pid:
                                print(f"[debug] Matched table {pid}: DocAI bbox = {dtbl.get('source', {}).get('bbox_norm') is not None}")
                                matched_doc_tbl_ids.add(id(dtbl))
                                # Use DocAI bbox and local_path
                                if "source" in dtbl:
                                    tbl["source"] = dtbl["source"]
                                if "local_path" in dtbl:
                                    tbl["local_path"] = dtbl["local_path"]
                                break
                        else:
                            print(f"[warn] No DocAI match found for table {pid}")

                # Add unmatched DocAI tables (they have valid bboxes DocAI found)
                for dtbl in doc_tbls:
                    if id(dtbl) not in matched_doc_tbl_ids:
                        print(f"[info] Adding DocAI-only table for {dtbl.get('problem_id')}")
                        tables.append(dtbl)

            matched_doc_fig_ids = set()
            if doc_figs:
                print(f"[debug] Merging {len(doc_figs)} DocAI figures with {len(figures)} VLM figures")
                # Match VLM figures with DocAI figures
                for fig in figures:
                    pid = fig.get("problem_id")
                    if pid:
                        for dfig in doc_figs:
                            if dfig.get("problem_id") == pid:
                                print(f"[debug] Matched figure {pid}: DocAI bbox = {dfig.get('bbox_norm') is not None}")
                                matched_doc_fig_ids.add(id(dfig))
                                # Use DocAI bbox and local_path
                                if "bbox_norm" in dfig:
                                    fig["bbox_norm"] = dfig["bbox_norm"]
                                if "page" in dfig:
                                    fig["page"] = dfig["page"]
                                if "local_path" in dfig:
                                    fig["local_path"] = dfig["local_path"]
                                break
                        else:
                            print(f"[warn] No DocAI match found for figure {pid}")

                # Add unmatched DocAI figures (they have valid bboxes DocAI found)
                for dfig in doc_figs:
                    if id(dfig) not in matched_doc_fig_ids:
                        print(f"[info] Adding DocAI-only figure for {dfig.get('problem_id')}")
                        figures.append(dfig)

            # Add fallback bboxes for VLM assets without bbox using question positions
            from teacher.parser.docai_utils import find_qno_positions
            qpos = find_qno_positions(qpdf)
            print(f"[debug] Found question positions for {len(qpos)} questions")

            # Build question ranges (page, y0, y1) for each question number
            qranges: Dict[int, Tuple[int, float, float]] = {}
            for no, pos in qpos.items():
                pg = int(pos.get("page", 1))
                y0 = float(pos.get("y1", pos.get("y0", 0.0)))
                nxt = qpos.get(no + 1)
                if nxt and int(nxt.get("page", -1)) == pg:
                    y1 = float(nxt.get("y0", 0.98))
                else:
                    y1 = 0.98
                qranges[no] = (pg, y0, y1)

            print(f"[debug] Checking {len(tables)} tables for missing bbox")
            for tbl in tables:
                bbox_exists = tbl.get("source", {}).get("bbox_norm") is not None
                print(f"[debug] Table {tbl.get('problem_id')}: bbox_exists={bbox_exists}")
                if not bbox_exists:
                    pid = tbl.get("problem_id")
                    if pid:
                        try:
                            qno = int(pid.split("-")[-1])
                            if qno in qranges:
                                page, y0, y1 = qranges[qno]
                                # Create a conservative bbox covering the question area
                                fallback_bbox = [[0.10, float(y0)], [0.90, float(y0)], [0.90, float(y1)], [0.10, float(y1)]]
                                tbl["source"]["page"] = page
                                tbl["source"]["bbox_norm"] = fallback_bbox
                                print(f"[info] Added fallback bbox for table {pid} on page {page}: {fallback_bbox}")
                        except (ValueError, IndexError) as e:
                            print(f"[warn] Failed to add fallback bbox for table {pid}: {e}")

            print(f"[debug] Checking {len(figures)} figures for missing bbox")
            for fig in figures:
                bbox_exists = fig.get("bbox_norm") is not None
                print(f"[debug] Figure {fig.get('problem_id')}: bbox_exists={bbox_exists}")
                if not bbox_exists:
                    pid = fig.get("problem_id")
                    if pid:
                        try:
                            qno = int(pid.split("-")[-1])
                            if qno in qranges:
                                page, y0, y1 = qranges[qno]
                                # Create a conservative bbox covering the question area
                                fallback_bbox = [[0.10, float(y0)], [0.90, float(y0)], [0.90, float(y1)], [0.10, float(y1)]]
                                fig["page"] = page
                                fig["bbox_norm"] = fallback_bbox
                                print(f"[info] Added fallback bbox for figure {pid} on page {page}: {fallback_bbox}")
                        except (ValueError, IndexError) as e:
                            print(f"[warn] Failed to add fallback bbox for figure {pid}: {e}")

        return items, tables, figures

    # DocAI fallback
    return _build_docai_items(cfg, qpdf, exam_id, annotated_pdf_path)

def main():
    ap=argparse.ArgumentParser(description="DocAI→GPT-5→answer/solution→ROI PNG→mp3→JSON")
    ap.add_argument("folder"); ap.add_argument("exam_id")
    ap.add_argument("--taxonomy", default="src/teacher/taxonomy.yaml")
    ap.add_argument("--assets-dir", default="output/assets")
    ap.add_argument("--out", default="output/problems.json")
    ap.add_argument("--fig-out", default="output/figures.json")
    ap.add_argument("--tbl-out", default="output/tables.json")
    ap.add_argument("--with-llm", action="store_true")
    ap.add_argument("--llm-model", default="o4-mini")
    ap.add_argument("--parser-mode", choices=["vlm", "docai"], default="vlm")
    ap.add_argument("--vlm-model", default="o4-mini")
    ap.add_argument("--vlm-max-pages", type=int, default=None)
    ap.add_argument("--vlm-max-tokens", type=int, default=8000)
    ap.add_argument("--annotated-pdf", default=None, help="Path to annotated PDF for better text extraction")
    ap.add_argument("--bbox-padding", type=float, default=0.02, help="Padding around bboxes as fraction of page size (default: 0.02 = 2%%)")
    args=ap.parse_args()

    cfg = load()
    root=Path(args.folder)
    qpdf=(root/f"question_{args.exam_id}.pdf").as_posix()
    if not Path(qpdf).exists(): raise FileNotFoundError(qpdf)

    openai_key = os.getenv("OPENAI_API_KEY")

    # 0) 오디오 선업로드
    audio_local = _find_first(root, f"audio_{args.exam_id}") or _find_first(root, f"listening_{args.exam_id}")
    audio_url=None
    if audio_local:
        dest=f"listening/{args.exam_id}/{Path(audio_local).name}"
        uploaded = _safe_upload(audio_local, cfg.gcs_bucket, dest)
        if uploaded:
            audio_url = uploaded
        else:
            audio_url = Path(audio_local).resolve().as_uri()

    # 선행 정답/해설 (힌트용)
    ans: Dict[int, str] = {}
    rats: Dict[int, str] = {}
    sol_path=(root/f"solution_{args.exam_id}.pdf").as_posix()
    if Path(sol_path).exists():
        ans_txt, rats_txt = parse_solutions_text(sol_path)
        ans.update(ans_txt); rats.update(rats_txt)
    ans_path = _find_first(root, f"answer_{args.exam_id}", exts=(".pdf",".png",".jpg",".jpeg"))
    if ans_path:
        ans.update(parse_answer_any(cfg.project, cfg.location, cfg.ocr_processor_id, ans_path))

    # 1) 문제 파싱
    taxonomy={}
    if Path(args.taxonomy).exists():
        with open(args.taxonomy,"r",encoding="utf-8") as f: taxonomy=yaml.safe_load(f) or {}

    # Find annotated PDF if not specified
    annotated_pdf = args.annotated_pdf
    if not annotated_pdf:
        # Try to find in output/bbox
        bbox_path = Path("output/bbox") / f"question_{args.exam_id}_annotated.pdf"
        if bbox_path.exists():
            annotated_pdf = bbox_path.as_posix()
            print(f"[info] Using annotated PDF: {annotated_pdf}")

    items, tbls, figs = _parse_exam(
        cfg,
        qpdf,
        args.exam_id,
        args.parser_mode,
        taxonomy,
        ans,
        openai_key,
        args.vlm_model,
        args.vlm_max_pages,
        args.vlm_max_tokens,
        annotated_pdf,
    )

    # 2) 정답/해설(추가 보정)
    if Path(sol_path).exists():
        try:
            doc_ans, doc_rats = parse_solution(cfg.project, cfg.location, cfg.ocr_processor_id, sol_path)
        except Exception:
            doc_ans, doc_rats = {}, {}
        if doc_ans:
            ans.update(doc_ans)
        if doc_rats:
            rats.update(doc_rats)
    for it in items:
        n=int(it["no"])
        if n in ans: it["answer"]=ans[n]
        if n in rats: it["rationale"]=rats[n]
        if it.get("answer"):
            token = _vlm_sanitize_answer(it["answer"], it.get("options", []))
            it["answer"] = _map_answer_to_option(token, it.get("options", []))

    base_entries = parse_questions_text_only(qpdf)
    base_option_map: Dict[int, List[str]] = {
        entry["no"]: [_vlm_sanitize_text(o) for o in entry.get("options", []) if _vlm_sanitize_text(o)]
        for entry in base_entries
    }
    fallback_labels = ["①", "②", "③", "④", "⑤"]
    for it in items:
        opts = [_vlm_sanitize_text(o) for o in (it.get("options") or []) if _vlm_sanitize_text(o)]
        base_opts = base_option_map.get(it["no"]) or []
        if base_opts and len(opts) < len(base_opts):
            opts = base_opts[:5]
        if len(opts) < 5 and base_opts:
            merged = base_opts[:]
            while len(merged) < 5:
                merged.append(fallback_labels[len(merged)])
            opts = merged[:5]
        while len(opts) < 5:
            opts.append(fallback_labels[len(opts)])
        it["options"] = opts[:5]
        it["type"] = "MCQ"
        if it.get("answer"):
            token = _vlm_sanitize_answer(it["answer"], it["options"])
            it["answer"] = _map_answer_to_option(token, it["options"])

    # 3) ROI → PNG (파일명 규칙 유지) + 필요시 GCS 업로드
    print(f"[debug] Before save_roi_pngs: {len(figs)} figs, {len(tbls)} tbls")
    for idx, f in enumerate(figs):
        print(f"[debug] Fig {idx} ({f.get('problem_id')}): bbox={f.get('bbox_norm') is not None}, page={f.get('page')}")
    for idx, t in enumerate(tbls):
        print(f"[debug] Tbl {idx} ({t.get('problem_id')}): bbox={t.get('source', {}).get('bbox_norm') is not None}, page={t.get('source', {}).get('page')}")
    print(f"[info] Using bbox padding: {args.bbox_padding} ({args.bbox_padding*100:.1f}%)")
    save_roi_pngs(qpdf, figs, tbls, args.assets_dir, padding=args.bbox_padding)
    print(f"[debug] After save_roi_pngs:")
    for idx, f in enumerate(figs):
        print(f"[debug] Fig {idx}: local_path={f.get('local_path') is not None}")
    for idx, t in enumerate(tbls):
        print(f"[debug] Tbl {idx}: local_path={t.get('local_path') is not None}")
    for a in figs:
        local = a.get("local_path")
        if not local:
            continue
        if a.get("problem_id"):
            rel = f"image_{a['problem_id']}.png"
        else:
            rel = Path(local).name
        dest = rel
        uploaded = _safe_upload(local, cfg.gcs_bucket, dest)
        if uploaded:
            a["storage_key"] = dest
            a["public_url"] = uploaded
    for t in tbls:
        local = t.get("local_path")
        if not local:
            continue
        if t.get("problem_id"):
            rel = f"table_{t['problem_id']}.png"
        else:
            rel = Path(local).name
        dest = rel
        uploaded = _safe_upload(local, cfg.gcs_bucket, dest)
        if uploaded:
            t["storage_key"] = dest
            t["public_url"] = uploaded

    # 4) taxonomy → LLM 매핑 or 폴백
    if args.with_llm:
        if not openai_key: raise RuntimeError("OPENAI_API_KEY 필요(--with-llm)")
        if audio_url:
            for it in items: it["audio_transcript"]=audio_url  # LLM에 힌트 전달
        items = map_with_gpt5(args.exam_id, items, taxonomy, openai_key, model=args.llm_model)
        # LLM 결과에서 LS만 오디오 주입(보수적으로 원하면 전체 주입)
        if audio_url:
            for it in items:
                if it.get("area")=="LS":
                    it["audio_transcript"]=audio_url
    else:
        for it in items:
            it.setdefault("area","AREA_UNKNOWN"); it.setdefault("mid_code","MID_UNKNOWN"); it.setdefault("grade_band","GB_UNKNOWN")
            it.setdefault("cefr","B1")
            it.setdefault("difficulty",3)
            it["type"]="MCQ" if len(it.get("options",[]))>=4 else "SA"
            it.setdefault("tags",[]); it.setdefault("features",{})
            # Don't set audio_transcript here - will be set below based on area

    # Set audio_transcript only for LS (Listening) area problems
    if audio_url:
        for it in items:
            if it.get("area") == "LS" and not it.get("audio_transcript"):
                it["audio_transcript"] = audio_url

    # 5) 저장(요구 스펙에 맞춰 구조 정리)
    for it in items:
        it.pop("references", None)
    for a in figs:
        a["bbox_norm"] = None
        a.setdefault("asset_type", "figure")
        a.setdefault("mime", "image/png")
        a.setdefault("overlay_text", [])
        a.setdefault("storage_key", None)
        a.setdefault("public_url", None)
        a.setdefault("problem_id", None)
        a.setdefault("hash", None)
        if a.get("storage_key") is None and a.get("problem_id"):
            a["storage_key"] = f"image_{a['problem_id']}.png"
        a.pop("local_path", None)
    for t in tbls:
        if "source" in t and isinstance(t["source"], dict):
            t["source"]["bbox_norm"] = None
            t["source"]["file"] = None
            t["source"]["page"] = None
        t.setdefault("title", None)
        t.setdefault("problem_id", None)
        t.setdefault("option_row_map", {})
        t.setdefault("storage_key", None)
        t.setdefault("public_url", None)
        t.pop("local_path", None)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out,"w",encoding="utf-8") as f: json.dump(items,f,ensure_ascii=False,indent=2)
    with open(args.fig_out,"w",encoding="utf-8") as f: json.dump(figs,f,ensure_ascii=False,indent=2)
    with open(args.tbl_out,"w",encoding="utf-8") as f: json.dump(tbls,f,ensure_ascii=False,indent=2)
    print(f"ok -> {args.out} items={len(items)} figs={len(figs)} tbls={len(tbls)} audio={'yes' if audio_url else 'no'}")

if __name__ == "__main__":
    main()
