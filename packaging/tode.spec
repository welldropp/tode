# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for the tode desktop application (RT-DETR edition).

Produces a self-contained one-directory bundle under ``dist/tode`` that ships
its own Python runtime and every dependency (torch, transformers, supervision,
OpenCV, Tk). RT-DETR model weights are NOT bundled — they download from the
HuggingFace Hub on first use.

Build:
    pyinstaller packaging/tode.spec

The one-dir output is then wrapped into a Windows setup wizard by
``packaging/tode_installer.iss`` (Inno Setup), or tarred for Linux.
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Resolve the repo root from the spec's own location (SPECPATH is injected by
# PyInstaller as the directory containing this .spec file → repo/packaging).
_ROOT = os.path.dirname(os.path.abspath(SPECPATH))  # noqa: F821 (PyInstaller global)
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _safe_collect_all(pkg):
    """collect_all() that degrades to empty when a package isn't installed,
    so a local (e.g. torch-less) build still succeeds for smoke testing."""
    try:
        return collect_all(pkg)
    except Exception:
        return ([], [], [])


datas, binaries, hiddenimports = [], [], []

# Third-party packages that need their data files / dynamic libs collected.
for _pkg in (
    "torch", "torchvision", "transformers", "supervision",
    "tokenizers", "safetensors", "huggingface_hub", "regex",
    "cv2", "PIL", "numpy", "PyQt6",
):
    _d, _b, _h = _safe_collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# First-party packages (bundled from src/ via pathex below).
for _pkg in ("core", "ui", "utils", "models", "storage"):
    try:
        hiddenimports += collect_submodules(_pkg)
    except Exception:
        pass

# Application data files (absolute source paths, spec-relative → build-safe).
if os.path.isdir(os.path.join(_ROOT, "server", "static")):
    datas += [(os.path.join(_ROOT, "server", "static"), "server/static")]
if os.path.isfile(os.path.join(_ROOT, "LICENSE")):
    datas += [(os.path.join(_ROOT, "LICENSE"), ".")]

_icon = os.path.join(_ROOT, "packaging", "tode.ico")
_icon = _icon if os.path.isfile(_icon) else None

a = Analysis(
    [os.path.join(_ROOT, "main.py")],
    pathex=[_SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "bandit", "pip_audit"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="tode",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # GUI app — no console window (WEKA-style)
    disable_windowed_traceback=False,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="tode",
)
