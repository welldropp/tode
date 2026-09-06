"""
core/analytics/class_stats.py
───────────────────────────────
Per-class statistics computed from annotation data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClassStats:
    """Statistics for a single class."""

    name:      str
    count:     int
    frequency: float   # relative frequency in [0, 1]
    avg_area:  float   # average bounding-box area (in normalised units)


def compute_class_stats(class_names: list[str], labels_dir: str) -> list[ClassStats]:
    """Return per-class statistics for all label files in *labels_dir*."""
    import os

    counts:    dict[int, int]   = {}
    area_sums: dict[int, float] = {}

    if os.path.isdir(labels_dir):
        for fname in os.listdir(labels_dir):
            if not fname.endswith(".txt"):
                continue
            with open(os.path.join(labels_dir, fname), encoding="utf-8") as fh:
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    cls_id = int(parts[0])
                    w, h   = float(parts[3]), float(parts[4])
                    counts[cls_id]    = counts.get(cls_id, 0) + 1
                    area_sums[cls_id] = area_sums.get(cls_id, 0.0) + w * h

    total = sum(counts.values()) or 1
    result = []
    for cls_id, cnt in sorted(counts.items()):
        name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
        result.append(ClassStats(
            name=name,
            count=cnt,
            frequency=cnt / total,
            avg_area=area_sums.get(cls_id, 0.0) / cnt,
        ))
    return result
