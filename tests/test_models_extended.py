"""Tests for extended model classes."""
import pytest

from models.batch_config import BatchConfig
from models.class_definition import ClassDefinition
from models.export_config import ExportConfig
from models.project_config import ProjectConfig
from models.session import Session


def test_class_definition_valid():
    cd = ClassDefinition(name="cat", id=0)
    assert cd.name == "cat"
    assert cd.id   == 0
    assert cd.color.startswith("#")


def test_class_definition_invalid():
    with pytest.raises(ValueError):
        ClassDefinition(name="", id=0)
    with pytest.raises(ValueError):
        ClassDefinition(name="cat", id=-1)


def test_class_definition_roundtrip():
    cd  = ClassDefinition(name="dog", id=1, color="#ff0000")
    cd2 = ClassDefinition.from_dict(cd.to_dict())
    assert cd2.name  == cd.name
    assert cd2.id    == cd.id
    assert cd2.color == cd.color


def test_export_config_valid():
    cfg = ExportConfig(output_dir="/tmp/export", format="YOLO TXT")
    assert cfg.val_ratio() == pytest.approx(0.2)


def test_export_config_invalid():
    with pytest.raises(ValueError):
        ExportConfig(output_dir="", format="YOLO TXT")
    with pytest.raises(ValueError):
        ExportConfig(output_dir="/tmp", train_ratio=0.0)


def test_session_save_load(tmp_path):
    path = str(tmp_path / "session.json")
    s    = Session(source_path="/data/video.mp4", class_names=["cat"], total_frames=100)
    s.save(path)
    s2 = Session.load(path)
    assert s2.source_path == "/data/video.mp4"
    assert s2.class_names == ["cat"]


def test_project_config_roundtrip(tmp_path):
    path = str(tmp_path / "project.json")
    cfg  = ProjectConfig(name="test", class_names=["a", "b"], confidence=0.6)
    cfg.save(path)
    cfg2 = ProjectConfig.load(path)
    assert cfg2.name        == "test"
    assert cfg2.confidence  == pytest.approx(0.6)
    assert cfg2.class_names == ["a", "b"]


def test_batch_config_defaults():
    cfg = BatchConfig()
    assert cfg.confidence    == pytest.approx(0.45)
    assert cfg.num_workers   == 1
    assert cfg.skip_annotated is True


def test_batch_config_invalid():
    with pytest.raises(ValueError):
        BatchConfig(confidence=0.0)
    with pytest.raises(ValueError):
        BatchConfig(num_workers=0)
