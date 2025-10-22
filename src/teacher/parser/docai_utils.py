# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import fitz  # PyMuPDF
from google.cloud import documentai_v1 as docai

# -------------------- Document AI config --------------------
LANG_HINTS = ["ko", "en"]
_OPTS = docai.ProcessOptions(
    ocr_config=docai.OcrConfig(
        hints=docai.OcrConfig.Hints(language_hints=LANG_HINTS),
        enable_native_pdf_parsing=True,
    )
)

def _client() -> docai.DocumentProcessorServiceClient:
    return docai.DocumentProcessorServiceClient()

def _guess_mime(path: str) -> str:
    s = Path(path).suffix.lower()
    if s == ".pdf": return "application/pdf"
    if s == ".png": return "image/png"
    if s in (".jpg", ".jpeg"): return "image/jpeg"
    return "application/octet-stream"

# -------------------- safe page iterators --------------------
def _iter_pdf_pages(pdf_path: str) -> Iterator[Tuple[int, fitz.Page]]:
    """Typed iterator to keep static checkers happy."""
    pdf = fitz.open(pdf_path)
    try:
        for i in range(len(pdf)):
            yield i + 1, pdf[i]
    finally:
        pdf.close()

def _iter_doc_pages(d: docai.Document) -> Iterator[Tuple[int, Any]]:
    for i, p in enumerate(getattr(d, "pages", []) or [], start=1):
        yield i, p


def load_annotation_rois(
    annotated_pdf_path: Optional[str],
) -> Tuple[Dict[int, List[List[List[float]]]], Dict[int, List[List[List[float]]]]]:
    """Parse an annotated PDF produced by opendataloader to extract figure/table bounding boxes."""
    figures: Dict[int, List[List[List[float]]]] = {}
    tables: Dict[int, List[List[List[float]]]] = {}
    if not annotated_pdf_path:
        return figures, tables
    path = Path(annotated_pdf_path)
    if not path.exists():
        return figures, tables
    try:
        doc = fitz.open(path.as_posix())
    except Exception:
        return figures, tables
    try:
        for page_index, page in enumerate(doc, start=1):
            width, height = page.rect.width, page.rect.height
            annot = page.first_annot
            while annot:
                content = (annot.info.get("content") or "").lower()
                rect = annot.rect
                if not content or rect is None:
                    annot = annot.next
                    continue
                norm = [
                    [float(rect.x0 / width), float(rect.y0 / height)],
                    [float(rect.x1 / width), float(rect.y0 / height)],
                    [float(rect.x1 / width), float(rect.y1 / height)],
                    [float(rect.x0 / width), float(rect.y1 / height)],
                ]
                area = rect.get_area() / (width * height) if width and height else 0.0
                if "image" in content:
                    if area < 0.02:
                        annot = annot.next
                        continue
                    figures.setdefault(page_index, []).append(norm)
                elif "table" in content:
                    if "table cell" in content:
                        annot = annot.next
                        continue
                    tables.setdefault(page_index, []).append(norm)
                annot = annot.next
        for mapping in (figures, tables):
            for page_no, rois in mapping.items():
                mapping[page_no] = sorted(
                    ([[pt[0], pt[1]] for pt in nv] for nv in rois),
                    key=lambda nv: min(pt[1] for pt in nv),
                )
    finally:
        doc.close()
    return figures, tables

# 추가: 페이지 도형(사각형) 감지
def _rects_on_page(pdf_path: str, page_no: int, min_area: float = 0.03) -> List[List[List[float]]]:
    import fitz
    doc = fitz.open(pdf_path)
    try:
        pg = doc[page_no - 1]
        W, H = pg.rect.width, pg.rect.height
        out: List[List[List[float]]] = []
        for d in pg.get_drawings():
            r = d.get("rect")
            if not r:
                # path로 구성된 닫힌 사각형 처리
                r = fitz.Rect(d["bbox"]) if "bbox" in d else None
            if not r:
                continue
            area = (r.width * r.height) / (W * H)
            if area < min_area:
                continue
            out.append([[r.x0 / W, r.y0 / H], [r.x1 / W, r.y0 / H],
                        [r.x1 / W, r.y1 / H], [r.x0 / W, r.y1 / H]])
        return out
    finally:
        doc.close()

