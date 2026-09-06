"""
core/image_frame_extractor.py
──────────────────────────────
Drop-in replacement for FrameExtractor when source is ImageLoader.
Copies source images into the output frames folder.
"""
import os
import shutil
from collections.abc import Generator

import cv2
import numpy as np

from core.image_loader import ImageLoader
from utils.config import FRAMES_DIR
from utils.logger import get_logger

log = get_logger("core.ImageFrameExtractor")


class ImageFrameExtractor:
    """
    Same generator contract as FrameExtractor:
        yields (frame_index, bgr_ndarray, saved_path)
    """

    def __init__(self, image_loader: ImageLoader, copy_files: bool = True):
        self.loader     = image_loader
        self.copy_files = copy_files

        raw_name        = os.path.basename(
            image_loader.source_path.rstrip("/\\")
        )
        # sanitise for use as directory name
        safe_name       = "".join(
            c if c.isalnum() or c in "-_." else "_"
            for c in raw_name
        )
        self.output_dir = os.path.join(FRAMES_DIR, safe_name)
        os.makedirs(self.output_dir, exist_ok=True)

        log.info(
            f"ImageFrameExtractor — {image_loader.total_frames} image(s), "
            f"output dir: {self.output_dir}"
        )

    # ── main iterator ─────────────────────────────────────────────────────────
    def extract(self) -> Generator[tuple[int, np.ndarray, str], None, None]:
        total     = self.loader.total_frames
        extracted = 0
        log.info(f"Starting image extraction — {total} image(s)")

        for idx in range(total):
            src_path = self.loader.get_image_path(idx)
            if not src_path:
                log.warning(f"Skipping index {idx} — no image path")
                continue

            saved_path = (
                self._copy_to_output(idx)
                if self.copy_files
                else src_path
            )
            extracted += 1

            if extracted % 50 == 0:
                log.debug(f"Processed {extracted}/{total} images")

            yield idx, None, saved_path

        log.info(f"Image extraction complete — {extracted}/{total} succeeded")

    # ── single frame ──────────────────────────────────────────────────────────
    def extract_single(self, idx: int) -> tuple[np.ndarray | None, str]:
        frame = self.loader.read_frame(idx)
        if frame is None:
            return None, ""
        saved_path = (
            self._copy_to_output(idx)
            if self.copy_files
            else self.loader.get_image_path(idx)
        )
        return frame, saved_path

    # ── helpers ───────────────────────────────────────────────────────────────
    def _copy_to_output(self, idx: int) -> str:
        src = self.loader.get_image_path(idx)
        if not src:
            return ""
        ext = os.path.splitext(src)[1].lower() or ".png"
        dst = os.path.join(self.output_dir, f"frame_{idx:06d}{ext}")
        if not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                log.debug(f"Copied frame {idx}: {src} → {dst}")
            except Exception as e:
                log.warning(f"Copy failed for frame {idx}: {e}")
                # Fall back: write via OpenCV
                frame = self.loader.read_frame(idx)
                if frame is not None:
                    cv2.imwrite(dst, frame)
        return dst

    def frame_path(self, idx: int) -> str:
        src = self.loader.get_image_path(idx)
        ext = os.path.splitext(src)[1].lower() if src else ".png"
        return os.path.join(self.output_dir, f"frame_{idx:06d}{ext}")

    @property
    def estimated_frame_count(self) -> int:
        return self.loader.total_frames
