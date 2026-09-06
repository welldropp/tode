"""
tode — Entry Point (PyQt6)
Run: python main.py
"""
import os
import sys

# src/ layout: put the package root on the path so `from core...` works.
# When frozen by PyInstaller the packages are bundled top-level, so this is a
# no-op there (the inserted path simply doesn't exist).
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# ── OpenCV / FFmpeg thread safety ────────────────────────────────────────────
# Must be set BEFORE the first `import cv2` anywhere in the process.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "threads;1")
import cv2

cv2.setNumThreads(0)

from PyQt6.QtWidgets import QApplication

from ui.qt_main_window import TodeMainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("tode")
    window = TodeMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
