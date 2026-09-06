"""
core/analytics/report_generator.py
─────────────────────────────────────
Generate text/JSON reports from annotation statistics.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from core.analytics.session_stats import SessionStats
from core.analytics.stats import AnnotationStats


class ReportGenerator:
    """Generate human-readable and machine-readable reports."""

    def __init__(self, stats: AnnotationStats, session: SessionStats | None = None) -> None:
        self._stats   = stats
        self._session = session

    def to_json(self, output_path: str) -> None:
        """Write a JSON report to *output_path*."""
        payload: dict = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "annotation_stats": {
                "total_annotations": self._stats.total_annotations,
                "annotated_frames":  self._stats.annotated_frames,
                "total_frames":      self._stats.total_frames,
                "annotation_rate":   round(self._stats.annotation_rate, 4),
                "class_counts":      self._stats.class_counts,
            },
        }
        if self._session:
            payload["session_stats"] = self._session.summary()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def to_text(self) -> str:
        """Return a human-readable report string."""
        s = self._stats
        lines = [
            "=== tode Annotation Report ===",
            f"Generated : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"Total annotations : {s.total_annotations}",
            f"Annotated frames  : {s.annotated_frames} / {s.total_frames}"
            f" ({s.annotation_rate:.1%})",
            "",
            "Class distribution:",
        ]
        for cls, cnt in sorted(s.class_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {cls:<20s} {cnt:>6d}")

        if self._session:
            sm = self._session.summary()
            lines += [
                "",
                "Session:",
                f"  Duration         : {sm['elapsed_s']}s",
                f"  Frames visited   : {sm['frames_visited']}",
                f"  Annotations/min  : {sm['annotations_per_min']}",
            ]
        return "\n".join(lines)
