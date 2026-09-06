"""Tests for utils.image_utils — hex_to_bgr, resize_frame, draw_boxes."""
import numpy as np

from models.annotation_model import BoundingBox
from utils.image_utils import draw_boxes, hex_to_bgr, resize_frame


class TestHexToBgr:
    def test_white(self):
        assert hex_to_bgr("#ffffff") == (255, 255, 255)

    def test_black(self):
        assert hex_to_bgr("#000000") == (0, 0, 0)

    def test_pure_red(self):
        # HTML red #ff0000 → R=255, G=0, B=0 → BGR=(0, 0, 255)
        assert hex_to_bgr("#ff0000") == (0, 0, 255)

    def test_pure_green(self):
        assert hex_to_bgr("#00ff00") == (0, 255, 0)

    def test_pure_blue(self):
        assert hex_to_bgr("#0000ff") == (255, 0, 0)

    def test_without_hash(self):
        assert hex_to_bgr("00ff88") == hex_to_bgr("#00ff88")


class TestResizeFrame:
    def test_output_dimensions(self):
        frame   = np.zeros((1080, 1920, 3), dtype=np.uint8)
        resized = resize_frame(frame, 640, 480)
        assert resized.shape == (480, 640, 3)

    def test_square_input_no_distortion(self):
        frame   = np.full((200, 200, 3), 128, dtype=np.uint8)
        resized = resize_frame(frame, 100, 100)
        assert resized.shape == (100, 100, 3)

    def test_letterbox_preserves_aspect_ratio(self):
        # 200×100 frame (2:1) into 100×100 canvas
        # Scale = min(100/200, 100/100) = 0.5 → new size 100×50
        # Vertical padding: (100-50)//2 = 25 top and bottom
        frame = np.full((100, 200, 3), 200, dtype=np.uint8)
        out   = resize_frame(frame, 100, 100)
        assert np.all(out[:25, :] == 0)
        assert out[50, 50, 0] > 0

    def test_returns_copy_not_original(self):
        frame   = np.zeros((100, 100, 3), dtype=np.uint8)
        resized = resize_frame(frame, 100, 100)
        frame[0, 0] = [255, 0, 0]
        assert resized[0, 0, 0] == 0


class TestDrawBoxes:
    def _box(self):
        return BoundingBox(0, "car", 0.5, 0.5, 0.4, 0.4, 0.9)

    def test_returns_copy_not_original(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out   = draw_boxes(frame, [self._box()])
        assert not np.array_equal(frame, out)

    def test_original_unchanged(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        draw_boxes(frame, [self._box()])
        assert np.all(frame == 0)

    def test_no_boxes_returns_identical(self):
        frame = np.full((100, 100, 3), 42, dtype=np.uint8)
        out   = draw_boxes(frame, [])
        assert np.array_equal(frame, out)

    def test_box_drawn_modifies_pixels(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out   = draw_boxes(frame, [self._box()], color="#00ff00")
        assert out.sum() > 0

    def test_multiple_boxes(self):
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        boxes = [
            BoundingBox(0, "a", 0.25, 0.25, 0.2, 0.2, 0.9),
            BoundingBox(1, "b", 0.75, 0.75, 0.2, 0.2, 0.8),
        ]
        out = draw_boxes(frame, boxes)
        assert out.sum() > 0
