"""
core/exporters/coco.py
────────────────────────
Export annotations in COCO JSON format.
"""
from __future__ import annotations

import json
import os

from core.exporters.base import BaseExporter


class COCOExporter(BaseExporter):
    """Export to a single ``annotations.json`` in COCO format."""

    def export(self) -> int:
        categories = [
            {"id": i, "name": n, "supercategory": "object"}
            for i, n in enumerate(self.class_names)
        ]
        images   = []
        anns     = []
        ann_id   = 0
        img_id   = 0
        count    = 0

        for lbl_file in self._label_files():
            stem  = os.path.splitext(lbl_file)[0]
            img_w, img_h = 640, 640  # fallback if image not found

            for ext in (".jpg", ".jpeg", ".png", ".bmp"):
                img_path = os.path.join(self.images_dir, stem + ext)
                if os.path.isfile(img_path):
                    try:
                        from PIL import Image  # type: ignore
                        with Image.open(img_path) as im:
                            img_w, img_h = im.size
                    except Exception:  # nosec B110
                        pass
                    break

            images.append({"id": img_id, "file_name": stem + ".jpg", "width": img_w, "height": img_h})

            for row in self._parse_label_file(lbl_file):
                x = (row["cx"] - row["w"] / 2) * img_w
                y = (row["cy"] - row["h"] / 2) * img_h
                w = row["w"] * img_w
                h = row["h"] * img_h
                anns.append({
                    "id": ann_id,
                    "image_id": img_id,
                    "category_id": row["class_id"],
                    "bbox": [round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
                    "area": round(w * h, 2),
                    "iscrowd": 0,
                })
                ann_id += 1
                count  += 1

            img_id += 1

        payload = {
            "info":        {"description": "tode export"},
            "categories":  categories,
            "images":      images,
            "annotations": anns,
        }
        out_path = os.path.join(self.output_dir, "annotations.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return count
