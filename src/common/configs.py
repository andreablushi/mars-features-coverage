"""Central configuration shared by both stages.

Both stages keep their data inside the repository, and a script run from the
root used to be the only thing that resolved a relative data path correctly. A
notebook opens with its own directory as the working directory, so every root
hangs off `REPO_ROOT` instead and means the same place wherever it is resolved
from. Each stage's own `configs.py` builds its paths from this one.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = REPO_ROOT / "config.yaml"
