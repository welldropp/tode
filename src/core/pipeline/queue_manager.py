"""
core/pipeline/queue_manager.py
────────────────────────────────
Thread-safe queue for distributing frames to workers.
"""
from __future__ import annotations

import queue
import threading


class QueueManager:
    """
    Distribute work items across a pool of consumer threads.

    Parameters
    ----------
    num_workers : int
        Number of consumer threads to spawn.
    consumer : Callable[[object], None]
        Called by each worker with a dequeued item.
    """

    def __init__(self, num_workers: int = 2, consumer=None) -> None:
        self._queue    = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._consumer = consumer
        self._stop     = threading.Event()

        for _ in range(num_workers):
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()
            self._workers.append(t)

    def put(self, item) -> None:
        self._queue.put(item)

    def drain(self) -> None:
        """Block until all queued items have been processed."""
        self._queue.join()

    def stop(self, join: bool = False) -> None:
        self._queue.join()  # wait for all real items to be consumed first
        self._stop.set()
        for _ in self._workers:
            self._queue.put(None)  # sentinel to unblock each worker
        if join:
            for t in self._workers:
                t.join()

    def _loop(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                if self._stop.is_set():
                    break
                continue
            if item is None:
                self._queue.task_done()
                break
            if self._consumer:
                self._consumer(item)
            self._queue.task_done()
