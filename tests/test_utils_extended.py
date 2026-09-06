"""Tests for utility modules: validators, string_utils, date_utils, file_utils."""
import os

from utils.date_utils import format_elapsed, now_filename_safe, utcnow_iso
from utils.file_utils import ensure_dir, is_image, is_video, list_images, stem
from utils.string_utils import human_size, pluralise, slugify, truncate
from utils.validators import (
    is_valid_confidence,
    is_valid_directory,
    is_valid_file,
    is_valid_iou,
    validate_class_names,
)

# ── validators ────────────────────────────────────────────────────────────────

def test_valid_confidence():
    assert is_valid_confidence(0.45) is True
    assert is_valid_confidence(0.0)  is False
    assert is_valid_confidence(1.01) is False


def test_valid_iou():
    assert is_valid_iou(0.5) is True
    assert is_valid_iou(0.0) is False


def test_valid_directory(tmp_path):
    assert is_valid_directory(str(tmp_path)) is True
    assert is_valid_directory("/no/such/path") is False


def test_valid_file(tmp_path):
    f = tmp_path / "test.onnx"
    f.write_text("x")
    assert is_valid_file(str(f)) is True
    assert is_valid_file(str(f), (".onnx",)) is True
    assert is_valid_file(str(f), (".pt",))   is False


def test_validate_class_names():
    names = validate_class_names(["cat", "cat", " dog ", "", "cat"])
    assert names == ["cat", "dog"]


# ── string_utils ──────────────────────────────────────────────────────────────

def test_truncate():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 8) == "hello w…"


def test_slugify():
    assert slugify("Hello World!") == "hello_world"
    assert slugify("  ") == "untitled"


def test_human_size():
    assert human_size(500)       == "500.0 B"
    assert human_size(1024)      == "1.0 KB"
    assert human_size(1024**2)   == "1.0 MB"


def test_pluralise():
    assert pluralise(1, "item")  == "1 item"
    assert pluralise(2, "item")  == "2 items"
    assert pluralise(0, "frame") == "0 frames"


# ── date_utils ────────────────────────────────────────────────────────────────

def test_utcnow_iso():
    s = utcnow_iso()
    assert s.endswith("Z")
    assert "T" in s


def test_now_filename_safe():
    s = now_filename_safe()
    assert "_" in s
    assert len(s) == 15


def test_format_elapsed():
    assert format_elapsed(30)   == "30s"
    assert format_elapsed(90)   == "1m 30s"
    assert format_elapsed(3661) == "1h 01m 01s"


# ── file_utils ────────────────────────────────────────────────────────────────

def test_is_image():
    assert is_image("photo.jpg") is True
    assert is_image("clip.mp4")  is False


def test_is_video():
    assert is_video("clip.mp4")   is True
    assert is_video("photo.jpg")  is False


def test_list_images(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.png").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    imgs = list_images(str(tmp_path))
    assert len(imgs) == 2
    assert all(is_image(p) for p in imgs)


def test_ensure_dir(tmp_path):
    d = str(tmp_path / "new" / "dir")
    result = ensure_dir(d)
    assert result == d
    assert os.path.isdir(d)


def test_stem():
    assert stem("/path/to/frame_001.jpg") == "frame_001"
