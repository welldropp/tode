"""
core/detectors/rtdetr_detector.py
──────────────────────────────────
Detection backend powered by **RT-DETR** (Real-Time DEtection TRansformer)
from HuggingFace `transformers`, with **supervision** for post-processing.

  Model      : RT-DETR / RT-DETRv2  (Apache-2.0)   — via transformers
  Post-proc  : supervision.Detections (+ NMS)      — via supervision

Weights are pulled from the HuggingFace Hub on first use and cached; no local
weight files are needed. Heavy deps (torch / transformers / supervision) are
imported lazily inside the methods so importing this module stays cheap.
"""
from __future__ import annotations

import cv2

from core.base_detector import BaseDetector
from models.annotation_model import BoundingBox
from utils.logger import get_logger

log = get_logger("core.detectors.RTDetrDetector")


class RTDetrDetector(BaseDetector):
    """RT-DETR object detector. Accepts a HuggingFace model id."""

    def __init__(self, confidence: float = 0.45, iou: float = 0.45):
        self.confidence = confidence
        self.iou        = iou
        self._model      = None
        self._processor  = None
        self._device     = "cpu"
        self._model_id: str = ""
        self._id2label: dict[int, str] = {}

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def load(self, model_path: str) -> None:
        """`model_path` is a HuggingFace model id (e.g. 'PekingU/rtdetr_r50vd')."""
        if self._model is not None and self._model_id == model_path:
            return
        self._load_model(model_path)

    def _load_model(self, model_id: str) -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ImportError(
                "RT-DETR backend requires 'torch' and 'transformers'. "
                "Install them with:  pip install torch transformers"
            ) from exc

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        log.info(f"[RT-DETR] loading '{model_id}' on {self._device}…")
        try:
            self._processor = AutoImageProcessor.from_pretrained(model_id)
            self._model = (
                AutoModelForObjectDetection.from_pretrained(model_id)
                .to(self._device)
                .eval()
            )
            self._model_id = model_id
            self._id2label = {int(k): v for k, v in self._model.config.id2label.items()}
            log.info(f"[RT-DETR] ready — {len(self._id2label)} classes")
        except Exception as exc:
            log.error(f"[RT-DETR] load failed: {exc}", exc_info=True)
            raise

    def is_loaded(self) -> bool:
        return self._model is not None

    # ── inference ─────────────────────────────────────────────────────────────
    def detect(self, bgr_frame) -> list[BoundingBox]:
        if not self.is_loaded() or bgr_frame is None:
            return []
        return self.detect_batch([bgr_frame])[0]

    def detect_batch(self, bgr_frames: list) -> list[list[BoundingBox]]:
        """Batched RT-DETR inference. Returns a per-frame BoundingBox list."""
        if not self.is_loaded():
            return [[] for _ in bgr_frames]

        import torch

        # Keep track of which inputs are real frames (skip None).
        rgb_images: list = []
        sizes:      list = []          # (h, w) per valid frame
        valid_idx:  list = []
        for i, f in enumerate(bgr_frames):
            if f is None:
                continue
            rgb_images.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
            sizes.append((f.shape[0], f.shape[1]))
            valid_idx.append(i)

        results_out: list[list[BoundingBox]] = [[] for _ in bgr_frames]
        if not rgb_images:
            return results_out

        inputs = self._processor(images=rgb_images, return_tensors="pt").to(self._device)
        with torch.no_grad():
            outputs = self._model(**inputs)

        target_sizes = torch.tensor(sizes, device=self._device)
        post = self._processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=self.confidence,
        )

        for rel_i, res in enumerate(post):
            h, w = sizes[rel_i]
            results_out[valid_idx[rel_i]] = self._to_boxes(res, w, h)
        return results_out

    # ── helpers ───────────────────────────────────────────────────────────────
    def _to_boxes(self, result: dict, img_w: int, img_h: int) -> list[BoundingBox]:
        """Convert a transformers detection result → normalized BoundingBox list,
        routing through a supervision Detections object for optional NMS."""
        import numpy as np
        import supervision as sv

        boxes  = result["boxes"].detach().cpu().numpy()
        scores = result["scores"].detach().cpu().numpy()
        labels = result["labels"].detach().cpu().numpy().astype(int)
        if boxes.shape[0] == 0:
            return []

        detections = sv.Detections(
            xyxy=boxes.astype(np.float32),
            confidence=scores.astype(np.float32),
            class_id=labels,
        )
        # supervision class-aware NMS to drop overlapping duplicates
        if len(detections) > 1:
            detections = detections.with_nms(threshold=self.iou, class_agnostic=False)

        out: list[BoundingBox] = []
        for (x1, y1, x2, y2), conf, cls_id in zip(
            detections.xyxy, detections.confidence, detections.class_id, strict=False,
        ):
            cid = int(cls_id)
            out.append(BoundingBox(
                class_id   = cid,
                class_name = self._id2label.get(cid, str(cid)),
                x_center   = ((x1 + x2) / 2) / img_w,
                y_center   = ((y1 + y2) / 2) / img_h,
                width      = (x2 - x1)       / img_w,
                height     = (y2 - y1)       / img_h,
                confidence = float(conf),
            ))
        return out

    # ── metadata ──────────────────────────────────────────────────────────────
    @property
    def class_names(self) -> dict[int, str]:
        return self._id2label

    @property
    def backend_name(self) -> str:
        return "RT-DETR"
