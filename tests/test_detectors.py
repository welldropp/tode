"""AutoAnnotator facade + RTDetrDetector routing (torch-free).

These tests exercise the facade wiring and the batch fallback path with a stub
backend, so they run in headless CI without torch/transformers/supervision.
Real RT-DETR inference is covered separately and skipped when torch is absent.
"""
import numpy as np

from core.auto_annotator import AutoAnnotator
from core.base_detector import BaseDetector
from core.detectors.rtdetr_detector import RTDetrDetector
from models.annotation_model import BoundingBox


class _StubDetector(BaseDetector):
    """Minimal in-memory detector for testing the facade without torch."""

    def __init__(self, confidence=0.45, iou=0.45):
        self.confidence = confidence
        self.iou = iou
        self._loaded = False
        self.batch_should_raise = False

    def load(self, model_path):
        self._loaded = True

    def is_loaded(self):
        return self._loaded

    def detect(self, bgr_frame):
        if bgr_frame is None:
            return []
        return [BoundingBox(0, "obj", 0.5, 0.5, 0.2, 0.2, 0.9)]

    def detect_batch(self, bgr_frames):
        if self.batch_should_raise:
            raise RuntimeError("batch failure")
        return [self.detect(f) for f in bgr_frames]

    @property
    def class_names(self):
        return {0: "obj"}

    @property
    def backend_name(self):
        return "Stub"


class TestRTDetrDetectorConstruction:
    def test_default_backend_is_rtdetr(self):
        ann = AutoAnnotator()
        assert isinstance(ann._detector, RTDetrDetector)
        assert ann.backend_name == "RT-DETR"

    def test_not_loaded_on_construction(self):
        # Lazy: constructing the detector must not load weights.
        assert AutoAnnotator().is_loaded() is False

    def test_confidence_iou_propagate_to_backend(self):
        ann = AutoAnnotator(confidence=0.3, iou=0.6)
        ann.confidence = 0.7
        ann.iou = 0.5
        assert ann._detector.confidence == 0.7
        assert ann._detector.iou == 0.5

    def test_detect_returns_empty_without_load(self):
        # RTDetrDetector.detect returns [] when the model isn't loaded.
        assert RTDetrDetector().detect(np.zeros((10, 10, 3), np.uint8)) == []


class TestFacadeRouting:
    def _annotator_with_stub(self):
        ann = AutoAnnotator()
        ann._detector = _StubDetector()
        return ann

    def test_annotate_frame(self):
        ann = self._annotator_with_stub()
        boxes = ann.annotate_frame(np.zeros((20, 20, 3), np.uint8))
        assert len(boxes) == 1
        assert boxes[0].class_name == "obj"

    def test_annotate_frames_batch(self):
        ann = self._annotator_with_stub()
        frames = [np.zeros((20, 20, 3), np.uint8) for _ in range(3)]
        out = ann.annotate_frames(frames)
        assert len(out) == 3
        assert all(len(b) == 1 for b in out)

    def test_batch_falls_back_to_single(self):
        ann = self._annotator_with_stub()
        ann._detector.batch_should_raise = True
        frames = [np.zeros((20, 20, 3), np.uint8), None]
        out = ann.annotate_frames(frames)
        assert len(out) == 2
        assert len(out[0]) == 1   # real frame detected
        assert out[1] == []       # None frame → empty

    def test_class_names_proxy(self):
        assert self._annotator_with_stub().class_names == {0: "obj"}
