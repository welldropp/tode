"""Root application frame — supports video, image, and image-folder sources."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from core.annotation_manager import AnnotationManager
from core.auto_annotator import AutoAnnotator
from core.exporter import DatasetExporter
from core.frame_extractor import FrameExtractor
from core.image_frame_extractor import ImageFrameExtractor
from core.image_loader import ImageLoader
from core.video_loader import VideoLoader
from models.annotation_model import BoundingBox
from storage.frame_storage import FrameStorage
from storage.label_storage import LabelStorage
from ui.annotation_panel import AnnotationPanel
from ui.export_dialog import ExportDialog
from ui.log_viewer import LogViewer
from ui.segmentation_panel import SegmentationPanel
from ui.source_dialog import SourceDialog
from ui.video_player import VideoPlayer
from utils.config import ACCENT, BG_DARK, BG_PANEL, TEXT_LIGHT
from utils.logger import get_logger

log = get_logger("ui.MainWindow")

_SOURCE_LABELS = {
    "video":        "🎬 Video",
    "image":        "🖼 Image",
    "image_folder": "📂 Image Folder",
}

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def _find_images_recursive(folder: str):
    """
    Scan folder AND all subfolders for supported image files.
    Returns sorted list of absolute paths.
    """
    found = []
    for root, dirs, files in os.walk(folder):
        # Sort dirs so traversal is deterministic
        dirs.sort()
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                found.append(os.path.join(root, f))
    return found


class MainWindow(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG_DARK)
        self.manager: AnnotationManager | None = None
        self._busy        = False
        self._log_viewer  = None
        self._source_type = None
        self._build_ui()
        log.info("MainWindow initialised")

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_toolbar()

        content = tk.Frame(self, bg=BG_DARK)
        content.pack(fill=tk.BOTH, expand=True)

        self.player = VideoPlayer(
            content,
            on_frame_change=self._on_frame_change,
            on_box_drawn=self._on_box_drawn,
            on_open_request=self._open_source,
            on_box_edited=self._on_box_edited,
            on_box_selected=self._on_box_selected_in_canvas,
            on_polygon_drawn=self._on_polygon_drawn,
            on_mode_change=self._on_mode_change,
        )
        self.player.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                         padx=6, pady=6)

        self.ann_panel = AnnotationPanel(
            content,
            on_detect_click     = self._run_detect,
            on_detect_all_click = self._run_detect_all,
            on_save_click     = self._save,
            on_clear_click    = self._clear_frame,
            on_delete_box     = self._delete_box,
            on_conf_change    = self._on_conf_change,
            on_model_change   = self._on_model_change,
            on_box_select     = self._on_box_selected_in_list,
        )
        self.ann_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)

        # ── semantic segmentation panel (hidden until polygon mode) ────────
        self._class_color_map: dict[str, str] = {}
        self.seg_panel = SegmentationPanel(
            content,
            on_save_click     = self._save,
            on_clear_click    = self._clear_seg_frame,
            on_delete_poly    = self._delete_polygon,
            on_poly_select    = self._on_poly_selected,
            on_class_changed  = self._on_seg_class_changed,
            on_opacity_change = self._on_seg_opacity_changed,
        )
        # seg_panel is shown/hidden by the polygon mode button in video_player
        self.seg_panel.pack_forget()

        self._build_status()
        self._build_progress()
        self._bind_shortcuts()

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG_PANEL, height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        def btn(text, cmd, color=ACCENT):
            b = tk.Button(
                bar, text=text, command=cmd,
                bg=color, fg="white", relief=tk.FLAT,
                padx=12, pady=6, font=("Consolas", 9, "bold"),
                activebackground="#9d8fff", cursor="hand2",
            )
            b.pack(side=tk.LEFT, padx=3, pady=6)
            return b

        btn("📂  Open",       self._open_source)
        btn("🎬  Video",      self._open_video_direct)
        btn("🖼  Image",      self._open_image_direct)
        btn("💾  Save",       self._save,               color="#2d7a4e")
        btn("⚡  Detect Frame", self._run_detect)
        btn("🔁  Detect All",   self._run_detect_all,     color="#5a4fbf")
        btn("📤  Export",    self._export_dataset,     color="#1f7a8c")
        btn("📋  Logs",       self._show_logs,           color="#3a4a6a")

        self._source_badge = tk.Label(
            bar, text="  No source",
            bg=BG_PANEL, fg="#666688",
            font=("Consolas", 8, "italic"),
        )
        self._source_badge.pack(side=tk.RIGHT, padx=10)

    def _build_status(self):
        self.status_var = tk.StringVar(
            value="No source loaded. Click 📂 Open or choose a source type."
        )
        bar = tk.Frame(self, bg=BG_PANEL, height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Label(
            bar, textvariable=self.status_var,
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 9),
        ).pack(side=tk.LEFT, padx=10)

    def _build_progress(self):
        from tkinter import ttk
        pf = tk.Frame(self, bg=BG_PANEL, height=6)
        pf.pack(fill=tk.X, side=tk.BOTTOM)
        pf.pack_propagate(False)
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "App.Horizontal.TProgressbar",
            troughcolor=BG_PANEL, background=ACCENT, thickness=6,
        )
        self._progress = ttk.Progressbar(
            pf, mode="indeterminate",
            style="App.Horizontal.TProgressbar",
        )
        self._progress_visible = False

    # ── keyboard shortcuts (labelImg-style) ───────────────────────────────────
    def _bind_shortcuts(self):
        """
        labelImg-style bindings. Bound at the root so they fire regardless
        of which widget has focus.
        """
        root = self.master
        mappings = {
            # Navigation
            "<Left>":         lambda _e: self._nav(-1),
            "a":              lambda _e: self._nav(-1),
            "A":              lambda _e: self._nav(-1),
            "<Right>":        lambda _e: self._nav(+1),
            "d":              lambda _e: self._nav(+1),
            "D":              lambda _e: self._nav(+1),
            "<Home>":         lambda _e: self._nav("first"),
            "<End>":          lambda _e: self._nav("last"),
            # Mode switching
            "w":              lambda _e: self.player.set_draw_mode(),
            "W":              lambda _e: self.player.set_draw_mode(),
            "v":              lambda _e: self.player.set_view_mode(),
            "V":              lambda _e: self.player.set_view_mode(),
            "<Escape>":       lambda _e: self.player.set_view_mode(),
            # Actions
            "<Control-s>":    lambda _e: self._save(),
            "<Control-S>":    lambda _e: self._save(),
            "<Control-e>":    lambda _e: self._export_dataset(),
            "<Control-E>":    lambda _e: self._export_dataset(),
            "<Control-o>":    lambda _e: self._open_source(),
            "<Control-O>":    lambda _e: self._open_source(),
            "<Delete>":       lambda _e: self._clear_frame(),
            # RT-DETR auto-detect
            "y":              lambda _e: self._run_detect(),
            "Y":              lambda _e: self._run_detect(),
        }
        for key, fn in mappings.items():
            root.bind(key, fn)
        log.debug("Keyboard shortcuts bound (labelImg-style)")

    def _nav(self, where):
        """Move slider — accepts -1, +1, 'first', 'last'."""
        if where == "first":
            self.player._go_first()
        elif where == "last":
            self.player._go_last()
        elif where == -1:
            self.player._prev()
        elif where == +1:
            self.player._next()

    # ── progress ──────────────────────────────────────────────────────────────
    def _show_progress(self):
        if not self._progress_visible:
            self._progress.pack(fill=tk.X)
            self._progress.start(12)
            self._progress_visible = True

    def _hide_progress(self):
        if self._progress_visible:
            self._progress.stop()
            self._progress.pack_forget()
            self._progress_visible = False

    def _run_in_thread(self, task_fn, done_fn=None, error_fn=None):
        self._busy = True
        self._show_progress()

        def _worker():
            try:
                result = task_fn()
                if done_fn:
                    self.after(0, lambda r=result: done_fn(r))
            except Exception as exc:
                # FIX: Python 3.13 lambda scoping bug — capture exc explicitly
                _exc = exc
                log.error(f"Background task error: {_exc}", exc_info=True)
                if error_fn:
                    self.after(0, lambda e=_exc: error_fn(e))
                else:
                    self.after(
                        0, lambda e=_exc: messagebox.showerror("Error", str(e))
                    )
            finally:
                self.after(0, self._task_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _task_done(self):
        self._busy = False
        self._hide_progress()

    # ── open source actions ───────────────────────────────────────────────────
    def _open_source(self):
        """Unified tabbed source dialog."""
        if self._busy:
            return
        dlg = SourceDialog(self.master)
        if dlg.result:
            self._load_from_result(dlg.result)

    def _open_video_direct(self):
        """Quick-open a video file."""
        if self._busy:
            return
        path = filedialog.askopenfilename(
            title="Open Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.webm *.flv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._load_from_result({"type": "video", "path": path, "step": 1})

    def _open_image_direct(self):
        """Quick-open a single image or image folder."""
        if self._busy:
            return

        win = tk.Toplevel(self.master)
        win.title("Open Image")
        win.configure(bg=BG_DARK)
        win.resizable(False, False)
        win.grab_set()
        win.focus_set()

        result = {"type": None, "path": None}

        tk.Label(
            win, text="What do you want to open?",
            bg=BG_DARK, fg=TEXT_LIGHT,
            font=("Consolas", 11, "bold"),
        ).pack(pady=(20, 10), padx=24)

        def _pick_image():
            path = filedialog.askopenfilename(
                title="Select Image", parent=win,
                filetypes=[
                    ("Image files",
                     "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                result["type"] = "image"
                result["path"] = path
                win.destroy()

        def _pick_folder():
            path = filedialog.askdirectory(
                title="Select Image Folder", parent=win
            )
            if path:
                result["type"] = "image_folder"
                result["path"] = path
                win.destroy()

        btn_cfg = dict(
            bg=ACCENT, fg="white", relief=tk.FLAT,
            padx=20, pady=10,
            font=("Consolas", 10, "bold"),
            cursor="hand2",
        )
        tk.Button(win, text="🖼   Single Image",
                  command=_pick_image, **btn_cfg).pack(
            fill=tk.X, padx=24, pady=4)
        tk.Button(win, text="📂   Image Folder",
                  command=_pick_folder, **btn_cfg).pack(
            fill=tk.X, padx=24, pady=4)
        tk.Button(win, text="Cancel",
                  command=win.destroy,
                  bg="#444455", fg="white", relief=tk.FLAT,
                  padx=20, pady=8,
                  font=("Consolas", 9),
                  cursor="hand2").pack(pady=(4, 16), padx=24, fill=tk.X)

        win.wait_window()

        if result["path"]:
            self._load_from_result(result)

    # ── unified loader dispatcher ─────────────────────────────────────────────
    def _load_from_result(self, result: dict):
        src_type = result["type"]
        path     = result["path"]
        self._source_type = src_type
        self._update_badge(src_type)
        log.info(f"Loading source — type={src_type}, path={path}")

        if src_type == "video":
            self._load_video(path, step=result.get("step", 1))
        elif src_type in ("image", "image_folder"):
            self._load_images(path)

    # ── video loader ──────────────────────────────────────────────────────────
    def _load_video(self, path: str, step: int = 1):
        self._set_status(f"Opening video: {os.path.basename(path)}…")

        def _on_bg_progress(done, total):
            pct = (100 * done) // max(1, total)
            self.after(0, lambda d=done, t=total, p=pct: self._set_status(
                f"Extracting frames in background… {d}/{t} ({p}%)"
                if d < t else f"All {t} frames extracted."
            ))

        def _work():
            loader    = VideoLoader(path)
            loader.open()
            extractor = FrameExtractor(loader, step=step, save_frames=True)
            detector  = AutoAnnotator()
            vname = os.path.splitext(os.path.basename(path))[0]
            mgr   = AnnotationManager(
                loader, extractor, detector,
                FrameStorage(vname),
                LabelStorage(vname),
            )
            mgr.load_video(on_progress=_on_bg_progress)
            mgr.load_existing_labels()
            return mgr

        def _done(mgr: AnnotationManager):
            self.manager = mgr
            self.player.load(
                mgr.loader, mgr.all_frame_indices(),
                frame_path_provider=self._frame_path_for,
            )
            self._set_status(
                f"Video ready — '{os.path.basename(path)}'  "
                f"| {mgr.loader.total_frames} frames "
                f"| {mgr.loader.fps:.0f} fps  "
                f"(frames extract in background — start annotating now)"
            )

        def _err(exc):
            messagebox.showerror("Video Load Error", str(exc))
            self._set_status("Failed to load video.")

        self._run_in_thread(_work, _done, _err)

    # ── image loader ──────────────────────────────────────────────────────────
    def _load_images(self, path: str):
        is_folder = os.path.isdir(path)
        label     = "folder" if is_folder else "image"
        self._set_status(f"Loading {label}: {os.path.basename(path)}…")
        log.info(f"Loading images — is_folder={is_folder}, path={path}")

        def _work():
            # ── FIX: if folder has no images at root, scan subfolders ─────────
            if is_folder:
                all_images = _find_images_recursive(path)
                if not all_images:
                    raise FileNotFoundError(
                        f"No images found in folder or subfolders:\n{path}\n\n"
                        f"Supported formats: JPG, PNG, BMP, TIFF, WEBP\n\n"
                        f"Make sure your images are inside the selected folder."
                    )
                log.info(f"Found {len(all_images)} image(s) in: {path}")

            loader = ImageLoader(path)
            loader.open()

            if loader.total_frames == 0:
                raise ValueError(
                    "No supported images found.\n"
                    "Supported formats: JPG, PNG, BMP, TIFF, WEBP"
                )

            extractor = ImageFrameExtractor(loader, copy_files=True)
            detector  = AutoAnnotator()

            src_name = (
                os.path.basename(path.rstrip("/\\")) or "images"
            )
            # Sanitise name for use as directory
            src_name = "".join(
                c if c.isalnum() or c in "-_." else "_"
                for c in src_name
            )

            mgr = AnnotationManager(
                loader, extractor, detector,
                FrameStorage(src_name),
                LabelStorage(src_name),
            )
            self.after(0, lambda: self._set_status(
                f"Processing {loader.total_frames} image(s)…"
            ))
            mgr.load_video()           # duck-typed — works for images too
            mgr.load_existing_labels()
            return mgr

        def _done(mgr: AnnotationManager):
            self.manager = mgr
            indices = mgr.all_frame_indices()
            self.player.load(
                mgr.loader, indices,
                frame_path_provider=self._frame_path_for,
            )
            noun = "images" if is_folder else "image"
            self._set_status(
                f"{'Folder' if is_folder else 'Image'} loaded — "
                f"'{os.path.basename(path)}'  |  {len(indices)} {noun}"
            )
            log.info(f"Image source ready — {len(indices)} item(s)")

        def _err(exc):
            log.error(f"Image load error: {exc}", exc_info=True)
            messagebox.showerror(
                "Image Load Error",
                f"Could not load:\n{path}\n\n{exc}",
            )
            self._set_status("Failed to load image source.")

        self._run_in_thread(_work, _done, _err)

    # ── frame change callback ─────────────────────────────────────────────────
    def _on_frame_change(self, frame_index: int, bgr_frame):
        if self.manager is None:
            return
        ann      = self.manager.get_annotation(frame_index)
        boxes    = ann.boxes    if ann else []
        polygons = ann.polygons if ann else []
        self.player.set_overlay_boxes(boxes)
        self.player.set_overlay_polygons(polygons)
        self.ann_panel.update_boxes(boxes, self.manager.detector.class_names)
        # refresh seg panel polygon list
        class_names = list(self.manager.detector.class_names.values())
        self.seg_panel.update_polygons(polygons, class_names)
        self._sync_color_map()

    # ── mode change callback (panel swap) ─────────────────────────────────────
    def _on_mode_change(self, mode: str) -> None:
        """Show the segmentation panel in polygon mode; bbox panel otherwise."""
        if mode == "polygon":
            self.ann_panel.pack_forget()
            self.seg_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)
            # seed class names from the RT-DETR model if available
            if self.manager:
                self.seg_panel.set_class_names(
                    list(self.manager.detector.class_names.values())
                )
        else:
            self.seg_panel.pack_forget()
            self.ann_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)

    # ── polygon drawn callback ────────────────────────────────────────────────
    def _on_polygon_drawn(self, points: list):
        if self.manager is None:
            return
        from models.annotation_model import PolygonAnnotation
        idx      = self.player.current_frame_index
        # Use class from seg_panel (semantic) if polygon mode active
        cls_name = self.seg_panel.get_selected_class()
        class_names = self.manager.detector.class_names
        cls_id   = next(
            (k for k, v in class_names.items()
             if v.lower() == cls_name.lower()), 0
        )
        poly = PolygonAnnotation(
            class_id=cls_id, class_name=cls_name, points=points
        )
        self.manager.add_polygon(idx, poly)
        ann = self.manager.get_annotation(idx)
        self.player.set_overlay_polygons(ann.polygons)
        self._sync_color_map()
        self.seg_panel.update_polygons(
            ann.polygons, list(class_names.values())
        )
        self._set_status(
            f"Polygon added to frame {idx} — '{cls_name}', "
            f"{len(points)} pts. Total: {len(ann.polygons)} polygon(s)."
        )

    # ── seg panel callbacks ───────────────────────────────────────────────────

    def _on_seg_class_changed(self, class_name: str, color: str) -> None:
        """Called when user picks a different semantic class in seg_panel."""
        self._class_color_map[class_name] = color
        self.player.set_active_poly_color(color)
        self.player.set_class_color_map(dict(self._class_color_map))

    def _on_seg_opacity_changed(self, value: float) -> None:
        self.player.set_poly_opacity(value)

    def _on_poly_selected(self, index: int | None) -> None:
        """Highlight the selected polygon in the canvas (future use)."""
        pass

    def _delete_polygon(self, poly_index: int) -> None:
        if not self._require_manager():
            return
        idx = self.player.current_frame_index
        self.manager.remove_polygon(idx, poly_index)
        ann = self.manager.get_annotation(idx)
        self.player.set_overlay_polygons(ann.polygons)
        self.seg_panel.update_polygons(
            ann.polygons, list(self.manager.detector.class_names.values())
        )
        self._set_status(f"Deleted polygon [{poly_index}] from frame {idx}.")

    def _clear_seg_frame(self) -> None:
        """Clear all polygons on the current frame."""
        if not self._require_manager():
            return
        idx = self.player.current_frame_index
        self.manager.clear_polygons(idx)
        ann = self.manager.get_annotation(idx)
        self.player.set_overlay_polygons(ann.polygons)
        self.seg_panel.update_polygons([], [])
        self._set_status(f"Cleared all polygons on frame {idx}.")

    def _sync_color_map(self) -> None:
        """Push current class→colour mapping into the canvas."""
        # merge seg_panel class colours into the map
        for cls in self.seg_panel._classes:
            self._class_color_map[cls["name"]] = cls["color"]
        self.player.set_class_color_map(dict(self._class_color_map))

    # ── manual box drawn ──────────────────────────────────────────────────────
    def _on_box_drawn(self, x1_n: float, y1_n: float,
                      x2_n: float, y2_n: float):
        if self.manager is None:
            return

        cls_name    = self.ann_panel.get_selected_class()
        class_names = self.manager.detector.class_names
        cls_id      = next(
            (k for k, v in class_names.items()
             if v.lower() == cls_name.lower()), 0
        )

        box = BoundingBox(
            class_id   = cls_id,
            class_name = cls_name,
            x_center   = (x1_n + x2_n) / 2,
            y_center   = (y1_n + y2_n) / 2,
            width      = x2_n - x1_n,
            height     = y2_n - y1_n,
            confidence = 1.0,
        )

        idx = self.player.current_frame_index
        self.manager.add_box(idx, box)

        ann = self.manager.get_annotation(idx)
        self.player.set_overlay_boxes(ann.boxes)
        self.ann_panel.update_boxes(ann.boxes, self.manager.detector.class_names)
        src_label = (
            "image" if self._source_type in ("image", "image_folder")
            else "frame"
        )
        self._set_status(
            f"Manual box added — '{cls_name}' on {src_label} {idx}. "
            f"Total: {len(ann.boxes)} box(es)."
        )

    # ── box edit / select callbacks ───────────────────────────────────────────
    def _on_box_edited(self, box_index: int,
                       x1_n: float, y1_n: float,
                       x2_n: float, y2_n: float):
        if self.manager is None:
            return
        idx = self.player.current_frame_index
        ann = self.manager.get_annotation(idx)
        if not ann or box_index >= len(ann.boxes):
            return
        box = ann.boxes[box_index]
        box.x_center = (x1_n + x2_n) / 2
        box.y_center = (y1_n + y2_n) / 2
        box.width    = x2_n - x1_n
        box.height   = y2_n - y1_n
        ann.is_annotated = bool(ann.boxes)
        self.ann_panel.update_boxes(ann.boxes, self.manager.detector.class_names)
        self._set_status(
            f"Edited box [{box_index}] — '{box.class_name}' "
            f"({box.width:.2f}×{box.height:.2f})"
        )

    def _on_box_selected_in_canvas(self, box_index):
        """Sync canvas → listbox highlight."""
        self.ann_panel.set_selected_box(box_index)

    def _on_box_selected_in_list(self, box_index):
        """Sync listbox → canvas highlight."""
        self.player.set_selected_box(box_index)

    # ── delete selected box ───────────────────────────────────────────────────
    def _delete_box(self, box_index: int):
        if not self._require_manager():
            return
        idx = self.player.current_frame_index
        self.manager.remove_box(idx, box_index)
        ann = self.manager.get_annotation(idx)
        self.player.set_overlay_boxes(ann.boxes)
        self.ann_panel.update_boxes(ann.boxes, self.manager.detector.class_names)
        self._set_status(f"Deleted box [{box_index}] from index {idx}.")

    # ── confidence change ─────────────────────────────────────────────────────
    def _on_conf_change(self, val: float):
        if self.manager:
            self.manager.detector.confidence = val
            log.debug(f"Confidence updated → {val:.2f}")

    # ── model change ──────────────────────────────────────────────────────────
    def _on_model_change(self, model: str):
        detector = self.manager.detector if self.manager else None
        target = detector or AutoAnnotator()
        self._set_status(f"Loading model '{model}'…")
        log.info(f"Model change requested → {model}")

        def _work():
            if self.manager:
                self.manager.detector.reload(model)
            else:
                target.reload(model)

        def _done(_):
            name = model.split("/")[-1].split("\\")[-1]
            self._set_status(f"Model ready: {name}")

        def _err(exc):
            messagebox.showerror("Model Load Error",
                                 f"Could not load '{model}':\n{exc}")
            self._set_status("Model load failed.")

        self._run_in_thread(_work, _done, _err)

    # ── RT-DETR single frame ──────────────────────────────────────────────────
    def _run_detect(self):
        if not self._require_manager() or self._busy:
            return
        idx        = self.player.current_frame_index
        conf       = self.ann_panel.get_confidence_threshold()
        cls_filter = self.ann_panel.get_class_filter()
        self.manager.detector.confidence = conf
        self._set_status(f"Running RT-DETR on index {idx}…")
        log.info(f"RT-DETR single — idx={idx}, conf={conf}, filter={cls_filter}")

        def _work():
            ann = self.manager.auto_annotate_frame(idx)
            if cls_filter:
                ann.boxes = [
                    b for b in ann.boxes
                    if b.class_name.lower() in cls_filter
                ]
                ann.is_annotated = bool(ann.boxes)
            return ann

        def _done(ann):
            self.player.set_overlay_boxes(ann.boxes)
            self.ann_panel.update_boxes(
                ann.boxes, self.manager.detector.class_names
            )
            self._set_status(
                f"RT-DETR: {len(ann.boxes)} object(s) at index {idx}."
            )

        self._run_in_thread(_work, _done)

    # ── RT-DETR all frames ────────────────────────────────────────────────────
    def _run_detect_all(self):
        if not self._require_manager() or self._busy:
            return
        total      = self.manager.total_count
        conf       = self.ann_panel.get_confidence_threshold()
        cls_filter = self.ann_panel.get_class_filter()
        self.manager.detector.confidence = conf
        self._set_status("Running RT-DETR on all…")
        log.info(f"RT-DETR all — conf={conf}, filter={cls_filter}")

        def _progress(done, tot):
            self.after(0, lambda d=done, t=tot: self._set_status(
                f"RT-DETR annotating… {d}/{t}"
            ))

        def _work():
            self.manager.auto_annotate_all(progress_callback=_progress)
            if cls_filter:
                for ann in self.manager._annotations.values():
                    ann.boxes = [
                        b for b in ann.boxes
                        if b.class_name.lower() in cls_filter
                    ]
                    ann.is_annotated = bool(ann.boxes)
            return self.manager.annotated_count

        def _done(count):
            self._set_status(
                f"RT-DETR complete — {count}/{total} annotated."
            )

        self._run_in_thread(_work, _done)

    # ── save annotations ──────────────────────────────────────────────────────
    def _save(self):
        if not self._require_manager() or self._busy:
            return
        self._set_status("Saving annotations…")

        def _work():
            self.manager.save_annotations()
            return self.manager.annotated_count

        def _done(count):
            self._set_status(f"Saved {count} annotation file(s).")

        self._run_in_thread(_work, _done)

    # ── export dataset ────────────────────────────────────────────────────────
    def _export_dataset(self):
        if not self._require_manager() or self._busy:
            return
        if self.manager.annotated_count == 0:
            messagebox.showinfo(
                "Nothing to export",
                "No annotated frames yet. Annotate at least one frame, "
                "then export.",
            )
            return

        # Default to ~/Documents/labeled_img/<source_name>/ so exported
        # datasets land somewhere users can find easily.
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        if not os.path.isdir(docs):
            docs = os.path.expanduser("~")
        src_name = self.manager.f_store.video_name or "dataset"
        default_out = os.path.join(docs, "labeled_img", src_name)
        dlg = ExportDialog(self.master, default_dir=default_out)
        if not dlg.result:
            return

        fmt     = dlg.result["format"]
        out_dir = dlg.result["output_dir"]
        self._set_status(f"Exporting as {fmt.upper()} → {out_dir}…")
        log.info(f"Export started — fmt={fmt}, out={out_dir}")

        exporter = DatasetExporter(
            annotations = self.manager._annotations,
            class_names = self.manager.detector.class_names,
            output_dir  = out_dir,
        )

        def _progress(done, total):
            self.after(0, lambda d=done, t=total: self._set_status(
                f"Exporting… {d}/{t}"
            ))

        def _work():
            return exporter.export(fmt=fmt, progress_callback=_progress)

        def _done(summary: dict):
            self._set_status(
                f"Export complete — {summary['images']} images, "
                f"{summary['labels']} labels, "
                f"{len(summary['classes'])} class(es) → {summary['output_dir']}"
            )
            messagebox.showinfo(
                "Export complete",
                f"Format : {summary['format'].upper()}\n"
                f"Images : {summary['images']}\n"
                f"Labels : {summary['labels']}\n"
                f"Classes: {', '.join(summary['classes'])}\n\n"
                f"Saved to:\n{summary['output_dir']}",
            )

        def _err(exc):
            messagebox.showerror("Export Error", str(exc))
            self._set_status("Export failed.")

        self._run_in_thread(_work, _done, _err)

    # ── clear current frame ───────────────────────────────────────────────────
    def _clear_frame(self):
        if not self._require_manager():
            return
        idx = self.player.current_frame_index
        self.manager.clear_frame(idx)
        self.player.set_overlay_boxes([])
        self.ann_panel.update_boxes([], {})
        self._set_status(f"Cleared annotations for index {idx}.")

    # ── log viewer ────────────────────────────────────────────────────────────
    def _show_logs(self):
        if self._log_viewer is None or not self._log_viewer.winfo_exists():
            self._log_viewer = LogViewer(self.master)
            log.info("Log viewer opened")
        else:
            self._log_viewer.deiconify()
            self._log_viewer.lift()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _frame_path_for(self, frame_index: int) -> str:
        """Resolve the on-disk PNG path for a frame index, or '' if missing."""
        if self.manager is None:
            return ""
        ann = self.manager.get_annotation(frame_index)
        return ann.frame_path if ann else ""

    def _require_manager(self) -> bool:
        if self.manager is None:
            messagebox.showinfo("No source",
                                "Please open a source first.")
            return False
        return True

    def _set_status(self, msg: str):
        self.status_var.set(msg)
        log.info(f"[STATUS] {msg}")
        self.update_idletasks()

    def _update_badge(self, src_type: str):
        label = _SOURCE_LABELS.get(src_type, src_type)
        self._source_badge.config(text=f"  Source: {label}  ")

    def setup_drag_drop(self):
        _VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
        self.master.drop_target_register("DND_Files")  # type: ignore[attr-defined]

        def _on_drop(event):
            raw = event.data.strip()
            # tkinterdnd2 wraps paths containing spaces in { }
            if raw.startswith("{") and raw.endswith("}"):
                path = raw[1:-1]
            else:
                path = raw.split()[0]
            ext = os.path.splitext(path)[1].lower()
            if ext in _VIDEO_EXTS:
                self._load_from_result({"type": "video", "path": path, "step": 1})
            elif ext in SUPPORTED_EXTS:
                self._load_from_result({"type": "image", "path": path, "step": 1})
            elif os.path.isdir(path):
                self._load_from_result({"type": "image_folder", "path": path, "step": 1})
            else:
                log.warning(f"Dropped file has unsupported type: {path}")

        self.master.dnd_bind("<<Drop>>", _on_drop)  # type: ignore[attr-defined]

    def on_close(self):
        log.info("Application closing — releasing resources")
        if self.manager:
            self.manager.loader.release()
        self.master.destroy()

