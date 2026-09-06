"""
server/services/export_service.py
───────────────────────────────────
Wraps core exporters for the web API.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile

from core.exporters.coco import COCOExporter
from core.exporters.csv_exporter import CSVExporter
from core.exporters.json_exporter import JSONExporter
from core.exporters.yolo import YOLOExporter
from server.services.project_service import ProjectService

_svc = ProjectService()

_EXPORTERS = {
    "yolo": YOLOExporter,
    "coco": COCOExporter,
    "csv":  CSVExporter,
    "json": JSONExporter,
}


def export_project(project_id: str, fmt: str = "yolo") -> str:
    """
    Run the requested exporter and return a path to a ready-to-download ZIP.
    The caller is responsible for removing the ZIP after sending it.
    """
    meta       = _svc.get(project_id)
    class_names = (meta or {}).get("class_names", [])
    labels_dir  = _svc.labels_dir(project_id)
    images_dir  = _svc.frames_dir(project_id)

    tmp_dir = tempfile.mkdtemp(prefix="tode_export_")
    exp_dir = os.path.join(tmp_dir, "export")
    os.makedirs(exp_dir)

    exporter_cls = _EXPORTERS.get(fmt, YOLOExporter)
    exporter     = exporter_cls(
        labels_dir=labels_dir,
        images_dir=images_dir,
        class_names=class_names,
        output_dir=exp_dir,
    )
    exporter.export()

    zip_path = os.path.join(tmp_dir, f"{project_id}_{fmt}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(exp_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arc_name = os.path.relpath(abs_path, exp_dir)
                zf.write(abs_path, arc_name)
    shutil.rmtree(exp_dir)
    return zip_path
