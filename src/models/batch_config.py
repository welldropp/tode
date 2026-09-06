"""
models/batch_config.py
────────────────────────
Configuration model for a batch annotation run.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BatchConfig:
    """Settings for a batch auto-annotation job."""

    model_name:     str   = "yolo26x"
    confidence:     float = 0.45
    iou_threshold:  float = 0.45
    num_workers:    int   = 1
    skip_annotated: bool  = True
    save_interval:  int   = 10   # save every N frames

    def __post_init__(self) -> None:
        if not 0.0 < self.confidence <= 1.0:
            raise ValueError("confidence must be in (0, 1]")
        if not 0.0 < self.iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be in (0, 1]")
        if self.num_workers < 1:
            raise ValueError("num_workers must be >= 1")
