#!/usr/bin/env python3
"""H-037 VIX Carry — 30-Day Forward Verification Harness with Kill-Switch.

Monitors H-037 paper trading performance in real-time and enforces:
  - 30-day forward verification period
  - Kill-switch if PF < 1.0 or WR < 45% or MDD > 25%
  - Tier-2 promotion if PF >= 1.5 and WR >= 50% after 30 days
  - Daily performance reports to audit trail
  - DSR/PBO/WFE/FDR validation on promotion

North-star metrics (Tier-2):
  - DSR > 0.95 (Deflated Sharpe Ratio)
  - PBO < 0.05 (Probability of Backtest Overfitting)
  - WFE > 60% (Walk-Forward Efficiency)
  - FDR(q) <= 0.10 (False Discovery Rate)

Usage:
    python tools/h037_forward_verification.py [--days 30] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.dsr import deflated_sharpe_ratio
from tools.pbo import probability_of_backtest_overfitting
from tools.wfe import walk_forward_efficiency
from tools.fdr_control import benjamini_hochberg

DATA_DIR = ROOT / "paper_trading" / "data"
H037_STATE_FILE = DATA_DIR / "h037_verification_state.json"
CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"

# Kill-switch thresholds
KILL_PF_MIN = 1.0
KILL_WR_MIN = 0.45
KILL_MDD_MAX = 0.25

# Tier-2 promotion thresholds
TIER2_PF_MIN = 1.5
TIER2_WR_MIN = 0.50
TIER2_N_MIN = 30  # Minimum trades in 30-day window

# Verification period
DEFAULT_DAYS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [H-037] %(levelname)s: %(message)s",
)
logger = logging.getLogger("h037_verification")


def _load_state() -> dict:
    """Load or initialize H-037 verification state."""
    if H037_STATE_FILE.exists():
        try:
            return json.loads(H037_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "start_date": datetime.now(timezone.utc).isoformat(),
        "status": "ACTIVE",  # ACTIVE, KILLED, PROMOTED
        "trades": [],
        "daily_snapshots": [],
        "kill_reason": None,
        "promotion_date": None,
    }


def _save_state(state: dict):
    """Persist verification state."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    H037_STATE_FILE.write_text(
        json.dumps(state, indent=2, default=str),
        encoding="utf-8",
    )


def _load_closed_picks() -> list[dict]:
    """Load closed picks filtered to H-037 strategy."""
    if not CLOSED_PICKS_FILE.exists():
        return []

    try:
        picks = json.loads(CLOSED_PICKS_FILE.read_text(encoding="utf-8"))
        return [
            p for p in picks
            if isinstance(p, dict) and p.get("strategy") == "h037_vix_carry"
        ]
    except Exception:
        return []


