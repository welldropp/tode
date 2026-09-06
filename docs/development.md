# Development

## Local setup

```bash
git clone https://github.com/tedo001/tode.git
cd tode
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt
```

The `requirements-test.txt` variant intentionally omits `torch` / `transformers`
/ `PyQt6` so it installs in seconds and is fine for headless CI. The detector
tests use a stub backend, so no heavy ML deps are needed to run the suite.

## Tests

```bash
pytest tests/ -v
```

Tests are split per-module:

| File                          | Layer covered                                        |
|-------------------------------|------------------------------------------------------|
| `tests/test_models.py`        | `models.annotation_model` — BoundingBox, FrameAnnotation |
| `tests/test_storage.py`       | `storage.{label_storage,frame_storage}`              |
| `tests/test_exporter.py`      | `core.exporter` — YOLO + COCO export                  |
| `tests/test_detectors.py`     | `core.auto_annotator` facade + RT-DETR routing (stub) |
| `tests/test_loaders.py`       | `core.{image_loader,image_frame_extractor}`          |
| `tests/test_image_utils.py`   | `utils.image_utils` — drawing, resizing               |
| `tests/test_config.py`        | `utils.config` defaults                              |

All tests are headless; they don't open a display, a webcam, or load real model
weights.

## Lint

```bash
ruff check .
```

Ruff is pinned in CI so a new ruff release can't break a previously
green build — bump the pin in `.github/workflows/ci.yml` deliberately.

## Docker

The repository root `Dockerfile` builds the default GUI-capable image used
by `docker-compose.yml` (and a `web` stage for the FastAPI server). CPU and GPU
variants live under `docker/` — see `docker/README.md` for build commands and
the trade-offs of each. To build the desktop installer instead, see
`packaging/README.md`.
