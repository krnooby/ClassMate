# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

@dataclass
class Config:
    project: str
    location: str
    ocr_processor_id: str
    form_processor_id: Optional[str]
    gcs_bucket: Optional[str]

def load() -> Config:
    prj = os.getenv("GCP_PROJECT") or ""
    loc = os.getenv("DOC_LOCATION", "us")
    ocr = os.getenv("DOC_OCR_PROCESSOR_ID") or ""
    form = os.getenv("DOC_FORM_PROCESSOR_ID")
    bucket = os.getenv("GCS_BUCKET")
    if not prj or not ocr:
        raise RuntimeError("GCP_PROJECT 또는 DOC_OCR_PROCESSOR_ID 없음")
    return Config(prj, loc, ocr, form, bucket)

def scan_assets(folder: str) -> Dict[str, Dict[str, Optional[str]]]:
    rx = re.compile(r"^(question|answer|solution|script|listening|audio)_(.+?)\.(pdf|png|jpe?g|mp3|wav|m4a)$", re.I)
    out: Dict[str, Dict[str, Optional[str]]] = {}
    root = Path(folder)
    for p in root.rglob("*"):
        if not p.is_file(): continue
        m = rx.match(p.name)
        if not m: continue
        kind, key = m.group(1).lower(), m.group(2)
        g = out.setdefault(key, {"question":None,"answer":None,"solution":None,"script":None,"listening":None})
        g[kind] = str(p.resolve())
    return out
