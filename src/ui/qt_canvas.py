"""
ui/qt_canvas.py
────────────────
PyQt6 annotation canvas. Displays a frame (letterboxed) and supports:

  • view mode    — click a box to select it, drag body to move, drag one of the
                   8 handles to resize
  • draw mode    — click-drag to draw a new bounding box
  • polygon mode — click to place vertices, double-click to close, Esc cancels

All box / polygon coordinates the canvas emits and consumes are NORMALISED
([0, 1]) so they map 1-to-1 onto the core BoundingBox / PolygonAnnotation
models regardless of the displayed scale.
"""
from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtWidgets import QWidget

# Modes
VIEW, DRAW, POLYGON = "view", "draw", "polygon"

_HANDLE = 7          # half-size of a resize handle, in pixels
_PALETTE = [
    "#00ff88", "#ff5a5a", "#4da6ff", "#ffb14d", "#c86bff",
    "#ffe14d", "#4dffd6", "#ff7ac0", "#9dff4d", "#4d7aff",
]


def _class_color(class_id: int) -> QColor:
    return QColor(_PALETTE[class_id % len(_PALETTE)])


class AnnotationCanvas(QWidget):
    """Interactive annotation surface (bounding boxes + polygons)."""

    boxDrawn      = pyqtSignal(float, float, float, float)  # cx, cy, w, h (norm)
    boxEdited     = pyqtSignal(int, float, float, float, float)
    boxSelected   = pyqtSignal(int)                          # -1 = deselect
    polygonDrawn  = pyqtSignal(object)                       # list[(nx, ny)]
    openRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._pixmap: QPixmap | None = None
        self._img_w = 0
        self._img_h = 0

        self._mode = VIEW
        self._boxes: list = []       # list[BoundingBox]
        self._polys: list = []       # list[PolygonAnnotation]
        self._selected = -1
        self._poly_opacity = 0.35

        # interaction state
        self._drag_start: QPointF | None = None
        self._drag_cur:   QPointF | None = None
        self._active_handle: int | None = None   # 0..7, or 8 = body-move
        self._poly_points: list[tuple[float, float]] = []  # normalized, in progress

    # ── public API ────────────────────────────────────────────────────────────
    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode != POLYGON:
            self._poly_points = []
        if mode != VIEW:
            self._selected = -1
        self.update()

    def mode(self) -> str:
        return self._mode

    def set_image_bgr(self, bgr) -> None:
        if bgr is None:
            self._pixmap = None
            self._img_w = self._img_h = 0
        else:
            self._img_h, self._img_w = bgr.shape[:2]
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            rgb = np.ascontiguousarray(rgb)
            qimg = QImage(rgb.data, self._img_w, self._img_h,
                          3 * self._img_w, QImage.Format.Format_RGB888)
            self._pixmap = QPixmap.fromImage(qimg.copy())
        self.update()

    def set_boxes(self, boxes: list, selected: int = -1) -> None:
        self._boxes = list(boxes)
        self._selected = selected if -1 <= selected < len(self._boxes) else -1
        self.update()

    def set_polygons(self, polys: list) -> None:
        self._polys = list(polys)
        self.update()

    def set_selected(self, index: int) -> None:
        self._selected = index if -1 <= index < len(self._boxes) else -1
        self.update()

    def set_polygon_opacity(self, value: float) -> None:
        self._poly_opacity = max(0.0, min(1.0, value))
        self.update()

    def clear(self) -> None:
        self._boxes, self._polys, self._poly_points = [], [], []
        self._selected = -1
        self.update()

    # ── coordinate mapping (widget ↔ normalized) ───────────────────────────────
    def _display_rect(self) -> QRectF:
        """Letterboxed rectangle where the image is painted, in widget coords."""
        if not self._img_w or not self._img_h:
            return QRectF(0, 0, self.width(), self.height())
        scale = min(self.width() / self._img_w, self.height() / self._img_h)
        dw, dh = self._img_w * scale, self._img_h * scale
        return QRectF((self.width() - dw) / 2, (self.height() - dh) / 2, dw, dh)

    def _to_norm(self, p: QPointF) -> tuple[float, float]:
        r = self._display_rect()
        if r.width() <= 0 or r.height() <= 0:
            return 0.0, 0.0
        nx = (p.x() - r.left()) / r.width()
        ny = (p.y() - r.top()) / r.height()
        return min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0)

    def _to_widget(self, nx: float, ny: float) -> QPointF:
        r = self._display_rect()
        return QPointF(r.left() + nx * r.width(), r.top() + ny * r.height())

    def _box_widget_rect(self, box) -> QRectF:
        tl = self._to_widget(box.x_center - box.width / 2, box.y_center - box.height / 2)
        br = self._to_widget(box.x_center + box.width / 2, box.y_center + box.height / 2)
        return QRectF(tl, br)

    def _handle_points(self, rect: QRectF) -> list[QPointF]:
        lft, top, rgt, bot = rect.left(), rect.top(), rect.right(), rect.bottom()
        mx, my = (lft + rgt) / 2, (top + bot) / 2
        # order: 0 TL,1 TM,2 TR,3 MR,4 BR,5 BM,6 BL,7 ML
        return [
            QPointF(lft, top), QPointF(mx, top), QPointF(rgt, top), QPointF(rgt, my),
            QPointF(rgt, bot), QPointF(mx, bot), QPointF(lft, bot), QPointF(lft, my),
        ]

    # ── painting ────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#14141f"))
        if self._pixmap is None:
            p.setPen(QColor("#666688"))
            p.setFont(QFont("Sans", 12))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Open a video, image, or folder to begin\n(click here or use the toolbar)")
            p.end()
            return

        rect = self._display_rect()
        p.drawPixmap(rect.toRect(), self._pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # polygons (committed)
        for poly in self._polys:
            self._paint_polygon(p, poly)

        # polygon in progress
        if self._mode == POLYGON and self._poly_points:
            pen = QPen(QColor("#ffe14d"), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            pts = [self._to_widget(nx, ny) for nx, ny in self._poly_points]
            for i in range(1, len(pts)):
                p.drawLine(pts[i - 1], pts[i])
            for pt in pts:
                p.setBrush(QBrush(QColor("#ffe14d")))
                p.drawEllipse(pt, 3, 3)

        # boxes
        for i, box in enumerate(self._boxes):
            self._paint_box(p, box, i == self._selected)

        # box being drawn
        if self._mode == DRAW and self._drag_start and self._drag_cur:
            pen = QPen(QColor("#00ff88"), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(self._drag_start, self._drag_cur).normalized())
        p.end()

    def _paint_box(self, p: QPainter, box, selected: bool) -> None:
        rect = self._box_widget_rect(box)
        color = _class_color(box.class_id)
        p.setPen(QPen(color, 3 if selected else 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(rect)

        label = f"{box.class_name}"
        if box.confidence < 1.0:
            label += f" {box.confidence:.2f}"
        p.setFont(QFont("Sans", 8, QFont.Weight.Bold))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(label) + 8
        th = fm.height() + 2
        p.fillRect(QRectF(rect.left(), rect.top() - th, tw, th), color)
        p.setPen(QColor("#101018"))
        p.drawText(QRectF(rect.left() + 4, rect.top() - th, tw, th),
                   Qt.AlignmentFlag.AlignVCenter, label)

        if selected:
            p.setBrush(QBrush(QColor("#ffffff")))
            p.setPen(QPen(color, 1))
            for hp in self._handle_points(rect):
                p.drawRect(QRectF(hp.x() - _HANDLE, hp.y() - _HANDLE, 2 * _HANDLE, 2 * _HANDLE))

    def _paint_polygon(self, p: QPainter, poly) -> None:
        if len(poly.points) < 2:
            return
        color = _class_color(poly.class_id)
        qpoly = QPolygonF([self._to_widget(nx, ny) for nx, ny in poly.points])
        fill = QColor(color)
        fill.setAlphaF(self._poly_opacity)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(color, 2))
        p.drawPolygon(qpoly)

    # ── mouse / keyboard ──────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            if event.button() == Qt.MouseButton.RightButton and self._mode == POLYGON:
                self._poly_points = []
                self.update()
            return
        pos = QPointF(event.position())

        if self._pixmap is None:
            self.openRequested.emit()
            return

        if self._mode == DRAW:
            self._drag_start = pos
            self._drag_cur = pos
        elif self._mode == POLYGON:
            self._poly_points.append(self._to_norm(pos))
            self.update()
        else:  # VIEW — select / begin edit
            self._begin_view_interaction(pos)

    def _begin_view_interaction(self, pos: QPointF) -> None:
        # handle hit-test on the currently selected box first
        if 0 <= self._selected < len(self._boxes):
            rect = self._box_widget_rect(self._boxes[self._selected])
            for hi, hp in enumerate(self._handle_points(rect)):
                if abs(pos.x() - hp.x()) <= _HANDLE and abs(pos.y() - hp.y()) <= _HANDLE:
                    self._active_handle = hi
                    self._drag_start = pos
                    return
            if rect.contains(pos):
                self._active_handle = 8   # body move
                self._drag_start = pos
                return
        # otherwise select whichever box is under the cursor (topmost last)
        hit = -1
        for i in range(len(self._boxes) - 1, -1, -1):
            if self._box_widget_rect(self._boxes[i]).contains(pos):
                hit = i
                break
        self._selected = hit
        self._active_handle = None
        self.boxSelected.emit(hit)
        self.update()

    def mouseMoveEvent(self, event):
        pos = QPointF(event.position())
        if self._mode == DRAW and self._drag_start:
            self._drag_cur = pos
            self.update()
        elif self._mode == VIEW and self._active_handle is not None and self._drag_start:
            self._apply_edit_drag(pos)

    def _apply_edit_drag(self, pos: QPointF) -> None:
        box = self._boxes[self._selected]
        nx1 = box.x_center - box.width / 2
        ny1 = box.y_center - box.height / 2
        nx2 = box.x_center + box.width / 2
        ny2 = box.y_center + box.height / 2
        cx, cy = self._to_norm(pos)

        h = self._active_handle
        if h == 8:  # move body
            pnx, pny = self._to_norm(self._drag_start)
            dx, dy = cx - pnx, cy - pny
            nx1 += dx
            nx2 += dx
            ny1 += dy
            ny2 += dy
            self._drag_start = pos
        else:
            if h in (0, 6, 7):      # left edge
                nx1 = cx
            if h in (2, 3, 4):      # right edge
                nx2 = cx
            if h in (0, 1, 2):      # top edge
                ny1 = cy
            if h in (4, 5, 6):      # bottom edge
                ny2 = cy

        nx1, nx2 = sorted((max(0.0, nx1), min(1.0, nx2)))
        ny1, ny2 = sorted((max(0.0, ny1), min(1.0, ny2)))
        box.x_center = (nx1 + nx2) / 2
        box.y_center = (ny1 + ny2) / 2
        box.width = max(1e-4, nx2 - nx1)
        box.height = max(1e-4, ny2 - ny1)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._mode == DRAW and self._drag_start and self._drag_cur:
            nx1, ny1 = self._to_norm(self._drag_start)
            nx2, ny2 = self._to_norm(self._drag_cur)
            self._drag_start = self._drag_cur = None
            if abs(nx2 - nx1) > 0.005 and abs(ny2 - ny1) > 0.005:
                cx, cy = (nx1 + nx2) / 2, (ny1 + ny2) / 2
                w, h = abs(nx2 - nx1), abs(ny2 - ny1)
                self.boxDrawn.emit(cx, cy, w, h)
            self.update()
        elif self._mode == VIEW and self._active_handle is not None:
            b = self._boxes[self._selected]
            self.boxEdited.emit(self._selected, b.x_center, b.y_center, b.width, b.height)
            self._active_handle = None
            self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        if self._mode == POLYGON and len(self._poly_points) >= 3:
            pts = list(self._poly_points)
            self._poly_points = []
            self.polygonDrawn.emit(pts)
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._mode == POLYGON:
            self._poly_points = []
            self.update()
        else:
            super().keyPressEvent(event)
