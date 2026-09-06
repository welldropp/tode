"""
storage/formats/json_format.py
────────────────────────────────
Read/write annotations in tode JSON format.
"""
from __future__ import annotations

import json


class JSONFormat:
    """Static helpers for tode JSON annotation files."""

    @staticmethod
    def read(path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def write(path: str, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
