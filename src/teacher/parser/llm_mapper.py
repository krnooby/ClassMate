# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any
import json, re
from openai import OpenAI  # type: ignore

def _heal(opts: List[str]) -> List[str]:
    def sq(s:str)->str: return re.sub(r"[ \t\u00A0\u2000-\u200B\ufeff]+"," ", s).strip()
    out=[sq(o) for o in opts if sq(o)]
    return out[:5]

_SYS = (
"You are a curriculum metadata mapper for mock CSAT-style English exams. "
"Given raw items, fill in taxonomy fields and enrich with short metadata. "
"Return STRICT JSON with key 'items'; each element must contain:"
" item_id, area, mid_code, grade_band, cefr, difficulty (1-5 integer), type (always 'MCQ'), "
"stem, options (exactly 5 strings; reuse the provided order), answer, rationale, "
"audio_transcript (if supplied), tags, and features."
" Guidelines:\n"
" - area/mid_code/grade_band should come from the supplied taxonomy; if unsure use AREA_UNKNOWN/MID_UNKNOWN/GB_UNKNOWN.\n"
" - cefr defaults to B1 when the prompt gives no clue.\n"
" - tags: 1-3 concise English skill labels (e.g., 'object complement', 'listening purpose').\n"
" - features: small JSON object capturing key attributes such as {'skill': '...', 'focus': '...', 'context': '...'}; keep values short.\n"
" - Never invent or drop answer choices; do not translate stems.\n"
" - Preserve any provided audio_transcript URL unchanged.\n"
" Respond with valid JSON only."
)

def map_with_gpt5(exam_id: str, items_in: List[Dict[str,Any]],
                  taxonomy: Dict[str,Any], api_key: str, model="o4-mini", batch_size=15)->List[Dict[str,Any]]:
    """
    Classify problems with o4-mini in batches to avoid token limits.

    Args:
        exam_id: Exam identifier
        items_in: List of problems to classify
        taxonomy: Taxonomy dict with areas, mid_codes, grade_bands
        api_key: OpenAI API key
        model: Model name (default: o4-mini)
        batch_size: Number of problems to process per batch (default: 15)

    Returns:
        List of classified problems with tags and features
    """
    cli = OpenAI(api_key=api_key)
    all_results = []

    # Process in batches
    for batch_start in range(0, len(items_in), batch_size):
        batch_end = min(batch_start + batch_size, len(items_in))
        batch = items_in[batch_start:batch_end]

        print(f"   Processing batch {batch_start+1}-{batch_end} ({len(batch)} problems)...")

        payload = {"exam_id":exam_id,"taxonomy":taxonomy,"items":[
            {"item_id":it["item_id"],"no":it["no"],"stem":it["stem"],
             "options":_heal(it.get("options",[])),
             "answer":it.get("answer"),"rationale":it.get("rationale",""),
             "audio_transcript":it.get("audio_transcript")} for it in batch]}

        r = cli.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":_SYS},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}],
            response_format={"type":"json_object"},
            max_completion_tokens=8000  # Increase token limit for longer responses
        )

        js = json.loads(r.choices[0].message.content or "{}").get("items",[])

        # Process batch results
        for i,it in enumerate(js):
            if i >= len(batch):
                break  # Safety check
            base = batch[i]
            it.setdefault("item_id", base["item_id"])
            it.setdefault("no", base.get("no"))  # Preserve problem number
            it.setdefault("stem", base["stem"])
            it["options"]=_heal(it.get("options",[]) or base.get("options",[]))
            it.setdefault("answer", base.get("answer"))  # Preserve answer
            if base.get("audio_transcript"): it["audio_transcript"]=base["audio_transcript"]
            it.setdefault("area","AREA_UNKNOWN"); it.setdefault("mid_code","MID_UNKNOWN")
            it.setdefault("grade_band","GB_UNKNOWN"); it.setdefault("cefr","A1")
            it["difficulty"]=int(it.get("difficulty") or 1)
            it.setdefault("type","MCQ" if len(it["options"])>=4 else "SA")
            it.setdefault("rationale",""); it.setdefault("tags",[]); it.setdefault("features",{})
            all_results.append(it)

    return all_results
