# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Dict, Tuple
from pathlib import Path
from teacher.parser.docai_utils import process_file, doc_text
import fitz  # type: ignore

ANS1 = re.compile(r"(?m)^\s*(\d{1,3})\s*[\).:：-]?\s*([A-Ea-e1-9]|[①-⑳])\b")
ANS2 = re.compile(r"(?mi)^\s*(\d{1,3})\s*(?:번)?\s*(?:정답|Answer)\s*[:：=\)]?\s*([A-Ea-e1-9]|[①-⑳])\b")

def parse_answer_any(project: str, location: str, pid: str, path: str) -> Dict[int,str]:
    d = process_file(project, location, pid, path)
    t = doc_text(d)
    out: Dict[int,str] = {}
    for m in ANS1.finditer(t): out[int(m.group(1))] = m.group(2).upper()
    for m in ANS2.finditer(t): out[int(m.group(1))] = m.group(2).upper()
    return out

def _pdf_pages(path: str) -> int:
    d = fitz.open(path); n=d.page_count; d.close(); return n

def parse_solution(project: str, location: str, pid: str, path: str) -> Tuple[Dict[int,str], Dict[int,str]]:
    # 15p 초과는 로컬 텍스트로 우회
    if Path(path).suffix.lower()==".pdf" and _pdf_pages(path)>15:
        d=fitz.open(path)
        txt="\n".join(p.get_text("text") for p in d); d.close()  # type: ignore[attr-defined]
    else:
        d = process_file(project, location, pid, path)
        txt = doc_text(d)
    parts = re.split(r"(?m)^\s*(\d{1,3})[.)]\s+", txt or "")
    answers: Dict[int,str] = {}; rationales: Dict[int,str] = {}
    for i in range(1,len(parts),2):
        try: no=int(parts[i])
        except: continue
        body=(parts[i+1] or "").strip()
        m = re.search(r"(?:정답|Answer)\s*[:：]?\s*([A-Ea-e1-9]|[①-⑳])", body, re.I)
        if m: answers[no]=m.group(1).upper()
        rationales[no] = re.sub(r"^\s*(?:정답|Answer).*$","", body, flags=re.I|re.M).strip()
    return answers, rationales
