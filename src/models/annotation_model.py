"""Pure-data model classes (no I/O)."""
from dataclasses import dataclass, field


@dataclass
class BoundingBox:
    """
    Stores one bounding box in YOLO normalised format.
    x_center, y_center, width, height — all in [0, 1].
    """
    class_id:   int
    class_name: str
    x_center:   float
    y_center:   float
    width:      float
    height:     float
    confidence: float = 1.0          # 1.0 for manual, model score for YOLO

    # ── pixel helpers ─────────────────────────────────────────────────────────
    def to_pixel_coords(self, img_w: int, img_h: int):
        """Return (x1, y1, x2, y2) in pixel coordinates."""
        cx = self.x_center * img_w
        cy = self.y_center * img_h
        w  = self.width    * img_w
        h  = self.height   * img_h
        return int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2)

    def to_yolo_line(self) -> str:
        return (
            f"{self.class_id} {self.x_center:.6f} {self.y_center:.6f} "
            f"{self.width:.6f} {self.height:.6f}"
        )


@dataclass
class PolygonAnnotation:
    """
    One polygon/segmentation mask in YOLO-seg normalised format.
    ``points`` is a list of (x, y) pairs, each in [0, 1].
    """
    class_id:   int
    class_name: str
    points:     list[tuple[float, float]]   # ordered vertices, normalised
    confidence: float = 1.0

    def to_yolo_seg_line(self) -> str:
        pts = " ".join(f"{x:.6f} {y:.6f}" for x, y in self.points)
        return f"{self.class_id} {pts}"

    @classmethod
    def from_yolo_seg_line(cls, line: str, class_map: dict) -> "PolygonAnnotation":
        parts = line.strip().split()
        cid   = int(parts[0])
        coords = list(map(float, parts[1:]))
        pts   = [(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)]
        return cls(class_id=cid, class_name=class_map.get(cid, str(cid)), points=pts)


@dataclass
class ImageClassification:
    """Image-level classification label (no spatial extent)."""
    class_id:   int
    class_name: str
    confidence: float = 1.0


@dataclass
class FrameAnnotation:
    """All annotations belonging to one video frame."""
    frame_index:     int
    frame_path:      str
    label_path:      str | None = None
    boxes:           list[BoundingBox] = field(default_factory=list)
    polygons:        list[PolygonAnnotation] = field(default_factory=list)
    classifications: list[ImageClassification] = field(default_factory=list)
    is_annotated:    bool = False

    def _refresh_annotated(self) -> None:
        self.is_annotated = bool(self.boxes or self.polygons or self.classifications)

    def add_box(self, box: BoundingBox) -> None:
        self.boxes.append(box)
        self._refresh_annotated()

    def remove_box(self, index: int) -> None:
        if 0 <= index < len(self.boxes):
            self.boxes.pop(index)
        self._refresh_annotated()

    def clear_boxes(self) -> None:
        self.boxes.clear()
        self._refresh_annotated()

    # ── polygon helpers ───────────────────────────────────────────────────────

    def add_polygon(self, poly: PolygonAnnotation) -> None:
        self.polygons.append(poly)
        self._refresh_annotated()

    def remove_polygon(self, index: int) -> None:
        if 0 <= index < len(self.polygons):
            self.polygons.pop(index)
        self._refresh_annotated()

    def clear_polygons(self) -> None:
        self.polygons.clear()
        self._refresh_annotated()

    # ── classification helpers ────────────────────────────────────────────────

    def set_classification(self, cls: ImageClassification) -> None:
        self.classifications = [cls]
        self._refresh_annotated()

    def clear_classifications(self) -> None:
        self.classifications.clear()
        self._refresh_annotated()
