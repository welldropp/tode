"""
core/importers/base.py
────────────────────────
Abstract base class for annotation importers.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class BaseImporter(ABC):
    """
    Import annotations from an external source into YOLO .txt format.

    Parameters
    ----------
    source_dir : str
        Directory or file containing the source annotations.
    output_labels_dir : str
        Where to write the converted YOLO .txt files.
    """

    def __init__(self, source_dir: str, output_labels_dir: str) -> None:
        self.source_dir        = source_dir
        self.output_labels_dir = output_labels_dir
        os.makedirs(output_labels_dir, exist_ok=True)

    @abstractmethod
    def load(self) -> tuple[list[str], int]:
        """
        Load and convert annotations.

        Returns
        -------
        tuple[list[str], int]
            ``(class_names, annotation_count)``
        """

    def _write_yolo(self, stem: str, rows: list[dict]) -> None:
        """Write *rows* to ``<stem>.txt`` in YOLO format."""
        path = os.path.join(self.output_labels_dir, stem + ".txt")
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(f"{r['class_id']} {r['cx']:.6f} {r['cy']:.6f} {r['w']:.6f} {r['h']:.6f}\n")
