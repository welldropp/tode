"""Tests for core/pipeline."""
import time

from core.pipeline.batch_processor import BatchProcessor
from core.pipeline.job_scheduler import JobScheduler
from core.pipeline.queue_manager import QueueManager
from core.pipeline.worker import AnnotationWorker


class _FakeDetector:
    def detect(self, frame):
        return [{"class_id": 0, "confidence": 0.9}]


def test_batch_processor():
    frames   = [object() for _ in range(5)]
    detector = _FakeDetector()
    progress = []
    results  = BatchProcessor(
        detector,
        on_progress=lambda c, t: progress.append((c, t)),
    ).run(frames)
    assert len(results) == 5
    assert len(progress) == 5
    assert progress[-1] == (5, 5)


def test_batch_processor_empty():
    results = BatchProcessor(_FakeDetector()).run([])
    assert results == []


def test_annotation_worker():
    results = []

    def _cb(r):
        results.append(r)

    w = AnnotationWorker(_FakeDetector(), object(), _cb)
    w.start()
    w.join(timeout=3)
    assert len(results) == 1


def test_queue_manager():
    consumed = []

    def _consumer(item):
        consumed.append(item)

    mgr = QueueManager(num_workers=2, consumer=_consumer)
    for i in range(5):
        mgr.put(i)
    mgr.stop(join=True)
    # All 5 items should have been consumed
    assert len(consumed) == 5


def test_job_scheduler():
    order   = []
    sched   = JobScheduler(num_workers=1)

    for prio in (3, 1, 2):
        sched.submit(order.append, prio, priority=prio)

    time.sleep(0.1)
    sched.shutdown()
    # Highest priority (lowest int) should run first
    assert order[0] == 1
