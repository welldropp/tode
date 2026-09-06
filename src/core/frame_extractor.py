"""Extracts frames from a video at a configurable step."""
import os
from collections.abc import Generator

import cv2

from core.video_loader import VideoLoader
from utils.config import DEFAULT_FPS_STEP, FRAMES_DIR
from utils.logger import get_logger

log = get_logger("core.FrameExtractor")

_JPEG_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, 92]


class FrameExtractor:
    def __init__(
        self,
        video_loader: VideoLoader,
        step: int        = DEFAULT_FPS_STEP,
        save_frames: bool= True,
    ):
        self.loader      = video_loader
        self.step        = max(1, step)
        self.save_frames = save_frames

        video_name       = os.path.splitext(
            os.path.basename(video_loader.video_path)
        )[0]
        self.output_dir  = os.path.join(FRAMES_DIR, video_name)
        os.makedirs(self.output_dir, exist_ok=True)

        log.info(
            f"FrameExtractor — step={self.step}, "
            f"save={self.save_frames}, dir={self.output_dir}"
        )

    def extract(self) -> Generator[tuple[int, object, str], None, None]:
        """
        Sequential extraction — does NOT seek per frame, which avoids the
        H.264 "mmco: unref short failure" silent-drop pattern caused by
        random seeks into bitstreams with B-frames or bad DTS/PTS.
        Dropped frames (decode errors) are counted and reported.
        """
        total    = self.estimated_frame_count
        extracted = 0
        dropped   = 0
        log.info(f"Starting extraction — ~{total} frames expected")

        self.loader.seek(0)
        for raw_idx in range(self.loader.total_frames):
            idx, frame = self.loader.read_next_frame()
            if frame is None:
                dropped += 1
                log.warning(f"Skipped frame ~{raw_idx} — decode failed (codec bitstream error)")
                continue
            if (idx if idx is not None else raw_idx) % self.step != 0:
                continue
            frame_idx = idx if idx is not None else raw_idx
            saved_path = self._save(frame_idx, frame) if self.save_frames else ""
            extracted += 1
            if extracted % 100 == 0:
                log.debug(f"Extracted {extracted}/{total} frames…")
            yield frame_idx, frame, saved_path

        if dropped:
            log.warning(
                f"Extraction finished with {dropped} dropped frame(s) — "
                f"video bitstream had decode errors. {extracted} frames saved."
            )
        else:
            log.info(f"Extraction complete — {extracted} frames processed")

    def extract_single(self, frame_index: int) -> tuple[object, str]:
        log.debug(f"Extracting single frame {frame_index}")
        frame = self.loader.read_frame(frame_index)
        if frame is None:
            log.warning(f"Frame {frame_index} could not be read")
            return None, ""
        saved_path = self._save(frame_index, frame) if self.save_frames else ""
        return frame, saved_path

    def _save(self, frame_idx: int, frame) -> str:
        path = os.path.join(self.output_dir, f"frame_{frame_idx:06d}.jpg")
        cv2.imwrite(path, frame, _JPEG_PARAMS)
        log.debug(f"Saved frame {frame_idx} → {path}")
        return path

    def frame_path(self, frame_index: int) -> str:
        """Return expected path; prefer existing PNG for backward compat."""
        jpg = os.path.join(self.output_dir, f"frame_{frame_index:06d}.jpg")
        png = os.path.join(self.output_dir, f"frame_{frame_index:06d}.png")
        return png if (os.path.exists(png) and not os.path.exists(jpg)) else jpg

    @property
    def estimated_frame_count(self) -> int:
        return self.loader.total_frames // self.step
