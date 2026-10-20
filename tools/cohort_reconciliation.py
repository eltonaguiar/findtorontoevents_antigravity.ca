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


def _pf(rows):
    rows = [r for r in rows if r.get("pnl_pct") is not None]
    if not rows:
        return None
    pos = sum(r["pnl_pct"] for r in rows if r["pnl_pct"] > 0)
    neg = abs(sum(r["pnl_pct"] for r in rows if r["pnl_pct"] < 0))
    if neg == 0:
        return "inf" if pos > 0 else 0.0
    return pos / neg


def metric_block(rows):
    rows = [r for r in rows if r.get("pnl_pct") is not None]
    n = len(rows)
    wins = sum(1 for r in rows if r["pnl_pct"] > 0)
    losses = sum(1 for r in rows if r["pnl_pct"] < 0)
    hidden = n < 20
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": None if hidden else (wins / n if n else None),
        "win_rate_hidden": hidden,
        "pf": _pf(rows),
    }


def _coverage(records, window_hours, generated_dt):
    ats = [parse_ts(r["closed_at"]) for r in records if r.get("closed_at")]
    window_start = generated_dt - timedelta(hours=window_hours)
    if not ats:
        return {"status": "incomplete_coverage", "oldest_closed_at": None,
                "window_start_utc": window_start.isoformat(), "covers_window": False}
    oldest = min(ats)
    return {"oldest_closed_at": oldest.isoformat(),
            "window_start_utc": window_start.isoformat(),
            "covers_window": oldest <= window_start,
            "status": "complete" if oldest <= window_start else "incomplete_coverage"}


def _group_metrics(records):
    by_class = {}
    by_strategy = {}
    for r in records:
        cls = r.get("asset_class") or "UNKNOWN"
        strat = r.get("strategy") or "UNKNOWN"
        by_class.setdefault(cls, []).append(r)
        by_strategy.setdefault(strat, []).append(r)
    return ({"class": k, "metrics": metric_block(v)} for k, v in by_class.items()), \
           ({"strategy": k, "metrics": metric_block(v)} for k, v in by_strategy.items())


def recompute_rolling_metrics(records, window_hours, generated_at):
    generated_dt = parse_ts(generated_at)
    cov = _coverage(records, window_hours, generated_dt)
    by_class = {it["class"]: it["metrics"] for it in _group_metrics(records)[0]}
    by_strategy = {it["strategy"]: it["metrics"] for it in _group_metrics(records)[1]}
    return {"window_hours": window_hours, "coverage": cov,
            "by_class": by_class, "by_strategy": by_strategy}
