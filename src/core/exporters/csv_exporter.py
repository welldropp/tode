"""
core/exporters/csv_exporter.py
────────────────────────────────
Export annotations to a flat CSV file.
"""
from __future__ import annotations

import csv
import os

from core.exporters.base import BaseExporter


class CSVExporter(BaseExporter):
    """Export all annotations to a single ``annotations.csv``."""

    _FIELDNAMES = ["filename", "class_id", "class_name", "cx", "cy", "w", "h"]

    def export(self) -> int:
        out_path = os.path.join(self.output_dir, "annotations.csv")
        count    = 0

        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._FIELDNAMES)
            writer.writeheader()
            for lbl_file in self._label_files():
                stem = os.path.splitext(lbl_file)[0]
                for row in self._parse_label_file(lbl_file):
                    cls_id   = row["class_id"]
                    cls_name = (
                        self.class_names[cls_id]
                        if cls_id < len(self.class_names)
                        else str(cls_id)
                    )
                    writer.writerow({
                        "filename":   stem,
                        "class_id":   cls_id,
                        "class_name": cls_name,
                        "cx":         round(row["cx"], 6),
                        "cy":         round(row["cy"], 6),
                        "w":          round(row["w"],  6),
                        "h":          round(row["h"],  6),
                    })
                    count += 1
        return count
