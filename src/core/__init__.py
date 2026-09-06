"""
core/
────
Business-logic layer — video I/O, frame extraction,
RT-DETR detection, and annotation orchestration.

Public API (importable directly from `core`):
    from core import VideoLoader, FrameExtractor, AutoAnnotator, AnnotationManager
"""

from core.annotation_manager import AnnotationManager
from core.auto_annotator import AutoAnnotator
from core.frame_extractor import FrameExtractor
from core.video_loader import VideoLoader

__all__ = [
    "VideoLoader",
    "FrameExtractor",
    "AutoAnnotator",
    "AnnotationManager",
]
