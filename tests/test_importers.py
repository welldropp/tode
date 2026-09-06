"""Tests for core/importers."""
import csv
import json
import os

import pytest

from core.importers.base import BaseImporter
from core.importers.csv_importer import CSVImporter
from core.importers.json_importer import JSONImporter
from core.importers.yolo import YOLOImporter


@pytest.fixture
def out_dir(tmp_path):
    return str(tmp_path / "out_labels")


def test_yolo_importer(tmp_path, out_dir):
    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / "img1.txt").write_text("0 0.5 0.5 0.2 0.2\n")
    importer = YOLOImporter(str(tmp_path), out_dir)
    names, count = importer.load()
    assert count == 1
    assert os.path.isfile(os.path.join(out_dir, "img1.txt"))


def test_yolo_importer_with_yaml(tmp_path, out_dir):
    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / "img1.txt").write_text("0 0.5 0.5 0.2 0.2\n")
    (tmp_path / "data.yaml").write_text("names:\n- cat\n- dog\n")
    importer = YOLOImporter(str(tmp_path), out_dir)
    names, count = importer.load()
    assert "cat" in names


def test_json_importer(tmp_path, out_dir):
    data = {
        "class_names": ["car", "person"],
        "frames": {
            "frame_01": [{"class_id": 0, "cx": 0.5, "cy": 0.5, "w": 0.3, "h": 0.3}],
        },
    }
    json_path = str(tmp_path / "annotations.json")
    with open(json_path, "w") as fh:
        json.dump(data, fh)
    importer = JSONImporter(str(tmp_path), out_dir, json_path=json_path)
    names, count = importer.load()
    assert count == 1
    assert names == ["car", "person"]
    assert os.path.isfile(os.path.join(out_dir, "frame_01.txt"))


def test_csv_importer(tmp_path, out_dir):
    csv_path = tmp_path / "annotations.csv"
    with open(str(csv_path), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["filename", "class_id", "class_name", "cx", "cy", "w", "h"])
        writer.writeheader()
        writer.writerow({"filename": "frame_01", "class_id": 0, "class_name": "cat",
                         "cx": 0.5, "cy": 0.5, "w": 0.3, "h": 0.3})
    importer = CSVImporter(str(tmp_path), out_dir)
    names, count = importer.load()
    assert count == 1
    assert "cat" in names


def test_base_importer_is_abstract():
    with pytest.raises(TypeError):
        BaseImporter("a", "b")  # type: ignore
