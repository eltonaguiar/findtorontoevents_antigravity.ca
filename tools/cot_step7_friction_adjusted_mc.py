#!/usr/bin/env python3
"""COT Step 7 friction-adjusted Risk-of-Ruin MC + Deflated Sharpe Ratio.

Per quant_rescue_master_plan Action #3 (2026-05-12). Companion to
`tools/cot_step7_risk_of_ruin_mc.py` which uses a flat $10 round-trip
cost. This version adds:

  1. Per-fill slippage: 0.5 tick × volatility-state multiplier
     - Vol-state derived from rolling pnl-stdev quartile of the
       trailing 20-trade window (a proxy when ATR data is not in
       trading_picks). vol_mult in {0.75, 1.0, 1.25, 1.5} for the
       low/normal/elevated/high quartiles.
     - 2 fills per round trip (entry + exit), so total slippage_pct
       = 2 × 0.5_tick_pct × vol_mult = 1 tick_pct × vol_mult.

  2. Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) at n_trials=500
     to deflate for multiple-testing bias. Master-plan gate:
       friction-adjusted DSR >= 0.85 at n_trials=500
     If not, CT=F is NOT LIVE_ELIGIBLE regardless of paper-pilot result.

Inputs: trading_picks (DB) same as Step 7 baseline.
Outputs: audit_dashboard/data/cot_step7_friction_adjusted_mc.json

NFA: research surface only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

# Contract spec (matches cot_step7_risk_of_ruin_mc.py + cot_paper_pilot.py)
CONTRACT_NOTIONAL_LBS = 50_000
TICK_USD = 5.0
ROUND_TRIP_COMM_USD = 10.0
BASE_PRICE_USD_PER_LB = 0.70
NOTIONAL_USD = BASE_PRICE_USD_PER_LB * CONTRACT_NOTIONAL_LBS

# 1 tick = $5 on a $35,000 notional = 0.01429% of notional
TICK_PCT_OF_NOTIONAL = TICK_USD / NOTIONAL_USD * 100.0  # 0.01429

MAINTENANCE_MARGIN_USD = 1500.0
TIERS = [5_000, 10_000, 25_000, 50_000]

# Volatility-state multiplier table (quartile of rolling 20-trade |pnl| stdev)
VOL_MULT_BY_QUARTILE = {0: 0.75, 1: 1.0, 2: 1.25, 3: 1.5}


def connect():
    pw = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASSWORD")
    if not pw:
        raise RuntimeError("DB_STOCKS_PASSWORD env var required")
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=pw,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=60,
    )


def fetch_pnls_ordered() -> list[float]:
    c = connect()
    cur = c.cursor()
    cur.execute("""
        SELECT pnl_pct FROM trading_picks
         WHERE strategy='cot_positioning' AND symbol='CT=F'
           AND status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT')
           AND pnl_pct IS NOT NULL
         ORDER BY COALESCE(closed_at, created_at) ASC
        """)
    pnls = [float(r[0]) for r in cur.fetchall() if r[0] is not None]
    c.close()
    return pnls


def rolling_vol_quartile(pnls: list[float], window: int = 20) -> list[int]:
    """Per-trade quartile (0-3) of trailing-window |pnl| stdev.

    Trade i's quartile is computed from |pnls[i-window..i-1]|. First
    `window` trades fall back to quartile 1 (normal).
    """
    n = len(pnls)
    if n < window + 1:
        return [1] * n
    # Compute rolling stdevs
    stdevs = []
    for i in range(n):
        if i < window:
            stdevs.append(None)
        else:
            w = [abs(p) for p in pnls[i - window:i]]
            stdevs.append(statistics.stdev(w) if len(w) > 1 else 0.0)
    valid = [s for s in stdevs if s is not None]
    if not valid:
        return [1] * n
    sv = sorted(valid)
    q1 = sv[int(len(sv) * 0.25)]
    q2 = sv[int(len(sv) * 0.50)]
    q3 = sv[int(len(sv) * 0.75)]
    out = []
    for s in stdevs:
        if s is None:
            out.append(1)
        elif s <= q1:
            out.append(0)
        elif s <= q2:
            out.append(1)
        elif s <= q3:
            out.append(2)
        else:
            out.append(3)
    return out


def apply_friction(pnls: list[float], quartiles: list[int]) -> list[float]:
    """Subtract slippage (in pnl_pct units) per trade based on vol quartile.

    2 fills × 0.5 tick × vol_mult = 1 tick_pct × vol_mult per round trip.
    """
    adj = []
    for p, q in zip(pnls, quartiles):
        mult = VOL_MULT_BY_QUARTILE.get(q, 1.0)
        slippage_pct = TICK_PCT_OF_NOTIONAL * mult  # in pnl_pct units already
        adj.append(p - slippage_pct)
    return adj


def _moment(xs: list[float], k: int) -> float:
    m = statistics.mean(xs)
    return sum((x - m) ** k for x in xs) / len(xs)


def sharpe_ratio(pnls: list[float]) -> float:
    if len(pnls) < 2:
        return 0.0
    s = statistics.stdev(pnls)
    if s == 0:
        return 0.0
    return statistics.mean(pnls) / s


def skewness(pnls: list[float]) -> float:
    if len(pnls) < 3:
        return 0.0
    m2 = _moment(pnls, 2)
    m3 = _moment(pnls, 3)
    if m2 == 0:
        return 0.0
    return m3 / (m2 ** 1.5)


def kurtosis(pnls: list[float]) -> float:
    """Pearson kurtosis (NOT excess) — needed for DSR formula."""
    if len(pnls) < 4:
        return 3.0
    m2 = _moment(pnls, 2)
    m4 = _moment(pnls, 4)
    if m2 == 0:
        return 3.0
    return m4 / (m2 ** 2)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_inv_cdf(p: float) -> float:
    """Beasley-Springer-Moro approximation of the inverse standard normal CDF.

    Accurate to ~1e-9 over (0, 1) — adequate for DSR's SR_expected term.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
          4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    p_low = 0.02425
    p_high = 1 - p_low
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5])*q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
            ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)


