"""Tests for core/exporters."""
import csv
import json
import os
import xml.etree.ElementTree as ET

import pytest

from core.exporters.base import BaseExporter
from core.exporters.coco import COCOExporter
from core.exporters.csv_exporter import CSVExporter
from core.exporters.json_exporter import JSONExporter
from core.exporters.pascal_voc import PascalVOCExporter
from core.exporters.yolo import YOLOExporter


@pytest.fixture
def label_dir(tmp_path):
    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / "frame_001.txt").write_text("0 0.5 0.5 0.3 0.3\n1 0.2 0.2 0.1 0.1\n")
    (labels / "frame_002.txt").write_text("0 0.6 0.6 0.2 0.2\n")
    return str(labels)


@pytest.fixture
def exporter_args(tmp_path, label_dir):
    return {
        "labels_dir":  label_dir,
        "images_dir":  str(tmp_path / "images"),
        "class_names": ["cat", "dog"],
        "output_dir":  str(tmp_path / "export"),
    }


def test_yolo_exporter(exporter_args):
    exp   = YOLOExporter(**exporter_args)
    count = exp.export()
    assert count == 3
    out = exporter_args["output_dir"]
    assert os.path.isfile(os.path.join(out, "data.yaml"))
    assert os.path.isfile(os.path.join(out, "labels", "frame_001.txt"))


def test_coco_exporter(exporter_args):
    exp   = COCOExporter(**exporter_args)
    count = exp.export()
    assert count == 3
    out  = os.path.join(exporter_args["output_dir"], "annotations.json")
    data = json.loads(open(out).read())
    assert len(data["annotations"]) == 3
    assert len(data["categories"])  == 2


def test_csv_exporter(exporter_args):
    exp   = CSVExporter(**exporter_args)
    count = exp.export()
    assert count == 3
    csv_path = os.path.join(exporter_args["output_dir"], "annotations.csv")
    rows = list(csv.DictReader(open(csv_path)))
    assert len(rows) == 3


def test_json_exporter(exporter_args):
    exp   = JSONExporter(**exporter_args)
    count = exp.export()
    assert count == 3
    data = json.loads(open(os.path.join(exporter_args["output_dir"], "annotations.json")).read())
    assert "frame_001" in data["frames"]


def test_pascal_voc_exporter(exporter_args):
    exp   = PascalVOCExporter(**exporter_args)
    count = exp.export()
    assert count == 3
    xml_path = os.path.join(exporter_args["output_dir"], "Annotations", "frame_001.xml")
    tree = ET.parse(xml_path)
    assert len(tree.getroot().findall("object")) == 2


def test_base_exporter_is_abstract():
    with pytest.raises(TypeError):
        BaseExporter("a", "b", [], "c")  # type: ignore
