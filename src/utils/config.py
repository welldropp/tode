"""Global configuration constants."""
import os

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
FRAMES_DIR  = os.path.join(OUTPUT_DIR, "frames")
LABELS_DIR  = os.path.join(OUTPUT_DIR, "labels")
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")

# ── Frame extraction ──────────────────────────────────────────────────────────
DEFAULT_FPS_STEP = 1        # extract every N-th frame
FRAME_WIDTH      = 640
FRAME_HEIGHT     = 480

# ── Detection model catalogue (RT-DETR via HuggingFace transformers) ───────────
# tode uses RT-DETR (Apache-2.0) for detection + the `supervision` library for
# post-processing. Weights are auto-downloaded from the HuggingFace Hub on first
# use and cached under the HF cache dir. No local weight files are required.
RTDETR_MODELS = [
    "PekingU/rtdetr_r18vd",       # fastest / smallest (~76 MB)
    "PekingU/rtdetr_r34vd",
    "PekingU/rtdetr_r50vd",       # balanced (default)
    "PekingU/rtdetr_r101vd",      # most accurate
    "PekingU/rtdetr_v2_r18vd",    # RT-DETRv2 variants
    "PekingU/rtdetr_v2_r50vd",
]
RTDETR_DEFAULT_MODEL = os.environ.get("TODE_RTDETR_MODEL", "PekingU/rtdetr_r50vd")

# ── Inference defaults ────────────────────────────────────────────────────────
DETECT_CONFIDENCE = 0.45
DETECT_IOU        = 0.45

# ── UI colours ────────────────────────────────────────────────────────────────
BG_DARK    = "#1e1e2e"
BG_PANEL   = "#2a2a3e"
ACCENT     = "#7c6af7"
TEXT_LIGHT = "#e0e0f0"
BOX_COLOR  = "#00ff88"          # manual bbox overlay colour

# ── Label storage format ──────────────────────────────────────────────────────
# "yolo" → .txt  (class cx cy w h — normalised)
LABEL_FORMAT = "yolo"

for _d in (OUTPUT_DIR, FRAMES_DIR, LABELS_DIR, WEIGHTS_DIR):
    os.makedirs(_d, exist_ok=True)