def deflated_sharpe_ratio(pnls: list[float], n_trials: int = 500) -> dict:
    """DSR per Bailey & Lopez de Prado (2014).

    DSR = Phi( (SR - SR_expected) * sqrt((n-1) / (1 - skew*SR + (kurt-1)/4 * SR^2)) )

    SR_expected = sqrt(2*ln(n_trials)) * (1 - euler_gamma) / approx
                  (Bailey & Lopez de Prado simplification)

    Output: DSR in [0, 1] interpretable as 1 - P(SR_observed | null SR=0)
    """
    n = len(pnls)
    if n < 4:
        return {"n": n, "sr": 0.0, "dsr": 0.0,
                "note": "n<4 — insufficient for DSR"}
    sr = sharpe_ratio(pnls)
    skew = skewness(pnls)
    kurt = kurtosis(pnls)

    # E[max_n] of n_trials independent SR observations, from B&L de P:
    # SR_expected = (1 - euler) * Phi^-1(1 - 1/N) + euler * Phi^-1(1 - 1/(N*e))
    EULER = 0.5772156649015328606
    try:
        z1 = _norm_inv_cdf(1.0 - 1.0 / n_trials)
        z2 = _norm_inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    except ValueError:
        z1, z2 = 0.0, 0.0
    sr_expected = (1.0 - EULER) * z1 + EULER * z2

    # DSR
    denom_var = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr
    if denom_var <= 0:
        return {"n": n, "sr": round(sr, 4), "skew": round(skew, 4),
                "kurt": round(kurt, 4), "sr_expected": round(sr_expected, 4),
                "dsr": 0.0, "note": "negative variance — SR too extreme"}
    z_dsr = (sr - sr_expected) * math.sqrt((n - 1) / denom_var)
    dsr = _norm_cdf(z_dsr)
    return {
        "n": n,
        "sr": round(sr, 4),
        "skew": round(skew, 4),
        "kurt": round(kurt, 4),
        "n_trials": n_trials,
        "sr_expected": round(sr_expected, 4),
        "z_dsr": round(z_dsr, 4),
        "dsr": round(dsr, 4),
    }


