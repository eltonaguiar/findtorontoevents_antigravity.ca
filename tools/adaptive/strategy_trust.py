"""Adaptive strategy trust scorer — hot/cold hand detection (diagnostic only).

Context: PR #145 shipped ``tools/data_integrity/_common.py`` helpers; PR #157
confirmed the full-ledger system has bootstrap 95% CI [-0.163%, -0.130%] on
expectancy (p=1.0 vs random). Independent analysis shows edge is real in
narrow pockets and strategies rotate on a multi-day cadence
(``st_fear_greed_contrarian`` collapsed elite → PF 0.68 in 2 days while
``luxalgo_filters`` rose to PF 3.05 same window). This scorer classifies each
strategy as HOT / COLD / STABLE / INSUFFICIENT from rolling windows and
exponentially-weighted PF/WR with a 23-day half-life (Phase 3 spec).

Emits JSON to ``tools/adaptive/out/strategy_trust.json``. Does NOT modify any
live gate — integration with ``hourly_performance_monitor.py`` /
``non_crypto_agent/main.py`` is a follow-up PR. Stdlib only.

Usage:
    python tools/adaptive/strategy_trust.py [--json] [--now ISO_TS]

Exit codes: 0 ok, 3 insufficient (<3 strategies with n >= 20).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any

try:
    from tools.data_integrity import _common
except ImportError:  # direct execution fallback
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from tools.data_integrity import _common  # type: ignore

MIN_TRADES = 20
MIN_RECENT_48H = 3
HOT_COLD_MIN_N = 5
HOT_RATIO = 2.0
COLD_RATIO = 0.5
HALF_LIFE_DAYS = 23.0  # implementation_plan.md Phase 3 spec
SEC_PER_DAY = 86400.0

TS_KEYS = ("closed_at", "close_time", "resolved_at", "exit_time", "timestamp", "created_at")
OUT_FILENAME = "strategy_trust.json"


# --- math helpers ---------------------------------------------------------- #
def _profit_factor(pnls: list[float]) -> float | None:
    """Return classic (unweighted) profit factor, or None if undefined."""
    if not pnls:
        return None
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss <= 0:
        if gross_win <= 0:
            return None
        return float("inf")
    return gross_win / gross_loss


def _win_rate(pnls: list[float]) -> float | None:
    if not pnls:
        return None
    wins = sum(1 for p in pnls if p > 0)
    return wins / len(pnls)


def _ewm_weight(now_ts: float, t_ts: float, half_life_days: float) -> float:
    """Exponential decay weight w_i = exp(-dt / tau) where tau = half_life / ln 2 in seconds."""
    tau = (half_life_days * SEC_PER_DAY) / math.log(2.0)
    dt = max(0.0, now_ts - t_ts)
    return math.exp(-dt / tau)


def ewm_profit_factor(trades, now_ts, half_life_days=HALF_LIFE_DAYS):
    """EWM profit factor with the given half-life (days).

    Each ``trades`` element is ``(ts_seconds, pnl_pct)``.
    """
    if not trades:
        return None
    gw = gl = 0.0
    for ts, pnl in trades:
        w = _ewm_weight(now_ts, ts, half_life_days)
        if pnl > 0:
            gw += w * pnl
        elif pnl < 0:
            gl += w * (-pnl)
    if gl <= 0:
        return float("inf") if gw > 0 else None
    return gw / gl


def ewm_win_rate(trades, now_ts, half_life_days=HALF_LIFE_DAYS):
    """EWM win rate with the given half-life (days)."""
    if not trades:
        return None
    wsum = wwin = 0.0
    for ts, pnl in trades:
        w = _ewm_weight(now_ts, ts, half_life_days)
        wsum += w
        if pnl > 0:
            wwin += w
    return (wwin / wsum) if wsum > 0 else None


def wilson_ci_95(wins: int, n: int) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion at 95% (z=1.96)."""
    if n <= 0:
        return (0.0, 0.0)
    z = 1.96
    p = wins / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    halfwidth = (z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)) / denom
    lo = max(0.0, center - halfwidth)
    hi = min(1.0, center + halfwidth)
    return (lo, hi)


# --- data loading ---------------------------------------------------------- #
def _strategy_name(p: dict) -> str:
    for key in ("strategy", "source_system", "source", "strategy_name"):
        v = p.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "UNKNOWN"


