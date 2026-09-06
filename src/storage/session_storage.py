"""
storage/session_storage.py
────────────────────────────
Persist and restore annotation sessions to disk.
"""
from __future__ import annotations

import json
import os
from typing import Any


class SessionStorage:
    """
    Simple key-value session store backed by a JSON file.

    Parameters
    ----------
    session_file : str
        Path to the JSON file used as the session store.
    """

    def __init__(self, session_file: str) -> None:
        self._path = session_file
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict:
        if os.path.isfile(self._path):
            try:
                with open(self._path, encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._flush()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._flush()

    def all(self) -> dict:
        return dict(self._data)

    def clear(self) -> None:
        self._data.clear()
        self._flush()

    def _flush(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
