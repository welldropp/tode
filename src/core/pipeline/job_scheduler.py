"""
core/pipeline/job_scheduler.py
────────────────────────────────
Simple priority-based job scheduler for annotation tasks.
"""
from __future__ import annotations

import heapq
import threading
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(order=True)
class _Job:
    priority: int
    fn: Callable = field(compare=False)
    args: tuple   = field(compare=False, default_factory=tuple)


class JobScheduler:
    """
    Priority-queue scheduler.  Higher priority (lower int) jobs run first.

    Parameters
    ----------
    num_workers : int
        Number of worker threads.
    """

    def __init__(self, num_workers: int = 1) -> None:
        self._heap:    list[_Job]              = []
        self._lock     = threading.Lock()
        self._cond     = threading.Condition(self._lock)
        self._workers: list[threading.Thread]  = []
        self._running  = True

        for _ in range(num_workers):
            t = threading.Thread(target=self._run, daemon=True)
            t.start()
            self._workers.append(t)

    def submit(self, fn: Callable, *args, priority: int = 5) -> None:
        """Schedule *fn* to run with *args* at the given *priority*."""
        with self._cond:
            heapq.heappush(self._heap, _Job(priority=priority, fn=fn, args=args))
            self._cond.notify()

    def shutdown(self) -> None:
        with self._cond:
            self._running = False
            self._cond.notify_all()

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._heap and self._running:
                    self._cond.wait()
                if not self._running and not self._heap:
                    return
                job = heapq.heappop(self._heap)
            job.fn(*job.args)
