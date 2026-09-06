"""Project CRUD endpoints."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from server.schemas.project import ClassNamesUpdate, ProjectCreate, ProjectOut
from server.services.export_service import export_project
from server.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects")
_svc   = ProjectService()


@router.get("", response_model=list[ProjectOut])
def list_projects():
    return _svc.list_all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate):
    return _svc.create(body.name, body.description, body.class_names, body.annotation_type)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str):
    proj = _svc.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str):
    if not _svc.delete(project_id):
        raise HTTPException(status_code=404, detail="Project not found")


@router.patch("/{project_id}/classes", status_code=204)
def update_classes(project_id: str, body: ClassNamesUpdate):
    if not _svc.update_classes(project_id, body.class_names):
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/upload")
async def upload_frames(project_id: str, files: list[UploadFile]):
    """Upload one or more image files as frames into the project."""
    proj = _svc.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    frames_dir = _svc.frames_dir(project_id)
    existing   = len([f for f in os.listdir(frames_dir) if f.endswith((".jpg", ".png"))])
    for i, file in enumerate(files):
        ext  = os.path.splitext(file.filename or "")[1] or ".jpg"
        dest = os.path.join(frames_dir, f"frame_{existing + i:06d}{ext}")
        with open(dest, "wb") as fh:
            content = await file.read()
            fh.write(content)
    return {"uploaded": len(files)}


@router.get("/{project_id}/export")
def export(project_id: str, fmt: str = "yolo"):
    """Download a ZIP of the exported dataset."""
    if _svc.get(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if fmt not in ("yolo", "coco", "csv", "json"):
        raise HTTPException(status_code=400, detail=f"Unknown format '{fmt}'")
    zip_path = export_project(project_id, fmt)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=os.path.basename(zip_path),
        background=None,
    )
