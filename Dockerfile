# syntax=docker/dockerfile:1.6
#
# tode — container image
# Source: https://github.com/tedo001/tode
#
# Build:
#   docker build -t tode .
#
# Run (headless / CI — no GUI):
#   docker run --rm -it tode python -c "from core import YOLOAnnotator"
#
# Run (Linux desktop with X11 forwarding):
#   xhost +local:docker
#   docker run --rm -it \
#       -e DISPLAY=$DISPLAY \
#       -v /tmp/.X11-unix:/tmp/.X11-unix \
#       -v $(pwd)/output:/app/output \
#       -v $HOME/Documents/labeled_img:/root/Documents/labeled_img \
#       tode
#
# Run with GPU (NVIDIA, requires nvidia-container-toolkit on host):
#   docker run --gpus all --rm -it -e DISPLAY=$DISPLAY \
#       -v /tmp/.X11-unix:/tmp/.X11-unix tode

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    OPENCV_FFMPEG_CAPTURE_OPTIONS="threads;1" \
    PYTHONPATH="/app/src"

# System dependencies:
#   libgl1, libegl1, libglib2.0-0     — OpenCV + Qt (QtGui/OpenGL) runtime
#   libxcb*, libxkbcommon0, libdbus-1 — PyQt6 xcb platform plugin on X11
RUN apt-get update && apt-get install --no-install-recommends -y \
        libgl1 \
        libegl1 \
        libglib2.0-0 \
        libxkbcommon0 \
        libdbus-1-3 \
        libxcb1 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xinerama0 \
        libxext6 \
        libsm6 \
        libxrender1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: dependency cache.  Touching code shouldn't reinstall packages.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Layer 2: application code
COPY . .

CMD ["python", "main.py"]

# ── web server stage ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS web

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH="/app/src"

RUN apt-get update && apt-get install --no-install-recommends -y \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-server.txt ./
RUN pip install -r requirements.txt -r requirements-server.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "server.app:app"]
