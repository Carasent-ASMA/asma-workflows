"""Pytest configuration: add deploy script directory to import path."""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory (deploy scripts root) to sys.path for test imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
