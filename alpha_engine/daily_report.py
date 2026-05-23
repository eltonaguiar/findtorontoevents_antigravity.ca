"""
daily_report.py — Automated daily performance report generator.

Reads closed picks, active picks, and dashboard payload to produce a
structured daily report dict.  Stdlib only: csv, json, datetime.
"""

import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ASSET_CLASSES = ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "INDEX")
HF_TIERS = ("S", "A", "B")
BIG_MOVER_THRESHOLD = 0.03          # |PnL| > 3 %
KILL_MIN_TRADES = 20
KILL_PF_CEIL = 0.70
KILL_WR_FLOOR = 0.35
EXPOSURE_WARN_PCT = 5.0
TOP_SYSTEMS = 10
LOOKBACK_7D_DAYS = 7


# ---------------------------------------------------------------------------
# Helpers (same helpers used in policy_eval — kept local for standalone use)
# ---------------------------------------------------------------------------

def _parse_iso(ts: str) -> datetime:
    """Parse ISO-8601 timestamp, tolerating Z suffix."""
    ts = ts.replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {ts}")


def _safe_mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _safe_median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def _profit_factor(pnls: List[float]) -> float:
    gains = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p <= 0))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _win_rate(pnls: List[float]) -> float:
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls)


# ---------------------------------------------------------------------------
# Pick loaders
# ---------------------------------------------------------------------------

def _load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("picks") or data.get("closed_picks") or data.get("active_picks") or []
    return data


def _load_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", newline="") as f:
        return list(csv.DictReader(f))