def _row_ts(p: dict) -> datetime | None:
    for key in TS_KEYS:
        if key in p:
            dt = _common.parse_ts(p.get(key))
            if dt is not None:
                return dt
    return None


def _row_pnl(p: dict) -> float | None:
    raw = p.get("pnl_pct")
    if raw is None:
        raw = p.get("pnl")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def load_strategy_trades(path: str) -> dict[str, list[tuple[float, float]]]:
    """Return ``{strategy: [(ts_seconds, pnl_pct), ...]}`` sorted ascending.

    Ghost rows are dropped. Rows without a timestamp or pnl_pct are dropped.
    """
    if not os.path.exists(path):
        return {}
    rows = _common.load_json_list(path)
    bucket: dict[str, list[tuple[float, float]]] = {}
    for p in rows:
        if _common.is_ghost_row(p):
            continue
        pnl = _row_pnl(p)
        if pnl is None:
            continue
        dt = _row_ts(p)
        if dt is None:
            continue
        strat = _strategy_name(p)
        bucket.setdefault(strat, []).append((dt.timestamp(), pnl))
    for k in bucket:
        bucket[k].sort(key=lambda x: x[0])
    return bucket


# --- per-strategy metrics -------------------------------------------------- #
def _window(trades, now_ts, days):
    cutoff = now_ts - days * SEC_PER_DAY
    return [t for t in trades if t[0] >= cutoff]