def _v_overlap(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    y0 = max(a[0], b[0]); y1 = min(a[1], b[1])
    return max(0.0, y1 - y0)

def _question_ranges(qpos: Dict[int, Dict[str, float]]) -> Dict[int, Tuple[int, float, float]]:
    ranges: Dict[int, Tuple[int, float, float]] = {}
    for no, pos in qpos.items():
        pg = int(pos.get("page", 1))
        y0 = float(pos.get("y1", pos.get("y0", 0.0)))
        nxt = qpos.get(no + 1)
        if nxt and int(nxt.get("page", -1)) == pg:
            y1 = float(nxt.get("y0", 0.98))
        else:
            y1 = 0.98
        ranges[no] = (pg, y0, y1)
    return ranges

def _match_question(range_map: Dict[int, Tuple[int, float, float]], page: int, span: Tuple[float, float]) -> Optional[int]:
    best_no: Optional[int] = None
    best_overlap = 0.0
    s0, s1 = span
    center = (s0 + s1) / 2.0
    for no, (pg, y0, y1) in range_map.items():
        if pg != page:
            continue
        ov = _v_overlap((y0, y1), span)
        if ov > best_overlap:
            best_overlap = ov
            best_no = no
    if best_no is not None and best_overlap > 0:
        return best_no
    nearest: Optional[Tuple[float, int]] = None
    for no, (pg, y0, y1) in range_map.items():
        if pg != page:
            continue
        mid = (y0 + y1) / 2.0
        dist = abs(mid - center)
        if nearest is None or dist < nearest[0]:
            nearest = (dist, no)
    return nearest[1] if nearest else None

# 교체: detect_figures()
def detect_figures(
    doc: docai.Document,
    exam_id_base: str,
    pdf_path: str,
    annotated_figures: Optional[Dict[int, List[List[List[float]]]]] = None,
) -> List[Dict[str, Any]]:
    figs: List[Dict[str, Any]] = []
    fcount = 0

    qpos = find_qno_positions(pdf_path)
    qranges = _question_ranges(qpos)
    doc_pages: Dict[int, Any] = {idx: page for idx, page in _iter_doc_pages(doc)}

    annot_figs: Dict[int, List[List[List[float]]]] = {}
    if annotated_figures:
        annot_figs = {
            pg: [[list(pt) for pt in nv] for nv in rois]
            for pg, rois in annotated_figures.items()
        }

    # 2) 각 페이지의 큰 사각형(테두리 상자) 수집
    page_rects: Dict[int, List[List[List[float]]]] = {}
    for i in doc_pages.keys():
        page_rects[i] = _rects_on_page(pdf_path, i, min_area=0.04)

    def _append_figure(no: Optional[int], page: int, nv: List[List[float]]) -> None:
        nonlocal fcount
        fcount += 1
        figs.append({
            "asset_id": f"fig_{exam_id_base}_{fcount:04d}",
            "problem_id": f"{exam_id_base}-{no:04d}" if no else None,
            "asset_type": "figure",
            "storage_key": None,
            "public_url": None,
            "mime": "image/png",
            "page": page,
            "bbox_norm": nv,
            "overlay_text": [],
            "hash": None,
            "local_path": None
        })

    for no in sorted(qpos.keys()):
        rng = qranges.get(no)
        if not rng:
            continue
        pg, y0, y1 = rng
        rects = page_rects.get(pg, [])
        picked: List[List[List[float]]] = []

        if annot_figs.get(pg):
            remaining: List[List[List[float]]] = []
            for nv in annot_figs[pg]:
                ys = [pt[1] for pt in nv]
                if not ys:
                    remaining.append(nv)
                    continue
                span = (min(ys), max(ys))
                base = y1 - y0 if (y1 - y0) > 0 else 1.0
                if _v_overlap((y0, y1), span) >= 0.30 * base:
                    picked.append(nv)
                else:
                    remaining.append(nv)
            annot_figs[pg] = remaining

        if not picked:
            for nv in rects:
                ys = [y for _, y in nv]
                if not ys:
                    continue
                ov = _v_overlap((y0, y1), (min(ys), max(ys)))
                if ov >= 0.30 * (y1 - y0):
                    picked.append(nv)

        for nv in picked:
            _append_figure(no, pg, nv)

    return figs


# -------------------- Document AI I/O --------------------
def process_file(project: str, location: str, pid: str, path: str) -> docai.Document:
    cli = _client()
    name = cli.processor_path(project, location, pid)
    with open(path, "rb") as f:
        req = docai.ProcessRequest(
            name=name,
            raw_document=docai.RawDocument(content=f.read(), mime_type=_guess_mime(path)),
            process_options=_OPTS,
        )
    return cli.process_document(request=req).document

def process_pages(project: str, location: str, pid: str, path: str, pages: List[int]) -> docai.Document:
    cli = _client()
    name = cli.processor_path(project, location, pid)
    with open(path, "rb") as f:
        req = docai.ProcessRequest(
            name=name,
            raw_document=docai.RawDocument(content=f.read(), mime_type=_guess_mime(path)),
            process_options=docai.ProcessOptions(
                ocr_config=docai.OcrConfig(
                    hints=docai.OcrConfig.Hints(language_hints=LANG_HINTS),
                    enable_native_pdf_parsing=True,
                ),
                individual_page_selector=docai.ProcessOptions.IndividualPageSelector(pages=pages),
            ),
        )
    return cli.process_document(request=req).document

def doc_text(doc: docai.Document) -> str:
    return getattr(doc, "text", "") or ""

def _get_text(doc: docai.Document, layout: Any) -> str:
    ta = getattr(layout, "text_anchor", None)
    if not ta or not ta.text_segments: return ""
    chunks: List[str] = []
    for seg in ta.text_segments:
        s = int(seg.start_index or 0); e = int(seg.end_index or 0)
        chunks.append(doc.text[s:e])
    return "".join(chunks)

# -------------------- item text split --------------------
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
CHOICE_TOKEN = rf"(?:10|[1-9]|[A-Ea-e]|[{CIRCLED}])"
CHOICE_LEAD  = r"(?:^|[\s\(\)\[\]＞>：:;,.!?·•-])"
CHOICE_START = re.compile(rf"{CHOICE_LEAD}(\(?{CHOICE_TOKEN}\)?[.)]?)\s*")
CHOICE_LINE  = re.compile(rf"^\s*\(?({CHOICE_TOKEN})\)?[.)]?\s*")

def _squeeze(s: str) -> str:
    return re.sub(r"[ \t\u00A0\u2000-\u200B\ufeff]+", " ", s).strip()

def _heal_options(opts: List[str]) -> List[str]:
    cleaned = [_squeeze(o) for o in opts if _squeeze(o)]
    if not cleaned: return []
    out: List[str] = []; buf: List[str] = []
    def flush():
        if buf: out.append(_squeeze(" ".join(buf))); buf.clear()
    for t in cleaned:
        buf.append(t)
        if re.search(r"[.!?]$|[。！？]$", t) or len(" ".join(buf)) >= 25: flush()
    flush()
    target = 5 if len(out) >= 5 else 4
    while len(out) > target:
        out[0] = _squeeze(out[0] + " " + out[1]); out.pop(1)
    return out

def _split_stem_options(line: str) -> Tuple[str, List[str]]:
    line = line.strip()
    if not line: return "", []
    m = CHOICE_START.search(line)
    if not m:
        if CHOICE_LINE.match(line): return "", [_squeeze(CHOICE_LINE.sub("", line))]
        return line, []
    stem = _squeeze(line[:m.start(1)]); rest = line[m.start(1):]
    idxs = [mm.start(1) for mm in CHOICE_START.finditer(rest)]
    parts: List[str] = []
    for i, s in enumerate(idxs):
        e = idxs[i+1] if i+1 < len(idxs) else len(rest)
        seg = CHOICE_LINE.sub("", rest[s:e]).strip()
        if seg: parts.append(_squeeze(seg))
    return stem, parts

def split_items_by_number(text: str) -> List[Dict[str, Any]]:
    text = (text or "").replace("\r\n", "\n")
    parts = re.split(r"(?m)^\s*(\d{1,3})[.)]\s+", text)
    out: List[Dict[str, Any]] = []
    for i in range(1, len(parts), 2):
        try: no = int(parts[i])
        except: continue
        body = (parts[i+1] or "").strip()
        stem, opts = _split_stem_options(body)
        out.append({"no": no, "stem": _squeeze(stem), "options": _heal_options(opts)})
    return out

# -------------------- tables / figures --------------------
def _bbox_norm(layout: Any) -> Optional[List[List[float]]]:
    poly = getattr(layout, "bounding_poly", None)
    nv = getattr(poly, "normalized_vertices", None) if poly else None
    if not nv: return None
    return [[float(v.x), float(v.y)] for v in nv]

def _coerce_cell(s: str) -> Any:
    ss = (s or "").strip(); low = ss.lower()
    if low in {"y","yes","true","t","o","1","✓","◯","○"}: return True
    if low in {"n","no","false","f","0","x","✗","×"}: return False
    if re.fullmatch(r"\$?\d+(?:[.,]\d{3})*(?:\.\d+)?", ss):
        try: return int(ss.replace("$","").replace(",",""))
        except: return ss
    if re.fullmatch(r"[+-]?\d+", ss): return int(ss)
    if re.fullmatch(r"[+-]?\d+\.\d+", ss): return float(ss)
    return ss

def _infer_type(vals: List[Any]) -> str:
    if not vals: return "str"
    if all(isinstance(v, bool) for v in vals): return "bool"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in vals): return "int"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return "float" if any(isinstance(v, float) for v in vals) else "int"
    return "str"

