"""
core/exporters/pascal_voc.py
──────────────────────────────
Export annotations as Pascal VOC XML files.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET  # nosec B405

from core.exporters.base import BaseExporter


class PascalVOCExporter(BaseExporter):
    """Export one XML file per image in Pascal VOC format."""

    def export(self) -> int:
        xml_dir = os.path.join(self.output_dir, "Annotations")
        os.makedirs(xml_dir, exist_ok=True)
        count = 0

        for lbl_file in self._label_files():
            stem     = os.path.splitext(lbl_file)[0]
            img_w, img_h = 640, 640
            img_name = stem + ".jpg"

            for ext in (".jpg", ".jpeg", ".png", ".bmp"):
                img_path = os.path.join(self.images_dir, stem + ext)
                if os.path.isfile(img_path):
                    img_name = stem + ext
                    try:
                        from PIL import Image  # type: ignore
                        with Image.open(img_path) as im:
                            img_w, img_h = im.size
                    except Exception:  # nosec B110
                        pass
                    break

            annotation = ET.Element("annotation")
            ET.SubElement(annotation, "filename").text = img_name
            size = ET.SubElement(annotation, "size")
            ET.SubElement(size, "width").text  = str(img_w)
            ET.SubElement(size, "height").text = str(img_h)
            ET.SubElement(size, "depth").text  = "3"

            for row in self._parse_label_file(lbl_file):
                xmin = int((row["cx"] - row["w"] / 2) * img_w)
                ymin = int((row["cy"] - row["h"] / 2) * img_h)
                xmax = int((row["cx"] + row["w"] / 2) * img_w)
                ymax = int((row["cy"] + row["h"] / 2) * img_h)
                name = (
                    self.class_names[row["class_id"]]
                    if row["class_id"] < len(self.class_names)
                    else str(row["class_id"])
                )
                obj = ET.SubElement(annotation, "object")
                ET.SubElement(obj, "name").text = name
                bndbox = ET.SubElement(obj, "bndbox")
                ET.SubElement(bndbox, "xmin").text = str(xmin)
                ET.SubElement(bndbox, "ymin").text = str(ymin)
                ET.SubElement(bndbox, "xmax").text = str(xmax)
                ET.SubElement(bndbox, "ymax").text = str(ymax)
                count += 1

            tree = ET.ElementTree(annotation)
            ET.indent(tree, space="  ")
            tree.write(os.path.join(xml_dir, stem + ".xml"), encoding="unicode", xml_declaration=False)

        return count
