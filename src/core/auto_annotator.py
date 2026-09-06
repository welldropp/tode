"""
core/auto_annotator.py
───────────────────────
Public-facing detector facade. All other modules use:

    from core.auto_annotator import AutoAnnotator

The backend is RT-DETR (transformers + supervision). The facade is thread-safe
for model load/reload and exposes .load(), .reload(), .annotate_frame(),
.annotate_frames(), .class_names, .confidence, and .iou.
"""
import threading

from core.base_detector import BaseDetector
from core.detectors.rtdetr_detector import RTDetrDetector
from models.annotation_model import BoundingBox
from utils.config import DETECT_CONFIDENCE, DETECT_IOU, RTDETR_DEFAULT_MODEL
from utils.logger import get_logger

log = get_logger("core.AutoAnnotator")


class AutoAnnotator:
    """Thread-safe RT-DETR detector facade."""

    def __init__(
        self,
        model_id:   str   = RTDETR_DEFAULT_MODEL,
        confidence: float = DETECT_CONFIDENCE,
        iou:        float = DETECT_IOU,
    ):
        self._model_id   = model_id
        self._confidence = confidence
        self._iou        = iou
        self._detector: BaseDetector = RTDetrDetector(confidence=confidence, iou=iou)
        self._lock = threading.Lock()
        log.debug(f"AutoAnnotator created — conf={confidence}, iou={iou}, model={model_id}")

    # ── confidence / iou pass-through ─────────────────────────────────────────
    @property
    def confidence(self) -> float:
        return self._confidence

    @confidence.setter
    def confidence(self, val: float):
        self._confidence = val
        self._detector.confidence = val

    @property
    def iou(self) -> float:
        return self._iou

    @iou.setter
    def iou(self, val: float):
        self._iou = val
        self._detector.iou = val

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def load(self):
        with self._lock:
            if self._detector.is_loaded():
                return
            self._detector.load(self._model_id)

    def reload(self, model_id: str):
        """Swap the RT-DETR model at runtime (HuggingFace model id)."""
        with self._lock:
            self._detector.confidence = self._confidence
            self._detector.iou        = self._iou
            self._model_id = model_id
        self._detector.load(model_id)
        log.info(f"Model reloaded — {model_id}  backend={self._detector.backend_name}")

    def is_loaded(self) -> bool:
        return self._detector.is_loaded()

    # ── inference ─────────────────────────────────────────────────────────────
    def annotate_frame(self, bgr_frame) -> list[BoundingBox]:
        self.load()
        log.debug(
            f"Running detection — conf={self._confidence}, iou={self._iou}, "
            f"backend={self._detector.backend_name}"
        )
        boxes = self._detector.detect(bgr_frame)
        log.info(f"Detection complete — {len(boxes)} object(s)  [{self._detector.backend_name}]")
        return boxes

    def annotate_frames(self, bgr_frames: list) -> list[list[BoundingBox]]:
        """Batch annotation API — delegates to the backend's batched inference."""
        self.load()
        log.debug(
            f"Running batched detection — {len(bgr_frames)} frames, "
            f"conf={self._confidence}, iou={self._iou}, backend={self._detector.backend_name}"
        )
        try:
            boxes_list = self._detector.detect_batch(bgr_frames)
        except Exception:
            boxes_list = [self._detector.detect(f) if f is not None else [] for f in bgr_frames]
        total = sum(len(b) for b in boxes_list)
        log.info(f"Batched detection complete — {total} object(s)  [{self._detector.backend_name}]")
        return boxes_list

    # ── metadata ──────────────────────────────────────────────────────────────
    @property
    def class_names(self) -> dict[int, str]:
        return self._detector.class_names

    @property
    def model_path(self) -> str:
        return self._model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def backend_name(self) -> str:
        return self._detector.backend_name
