"""
server/services/annotation_service.py
────────────────────────────────────────
Save/load per-frame annotations using the existing LabelStorage logic.
"""
from __future__ import annotations

import os

from server.schemas.annotation import (
    BBoxIn,
    ClassificationIn,
    FrameAnnotationsIn,
    FrameAnnotationsOut,
    FrameOut,
    PolygonIn,
)
from server.services.project_service import ProjectService
from storage.formats.yolo_format import YOLOFormat

_svc = ProjectService()


def _label_path(labels_dir: str, frame_index: int, ext: str = ".txt") -> str:
    return os.path.join(labels_dir, f"frame_{frame_index:06d}{ext}")


def _class_map(labels_dir: str) -> dict[int, str]:
    import json
    p = os.path.join(labels_dir, "classes.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            raw = json.load(fh)
        return {int(k): v for k, v in raw.items()}
    return {}


def _save_class_map(labels_dir: str, cmap: dict[int, str]) -> None:
    import json
    with open(os.path.join(labels_dir, "classes.json"), "w", encoding="utf-8") as fh:
        json.dump({str(k): v for k, v in cmap.items()}, fh, indent=2)


def list_frames(project_id: str) -> list[FrameOut]:
    frames_dir = _svc.frames_dir(project_id)
    labels_dir = _svc.labels_dir(project_id)
    if not os.path.isdir(frames_dir):
        return []
    files = sorted(f for f in os.listdir(frames_dir) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    result = []
    for fname in files:
        stem = os.path.splitext(fname)[0]
        try:
            idx = int(stem.split("_")[-1])
        except ValueError:
            idx = 0
        lbl = os.path.join(labels_dir, f"{stem}.txt")
        rows = YOLOFormat.read(lbl) if os.path.isfile(lbl) else []
        result.append(FrameOut(frame_index=idx, is_annotated=bool(rows), annotation_count=len(rows)))
    return result


def get_frame_annotations(project_id: str, frame_index: int) -> FrameAnnotationsOut:
    labels_dir = _svc.labels_dir(project_id)
    cmap = _class_map(labels_dir)

    boxes = [
        BBoxIn(
            class_id=r["class_id"],
            class_name=cmap.get(r["class_id"], str(r["class_id"])),
            x_center=r["cx"], y_center=r["cy"],
            width=r["w"], height=r["h"],
        )
        for r in YOLOFormat.read(_label_path(labels_dir, frame_index))
    ]

    polys: list[PolygonIn] = []
    seg_path = _label_path(labels_dir, frame_index, ext=".seg.txt")
    if os.path.isfile(seg_path):
        with open(seg_path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) < 7:
                    continue
                cid    = int(parts[0])
                coords = list(map(float, parts[1:]))
                pts    = [(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)]
                polys.append(PolygonIn(
                    class_id=cid, class_name=cmap.get(cid, str(cid)), points=pts,
                ))

    clss: list[ClassificationIn] = []
    cls_path = _label_path(labels_dir, frame_index, ext=".cls.txt")
    if os.path.isfile(cls_path):
        with open(cls_path, encoding="utf-8") as fh:
            for line in fh:
                p = line.strip().split()
                if p:
                    cid  = int(p[0])
                    conf = float(p[1]) if len(p) > 1 else 1.0
                    clss.append(ClassificationIn(
                        class_id=cid, class_name=cmap.get(cid, str(cid)), confidence=conf,
                    ))

    return FrameAnnotationsOut(
        frame_index=frame_index,
        boxes=boxes,
        polygons=polys,
        classifications=clss,
        is_annotated=bool(boxes or polys or clss),
    )


def save_frame_annotations(project_id: str, frame_index: int, body: FrameAnnotationsIn) -> None:
    labels_dir = _svc.labels_dir(project_id)
    os.makedirs(labels_dir, exist_ok=True)
    cmap = _class_map(labels_dir)

    # Boxes → YOLO .txt
    rows = [
        {"class_id": b.class_id, "cx": b.x_center, "cy": b.y_center, "w": b.width, "h": b.height}
        for b in body.boxes
    ]
    YOLOFormat.write(_label_path(labels_dir, frame_index), rows)
    for b in body.boxes:
        cmap[b.class_id] = b.class_name

    # Polygons → .seg.txt
    if body.polygons:
        with open(_label_path(labels_dir, frame_index, ".seg.txt"), "w", encoding="utf-8") as fh:
            for poly in body.polygons:
                pts = " ".join(f"{x:.6f} {y:.6f}" for x, y in poly.points)
                fh.write(f"{poly.class_id} {pts}\n")
                cmap[poly.class_id] = poly.class_name

    # Classifications → .cls.txt
    if body.classifications:
        with open(_label_path(labels_dir, frame_index, ".cls.txt"), "w", encoding="utf-8") as fh:
            for cls in body.classifications:
                fh.write(f"{cls.class_id} {cls.confidence:.4f}\n")
                cmap[cls.class_id] = cls.class_name

    _save_class_map(labels_dir, cmap)
