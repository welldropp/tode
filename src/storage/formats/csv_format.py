"""
storage/formats/csv_format.py
───────────────────────────────
Read/write annotations as flat CSV.
"""
from __future__ import annotations

import csv

_FIELDS = ["filename", "class_id", "class_name", "cx", "cy", "w", "h"]


class CSVFormat:
    """Static helpers for CSV annotation files."""

    @staticmethod
    def read(path: str) -> list[dict]:
        rows: list[dict] = []
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    rows.append(row)
        except FileNotFoundError:
            pass
        return rows

    @staticmethod
    def write(path: str, rows: list[dict]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
