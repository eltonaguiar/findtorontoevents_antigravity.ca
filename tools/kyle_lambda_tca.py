#!/usr/bin/env python3
"""Kyle-style market impact + TCA summary from closed picks (HEDGE_FUND plan §3 v0).

Without L2 order-book data we use a **cross-sectional proxy** (Kyle 1985 reduced form):

  For each symbol s:
    Q_s = (n_long - n_short) / n_trades   # order-flow imbalance in [-1, 1]
    r_s = mean per-trade signed return (exit vs entry), LONG/SHORT aware

  OLS across symbols with enough trades:  r_s ≈ α + λ * Q_s

Positive λ suggests that net buying pressure coincides with higher subsequent
mean returns on that symbol in this window — interpret with care (selection,
regime, and confounding).  This is a **monitoring / research** artifact, not
a trading signal.

Data: ``audit_dashboard/data/dashboard_data.json`` → ``picks.recent_closed``.

Usage:
  python tools/kyle_lambda_tca.py
  python tools/kyle_lambda_tca.py --min-trades-per-symbol 8 --dashboard path.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = Path(__file__).resolve().parent / "kyle_lambda_results.json"


def _float(x: Any) -> float:
    try:
        if x is None or x == "":
            return 0.0
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _is_long(direction: str) -> bool:
    d = str(direction or "").upper()
    return d in ("LONG", "BUY")


def signed_return_pct(pick: Dict[str, Any]) -> float | None:
    """Signed return as fraction (e.g. 0.02 = 2%). None if invalid."""
    entry = _float(pick.get("entry_price"))
    exit_px = _float(pick.get("exit_price"))
    if entry <= 0 or exit_px <= 0:
        return None
    if _is_long(pick.get("direction")):
        return (exit_px - entry) / entry
    return (entry - exit_px) / entry


def load_closed(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    picks = doc.get("picks") or {}
    closed = picks.get("recent_closed") or []
    if not isinstance(closed, list):
        return []
    return [p for p in closed if isinstance(p, dict)]


def aggregate_by_symbol(
    closed: List[Dict[str, Any]], min_n: int
) -> Tuple[List[str], List[float], List[float], List[int]]:
    """Return parallel lists: symbol, Q_s, r_s, n — only symbols with n >= min_n."""
    by_sym: Dict[str, List[float]] = defaultdict(list)
    dir_by: Dict[str, List[bool]] = defaultdict(list)

    for p in closed:
        sym = str(p.get("symbol") or "").upper().strip()
        if not sym:
            continue
        r = signed_return_pct(p)
        if r is None:
            continue
        by_sym[sym].append(r)
        dir_by[sym].append(_is_long(p.get("direction")))

    syms: List[str] = []
    q_list: List[float] = []
    r_list: List[float] = []
    n_list: List[int] = []

    for sym, returns in by_sym.items():
        n = len(returns)
        if n < min_n:
            continue
        longs = sum(1 for x in dir_by[sym] if x)
        shorts = n - longs
        q = (longs - shorts) / float(n)
        r_bar = sum(returns) / float(n)
        syms.append(sym)
        q_list.append(q)
        r_list.append(r_bar)
        n_list.append(n)

    return syms, q_list, r_list, n_list


def ols_simple(x: List[float], y: List[float]) -> Dict[str, float]:
    """y = a + b*x + e; unweighted. Returns a, b, r2, n."""
    n = len(x)
    if n < 3:
        return {"alpha": 0.0, "lambda_kyle": 0.0, "r_squared": 0.0, "n": float(n)}

    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    syy = sum((yi - my) ** 2 for yi in y)
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    if sxx <= 1e-18:
        return {"alpha": my, "lambda_kyle": 0.0, "r_squared": 0.0, "n": float(n)}

    b = sxy / sxx
    a = my - b * mx
    # R^2
    ss_res = sum((y[i] - (a + b * x[i])) ** 2 for i in range(n))
    r2 = 1.0 - (ss_res / syy) if syy > 1e-18 else 0.0

    # stderr of b (homoskedastic)
    sigma2 = ss_res / max(n - 2, 1)
    se_b = math.sqrt(sigma2 / sxx) if sxx > 1e-18 else float("nan")

    out_ols: Dict[str, Any] = {
        "alpha": round(a, 8),
        "lambda_kyle": round(b, 8),
        "r_squared": round(max(0.0, min(1.0, r2)), 6),
        "n": float(n),
    }
    if se_b == se_b:
        out_ols["lambda_stderr"] = round(se_b, 8)
    return out_ols


def tca_distribution(closed: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Round-trip signed returns and |slippage|-free fee line (0.1% taker placeholder)."""
    rs: List[float] = []
    for p in closed:
        r = signed_return_pct(p)
        if r is not None:
            rs.append(r)
    if not rs:
        return {"n": 0}
    rs_sorted = sorted(rs)
    n = len(rs)

    def pct(p: float) -> float:
        idx = int(round((n - 1) * p))
        idx = max(0, min(n - 1, idx))
        return rs_sorted[idx]

    return {
        "n": n,
        "mean_signed_return_pct": round(100.0 * sum(rs) / n, 4),
        "median_signed_return_pct": round(100.0 * pct(0.5), 4),
        "p05_signed_return_pct": round(100.0 * pct(0.05), 4),
        "p95_signed_return_pct": round(100.0 * pct(0.95), 4),
        "assumed_round_trip_fee_pct": 0.2,
        "note": "fee is placeholder 2x 0.1% — replace when fills JSON exists",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--min-trades-per-symbol", type=int, default=8)
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument(
        "--log-experiment",
        action="store_true",
        help="append one row to tools/data/experiment_log.jsonl",
    )
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard JSON not found: %s" % path, file=sys.stderr)
        return 1

    closed = load_closed(path)
    dist = tca_distribution(closed)

    syms, q_list, r_list, n_list = aggregate_by_symbol(
        closed, max(3, args.min_trades_per_symbol)
    )
    ols = ols_simple(q_list, r_list)

    out: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "closed_picks_used": len(closed),
        "symbols_in_regression": len(syms),
        "min_trades_per_symbol": args.min_trades_per_symbol,
        "kyle_cross_sectional_ols": ols,
        "interpretation": (
            "lambda_kyle: mean signed return (per unit time in data) vs "
            "long-short imbalance Q_s per symbol. Not causal; use for trends only."
        ),
        "tca_round_trip": dist,
        "top_symbols_by_n": [
            {
                "symbol": t[0],
                "n": t[1],
                "Q_imbalance": round(t[2], 6),
                "mean_signed_r": round(t[3], 8),
            }
            for t in sorted(zip(syms, n_list, q_list, r_list), key=lambda x: -x[1])[:15]
        ],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Closed picks:", len(closed))
    print("Symbols in Kyle OLS (n>=%d): %d" % (args.min_trades_per_symbol, len(syms)))
    print("lambda_kyle:", ols.get("lambda_kyle"), " R2:", ols.get("r_squared"))
    print("Mean signed return %:", dist.get("mean_signed_return_pct"))
    print("Wrote", out_path)

    if args.log_experiment:
        try:
            sys.path.insert(0, str(REPO))
            from tools.experiment_log import append_experiment

            append_experiment(
                experiment_id="kyle_lambda_tca_%s"
                % datetime.now(timezone.utc).strftime("%Y%m%d"),
                metrics={
                    "lambda_kyle": ols.get("lambda_kyle"),
                    "r_squared": ols.get("r_squared"),
                    "symbols_regression_n": len(syms),
                    "closed_n": len(closed),
                },
                agent="cursor-composer",
                related_tools=["tools/kyle_lambda_tca.py"],
                outcome="in_progress",
                notes="§3 Kyle cross-sectional proxy from dashboard recent_closed",
            )
            print("Appended to experiment_log.jsonl")
        except Exception as exc:
            print("experiment_log skip:", exc, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
