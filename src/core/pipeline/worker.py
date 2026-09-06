"""
core/pipeline/worker.py
─────────────────────────
Thread worker that runs inference on a single frame.
"""
from __future__ import annotations

import threading
from collections.abc import Callable


class AnnotationWorker(threading.Thread):
    """
    Background worker thread for single-frame inference.

    Parameters
    ----------
    detector : object
        Any object with a ``detect(frame)`` method.
    frame : object
        The frame (numpy array) to process.
    callback : Callable
        Called with the detection results when done.
    """

    def __init__(self, detector, frame, callback: Callable) -> None:
        super().__init__(daemon=True)
        self._detector = detector
        self._frame    = frame
        self._callback = callback

    def run(self) -> None:
        try:
            results = self._detector.detect(self._frame)
        except Exception as exc:  # noqa: BLE001
            results = []
            print(f"[AnnotationWorker] error: {exc}")
        self._callback(results)
