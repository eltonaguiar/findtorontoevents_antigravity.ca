"""Shared helpers for data_integrity diagnostic scripts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Iterable

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLOSED_PICKS = os.path.join(REPO_ROOT, "alpha_engine", "data", "closed_picks.json")
ACTIVE_PICKS = os.path.join(REPO_ROOT, "alpha_engine", "data", "active_picks.json")
UNIVERSAL_RESOLVED = os.path.join(
    REPO_ROOT, "audit_trail", "data", "universal_resolved_picks.json"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "out")


def load_json_list(path: str) -> list[dict]:
    """Load a JSON file that contains a list (or dict wrapping a list)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def parse_ts(value: Any) -> datetime | None:
    """Best-effort parse of many timestamp formats to aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if not isinstance(value, str):
        return None
    s = value.strip().replace("Z", "+00:00")
    # try ISO first
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def is_ghost_row(p: dict) -> bool:
    """Known synthetic MATICUSDT -0.15% ghost rows from legacy migration."""
    try:
        return p.get("symbol") == "MATICUSDT" and float(p.get("pnl_pct", 0)) == -0.15
    except Exception:
        return False


def classify_asset(p: dict) -> str:
    """Return declared asset_class or best-effort inference. Returns UNKNOWN if nothing fits."""
    ac = p.get("asset_class")
    if isinstance(ac, str) and ac.strip() and ac.upper() != "UNKNOWN":
        return ac.upper()
    sym = str(p.get("symbol", "")).upper()
    if sym.endswith("USDT") or sym.endswith("USD") or "BTC" in sym or "ETH" in sym:
        return "CRYPTO"
    return "UNKNOWN"


def ensure_out_dir() -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    return OUT_DIR
