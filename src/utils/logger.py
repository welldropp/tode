"""
utils/logger.py
───────────────
Single source of truth for all logging in the application.

Features
────────
- Rotating file handler  (10 MB × 5 backups)
- Coloured console handler
- Per-module child loggers via get_logger(name)
- Thread-safe: Python's logging module is thread-safe by default
- GUI queue handler  — UI can subscribe to log records via LogQueue
"""

import logging
import os
import queue
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from utils.config import BASE_DIR

# ── Paths ─────────────────────────────────────────────────────────────────────
LOG_DIR  = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_today   = datetime.now().strftime("%Y%m%d")
LOG_FILE = os.path.join(LOG_DIR, f"annotation_{_today}.log")

# ── Format ────────────────────────────────────────────────────────────────────
FILE_FMT    = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
CONSOLE_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FMT    = "%Y-%m-%d %H:%M:%S"

# ── Colour codes (console only) ───────────────────────────────────────────────
_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
    "RESET":    "\033[0m",
}


class _ColouredFormatter(logging.Formatter):
    """Add ANSI colour codes to levelname in console output."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        reset  = _COLOURS["RESET"]
        record.levelname = f"{colour}{record.levelname}{reset}"
        return super().format(record)


# ── GUI Queue Handler ─────────────────────────────────────────────────────────
class QueueHandler(logging.Handler):
    """
    Pushes formatted log strings into a thread-safe queue so the
    Tkinter log viewer can poll without blocking.
    """

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.log_queue.put_nowait(msg)
        except Exception:
            self.handleError(record)


# ── Shared GUI queue (created once) ──────────────────────────────────────────
gui_log_queue: queue.Queue = queue.Queue(maxsize=2000)

# ── Root app logger ───────────────────────────────────────────────────────────
_root_logger = logging.getLogger("tode")
_root_logger.setLevel(logging.DEBUG)

if not _root_logger.handlers:
    # 1. Rotating file handler
    _file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes   = 10 * 1024 * 1024,   # 10 MB
        backupCount= 5,
        encoding   = "utf-8",
    )
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(logging.Formatter(FILE_FMT, DATE_FMT))
    _root_logger.addHandler(_file_handler)

    # 2. Coloured console handler
    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setLevel(logging.INFO)
    _console_handler.setFormatter(
        _ColouredFormatter(CONSOLE_FMT, DATE_FMT)
    )
    _root_logger.addHandler(_console_handler)

    # 3. GUI queue handler
    _queue_handler = QueueHandler(gui_log_queue)
    _queue_handler.setLevel(logging.DEBUG)
    _queue_handler.setFormatter(logging.Formatter(FILE_FMT, DATE_FMT))
    _root_logger.addHandler(_queue_handler)

    _root_logger.info("=" * 70)
    _root_logger.info("tode — Session started")
    _root_logger.info(f"Log file: {LOG_FILE}")
    _root_logger.info("=" * 70)


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger namespaced under 'tode'.

    Usage
    -----
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Hello")
    """
    return _root_logger.getChild(name)


def get_log_file_path() -> str:
    return LOG_FILE


def get_log_dir() -> str:
    return LOG_DIR
