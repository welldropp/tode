"""Server configuration."""
import os
import sys

# Put src/ on the path so server code can import core modules directly
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

HOST         = os.environ.get("TODE_HOST", "0.0.0.0")
PORT         = int(os.environ.get("PORT", os.environ.get("TODE_PORT", "8000")))
RELOAD       = os.environ.get("TODE_RELOAD", "false").lower() == "true"
CORS_ORIGINS = ["*"]   # tighten in production

PROJECTS_DIR = os.path.join(_ROOT, "output", "server_projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)
