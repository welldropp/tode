"""Tests for core/analytics."""
import os

import pytest

from core.analytics.class_stats import ClassStats, compute_class_stats
from core.analytics.report_generator import ReportGenerator
from core.analytics.session_stats import SessionStats
from core.analytics.stats import AnnotationStats


@pytest.fixture
def labels_dir(tmp_path):
    d = tmp_path / "labels"
    d.mkdir()
    (d / "frame_1.txt").write_text("0 0.5 0.5 0.3 0.3\n0 0.2 0.2 0.1 0.1\n")
    (d / "frame_2.txt").write_text("1 0.6 0.6 0.2 0.2\n")
    (d / "frame_3.txt").write_text("")
    return str(d)


def test_annotation_stats_counts(labels_dir):
    stats = AnnotationStats.from_label_dir(labels_dir, ["cat", "dog"])
    assert stats.total_annotations == 3
    assert stats.annotated_frames  == 2
    assert stats.total_frames      == 3


def test_annotation_rate(labels_dir):
    stats = AnnotationStats.from_label_dir(labels_dir, ["cat", "dog"])
    assert abs(stats.annotation_rate - 2 / 3) < 1e-6


def test_class_stats(labels_dir):
    results = compute_class_stats(["cat", "dog"], labels_dir)
    assert isinstance(results[0], ClassStats)
    total = sum(cs.count for cs in results)
    assert total == 3


def test_session_stats():
    ss = SessionStats()
    ss.record_frame()
    ss.record_add(auto=True)
    ss.record_add(auto=False)
    ss.record_delete()
    assert ss.frames_visited     == 1
    assert ss.annotations_added  == 2
    assert ss.auto_annotations   == 1
    assert ss.manual_annotations == 1
    assert ss.annotations_deleted == 1


def test_session_stats_summary():
    ss = SessionStats()
    ss.record_add()
    sm = ss.summary()
    assert "elapsed_s" in sm
    assert sm["annotations_added"] == 1


def test_report_generator_json(tmp_path, labels_dir):
    stats  = AnnotationStats.from_label_dir(labels_dir, ["cat", "dog"])
    report = ReportGenerator(stats)
    out    = str(tmp_path / "report.json")
    report.to_json(out)
    assert os.path.isfile(out)


def test_report_generator_text(labels_dir):
    stats  = AnnotationStats.from_label_dir(labels_dir, ["cat", "dog"])
    report = ReportGenerator(stats)
    text   = report.to_text()
    assert "tode Annotation Report" in text
    assert "cat" in text


def test_empty_labels_dir(tmp_path):
    stats = AnnotationStats.from_label_dir(str(tmp_path / "nonexistent"), [])
    assert stats.total_annotations == 0
    assert stats.annotation_rate   == 0.0
