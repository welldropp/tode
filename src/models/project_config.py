"""
models/project_config.py
──────────────────────────
Project-level configuration (source, classes, model, paths).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field


@dataclass
class ProjectConfig:
    """All configurable parameters for a tode project."""

    name:           str
    source_path:    str         = ""
    class_names:    list[str]   = field(default_factory=list)
    model_name:     str         = "yolo26x"
    confidence:     float       = 0.45
    iou_threshold:  float       = 0.45
    label_format:   str         = "yolo"
    fps_step:       int         = 1
    auto_save:      bool        = False

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> ProjectConfig:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)
