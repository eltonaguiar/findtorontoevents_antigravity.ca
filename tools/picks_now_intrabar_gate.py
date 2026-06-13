"""Intrabar sym×dir gate for picks-now pro-level selection (2026-06-13).

Uses honest forward WR/PF from at_signal_outcomes intrabar replay (via
intrabar_sym_dir_fwd.json). Blocks symbols with proven bad forward track
records; demotes marginal ones from STRONG_BUY/BUY to WATCH.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM_DIR_JSON = os.path.join(REPO_ROOT, "audit_dashboard", "data", "intrabar_sym_dir_fwd.json")
CLASS_JSON = os.path.join(REPO_ROOT, "audit_dashboard", "data", "intrabar_truth_by_class.json")

_IS_CRYPTO_RE = re.compile(r"-USD$", re.I)
_IS_FOREX_RE = re.compile(r"=X$", re.I)
_IS_COMMODITY_RE = re.compile(r"=F$", re.I)

# Classes with intrabar FAIL at n≥100 — no STRONG_BUY promotion without override.
_CLASS_FAIL_BLOCK = {"CRYPTO", "EQUITY", "COMMODITY"}


def normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if s.endswith("=X"):
        s = s[:-2]
    return s.replace("-", "").replace("_", "").replace("/", "")


def normalize_direction(direction: str) -> str:
    d = (direction or "").upper().strip()
    if d in ("BUY", "LONG", "STRONG_BUY"):
        return "LONG"
    if d in ("SELL", "SHORT", "STRONG_SELL"):
        return "SHORT"
    return d or "UNKNOWN"


def asset_class_for_symbol(symbol: str, fallback: str = "") -> str:
    sym = (symbol or "").upper()
    if _IS_CRYPTO_RE.search(sym):
        return "CRYPTO"
    if _IS_FOREX_RE.search(sym):
        return "FOREX"
    if _IS_COMMODITY_RE.search(sym):
        return "COMMODITY"
    fb = (fallback or "").upper().strip()
    return fb if fb else "EQUITY"


def load_sym_dir_map(path: str = SYM_DIR_JSON) -> Dict[str, dict]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("by_sym_dir") or {}


def load_class_truth(path: str = CLASS_JSON) -> Dict[str, dict]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("by_class") or {}


def lookup_sym_dir(sym_dir_map: Dict[str, dict], symbol: str, direction: str) -> Optional[dict]:
    key = f"{normalize_symbol(symbol)}|{normalize_direction(direction)}"
    row = sym_dir_map.get(key)
    if not row:
        return None
    return {
        "n": int(row.get("n") or 0),
        "wr_pct": float(row.get("wr_pct") or 0.0),
        "pf": float(row.get("pf") or 0.0),
    }


def classify_intrabar_pick(
    direction: str,
    wr_pct: float,
    n: int,
    *,
    min_n_block: int = 5,
    wr_block: float = 40.0,
    wr_demote: float = 50.0,
    min_n_proven: int = 10,
) -> Tuple[str, str, str]:
    """Return (new_direction, gate_status, gate_note)."""
    if n < min_n_block:
        return direction, "INSUFFICIENT_N", f"intrabar n={n} (<{min_n_block})"

    if wr_pct < wr_block:
        return "AVOID", "BLOCKED", f"intrabar_fwd_wr={wr_pct:.1f}% n={n}"

    if direction in ("STRONG_BUY", "BUY") and wr_pct < wr_demote:
        return "WATCH", "DEMOTED", f"intrabar_fwd_wr={wr_pct:.1f}% n={n} (<{wr_demote}%)"

    if wr_pct >= wr_demote and n >= min_n_proven:
        return direction, "PROVEN_LANE", f"intrabar_fwd_wr={wr_pct:.1f}% n={n}"

    return direction, "OK", f"intrabar_fwd_wr={wr_pct:.1f}% n={n}"


def apply_class_fail_gate(
    direction: str,
    asset_class: str,
    class_truth: Dict[str, dict],
) -> Tuple[str, str]:
    """Demote BUY labels when entire class fails intrabar at n≥100."""
    ac = (asset_class or "").upper().strip()
    if direction not in ("STRONG_BUY", "BUY"):
        return direction, ""
    if ac not in _CLASS_FAIL_BLOCK:
        return direction, ""
    row = class_truth.get(ac) or {}
    n = int(row.get("n") or 0)
    verdict = (row.get("verdict") or "").upper()
    if n >= 100 and verdict == "FAIL":
        return "WATCH", f"class_intrabar_FAIL({ac} n={n})"
    return direction, ""


def stamp_intrabar_fields(
    result: dict,
    sym_dir_map: Dict[str, dict],
    class_truth: Dict[str, dict],
) -> dict:
    """Mutate scoring result with intrabar gate fields."""
    sym = result.get("symbol") or ""
    cls = result.get("class") or asset_class_for_symbol(sym, "")
    direction = result.get("direction") or "WATCH"

    row = lookup_sym_dir(sym_dir_map, sym, direction)
    if row:
        new_dir, gate_status, gate_note = classify_intrabar_pick(
            direction, row["wr_pct"], row["n"],
        )
        result["intrabar_fwd_n"] = row["n"]
        result["intrabar_fwd_wr_pct"] = row["wr_pct"]
        result["intrabar_fwd_pf"] = row["pf"]
    else:
        new_dir, gate_status, gate_note = direction, "NO_DATA", "no intrabar sym×dir cohort"

    class_dir, class_note = apply_class_fail_gate(new_dir, cls, class_truth)
    if class_note:
        new_dir = class_dir
        gate_note = f"{gate_note}; {class_note}" if gate_note else class_note
        if gate_status == "OK":
            gate_status = "CLASS_DEMOTED"

    if new_dir != direction:
        result["direction"] = new_dir
        sig = result.get("signals") or ""
        result["signals"] = f"{sig} | INTRABAR_GATE({gate_note})".strip(" |")

    if new_dir not in ("STRONG_BUY", "BUY"):
        result["position_size_pct"] = 0

    result["intrabar_gate"] = gate_status
    result["intrabar_gate_note"] = gate_note
    return result
