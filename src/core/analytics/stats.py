"""
core/analytics/stats.py
─────────────────────────
Core annotation statistics aggregator.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class AnnotationStats:
    """Aggregate statistics for a set of annotated frames."""

    total_annotations: int = 0
    annotated_frames:  int = 0
    total_frames:      int = 0
    class_counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_label_dir(cls, labels_dir: str, class_names: list[str]) -> AnnotationStats:
        """Build stats by scanning a YOLO labels directory."""
        import os

        stats = cls()
        if not os.path.isdir(labels_dir):
            return stats

        counts: dict[int, int] = defaultdict(int)
        for fname in os.listdir(labels_dir):
            if not fname.endswith(".txt"):
                continue
            stats.total_frames += 1
            frame_has_ann = False
            with open(os.path.join(labels_dir, fname), encoding="utf-8") as fh:
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    counts[int(parts[0])] += 1
                    stats.total_annotations += 1
                    frame_has_ann = True
            if frame_has_ann:
                stats.annotated_frames += 1

        stats.class_counts = {
            class_names[i] if i < len(class_names) else str(i): v
            for i, v in counts.items()
        }
        return stats

    @property
    def annotation_rate(self) -> float:
        """Fraction of frames that have at least one annotation."""
        if not self.total_frames:
            return 0.0
        return self.annotated_frames / self.total_frames
