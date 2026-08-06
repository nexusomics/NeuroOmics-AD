"""File handling utilities."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.core.config import settings


def save_upload(file_bytes: bytes, original_name: str, subdir: str = "uploads") -> tuple[Path, str]:
    """Persist an uploaded file under the storage root; returns (path, stored_name)."""
    root = settings.storage_path / subdir
    root.mkdir(parents=True, exist_ok=True)
    ext = Path(original_name).suffix.lower()
    stored = f"{uuid.uuid4().hex}{ext}"
    dest = root / stored
    dest.write_bytes(file_bytes)
    return dest, stored


def artifact_dir(analysis_id: str) -> Path:
    d = settings.storage_path / "artifacts" / analysis_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
