"""LabelStorage (YOLO + JSON) and FrameStorage."""
import json
import os

import numpy as np
import pytest

from models.annotation_model import BoundingBox, FrameAnnotation
from storage.frame_storage import FrameStorage
from storage.label_storage import LabelStorage


class TestLabelStorageYOLO:
    """YOLO .txt round-trip."""

    @pytest.fixture(autouse=True)
    def tmp_labels(self, tmp_path, monkeypatch):
        import storage.label_storage as ls_mod
        import utils.config as cfg
        monkeypatch.setattr(cfg, "LABELS_DIR", str(tmp_path))
        monkeypatch.setattr(ls_mod, "LABELS_DIR", str(tmp_path))

    def test_yolo_roundtrip(self, tmp_path):
        storage = LabelStorage.__new__(LabelStorage)
        storage.video_name = "test_vid"
        storage.fmt        = "yolo"
        storage.base_dir   = str(tmp_path / "test_vid")
        os.makedirs(storage.base_dir, exist_ok=True)
        storage._class_map = {}

        box1 = BoundingBox(0, "car",  0.5, 0.5, 0.4, 0.3, 0.9)
        box2 = BoundingBox(1, "person", 0.2, 0.3, 0.1, 0.2, 0.7)
        ann  = FrameAnnotation(42, str(tmp_path / "frame_000042.png"))
        ann.add_box(box1)
        ann.add_box(box2)

        path  = storage.save(ann)
        assert os.path.exists(path)

        boxes = storage.load(str(tmp_path / "frame_000042.png"))
        assert boxes is not None
        assert len(boxes) == 2
        assert boxes[0].class_name == "car"
        assert boxes[1].class_name == "person"
        assert boxes[0].x_center == pytest.approx(0.5, rel=1e-4)

    def test_yolo_empty_frame_loads_empty(self, tmp_path):
        storage = LabelStorage.__new__(LabelStorage)
        storage.video_name = "test_vid"
        storage.fmt        = "yolo"
        storage.base_dir   = str(tmp_path / "test_vid")
        os.makedirs(storage.base_dir, exist_ok=True)
        storage._class_map = {}

        boxes = storage.load(str(tmp_path / "frame_000007.png"))
        assert boxes == []

    def test_class_map_sidecar_written(self, tmp_path):
        storage = LabelStorage.__new__(LabelStorage)
        storage.video_name = "v"
        storage.fmt        = "yolo"
        storage.base_dir   = str(tmp_path / "v")
        os.makedirs(storage.base_dir, exist_ok=True)
        storage._class_map = {}

        ann = FrameAnnotation(1, str(tmp_path / "frame_000001.png"))
        ann.add_box(BoundingBox(0, "truck", 0.5, 0.5, 0.2, 0.2))
        storage.save(ann)

        classes_path = os.path.join(storage.base_dir, "classes.json")
        assert os.path.exists(classes_path)
        with open(classes_path) as f:
            data = json.load(f)
        assert data["0"] == "truck"

    def test_unknown_class_id_falls_back_to_string(self, tmp_path):
        storage = LabelStorage.__new__(LabelStorage)
        storage.video_name = "v"
        storage.fmt        = "yolo"
        storage.base_dir   = str(tmp_path / "v")
        os.makedirs(storage.base_dir, exist_ok=True)
        storage._class_map = {}

        lbl = os.path.join(storage.base_dir, "frame_000001.txt")
        with open(lbl, "w") as f:
            f.write("99 0.5 0.5 0.2 0.2\n")

        boxes = storage.load(str(tmp_path / "frame_000001.png"))
        assert len(boxes) == 1
        assert boxes[0].class_name == "99"

    def test_index_from_path_parses_correctly(self):
        assert LabelStorage._index_from_path("/some/path/frame_000042.png") == 42
        assert LabelStorage._index_from_path("/some/path/frame_000001.png") == 1
        assert LabelStorage._index_from_path("/no_frame_here.png") is None

    def test_json_roundtrip(self, tmp_path):
        storage = LabelStorage.__new__(LabelStorage)
        storage.video_name = "v"
        storage.fmt        = "json"
        storage.base_dir   = str(tmp_path / "v")
        os.makedirs(storage.base_dir, exist_ok=True)
        storage._class_map = {}

        box = BoundingBox(2, "bike", 0.3, 0.4, 0.15, 0.1, 0.85)
        ann = FrameAnnotation(5, str(tmp_path / "frame_000005.png"))
        ann.add_box(box)
        storage.save(ann)

        boxes = storage.load(str(tmp_path / "frame_000005.png"))
        assert len(boxes) == 1
        assert boxes[0].class_name == "bike"
        assert boxes[0].confidence == pytest.approx(0.85, rel=1e-4)


class TestFrameStorage:
    def _make(self, tmp_path):
        storage = FrameStorage.__new__(FrameStorage)
        storage.video_name = "vid"
        storage.base_dir   = str(tmp_path / "vid")
        os.makedirs(storage.base_dir, exist_ok=True)
        return storage

    def test_save_and_load(self, tmp_path):
        fs    = self._make(tmp_path)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[50, 50] = [0, 255, 0]
        path  = fs.save(0, frame)
        assert os.path.exists(path)
        loaded = fs.load(0)
        assert loaded is not None
        assert loaded.shape == (100, 100, 3)

    def test_load_missing_returns_none(self, tmp_path):
        fs = self._make(tmp_path)
        assert fs.load(999) is None

    def test_exists(self, tmp_path):
        fs    = self._make(tmp_path)
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        assert not fs.exists(0)
        fs.save(0, frame)
        assert fs.exists(0)

    def test_list_saved_indices(self, tmp_path):
        fs    = self._make(tmp_path)
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        for i in [3, 7, 1]:
            fs.save(i, frame)
        assert fs.list_saved_indices() == [1, 3, 7]

    def test_frame_path_format(self, tmp_path):
        fs   = self._make(tmp_path)
        path = fs._frame_path(42)
        assert path.endswith("frame_000042.png")