def compute_strategy_metrics(name, trades, now_ts):
    n = len(trades)
    pnls = [t[1] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    wilson_lo, wilson_hi = wilson_ci_95(wins, n)
    last_48h = _window(trades, now_ts, 2.0)
    last_7d = _window(trades, now_ts, 7.0)
    last_48h_pnls = [t[1] for t in last_48h]
    last_7d_pnls = [t[1] for t in last_7d]
    result: dict[str, Any] = {
        "strategy": name,
        "n": n,
        "wins": wins,
        "raw_wr": (wins / n) if n else None,
        "wilson_ci_95": [wilson_lo, wilson_hi],
        "ewm_pf_23d": ewm_profit_factor(trades, now_ts),
        "ewm_wr_23d": ewm_win_rate(trades, now_ts),
        "last_48h": {
            "n": len(last_48h),
            "pf": _profit_factor(last_48h_pnls),
            "wr": _win_rate(last_48h_pnls),
        },
        "last_7d": {
            "n": len(last_7d),
            "pf": _profit_factor(last_7d_pnls),
            "wr": _win_rate(last_7d_pnls),
        },
    }

    result["classification"] = classify(result)
    return result


def classify(metrics: dict[str, Any]) -> str:
    """HOT / COLD / STABLE / INSUFFICIENT per spec."""
    n = metrics.get("n", 0)
    last_48h = metrics.get("last_48h", {}) or {}
    last_7d = metrics.get("last_7d", {}) or {}
    n_48 = last_48h.get("n", 0)
    if n < MIN_TRADES or n_48 < MIN_RECENT_48H:
        return "INSUFFICIENT"

    pf_48 = last_48h.get("pf")
    pf_7 = last_7d.get("pf")

    if n_48 >= HOT_COLD_MIN_N and pf_48 is not None and pf_7 is not None:
        # Hot: recent PF at least HOT_RATIO * weekly PF.
        # inf recent PF always qualifies as hot when 7d PF is finite and positive.
        if pf_7 > 0 and (pf_48 == float("inf") or pf_48 >= HOT_RATIO * pf_7):
            return "HOT"
        if pf_48 != float("inf") and pf_48 <= COLD_RATIO * pf_7:
            return "COLD"
    return "STABLE"


# --- orchestration --------------------------------------------------------- #
def _sanitize(obj: Any) -> Any:
    """Convert inf/nan to JSON-safe strings while keeping numbers numeric."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        if math.isnan(obj):
            return None
    return obj


def build_report(
    bucket: dict[str, list[tuple[float, float]]],
    now_ts: float,
) -> dict[str, Any]:
    rows = [
        compute_strategy_metrics(name, trades, now_ts)
        for name, trades in bucket.items()
    ]
    eligible = [r for r in rows if r["n"] >= MIN_TRADES]

    hot = [r for r in eligible if r["classification"] == "HOT"]
    cold = [r for r in eligible if r["classification"] == "COLD"]
    stable = [r for r in eligible if r["classification"] == "STABLE"]
    insufficient = [r for r in rows if r["classification"] == "INSUFFICIENT"]

    def _pf_sort_key(r: dict[str, Any]) -> float:
        pf = r.get("ewm_pf_23d")
        if pf is None:
            return -1.0
        if isinstance(pf, float) and math.isinf(pf):
            return 1e18
        return float(pf)

    hot.sort(key=_pf_sort_key, reverse=True)
    cold.sort(key=_pf_sort_key)
    stable.sort(key=_pf_sort_key, reverse=True)

    return {
        "generated_at": datetime.fromtimestamp(now_ts, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "total_strategies": len(bucket),
        "eligible_strategies": len(eligible),
        "half_life_days": HALF_LIFE_DAYS,
        "hot_hand": hot,
        "cold_hand": cold,
        "stable": stable,
        "insufficient": insufficient,
    }


def _fmt_num(v: Any, spec: str = "5.2f", suffix: str = "") -> str:
    if v is None:
        return "  n/a"
    if isinstance(v, float) and math.isinf(v):
        return "  inf"
    try:
        return f"{float(v):{spec}}{suffix}"
    except (TypeError, ValueError):
        return "  n/a"


def format_console(report: dict[str, Any]) -> str:
    out = [
        "=== ADAPTIVE STRATEGY TRUST ===",
        f"Generated:  {report['generated_at']}",
        f"Strategies: total={report['total_strategies']} eligible(n>=20)={report['eligible_strategies']}",
        (
            f"Classes:    HOT={len(report['hot_hand'])} COLD={len(report['cold_hand'])} "
            f"STABLE={len(report['stable'])} INSUFF={len(report['insufficient'])}"
        ),
        f"Half-life:  {report['half_life_days']} days",
        "",
    ]
    header = f"  {'STRATEGY':<44} {'n':>5} {'48h_n':>6} {'48h_pf':>7} {'7d_pf':>7} {'ewm_pf':>7} {'ewm_wr':>7}"
    sections = [
        ("HOT HAND", report["hot_hand"], None),
        ("COLD HAND", report["cold_hand"], None),
        ("TOP STABLE (by ewm_pf_23d)", report["stable"], 10),
    ]
    for title, rows, limit in sections:
        out.append(f"--- {title} ({len(rows)}) ---")
        if not rows:
            out.append("  (none)")
            out.append("")
            continue
        out.append(header)
        for r in (rows if limit is None else rows[:limit]):
            out.append(
                "  "
                f"{r['strategy'][:44]:<44} "
                f"{r['n']:>5d} "
                f"{r['last_48h']['n']:>6d} "
                f"{_fmt_num(r['last_48h']['pf']):>7} "
                f"{_fmt_num(r['last_7d']['pf']):>7} "
                f"{_fmt_num(r['ewm_pf_23d']):>7} "
                f"{_fmt_num(r['ewm_wr_23d'], '5.2f'):>7}"
            )
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adaptive strategy trust scorer")
    parser.add_argument(
        "--closed-picks",
        default=_common.CLOSED_PICKS,
        help="path to closed_picks.json",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout")
    parser.add_argument(
        "--now",
        default=None,
        help="ISO timestamp to treat as 'now' (defaults to current UTC)",
    )
    args = parser.parse_args(argv)

    if args.now:
        dt_now = _common.parse_ts(args.now)
        if dt_now is None:
            print(f"ERROR: could not parse --now value {args.now!r}", file=sys.stderr)
            return 1
        now_ts = dt_now.timestamp()
    else:
        now_ts = datetime.now(tz=timezone.utc).timestamp()

    bucket = load_strategy_trades(args.closed_picks)
    eligible_count = sum(1 for trades in bucket.values() if len(trades) >= MIN_TRADES)
    if eligible_count < 3:
        msg = (
            f"INSUFFICIENT: only {eligible_count} strategies have n >= {MIN_TRADES} "
            f"after ghost filtering (need 3 for a meaningful report)."
        )
        print(msg, file=sys.stderr)
        return 3

    report = build_report(bucket, now_ts)
    serializable = _sanitize(report)

    if args.json:
        print(json.dumps(serializable, indent=2))
    else:
        print(format_console(report))

    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, OUT_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
