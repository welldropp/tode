"""
core/importers/csv_importer.py
────────────────────────────────
Import annotations from a flat CSV file.
"""
from __future__ import annotations

import csv
import os

from core.importers.base import BaseImporter


class CSVImporter(BaseImporter):
    """Import from a flat CSV with columns: filename, class_id, class_name, cx, cy, w, h."""

    def load(self) -> tuple[list[str], int]:
        csv_path = os.path.join(self.source_dir, "annotations.csv")
        if not os.path.isfile(csv_path):
            for f in os.listdir(self.source_dir):
                if f.endswith(".csv"):
                    csv_path = os.path.join(self.source_dir, f)
                    break

        by_file: dict[str, list] = {}
        class_set: dict[int, str] = {}
        count = 0

        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                stem   = row.get("filename", "frame")
                cls_id = int(row.get("class_id", 0))
                cls_nm = row.get("class_name", str(cls_id))
                class_set[cls_id] = cls_nm
                by_file.setdefault(stem, []).append({
                    "class_id": cls_id,
                    "cx": float(row.get("cx", 0.5)),
                    "cy": float(row.get("cy", 0.5)),
                    "w":  float(row.get("w",  0.1)),
                    "h":  float(row.get("h",  0.1)),
                })
                count += 1

        for stem, rows in by_file.items():
            self._write_yolo(stem, rows)

        class_names = [class_set.get(i, str(i)) for i in sorted(class_set)]
        return class_names, count
