"""Sanity checks for utils.config defaults."""
import os

from utils.config import (
    ACCENT,
    BG_DARK,
    BG_PANEL,
    DETECT_CONFIDENCE,
    DETECT_IOU,
    FRAMES_DIR,
    LABEL_FORMAT,
    LABELS_DIR,
    OUTPUT_DIR,
    RTDETR_DEFAULT_MODEL,
    RTDETR_MODELS,
    WEIGHTS_DIR,
)


class TestConfig:
    def test_directories_exist(self):
        for d in (OUTPUT_DIR, FRAMES_DIR, LABELS_DIR, WEIGHTS_DIR):
            assert os.path.isdir(d), f"Expected directory: {d}"

    def test_rtdetr_models_is_list(self):
        assert isinstance(RTDETR_MODELS, list)
        assert len(RTDETR_MODELS) >= 1

    def test_default_model_in_catalogue(self):
        assert RTDETR_DEFAULT_MODEL in RTDETR_MODELS

    def test_inference_defaults_in_range(self):
        assert 0.0 < DETECT_CONFIDENCE < 1.0
        assert 0.0 < DETECT_IOU < 1.0

    def test_label_format_is_yolo(self):
        # YOLO is the on-disk dataset FORMAT (class cx cy w h), independent of
        # the detector — RT-DETR datasets export/train in this same format.
        assert LABEL_FORMAT == "yolo"

    def test_color_strings_are_hex(self):
        for color in (BG_DARK, BG_PANEL, ACCENT):
            assert color.startswith("#")
            assert len(color) == 7
