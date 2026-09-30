"""Test configuration: make ``src`` importable.

The suite runs inside the crawler image (or any environment where the pinned
``crawl4ai`` is installed); it needs no browser and no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
