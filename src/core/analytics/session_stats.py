"""
core/analytics/session_stats.py
─────────────────────────────────
Track live statistics during an annotation session.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SessionStats:
    """Mutable stats accumulated during a live annotation session."""

    start_time: float = field(default_factory=time.time)
    frames_visited:     int = 0
    annotations_added:  int = 0
    annotations_deleted: int = 0
    auto_annotations:   int = 0
    manual_annotations: int = 0

    def record_frame(self) -> None:
        self.frames_visited += 1

    def record_add(self, *, auto: bool = False) -> None:
        self.annotations_added += 1
        if auto:
            self.auto_annotations  += 1
        else:
            self.manual_annotations += 1

    def record_delete(self) -> None:
        self.annotations_deleted += 1

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def annotations_per_minute(self) -> float:
        elapsed = self.elapsed_seconds / 60
        return self.annotations_added / elapsed if elapsed > 0 else 0.0

    def summary(self) -> dict:
        return {
            "elapsed_s":         round(self.elapsed_seconds, 1),
            "frames_visited":    self.frames_visited,
            "annotations_added": self.annotations_added,
            "annotations_deleted": self.annotations_deleted,
            "auto_annotations":  self.auto_annotations,
            "manual_annotations": self.manual_annotations,
            "annotations_per_min": round(self.annotations_per_minute, 2),
        }