def load_picks(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    if path.endswith(".csv"):
        return _load_csv(path)
    return _load_json(path)


def load_payload(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# PnL extraction
# ---------------------------------------------------------------------------

def _extract_pnl(pick: Dict[str, Any]) -> Optional[float]:
    for key in ("pnl", "pnl_pct", "return_pct", "return", "pnl_percent"):
        val = pick.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    entry = pick.get("entry_price") or pick.get("entry")
    exit_ = pick.get("exit_price") or pick.get("exit")
    side = pick.get("side", "long")
    if entry is not None and exit_ is not None:
        try:
            entry, exit_ = float(entry), float(exit_)
            if side == "short":
                return (entry - exit_) / entry
            return (exit_ - entry) / entry
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return None


# ---------------------------------------------------------------------------
# Metric builders
# ---------------------------------------------------------------------------

def _overall_metrics(picks: List[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    pnls = []
    pnls_7d = []
    today_str = now.strftime("%Y-%m-%d")

    for p in picks:
        pnl = _extract_pnl(p)
        if pnl is None:
            continue
        pnls.append(pnl)
        closed = p.get("closed_at") or p.get("exit_time") or p.get("timestamp")
        if closed:
            try:
                t = _parse_iso(closed)
                if t >= now - timedelta(days=LOOKBACK_7D_DAYS):
                    pnls_7d.append(pnl)
                if t.strftime("%Y-%m-%d") == today_str:
                    pass  # counted in trades_today
            except (ValueError, TypeError):
                pass

    trades_today = 0
    for p in picks:
        closed = p.get("closed_at") or p.get("exit_time") or p.get("timestamp")
        if closed:
            try:
                if _parse_iso(closed).strftime("%Y-%m-%d") == today_str:
                    trades_today += 1
            except (ValueError, TypeError):
                pass

    pf = _profit_factor(pnls)
    return {
        "win_rate": round(_win_rate(pnls), 4),
        "profit_factor": round(pf, 4) if pf != float("inf") else 999.99,
        "avg_pnl": round(_safe_mean(pnls), 6),
        "median_pnl": round(_safe_median(pnls), 6),
        "trades_today": trades_today,
        "trades_7d": len(pnls_7d),
    }


def _by_asset_class(picks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[float]] = {}
    for p in picks:
        ac = (p.get("asset_class") or p.get("asset") or "").upper()
        if ac not in ASSET_CLASSES:
            # Try to infer from symbol
            sym = (p.get("symbol") or "").upper()
            if any(x in sym for x in ("/", "USD", "BTC", "ETH", "SOL")):
                ac = "CRYPTO"
            else:
                ac = "EQUITY"
        pnl = _extract_pnl(p)
        if pnl is not None:
            groups.setdefault(ac, []).append(pnl)

    result = {}
    for ac in sorted(groups):
        pnls = groups[ac]
        pf = _profit_factor(pnls)
        result[ac] = {
            "n": len(pnls),
            "win_rate": round(_win_rate(pnls), 4),
            "profit_factor": round(pf, 4) if pf != float("inf") else 999.99,
            "avg_pnl": round(_safe_mean(pnls), 6),
            "median_pnl": round(_safe_median(pnls), 6),
        }
    return result


def _by_system(picks: List[Dict[str, Any]], top_n: int = TOP_SYSTEMS) -> List[Dict[str, Any]]:
    groups: Dict[str, List[float]] = {}
    for p in picks:
        sys_name = p.get("system") or p.get("source") or p.get("strategy") or "unknown"
        pnl = _extract_pnl(p)
        if pnl is not None:
            groups.setdefault(sys_name, []).append(pnl)

    rows = []
    for name, pnls in groups.items():
        pf = _profit_factor(pnls)
        rows.append({
            "system": name,
            "n": len(pnls),
            "win_rate": round(_win_rate(pnls), 4),
            "profit_factor": round(pf, 4) if pf != float("inf") else 999.99,
            "avg_pnl": round(_safe_mean(pnls), 6),
        })
    # Sort by profit factor descending, then by n descending
    rows.sort(key=lambda r: (r["profit_factor"], r["n"]), reverse=True)
    return rows[:top_n]


def _big_movers(picks: List[Dict[str, Any]], threshold: float = BIG_MOVER_THRESHOLD) -> List[Dict[str, Any]]:
    movers = []
    for p in picks:
        pnl = _extract_pnl(p)
        if pnl is not None and abs(pnl) > threshold:
            movers.append({
                "symbol": p.get("symbol", "?"),
                "system": p.get("system") or p.get("source") or "?",
                "pnl": round(pnl, 6),
                "pnl_pct": round(pnl * 100, 2),
                "closed_at": p.get("closed_at") or p.get("exit_time") or p.get("timestamp") or "?",
            })
    movers.sort(key=lambda m: abs(m["pnl"]), reverse=True)
    return movers


def _kill_candidates(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strategies with n>=20, PF<0.7, WR<35%."""
    groups: Dict[str, List[float]] = {}
    for p in picks:
        sys_name = p.get("system") or p.get("source") or p.get("strategy") or "unknown"
        pnl = _extract_pnl(p)
        if pnl is not None:
            groups.setdefault(sys_name, []).append(pnl)

    candidates = []
    for name, pnls in groups.items():
        if len(pnls) < KILL_MIN_TRADES:
            continue
        pf = _profit_factor(pnls)
        wr = _win_rate(pnls)
        if pf < KILL_PF_CEIL and wr < KILL_WR_FLOOR:
            candidates.append({
                "system": name,
                "n": len(pnls),
                "win_rate": round(wr, 4),
                "profit_factor": round(pf, 4) if pf != float("inf") else 999.99,
                "avg_pnl": round(_safe_mean(pnls), 6),
                "reason": f"n={len(pnls)}, PF={pf:.2f}<0.7, WR={wr:.2f}<0.35",
            })
    candidates.sort(key=lambda c: c["profit_factor"])
    return candidates


def _exposure_warnings(picks: List[Dict[str, Any]], limit: float = EXPOSURE_WARN_PCT) -> List[Dict[str, Any]]:
    """Symbols whose weight_pct exceeds limit."""
    warnings = []
    for p in picks:
        pct = float(p.get("weight_pct", 0) or p.get("allocation_pct", 0) or 0)
        sym = p.get("symbol", "?")
        if pct > limit:
            warnings.append({
                "symbol": sym,
                "weight_pct": round(pct, 2),
                "limit_pct": limit,
                "action": f"Trim {sym} from {pct:.1f}% to <= {limit:.1f}%",
            })
    warnings.sort(key=lambda w: w["weight_pct"], reverse=True)
    return warnings


def _hf_tier_summary(picks: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count picks by HF tier (S/A/B/non_hf)."""
    counts = {"S": 0, "A": 0, "B": 0, "non_hf": 0}
    for p in picks:
        tier = (p.get("hf_tier") or p.get("tier") or "").upper()
        if tier in HF_TIERS:
            counts[tier] += 1
        else:
            counts["non_hf"] += 1
    return counts


def _data_lag(payload: Dict[str, Any]) -> Optional[float]:
    """Return hours since payload generated_at, or None."""
    gen = payload.get("generated_at") or payload.get("generated_at_utc")
    if not gen:
        return None
    try:
        t = _parse_iso(gen)
        now = datetime.now(timezone.utc)
        # Make t timezone-aware if naive
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return round((now - t).total_seconds() / 3600.0, 2)
    except (ValueError, TypeError):
        return None


def _policy_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract policy metadata from payload or feature flags file."""
    # Try payload first, then fall back to feature_flags.json
    version = payload.get("policy_version")
    last_change = payload.get("last_policy_change_at")
    flags = payload.get("feature_flags")

    if flags is None:
        # Try loading feature_flags.json
        ff_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "feature_flags.json"
        )
        if os.path.isfile(ff_path):
            with open(ff_path, "r") as f:
                ff = json.load(f)
            version = version or ff.get("policy_version")
            last_change = last_change or ff.get("last_policy_change_at")
            flags = ff

    return {
        "version": version or "unknown",
        "flags": flags or {},
        "last_change": last_change or "unknown",
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_daily_report(
    closed_picks_path: str,
    active_picks_path: str,
    payload_path: str,
) -> Dict[str, Any]:
    """Generate the complete daily report dict.

    Parameters
    ----------
    closed_picks_path : str
        Path to closed/past picks file (JSON or CSV).
    active_picks_path : str
        Path to currently active picks file (JSON or CSV).
    payload_path : str
        Path to dashboard_payload.json (or similar).

    Returns
    -------
    dict with keys: date, overall, by_asset_class, by_system, big_movers,
                    kill_candidates, exposure_warnings, hf_tier_summary,
                    data_lag, policy_status
    """
    now = datetime.now(timezone.utc)
    closed_picks = load_picks(closed_picks_path)
    active_picks = load_picks(active_picks_path)

    # Load payload for metadata
    try:
        payload = load_payload(payload_path)
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {}

    report = {
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "overall": _overall_metrics(closed_picks, now),
        "by_asset_class": _by_asset_class(closed_picks),
        "by_system": _by_system(closed_picks),
        "big_movers": _big_movers(closed_picks),
        "kill_candidates": _kill_candidates(closed_picks),
        "exposure_warnings": _exposure_warnings(active_picks),
        "hf_tier_summary": _hf_tier_summary(active_picks),
        "data_lag_hours": _data_lag(payload),
        "policy_status": _policy_status(payload),
    }
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate daily performance report")
    parser.add_argument("--closed", default="closed_picks.json",
                        help="Path to closed picks (JSON/CSV)")
    parser.add_argument("--active", default="active_picks.json",
                        help="Path to active picks (JSON/CSV)")
    parser.add_argument("--payload", default="dashboard_payload.json",
                        help="Path to dashboard payload JSON")
    parser.add_argument("--output", default=None,
                        help="Write JSON report to file (default: stdout)")
    args = parser.parse_args()

    report = generate_daily_report(args.closed, args.active, args.payload)
    out = json.dumps(report, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(out)
        print(f"Report written to {args.output}")
    else:
        print(out)
