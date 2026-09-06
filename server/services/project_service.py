"""
server/services/project_service.py
─────────────────────────────────────
Manages project lifecycle on disk using storage.ProjectStorage.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime

import server.config as cfg


class ProjectService:
    """CRUD operations for tode server projects."""

    _META = "project.json"

    def __init__(self) -> None:
        self._root = cfg.PROJECTS_DIR

    # ── helpers ───────────────────────────────────────────────────────────────

    def _project_dir(self, project_id: str) -> str:
        return os.path.join(self._root, project_id)

    def _meta_path(self, project_id: str) -> str:
        return os.path.join(self._project_dir(project_id), self._META)

    def _read_meta(self, project_id: str) -> dict | None:
        p = self._meta_path(project_id)
        if not os.path.isfile(p):
            return None
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)

    def _write_meta(self, project_id: str, data: dict) -> None:
        path = self._meta_path(project_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _frame_count(self, project_id: str) -> tuple[int, int]:
        frames_dir  = os.path.join(self._project_dir(project_id), "frames")
        labels_dir  = os.path.join(self._project_dir(project_id), "labels")
        frames = [f for f in os.listdir(frames_dir) if f.endswith((".jpg", ".png"))] if os.path.isdir(frames_dir) else []
        labels = [f for f in os.listdir(labels_dir) if f.endswith(".txt")] if os.path.isdir(labels_dir) else []
        return len(frames), len(labels)

    # ── public API ────────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        description: str = "",
        class_names: list[str] | None = None,
        annotation_type: str = "detection",
    ) -> dict:
        project_id = name.lower().replace(" ", "_") + "_" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        pdir = self._project_dir(project_id)
        for sub in ("frames", "labels"):
            os.makedirs(os.path.join(pdir, sub), exist_ok=True)

        meta = {
            "id":              project_id,
            "name":            name,
            "description":     description,
            "class_names":     class_names or [],
            "annotation_type": annotation_type,
            "created_at":      datetime.now(UTC).isoformat(),
        }
        self._write_meta(project_id, meta)
        return {**meta, "frame_count": 0, "annotated_count": 0}

    def list_all(self) -> list[dict]:
        result = []
        if not os.path.isdir(self._root):
            return result
        for name in sorted(os.listdir(self._root)):
            meta = self._read_meta(name)
            if meta:
                meta.setdefault("annotation_type", "detection")
                fc, ac = self._frame_count(name)
                result.append({**meta, "frame_count": fc, "annotated_count": ac})
        return result

    def get(self, project_id: str) -> dict | None:
        meta = self._read_meta(project_id)
        if not meta:
            return None
        meta.setdefault("annotation_type", "detection")
        fc, ac = self._frame_count(project_id)
        return {**meta, "frame_count": fc, "annotated_count": ac}

    def delete(self, project_id: str) -> bool:
        import shutil
        pdir = self._project_dir(project_id)
        if os.path.isdir(pdir):
            shutil.rmtree(pdir)
            return True
        return False

    def update_classes(self, project_id: str, class_names: list[str]) -> bool:
        meta = self._read_meta(project_id)
        if not meta:
            return False
        meta["class_names"] = class_names
        self._write_meta(project_id, meta)
        return True

    def frames_dir(self, project_id: str) -> str:
        return os.path.join(self._project_dir(project_id), "frames")

    def labels_dir(self, project_id: str) -> str:
        return os.path.join(self._project_dir(project_id), "labels")
