"""
utils/date_utils.py
─────────────────────
Date/time formatting helpers.
"""
from __future__ import annotations

from datetime import UTC, datetime


def utcnow_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_filename_safe() -> str:
    """Return current local time as a filename-safe string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_elapsed(seconds: float) -> str:
    """Return a human-readable elapsed time like '2h 03m 14s'."""
    seconds = int(seconds)
    h, rem  = divmod(seconds, 3600)
    m, s    = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"
