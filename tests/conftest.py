from __future__ import annotations

import sys
from pathlib import Path


# Ensure the repo root (where app.py lives) is importable when pytest runs
# with importlib-based import modes.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
