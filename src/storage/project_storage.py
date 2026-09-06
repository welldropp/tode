"""
storage/project_storage.py
────────────────────────────
Manage project directories and metadata files.
"""
from __future__ import annotations

import json
from pathlib import Path


class ProjectStorage:
    """
    Handle project directory creation and metadata I/O.

    Parameters
    ----------
    root : str
        Base directory under which projects are stored.
    """

    _META_FILE = "project.json"

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def create_project(self, name: str) -> Path:
        """Create and return the path to a new named project directory."""
        project_dir = self._root / name
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "labels").mkdir(exist_ok=True)
        (project_dir / "frames").mkdir(exist_ok=True)
        return project_dir

    def list_projects(self) -> list[str]:
        """Return names of all projects under *root*."""
        return [
            p.name for p in sorted(self._root.iterdir())
            if p.is_dir() and (p / self._META_FILE).exists()
        ]

    def load_meta(self, name: str) -> dict:
        """Load project metadata dict."""
        path = self._root / name / self._META_FILE
        if path.is_file():
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def save_meta(self, name: str, data: dict) -> None:
        """Persist project metadata."""
        project_dir = self._root / name
        project_dir.mkdir(parents=True, exist_ok=True)
        with open(project_dir / self._META_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def delete_project(self, name: str) -> bool:
        """Delete a project directory. Returns True if it existed."""
        import shutil
        project_dir = self._root / name
        if project_dir.is_dir():
            shutil.rmtree(project_dir)
            return True
        return False