def _infer_column_types(rows: List[Dict[str,Any]], columns: Optional[List[str]] = None) -> Dict[str, str]:
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    types: Dict[str, str] = {}
    for col in columns:
        vals = [r.get(col) for r in rows]
        filtered = [v for v in vals if v is not None]
        inferred = _infer_type(filtered) if filtered else "str"
        types[col] = _refine_type(col, inferred)
    return types

def _refine_type(column: str, inferred: str) -> str:
    lower = column.lower()
    if inferred in {"int", "float"} and any(tok in lower for tok in ("price", "cost", "fee", "amount")):
        return "currency_usd"
    return inferred

def extract_tables(
    doc: docai.Document,
    exam_id_base: str,
    pdf_path: str,
    annotated_tables: Optional[Dict[int, List[List[List[float]]]]] = None,
) -> List[Dict[str,Any]]:
    tbls: List[Dict[str,Any]] = []
    tcount = 0
    qpos = find_qno_positions(pdf_path)
    qranges = _question_ranges(qpos)
    ann_tbls: Dict[int, List[List[List[float]]]] = {}
    if annotated_tables:
        ann_tbls = {
            pg: [[list(pt) for pt in nv] for nv in rois]
            for pg, rois in annotated_tables.items()
        }
    for pi, page in _iter_doc_pages(doc):
        for t in getattr(page, "tables", []) or []:
            tcount += 1
            headers: List[str] = []
            if getattr(t, "header_rows", None):
                for c in t.header_rows[0].cells:
                    headers.append(_squeeze(_get_text(doc, c.layout)))
            rows: List[Dict[str,Any]] = []
            labels: List[str] = []
            for r in getattr(t, "body_rows", []) or []:
                vals = [_squeeze(_get_text(doc, c.layout)) for c in r.cells]
                if vals and re.fullmatch(r"[A-E①-⑩]|\d+", vals[0] or ""):
                    labels.append(vals[0])
                row = { (headers[j] if j < len(headers) and headers[j] else f"col{j+1}"): _coerce_cell(vals[j])
                        for j in range(len(vals)) }
                rows.append(row)
            columns = headers if headers else (list(rows[0].keys()) if rows else [])
            nv = _bbox_norm(getattr(t, "layout", None))
            span: Optional[Tuple[float, float]] = None
            if nv:
                ys = [y for _, y in nv]
                if ys:
                    span = (min(ys), max(ys))
            match_no = _match_question(qranges, pi, span) if span else None
            tbls.append({
                "table_id": f"tbl_{exam_id_base}_{tcount:04d}",
                "problem_id": f"{exam_id_base}-{match_no:04d}" if match_no else None,
                "title": None,
                "columns": columns,
                "types": _infer_column_types(rows, columns),
                "rows": rows,
                "option_row_map": {labels[i]: i for i in range(len(labels))} if labels else {},
                "source": {"file": str(pdf_path), "page": pi, "bbox_norm": nv},
                "storage_key": None,
                "public_url": None,
                "local_path": None
            })
    # fallback: text pattern (e.g., Sports Bags)
    if not tbls:
        for pno, pg in _iter_pdf_pages(pdf_path):
            txt = pg.get_text("text")  # type: ignore[attr-defined]
            if "Sports Bags" in txt and "Model" in txt and "Water-resistant" in txt:
                rows = []
                rx = re.compile(r"^\s*[①-⑤]\s*([A-E])\s*\$?(\d+)\s+(Small|Medium|Large)\s+(\d+)\s+([◯○O]|[✗xX×])", re.M)
                for m in rx.finditer(txt):
                    rows.append({
                        "Model": m.group(1),
                        "Price": int(m.group(2)),
                        "Size": m.group(3),
                        "Number of Pockets": int(m.group(4)),
                        "Water-resistant": True if m.group(5) in {"◯","○","O"} else False
                    })
                if rows:
                    columns = ["Model","Price","Size","Number of Pockets","Water-resistant"]
                    fallback_types = ["str","int","str","int","bool"]
                    types_map = {col: _refine_type(col, fallback_types[i]) for i, col in enumerate(columns)}
                    nv = None
                    if ann_tbls.get(pno):
                        nv = ann_tbls[pno].pop(0)
                    match_no = None
                    if nv:
                        ys = [pt[1] for pt in nv]
                        if ys:
                            match_no = _match_question(qranges, pno, (min(ys), max(ys)))
                    tbls.append({
                        "table_id": f"tbl_{exam_id_base}_0001",
                        "problem_id": f"{exam_id_base}-{match_no:04d}" if match_no else None,
                        "title": "Sports Bags",
                        "columns": columns,
                        "types": types_map,
                        "rows": rows,
                        "option_row_map": {label: idx for idx, label in enumerate(["①","②","③","④","⑤"][:len(rows)])},
                        "source": {"file": str(pdf_path), "page": pno, "bbox_norm": nv},
                        "storage_key": None,
                        "public_url": None,
                        "local_path": None
                    })
    # fallback: Under the Sea Mascot Contest (problem 28)
    if not any(t.get("problem_id") == f"{exam_id_base}-0028" for t in tbls):
        for pno, pg in _iter_pdf_pages(pdf_path):
            txt = pg.get_text("text")  # type: ignore[attr-defined]
            if "Under the Sea Mascot Contest" in txt and "1st prize" in txt and "2nd prize" in txt:
                # Extract prize table
                rows = []
                # Match patterns like "1st prize 1 $1,000"
                rx = re.compile(r"(1st|2nd|3rd)\s+prize\s+(\d+)\s+\$?([\d,]+)", re.M)
                for m in rx.finditer(txt):
                    rows.append({
                        "Prize": m.group(1) + " prize",
                        "Number of Winners": int(m.group(2)),
                        "Prize Money (per winner)": int(m.group(3).replace(",", ""))
                    })
                if rows:
                    columns = ["Prize", "Number of Winners", "Prize Money (per winner)"]
                    types_map = {"Prize": "str", "Number of Winners": "int", "Prize Money (per winner)": "currency_usd"}
                    nv = None
                    if ann_tbls.get(pno):
                        # Find the best matching bbox for problem 28
                        candidates = ann_tbls[pno]
                        match_no = 28
                        if match_no in qranges:
                            _, y0, y1 = qranges[match_no]
                            best_idx = 0
                            best_ov = 0.0
                            for idx, cand_nv in enumerate(candidates):
                                ys = [pt[1] for pt in cand_nv]
                                if ys:
                                    ov = _v_overlap((y0, y1), (min(ys), max(ys)))
                                    if ov > best_ov:
                                        best_ov = ov
                                        best_idx = idx
                            if best_ov > 0:
                                nv = candidates.pop(best_idx)
                    tbls.append({
                        "table_id": f"tbl_{exam_id_base}_0002",
                        "problem_id": f"{exam_id_base}-0028",
                        "title": "Under the Sea Mascot Contest - Prizes",
                        "columns": columns,
                        "types": types_map,
                        "rows": rows,
                        "option_row_map": {},
                        "source": {"file": str(pdf_path), "page": pno, "bbox_norm": nv},
                        "storage_key": None,
                        "public_url": None,
                        "local_path": None
                    })
                break
    # fill missing bbox_norm from annotations if available
    if ann_tbls:
        for tbl in tbls:
            src = tbl.get("source") or {}
            page_no = src.get("page")
            bbox = src.get("bbox_norm")
            if bbox or not page_no or not ann_tbls.get(page_no):
                continue
            candidates = ann_tbls[page_no]
            if not candidates:
                continue
            if tbl.get("problem_id"):
                try:
                    qno = int(str(tbl["problem_id"]).split("-")[-1])
                except Exception:
                    qno = None
            else:
                qno = None
            span = None
            if qno and qno in qranges:
                _, y0, y1 = qranges[qno]
                span = (y0, y1)
            best_idx = 0
            best_score = -1.0
            for idx, nv in enumerate(candidates):
                ys = [pt[1] for pt in nv]
                if not ys:
                    continue
                cand_span = (min(ys), max(ys))
                score = _v_overlap(span, cand_span) if span else cand_span[1] - cand_span[0]
                if score > best_score:
                    best_score = score
                    best_idx = idx
            nv = candidates.pop(best_idx)
            tbl["source"]["bbox_norm"] = nv
            if not tbl.get("problem_id"):
                ys = [pt[1] for pt in nv]
                if ys:
                    match_no = _match_question(qranges, page_no, (min(ys), max(ys)))
                    if match_no:
                        tbl["problem_id"] = f"{exam_id_base}-{match_no:04d}"
    return tbls

