"""
ui/qt_workers.py
─────────────────
Background QThread workers so the Qt event loop never blocks on slow work
(frame extraction, model download, inference). Each worker maps directly onto
the headless core (AnnotationManager / AutoAnnotator).
"""
from __future__ import annotations

import os

from PyQt6.QtCore import QThread, pyqtSignal

from core.annotation_manager import AnnotationManager
from core.auto_annotator import AutoAnnotator
from core.frame_extractor import FrameExtractor
from core.image_frame_extractor import ImageFrameExtractor
from core.image_loader import ImageLoader
from core.video_loader import VideoLoader
from storage.frame_storage import FrameStorage
from storage.label_storage import LabelStorage
from utils.logger import get_logger

log = get_logger("ui.qt_workers")


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name) or "images"


class LoadWorker(QThread):
    """Builds an AnnotationManager for a video / image / folder source."""

    progress = pyqtSignal(int, int)     # done, total
    done     = pyqtSignal(object)       # AnnotationManager
    error    = pyqtSignal(str)

    def __init__(self, source_type: str, path: str, step: int = 1):
        super().__init__()
        self.source_type = source_type
        self.path = path
        self.step = max(1, step)

    def run(self):
        try:
            if self.source_type == "video":
                loader = VideoLoader(self.path)
                loader.open()
                extractor = FrameExtractor(loader, step=self.step, save_frames=True)
                name = os.path.splitext(os.path.basename(self.path))[0]
            else:  # "image" or "image_folder"
                loader = ImageLoader(self.path)
                loader.open()
                extractor = ImageFrameExtractor(loader, copy_files=True)
                base = os.path.basename(self.path.rstrip("/\\")) or "images"
                name = _sanitize(base)

            detector = AutoAnnotator()
            mgr = AnnotationManager(
                loader, extractor, detector,
                FrameStorage(name), LabelStorage(name),
            )
            mgr.load_video(on_progress=lambda d, t: self.progress.emit(d, t))
            mgr.load_existing_labels()
            self.done.emit(mgr)
        except Exception as exc:               # noqa: BLE001 - surfaced to UI
            log.error(f"Load failed: {exc}", exc_info=True)
            self.error.emit(str(exc))


class DetectWorker(QThread):
    """Runs RT-DETR on a single frame or on every frame."""

    progress = pyqtSignal(int, int)
    done     = pyqtSignal(object)       # frame index (single) or count (all)
    error    = pyqtSignal(str)

    def __init__(self, manager: AnnotationManager, index: int | None, conf: float):
        super().__init__()
        self.manager = manager
        self.index = index              # None → all frames
        self.conf = conf

    def run(self):
        try:
            self.manager.detector.confidence = self.conf
            if self.index is None:
                self.manager.auto_annotate_all(
                    progress_callback=lambda d, t: self.progress.emit(d, t)
                )
                self.done.emit(self.manager.annotated_count)
            else:
                self.manager.auto_annotate_frame(self.index)
                self.done.emit(self.index)
        except Exception as exc:               # noqa: BLE001 - surfaced to UI
            log.error(f"Detection failed: {exc}", exc_info=True)
            self.error.emit(str(exc))
