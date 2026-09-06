# Third-Party Licenses

This project bundles and depends on the following third-party software. Each is
the property of its respective owners and licensed under the terms below.

## Direct Python dependencies

| Package | Version | License | Notes |
|---|---|---|---|
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | ≥ 6.6.0 | **GPL-3.0** (or commercial) | Copyleft desktop GUI toolkit — the copyleft driver for this project. A commercial Qt/PyQt licence (or a swap to LGPL PySide6) is required for closed-source distribution. |
| [torch](https://github.com/pytorch/pytorch) | ≥ 2.2.0 | BSD-3-Clause | Permissive. RT-DETR runtime. |
| [torchvision](https://github.com/pytorch/vision) | ≥ 0.17.0 | BSD-3-Clause | Permissive. |
| [transformers](https://github.com/huggingface/transformers) | ≥ 4.48.0 | Apache-2.0 | Permissive. Provides RT-DETR / RT-DETRv2. |
| [supervision](https://github.com/roboflow/supervision) | ≥ 0.22.0 | MIT | Permissive. Detection post-processing / NMS. |
| [opencv-python](https://github.com/opencv/opencv-python) | ≥ 4.8.0 | Apache-2.0 | Permissive. |
| [Pillow](https://github.com/python-pillow/Pillow) | ≥ 10.0.0 | MIT-CMU (HPND) | Permissive. |
| [numpy](https://github.com/numpy/numpy) | ≥ 1.24.0 | BSD-3-Clause | Permissive. |
| [requests](https://github.com/psf/requests) | ≥ 2.28.0 | Apache-2.0 | Permissive. |

### Web server (optional, `requirements-server.txt`)

| Package | License |
|---|---|
| [fastapi](https://github.com/tiangolo/fastapi) | MIT |
| [uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause |
| [gunicorn](https://github.com/benoitc/gunicorn) | MIT |
| [python-multipart](https://github.com/Kludex/python-multipart) | Apache-2.0 |
| [aiofiles](https://github.com/Tinche/aiofiles) | Apache-2.0 |

## Model weights

| Software | Source | License | Notes |
|---|---|---|---|
| RT-DETR pretrained weights (`PekingU/rtdetr_*`) | downloaded from the [HuggingFace Hub](https://huggingface.co/PekingU) at runtime | Apache-2.0 | Trained on **COCO** ([cocodataset.org](https://cocodataset.org), CC-BY-4.0). Predictions inherit dataset attribution requirements. Weights are not bundled — they download on first use. |

## User-supplied content

- **Annotated images** — the user retains all rights to images and labels they
  create with this tool. Exported datasets are the user's property.

## Why AGPL-3.0 for this project

The **detection stack is permissively licensed** — RT-DETR / `transformers`
(Apache-2.0), `supervision` (MIT), torch (BSD). There is no longer any AGPL
dependency (the previous Ultralytics YOLO engine was removed).

The remaining copyleft dependency is **PyQt6 (GPL-3.0)**. AGPL-3.0 is
GPL-compatible, so distributing tode under AGPL-3.0 satisfies PyQt6's terms
while keeping the project fully open source. For a closed-source distribution
you would instead need a commercial Qt/PyQt licence, or replace PyQt6 with the
LGPL-licensed **PySide6** (a near drop-in Qt binding).
