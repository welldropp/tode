"""Handles saving / listing extracted frame images."""
import os

import cv2

from utils.config import FRAMES_DIR


class FrameStorage:
    """
    Saves BGR numpy frames as PNG files and provides helpers
    to list/retrieve already-saved frames.
    """

    def __init__(self, video_name: str):
        self.video_name = video_name
        self.base_dir   = os.path.join(FRAMES_DIR, video_name)
        os.makedirs(self.base_dir, exist_ok=True)

    # ── write ─────────────────────────────────────────────────────────────────
    def save(self, frame_index: int, bgr_frame) -> str:
        """Write frame to disk and return its path."""
        path = self._frame_path(frame_index)
        cv2.imwrite(path, bgr_frame)
        return path

    # ── read ──────────────────────────────────────────────────────────────────
    def load(self, frame_index: int):
        """Return a BGR numpy array or None if the file doesn't exist."""
        path = self._frame_path(frame_index)
        if os.path.exists(path):
            return cv2.imread(path)
        return None

    # ── listing ───────────────────────────────────────────────────────────────
    def list_saved_indices(self):
        """Return sorted list of frame indices that have been saved."""
        indices = []
        for fname in os.listdir(self.base_dir):
            if fname.startswith("frame_") and fname.endswith(".png"):
                try:
                    idx = int(fname[6:12])
                    indices.append(idx)
                except ValueError:
                    pass
        return sorted(indices)

    def exists(self, frame_index: int) -> bool:
        return os.path.exists(self._frame_path(frame_index))

    # ── helpers ───────────────────────────────────────────────────────────────
    def _frame_path(self, frame_index: int) -> str:
        return os.path.join(self.base_dir, f"frame_{frame_index:06d}.png")

    @property
    def directory(self) -> str:
        return self.base_dir
