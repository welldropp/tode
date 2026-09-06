"""
storage/
────────
Persistence layer — reads and writes frames (PNG) and
labels (YOLO .txt or JSON) to the local filesystem.

Public API:
    from storage import FrameStorage, LabelStorage
"""

from storage.frame_storage import FrameStorage
from storage.label_storage import LabelStorage

__all__ = [
    "FrameStorage",
    "LabelStorage",
]
