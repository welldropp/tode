"""
storage/formats/pascal_voc_format.py
──────────────────────────────────────
Read/write annotations in Pascal VOC XML format.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405


class PascalVOCFormat:
    """Static helpers for Pascal VOC XML annotation files."""

    @staticmethod
    def read(path: str) -> list[dict]:
        rows: list[dict] = []
        try:
            tree = ET.parse(path)  # nosec B314
            root = tree.getroot()
            size = root.find("size")
            img_w = int(size.findtext("width", "640"))
            img_h = int(size.findtext("height", "640"))
            for obj in root.findall("object"):
                name = obj.findtext("name", "")
                bb   = obj.find("bndbox")
                if bb is None:
                    continue
                xmin = float(bb.findtext("xmin", "0"))
                ymin = float(bb.findtext("ymin", "0"))
                xmax = float(bb.findtext("xmax", "640"))
                ymax = float(bb.findtext("ymax", "640"))
                rows.append({
                    "name": name,
                    "xmin": xmin, "ymin": ymin,
                    "xmax": xmax, "ymax": ymax,
                    "img_w": img_w, "img_h": img_h,
                })
        except (FileNotFoundError, ET.ParseError):
            pass
        return rows

    @staticmethod
    def write(path: str, rows: list[dict], img_w: int = 640, img_h: int = 640, filename: str = "frame.jpg") -> None:
        ann = ET.Element("annotation")
        ET.SubElement(ann, "filename").text = filename
        size = ET.SubElement(ann, "size")
        ET.SubElement(size, "width").text  = str(img_w)
        ET.SubElement(size, "height").text = str(img_h)
        ET.SubElement(size, "depth").text  = "3"
        for r in rows:
            obj = ET.SubElement(ann, "object")
            ET.SubElement(obj, "name").text = r.get("name", "object")
            bb = ET.SubElement(obj, "bndbox")
            ET.SubElement(bb, "xmin").text = str(int(r.get("xmin", 0)))
            ET.SubElement(bb, "ymin").text = str(int(r.get("ymin", 0)))
            ET.SubElement(bb, "xmax").text = str(int(r.get("xmax", img_w)))
            ET.SubElement(bb, "ymax").text = str(int(r.get("ymax", img_h)))
        tree = ET.ElementTree(ann)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="unicode", xml_declaration=False)
