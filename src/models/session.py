"""
models/session.py
───────────────────
Data model for a tode annotation session (persisted as JSON).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Session:
    """Represents one annotation session — source path, classes, progress."""

    source_path:    str
    class_names:    list[str] = field(default_factory=list)
    current_frame:  int       = 0
    total_frames:   int       = 0
    created_at:     str       = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at:     str       = field(default_factory=lambda: datetime.utcnow().isoformat())

    def save(self, path: str) -> None:
        self.updated_at = datetime.utcnow().isoformat()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> Session:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(**data)
