"""Project-related request / response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    class_names: list[str] = []
    annotation_type: str = "detection"


class ClassNamesIn(BaseModel):
    class_names: list[str] = []


class ClassNamesUpdate(BaseModel):
    class_names: list[str] = []


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    class_names: list[str]
    annotation_type: str = "detection"
    frame_count: int
    annotated_count: int
    created_at: str
