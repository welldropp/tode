"""Gunicorn configuration for tode web server."""
import multiprocessing
import os

# ── binding ───────────────────────────────────────────────────────────────────
port = int(os.environ.get("PORT", os.environ.get("TODE_PORT", "8000")))
bind = f"0.0.0.0:{port}"

# ── workers ───────────────────────────────────────────────────────────────────
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# ── timeouts ──────────────────────────────────────────────────────────────────
# 120s allows slow YOLO inference on CPU without killing the worker
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = 5
graceful_timeout = 30

# ── logging ───────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog  = "-"
loglevel  = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'
