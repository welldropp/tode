"""Shared test fixtures + sys.path setup so `from core import ...` works."""
import os
import sys

_repo_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(_repo_root, "src"))