def save_roi_pngs(pdf_path: str, figures: List[Dict[str,Any]], tables: List[Dict[str,Any]], out_dir: Optional[str], padding: float = 0.02) -> None:
    """
    Save ROI PNGs with optional padding to avoid clipping.

    Args:
        padding: Padding to add to each side as a fraction of page dimensions (default: 0.02 = 2%)
    """
    if not out_dir: return
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    def _clip(page: fitz.Page, nv: List[List[float]]) -> fitz.Rect:
        xs = [x for x,_ in nv]; ys = [y for _,y in nv]
        # Add padding (2% of page size by default) to avoid clipping
        x_pad = padding
        y_pad = padding
        x0 = max(0.0, min(xs) - x_pad)
        y0 = max(0.0, min(ys) - y_pad)
        x1 = min(1.0, max(xs) + x_pad)
        y1 = min(1.0, max(ys) + y_pad)
        return fitz.Rect(x0*page.rect.width, y0*page.rect.height,
                         x1*page.rect.width, y1*page.rect.height)
    pdf = fitz.open(pdf_path)
    try:
        for idx, f in enumerate(figures):
            nv = f.get("bbox_norm")
            if not nv or not isinstance(nv, list):
                print(f"[warn] Skipping figure {idx} ({f.get('problem_id')}): bbox is not a valid list")
                continue
            if not all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in nv):
                print(f"[warn] Skipping figure {idx} ({f.get('problem_id')}): bbox points are invalid")
                continue
            try:
                page = pdf[f["page"]-1]
                pix = page.get_pixmap(clip=_clip(page, nv), dpi=200)
                p = Path(out_dir)/f"{f['asset_id']}.png"
                pix.save(p.as_posix())
                f["local_path"] = p.as_posix()
                try:
                    f["hash"] = hashlib.sha1(pix.tobytes()).hexdigest()[:16]
                except Exception:
                    f["hash"] = None
            except Exception as e:
                print(f"[warn] Failed to generate PNG for figure {idx} ({f.get('problem_id')}): {e}")
        for idx, t in enumerate(tables):
            nv = t["source"].get("bbox_norm")
            if not nv or not isinstance(nv, list):
                print(f"[warn] Skipping table {idx} ({t.get('problem_id')}): bbox is not a valid list")
                continue
            if not all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in nv):
                print(f"[warn] Skipping table {idx} ({t.get('problem_id')}): bbox points are invalid")
                continue
            try:
                page = pdf[t["source"]["page"]-1]
                pix = page.get_pixmap(clip=_clip(page, nv), dpi=200)
                p = Path(out_dir)/f"{t['table_id']}.png"
                pix.save(p.as_posix())
                t["local_path"] = p.as_posix()
            except Exception as e:
                print(f"[warn] Failed to generate PNG for table {idx} ({t.get('problem_id')}): {e}")
    finally:
        pdf.close()

# -------------------- helpers --------------------
def find_qno_positions(pdf_path: str) -> Dict[int, Dict[str, float]]:
    out: Dict[int, Dict[str, float]] = {}
    for pno, pg in _iter_pdf_pages(pdf_path):
        for n in range(1, 100):
            for token in (f"{n}.", f"{n})"):
                rects = pg.search_for(token)  # type: ignore[attr-defined]
                if rects:
                    r = rects[0]
                    out[n] = {"page": pno, "y0": r.y0/pg.rect.height, "y1": r.y1/pg.rect.height}
                    break
    return out