def simulate(pnls_pct: list[float], starter: float, seq_trades: int,
             sims: int, seed: int = 1234) -> dict:
    rng = random.Random(seed)
    margin_calls = 0
    finals = []
    drawdowns = []
    for _ in range(sims):
        equity = starter
        peak = starter
        max_dd = 0.0
        called = False
        for _ in range(seq_trades):
            pnl_pct = rng.choice(pnls_pct)
            pnl_usd_gross = pnl_pct / 100.0 * NOTIONAL_USD
            pnl_usd_net = pnl_usd_gross - ROUND_TRIP_COMM_USD
            equity += pnl_usd_net
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            if equity < MAINTENANCE_MARGIN_USD:
                called = True
                break
        if called:
            margin_calls += 1
        finals.append(equity)
        drawdowns.append(max_dd)
    finals_sorted = sorted(finals)
    return {
        "starter": starter,
        "sims": sims,
        "seq_trades": seq_trades,
        "margin_call_count": margin_calls,
        "margin_call_pct": round(margin_calls * 100.0 / sims, 4),
        "final_equity_mean": round(statistics.mean(finals), 2),
        "final_equity_p05": round(finals_sorted[int(sims * 0.05)], 2),
        "final_equity_p50": round(finals_sorted[int(sims * 0.50)], 2),
        "final_equity_p95": round(finals_sorted[int(sims * 0.95)], 2),
        "max_drawdown_mean_pct": round(statistics.mean(drawdowns) * 100, 3),
        "max_drawdown_p95_pct": round(sorted(drawdowns)[int(sims * 0.95)] * 100, 3),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sims", type=int, default=10000)
    p.add_argument("--seq-trades", type=int, default=50)
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--n-trials", type=int, default=500,
                   help="DSR deflation: number of independent strategy "
                        "configurations searched (master-plan gate uses 500)")
    p.add_argument("--vol-window", type=int, default=20)
    p.add_argument("--dsr-gate", type=float, default=0.85,
                   help="LIVE_ELIGIBLE gate per master-plan Action #3")
    p.add_argument("--out", default="audit_dashboard/data/cot_step7_friction_adjusted_mc.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# friction-adjusted MC — sims={args.sims} seq={args.seq_trades} "
          f"n_trials={args.n_trials} dsr_gate={args.dsr_gate}",
          file=sys.stderr)

    try:
        raw_pnls = fetch_pnls_ordered()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    if len(raw_pnls) < 50:
        print(f"# WARN: n={len(raw_pnls)} too few for stable MC", file=sys.stderr)

    quartiles = rolling_vol_quartile(raw_pnls, window=args.vol_window)
    adj_pnls = apply_friction(raw_pnls, quartiles)

    raw_summary = {
        "n": len(raw_pnls),
        "mean_pct": round(statistics.mean(raw_pnls), 4),
        "stdev_pct": round(statistics.stdev(raw_pnls), 4) if len(raw_pnls) > 1 else 0,
        "wins": sum(1 for p in raw_pnls if p > 0),
        "losses": sum(1 for p in raw_pnls if p < 0),
    }
    adj_summary = {
        "n": len(adj_pnls),
        "mean_pct": round(statistics.mean(adj_pnls), 4),
        "stdev_pct": round(statistics.stdev(adj_pnls), 4) if len(adj_pnls) > 1 else 0,
        "wins": sum(1 for p in adj_pnls if p > 0),
        "losses": sum(1 for p in adj_pnls if p < 0),
        "slippage_drag_pct": round(statistics.mean(raw_pnls) - statistics.mean(adj_pnls), 4),
    }
    dsr_raw = deflated_sharpe_ratio(raw_pnls, n_trials=args.n_trials)
    dsr_adj = deflated_sharpe_ratio(adj_pnls, n_trials=args.n_trials)

    tiers_results = {}
    for starter in TIERS:
        r = simulate(adj_pnls, starter, args.seq_trades, args.sims, args.seed)
        tiers_results[f"${starter}"] = r
        print(f"#   ${starter}: margin_call={r['margin_call_pct']:.3f}% "
              f"final_p50=${r['final_equity_p50']}", file=sys.stderr)

    quartile_counts = {q: quartiles.count(q) for q in range(4)}

    overall_gate = "PASS" if dsr_adj.get("dsr", 0) >= args.dsr_gate else "FAIL"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "cot_positioning",
        "symbol": "CT=F",
        "spec": "master-plan Action #3 — friction-adjusted Step 7 MC + DSR gate",
        "friction_model": {
            "per_fill_ticks": 0.5,
            "fills_per_round_trip": 2,
            "vol_state": "rolling 20-trade |pnl| stdev quartile",
            "vol_multiplier_by_quartile": VOL_MULT_BY_QUARTILE,
            "tick_pct_of_notional": round(TICK_PCT_OF_NOTIONAL, 6),
            "round_trip_commission_usd": ROUND_TRIP_COMM_USD,
        },
        "vol_quartile_distribution": quartile_counts,
        "raw_pnl_summary": raw_summary,
        "friction_adjusted_pnl_summary": adj_summary,
        "raw_dsr": dsr_raw,
        "friction_adjusted_dsr": dsr_adj,
        "ror_mc_friction_adjusted": tiers_results,
        "gate": {
            "metric": "friction_adjusted_dsr",
            "threshold": args.dsr_gate,
            "n_trials_used": args.n_trials,
            "observed": dsr_adj.get("dsr", 0),
            "verdict": overall_gate,
            "rule": "per master-plan: CT=F NOT LIVE_ELIGIBLE if DSR < 0.85",
        },
        "caveat": (
            "v1 vol-state proxy uses rolling-|pnl|-stdev quartile because "
            "trading_picks lacks per-trade ATR. v2 should join an ATR snapshot "
            "from the price-cache table. Slippage tick estimate (0.5) is "
            "industry-typical for CT=F outside US session hours; refine after "
            "broker confirms execution venue."
        ),
        "nfa": "Research surface only.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)",
          file=sys.stderr)
    print(f"# RAW SR={dsr_raw.get('sr')} DSR={dsr_raw.get('dsr')}",
          file=sys.stderr)
    print(f"# ADJ SR={dsr_adj.get('sr')} DSR={dsr_adj.get('dsr')}",
          file=sys.stderr)
    print(f"# GATE: {overall_gate} (need DSR>={args.dsr_gate})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
