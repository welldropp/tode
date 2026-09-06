"""Annotation request / response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class BBoxIn(BaseModel):
    class_id: int
    class_name: str
    x_center: float
    y_center: float
    width: float
    height: float
    confidence: float = 1.0


class PolygonIn(BaseModel):
    class_id: int
    class_name: str
    points: list[tuple[float, float]]
    confidence: float = 1.0


class ClassificationIn(BaseModel):
    class_id: int
    class_name: str
    confidence: float = 1.0


class FrameAnnotationsIn(BaseModel):
    boxes: list[BBoxIn] = []
    polygons: list[PolygonIn] = []
    classifications: list[ClassificationIn] = []


class FrameAnnotationsOut(BaseModel):
    frame_index: int
    boxes: list[BBoxIn] = []
    polygons: list[PolygonIn] = []
    classifications: list[ClassificationIn] = []
    is_annotated: bool


class FrameOut(BaseModel):
    frame_index: int
    is_annotated: bool
    annotation_count: int
