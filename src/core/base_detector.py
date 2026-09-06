"""
core/base_detector.py
─────────────────────
Detector abstraction — every backend implements this interface so the rest of
the app never imports a specific backend.

The active backend is RT-DETR (transformers + supervision). Keeping this ABC
means future backends (OpenVINO, TFLite, CoreML, …) drop in without UI changes.
"""
from abc import ABC, abstractmethod

from models.annotation_model import BoundingBox


class BaseDetector(ABC):
    """Shared interface for every detection backend."""

    confidence: float = 0.45
    iou:        float = 0.45

    # ── lifecycle ─────────────────────────────────────────────────────────────
    @abstractmethod
    def load(self, model_path: str) -> None:
        """Load weights from *model_path*.  Must be idempotent."""

    @abstractmethod
    def is_loaded(self) -> bool: ...

    # ── inference ─────────────────────────────────────────────────────────────
    @abstractmethod
    def detect(self, bgr_frame) -> list[BoundingBox]:
        """
        Run detection on a single BGR frame (numpy HWC uint8).
        Returns normalised BoundingBox list (x_center, y_center, w, h ∈ [0,1]).
        """

    def detect_batch(self, bgr_frames: list) -> list[list[BoundingBox]]:
        """
        Optional batch API. Default implementation falls back to calling
        `detect` for each frame which preserves backwards compatibility.
        Backends can override this for faster batched inference.
        """
        return [self.detect(f) for f in bgr_frames]

    # ── metadata ──────────────────────────────────────────────────────────────
    @property
    @abstractmethod
    def class_names(self) -> dict[int, str]:
        """Return {class_id: class_name} dict."""

    # ── helpers ───────────────────────────────────────────────────────────────
    @property
    def backend_name(self) -> str:
        return self.__class__.__name__
