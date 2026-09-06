"""Tests for extended storage modules."""

from storage.formats.csv_format import CSVFormat
from storage.formats.json_format import JSONFormat
from storage.formats.pascal_voc_format import PascalVOCFormat
from storage.formats.yolo_format import YOLOFormat
from storage.project_storage import ProjectStorage
from storage.session_storage import SessionStorage

# ── YOLOFormat ────────────────────────────────────────────────────────────────

def test_yolo_format_roundtrip(tmp_path):
    path = str(tmp_path / "label.txt")
    rows = [{"class_id": 0, "cx": 0.5, "cy": 0.5, "w": 0.2, "h": 0.3}]
    YOLOFormat.write(path, rows)
    loaded = YOLOFormat.read(path)
    assert len(loaded) == 1
    assert loaded[0]["class_id"] == 0


def test_yolo_format_missing_file(tmp_path):
    rows = YOLOFormat.read(str(tmp_path / "missing.txt"))
    assert rows == []


# ── JSONFormat ────────────────────────────────────────────────────────────────

def test_json_format_roundtrip(tmp_path):
    path = str(tmp_path / "data.json")
    data = {"key": [1, 2, 3]}
    JSONFormat.write(path, data)
    loaded = JSONFormat.read(path)
    assert loaded == data


def test_json_format_missing_file(tmp_path):
    result = JSONFormat.read(str(tmp_path / "missing.json"))
    assert result == {}


# ── CSVFormat ─────────────────────────────────────────────────────────────────

def test_csv_format_roundtrip(tmp_path):
    path = str(tmp_path / "anns.csv")
    rows = [{"filename": "f1", "class_id": "0", "class_name": "cat",
             "cx": "0.5", "cy": "0.5", "w": "0.2", "h": "0.2"}]
    CSVFormat.write(path, rows)
    loaded = CSVFormat.read(path)
    assert len(loaded) == 1
    assert loaded[0]["class_name"] == "cat"


# ── PascalVOCFormat ───────────────────────────────────────────────────────────

def test_pascal_voc_roundtrip(tmp_path):
    path = str(tmp_path / "ann.xml")
    rows = [{"name": "cat", "xmin": 10, "ymin": 20, "xmax": 100, "ymax": 200}]
    PascalVOCFormat.write(path, rows, img_w=640, img_h=480)
    loaded = PascalVOCFormat.read(path)
    assert len(loaded) == 1
    assert loaded[0]["name"] == "cat"


# ── SessionStorage ────────────────────────────────────────────────────────────

def test_session_storage_crud(tmp_path):
    store = SessionStorage(str(tmp_path / "sess.json"))
    store.set("key", "value")
    assert store.get("key") == "value"
    store.delete("key")
    assert store.get("key") is None


def test_session_storage_persist(tmp_path):
    path = str(tmp_path / "sess.json")
    SessionStorage(path).set("x", 42)
    assert SessionStorage(path).get("x") == 42


def test_session_storage_clear(tmp_path):
    store = SessionStorage(str(tmp_path / "sess.json"))
    store.set("a", 1)
    store.clear()
    assert store.all() == {}


# ── ProjectStorage ────────────────────────────────────────────────────────────

def test_project_storage_create_list(tmp_path):
    ps = ProjectStorage(str(tmp_path))
    ps.create_project("alpha")
    ps.save_meta("alpha", {"name": "alpha"})
    projects = ps.list_projects()
    assert "alpha" in projects


def test_project_storage_load_meta(tmp_path):
    ps = ProjectStorage(str(tmp_path))
    ps.create_project("beta")
    ps.save_meta("beta", {"class_names": ["cat"]})
    meta = ps.load_meta("beta")
    assert meta["class_names"] == ["cat"]


def test_project_storage_delete(tmp_path):
    ps = ProjectStorage(str(tmp_path))
    ps.create_project("gamma")
    ps.save_meta("gamma", {})
    assert ps.delete_project("gamma") is True
    assert "gamma" not in ps.list_projects()
