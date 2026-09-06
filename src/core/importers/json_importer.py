"""
core/importers/json_importer.py
─────────────────────────────────
Import annotations from tode-native JSON format.
"""
from __future__ import annotations

import json
import os

from core.importers.base import BaseImporter


class JSONImporter(BaseImporter):
    """Import from a tode JSON export (``annotations.json``)."""

    def __init__(self, source_dir: str, output_labels_dir: str, json_path: str = "") -> None:
        super().__init__(source_dir, output_labels_dir)
        self._json_path = json_path or os.path.join(source_dir, "annotations.json")

    def load(self) -> tuple[list[str], int]:
        with open(self._json_path, encoding="utf-8") as fh:
            data = json.load(fh)

        class_names: list[str] = data.get("class_names", [])
        count = 0
        for stem, rows in data.get("frames", {}).items():
            self._write_yolo(stem, rows)
            count += len(rows)

        return class_names, count
