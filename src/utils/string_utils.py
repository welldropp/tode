"""
utils/string_utils.py
───────────────────────
Miscellaneous string helpers.
"""
from __future__ import annotations

import re


def truncate(text: str, max_len: int = 40, suffix: str = "…") -> str:
    """Truncate *text* to *max_len* characters, appending *suffix* if cut."""
    return text if len(text) <= max_len else text[: max_len - len(suffix)] + suffix


def slugify(text: str) -> str:
    """Convert *text* to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    slug = slug.strip("_")
    return slug or "untitled"


def human_size(num_bytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"


def pluralise(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"
