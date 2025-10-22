# -*- coding: utf-8 -*-
from __future__ import annotations
import base64, json, re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import fitz  # type: ignore
from openai import OpenAI

CHOICE_TOKEN = r"(?:10|[1-9]|[A-Ea-e]|①|②|③|④|⑤)"
CHOICE_LINE_RE = re.compile(rf"^\s*\(?({CHOICE_TOKEN})\)?[.)]?\s*")


def _squeeze(text: str) -> str:
    return re.sub(r"[ \t\u00A0\u2000-\u200B\ufeff]+", " ", text or "").strip()


def _dedupe(seq: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in seq:
        cleaned = _squeeze(item)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def _encode_image(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _extract_response_text(resp: Any) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    output = getattr(resp, "output", None)
    if output:
        chunks: List[str] = []
        for item in output:
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text") or "")
        if chunks:
            return "".join(chunks)
    choices = getattr(resp, "choices", None)
    if choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else getattr(choices[0], "message", None)
        if message and isinstance(message, dict):
            return message.get("content", "") or ""
    return ""


def render_pdf_pages(pdf_path: str, dpi: int = 180) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    pages: List[Dict[str, Any]] = []
    try:
        for page_no, page in enumerate(doc, start=1):  # type: ignore
            pix = page.get_pixmap(dpi=dpi)
            pages.append({
                "page": page_no,
                "image": pix.tobytes("png"),
                "width": pix.width,
                "height": pix.height,
                "text": page.get_text("text") or "",
            })
    finally:
        doc.close()
    return pages


def parse_questions_text_only(pdf_path: str) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    items: List[Dict[str, Any]] = []
    try:
        for page_no, page in enumerate(doc, start=1):  # type: ignore
            text = page.get_text("text") or ""
            if not text.strip():
                continue
            lines = text.splitlines()
            current_no: Optional[int] = None
            buffer: List[str] = []

            def flush() -> None:
                nonlocal current_no, buffer
                if current_no is None:
                    buffer = []
                    return
                stem_lines: List[str] = []
                opts: List[str] = []
                for raw in buffer:
                    line = raw.strip()
                    if not line:
                        continue
                    if CHOICE_LINE_RE.match(line):
                        opt = CHOICE_LINE_RE.sub("", line).strip()
                        if opt:
                            opts.append(opt)
                    else:
                        stem_lines.append(line)
                stem = _squeeze(" ".join(stem_lines))
                options = _heal_options(_dedupe(opts))
                items.append({
                    "no": current_no,
                    "page": page_no,
                    "stem": stem,
                    "options": options,
                })
                buffer = []
                current_no = None

            for raw_line in lines:
                line = raw_line.strip()
                if not line:
                    continue
                m = re.match(r"^(\d{1,3})[.)]\s*(.*)$", line)
                if m:
                    flush()
                    current_no = int(m.group(1))
                    buffer = []
                    remainder = m.group(2).strip()
                    if remainder:
                        buffer.append(remainder)
                    continue
                buffer.append(line)
            flush()
    finally:
        doc.close()
    deduped: Dict[int, Dict[str, Any]] = {}
    for it in items:
        if it["no"] not in deduped or not deduped[it["no"]]["options"]:
            deduped[it["no"]] = it
    return list(deduped.values())


def _heal_options(opts: List[str]) -> List[str]:
    canonical = [_squeeze(o) for o in opts if _squeeze(o)]
    if len(canonical) >= 4 and all(len(o) >= 1 for o in canonical):
        return canonical[:5]
    merged: List[str] = []
    buf: List[str] = []

    def flush() -> None:
        if buf:
            merged.append(_squeeze(" ".join(buf)))
            buf.clear()

    for opt in canonical:
        buf.append(opt)
        if len(" ".join(buf)) >= 25 or re.search(r"[.!?]$", opt):
            flush()
    flush()
    if not merged:
        merged = canonical
    while len(merged) > 5:
        merged[0] = _squeeze(merged[0] + " " + merged[1])
        merged.pop(1)
    return merged[:5]


class VlmTaxonomy:
    def __init__(self, data: Dict[str, Any]):
        self.areas = list(data.get("areas") or ["AREA_UNKNOWN"])
        self.mid_codes: List[str] = []
        self.mid2area: Dict[str, str] = {}
        for entry in data.get("mid_codes") or []:
            if isinstance(entry, dict) and "code" in entry and "area" in entry:
                code = str(entry["code"])
                self.mid_codes.append(code)
                self.mid2area[code] = str(entry["area"])
        self.grade_bands = list(data.get("grade_bands") or ["GB_UNKNOWN"])


def _normalize_difficulty(val: Any) -> int:
    if val is None:
        return 3
    if isinstance(val, (int, float)):
        return int(min(5, max(1, round(float(val)))))
    if isinstance(val, str):
        stripped = val.strip()
        if stripped.isdigit():
            return min(5, max(1, int(stripped)))
        mapping = {
            "very easy": 1,
            "easy": 2,
            "medium": 3,
            "moderate": 3,
            "normal": 3,
            "standard": 3,
            "hard": 4,
            "difficult": 4,
            "very hard": 5,
            "extreme": 5,
            "advanced": 4,
            "intro": 2,
        }
        return mapping.get(stripped.lower(), 3)
    return 3


def _sanitize_answer(ans: Any, options: List[str]) -> Optional[str]:
    if ans is None:
        return None
    if isinstance(ans, (list, tuple)):
        ans = ans[0] if ans else None
    if ans is None:
        return None
    if isinstance(ans, float) and ans.is_integer():
        ans = int(ans)
    if isinstance(ans, int):
        ans = str(ans)
    text = str(ans).strip()
    if not text:
        return None
    upper = text.upper()

    # Try to extract answer from longer text (e.g., "② 달리면서..." -> "②")
    # Look for circled numbers at the start
    all_circled = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    for char in text:
        if char in all_circled:
            idx = all_circled.index(char) + 1
            if 1 <= idx <= len(options):
                return char
            break  # Found circled number but invalid

    # Look for letter answers (A-E) at start or after whitespace
    letter_match = re.search(r'\b([A-E])\b', upper)
    if letter_match:
        letter = letter_match.group(1)
        idx = ord(letter) - 64
        if idx <= len(options):
            return letter

    # Look for numeric answers (1-5)
    num_match = re.search(r'\b([1-5])\b', text)
    if num_match:
        num = num_match.group(1)
        idx = int(num)
        if 1 <= idx <= len(options):
            return num

    # Fallback to original logic for clean single-character answers
    if len(text) == 1:
        if text in all_circled:
            idx = all_circled.index(text) + 1
            return text if 1 <= idx <= len(options) else None
        if re.fullmatch(r"[A-E]", upper):
            idx = ord(upper) - 64
            return upper if idx <= len(options) else None
        if upper.isdigit():
            idx = int(upper)
            return str(idx) if 1 <= idx <= len(options) else None

    return None  # Could not extract valid answer


def parse_solutions_text(path: str) -> Tuple[Dict[int, str], Dict[int, str]]:
    doc = fitz.open(path)
    try:
        text = "\n".join(page.get_text("text") for page in doc)  # type: ignore
    finally:
        doc.close()

    answers: Dict[int, str] = {}
    rationales: Dict[int, str] = {}

    # Try to parse answer table format first (e.g., "01. ① 02. ② 03. ③")
    answer_lines = []
    for line in text.split('\n')[:20]:  # Check first 20 lines
        if re.search(r'\d{2}\.\s*[①②③④⑤⑥⑦⑧⑨⑩]', line):
            answer_lines.append(line)

    if answer_lines:
        # Parse compact answer format
        for line in answer_lines:
            # Match patterns like "01. ①" or "1. ①"
            matches = re.findall(r'(\d{1,2})\.\s*([①②③④⑤⑥⑦⑧⑨⑩])', line)
            for no_str, ans in matches:
                try:
                    no = int(no_str)
                    answers[no] = ans
                except Exception:
                    continue

    # Fall back to detailed solution parsing
    if not answers:
        parts = re.split(r"(?m)^\s*(\d{1,3})[.)]\s+", text)
        for i in range(1, len(parts), 2):
            try:
                no = int(parts[i])
            except Exception:
                continue
            body = (parts[i + 1] or "").strip()
            m = re.search(r"(?:정답|Answer)\s*[:：]?\s*([A-Ea-e1-9①-⑩])", body)
            if m:
                answers[no] = m.group(1).upper()
            rationales[no] = re.sub(r"(?mi)^\s*(?:정답|Answer).*$", "", body).strip()

    return answers, rationales


def vlm_parse_exam(
    exam_id: str,
    pdf_path: str,
    answers_map: Dict[int, str],
    taxonomy: VlmTaxonomy,
    api_key: str,
    model: str,
    max_pages: Optional[int] = None,
    max_output_tokens: int = 2000,
    annotated_pdf_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    client = OpenAI(api_key=api_key)
    pages = render_pdf_pages(pdf_path)
    if max_pages is not None:
        pages = pages[:max_pages]

    # Load annotated PDF text if available
    annotated_pages: Dict[int, str] = {}
    if annotated_pdf_path and Path(annotated_pdf_path).exists():
        try:
            ann_doc = fitz.open(annotated_pdf_path)
            for page_no, page in enumerate(ann_doc, start=1):  # type: ignore
                annotated_pages[page_no] = page.get_text("text") or ""
            ann_doc.close()
        except Exception as err:
            print(f"[vlm] Failed to load annotated PDF: {err}")

    sys_prompt = (
        "You are an expert assessment parser. Your task is to read page images of mock CSAT English exams and "
        "return a JSON object with keys 'items', 'tables', and 'figures'.\n"
        "- Include every question number visible on the page.\n"
        "- Each item must include no, stem, options (2-5), answer (ONLY the choice number/letter: ①②③④⑤ or 1-5 or A-E), rationale (if available), "
        "difficulty (1-5), area/mid_code/grade_band (use provided lists; fall back to AREA_UNKNOWN/MID_UNKNOWN/GB_UNKNOWN), "
        "cefr (analyze reading difficulty: A2/B1/B2/C1/C2 based on vocabulary, grammar complexity, and text length), type (MCQ when options>=4 else SA), and any references.\n"
        "- ANSWER FORMAT: Return ONLY the choice indicator (①, ②, ③, ④, ⑤ or 1, 2, 3, 4, 5 or A, B, C, D, E). DO NOT include any explanation or text.\n"
        "- Tables should include id, title, columns, rows (list of dicts), labels, problem_nos, and bbox_norm as an array of 4 corner points [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] where x,y are 0-1 (relative to page dimensions).\n"
        "- Figures should include id, caption, problem_nos, labels, and bbox_norm as an array of 4 corner points [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] where x,y are 0-1.\n"
        "- IMPORTANT: bbox_norm coordinates MUST be exactly 4 points forming a rectangle. Example: [[0.1,0.2],[0.9,0.2],[0.9,0.8],[0.1,0.8]] for a box from (0.1,0.2) to (0.9,0.8).\n"
        "- Respond with valid JSON only."
    )
    answer_hint = json.dumps(answers_map, ensure_ascii=False)
    taxonomy_hint = json.dumps(
        {
            "areas": taxonomy.areas,
            "mid_codes": taxonomy.mid_codes,
            "grade_bands": taxonomy.grade_bands,
        },
        ensure_ascii=False,
    )

    items: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    figures: List[Dict[str, Any]] = []

    for page in pages:
        page_no = page["page"]
        img_base64 = _encode_image(page["image"])
        data_uri = f"data:image/png;base64,{img_base64}"

        # Use annotated text if available, otherwise fall back to OCR
        if page_no in annotated_pages:
            ocr_excerpt = annotated_pages[page_no]
            text_source = "Cleaned OCR text from annotated PDF"
        else:
            ocr_excerpt = page.get("text") or ""
            text_source = "Raw OCR text (may contain noise)"

        if len(ocr_excerpt) > 8000:
            ocr_excerpt = ocr_excerpt[:8000] + "...(truncated)"

        user_prompt = (
            f"Exam ID: {exam_id}\n"
            f"Page Number: {page_no}\n"
            f"Page Dimensions: {page['width']}x{page['height']} pixels\n"
            "Hints:\n"
            f"- Answer hints: {answer_hint}\n"
            f"- Taxonomy: {taxonomy_hint}\n"
            f"- {text_source}: {ocr_excerpt}\n\n"
            "IMPORTANT Instructions:\n"
            "1. Use the OCR text for accurate option extraction.\n"
            "2. For questions with image-based options (like '그림에서'), describe what you see.\n"
            "3. For EVERY table and figure, provide bbox_norm as 4 corner points [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] where:\n"
            "   - Each point [x, y] is normalized 0-1 relative to page dimensions\n"
            "   - Points form a rectangle: top-left, top-right, bottom-right, bottom-left\n"
            "   - Example: A table in the top-left quarter would be [[0.0,0.0],[0.5,0.0],[0.5,0.5],[0.0,0.5]]\n"
            "4. Include problem_nos array indicating which problem numbers use this visual element.\n\n"
            "Return JSON with keys 'items', 'tables', 'figures'."
        )
        try:
            resp = client.responses.create(
                model=model,
                input=[  # pyright: ignore[reportArgumentType]
                    {"role": "system", "content": [{"type": "input_text", "text": sys_prompt}]},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_prompt},
                            {"type": "input_image", "image_url": data_uri},
                        ],
                    },
                ],
                max_output_tokens=max_output_tokens,
            )
        except Exception as err:
            print(f"[vlm] page {page_no} request failed: {err}")
            continue

        raw = _extract_response_text(resp)

        # Strip markdown code blocks if present
        if raw.startswith("```json"):
            raw = raw[7:]  # Remove ```json
        elif raw.startswith("```"):
            raw = raw[3:]  # Remove ```
        if raw.endswith("```"):
            raw = raw[:-3]  # Remove closing ```
        raw = raw.strip()

        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError as err:
            print(f"[vlm] page {page_no} JSON decode failed: {err} :: {raw[:120]!r}")
            continue

        for itm in payload.get("items", []) or []:
            try:
                no = int(itm.get("no"))
            except Exception:
                continue
            # Ensure options is a list
            raw_options = itm.get("options", [])
            if not isinstance(raw_options, list):
                raw_options = []
            options = [_squeeze(str(opt)) for opt in raw_options if opt and _squeeze(str(opt))]
            items.append({
                "no": no,
                "page": itm.get("page") or page_no,
                "stem": _squeeze(itm.get("stem") or ""),
                "options": options[:5],
                "answer": itm.get("answer"),
                "rationale": _squeeze(itm.get("rationale") or ""),
                "area": itm.get("area"),
                "mid_code": itm.get("mid_code"),
                "grade_band": itm.get("grade_band"),
                "cefr": itm.get("cefr"),
                "difficulty": _normalize_difficulty(itm.get("difficulty")),
                "type": itm.get("type"),
                "references": itm.get("references") or {},
                "audio_transcript": itm.get("audio_transcript"),
            })

        for tbl in payload.get("tables", []) or []:
            table_id = tbl.get("id") or tbl.get("table_id")
            tables.append({
                "table_id": table_id,
                "problem_id": None,
                "title": tbl.get("title"),
                "columns": tbl.get("columns") or [],
                "types": tbl.get("types") or {},
                "rows": tbl.get("rows") or [],
                "labels": tbl.get("labels") or [],
                "option_row_map": tbl.get("option_row_map") or {},
                "problem_nos": tbl.get("problem_nos") or [],
                "source": {
                    "file": str(Path(pdf_path).resolve()),
                    "page": tbl.get("page") or page_no,
                    "bbox_norm": tbl.get("bbox_norm"),
                },
                "storage_key": None,
                "public_url": None,
                "local_path": None,
            })

        for fig in payload.get("figures", []) or []:
            asset_id = fig.get("id") or fig.get("asset_id")
            figures.append({
                "asset_id": asset_id,
                "problem_id": None,
                "asset_type": "figure",
                "storage_key": None,
                "public_url": None,
                "mime": "image/png",
                "page": fig.get("page") or page_no,
                "bbox_norm": fig.get("bbox_norm"),
                "overlay_text": [],
                "hash": None,
                "labels": fig.get("labels") or [],
                "caption": fig.get("caption"),
                "problem_nos": fig.get("problem_nos") or [],
                "local_path": None,
            })

    return items, tables, figures
