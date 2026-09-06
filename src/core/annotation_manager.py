"""Orchestrates annotation lifecycle — with logging."""
import os
import threading
from collections.abc import Callable

import cv2

from core.auto_annotator import AutoAnnotator
from core.frame_extractor import FrameExtractor
from core.video_loader import VideoLoader
from models.annotation_model import (
    BoundingBox,
    FrameAnnotation,
    ImageClassification,
    PolygonAnnotation,
)
from storage.frame_storage import FrameStorage
from storage.label_storage import LabelStorage
from utils.image_utils import safe_imread
from utils.logger import get_logger

log = get_logger("core.AnnotationManager")


class AnnotationManager:
    def __init__(
        self,
        video_loader:    VideoLoader,
        frame_extractor: FrameExtractor,
        detector:        AutoAnnotator,
        frame_storage:   FrameStorage,
        label_storage:   LabelStorage,
    ):
        self.loader    = video_loader
        self.extractor = frame_extractor
        self.detector  = detector
        self.f_store   = frame_storage
        self.l_store   = label_storage
        self._annotations: dict[int, FrameAnnotation] = {}
        self._bg_thread: threading.Thread | None = None
        self._bg_progress = (0, 0)            # (done, total)
        log.info("AnnotationManager initialised")

    def load_video(self, on_progress: Callable | None = None):
        """
        Build the frame index instantly so the UI is responsive immediately.
        Frame PNG extraction runs in a daemon background thread; the cv2
        fallback in ``_read_frame_reliable`` covers any frame the worker
        hasn't reached yet (and writes it through opportunistically).
        """
        self._annotations.clear()

        loader = self.loader
        step   = max(1, getattr(self.extractor, "step", 1))
        total  = loader.total_frames

        # Pre-populate the expected on-disk path for each entry. The file
        # may not exist yet — _read_frame_reliable handles that — but
        # label loading uses the path to derive the frame index.
        for idx in range(0, total, step):
            expected_path = self.extractor.frame_path(idx)
            self._annotations[idx] = FrameAnnotation(
                frame_index=idx, frame_path=expected_path
            )
        log.info(
            f"Frame index built — {len(self._annotations)} entries; "
            f"extracting in background"
        )

        # Image folders don't have a video bitstream to decode and the
        # extractor's "extract" step is just a file copy — keep it
        # synchronous because it's already fast.
        if not isinstance(loader, VideoLoader):
            for idx, _frame, saved in self.extractor.extract():
                if (ann := self._annotations.get(idx)):
                    ann.frame_path = saved
            return

        self._bg_progress = (0, len(self._annotations))
        self._bg_thread = threading.Thread(
            target=self._background_extract,
            args=(on_progress,),
            name="annotation-extract",
            daemon=True,
        )
        self._bg_thread.start()

    def _background_extract(self, on_progress: Callable | None):
        """
        Sequential extraction against a SECOND VideoCapture so the UI
        thread's seeks don't disrupt our cursor (cv2's CAP_PROP_POS_FRAMES
        is one-cursor-per-capture). The output dir is shared with the
        primary extractor; both writers produce identical bytes for the
        same frame index so an overwrite race is benign.
        """
        try:
            bg_loader = VideoLoader(self.loader.video_path)
            bg_loader.open()
            bg_extractor = FrameExtractor(
                bg_loader,
                step        = max(1, getattr(self.extractor, "step", 1)),
                save_frames = True,
            )
            bg_extractor.output_dir = self.extractor.output_dir
            os.makedirs(bg_extractor.output_dir, exist_ok=True)

            done = 0
            total = self._bg_progress[1]
            for idx, _frame, saved_path in bg_extractor.extract():
                if (ann := self._annotations.get(idx)) and saved_path:
                    ann.frame_path = saved_path
                done += 1
                self._bg_progress = (done, total)
                if on_progress and (done % 20 == 0 or done == total):
                    on_progress(done, total)
            bg_loader.release()
            log.info(f"Background extraction complete — {done}/{total} frames")
            if on_progress:
                on_progress(done, total)
        except Exception as exc:
            log.error(f"Background extraction failed: {exc}", exc_info=True)

    @property
    def bg_progress(self):
        return self._bg_progress

    def get_annotation(self, frame_index: int) -> FrameAnnotation | None:
        return self._annotations.get(frame_index)

    def all_frame_indices(self) -> list[int]:
        return sorted(self._annotations.keys())

    def auto_annotate_frame(self, frame_index: int) -> FrameAnnotation:
        log.debug(f"Auto-annotating frame {frame_index}")
        ann = self._annotations.get(frame_index)
        if ann is None:
            frame, saved_path = self.extractor.extract_single(frame_index)
            ann = FrameAnnotation(frame_index=frame_index, frame_path=saved_path)
            self._annotations[frame_index] = ann
        else:
            frame = self._read_frame_reliable(ann, frame_index)

        ann.clear_boxes()
        if frame is None:
            log.warning(
                f"Frame {frame_index} could not be read — "
                "skipping YOLO inference"
            )
        else:
            boxes = self.detector.annotate_frame(frame)
            for box in boxes:
                ann.add_box(box)
        log.info(
            f"Frame {frame_index} auto-annotated — "
            f"{len(ann.boxes)} box(es)"
        )
        return ann

    def _read_frame_reliable(self, ann: FrameAnnotation, frame_index: int):
        """
        Prefer the saved frame on disk over re-seeking the source video.
        cv2.VideoCapture.set(CAP_PROP_POS_FRAMES, n) is unreliable for many
        codecs (H.264, B-frames, variable bitrate) and can return the wrong
        frame or None. The on-disk PNG is the source of truth.

        If the file doesn't exist yet (lazy / background-extracted videos),
        read from the video and cache the result to disk so the next read
        is reliable.
        """
        if ann.frame_path and os.path.exists(ann.frame_path):
            frame = safe_imread(ann.frame_path)
            if frame is not None:
                return frame
            log.debug(
                f"Saved frame on disk unreadable, falling back to video: "
                f"{ann.frame_path}"
            )

        # Backward compat: .jpg path set but only .png exists (old project)
        if ann.frame_path:
            root, ext = os.path.splitext(ann.frame_path)
            alt_ext = ".png" if ext.lower() == ".jpg" else ".jpg"
            alt_path = root + alt_ext
            if os.path.exists(alt_path):
                frame = safe_imread(alt_path)
                if frame is not None:
                    ann.frame_path = alt_path
                    return frame

        frame = self.loader.read_frame(frame_index)
        if frame is not None and ann.frame_path and not os.path.exists(ann.frame_path):
            try:
                os.makedirs(os.path.dirname(ann.frame_path), exist_ok=True)
                cv2.imwrite(ann.frame_path, frame)
            except OSError as exc:
                log.debug(f"Could not cache frame {frame_index}: {exc}")
        return frame

    def auto_annotate_all(self, progress_callback=None):
        indices = self.all_frame_indices()
        total = len(indices)
        log.info(f"Auto-annotating all {total} frames (batched)…")

        # Tune this for memory / speed tradeoff. Smaller batches use less RAM
        # but incur more Python overhead. 8 is a reasonable default.
        batch_size = 8
        for bstart in range(0, total, batch_size):
            batch_idx = indices[bstart:bstart + batch_size]
            frames = []
            for idx in batch_idx:
                ann = self._annotations.get(idx)
                if ann is None:
                    frame, saved_path = self.extractor.extract_single(idx)
                    if ann is None:
                        ann = FrameAnnotation(frame_index=idx, frame_path=saved_path)
                        self._annotations[idx] = ann
                    frames.append(frame)
                else:
                    frame = self._read_frame_reliable(ann, idx)
                    frames.append(frame)

            # Run batched YOLO; detector implementations may optimise this
            boxes_list = self.detector.annotate_frames(frames)

            # Apply detections back into annotations
            for rel_i, idx in enumerate(batch_idx):
                ann = self._annotations.get(idx)
                if ann is None:
                    ann = FrameAnnotation(frame_index=idx)
                    self._annotations[idx] = ann
                ann.clear_boxes()
                boxes = boxes_list[rel_i] if rel_i < len(boxes_list) else []
                for box in boxes:
                    ann.add_box(box)
                # Refresh annotated flag
                ann._refresh_annotated()

            # progress callback (converted to absolute)
            if progress_callback:
                progress_callback(min(bstart + batch_size, total), total)

        log.info(
            f"Bulk annotation complete — "
            f"{self.annotated_count}/{self.total_count} annotated"
        )

    def add_box(self, frame_index: int, box: BoundingBox):
        ann = self._annotations.get(frame_index)
        if ann:
            ann.add_box(box)
            log.info(
                f"Manual box added to frame {frame_index} — "
                f"class='{box.class_name}' "
                f"cx={box.x_center:.3f} cy={box.y_center:.3f}"
            )

    def remove_box(self, frame_index: int, box_index: int):
        ann = self._annotations.get(frame_index)
        if ann:
            removed = ann.boxes[box_index] if 0 <= box_index < len(ann.boxes) else None
            ann.remove_box(box_index)
            if removed:
                log.info(
                    f"Box [{box_index}] removed from frame {frame_index} "
                    f"— was '{removed.class_name}'"
                )

    def clear_frame(self, frame_index: int):
        ann = self._annotations.get(frame_index)
        if ann:
            n = len(ann.boxes)
            ann.clear_boxes()
            log.info(f"Cleared {n} box(es) from frame {frame_index}")

    def save_annotations(self):
        saved = 0
        for ann in self._annotations.values():
            if ann.is_annotated:
                label_path     = self.l_store.save(ann)
                ann.label_path = label_path
                saved         += 1
                log.debug(f"Saved frame {ann.frame_index} → {label_path}")
        log.info(f"Save complete — {saved} label file(s) written")

    def load_existing_labels(self):
        annotated = self.l_store.annotated_frame_indices()
        loaded = 0
        for ann in self._annotations.values():
            if ann.frame_index not in annotated:
                continue
            boxes   = self.l_store.load(ann.frame_path)
            polys   = self.l_store.load_polygons(ann.frame_path)
            classes = self.l_store.load_classifications(ann.frame_path)
            if boxes:
                ann.boxes = boxes
            if polys:
                ann.polygons = polys
            if classes:
                ann.classifications = classes
            if boxes or polys or classes:
                ann._refresh_annotated()
                loaded += 1
        log.info(f"Loaded existing labels for {loaded} frame(s)")

    # ── polygon operations ────────────────────────────────────────────────────

    def add_polygon(self, frame_index: int, poly: PolygonAnnotation) -> None:
        ann = self._annotations.get(frame_index)
        if ann:
            ann.add_polygon(poly)
            log.info(
                f"Polygon added to frame {frame_index} — "
                f"class='{poly.class_name}' pts={len(poly.points)}"
            )

    def remove_polygon(self, frame_index: int, poly_index: int) -> None:
        ann = self._annotations.get(frame_index)
        if ann:
            ann.remove_polygon(poly_index)
            log.info(f"Polygon [{poly_index}] removed from frame {frame_index}")

    def clear_polygons(self, frame_index: int) -> None:
        ann = self._annotations.get(frame_index)
        if ann:
            n = len(ann.polygons)
            ann.clear_polygons()
            log.info(f"Cleared {n} polygon(s) from frame {frame_index}")

    # ── classification operations ─────────────────────────────────────────────

    def set_classification(self, frame_index: int, cls: ImageClassification) -> None:
        ann = self._annotations.get(frame_index)
        if ann:
            ann.set_classification(cls)
            log.info(
                f"Classification set on frame {frame_index} — "
                f"class='{cls.class_name}'"
            )

    def clear_classifications(self, frame_index: int) -> None:
        ann = self._annotations.get(frame_index)
        if ann:
            ann.clear_classifications()
            log.info(f"Classifications cleared from frame {frame_index}")

    @property
    def annotated_count(self) -> int:
        return sum(1 for a in self._annotations.values() if a.is_annotated)

    @property
    def total_count(self) -> int:
        return len(self._annotations)
