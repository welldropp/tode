"""
core/exporters/json_exporter.py
─────────────────────────────────
Export annotations to a tode-native JSON file.
"""
from __future__ import annotations

import json
import os

from core.exporters.base import BaseExporter


class JSONExporter(BaseExporter):
    """Export to a structured JSON file keyed by frame filename."""

    def export(self) -> int:
        data:  dict = {"class_names": self.class_names, "frames": {}}
        count = 0

        for lbl_file in self._label_files():
            stem = os.path.splitext(lbl_file)[0]
            rows = self._parse_label_file(lbl_file)
            data["frames"][stem] = rows
            count += len(rows)

        out_path = os.path.join(self.output_dir, "annotations.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return count
