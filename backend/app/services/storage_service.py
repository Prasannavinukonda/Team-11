"""Local-disk storage for uploaded fundus images.

Swappable: replace this module's implementation with an S3 / GCS backed
one for production deployments without touching the API layer, since
routes only call save_upload() / read_upload().
"""
from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def _upload_dir() -> Path:
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(file_bytes: bytes, original_filename: str) -> str:
    ext = Path(original_filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = _upload_dir() / filename
    dest.write_bytes(file_bytes)
    return str(dest)


def read_upload(image_path: str) -> bytes:
    return Path(image_path).read_bytes()
