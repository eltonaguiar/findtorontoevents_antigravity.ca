"""P0.5 (2026-11-20) — one persistent count of every trial ever run.

DSR and BH are only meaningful against the true number of attempts. The audit
path previously derived ``n_trials`` from the cells in a single run, which
understates a 700-strategy history by orders of magnitude. This module owns the
counter; callers use ``effective_n_trials`` so a local estimate can never
*lower* the global figure (monotone-conservative: more trials only makes
promotion harder).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = _REPO_ROOT / "reports" / "trial_counter.json"
_CACHE: dict = {"mtime": None, "data": None}


def _load(path: Path) -> dict:
    try:
        st = path.stat()
    except FileNotFoundError:
        return {"families": {}, "total": 0}
    if _CACHE["mtime"] == st.st_mtime and _CACHE["data"] is not None:
        return _CACHE["data"]
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError):
        data = {"families": {}, "total": 0}
    data.setdefault("families", {})
    data.setdefault("total", sum(int(v or 0) for v in data["families"].values()))
    _CACHE.update(mtime=st.st_mtime, data=data)
    return data


def record(trials: int, family: str = "GLOBAL", path: str | os.PathLike | None = None) -> dict:
    """Add ``trials`` attempts to ``family``. Idempotency is the caller's job."""
    p = Path(path) if path else DEFAULT_PATH
    data = _load(p)
    n = max(int(trials), 0)
    data["families"][family] = int(data["families"].get(family, 0)) + n
    data["total"] = sum(int(v or 0) for v in data["families"].values())
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
    os.replace(tmp, p)
    _CACHE.update(mtime=None, data=None)
    return data


def effective_n_trials(local_trials: int | None, family: str = "GLOBAL",
                       path: str | os.PathLike | None = None, floor: int = 1) -> int:
    """The trial count a multiplicity correction must use: never below global."""
    p = Path(path) if path else DEFAULT_PATH
    data = _load(p)
    global_n = int(data.get("total", 0) or 0)
    fam_n = int(data["families"].get(family, 0) or 0)
    return max(int(local_trials or 0), global_n, fam_n, int(floor))
