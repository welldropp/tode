"""
examples/export_dataset.py
──────────────────────────
Programmatic example: build a small in-memory dataset and export it
as YOLO and as COCO. Useful for verifying the export pipeline end-to-end
without launching the GUI.

Usage:
    python examples/export_dataset.py <output_dir>
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from core.exporter import DatasetExporter  # noqa: E402
from models.annotation_model import BoundingBox, FrameAnnotation  # noqa: E402


def _build_fake_annotations(work_dir: str, n_frames: int = 3):
    os.makedirs(work_dir, exist_ok=True)
    annotations = {}
    for i in range(n_frames):
        img_path = os.path.join(work_dir, f"frame_{i:06d}.png")
        cv2.imwrite(img_path, np.full((200, 200, 3), 64, dtype=np.uint8))
        ann = FrameAnnotation(i, img_path)
        ann.add_box(BoundingBox(0, "car",    0.5, 0.5, 0.4, 0.3, 0.9))
        ann.add_box(BoundingBox(1, "person", 0.2, 0.3, 0.1, 0.2, 0.7))
        annotations[i] = ann
    return annotations


def main(out_root: str) -> int:
    work     = os.path.join(out_root, "_source_frames")
    yolo_dir = os.path.join(out_root, "yolo")
    coco_dir = os.path.join(out_root, "coco")

    annotations = _build_fake_annotations(work)
    class_names = {0: "car", 1: "person"}

    yolo = DatasetExporter(annotations, class_names, yolo_dir).export("yolo")
    coco = DatasetExporter(annotations, class_names, coco_dir).export("coco")

    print(f"YOLO  → {yolo['images']} images, classes={yolo['classes']} → {yolo['output_dir']}")
    print(f"COCO  → {coco['images']} images, labels={coco['labels']}    → {coco['output_dir']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
