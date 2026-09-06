"""
models/
───────
Pure-data layer — dataclasses with zero I/O dependencies.
Safe to import anywhere without side-effects.

Public API:
    from models import BoundingBox, FrameAnnotation
"""

from models.annotation_model import BoundingBox, FrameAnnotation

__all__ = [
    "BoundingBox",
    "FrameAnnotation",
]
