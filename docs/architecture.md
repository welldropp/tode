# Architecture

`tode` is a **PyQt6 desktop app** (plus an optional FastAPI web server) on top of
a fully headless core. The package layout mirrors the runtime layers — the UI
never reaches into another UI module's internals, and the headless layers never
import Qt.

```
┌─────────────────────────────────────────────────────────────────┐
│  ui/        PyQt6 — qt_main_window, qt_canvas, qt_workers        │  ← display layer
├─────────────────────────────────────────────────────────────────┤
│  core/      annotation_manager, auto_annotator, exporter,        │
│             detectors/rtdetr_detector, loaders                   │  ← headless app logic
├─────────────────────────────────────────────────────────────────┤
│  storage/   label_storage (YOLO/JSON), frame_storage             │  ← persistence
├─────────────────────────────────────────────────────────────────┤
│  models/    BoundingBox, PolygonAnnotation, FrameAnnotation      │  ← pure types
│  utils/     config, image_utils, logger                          │  ← shared helpers
└─────────────────────────────────────────────────────────────────┘
```

## Detection backend

Detection is **RT-DETR** (Real-Time DEtection TRansformer) from HuggingFace
`transformers` (Apache-2.0), with **supervision** for post-processing / NMS.

```python
from core.auto_annotator import AutoAnnotator          # facade
from core.detectors.rtdetr_detector import RTDetrDetector
```

- `core.auto_annotator.AutoAnnotator` is the thread-safe facade every caller
  uses (`annotate_frame`, `annotate_frames`, `class_names`, `confidence`, `iou`).
- `core.detectors.rtdetr_detector.RTDetrDetector` implements `BaseDetector`.
  torch / transformers / supervision are imported **lazily** inside its methods,
  so importing the module (and constructing the facade) stays cheap.
- Model weights are pulled from the HuggingFace Hub on first inference and
  cached — there are no local weight files to manage. The model id is
  configurable (`utils.config.RTDETR_MODELS`, default `PekingU/rtdetr_r50vd`).

## Why RT-DETR + supervision

RT-DETR is anchor-free and NMS-light with strong accuracy at real-time speeds,
and — unlike the previous YOLO/Ultralytics engine — carries an **Apache-2.0**
license with no AGPL entanglement for downstream products. `supervision`
provides a clean `Detections` representation and post-processing that the
detector converts into the app's normalised `BoundingBox` model.

## Note on the YOLO *format*

The YOLO **dataset format** (`class cx cy w h`, normalised) is retained for
export/import and on-disk labels. It is the de-facto standard training layout
and is independent of the detector — RT-DETR datasets export/train in it too.

## Packaging

The desktop app ships as a WEKA-style installer (PyInstaller bundle wrapped in
an Inno Setup wizard on Windows; a tarball on Linux). See `packaging/README.md`.
