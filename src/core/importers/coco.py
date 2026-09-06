"""
core/importers/coco.py
────────────────────────
Import annotations from a COCO JSON file.
"""
from __future__ import annotations

import json
import os

from core.importers.base import BaseImporter


class COCOImporter(BaseImporter):
    """
    Import from a COCO-format annotations.json.

    Parameters
    ----------
    json_path : str
        Path to the COCO JSON file (overrides *source_dir* if given).
    """

    def __init__(self, source_dir: str, output_labels_dir: str, json_path: str = "") -> None:
        super().__init__(source_dir, output_labels_dir)
        self._json_path = json_path or os.path.join(source_dir, "annotations.json")

    def load(self) -> tuple[list[str], int]:
        with open(self._json_path, encoding="utf-8") as fh:
            data = json.load(fh)

        id_to_name = {c["id"]: c["name"] for c in data.get("categories", [])}
        class_names = [id_to_name[k] for k in sorted(id_to_name)]
        name_to_idx = {n: i for i, n in enumerate(class_names)}

        img_id_to_info = {
            img["id"]: img for img in data.get("images", [])
        }

        by_image: dict[int, list] = {}
        for ann in data.get("annotations", []):
            by_image.setdefault(ann["image_id"], []).append(ann)

        count = 0
        for img_id, anns in by_image.items():
            info  = img_id_to_info.get(img_id, {})
            img_w = info.get("width", 640)
            img_h = info.get("height", 640)
            stem  = os.path.splitext(info.get("file_name", str(img_id)))[0]
            rows  = []
            for ann in anns:
                x, y, w, h = ann["bbox"]
                cat_name = id_to_name.get(ann["category_id"], "")
                cls_id   = name_to_idx.get(cat_name, 0)
                rows.append({
                    "class_id": cls_id,
                    "cx": (x + w / 2) / img_w,
                    "cy": (y + h / 2) / img_h,
                    "w":  w / img_w,
                    "h":  h / img_h,
                })
                count += 1
            self._write_yolo(stem, rows)

        return class_names, count
