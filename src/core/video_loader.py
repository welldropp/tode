"""Responsible for opening a video file and exposing its metadata."""
import threading

import cv2

from utils.logger import get_logger

log = get_logger("core.VideoLoader")


class VideoLoader:
    def __init__(self, video_path: str):
        self.video_path    = video_path
        self._cap: cv2.VideoCapture | None = None
        self._lock         = threading.Lock()
        self.total_frames  = 0
        self.fps           = 0.0
        self.width         = 0
        self.height        = 0
        self.duration_sec  = 0.0
        log.debug(f"VideoLoader created for: {video_path}")

    def open(self) -> bool:
        log.info(f"Opening video: {self.video_path}")
        with self._lock:
            self._cap = cv2.VideoCapture(self.video_path)
            if not self._cap.isOpened():
                log.error(f"Failed to open video: {self.video_path}")
                raise OSError(f"Cannot open video: {self.video_path}")

            self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps          = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.width        = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height       = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.duration_sec = self.total_frames / self.fps

        log.info(
            f"Video opened — frames={self.total_frames}, "
            f"fps={self.fps:.1f}, "
            f"resolution={self.width}x{self.height}, "
            f"duration={self.duration_sec:.1f}s"
        )
        return True

    def release(self):
        with self._lock:
            if self._cap:
                self._cap.release()
                self._cap = None
                log.info(f"VideoLoader released: {self.video_path}")

    def is_open(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    def read_frame(self, frame_index: int):
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                log.error("read_frame() called but capture is not open.")
                raise RuntimeError("VideoLoader is not open.")
            if not (0 <= frame_index < self.total_frames):
                log.warning(f"Frame index {frame_index} out of range "
                            f"[0, {self.total_frames})")
                return None
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = self._cap.read()
        if not ret:
            log.warning(f"Failed to decode frame {frame_index}")
        return frame if ret else None

    def read_next_frame(self):
        """Sequential read — much more reliable than per-frame seeking for
        bitstreams with B-frames or bad DTS/PTS (mmco: unref short failure)."""
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return None, None
            idx = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
            ret, frame = self._cap.read()
        return (idx, frame) if ret else (None, None)

    def seek(self, frame_index: int):
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                log.debug(f"Seeked to frame {frame_index}")

    @property
    def current_position(self) -> int:
        with self._lock:
            return int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) if self._cap else 0
