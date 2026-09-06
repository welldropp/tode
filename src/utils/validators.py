"""
utils/validators.py
─────────────────────
Input validation helpers used by dialogs and CLI entry points.
"""
from __future__ import annotations

import os
from pathlib import Path


def is_valid_confidence(value: float) -> bool:
    return 0.0 < value <= 1.0


def is_valid_iou(value: float) -> bool:
    return 0.0 < value <= 1.0


def is_valid_directory(path: str) -> bool:
    return bool(path) and os.path.isdir(path)


def is_valid_file(path: str, extensions: tuple[str, ...] | None = None) -> bool:
    if not path or not os.path.isfile(path):
        return False
    if extensions:
        return Path(path).suffix.lower() in extensions
    return True


def validate_class_names(names: list[str]) -> list[str]:
    """Strip, deduplicate, and remove empty names; return cleaned list."""
    seen:   set[str] = set()
    result: list[str] = []
    for name in names:
        cleaned = name.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
