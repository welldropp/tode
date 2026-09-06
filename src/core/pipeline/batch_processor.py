"""
core/pipeline/batch_processor.py
──────────────────────────────────
Processes a batch of frames through the detector in sequence.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable


class BatchProcessor:
    """
    Run inference across a list of frames sequentially.

    Parameters
    ----------
    detector : object
        Object with ``detect(frame)`` method.
    on_progress : Callable[[int, int], None] | None
        Called with ``(current, total)`` on each step.
    on_complete : Callable[[list], None] | None
        Called with all result batches when finished.
    """

    def __init__(
        self,
        detector,
        on_progress: Callable[[int, int], None] | None = None,
        on_complete: Callable[[list], None] | None = None,
    ) -> None:
        self._detector    = detector
        self._on_progress = on_progress
        self._on_complete = on_complete

    def run(self, frames: Iterable) -> list:
        """Process *frames* and return list of per-frame detections."""
        frames_list = list(frames)
        total   = len(frames_list)
        results = []

        for i, frame in enumerate(frames_list):
            try:
                dets = self._detector.detect(frame)
            except Exception:  # noqa: BLE001
                dets = []
            results.append(dets)
            if self._on_progress:
                self._on_progress(i + 1, total)

        if self._on_complete:
            self._on_complete(results)
        return results
