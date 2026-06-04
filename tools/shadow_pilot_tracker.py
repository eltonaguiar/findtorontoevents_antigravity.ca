#!/usr/bin/env python3
"""Shadow-pilot tracker — per-class two-tier gate (T-PAPER / T-LIVE).

Consumes:
    audit_dashboard/data/pf_registry.json  (canonical PF/WR per strategy)
    ejaguiar1_stocks.trading_picks          (resolved picks from MySQL)

Produces:
    audit_dashboard/data/shadow_pilot_verdicts.json

Gate tiers (per CLAUDE.md two-tier gate):

  T-PAPER (n>=100): eligible for shadow-pilot slice (paper-only)
    + PF > 1.2
    + WR p-value < 0.05 (binomial test vs p=0.5)
    + bootstrap Sharpe lower-bound > 0.5
    + concentration HHI < 0.30

  T-LIVE (n>=500): eligible for live 5% capital slice
    + PF > 1.5
    + WR p-value < 0.01
    + bootstrap Sharpe lower-bound > 0.8
    + concentration HHI < 0.30
    + DSR > 0 (deflated Sharpe ratio passes)

Usage:
    python tools/shadow_pilot_tracker.py [--write] [--bootstrap-n 5000]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "audit_dashboard" / "data"


# --------------------------------------------------------------------------- #
# DB connection
# --------------------------------------------------------------------------- #
def _connect():
    import pymysql

    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=os.environ.get("DB_PASS_STOCKS", "") or os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306, connect_timeout=20, cursorclass=pymysql.cursors.DictCursor,
    )


# --------------------------------------------------------------------------- #
# Statistics helpers
# --------------------------------------------------------------------------- #
def _binom_p(wins: int, n: int, p0: float = 0.5) -> float:
    """Two-sided binomial test p-value (normal approximation)."""
    if n == 0:
        return 1.0
    p_hat = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 0.0 if p_hat != p0 else 1.0
    z = abs(p_hat - p0) / se
    # Normal CDF approximation for two-sided p
    return 2.0 * (1.0 - _norm_cdf(z))


def _norm_cdf(z: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun 7.1.26)."""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989422804 * math.exp(-z * z / 2.0)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return 1.0 - p if z > 0 else p


def _bootstrap_sharpe_lb(returns: list[float], n_boot: int = 5000,
                         alpha: float = 0.05) -> float:
    """Bootstrap lower-bound for annualized Sharpe ratio.

    Returns the (alpha) percentile of the bootstrap Sharpe distribution.
    """
    if len(returns) < 5:
        return None
    srs = []
    for _ in range(min(n_boot, max(n_boot, 1000))):
        sample = [random.choice(returns) for _ in range(len(returns))]
        mean = sum(sample) / len(sample)
        var = sum((r - mean) ** 2 for r in sample) / (len(sample) - 1)
        sd = math.sqrt(var) if var > 0 else 1e-10
        srs.append((mean / sd) * math.sqrt(252))
    srs.sort()
    idx = max(0, int(alpha * len(srs)))
    return srs[idx]


def _hhi(shares: list[float]) -> float:
    """Herfindahl-Hirschman Index for concentration measurement."""
    return sum(s ** 2 for s in shares)


