"""
Right-hand panel with two tabs:
  AUTO  — RT-DETR confidence slider, run buttons
  MANUAL— class selector, box list, delete button
"""
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk

from models.annotation_model import BoundingBox
from utils.config import ACCENT, BG_DARK, BG_PANEL, RTDETR_DEFAULT_MODEL, RTDETR_MODELS, TEXT_LIGHT


class AnnotationPanel(tk.Frame):
    def __init__(
        self,
        master,
        on_detect_click:     Callable,
        on_detect_all_click: Callable,
        on_save_click:       Callable,
        on_clear_click:      Callable,
        on_delete_box:       Callable = None,   # callable(box_index)
        on_conf_change:      Callable = None,   # callable(float)
        on_model_change:     Callable = None,   # callable(model_name: str)
        on_box_select:       Callable = None,   # callable(box_index_or_None)
    ):
        super().__init__(master, bg=BG_PANEL, width=280)
        self.pack_propagate(False)

        self._on_detect      = on_detect_click
        self._on_detect_all  = on_detect_all_click
        self._on_save        = on_save_click
        self._on_clear       = on_clear_click
        self._on_delete_box  = on_delete_box
        self._on_conf_change = on_conf_change
        self._on_model_change = on_model_change
        self._on_box_select  = on_box_select
        self._syncing_selection = False

        # Current class names from the RT-DETR model
        self._class_names: dict[int, str] = {}

        # Manual annotation state
        self.selected_class_var = tk.StringVar(value="dog")
        self.custom_class_var   = tk.StringVar(value="")

        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build(self):
        # Header
        tk.Label(
            self, text="ANNOTATION PANEL",
            bg=BG_PANEL, fg=ACCENT,
            font=("Consolas", 10, "bold"),
        ).pack(pady=(10, 4))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8)

        # Notebook tabs
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Dark.TNotebook",
            background=BG_PANEL, borderwidth=0,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background=BG_DARK, foreground=TEXT_LIGHT,
            font=("Consolas", 9, "bold"),
            padding=[10, 4],
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", ACCENT)],
            foreground=[("selected", "white")],
        )

        nb = ttk.Notebook(self, style="Dark.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        auto_tab   = tk.Frame(nb, bg=BG_PANEL)
        manual_tab = tk.Frame(nb, bg=BG_PANEL)

        nb.add(auto_tab,   text="⚡ Auto (Detector)")
        nb.add(manual_tab, text="✏ Manual")

        self._build_auto_tab(auto_tab)
        self._build_manual_tab(manual_tab)

        # ── shared box list ───────────────────────────────────────────────────
        self._build_box_list()

        # ── bottom buttons ────────────────────────────────────────────────────
        self._build_bottom_buttons()

    def _build_auto_tab(self, parent):
        # ── Model selector ────────────────────────────────────────────────────
        tk.Label(
            parent, text="RT-DETR model  (auto-downloaded from HuggingFace)",
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 8),
        ).pack(pady=(10, 2), padx=10, anchor=tk.W)

        model_row = tk.Frame(parent, bg=BG_PANEL)
        model_row.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.model_var = tk.StringVar(value=RTDETR_DEFAULT_MODEL)
        self._model_combo = ttk.Combobox(
            model_row, textvariable=self.model_var,
            values=RTDETR_MODELS, font=("Consolas", 9), state="readonly", width=18,
        )
        self._model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self._model_combo.bind("<<ComboboxSelected>>",
                               lambda _e: self._on_model_selected())

        tk.Button(
            model_row, text="📂",
            command=self._browse_model,
            bg=BG_DARK, fg=TEXT_LIGHT, relief=tk.FLAT,
            padx=6, font=("Consolas", 10), cursor="hand2",
        ).pack(side=tk.LEFT, padx=(4, 0))

        # ── Confidence ────────────────────────────────────────────────────────
        tk.Label(
            parent, text="Confidence Threshold",
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 9),
        ).pack(pady=(4, 2), padx=10, anchor=tk.W)

        conf_row = tk.Frame(parent, bg=BG_PANEL)
        conf_row.pack(fill=tk.X, padx=10)

        self.conf_var = tk.DoubleVar(value=0.45)
        self.conf_label = tk.Label(
            conf_row, text="0.45",
            bg=BG_PANEL, fg=ACCENT, font=("Consolas", 10, "bold"), width=5,
        )
        self.conf_label.pack(side=tk.RIGHT)

        conf_slider = tk.Scale(
            conf_row, from_=0.1, to=0.95, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.conf_var,
            command=self._on_conf_slider,
            bg=BG_PANEL, fg=TEXT_LIGHT, troughcolor=BG_DARK,
            highlightthickness=0, sliderrelief=tk.FLAT, showvalue=False,
        )
        conf_slider.pack(fill=tk.X, side=tk.LEFT, expand=True)

        # Filter classes
        tk.Label(
            parent, text="Filter Classes (comma-sep, blank=all)",
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 8),
        ).pack(pady=(8, 2), padx=10, anchor=tk.W)

        self.filter_var = tk.StringVar(value="")
        tk.Entry(
            parent, textvariable=self.filter_var,
            bg=BG_DARK, fg=TEXT_LIGHT, insertbackground=TEXT_LIGHT,
            relief=tk.FLAT, font=("Consolas", 9),
        ).pack(fill=tk.X, padx=10, ipady=4)

        # Run buttons
        tk.Button(
            parent, text="⚡  Detect This Frame",
            command=self._on_detect,
            bg=ACCENT, fg="white", relief=tk.FLAT,
            padx=8, pady=6, font=("Consolas", 9, "bold"), cursor="hand2",
        ).pack(fill=tk.X, padx=10, pady=(12, 3))

        tk.Button(
            parent, text="🔁  Detect All Frames",
            command=self._on_detect_all,
            bg="#5a4fbf", fg="white", relief=tk.FLAT,
            padx=8, pady=6, font=("Consolas", 9, "bold"), cursor="hand2",
        ).pack(fill=tk.X, padx=10, pady=3)

    def _build_manual_tab(self, parent):
        tk.Label(
            parent, text="Select Class for New Box",
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 9),
        ).pack(pady=(10, 2), padx=10, anchor=tk.W)

        # Combobox (populated when the RT-DETR model loads)
        self.class_combo = ttk.Combobox(
            parent, textvariable=self.selected_class_var,
            font=("Consolas", 9), state="readonly",
        )
        self.class_combo.pack(fill=tk.X, padx=10, ipady=3)

        # Custom class override
        tk.Label(
            parent, text="  ─── or type custom class ───",
            bg=BG_PANEL, fg="#888899", font=("Consolas", 8),
        ).pack(pady=(6, 2))

        custom_row = tk.Frame(parent, bg=BG_PANEL)
        custom_row.pack(fill=tk.X, padx=10)

        tk.Entry(
            custom_row, textvariable=self.custom_class_var,
            bg=BG_DARK, fg=TEXT_LIGHT, insertbackground=TEXT_LIGHT,
            relief=tk.FLAT, font=("Consolas", 9),
        ).pack(fill=tk.X, ipady=4)

        tk.Label(
            parent,
            text=(
                "\n  HOW TO ANNOTATE:\n"
                "  1. Click '✏ Draw Box' above\n"
                "  2. Click & drag on the video\n"
                "  3. Box is added automatically\n"
                "  4. Navigate frames & repeat\n"
                "  5. Save when done"
            ),
            bg=BG_PANEL, fg="#8888aa",
            font=("Consolas", 8), justify=tk.LEFT,
        ).pack(pady=(10, 0), anchor=tk.W)

    def _build_box_list(self):
        separator_frame = tk.Frame(self, bg=BG_PANEL)
        separator_frame.pack(fill=tk.X, padx=8, pady=(4, 0))
        ttk.Separator(separator_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        tk.Label(
            self, text="DETECTED BOXES",
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 8, "bold"),
        ).pack(pady=(4, 2))

        list_frame = tk.Frame(self, bg=BG_PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set,
            bg=BG_DARK, fg=TEXT_LIGHT,
            selectbackground=ACCENT, selectforeground="white",
            font=("Consolas", 8), relief=tk.FLAT, bd=0, height=8,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        scrollbar.config(command=self.listbox.yview)

        self.stats_var = tk.StringVar(value="0 boxes")
        stats_row = tk.Frame(self, bg=BG_PANEL)
        stats_row.pack(fill=tk.X, padx=8, pady=(2, 0))

        tk.Label(
            stats_row, textvariable=self.stats_var,
            bg=BG_PANEL, fg=TEXT_LIGHT, font=("Consolas", 8),
        ).pack(side=tk.LEFT)

        tk.Button(
            stats_row, text="🗑 Delete Selected",
            command=self._delete_selected,
            bg="#7a3333", fg="white", relief=tk.FLAT,
            padx=6, pady=2, font=("Consolas", 8), cursor="hand2",
        ).pack(side=tk.RIGHT)

    def _build_bottom_buttons(self):
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        tk.Button(
            self, text="💾  Save Annotations",
            command=self._on_save,
            bg="#2d8a4e", fg="white", relief=tk.FLAT,
            padx=8, pady=6, font=("Consolas", 9, "bold"), cursor="hand2",
        ).pack(fill=tk.X, padx=8, pady=2)

        tk.Button(
            self, text="🗑  Clear Frame",
            command=self._on_clear,
            bg="#7a3333", fg="white", relief=tk.FLAT,
            padx=8, pady=6, font=("Consolas", 9, "bold"), cursor="hand2",
        ).pack(fill=tk.X, padx=8, pady=(2, 8))

    # ── model callbacks ───────────────────────────────────────────────────────
    def _on_model_selected(self):
        if self._on_model_change:
            self._on_model_change(self.model_var.get())

    def _browse_model(self):
        path = filedialog.askopenfilename(
            title="Select model weights",
            filetypes=[
                ("Model weights", "*.pt *.onnx"),
                ("PyTorch (Ultralytics/AGPL)", "*.pt"),
                ("ONNX (AGPL-free)", "*.onnx"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.model_var.set(path)
            current = list(self._model_combo["values"])
            if path not in current:
                self._model_combo["values"] = [path] + current
            if self._on_model_change:
                self._on_model_change(path)

    # ── callbacks ─────────────────────────────────────────────────────────────
    def _on_conf_slider(self, val):
        self.conf_label.config(text=f"{float(val):.2f}")
        if self._on_conf_change:
            self._on_conf_change(float(val))

    def _delete_selected(self):
        sel = self.listbox.curselection()
        if sel and self._on_delete_box:
            self._on_delete_box(sel[0])

    def _on_listbox_select(self, _event):
        if self._syncing_selection:
            return
        sel = self.listbox.curselection()
        idx = sel[0] if sel else None
        if self._on_box_select:
            self._on_box_select(idx)

    def set_selected_box(self, idx):
        """Sync listbox to match canvas selection (without re-firing callback)."""
        self._syncing_selection = True
        try:
            self.listbox.selection_clear(0, tk.END)
            if idx is not None and 0 <= idx < self.listbox.size():
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
        finally:
            self._syncing_selection = False

    # ── public API ────────────────────────────────────────────────────────────
    def update_boxes(self, boxes: list[BoundingBox], class_names: dict[int, str]):
        self._class_names = class_names

        # Update combobox values from the RT-DETR class names
        names = sorted(set(class_names.values())) if class_names else ["object"]
        self.class_combo["values"] = names
        if names and self.selected_class_var.get() not in names:
            self.selected_class_var.set(names[0])

        # Update listbox
        self.listbox.delete(0, tk.END)
        for i, box in enumerate(boxes):
            src  = "AUTO" if box.confidence < 1.0 else " MAN"
            conf = f"{box.confidence:.2f}" if box.confidence < 1.0 else "  — "
            self.listbox.insert(
                tk.END,
                f"  [{i:02d}] {src}  {box.class_name:<14} {conf}",
            )
        n = len(boxes)
        self.stats_var.set(f"{n} box{'es' if n != 1 else ''}")

    def get_selected_class(self) -> str:
        """Return custom class if typed, otherwise combo selection."""
        custom = self.custom_class_var.get().strip()
        return custom if custom else self.selected_class_var.get()

    def get_confidence_threshold(self) -> float:
        return float(self.conf_var.get())

    def get_model_name(self) -> str:
        return self.model_var.get()

    def get_class_filter(self) -> list[str]:
        """Return list of class names to keep, or [] for all."""
        raw = self.filter_var.get().strip()
        if not raw:
            return []
        return [c.strip().lower() for c in raw.split(",") if c.strip()]
