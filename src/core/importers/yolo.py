"""
core/importers/yolo.py
────────────────────────
Import annotations from a YOLO-format dataset directory.
"""
from __future__ import annotations

import os

from core.importers.base import BaseImporter


class YOLOImporter(BaseImporter):
    """Import from a YOLO dataset (labels/*.txt + optional data.yaml)."""

    def load(self) -> tuple[list[str], int]:
        labels_dir = os.path.join(self.source_dir, "labels")
        if not os.path.isdir(labels_dir):
            labels_dir = self.source_dir

        class_names: list[str] = []
        yaml_path = os.path.join(self.source_dir, "data.yaml")
        if os.path.isfile(yaml_path):
            class_names = self._parse_yaml_names(yaml_path)

        count = 0
        for fname in os.listdir(labels_dir):
            if not fname.endswith(".txt"):
                continue
            stem = os.path.splitext(fname)[0]
            rows: list[dict] = []
            with open(os.path.join(labels_dir, fname), encoding="utf-8") as fh:
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    rows.append({
                        "class_id": int(parts[0]),
                        "cx": float(parts[1]),
                        "cy": float(parts[2]),
                        "w":  float(parts[3]),
                        "h":  float(parts[4]),
                    })
            self._write_yolo(stem, rows)
            count += len(rows)

        return class_names, count

    @staticmethod
    def _parse_yaml_names(path: str) -> list[str]:
        names: list[str] = []
        in_names = False
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("names:"):
                    in_names = True
                    continue
                if in_names:
                    stripped = line.strip()
                    if stripped.startswith("-"):
                        names.append(stripped.lstrip("- "))
                    elif ":" in stripped and not stripped.startswith(" "):
                        break
        return names