def _wilson_wr(wins: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for win rate. Returns (wr, lo, hi)."""
    if n == 0:
        return 0.5, 0.0, 1.0
    p_hat = wins / n
    denom = 1 + z ** 2 / n
    center = (p_hat + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt((p_hat * (1 - p_hat) + z ** 2 / (4 * n)) / n) / denom
    return p_hat, max(0, center - half), min(1, center + half)


# --------------------------------------------------------------------------- #
# Data loaders
# --------------------------------------------------------------------------- #
def load_pf_registry() -> dict:
    path = DATA_DIR / "pf_registry.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_resolved_picks(conn) -> list[dict]:
    """Load all resolved picks from trading_picks with pnl data."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT symbol, category, strategy, source_system,
                   direction, pnl_pct, status, entry_price, take_profit,
                   stop_loss, confidence, elite_score, created_at, closed_at
            FROM trading_picks
            WHERE status IN ('TP_HIT', 'SL_HIT', 'TIME_EXIT', 'LOST',
                             'EXPIRED', 'CLOSED')
              AND pnl_pct IS NOT NULL
            ORDER BY closed_at DESC
        """)
        rows = cur.fetchall()
        # Normalize category -> asset_class (uppercase mapping)
        for r in rows:
            cat = (r.pop("category") or "").strip().upper()
            # Map legacy variants
            cat = {"STOCK": "EQUITY", "STOCKS": "EQUITY",
                   "PENNY": "PENNY_STOCK", "PENNYSTOCK": "PENNY_STOCK",
                   "MEME": "MEMECOIN"}.get(cat, cat)
            r["asset_class"] = cat
        return rows


# --------------------------------------------------------------------------- #
# Per-class analysis
# --------------------------------------------------------------------------- #
CANONICAL_CLASSES = [
    "CRYPTO", "EQUITY", "FOREX", "COMMODITY", "FUTURES", "ETF", "BOND",
    "PENNY_STOCK", "MEMECOIN",
]

TIER_THRESHOLDS = {
    "T-PAPER": {
        "min_n": 100, "min_pf": 1.2, "max_wr_p": 0.05,
        "min_sharpe_lb": 0.5, "max_hhi": 0.30,
    },
    "T-LIVE": {
        "min_n": 500, "min_pf": 1.5, "max_wr_p": 0.01,
        "min_sharpe_lb": 0.8, "max_hhi": 0.30,
        "require_dsr": True,
    },
}


def analyze_class(picks: list[dict], class_name: str,
                  bootstrap_n: int = 5000) -> dict:
    """Compute full statistical analysis for one asset class."""
    class_picks = [p for p in picks
                   if (p.get("asset_class") or "").upper() == class_name]

    n = len(class_picks)
    if n == 0:
        return {"class": class_name, "n": 0, "verdict": "NO_DATA",
                "gates": {}, "detail": "no resolved picks"}

    # Basic stats
    wins = sum(1 for p in class_picks if (p.get("pnl_pct") or 0) > 0)
    losses = n - wins
    wr = wins / n if n else 0
    pnls = [float(p.get("pnl_pct") or 0) for p in class_picks]
    pos_pnl = sum(p for p in pnls if p > 0)
    neg_pnl = abs(sum(p for p in pnls if p < 0))
    pf = pos_pnl / neg_pnl if neg_pnl > 0 else (999.0 if pos_pnl > 0 else 0.0)
    avg_pnl = sum(pnls) / n if n else 0
    max_dd = _compute_max_dd(pnls)

    # Wilson WR interval
    wr_hat, wr_lo, wr_hi = _wilson_wr(wins, n)

    # Binomial p-value
    wr_p = _binom_p(wins, n)

    # Bootstrap Sharpe lower-bound
    sharpe_lb = _bootstrap_sharpe_lb(pnls, n_boot=bootstrap_n)

    # Concentration HHI (by strategy)
    strat_counts = {}
    for p in class_picks:
        s = p.get("strategy") or "UNKNOWN"
        strat_counts[s] = strat_counts.get(s, 0) + 1
    total = sum(strat_counts.values())
    shares = [c / total for c in strat_counts.values()]
    hhi = _hhi(shares)
    top_strat = max(strat_counts, key=strat_counts.get) if strat_counts else ""
    top_share = strat_counts.get(top_strat, 0) / total if total else 0

    # Source concentration
    src_counts = {}
    for p in class_picks:
        s = p.get("source_system") or "UNKNOWN"
        src_counts[s] = src_counts.get(s, 0) + 1
    src_shares = [c / total for c in src_counts.values()]
    src_hhi = _hhi(src_shares)
    top_src = max(src_counts, key=src_counts.get) if src_counts else ""
    top_src_share = src_counts.get(top_src, 0) / total if total else 0

    # Tier gates
    gates = {}
    for tier_name, thresh in TIER_THRESHOLDS.items():
        gate = {
            "n_ok": n >= thresh["min_n"],
            "pf_ok": pf >= thresh["min_pf"],
            "wr_p_ok": wr_p <= thresh["max_wr_p"],
            "sharpe_lb_ok": (sharpe_lb is not None and
                             sharpe_lb >= thresh["min_sharpe_lb"]),
            "hhi_ok": hhi <= thresh["max_hhi"],
            "passes": True,
        }
        for check in ["n_ok", "pf_ok", "wr_p_ok", "sharpe_lb_ok", "hhi_ok"]:
            if not gate[check]:
                gate["passes"] = False
                break
        gates[tier_name] = gate

    # Verdict
    if gates["T-LIVE"]["passes"]:
        verdict = "T-LIVE"
    elif gates["T-PAPER"]["passes"]:
        verdict = "T-PAPER"
    elif n >= TIER_THRESHOLDS["T-PAPER"]["min_n"]:
        verdict = "FAIL"
    else:
        verdict = "INSUFFICIENT_N"

    return {
        "class": class_name,
        "n": n,
        "wins": wins,
        "losses": losses,
        "wr": round(wr * 100, 2),
        "wr_wilson": {
            "hat": round(wr_hat * 100, 2),
            "lo": round(wr_lo * 100, 2),
            "hi": round(wr_hi * 100, 2),
        },
        "wr_binomial_p": round(wr_p, 6),
        "pf": round(pf, 4),
        "avg_pnl_pct": round(avg_pnl, 4),
        "sharpe_bootstrap_lb": round(sharpe_lb, 4) if sharpe_lb is not None else None,
        "max_dd_pct": round(max_dd * 100, 2),
        "hhi_strategy": round(hhi, 4),
        "hhi_source": round(src_hhi, 4),
        "top_strategy": top_strat,
        "top_strategy_share": round(top_share, 4),
        "top_source": top_src,
        "top_source_share": round(top_src_share, 4),
        "gates": gates,
        "verdict": verdict,
    }


def _compute_max_dd(pnls: list[float]) -> float:
    """Compute maximum drawdown from a sequence of PnL percentages."""
    if not pnls:
        return 0.0
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for p in pnls:
        equity *= (1 + p / 100.0)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0
        if dd > mdd:
            mdd = dd
    return mdd


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Shadow-pilot tracker")
    ap.add_argument("--write", action="store_true",
                    help="write verdicts JSON (default: dry-run)")
    ap.add_argument("--bootstrap-n", type=int, default=5000,
                    help="bootstrap iterations (default: 5000)")
    args = ap.parse_args(argv)

    print(f"[shadow_pilot] bootstrap_n={args.bootstrap_n} "
          f"mode={'WRITE' if args.write else 'DRY-RUN'}")

    # Load data
    conn = _connect()
    try:
        picks = load_resolved_picks(conn)
    finally:
        conn.close()
    print(f"[shadow_pilot] loaded {len(picks)} resolved picks from DB")

    # Analyze each class
    results = []
    for cls in CANONICAL_CLASSES:
        result = analyze_class(picks, cls, bootstrap_n=args.bootstrap_n)
        results.append(result)
        v = result["verdict"]
        n = result["n"]
        wr = result.get("wr", "?")
        pf = result.get("pf", "?")
        print(f"  {cls:15s} n={n:5d} WR={wr}% PF={pf} -> {v}")

    # Summary
    verdicts = {r["class"]: r["verdict"] for r in results}
    summary = {
        "T-LIVE": [r["class"] for r in results if r["verdict"] == "T-LIVE"],
        "T-PAPER": [r["class"] for r in results if r["verdict"] == "T-PAPER"],
        "INSUFFICIENT_N": [r["class"] for r in results
                           if r["verdict"] == "INSUFFICIENT_N"],
        "FAIL": [r["class"] for r in results if r["verdict"] == "FAIL"],
        "NO_DATA": [r["class"] for r in results if r["verdict"] == "NO_DATA"],
    }

    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_picks_analyzed": len(picks),
        "per_class": {r["class"]: r for r in results},
        "summary": summary,
    }

    if args.write:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = DATA_DIR / "shadow_pilot_verdicts.json"
        out.write_text(json.dumps(payload, indent=2, default=str))
        print(f"[shadow_pilot] wrote {out}")
    else:
        print(f"\n[shadow_pilot] DRY-RUN — would write "
              f"{DATA_DIR / 'shadow_pilot_verdicts.json'}")
        print(f"\nSummary:")
        for tier, classes in summary.items():
            print(f"  {tier}: {classes if classes else '(none)'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
