# tools/cohort_reconciliation.py
"""Pure cohort reconciliation for /audit published JSONs (measurement only).

Reads only published files; never touches the live DB.
No trade triggers. Output contains no READY/ENTER wording.
"""
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "1.1.0"


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_ts(ts):
    """Parse an ISO timestamp; tolerate trailing 'Z' and microseconds."""
    if ts is None:
        raise ValueError("parse_ts(None)")
    s = str(ts).strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def load_json(path):
    """Load JSON. Return None if missing; raise ValueError if malformed."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON in {path}: {e}")
