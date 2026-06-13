#!/usr/bin/env python3
"""Strategy Analytics — statistical validation of live trading strategies.

Computes per-(asset_class, strategy):
  1. Binomial significance test (two-sided, H0: WR = 50%)
  2. Annualized Sharpe ratio (excess return / vol)
  3. Maximum drawdown (peak-to-trough cumulative PnL)
  4. OOS backtest (70/30 purged train/test split)

Usage:
    python3 tools/strategy_analytics.py
    python3 tools/strategy_analytics.py --min-trades 30
    python3 tools/strategy_analytics.py --min-trades 30 --oos-ratio 0.30
    python3 tools/strategy_analytics.py --output-json audit_dashboard/data/strategy_analytics.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.db_env import get_stocks_creds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("strategy_analytics")

_RISK_FREE_RATE = 0.04
_ANNUALIZATION_FACTOR = 252


def _connect():
    import pymysql

    creds = get_stocks_creds(raise_on_missing=True)
    return pymysql.connect(
        host=creds["host"],
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
        port=creds["port"],
        connect_timeout=creds["connect_timeout"],
        read_timeout=creds["read_timeout"],
        cursorclass=pymysql.cursors.DictCursor,
    )


_CLASS_MAP = {
    "STOCKS": "EQUITY",
    "STOCK": "EQUITY",
    "MEME": "MEMECOIN",
    "PENNY": "PENNY_STOCK",
    "PENNYSTOCK": "PENNY_STOCK",
    "": "UNKNOWN",
}


def normalize_class(ac: str) -> str:
    ac = str(ac or "").upper().strip()
    return _CLASS_MAP.get(ac, ac or "UNKNOWN")


def fetch_all_resolved() -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT asset_class, strategy, status, pnl_pct, resolved_at
        FROM at_pick_outcomes
        WHERE status IN ('WON', 'LOST')
        ORDER BY strategy, resolved_at
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ── Statistical Functions ─────────────────────────────────────────────────

def _norm_cdf(z: float) -> float:
    """Standard normal CDF via Abramowitz & Stegun approximation."""
    if z < -8:
        return 0.0
    if z > 8:
        return 1.0
    a1, a2, a3, a4, a5 = (
        0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    )
    p = 0.3275911
    sign = 1 if z >= 0 else -1
    z_abs = abs(z)
    t = 1.0 / (1.0 + p * z_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-z_abs * z_abs / 2)
    return 0.5 * (1.0 + sign * y)


def binomial_test(wins: int, n: int, p0: float = 0.5) -> float:
    """Two-sided binomial test p-value (normal approximation)."""
    if n == 0:
        return 1.0
    p_hat = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 0.0 if p_hat != p0 else 1.0
    z = abs(p_hat - p0) / se
    return 2.0 * (1.0 - _norm_cdf(z))


def wilson_ci(wins: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    from math import sqrt
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
    p_hat = wins / n
    denom = 1 + z * z / n
    centre = (p_hat + z * z / (2 * n)) / denom
    margin = z * sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def annualized_sharpe(pnl_pcts: List[float]) -> float:
    """Annualized Sharpe ratio from per-trade PnL percentages."""
    if len(pnl_pcts) < 2:
        return 0.0
    n = len(pnl_pcts)
    mean_r = sum(pnl_pcts) / n
    var_r = sum((r - mean_r) ** 2 for r in pnl_pcts) / (n - 1)
    std_r = math.sqrt(var_r) if var_r > 0 else 0.0
    if std_r == 0:
        return 0.0
    excess = mean_r - (_RISK_FREE_RATE / _ANNUALIZATION_FACTOR)
    return (excess / std_r) * math.sqrt(_ANNUALIZATION_FACTOR)


def max_drawdown(pnl_pcts: List[float]) -> float:
    """Maximum drawdown as percentage from peak cumulative PnL."""
    if not pnl_pcts:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    mdd = 0.0
    for r in pnl_pcts:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > mdd:
            mdd = dd
    return round(mdd, 4)


def profit_factor(pnl_pcts: List[float]) -> float:
    """Profit factor: sum(wins) / |sum(losses)|."""
    gains = sum(r for r in pnl_pcts if r > 0)
    losses = abs(sum(r for r in pnl_pcts if r < 0))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return round(gains / losses, 4)


def _resolve_at_key(t: Dict[str, Any]) -> str:
    """Normalize resolved_at to a sortable string."""
    v = t.get("resolved_at")
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return v.isoformat()


def oos_split(
    trades: List[Dict[str, Any]], oos_ratio: float = 0.30, purge_days: int = 7
) -> Tuple[List[Dict], List[Dict]]:
    """70/30 purged train/test split with embargo buffer."""
    sorted_trades = sorted(trades, key=_resolve_at_key)
    n = len(sorted_trades)
    if n < 10:
        return sorted_trades, []

    split_idx = int(n * (1 - oos_ratio))
    train_raw = sorted_trades[:split_idx]
    test_raw = sorted_trades[split_idx:]

    if not train_raw or not test_raw:
        return sorted_trades, []

    last_train_time = train_raw[-1].get("resolved_at")
    if last_train_time and purge_days > 0:
        from datetime import timedelta
        if isinstance(last_train_time, str):
            last_train_dt = datetime.datetime.fromisoformat(last_train_time.replace("Z", "+00:00"))
        else:
            last_train_dt = last_train_time
        purge_cutoff = last_train_dt + timedelta(days=purge_days)
        filtered = []
        for t in test_raw:
            raw = t.get("resolved_at")
            if raw is None:
                continue
            if isinstance(raw, str):
                dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            else:
                dt = raw
            if dt > purge_cutoff:
                filtered.append(t)
        test_raw = filtered

    return train_raw, test_raw


# ── Analysis ──────────────────────────────────────────────────────────────

def analyze_strategy(
    trades: List[Dict[str, Any]],
    oos_ratio: float = 0.30,
    min_trades: int = 30,
) -> Optional[Dict[str, Any]]:
    n = len(trades)
    if n < min_trades:
        return None

    first = trades[0]
    asset_class = normalize_class(first.get("asset_class", ""))
    strategy = first.get("strategy", "(unattributed)")

    wins = sum(1 for t in trades if (t.get("pnl_pct") or 0) > 0 or t.get("status") == "WON")
    losses = n - wins
    wr = round(100.0 * wins / n, 2)
    pnl_list = [float(t.get("pnl_pct") or 0) for t in trades]
    total_pnl = round(sum(pnl_list), 4)
    avg_pnl = round(total_pnl / n, 4)

    p_value = binomial_test(wins, n)
    ci_lo, ci_hi = wilson_ci(wins, n)
    sharpe = annualized_sharpe(pnl_list)
    mdd = max_drawdown(pnl_list)
    pf = profit_factor(pnl_list)

    significant = p_value < 0.05
    if significant:
        if wr > 50:
            verdict = "SIGNIFICANT_EDGE"
        else:
            verdict = "SIGNIFICANT_DRAIN"
    else:
        verdict = "NO_SIGNAL"

    train, test = oos_split(trades, oos_ratio=oos_ratio)
    oos_result = None
    if test:
        test_wins = sum(1 for t in test if (t.get("pnl_pct") or 0) > 0 or t.get("status") == "WON")
        test_n = len(test)
        test_wr = round(100.0 * test_wins / test_n, 2) if test_n else 0
        test_pnl = [float(t.get("pnl_pct") or 0) for t in test]
        test_sharpe = annualized_sharpe(test_pnl)
        test_pf = profit_factor(test_pnl)
        train_wins = sum(1 for t in train if (t.get("pnl_pct") or 0) > 0 or t.get("status") == "WON")
        train_n = len(train)
        train_wr = round(100.0 * train_wins / train_n, 2) if train_n else 0
        train_pnl = [float(t.get("pnl_pct") or 0) for t in train]
        train_sharpe = annualized_sharpe(train_pnl)
        train_pf = profit_factor(train_pnl)

        wr_decay = round(train_wr - test_wr, 2)
        sharpe_decay = round(train_sharpe - test_sharpe, 4)
        overfit = wr_decay > 15 or sharpe_decay > 1.0

        oos_result = {
            "train_n": train_n,
            "train_wr": train_wr,
            "train_sharpe": round(train_sharpe, 4),
            "train_pf": train_pf,
            "test_n": test_n,
            "test_wr": test_wr,
            "test_sharpe": round(test_sharpe, 4),
            "test_pf": test_pf,
            "wr_decay": wr_decay,
            "sharpe_decay": sharpe_decay,
            "overfit_risk": overfit,
        }

    return {
        "asset_class": asset_class,
        "strategy": strategy,
        "n": n,
        "wins": wins,
        "losses": losses,
        "wr": wr,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
        "p_value": round(p_value, 6),
        "significant": significant,
        "verdict": verdict,
        "ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
        "sharpe": round(sharpe, 4),
        "max_drawdown": mdd,
        "profit_factor": pf,
        "oos": oos_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Statistical validation of live trading strategies.",
    )
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--oos-ratio", type=float, default=0.30)
    parser.add_argument("--output-json", type=str, default=None)
    args = parser.parse_args()

    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log.info("Fetching resolved trades from at_pick_outcomes...")
    rows = fetch_all_resolved()
    log.info("Fetched %d resolved trades", len(rows))

    buckets: Dict[Tuple[str, str], List[Dict]] = {}
    for r in rows:
        ac = normalize_class(r.get("asset_class"))
        strat = str(r.get("strategy") or "").strip() or "(unattributed)"
        key = (ac, strat)
        buckets.setdefault(key, []).append(r)

    log.info("Analyzing %d strategy buckets...", len(buckets))
    results = []
    for (ac, strat), trades in buckets.items():
        result = analyze_strategy(trades, oos_ratio=args.oos_ratio, min_trades=args.min_trades)
        if result:
            results.append(result)

    results.sort(key=lambda x: (x["asset_class"], -x["n"]))

    significant_edge = [r for r in results if r["verdict"] == "SIGNIFICANT_EDGE"]
    significant_drain = [r for r in results if r["verdict"] == "SIGNIFICANT_DRAIN"]
    overfit = [r for r in results if (r.get("oos") or {}).get("overfit_risk")]

    report = {
        "generated_at": started_at,
        "thresholds": {
            "min_trades": args.min_trades,
            "oos_ratio": args.oos_ratio,
        },
        "total_strategies": len(results),
        "summary": {
            "significant_edge": len(significant_edge),
            "significant_drain": len(significant_drain),
            "no_signal": len(results) - len(significant_edge) - len(significant_drain),
            "overfit_risk": len(overfit),
        },
        "strategies": results,
    }

    print(json.dumps(report, indent=2, default=str))

    output_path = Path(args.output_json) if args.output_json else Path("audit_dashboard/data/strategy_analytics.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    log.info("Report written to %s", output_path)

    if significant_edge:
        log.info("SIGNIFICANT EDGE: %s", [r["strategy"] for r in significant_edge])
    if significant_drain:
        log.warning("SIGNIFICANT DRAIN: %s", [r["strategy"] for r in significant_drain])


if __name__ == "__main__":
    main()
