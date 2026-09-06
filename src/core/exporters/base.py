"""
core/exporters/base.py
────────────────────────
Abstract base class for all annotation exporters.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class BaseExporter(ABC):
    """
    Export annotations stored in a labels directory to a target format.

    Parameters
    ----------
    labels_dir : str
        Directory containing per-frame ``.txt`` label files.
    images_dir : str
        Directory containing corresponding image files.
    class_names : list[str]
        Ordered list of class name strings.
    output_dir : str
        Destination directory for the exported dataset.
    """

    def __init__(
        self,
        labels_dir: str,
        images_dir: str,
        class_names: list[str],
        output_dir: str,
    ) -> None:
        self.labels_dir  = labels_dir
        self.images_dir  = images_dir
        self.class_names = class_names
        self.output_dir  = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @abstractmethod
    def export(self) -> int:
        """
        Run the export.

        Returns
        -------
        int
            Number of annotations written.
        """

    def _label_files(self) -> list[str]:
        """Return sorted list of ``.txt`` files in :attr:`labels_dir`."""
        if not os.path.isdir(self.labels_dir):
            return []
        return sorted(
            f for f in os.listdir(self.labels_dir) if f.endswith(".txt")
        )

    def _parse_label_file(self, filename: str) -> list[dict]:
        """Parse a YOLO-format label file into a list of annotation dicts."""
        path = os.path.join(self.labels_dir, filename)
        rows = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                cls_id = int(parts[0])
                cx, cy, w, h = map(float, parts[1:5])
                rows.append({"class_id": cls_id, "cx": cx, "cy": cy, "w": w, "h": h})
        return rows
