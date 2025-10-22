# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import quote
from google.cloud import storage

def _clean_bucket(b: Optional[str]) -> Optional[str]:
    if not b: return None
    return b.replace("gs://","").split("/")[0]

def _mime(path: str) -> str:
    s = Path(path).suffix.lower()
    return {
        ".pdf":"application/pdf",".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",
        ".mp3":"audio/mpeg",".wav":"audio/wav",".m4a":"audio/mp4"
    }.get(s, "application/octet-stream")

def _public_url(bucket: str, blob_path: str) -> str:
    return f"https://storage.googleapis.com/{bucket}/{quote(blob_path, safe='/')}"

def upload_public(local: str, bucket: Optional[str], dest_blob: str) -> Tuple[str, str]:
    """
    UBLA 공개 버킷(정책으로 allUsers:Object Viewer) 전제.
    객체 ACL은 건드리지 않음. 권한 없으면 403을 그대로 던짐.
    """
    bname = _clean_bucket(bucket) or ""
    if not bname: raise RuntimeError("GCS_BUCKET 미설정")
    cli = storage.Client()
    blob = cli.bucket(bname).blob(dest_blob)

    # Check if blob already exists to avoid delete permission issue
    if blob.exists():
        # Return existing URL without re-uploading
        return _public_url(bname, dest_blob), f"gs://{bname}/{dest_blob}"

    blob.content_type = _mime(local)
    blob.upload_from_filename(local, content_type=blob.content_type)  # resumable 내부 사용
    return _public_url(bname, dest_blob), f"gs://{bname}/{dest_blob}"
