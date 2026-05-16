"""Pytest bootstrap: make the source packages importable in tests.

The pipelines live in separate directories (``src/pipelines/v1`` etc.) and
import their siblings by bare name, so the test process needs those
directories on ``sys.path`` the same way the entry-point scripts arrange it
at runtime.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_SRC_DIRS = [
    "src",
    "src/pipelines/v1",
    "src/pipelines/v2",
    "src/pipelines/v2/parsing",
    "src/pipelines/v3",
    "src/eval",
]

for _rel in _SRC_DIRS:
    _path = str(ROOT / _rel)
    if _path not in sys.path:
        sys.path.insert(0, _path)
