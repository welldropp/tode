#!/usr/bin/env python3
"""Entry-point: python run_server.py"""
import os
import sys

# Ensure server/ package is importable from repo root
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn

from server.config import HOST, PORT, RELOAD  # noqa: E402 (path manipulation above)

if __name__ == "__main__":
    uvicorn.run(
        "server.app:create_app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        factory=True,
    )
