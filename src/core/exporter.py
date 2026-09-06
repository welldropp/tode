"""
core/exporter.py
─────────────────
Exports annotated frames + labels in either YOLO or COCO format.

Only frames where ``is_annotated == True`` are exported.
Non-annotated frames are skipped entirely.
"""
import json
import os
import shutil
from collections.abc import Callable
from datetime import datetime

from models.annotation_model import FrameAnnotation
from utils.logger import get_logger

log = get_logger("core.DatasetExporter")


class DatasetExporter:
    """
    Parameters
    ----------
    annotations    : dict[int, FrameAnnotation]  — output of AnnotationManager
    class_names    : dict[int, str]              — id → name (e.g. YOLO model names)
    output_dir     : str                         — destination root folder
    """

    def __init__(
        self,
        annotations: dict[int, FrameAnnotation],
        class_names: dict[int, str],
        output_dir:  str,
    ):
        self.annotations = annotations
        self.class_names = class_names or {}
        self.output_dir  = output_dir

    # ── public API ────────────────────────────────────────────────────────────
    def export(
        self,
        fmt: str = "yolo",
        progress_callback: Callable | None = None,
    ) -> dict:
        """
        Returns a summary dict: {format, output_dir, images, labels, classes}.
        Raises ValueError on unknown format.
        """
        annotated = [
            a for a in self.annotations.values()
            if a.is_annotated and a.boxes and a.frame_path
        ]
        if not annotated:
            raise ValueError(
                "Nothing to export — no annotated frames found. "
                "Annotate at least one frame first."
            )

        os.makedirs(self.output_dir, exist_ok=True)

        fmt = fmt.lower().strip()
        if fmt == "yolo":
            return self._export_yolo(annotated, progress_callback)
        if fmt == "coco":
            return self._export_coco(annotated, progress_callback)
        raise ValueError(f"Unknown export format: {fmt!r}")

    # ── YOLO ──────────────────────────────────────────────────────────────────
    def _export_yolo(
        self,
        annotated: list[FrameAnnotation],
        progress_callback: Callable | None,
    ) -> dict:
        img_dir = os.path.join(self.output_dir, "images")
        lbl_dir = os.path.join(self.output_dir, "labels")
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)

        class_id_map = self._build_class_id_map(annotated)
        ordered = sorted(class_id_map.items(), key=lambda kv: kv[1])
        ordered_names = [name for name, _ in ordered]

        # Sequential 1-based numbering so files line up:
        #   images/img_1.png  ↔  labels/img_1.txt
        #   images/img_2.png  ↔  labels/img_2.txt
        # Sorted by original frame_index so order is deterministic.
        ordered_anns = sorted(annotated, key=lambda a: a.frame_index)

        total = len(ordered_anns)
        for seq, ann in enumerate(ordered_anns, start=1):
            src = ann.frame_path
            if not os.path.exists(src):
                log.warning(f"Frame missing on disk, skipping: {src}")
                continue
            ext     = os.path.splitext(src)[1].lower() or ".png"
            stem    = f"img_{seq}"
            dst_img = os.path.join(img_dir, stem + ext)
            shutil.copy2(src, dst_img)

            lbl_path = os.path.join(lbl_dir, stem + ".txt")
            with open(lbl_path, "w") as f:
                for box in ann.boxes:
                    cid = class_id_map[box.class_name]
                    f.write(
                        f"{cid} {box.x_center:.6f} {box.y_center:.6f} "
                        f"{box.width:.6f} {box.height:.6f}\n"
                    )

            if progress_callback:
                progress_callback(seq, total)

        # classes.txt + data.yaml
        with open(os.path.join(self.output_dir, "classes.txt"), "w") as f:
            f.write("\n".join(ordered_names) + "\n")

        yaml_path = os.path.join(self.output_dir, "data.yaml")
        with open(yaml_path, "w") as f:
            f.write(f"path: {os.path.abspath(self.output_dir)}\n")
            f.write("train: images\n")
            f.write("val: images\n")
            f.write(f"nc: {len(ordered_names)}\n")
            f.write("names:\n")
            for n in ordered_names:
                f.write(f"  - {n}\n")

        log.info(
            f"YOLO export complete — {total} images, "
            f"{len(ordered_names)} classes → {self.output_dir}"
        )
        return {
            "format":     "yolo",
            "output_dir": self.output_dir,
            "images":     total,
            "labels":     total,
            "classes":    ordered_names,
        }

    # ── COCO ──────────────────────────────────────────────────────────────────
    def _export_coco(
        self,
        annotated: list[FrameAnnotation],
        progress_callback: Callable | None,
    ) -> dict:
        import cv2  # local import — cv2 not needed for YOLO export

        img_dir = os.path.join(self.output_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        class_id_map = self._build_class_id_map(annotated)
        ordered = sorted(class_id_map.items(), key=lambda kv: kv[1])
        categories = [
            {"id": cid + 1, "name": name, "supercategory": "object"}
            for name, cid in ordered
        ]

        images_json: list[dict] = []
        anns_json:   list[dict] = []
        ann_id = 1

        ordered_anns = sorted(annotated, key=lambda a: a.frame_index)
        total  = len(ordered_anns)

        for seq, ann in enumerate(ordered_anns, start=1):
            src = ann.frame_path
            if not os.path.exists(src):
                log.warning(f"Frame missing on disk, skipping: {src}")
                continue

            img = cv2.imread(src)
            if img is None:
                log.warning(f"Could not read image, skipping: {src}")
                continue
            h, w = img.shape[:2]

            ext     = os.path.splitext(src)[1].lower() or ".png"
            file_nm = f"img_{seq}{ext}"
            shutil.copy2(src, os.path.join(img_dir, file_nm))

            image_id = seq
            images_json.append({
                "id":        image_id,
                "file_name": file_nm,
                "width":     w,
                "height":    h,
            })

            for box in ann.boxes:
                bw_px = box.width  * w
                bh_px = box.height * h
                x_tl  = box.x_center * w - bw_px / 2
                y_tl  = box.y_center * h - bh_px / 2
                anns_json.append({
                    "id":          ann_id,
                    "image_id":    image_id,
                    "category_id": class_id_map[box.class_name] + 1,
                    "bbox":        [round(x_tl, 2), round(y_tl, 2),
                                    round(bw_px, 2), round(bh_px, 2)],
                    "area":        round(bw_px * bh_px, 2),
                    "iscrowd":     0,
                    "segmentation": [],
                })
                ann_id += 1

            if progress_callback:
                progress_callback(seq, total)

        coco = {
            "info": {
                "description": "Exported from tode",
                "date_created": datetime.now().isoformat(timespec="seconds"),
            },
            "licenses":    [],
            "images":      images_json,
            "annotations": anns_json,
            "categories":  categories,
        }

        json_path = os.path.join(self.output_dir, "annotations.json")
        with open(json_path, "w") as f:
            json.dump(coco, f, indent=2)

        log.info(
            f"COCO export complete — {len(images_json)} images, "
            f"{len(anns_json)} annotations, {len(categories)} categories "
            f"→ {self.output_dir}"
        )
        return {
            "format":     "coco",
            "output_dir": self.output_dir,
            "images":     len(images_json),
            "labels":     len(anns_json),
            "classes":    [c["name"] for c in categories],
        }

    # ── helpers ───────────────────────────────────────────────────────────────
    def _build_class_id_map(self, annotated: list[FrameAnnotation]) -> dict[str, int]:
        """
        Build a stable name → 0-based id map.
        Preserves any ids already known from the YOLO model class_names,
        then appends user-typed manual classes.
        """
        # 1) Names from model — keep their numeric order if possible
        seen: dict[str, int] = {}
        for _cid, name in sorted(self.class_names.items(), key=lambda kv: kv[0]):
            if name not in seen:
                seen[name] = len(seen)
        # 2) Names from actual annotations — append any new ones
        for ann in annotated:
            for box in ann.boxes:
                if box.class_name not in seen:
                    seen[box.class_name] = len(seen)
        return seen
