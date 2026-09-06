# tode

A fast, open-source annotation tool for video frames and images — bounding boxes, polygon segmentation, and image classification — powered by RT-DETR auto-annotation and a built-in web server for multi-user workflows. Ships as a PyQt6 desktop app with a one-click installer.

---

## Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Desktop App](#desktop-app)
  - [Opening a Source](#opening-a-source)
  - [Annotation Types](#annotation-types)
  - [Keyboard Shortcuts](#keyboard-shortcuts)
  - [Playback Controls](#playback-controls)
  - [YOLO Models](#yolo-models)
  - [Exporting](#exporting)
- [Web Server](#web-server)
  - [Starting the Server](#starting-the-server)
  - [REST API](#rest-api)
- [Performance](#performance)
- [Output Structure](#output-structure)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Docker](#docker)
- [License](#license)

---

## Features

**Desktop app (PyQt6)**
- Auto-annotate with RT-DETR (HuggingFace transformers + supervision) — one frame or all at once
- Three annotation types: **bounding box**, **polygon segmentation**, **image classification**
- Click-and-drag box drawing with full resize / move handles
- Polygon draw mode — click to place vertices, double-click to close, Escape to cancel
- Play/pause video with variable speed (0.5× / 1× / 2× / 4×) and Space bar toggle
- Adjustable **frame step** — load every Nth frame for fast navigation on long videos
- Manual class names + confidence threshold slider
- Live log viewer, class-filter, per-frame undo (clear), label persistence across sessions

**Export formats**
- YOLO (images/ + labels/ + data.yaml)
- COCO JSON
- Pascal VOC XML
- CSV
- JSON

**Web server (FastAPI)**
- REST API for projects, frame upload, per-frame annotations, ZIP export
- Dark-theme SPA at `http://localhost:8000` — works in any browser
- Canvas annotation (bbox / polygon / classification), frame strip, keyboard navigation

**Performance**
- Frames saved as **JPEG** (not PNG) — 5–10× faster writes, 10× smaller files
- Image folder loading skips unnecessary decoding — near-instant for large folders
- Label scan does one `os.listdir()` at startup instead of per-frame file stats
- Background frame extraction — UI is responsive immediately after opening a video

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/tedo001/tode.git
cd tode

# 2. Virtual environment (Python 3.11 or 3.12)
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install desktop dependencies
pip install -r requirements.txt

# 4. Launch the desktop app
python main.py

# 5. (Optional) Install and launch the web server
pip install -r requirements-server.txt
python run_server.py               # → http://localhost:8000
```

> **Prefer a one-click install?** tode also ships as a WEKA-style installer
> (`tode-setup.exe` on Windows, a tarball on Linux) that bundles Python and all
> dependencies — no manual setup. See [`packaging/README.md`](packaging/README.md).

---

## Desktop App

### Opening a Source

| Toolbar button | Action |
|---|---|
| `📂 Open` | Tabbed dialog — Video / Image / Image Folder |
| `🎬 Video` | Direct video file picker |
| `🖼 Image` | Single image or image folder |

**Click the canvas** when no source is loaded to open the file picker directly.

**Supported video formats:** MP4, AVI, MOV, MKV, WEBM, FLV, WMV

**Supported image formats:** JPG, PNG, BMP, TIFF, WEBP

**Frame Step** — the Open dialog includes a "Video frame step" spinbox (1–30). At `step=5` a 30 fps video loads 6× fewer frames; at `step=1` (default) every frame is indexed. Frames not yet extracted from the background thread are decoded on-demand.

---

### Annotation Types

Select the annotation type from the mode bar above the canvas.

#### Bounding Box (`W` key → Draw mode)
1. Click and drag on the canvas to draw a box
2. Click inside a drawn box to select it — 8 resize handles appear
3. Drag a handle to resize; drag the body to move
4. Click an empty area or press `V` / `Esc` to deselect

#### Polygon Segmentation (`⬠ Polygon` button)
1. Click to place each vertex
2. **Double-click** to close the polygon and commit it
3. **Escape** cancels the polygon in progress
4. Saved in YOLO-seg format (`.seg.txt` sidecar)

#### Image Classification (`🏷 Cls` button)
- Assigns a single class label to the whole frame (no spatial extent)
- Saved as a `.cls.txt` sidecar

---

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `A` / `←` | Previous frame |
| `D` / `→` | Next frame |
| `Home` | Jump to first frame |
| `End` | Jump to last frame |
| `W` | Switch to **Draw Box** mode |
| `V` / `Esc` | Switch to **View** mode / cancel polygon |
| `Space` | Toggle play / pause |
| `Y` | Run RT-DETR on the current frame |
| `Ctrl+S` | Save annotations |
| `Ctrl+E` | Export dataset |
| `Ctrl+O` | Open source dialog |
| `Delete` | Clear all annotations on the current frame |

---

### Playback Controls

The navigation bar has five buttons:

```
⏮   ◀   ▶/⏸   ▶   ⏭
```

- **▶** (purple) — click or press `Space` to start auto-advance
- **⏸** (pink) — shown while playing; click or press `Space` to pause
- Speed row below: `0.5×` `1×` `2×` `4×`
- Any navigation button (⏮ ◀ ▶ ⏭) stops playback automatically

---

### RT-DETR Models

The control panel has an **RT-DETR model** dropdown (HuggingFace ids).

| Model | Backbone | Speed | Accuracy |
|---|---|---|---|
| `PekingU/rtdetr_r18vd` | ResNet-18 | Fastest | Good |
| `PekingU/rtdetr_r34vd` | ResNet-34 | Fast | Better |
| `PekingU/rtdetr_r50vd` | ResNet-50 | Medium | High (default) |
| `PekingU/rtdetr_r101vd` | ResNet-101 | Slow | Best |
| `PekingU/rtdetr_v2_r18vd` / `_r50vd` | RT-DETRv2 | — | improved |

Weights are **auto-downloaded from the HuggingFace Hub** on first use and cached
— no local weight files to manage. Set a different default with the
`TODE_RTDETR_MODEL` environment variable.

---

### Exporting

Click **📤 Export** and choose a format and output folder.

| Format | Output |
|---|---|
| **YOLO** | `images/` + `labels/` + `data.yaml` — ready for `yolo train` |
| **COCO** | `annotations.json` (images, annotations, categories) |
| **Pascal VOC** | One XML per image |
| **CSV** | One row per bounding box |
| **JSON** | Custom JSON with all annotation types |

Only annotated frames are exported. Frame files are renumbered sequentially (`img_1`, `img_2`, …) so images and labels always match 1-to-1.

The YOLO/COCO export uses the standard dataset layout, so the result feeds
straight into any detection trainer (RT-DETR fine-tuning via `transformers`,
or any framework that reads YOLO `data.yaml` / COCO `annotations.json`).

---

## Web Server

The web server is a standalone FastAPI app that does **not** modify `main.py` or any desktop code. Run it alongside or instead of the desktop app.

### Starting the Server

```bash
pip install -r requirements-server.txt
python run_server.py
```

Open `http://localhost:8000` in a browser.

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `TODE_HOST` | `0.0.0.0` | Bind address |
| `TODE_PORT` | `8000` | Port |
| `TODE_RELOAD` | `false` | Uvicorn auto-reload (dev mode) |

### REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/projects/{id}` | Get project metadata |
| `DELETE` | `/api/projects/{id}` | Delete a project |
| `PATCH` | `/api/projects/{id}/classes` | Update class list |
| `POST` | `/api/projects/{id}/upload` | Upload frame images |
| `GET` | `/api/projects/{id}/export?fmt=yolo` | Download annotations as ZIP |
| `GET` | `/api/projects/{id}/frames` | List frames |
| `GET` | `/api/projects/{id}/frames/{idx}/image` | Get frame image |
| `GET` | `/api/projects/{id}/frames/{idx}/annotations` | Get frame annotations |
| `POST` | `/api/projects/{id}/frames/{idx}/annotations` | Save frame annotations |

All annotation endpoints accept and return JSON with `boxes`, `polygons`, and `classifications` arrays.

---

## Performance

| Scenario | Before | After |
|---|---|---|
| Write one 1080p frame | ~40 ms (PNG) | ~6 ms (JPEG) |
| 1000-frame background extraction | ~40 s disk I/O | ~6 s |
| Load 1000-image folder | Decodes all 1000 images | Zero decodes — path copy only |
| Startup label scan (1000 frames) | ~3000 `stat()` calls | 1 `listdir()` call |
| 10-min 30fps video at `step=5` | 18 000 frames | 3 600 frames |

Frames are cached as JPEG on first access. Subsequent navigation reads the JPEG from disk (~5 ms per frame). Old projects with `.png` frames are supported automatically via a fallback path.

---

## Output Structure

```
output/
├── frames/
│   └── <source_name>/
│       ├── frame_000000.jpg        ← JPEG cache (new projects)
│       └── frame_000005.jpg
├── labels/
│   └── <source_name>/
│       ├── frame_000000.txt        ← YOLO bbox  (class cx cy w h)
│       ├── frame_000000.seg.txt    ← YOLO-seg polygons
│       ├── frame_000000.cls.txt    ← image-level classification
│       └── classes.json            ← class id → name mapping
└── server_projects/                ← web server projects
    └── <project_id>/
        ├── meta.json
        ├── frames/
        └── labels/
```

Label format:

| File | Format |
|---|---|
| `.txt` | `<class_id> <cx> <cy> <w> <h>` (normalised, YOLO) |
| `.seg.txt` | `<class_id> <x1> <y1> <x2> <y2> … <xN> <yN>` (normalised, YOLO-seg) |
| `.cls.txt` | `<class_id> <confidence>` |

---

## Project Structure

```
tode/
├── main.py                         # desktop app entry point
├── run_server.py                   # web server entry point
├── requirements.txt                # desktop dependencies
├── requirements-server.txt         # web server dependencies
├── requirements-test.txt           # test dependencies
│
├── src/
│   ├── core/
│   │   ├── annotation_manager.py   # orchestrates the full pipeline
│   │   ├── video_loader.py         # OpenCV video I/O
│   │   ├── frame_extractor.py      # sequential JPEG frame extraction
│   │   ├── image_loader.py         # single image / folder loader
│   │   ├── image_frame_extractor.py
│   │   ├── auto_annotator.py       # RT-DETR detector facade (thread-safe)
│   │   ├── exporter.py             # multi-format dataset export
│   │   ├── base_detector.py
│   │   ├── analytics/              # stats, report generator
│   │   ├── detectors/              # RT-DETR (transformers + supervision) backend
│   │   ├── exporters/              # YOLO / COCO / Pascal VOC / CSV / JSON
│   │   ├── importers/              # YOLO / COCO / CSV / JSON importers
│   │   └── pipeline/               # QueueManager, BatchProcessor, Scheduler
│   │
│   ├── models/
│   │   ├── annotation_model.py     # BoundingBox, PolygonAnnotation,
│   │   │                           # ImageClassification, FrameAnnotation
│   │   ├── project_config.py
│   │   ├── batch_config.py
│   │   ├── class_definition.py
│   │   ├── export_config.py
│   │   └── session.py
│   │
│   ├── storage/
│   │   ├── label_storage.py        # YOLO .txt / .seg.txt / .cls.txt I/O
│   │   ├── frame_storage.py
│   │   ├── project_storage.py
│   │   ├── session_storage.py
│   │   └── formats/                # YOLO / COCO / CSV / Pascal VOC / JSON
│   │
│   └── ui/                         # PyQt6 desktop UI
│       ├── qt_main_window.py       # main window, toolbar, panel, event wiring
│       ├── qt_canvas.py            # annotation canvas (boxes + polygons)
│       └── qt_workers.py           # QThread load / detect workers
│
├── server/                         # FastAPI web server (standalone)
│   ├── app.py
│   ├── config.py
│   ├── routes/                     # health, projects, frames
│   ├── schemas/                    # Pydantic request/response models
│   ├── services/                   # project, annotation, export services
│   └── static/                     # index.html, app.js, style.css
│
├── packaging/                      # PyInstaller spec + Inno Setup wizard + CI
├── tests/                          # pytest
└── output/                         # generated files (gitignored)
```

---

## Running Tests

```bash
pip install -r requirements-test.txt
pytest tests/ -q
```

135 tests covering loaders, extractors, exporters, importers, annotation models, storage, pipeline, analytics, and utilities.

---

## Docker

Build and run in a reproducible Linux environment with all dependencies pre-installed.

```bash
# Build
docker build -t tode .

# Smoke test
docker run --rm tode python -c "from core import YOLOAnnotator; print('OK')"

# GUI on Linux (X11)
xhost +local:docker
docker compose up
```

Outputs persist on the host via volume mounts (`./output/`).

### GPU (NVIDIA)

Install [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) then uncomment `deploy.resources` in `docker-compose.yml`:

```bash
docker compose up          # GPU used automatically
```

| Platform | GUI in Docker? | Recommended |
|---|---|---|
| Linux | ✅ X11 forwarding | Full app |
| Windows | ❌ Needs WSL2 + VcXsrv | Headless only |
| macOS | ❌ No native X11 | `python main.py` in venv |

---

## License

Licensed under **GNU AGPL-3.0** — see [`LICENSE`](LICENSE).

**Why AGPL?** The detection stack is now permissively licensed — RT-DETR /
`transformers` are Apache-2.0 and `supervision` is MIT (no Ultralytics/AGPL
dependency). The remaining copyleft driver is the **PyQt6** desktop GUI, which
is **GPL-3.0**; AGPL-3.0 is compatible with it and keeps tode fully open source.
For a closed-source desktop distribution you would need a commercial PyQt
licence (or swap PyQt6 for LGPL PySide6).

| Action | Allowed? |
|---|---|
| Use locally / privately | ✅ |
| Modify source code | ✅ |
| Share modifications | ✅ — must include AGPL-3.0 source |
| Run as a public web service | ✅ — must publish modifications under AGPL-3.0 |
| Distribute a closed-source fork | ❌ — AGPL-3.0 (and PyQt6 GPL) require source |
| Train on your own data and keep the weights | ✅ — your data, your weights |

See [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) for the full dependency licence table.
