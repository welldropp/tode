"""
core/exporters/yolo.py
────────────────────────
Export annotations in YOLO v5+ format (labels/ + images/ + data.yaml).
"""
from __future__ import annotations

import os
import shutil

from core.exporters.base import BaseExporter


class YOLOExporter(BaseExporter):
    """Export to YOLO directory layout with data.yaml."""

    def export(self) -> int:
        out_labels = os.path.join(self.output_dir, "labels")
        out_images = os.path.join(self.output_dir, "images")
        os.makedirs(out_labels, exist_ok=True)
        os.makedirs(out_images, exist_ok=True)

        count = 0
        for lbl_file in self._label_files():
            stem = os.path.splitext(lbl_file)[0]
            src_lbl = os.path.join(self.labels_dir, lbl_file)
            dst_lbl = os.path.join(out_labels, lbl_file)
            shutil.copy2(src_lbl, dst_lbl)

            for ext in (".jpg", ".jpeg", ".png", ".bmp"):
                src_img = os.path.join(self.images_dir, stem + ext)
                if os.path.isfile(src_img):
                    shutil.copy2(src_img, os.path.join(out_images, stem + ext))
                    break

            count += len(self._parse_label_file(lbl_file))

        self._write_yaml()
        return count

    def _write_yaml(self) -> None:
        names_block = "\n".join(f"  {i}: {n}" for i, n in enumerate(self.class_names))
        yaml_content = (
            f"path: {self.output_dir}\n"
            f"train: images\n"
            f"val: images\n\n"
            f"nc: {len(self.class_names)}\n"
            f"names:\n{names_block}\n"
        )
        with open(os.path.join(self.output_dir, "data.yaml"), "w", encoding="utf-8") as fh:
            fh.write(yaml_content)
