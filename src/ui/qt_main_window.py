"""
ui/qt_main_window.py
─────────────────────
PyQt6 main window for tode. A thin controller over the headless core:

    QMainWindow ── AnnotationCanvas
        │
        ├── LoadWorker   → AnnotationManager (video / image / folder)
        ├── DetectWorker → AutoAnnotator (RT-DETR) → boxes
        └── DatasetExporter (YOLO / COCO)

Every UI action maps onto an AnnotationManager call; the manager owns all state.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.exporter import DatasetExporter
from models.annotation_model import BoundingBox, ImageClassification, PolygonAnnotation
from ui.qt_canvas import DRAW, POLYGON, VIEW, AnnotationCanvas
from ui.qt_workers import DetectWorker, LoadWorker
from utils.config import RTDETR_DEFAULT_MODEL, RTDETR_MODELS
from utils.logger import get_logger

log = get_logger("ui.qt_main_window")

_VIDEO_EXTS = "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv"
_IMAGE_EXTS = "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"


class TodeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tode — RT-DETR annotation")
        self.resize(1280, 820)

        self.manager = None
        self.current_index = 0
        self._indices: list[int] = []
        self._class_ids: dict[str, int] = {}
        self._busy = False
        self._worker = None

        self._build_ui()
        self._build_shortcuts()
        log.info("Qt main window ready")

    # ── construction ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self.canvas = AnnotationCanvas()
        self.canvas.boxDrawn.connect(self._on_box_drawn)
        self.canvas.boxEdited.connect(self._on_box_edited)
        self.canvas.boxSelected.connect(self._on_box_selected)
        self.canvas.polygonDrawn.connect(self._on_polygon_drawn)
        self.canvas.openRequested.connect(self._open_source)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)

        # left: canvas + frame nav
        left = QVBoxLayout()
        left.addWidget(self.canvas, 1)
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev")
        self.next_btn = QPushButton("Next ▶")
        self.prev_btn.clicked.connect(lambda: self._nav(-1))
        self.next_btn.clicked.connect(lambda: self._nav(+1))
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.valueChanged.connect(self._on_slider)
        self.counter = QLabel("Frame 0 / 0")
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.frame_slider, 1)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.counter)
        left.addLayout(nav)
        root.addLayout(left, 1)

        # right: control panel
        root.addWidget(self._build_panel())

        self.setCentralWidget(central)
        self._build_toolbar()

        self.status = self.statusBar()
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.hide()
        self.status.addPermanentWidget(self.progress)
        self._set_status("No source loaded — open a video, image, or folder.")

    def _build_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(280)
        v = QVBoxLayout(panel)

        v.addWidget(QLabel("<b>Mode</b>"))
        mode_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["View (V)", "Draw box (W)", "Polygon"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_change)
        mode_row.addWidget(self.mode_combo)
        v.addLayout(mode_row)

        v.addWidget(QLabel("<b>RT-DETR model</b>"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(RTDETR_MODELS)
        self.model_combo.setCurrentText(RTDETR_DEFAULT_MODEL)
        self.model_combo.currentTextChanged.connect(self._on_model_change)
        v.addWidget(self.model_combo)

        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confidence"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 0.95)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.45)
        self.conf_spin.valueChanged.connect(self._on_conf_change)
        conf_row.addWidget(self.conf_spin)
        v.addLayout(conf_row)

        self.detect_btn = QPushButton("⚡ Detect Frame")
        self.detect_all_btn = QPushButton("🔁 Detect All Frames")
        self.detect_btn.clicked.connect(self._run_detect)
        self.detect_all_btn.clicked.connect(self._run_detect_all)
        v.addWidget(self.detect_btn)
        v.addWidget(self.detect_all_btn)

        v.addWidget(QLabel("<b>Class for new box</b>"))
        self.class_edit = QLineEdit("object")
        v.addWidget(self.class_edit)

        v.addWidget(QLabel("<b>Annotations</b>"))
        self.box_list = QListWidget()
        self.box_list.currentRowChanged.connect(self._on_list_row)
        v.addWidget(self.box_list, 1)

        del_row = QHBoxLayout()
        self.del_btn = QPushButton("🗑 Delete")
        self.clear_btn = QPushButton("Clear frame")
        self.del_btn.clicked.connect(self._delete_selected_box)
        self.clear_btn.clicked.connect(self._clear_frame)
        del_row.addWidget(self.del_btn)
        del_row.addWidget(self.clear_btn)
        v.addLayout(del_row)

        self.classify_btn = QPushButton("🏷 Classify frame")
        self.classify_btn.clicked.connect(self._classify_frame)
        v.addWidget(self.classify_btn)

        return panel

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        def act(text, slot, shortcut=None):
            a = QAction(text, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            tb.addAction(a)
            return a

        act("📂 Open", self._open_source, "Ctrl+O")
        act("🎬 Video", self._open_video)
        act("🖼 Image", self._open_image)
        act("📁 Folder", self._open_folder)
        tb.addSeparator()
        act("💾 Save", self._save, "Ctrl+S")
        act("📤 Export", self._export, "Ctrl+E")
        tb.addSeparator()
        act("📋 Logs", self._show_logs)

    def _build_shortcuts(self):
        specs = {
            "A": lambda: self._nav(-1), "Left": lambda: self._nav(-1),
            "D": lambda: self._nav(+1), "Right": lambda: self._nav(+1),
            "Home": lambda: self._nav("first"), "End": lambda: self._nav("last"),
            "W": lambda: self.mode_combo.setCurrentIndex(1),
            "V": lambda: self.mode_combo.setCurrentIndex(0),
            "Y": self._run_detect,
            "Delete": self._clear_frame,
        }
        for key, fn in specs.items():
            a = QAction(self)
            a.setShortcut(QKeySequence(key))
            a.triggered.connect(fn)
            self.addAction(a)

    # ── source opening ──────────────────────────────────────────────────────
    def _open_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open video or image", "",
            f"Media ({_VIDEO_EXTS} {_IMAGE_EXTS})",
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}:
            self._open_video(path)
        else:
            self._start_load("image", path)

    def _open_video(self, path: str | None = None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open video", "", f"Video ({_VIDEO_EXTS})")
        if not path:
            return
        step, ok = QInputDialog.getInt(self, "Frame step", "Load every N-th frame:", 1, 1, 30)
        if not ok:
            step = 1
        self._start_load("video", path, step)

    def _open_image(self, path: str | None = None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open image", "", f"Image ({_IMAGE_EXTS})")
        if path:
            self._start_load("image", path)

    def _open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open image folder")
        if path:
            self._start_load("image_folder", path)

    def _start_load(self, source_type: str, path: str, step: int = 1):
        if self._busy:
            return
        self._set_busy(True, f"Loading {os.path.basename(path)}…")
        self._worker = LoadWorker(source_type, path, step)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_loaded)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_loaded(self, manager):
        self.manager = manager
        self._indices = manager.all_frame_indices()
        self.current_index = 0
        self._set_busy(False)
        self.frame_slider.setMaximum(max(0, len(self._indices) - 1))
        self._show_frame(0)
        self._set_status(f"Loaded {len(self._indices)} frame(s).")

    # ── frame display ─────────────────────────────────────────────────────────
    def _show_frame(self, pos: int):
        if not self.manager or not self._indices:
            return
        pos = max(0, min(pos, len(self._indices) - 1))
        self.current_index = pos
        idx = self._indices[pos]
        ann = self.manager.get_annotation(idx)
        frame = self.manager._read_frame_reliable(ann, idx) if ann else None
        self.canvas.set_image_bgr(frame)
        self.canvas.set_boxes(ann.boxes if ann else [], selected=-1)
        self.canvas.set_polygons(ann.polygons if ann else [])
        self.counter.setText(f"Frame {pos + 1} / {len(self._indices)}")
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(pos)
        self.frame_slider.blockSignals(False)
        self._refresh_box_list()

    def _refresh_box_list(self):
        self.box_list.blockSignals(True)
        self.box_list.clear()
        ann = self._current_ann()
        if ann:
            for i, b in enumerate(ann.boxes):
                src = "AUTO" if b.confidence < 1.0 else "MAN "
                self.box_list.addItem(f"[{i:02d}] {src} {b.class_name}")
        self.box_list.blockSignals(False)

    def _current_ann(self):
        if not self.manager or not self._indices:
            return None
        return self.manager.get_annotation(self._indices[self.current_index])

    def _nav(self, where):
        if not self._indices:
            return
        if where == "first":
            self._show_frame(0)
        elif where == "last":
            self._show_frame(len(self._indices) - 1)
        else:
            self._show_frame(self.current_index + int(where))

    def _on_slider(self, value):
        self._show_frame(value)

    # ── mode ──────────────────────────────────────────────────────────────────
    def _on_mode_change(self, index: int):
        self.canvas.set_mode({0: VIEW, 1: DRAW, 2: POLYGON}.get(index, VIEW))

    # ── box operations (mapped to AnnotationManager) ───────────────────────────
    def _class_id_for(self, name: str) -> int:
        name = name.strip() or "object"
        if name not in self._class_ids:
            self._class_ids[name] = len(self._class_ids)
        return self._class_ids[name]

    def _on_box_drawn(self, cx, cy, w, h):
        ann = self._current_ann()
        if not ann:
            return
        name = self.class_edit.text().strip() or "object"
        box = BoundingBox(self._class_id_for(name), name, cx, cy, w, h, 1.0)
        self.manager.add_box(ann.frame_index, box)
        self.canvas.set_boxes(ann.boxes, selected=len(ann.boxes) - 1)
        self._refresh_box_list()

    def _on_box_edited(self, index, cx, cy, w, h):
        # The canvas mutated the BoundingBox object in place; just refresh views.
        self._refresh_box_list()

    def _on_box_selected(self, index):
        self.box_list.blockSignals(True)
        self.box_list.setCurrentRow(index)
        self.box_list.blockSignals(False)

    def _on_list_row(self, row):
        self.canvas.set_selected(row)

    def _delete_selected_box(self):
        ann = self._current_ann()
        row = self.box_list.currentRow()
        if ann and 0 <= row < len(ann.boxes):
            self.manager.remove_box(ann.frame_index, row)
            self.canvas.set_boxes(ann.boxes, selected=-1)
            self._refresh_box_list()

    def _clear_frame(self):
        ann = self._current_ann()
        if ann:
            self.manager.clear_frame(ann.frame_index)
            self.canvas.set_boxes(ann.boxes, selected=-1)
            self._refresh_box_list()

    def _on_polygon_drawn(self, points):
        ann = self._current_ann()
        if not ann:
            return
        name = self.class_edit.text().strip() or "object"
        poly = PolygonAnnotation(self._class_id_for(name), name, points, 1.0)
        self.manager.add_polygon(ann.frame_index, poly)
        self.canvas.set_polygons(ann.polygons)

    def _classify_frame(self):
        ann = self._current_ann()
        if not ann:
            return
        name = self.class_edit.text().strip() or "object"
        self.manager.set_classification(
            ann.frame_index, ImageClassification(self._class_id_for(name), name, 1.0)
        )
        self._set_status(f"Frame classified as '{name}'.")

    # ── RT-DETR detection ─────────────────────────────────────────────────────
    def _run_detect(self):
        ann = self._current_ann()
        if not ann or self._busy:
            return
        self._set_busy(True, "Running RT-DETR on this frame…")
        self._worker = DetectWorker(self.manager, ann.frame_index, self.conf_spin.value())
        self._worker.done.connect(self._on_detect_one)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_detect_one(self, _idx):
        self._set_busy(False)
        self._show_frame(self.current_index)
        ann = self._current_ann()
        n = len(ann.boxes) if ann else 0
        self._seed_classes_from_model()
        self._set_status(f"RT-DETR: {n} object(s).")

    def _run_detect_all(self):
        if not self.manager or self._busy:
            return
        self._set_busy(True, "Running RT-DETR on all frames…")
        self._worker = DetectWorker(self.manager, None, self.conf_spin.value())
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_detect_all)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_detect_all(self, count):
        self._set_busy(False)
        self._seed_classes_from_model()
        self._show_frame(self.current_index)
        self._set_status(f"RT-DETR complete — {count}/{self.manager.total_count} annotated.")

    def _seed_classes_from_model(self):
        if self.manager:
            for cid, cname in self.manager.detector.class_names.items():
                self._class_ids.setdefault(cname, cid)

    def _on_conf_change(self):
        if self.manager:
            self.manager.detector.confidence = self.conf_spin.value()

    def _on_model_change(self, model: str):
        if self.manager and not self._busy:
            self._set_status(f"Model set to {model} (loads on next detect).")
            try:
                self.manager.detector.reload(model)
            except Exception as exc:      # noqa: BLE001
                QMessageBox.warning(self, "Model", f"Could not load '{model}':\n{exc}")

    # ── save / export ─────────────────────────────────────────────────────────
    def _save(self):
        if not self.manager:
            return
        self.manager.save_annotations()
        self._set_status("Annotations saved.")

    def _export(self):
        if not self.manager:
            return
        fmt, ok = QInputDialog.getItem(
            self, "Export dataset", "Format:", ["yolo", "coco"], 0, False
        )
        if not ok:
            return
        out = QFileDialog.getExistingDirectory(self, "Export destination")
        if not out:
            return
        try:
            summary = DatasetExporter(
                self.manager._annotations,
                self.manager.detector.class_names or {v: k for k, v in self._class_ids.items()},
                out,
            ).export(fmt)
            QMessageBox.information(
                self, "Export complete",
                f"Exported {summary.get('images', '?')} image(s) as {fmt.upper()} to:\n{out}",
            )
        except Exception as exc:          # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(exc))

    def _show_logs(self):
        logs_dir = os.path.join(os.getcwd(), "logs")
        QMessageBox.information(self, "Logs", f"Logs are written to:\n{logs_dir}")

    # ── helpers ───────────────────────────────────────────────────────────────
    def _on_progress(self, done, total):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def _set_busy(self, busy: bool, msg: str = ""):
        self._busy = busy
        self.progress.setVisible(busy)
        if busy:
            self.progress.setRange(0, 0)
            if msg:
                self._set_status(msg)
        else:
            self.progress.setRange(0, 100)

    def _on_worker_error(self, msg: str):
        self._set_busy(False)
        QMessageBox.critical(self, "Error", msg)
        self._set_status("Error — see dialog.")

    def _set_status(self, text: str):
        self.status.showMessage(text)
