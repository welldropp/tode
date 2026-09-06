"""
utils/file_utils.py
─────────────────────
File-system helpers used across the application.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTS


def is_video(path: str) -> bool:
    return Path(path).suffix.lower() in _VIDEO_EXTS


def list_images(directory: str) -> list[str]:
    """Return sorted list of image file paths in *directory*."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if Path(f).suffix.lower() in _IMAGE_EXTS
    )


def ensure_dir(path: str) -> str:
    """Create *path* if it doesn't exist; return *path*."""
    os.makedirs(path, exist_ok=True)
    return path


def safe_copy(src: str, dst: str) -> bool:
    """Copy *src* to *dst*; return True on success."""
    try:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except OSError:
        return False


def stem(path: str) -> str:
    """Return the filename stem (no directory, no extension)."""
    return Path(path).stem
