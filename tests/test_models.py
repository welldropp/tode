"""BoundingBox + FrameAnnotation."""
import pytest

from models.annotation_model import BoundingBox, FrameAnnotation


class TestBoundingBox:
    def _make(self, **kw):
        defaults = dict(
            class_id=0, class_name="car",
            x_center=0.5, y_center=0.5,
            width=0.4, height=0.3,
            confidence=0.9,
        )
        return BoundingBox(**{**defaults, **kw})

    def test_to_pixel_coords_center(self):
        box = self._make(x_center=0.5, y_center=0.5, width=0.4, height=0.2)
        x1, y1, x2, y2 = box.to_pixel_coords(100, 100)
        assert x1 == 30 and y1 == 40
        assert x2 == 70 and y2 == 60

    def test_to_pixel_coords_top_left(self):
        box = self._make(x_center=0.1, y_center=0.1, width=0.2, height=0.2)
        x1, y1, x2, y2 = box.to_pixel_coords(100, 100)
        assert x1 == 0 and y1 == 0
        assert x2 == 20 and y2 == 20

    def test_to_yolo_line_format(self):
        box = self._make(class_id=3, x_center=0.5, y_center=0.25, width=0.8, height=0.1)
        line = box.to_yolo_line()
        parts = line.strip().split()
        assert parts[0] == "3"
        assert float(parts[1]) == pytest.approx(0.5, rel=1e-4)
        assert float(parts[2]) == pytest.approx(0.25, rel=1e-4)
        assert float(parts[3]) == pytest.approx(0.8, rel=1e-4)
        assert float(parts[4]) == pytest.approx(0.1, rel=1e-4)

    def test_default_confidence_is_one(self):
        box = BoundingBox(0, "obj", 0.5, 0.5, 0.1, 0.1)
        assert box.confidence == 1.0

    def test_to_pixel_coords_rectangular_frame(self):
        box = self._make(x_center=0.5, y_center=0.5, width=1.0, height=1.0)
        x1, y1, x2, y2 = box.to_pixel_coords(1920, 1080)
        assert x1 == 0 and y1 == 0
        assert x2 == 1920 and y2 == 1080


class TestFrameAnnotation:
    def _box(self, name="car"):
        return BoundingBox(0, name, 0.5, 0.5, 0.2, 0.2, 0.9)

    def test_starts_not_annotated(self):
        ann = FrameAnnotation(0, "/tmp/frame.png")
        assert not ann.is_annotated
        assert ann.boxes == []

    def test_add_box_sets_annotated(self):
        ann = FrameAnnotation(0, "/tmp/frame.png")
        ann.add_box(self._box())
        assert ann.is_annotated
        assert len(ann.boxes) == 1

    def test_remove_box(self):
        ann = FrameAnnotation(0, "/tmp/frame.png")
        ann.add_box(self._box("cat"))
        ann.add_box(self._box("dog"))
        ann.remove_box(0)
        assert len(ann.boxes) == 1
        assert ann.boxes[0].class_name == "dog"

    def test_remove_last_box_clears_annotated(self):
        ann = FrameAnnotation(0, "/tmp/frame.png")
        ann.add_box(self._box())
        ann.remove_box(0)
        assert not ann.is_annotated

    def test_remove_out_of_range_is_safe(self):
        ann = FrameAnnotation(0, "/tmp/frame.png")
        ann.remove_box(99)  # must not raise

    def test_clear_boxes(self):
        ann = FrameAnnotation(0, "/tmp/frame.png")
        ann.add_box(self._box())
        ann.add_box(self._box())
        ann.clear_boxes()
        assert ann.boxes == []
        assert not ann.is_annotated