def _compute_metrics(trades: list[dict]) -> dict:
    """Compute PF, WR, MDD, and n from trade list."""
    if not trades:
        return {"n": 0, "pf": None, "wr": None, "mdd": 0.0}

    n = len(trades)
    wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
    losses = [t for t in trades if t.get("pnl_pct", 0) <= 0]

    wr = len(wins) / n if n > 0 else 0

    gross_profit = sum(t.get("pnl_pct", 0) for t in wins)
    gross_loss = abs(sum(t.get("pnl_pct", 0) for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Max drawdown from cumulative PnL
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted(trades, key=lambda t: t.get("resolved_at", "")):
        cumulative += t.get("pnl_pct", 0)
        peak = max(peak, cumulative)
        dd = (peak - cumulative) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    return {
        "n": n,
        "pf": round(pf, 3) if pf != float("inf") else None,
        "wr": round(wr, 3),
        "mdd": round(max_dd, 3),
    }


def _check_kill_switch(metrics: dict, state: dict) -> bool:
    """Return True if kill-switch should trigger."""
    if metrics["n"] < 5:
        return False  # Too early to judge

    reasons = []

    if metrics["pf"] is not None and metrics["pf"] < KILL_PF_MIN:
        reasons.append(f"PF {metrics['pf']} < {KILL_PF_MIN}")

    if metrics["wr"] < KILL_WR_MIN:
        reasons.append(f"WR {metrics['wr']:.1%} < {KILL_WR_MIN:.0%}")

    if metrics["mdd"] > KILL_MDD_MAX:
        reasons.append(f"MDD {metrics['mdd']:.1%} > {KILL_MDD_MAX:.0%}")

    if reasons:
        state["status"] = "KILLED"
        state["kill_reason"] = "; ".join(reasons)
        state["killed_at"] = datetime.now(timezone.utc).isoformat()
        logger.critical(f"KILL-SWITCH TRIGGERED: {'; '.join(reasons)}")
        return True

    return False


def _compute_north_star_metrics(trades: list[dict]) -> dict:
    """Compute DSR, PBO, WFE, FDR for north-star validation."""
    if len(trades) < 10:
        return {
            "dsr": None,
            "pbo": None,
            "wfe": None,
            "fdr_q": None,
            "note": "Insufficient trades for north-star metrics (need >=10)",
        }

    returns = [t.get("pnl_pct", 0) for t in trades]
    n = len(returns)

    # DSR: Deflated Sharpe Ratio
    # Estimate Sharpe from returns, n_trials = total hypotheses tested (~30)
    mean_r = sum(returns) / n
    var_r = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
    std_r = var_r ** 0.5 if var_r > 0 else 0.0
    sharpe_obs = (mean_r / std_r) * (252 ** 0.5) if std_r > 0 else 0.0
    dsr = deflated_sharpe_ratio(sharpe_obs=sharpe_obs, n_trials=30, t=n)

    # PBO: Probability of Backtest Overfitting
    pbo = probability_of_backtest_overfitting(returns, n_splits=min(8, n // 4))

    # WFE: Walk-Forward Efficiency (split first 70% IS, last 30% OOS)
    split_idx = int(n * 0.7)
    is_returns = returns[:split_idx]
    oos_returns = returns[split_idx:]
    wfe = walk_forward_efficiency(is_returns, oos_returns) if oos_returns else 0.0

    # FDR: Benjamini-Hochberg on per-trade p-values (approximate)
    # Each trade is a Bernoulli trial; p-value = 1 - WR under null (WR=0.5)
    from scipy import stats as sp_stats
    p_values = []
    for t in trades:
        won = 1 if t.get("pnl_pct", 0) > 0 else 0
        # One-sided test: P(X >= observed | p=0.5)
        p_val = 1 - sp_stats.binom.cdf(won, 1, 0.5)
        p_values.append(p_val)
    rejected = benjamini_hochberg(p_values, q=0.10)
    fdr_q = sum(1 for r in rejected if r) / max(sum(rejected), 1) if any(rejected) else 0.0

    return {
        "dsr": round(dsr, 4),
        "pbo": round(pbo, 4),
        "wfe": round(wfe, 4),
        "fdr_q": round(fdr_q, 4),
        "sharpe_obs": round(sharpe_obs, 4),
    }


def _check_tier2_promotion(metrics: dict, state: dict) -> bool:
    """Return True if Tier-2 promotion criteria are met."""
    if state["status"] != "ACTIVE":
        return False

    start = datetime.fromisoformat(state["start_date"])
    elapsed = (datetime.now(timezone.utc) - start).days

    if elapsed < DEFAULT_DAYS:
        return False  # Not enough time

    if (
        metrics["n"] >= TIER2_N_MIN
        and metrics["pf"] is not None
        and metrics["pf"] >= TIER2_PF_MIN
        and metrics["wr"] >= TIER2_WR_MIN
    ):
        # Compute north-star metrics
        trades = _load_closed_picks()
        ns_metrics = _compute_north_star_metrics(trades)

        # Check north-star gates
        ns_pass = True
        ns_reasons = []

        if ns_metrics["dsr"] is not None and ns_metrics["dsr"] < 0.95:
            ns_pass = False
            ns_reasons.append(f"DSR {ns_metrics['dsr']} < 0.95")

        if ns_metrics["pbo"] is not None and ns_metrics["pbo"] >= 0.05:
            ns_pass = False
            ns_reasons.append(f"PBO {ns_metrics['pbo']} >= 0.05")

        if ns_metrics["wfe"] is not None and ns_metrics["wfe"] < 0.60:
            ns_pass = False
            ns_reasons.append(f"WFE {ns_metrics['wfe']:.1%} < 60%")

        if ns_metrics["fdr_q"] is not None and ns_metrics["fdr_q"] > 0.10:
            ns_pass = False
            ns_reasons.append(f"FDR q {ns_metrics['fdr_q']} > 0.10")

        if ns_pass:
            state["status"] = "PROMOTED"
            state["promotion_date"] = datetime.now(timezone.utc).isoformat()
            state["tier"] = "TIER2"
            state["north_star_metrics"] = ns_metrics
            logger.info(
                f"TIER-2 PROMOTION: PF={metrics['pf']}, WR={metrics['wr']:.1%}, n={metrics['n']}, "
                f"DSR={ns_metrics['dsr']}, PBO={ns_metrics['pbo']}, WFE={ns_metrics['wfe']:.1%}, FDR q={ns_metrics['fdr_q']}"
            )
            return True
        else:
            logger.warning(
                f"Tier-2 PF/WR/n met but north-star gates FAILED: {'; '.join(ns_reasons)}"
            )
            state["north_star_metrics"] = ns_metrics
            state["north_star_status"] = "PENDING"
            return False

    return False


def _daily_report(state: dict, metrics: dict):
    """Log daily performance report."""
    start = datetime.fromisoformat(state["start_date"])
    elapsed = (datetime.now(timezone.utc) - start).days
    days_left = max(0, DEFAULT_DAYS - elapsed)

    pf_str = f"{metrics['pf']}" if metrics['pf'] is not None else "N/A"
    wr_str = f"{metrics['wr']:.1%}" if metrics['wr'] is not None else "N/A"

    logger.info(
        f"Day {elapsed}/{DEFAULT_DAYS} | "
        f"n={metrics['n']} | PF={pf_str} | "
        f"WR={wr_str} | MDD={metrics['mdd']:.1%} | "
        f"Status={state['status']} | Days left={days_left}"
    )


def run_verification(days: int = DEFAULT_DAYS, dry_run: bool = False):
    """Run the H-037 forward verification harness."""
    global DEFAULT_DAYS
    DEFAULT_DAYS = days

    state = _load_state()

    if state["status"] in ("KILLED", "PROMOTED"):
        logger.warning(f"H-037 already {state['status']} (reason: {state.get('kill_reason', 'promotion')})")
        return state

    # Load H-037 trades
    trades = _load_closed_picks()
    state["trades"] = trades

    # Compute metrics
    metrics = _compute_metrics(trades)

    # Check kill-switch
    if _check_kill_switch(metrics, state):
        if not dry_run:
            _save_state(state)
        return state

    # Check Tier-2 promotion
    if _check_tier2_promotion(metrics, state):
        if not dry_run:
            _save_state(state)
        return state

    # Daily report
    _daily_report(state, metrics)

    # Snapshot
    state["daily_snapshots"].append({
        "date": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    })

    if not dry_run:
        _save_state(state)

    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="H-037 Forward Verification Harness")
    parser.add_argument("--days", type=int, default=30, help="Verification period in days")
    parser.add_argument("--dry-run", action="store_true", help="Don't persist state changes")
    args = parser.parse_args()

    result = run_verification(days=args.days, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
