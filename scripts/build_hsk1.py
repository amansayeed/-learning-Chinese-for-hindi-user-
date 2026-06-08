# -*- coding: utf-8 -*-
"""Build data/hsk-1.json — wrapper for scripts/build_hsk.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hsk import build_level

if __name__ == "__main__":
    build_level(1)
