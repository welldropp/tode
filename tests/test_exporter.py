"""DatasetExporter — YOLO + COCO formats."""
import json
import os

import cv2
import numpy as np
import pytest

from core.exporter import DatasetExporter
from models.annotation_model import BoundingBox, FrameAnnotation


@pytest.fixture()
def setup(tmp_path):
    imgs = []
    for i in range(3):
        p = str(tmp_path / f"frame_{i:06d}.png")
        cv2.imwrite(p, np.zeros((100, 100, 3), dtype=np.uint8))
        imgs.append(p)

    class_names = {0: "car", 1: "person"}
    annotations = {}
    for i, img_path in enumerate(imgs):
        ann = FrameAnnotation(i, img_path)
        ann.add_box(BoundingBox(0, "car", 0.5, 0.5, 0.4, 0.3, 0.9))
        annotations[i] = ann

    out_dir = str(tmp_path / "export")
    return annotations, class_names, out_dir


class TestDatasetExporter:
    def test_yolo_export_creates_files(self, setup):
        annotations, class_names, out_dir = setup
        exp    = DatasetExporter(annotations, class_names, out_dir)
        result = exp.export("yolo")

        assert result["format"] == "yolo"
        assert result["images"] == 3
        assert os.path.isdir(os.path.join(out_dir, "images"))
        assert os.path.isdir(os.path.join(out_dir, "labels"))
        assert os.path.exists(os.path.join(out_dir, "classes.txt"))
        assert os.path.exists(os.path.join(out_dir, "data.yaml"))

    def test_yolo_label_content(self, setup):
        annotations, class_names, out_dir = setup
        DatasetExporter(annotations, class_names, out_dir).export("yolo")

        lbl = os.path.join(out_dir, "labels", "img_1.txt")
        assert os.path.exists(lbl)
        with open(lbl) as f:
            line = f.read().strip().split()
        assert line[0] == "0"
        assert float(line[1]) == pytest.approx(0.5, rel=1e-4)

    def test_yolo_data_yaml_content(self, setup):
        annotations, class_names, out_dir = setup
        DatasetExporter(annotations, class_names, out_dir).export("yolo")

        with open(os.path.join(out_dir, "data.yaml")) as f:
            content = f.read()
        assert "nc: " in content
        assert "names:" in content

    def test_coco_export_creates_annotations_json(self, setup):
        annotations, class_names, out_dir = setup
        result = DatasetExporter(annotations, class_names, out_dir).export("coco")

        assert result["format"] == "coco"
        json_path = os.path.join(out_dir, "annotations.json")
        assert os.path.exists(json_path)
        with open(json_path) as f:
            coco = json.load(f)
        assert "images" in coco
        assert "annotations" in coco
        assert "categories" in coco
        assert len(coco["images"]) == 3
        assert len(coco["annotations"]) == 3

    def test_coco_bbox_pixel_coords(self, setup):
        annotations, class_names, out_dir = setup
        DatasetExporter(annotations, class_names, out_dir).export("coco")

        with open(os.path.join(out_dir, "annotations.json")) as f:
            coco = json.load(f)
        bbox = coco["annotations"][0]["bbox"]
        # box: cx=0.5, cy=0.5, w=0.4, h=0.3 → image 100x100
        assert bbox[0] == pytest.approx(30.0, abs=0.1)
        assert bbox[1] == pytest.approx(35.0, abs=0.1)
        assert bbox[2] == pytest.approx(40.0, abs=0.1)
        assert bbox[3] == pytest.approx(30.0, abs=0.1)

    def test_unknown_format_raises(self, setup):
        annotations, class_names, out_dir = setup
        with pytest.raises(ValueError, match="Unknown export format"):
            DatasetExporter(annotations, class_names, out_dir).export("csv")

    def test_no_annotated_frames_raises(self, tmp_path):
        ann = {0: FrameAnnotation(0, "/fake.png")}  # is_annotated=False
        with pytest.raises(ValueError, match="Nothing to export"):
            DatasetExporter(ann, {}, str(tmp_path / "out")).export("yolo")

    def test_progress_callback_called(self, setup):
        annotations, class_names, out_dir = setup
        calls = []
        DatasetExporter(annotations, class_names, out_dir).export(
            "yolo", progress_callback=lambda cur, tot: calls.append((cur, tot))
        )
        assert len(calls) == 3
        assert calls[-1] == (3, 3)

    def test_class_id_map_preserves_model_order(self, setup):
        annotations, class_names, out_dir = setup
        exp = DatasetExporter(annotations, class_names, out_dir)
        id_map = exp._build_class_id_map(list(annotations.values()))
        assert id_map["car"] == 0
        assert id_map["person"] == 1
