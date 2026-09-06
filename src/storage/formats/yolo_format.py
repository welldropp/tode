"""
storage/formats/yolo_format.py
────────────────────────────────
Read/write YOLO normalised bounding-box files.
"""
from __future__ import annotations


class YOLOFormat:
    """Static helpers for YOLO .txt label files."""

    @staticmethod
    def read(path: str) -> list[dict]:
        rows: list[dict] = []
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    rows.append({
                        "class_id": int(parts[0]),
                        "cx": float(parts[1]),
                        "cy": float(parts[2]),
                        "w":  float(parts[3]),
                        "h":  float(parts[4]),
                    })
        except FileNotFoundError:
            pass
        return rows

    @staticmethod
    def write(path: str, rows: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(
                    f"{r['class_id']} {r['cx']:.6f} {r['cy']:.6f} {r['w']:.6f} {r['h']:.6f}\n"
                )
