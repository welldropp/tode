"""Utility functions for drawing and resizing."""

import logging
import os

import cv2
import numpy as np

from models.annotation_model import BoundingBox
from utils.config import BOX_COLOR, FRAMES_DIR

_log = logging.getLogger(__name__)


def _is_extracted_frame(path: str) -> bool:
    try:
        return os.path.commonpath([
            os.path.abspath(path),
            os.path.abspath(FRAMES_DIR),
        ]) == os.path.abspath(FRAMES_DIR)
    except ValueError:
        return False


def safe_imread(path: str) -> np.ndarray | None:
    """
    Read an image from disk, correctly handling:
      - Paths with spaces, Unicode, or non-ASCII characters (Windows & macOS)
      - EXIF orientation tags (iPhone/macOS camera photos stored sideways)

    For frames extracted by the app, use a fast cv2 read path first.
    For other image files, keep the PIL fallback to preserve EXIF rotation.
    """
    if _is_extracted_frame(path):
        frame = cv2.imread(path)
        if frame is not None:
            return frame

    try:
        from PIL import Image, ImageOps
        pil = Image.open(path)
        pil = ImageOps.exif_transpose(pil)   # apply EXIF rotation
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    except Exception as exc:  # nosec B110 — PIL unavailable or unsupported format; falling through to cv2 fallback
        _log.debug("PIL read failed for %s (%s), trying cv2 fallback", path, exc)

    try:
        buf = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception as exc:
        _log.warning("safe_imread failed for %s: %s", path, exc)
        return None


def draw_boxes(bgr_frame, boxes: list[BoundingBox], color=BOX_COLOR) -> np.ndarray:
    """Return a copy of bgr_frame with all bounding boxes drawn."""
    frame = bgr_frame.copy()
    h, w  = frame.shape[:2]
    bgr   = hex_to_bgr(color)
    for box in boxes:
        x1, y1, x2, y2 = box.to_pixel_coords(w, h)
        cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 2)
        label = f"{box.class_name} {box.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), bgr, -1)
        cv2.putText(
            frame, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA,
        )
    return frame


def resize_frame(frame, width: int, height: int) -> np.ndarray:
    """Resize keeping aspect ratio, padding with black bars."""
    h, w = frame.shape[:2]
    scale = min(width / w, height / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas  = np.zeros((height, width, 3), dtype=np.uint8)
    y_off   = (height - nh) // 2
    x_off   = (width  - nw) // 2
    canvas[y_off:y_off+nh, x_off:x_off+nw] = resized
    return canvas


def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return b, g, r

