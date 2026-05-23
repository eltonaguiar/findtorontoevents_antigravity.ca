#!/usr/bin/env python3
"""
EQUITY edge validation script.

Uses the existing statistical_gates module (Bailey & Lopez de Prado 2014 DSR
with proper N/skewness/kurtosis, plus Newey-West t-stat) to assess whether the
EQUITY closed-picks pool has a statistically defensible edge.

NOTE on Grok patches:
- Grok's DSR formula `sr * norm.cdf(...)` is wrong — DSR is a probability (0-1),
  not SR × probability. Our statistical_gates.py has the correct implementation.
- Grok's PBO `1 - WR²` has no theoretical basis. Real PBO requires CPCV paths.
  We report win rate and use the Newey-West t-stat as the significance test instead.

Usage:
    python alpha_engine/validation/run_equity_edge_test.py
    python alpha_engine/validation/run_equity_edge_test.py --min-n 20 --dsr-threshold 0.90
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.validation.statistical_gates import (
    deflated_sharpe_ratio,
    newey_west_tstat,
    run_all_gates,
)

CLOSED_PICKS_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
EXTRA_LEDGER_PATHS = [
    REPO_ROOT / "alpha_engine" / "data" / "closed_picks_fast.json",
    REPO_ROOT / "alpha_engine" / "data" / "augmented_training.json",
]

WIN_STATUSES = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}

EQUITY_LABELS = {"EQUITY", "STOCKS", "STOCK"}


def _load_picks() -> list[dict]:
    def _read(p: Path) -> list[dict]:
        if not p.exists():
            return []
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, list):
            return d
        for k in ("picks", "closed_picks", "data"):
            if isinstance(d.get(k), list):
                return d[k]
        for v in d.values():
            if isinstance(v, list):
                return v
        return []

    picks = _read(CLOSED_PICKS_PATH)
    seen = {p.get("id", "") for p in picks if p.get("id")}
    for extra in EXTRA_LEDGER_PATHS:
        for p in _read(extra):
            pid = p.get("id", "")
            if pid and pid in seen:
                continue
            picks.append(p)
            if pid:
                seen.add(pid)
    return picks


def _is_equity(p: dict) -> bool:
    return (
        str(p.get("asset_class", "")).upper() in EQUITY_LABELS
        or str(p.get("category", "")).upper() in EQUITY_LABELS
    )


def _outcome(p: dict) -> bool | None:
    status = str(p.get("status") or "").upper()
    if status in WIN_STATUSES:
        return True
    if status in LOSS_STATUSES:
        return False
    pnl = p.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return None


def _pnl(p: dict) -> float | None:
    v = p.get("pnl_pct")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="EQUITY edge validation (correct DSR, NW t-stat)")
    parser.add_argument("--min-n", type=int, default=30, help="Minimum resolved picks to run test")
    parser.add_argument("--num-trials", type=int, default=50, help="Number of strategies tested (for DSR)")
    parser.add_argument("--dsr-threshold", type=float, default=0.95, help="DSR pass threshold")
    args = parser.parse_args()

    all_picks = _load_picks()
    equity = [p for p in all_picks if _is_equity(p)]
    resolved = [(p, _pnl(p), _outcome(p)) for p in equity]
    resolved = [(p, pnl, out) for p, pnl, out in resolved if pnl is not None and out is not None]

    n = len(resolved)
    wins = sum(1 for _, _, out in resolved if out)
    losses = n - wins
    returns = np.array([pnl for _, pnl, _ in resolved])

    print("\n=== EQUITY EDGE VALIDATION ===")
    print(f"Total closed picks loaded : {len(all_picks)}")
    print(f"EQUITY picks found        : {len(equity)}")
    print(f"Resolved with pnl_pct     : {n}")

    if n < args.min_n:
        print(f"\n⚠  INSUFFICIENT DATA — need {args.min_n} resolved picks, have {n}")
        print("   Cannot run statistical gates. Accumulate more closed picks first.")
        sys.exit(0)

    wr = wins / n
    mean_pnl = float(returns.mean())
    gross_wins = float(returns[returns > 0].sum()) if wins > 0 else 0.0
    gross_losses = abs(float(returns[returns <= 0].sum())) if losses > 0 else 0.0
    pf = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    print(f"\n--- Descriptive Stats ---")
    print(f"Win rate       : {wr:.1%}  ({wins}W / {losses}L)")
    print(f"Mean PnL/trade : {mean_pnl:.4%}")
    print(f"Profit Factor  : {pf:.3f}")
    print(f"Std dev PnL    : {float(returns.std()):.4%}")

    print(f"\n--- Statistical Gates (N_trials={args.num_trials}) ---")

    # Gate 1: Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
    # Uses correct formula: PSR = Φ((SR - SR*) * sqrt(T-1) / sqrt(1 - γ₃SR + (γ₄-1)/4·SR²))
    # NOT Grok's wrong formula: sr * norm.cdf(...)
    dsr_result = deflated_sharpe_ratio(
        returns=returns.tolist(),
        num_trials=args.num_trials,
        annualization_factor=252,
        dsr_threshold=args.dsr_threshold,
    )
    dsr_icon = "✅" if dsr_result["pass"] else "❌"
    print(f"{dsr_icon} DSR (LdP 2014)  : probability={dsr_result['dsr_probability']:.4f} "
          f"(threshold={args.dsr_threshold}), SR={dsr_result['sharpe']:.3f}, "
          f"E[maxSR|{args.num_trials}trials]={dsr_result['expected_max_sr']:.3f}")

    # Gate 2: Newey-West t-statistic (serial-correlation robust)
    nw_result = newey_west_tstat(returns=returns.tolist())
    nw_icon = "✅" if nw_result["pass"] else "❌"
    print(f"{nw_icon} Newey-West t   : t={nw_result['t_stat']:.3f} "
          f"p={nw_result['p_value']:.4f} (threshold=0.05), "
          f"mean={nw_result['mean_return']:.4%}")

    # Summary
    both_pass = dsr_result["pass"] and nw_result["pass"]
    summary_icon = "✅" if both_pass else ("⚠" if (dsr_result["pass"] or nw_result["pass"]) else "❌")
    print(f"\n{summary_icon} EQUITY EDGE VERDICT: {'STATISTICALLY DEFENSIBLE' if both_pass else 'NOT YET PROVEN'}")
    print(f"   WR={wr:.1%}, PF={pf:.2f}, n={n}")
    if not both_pass:
        if n < 100:
            print("   Primary blocker: insufficient resolved picks (need n≥100 for reliable inference).")
        if not dsr_result["pass"]:
            print(f"   DSR blocked: SR={dsr_result['sharpe']:.3f} not > E[max SR]={dsr_result['expected_max_sr']:.3f} at {args.num_trials} trials.")
        if not nw_result["pass"]:
            print(f"   NW t-stat blocked: mean return not significant (p={nw_result['p_value']:.4f}).")
    print()


if __name__ == "__main__":
    main()
