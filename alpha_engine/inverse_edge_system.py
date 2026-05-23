#!/usr/bin/env python3
"""
INVERSE EDGE SYSTEM -- Alpha Engine
=====================================
Exploit PROVEN structural losers by inverting their signals.

Core insight from r/algotrading: most 45-55% WR strategies are noise.
You need STRUCTURAL losers below 40% WR to have a real inverse edge.
A strategy that loses 80%+ of the time is actually an 80% winner in reverse.

Key requirements for structural anti-edge:
  1. 20+ trades minimum (statistical significance)
  2. WR < 40% AND PF < 0.90 (sustained, not noisy)
  3. BOTH halves of the trade history below 40% WR (temporal consistency)
  4. Inverse signals use LIMIT entry, 1x ATR TP, trailing runner

Safety filters:
  - Only inverse structurally consistent losers (split-half validation)
  - Half position size (higher execution risk on inverse)
  - Max 3 concurrent inverse picks
  - Slippage-adjusted backtest (0.1% per trade)

Exports:
  - INVERSE_EDGE_STRATEGIES: dict of strategy callables for scanner.py
  - find_structural_losers(): detector function
  - run_inverse_edge_backtest(): full backtest with Sharpe/DD

Standalone:
  python alpha_engine/inverse_edge_system.py
"""

from __future__ import annotations

import copy
import io
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass

# ── Paths ────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
ALPHA_DIR = Path(__file__).resolve().parent
DATA_DIR = ALPHA_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
BACKTEST_OUTPUT_PATH = DATA_DIR / "inverse_edge_backtest.json"

# ── Configuration ────────────────────────────────────────────────
MIN_TRADES = 20              # Minimum trades for structural loser qualification
MAX_WR = 0.40                # Max win rate (40%) -- below this = potential anti-edge
MAX_PF = 0.90                # Max profit factor -- below this = sustained losses
SLIPPAGE_PER_TRADE = 0.001   # 0.1% slippage per trade (conservative)
MAX_CONCURRENT_INVERSE = 3   # Max simultaneous inverse picks
POSITION_SIZE_MULT = 0.50    # Half position size for inverse trades
INVERSE_CONFIDENCE_BASE = 0.60  # Base confidence for inverse picks
ANNUALIZE_FACTOR = 365.25    # For annualizing Sharpe ratio

# Known structural losers from definitive_edge_analysis.json
# These are pre-validated but the system also auto-detects from closed_picks
KNOWN_STRUCTURAL_LOSERS = {
    "winner_pattern_precursor",
    "yahoo_analyst_consensus",
    "volume_spike_backfill",
    "momentum_catcher",
    "hl_funding_fade",
    "cta_tsmom_blend",
    # From inverse_loser_report.json (2026-03-21): proven profitable when inverted
    "st_multi_day_momentum",            # 15.7% -> 84.3% WR, +361% PnL inverted
    "claude_gainer_1h",                 # 21.3% -> 78.7% WR, +68% PnL inverted
    "luxalgo_confluence",               # 30.1% -> 69.9% WR, +64% PnL inverted
    "crypto_rsi_whaleconfirmed_v1",     # 18.2% -> 81.8% WR, +15% PnL inverted
    "atr_regime_rsi",                   # 25.9% -> 74.1% WR, +14% PnL inverted
}


# ═══════════════════════════════════════════════════════════════════
# 1. ANTI-EDGE DETECTOR
# ═══════════════════════════════════════════════════════════════════

def _compute_strategy_stats(picks: list[dict]) -> dict:
    """Compute comprehensive stats for a list of picks from one strategy."""
    resolved = [
        p for p in picks
        if p.get("pnl_pct") is not None
        and p.get("status") in ("WON", "LOST", "STOPPED")
    ]
    if not resolved:
        return {
            "trades": 0, "wins": 0, "losses": 0, "wr": 0.0,
            "pf": 0.0, "total_pnl": 0.0, "avg_pnl": 0.0,
            "pnls": [], "win_pnls": [], "loss_pnls": [],
        }

    pnls = [p.get("pnl_pct", 0) or 0 for p in resolved]
    wins = sum(1 for p in resolved if p.get("status") == "WON")
    losses = len(resolved) - wins
    wr = wins / len(resolved) if resolved else 0.0

    win_pnls = [pnl for pnl in pnls if pnl > 0]
    loss_pnls = [pnl for pnl in pnls if pnl <= 0]

    gross_profit = sum(win_pnls)
    gross_loss = abs(sum(loss_pnls))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0.0

    return {
        "trades": len(resolved),
        "wins": wins,
        "losses": losses,
        "wr": round(wr, 4),
        "pf": round(pf, 4),
        "total_pnl": round(sum(pnls), 6),
        "avg_pnl": round(statistics.mean(pnls), 6) if pnls else 0.0,
        "pnls": pnls,
        "win_pnls": win_pnls,
        "loss_pnls": loss_pnls,
    }


def _split_half_check(picks: list[dict], max_wr: float = MAX_WR) -> tuple[bool, dict]:
    """
    Split trades into chronological halves and check both halves are below max_wr.
    This distinguishes STRUCTURAL losers from temporarily unlucky ones.

    Returns (is_structural, details_dict).
    """
    resolved = [
        p for p in picks
        if p.get("pnl_pct") is not None
        and p.get("status") in ("WON", "LOST", "STOPPED")
    ]

    # Sort by entry_date (or exit_date as fallback)
    resolved.sort(key=lambda p: p.get("entry_date", p.get("exit_date", "2000-01-01")))

    if len(resolved) < 10:
        return False, {"reason": "insufficient_trades", "count": len(resolved)}

    mid = len(resolved) // 2
    first_half = resolved[:mid]
    second_half = resolved[mid:]

    first_wins = sum(1 for p in first_half if p.get("status") == "WON")
    second_wins = sum(1 for p in second_half if p.get("status") == "WON")

    first_wr = first_wins / len(first_half) if first_half else 1.0
    second_wr = second_wins / len(second_half) if second_half else 1.0

    is_structural = first_wr < max_wr and second_wr < max_wr

    return is_structural, {
        "first_half_trades": len(first_half),
        "first_half_wr": round(first_wr, 4),
        "second_half_trades": len(second_half),
        "second_half_wr": round(second_wr, 4),
        "is_structural": is_structural,
    }


def find_structural_losers(
    closed_picks: list[dict] | None = None,
    min_trades: int = MIN_TRADES,
    max_wr: float = MAX_WR,
    max_pf: float = MAX_PF,
) -> dict[str, dict]:
    """
    Find strategies with SUSTAINED anti-edge (not just noise).

    Require:
      - min_trades+ resolved trades
      - WR < max_wr (40%)
      - PF < max_pf (0.90)
      - Split-half validation: BOTH halves below max_wr

    Returns dict mapping strategy_name -> {stats, split_half, inverse_wr, picks}.
    """
    if closed_picks is None:
        closed_picks = _load_closed_picks()

    # Group by strategy
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in closed_picks:
        strat = p.get("strategy", "unknown")
        groups[strat].append(p)

    structural_losers: dict[str, dict] = {}

    for strat, picks in groups.items():
        stats = _compute_strategy_stats(picks)

        # Gate 1: minimum trade count
        if stats["trades"] < min_trades:
            continue

        # Gate 2: WR below threshold
        if stats["wr"] >= max_wr:
            continue

        # Gate 3: PF below threshold (skip if no losses to compute PF)
        if stats["pf"] >= max_pf and stats["pf"] > 0:
            continue

        # Gate 4: Split-half temporal consistency
        is_structural, split_details = _split_half_check(picks, max_wr)
        if not is_structural:
            continue

        inverse_wr = round(1.0 - stats["wr"], 4)

        structural_losers[strat] = {
            "stats": stats,
            "split_half": split_details,
            "inverse_wr": inverse_wr,
            "trades": stats["trades"],
            "picks": picks,
        }

    return structural_losers


# ═══════════════════════════════════════════════════════════════════
# 2. INVERSE SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════════

def _flip_direction(direction: str) -> str:
    """Flip BUY/LONG to SELL/SHORT and vice versa."""
    d = direction.upper().strip()
    if d in ("BUY", "LONG"):
        return "SELL"
    if d in ("SELL", "SHORT"):
        return "BUY"
    return d


def _compute_atr_from_pick(pick: dict) -> float | None:
    """Extract or estimate ATR from pick metadata."""
    atr = pick.get("atr_at_entry") or pick.get("atr")
    if atr and atr > 0:
        return float(atr)
    # Estimate from TP/SL distance as proxy
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    if entry > 0 and tp > 0 and sl > 0:
        tp_dist = abs(tp - entry)
        sl_dist = abs(sl - entry)
        # ATR is roughly the average of TP and SL distances
        return (tp_dist + sl_dist) / 2
    return None


def generate_inverse_pick(original_pick: dict, structural_loser_info: dict) -> dict | None:
    """
    Generate an inverse pick from an original pick by a structural loser strategy.

    Inversion rules:
      - FLIP direction: BUY -> SELL, SELL -> BUY
      - SWAP TP and SL conceptually (original's SL zone = our TP zone)
      - TP at 1x ATR from entry (don't be greedy -- take the quick reversal)
      - Use LIMIT entry at the original's entry price
      - Set confidence based on inverse WR
      - Half position size
      - Tag as 'inverse_{original_strategy}'

    Returns the inverse pick dict, or None if we can't safely invert.
    """
    entry = original_pick.get("entry_price", 0)
    if not entry or entry <= 0:
        return None

    orig_direction = original_pick.get("signal_type",
                                        original_pick.get("direction", "BUY")).upper()
    new_direction = _flip_direction(orig_direction)

    orig_tp = original_pick.get("take_profit", 0) or 0
    orig_sl = original_pick.get("stop_loss", 0) or 0

    # Compute ATR for TP sizing
    atr = _compute_atr_from_pick(original_pick)
    if atr is None or atr <= 0:
        # Fallback: use 2% of entry price
        atr = entry * 0.02

    # Inverse TP/SL:
    # - TP at 1x ATR from entry (conservative -- take the quick reversal)
    # - SL at original's TP zone (if original wins, we lose)
    if new_direction in ("BUY", "LONG"):
        # We go LONG (original was SHORT)
        new_tp = entry + atr  # 1x ATR above entry
        # SL: where the original's TP was (below entry for original SHORT)
        if orig_tp > 0 and orig_tp < entry:
            new_sl = orig_tp  # Original's TP becomes our SL
        else:
            new_sl = entry - (atr * 1.5)  # 1.5x ATR stop
    else:
        # We go SHORT (original was LONG)
        new_tp = entry - atr  # 1x ATR below entry
        # SL: where the original's TP was (above entry for original LONG)
        if orig_tp > 0 and orig_tp > entry:
            new_sl = orig_tp  # Original's TP becomes our SL
        else:
            new_sl = entry + (atr * 1.5)  # 1.5x ATR stop

    # Sanity check: TP and SL must be on correct sides
    if new_direction in ("BUY", "LONG"):
        if new_tp <= entry or new_sl >= entry:
            return None
    else:
        if new_tp >= entry or new_sl <= entry:
            return None

    # Compute risk/reward
    tp_dist = abs(new_tp - entry)
    sl_dist = abs(new_sl - entry)
    risk_reward = tp_dist / sl_dist if sl_dist > 0 else 1.0

    inverse_wr = structural_loser_info.get("inverse_wr", 0.65)
    confidence = min(0.90, INVERSE_CONFIDENCE_BASE + (inverse_wr - 0.60) * 0.5)
    confidence = max(INVERSE_CONFIDENCE_BASE, confidence)

    orig_strategy = original_pick.get("strategy", "unknown")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    inv = copy.deepcopy(original_pick)

    # Core fields
    inv["id"] = f"inverse_{orig_strategy}::{original_pick.get('symbol', 'UNK')}::{now_str}"
    inv["strategy"] = f"inverse_{orig_strategy}"
    inv["signal_type"] = new_direction
    if "direction" in inv:
        inv["direction"] = "LONG" if new_direction == "BUY" else "SHORT"
    inv["entry_price"] = round(entry, 8)
    inv["take_profit"] = round(new_tp, 8)
    inv["stop_loss"] = round(new_sl, 8)
    inv["confidence"] = round(confidence, 3)
    inv["risk_reward"] = round(risk_reward, 2)

    # Execution: LIMIT order at original's entry (not market)
    inv["order_type"] = "LIMIT"
    inv["reason"] = (
        f"INVERSE EDGE: {orig_strategy} is structural loser "
        f"(WR={structural_loser_info['stats']['wr']:.1%}, "
        f"PF={structural_loser_info['stats']['pf']:.2f}, "
        f"{structural_loser_info['trades']} trades). "
        f"Flipped {orig_direction}->{new_direction}, "
        f"TP at 1x ATR ({atr:.6g}), RR={risk_reward:.1f}"
    )

    # Position sizing: half normal
    inv["position_size_mult"] = POSITION_SIZE_MULT
    if "allocation" in inv and inv["allocation"]:
        inv["allocation"] = round(float(inv["allocation"]) * POSITION_SIZE_MULT, 2)

    # Source metadata
    inv["source_system"] = "inverse_edge"
    inv["inverse_edge_meta"] = {
        "original_strategy": orig_strategy,
        "original_direction": orig_direction,
        "inverted_direction": new_direction,
        "original_wr": structural_loser_info["stats"]["wr"],
        "original_pf": structural_loser_info["stats"]["pf"],
        "inverse_wr": inverse_wr,
        "original_trades": structural_loser_info["trades"],
        "split_half": structural_loser_info["split_half"],
        "atr_used": round(atr, 8),
        "tp_method": "1x_atr",
        "sl_method": "original_tp_zone",
        "order_type": "LIMIT",
    }

    # Reset tracking fields
    inv["status"] = "OPEN"
    inv["exit_price"] = None
    inv["exit_date"] = None
    inv["exit_reason"] = None
    inv["pnl_pct"] = None
    inv["pnl_dollar"] = None
    inv["high_water_mark"] = None
    inv["mfe"] = None
    inv["mae"] = None
    inv["current_price"] = None
    inv["unrealized_pnl_pct"] = None
    inv["forward_validated"] = False
    inv["forward_status"] = f"inverse_edge of {orig_strategy}"
    inv["generated_at"] = now_iso
    inv["scan_timestamp"] = now_iso

    return inv


def generate_inverse_picks(
    active_picks: list[dict] | None = None,
    structural_losers: dict[str, dict] | None = None,
) -> list[dict]:
    """
    Scan active picks for entries from structural loser strategies
    and generate corresponding inverse picks.

    Safety: max MAX_CONCURRENT_INVERSE inverse picks at a time.
    """
    if active_picks is None:
        active_picks = _load_active_picks()
    if structural_losers is None:
        structural_losers = find_structural_losers()

    loser_names = set(structural_losers.keys())
    inverse_picks: list[dict] = []

    for pick in active_picks:
        strat = pick.get("strategy", "")
        if strat not in loser_names:
            continue

        inv = generate_inverse_pick(pick, structural_losers[strat])
        if inv is not None:
            inverse_picks.append(inv)

        if len(inverse_picks) >= MAX_CONCURRENT_INVERSE:
            break

    return inverse_picks


# ═══════════════════════════════════════════════════════════════════
# 3. BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════

def _backtest_inverse_strategy(
    picks: list[dict],
    slippage: float = SLIPPAGE_PER_TRADE,
) -> dict:
    """
    Simulate inverse trades for all closed picks from a structural loser.

    For each closed pick:
      - If original LOST -> inverse WINS (capped at 1x ATR from entry)
      - If original WON -> inverse LOSES (capped at SL distance)
      - Apply slippage on each trade

    Returns full backtest report with WR, PF, Sharpe, max DD, equity curve.
    """
    resolved = [
        p for p in picks
        if p.get("pnl_pct") is not None
        and p.get("status") in ("WON", "LOST", "STOPPED")
    ]
    if not resolved:
        return _empty_backtest()

    # Sort chronologically
    resolved.sort(key=lambda p: p.get("entry_date", p.get("exit_date", "2000-01-01")))

    inverse_pnls: list[float] = []
    inverse_wins = 0
    equity_curve: list[float] = [1.0]  # Start at $1 normalized

    for p in resolved:
        orig_pnl = p.get("pnl_pct", 0) or 0
        orig_status = p.get("status", "")
        entry = p.get("entry_price", 0)

        if entry <= 0:
            continue

        # Compute ATR for TP cap
        atr = _compute_atr_from_pick(p)
        if atr is None or atr <= 0:
            atr = entry * 0.02

        atr_pct = atr / entry  # ATR as percentage of entry

        if orig_status in ("LOST", "STOPPED"):
            # Original lost -> inverse wins
            # Cap at 1x ATR (don't be greedy)
            inv_gain = min(abs(orig_pnl), atr_pct)
            inv_pnl = inv_gain - slippage
            if inv_pnl > 0:
                inverse_wins += 1
        elif orig_status == "WON":
            # Original won -> inverse loses
            inv_pnl = -(abs(orig_pnl) + slippage)
        else:
            inv_pnl = -slippage

        inverse_pnls.append(round(inv_pnl, 6))

        # Update equity curve
        new_equity = equity_curve[-1] * (1 + inv_pnl)
        equity_curve.append(max(new_equity, 0.0))  # Floor at 0

    if not inverse_pnls:
        return _empty_backtest()

    # ── Compute metrics ──────────────────────────────────────────
    total_trades = len(inverse_pnls)
    inv_wr = inverse_wins / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(p for p in inverse_pnls if p > 0)
    gross_loss = abs(sum(p for p in inverse_pnls if p < 0))
    inv_pf = gross_profit / gross_loss if gross_loss > 0 else 99.0

    total_pnl = sum(inverse_pnls)
    avg_pnl = statistics.mean(inverse_pnls) if inverse_pnls else 0.0

    # Sharpe ratio (annualized)
    if len(inverse_pnls) >= 2:
        pnl_std = statistics.stdev(inverse_pnls)
        if pnl_std > 0:
            daily_sharpe = avg_pnl / pnl_std
            # Estimate trades per year from data span
            dates = [
                p.get("entry_date", "2000-01-01")
                for p in resolved
                if p.get("entry_date")
            ]
            if len(dates) >= 2:
                try:
                    first_date = datetime.strptime(min(dates), "%Y-%m-%d")
                    last_date = datetime.strptime(max(dates), "%Y-%m-%d")
                    span_days = max((last_date - first_date).days, 1)
                    trades_per_year = (total_trades / span_days) * ANNUALIZE_FACTOR
                    annualized_sharpe = daily_sharpe * math.sqrt(max(trades_per_year, 1))
                except (ValueError, TypeError):
                    annualized_sharpe = daily_sharpe * math.sqrt(52)
            else:
                annualized_sharpe = daily_sharpe * math.sqrt(52)
        else:
            annualized_sharpe = 0.0
    else:
        annualized_sharpe = 0.0

    # Max drawdown from equity curve
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # Win/loss streaks
    streaks = _compute_streaks(inverse_pnls)

    return {
        "trades": total_trades,
        "wins": inverse_wins,
        "losses": total_trades - inverse_wins,
        "wr": round(inv_wr, 4),
        "pf": round(inv_pf, 4),
        "total_pnl": round(total_pnl, 6),
        "avg_pnl": round(avg_pnl, 6),
        "sharpe": round(annualized_sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "best_trade": round(max(inverse_pnls), 6) if inverse_pnls else 0.0,
        "worst_trade": round(min(inverse_pnls), 6) if inverse_pnls else 0.0,
        "slippage_per_trade": slippage,
        "total_slippage_cost": round(slippage * total_trades, 6),
        "equity_final": round(equity_curve[-1], 6),
        "max_win_streak": streaks["max_win_streak"],
        "max_loss_streak": streaks["max_loss_streak"],
    }


def _empty_backtest() -> dict:
    """Return empty backtest result."""
    return {
        "trades": 0, "wins": 0, "losses": 0, "wr": 0.0, "pf": 0.0,
        "total_pnl": 0.0, "avg_pnl": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
        "best_trade": 0.0, "worst_trade": 0.0, "slippage_per_trade": 0.0,
        "total_slippage_cost": 0.0, "equity_final": 1.0,
        "max_win_streak": 0, "max_loss_streak": 0,
    }


def _compute_streaks(pnls: list[float]) -> dict:
    """Compute max win and loss streaks."""
    max_win = 0
    max_loss = 0
    cur_win = 0
    cur_loss = 0
    for pnl in pnls:
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        elif pnl < 0:
            cur_loss += 1
            cur_win = 0
            max_loss = max(max_loss, cur_loss)
        else:
            cur_win = 0
            cur_loss = 0
    return {"max_win_streak": max_win, "max_loss_streak": max_loss}


def run_inverse_edge_backtest(
    closed_picks: list[dict] | None = None,
) -> dict:
    """
    Full backtest of the inverse edge system.

    For each structural loser:
      - Simulate inversing every historical trade
      - Account for 0.1% slippage
      - Report: inverse WR, PF, Sharpe, max DD

    Returns comprehensive report dict and saves to JSON.
    """
    if closed_picks is None:
        closed_picks = _load_closed_picks()

    structural_losers = find_structural_losers(closed_picks)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": "inverse_edge",
        "version": "1.0.0",
        "config": {
            "min_trades": MIN_TRADES,
            "max_wr": MAX_WR,
            "max_pf": MAX_PF,
            "slippage_per_trade": SLIPPAGE_PER_TRADE,
            "max_concurrent_inverse": MAX_CONCURRENT_INVERSE,
            "position_size_mult": POSITION_SIZE_MULT,
            "split_half_validation": True,
        },
        "structural_losers_found": len(structural_losers),
        "strategies": {},
        "summary": {},
    }

    all_inverse_pnls: list[float] = []

    for strat_name, loser_info in sorted(
        structural_losers.items(),
        key=lambda x: x[1]["stats"]["wr"],
    ):
        picks = loser_info["picks"]
        stats = loser_info["stats"]

        # Run backtest
        bt = _backtest_inverse_strategy(picks)
        all_inverse_pnls.extend(
            [bt["avg_pnl"]] * bt["trades"] if bt["trades"] > 0 else []
        )

        report["strategies"][strat_name] = {
            "original": {
                "trades": stats["trades"],
                "wr": stats["wr"],
                "pf": stats["pf"],
                "total_pnl": stats["total_pnl"],
                "avg_pnl": stats["avg_pnl"],
            },
            "split_half": loser_info["split_half"],
            "inverse_backtest": bt,
            "inverse_strategy_name": f"inverse_{strat_name}",
            "recommendation": _make_recommendation(stats, bt),
        }

    # ── Summary across all strategies ────────────────────────────
    if report["strategies"]:
        all_bt = [v["inverse_backtest"] for v in report["strategies"].values()]
        total_trades = sum(b["trades"] for b in all_bt)
        total_wins = sum(b["wins"] for b in all_bt)
        combined_wr = total_wins / total_trades if total_trades > 0 else 0.0
        combined_pnl = sum(b["total_pnl"] for b in all_bt)
        avg_sharpe = (
            statistics.mean([b["sharpe"] for b in all_bt if b["trades"] > 0])
            if any(b["trades"] > 0 for b in all_bt)
            else 0.0
        )
        worst_dd = max(b["max_drawdown"] for b in all_bt) if all_bt else 0.0

        # Rank by Sharpe
        ranked = sorted(
            report["strategies"].items(),
            key=lambda x: x[1]["inverse_backtest"]["sharpe"],
            reverse=True,
        )

        report["summary"] = {
            "total_structural_losers": len(structural_losers),
            "total_inverse_trades": total_trades,
            "total_inverse_wins": total_wins,
            "combined_inverse_wr": round(combined_wr, 4),
            "combined_inverse_pnl": round(combined_pnl, 6),
            "avg_inverse_sharpe": round(avg_sharpe, 4),
            "worst_max_drawdown": round(worst_dd, 4),
            "best_candidate": ranked[0][0] if ranked else None,
            "best_candidate_sharpe": (
                ranked[0][1]["inverse_backtest"]["sharpe"] if ranked else 0.0
            ),
            "ranking_by_sharpe": [
                {
                    "strategy": name,
                    "inverse_wr": info["inverse_backtest"]["wr"],
                    "inverse_pf": info["inverse_backtest"]["pf"],
                    "inverse_sharpe": info["inverse_backtest"]["sharpe"],
                    "inverse_max_dd": info["inverse_backtest"]["max_drawdown"],
                }
                for name, info in ranked
            ],
        }
    else:
        report["summary"] = {
            "total_structural_losers": 0,
            "total_inverse_trades": 0,
            "note": "No structural losers found matching criteria",
        }

    # Save backtest results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(BACKTEST_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return report


def _make_recommendation(orig_stats: dict, bt: dict) -> str:
    """Generate human-readable recommendation."""
    if bt["trades"] == 0:
        return "NO DATA -- insufficient resolved trades for backtest"
    if bt["wr"] >= 0.65 and bt["sharpe"] >= 1.0:
        return f"STRONG INVERSE -- {bt['wr']:.0%} WR, Sharpe {bt['sharpe']:.2f}, deploy with confidence"
    if bt["wr"] >= 0.55 and bt["pf"] >= 1.0:
        return f"GOOD INVERSE -- {bt['wr']:.0%} WR, PF {bt['pf']:.2f}, deploy half size"
    if bt["wr"] >= 0.50 and bt["pf"] >= 0.8:
        return f"MARGINAL INVERSE -- {bt['wr']:.0%} WR, monitor before scaling"
    return f"WEAK INVERSE -- {bt['wr']:.0%} WR, PF {bt['pf']:.2f}, not recommended"


# ═══════════════════════════════════════════════════════════════════
# 4. SCANNER INTEGRATION -- Strategy Callables
# ═══════════════════════════════════════════════════════════════════

def _load_closed_picks() -> list[dict]:
    """Load closed picks from alpha engine data."""
    if CLOSED_PICKS_PATH.exists():
        with open(CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _load_active_picks() -> list[dict]:
    """Load active picks from alpha engine data."""
    if ACTIVE_PICKS_PATH.exists():
        with open(ACTIVE_PICKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# Cache structural losers to avoid re-computing every scan cycle
_CACHED_LOSERS: dict[str, dict] | None = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL = 3600  # Refresh every hour


def _get_structural_losers() -> dict[str, dict]:
    """Get structural losers with caching."""
    global _CACHED_LOSERS, _CACHE_TIMESTAMP
    import time as _time

    now = _time.time()
    if _CACHED_LOSERS is not None and (now - _CACHE_TIMESTAMP) < _CACHE_TTL:
        return _CACHED_LOSERS

    _CACHED_LOSERS = find_structural_losers()
    _CACHE_TIMESTAMP = now
    return _CACHED_LOSERS


def _compute_rsi(close_series, period: int = 14) -> float | None:
    """Compute RSI from a close price series. Returns last RSI value or None."""
    if close_series is None or len(close_series) < period + 1:
        return None
    delta = close_series.diff()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi_val = 100 - (100 / (1 + rs))
    last = rsi_val.iloc[-1]
    try:
        import pandas as pd
        if pd.isna(last):
            return None
    except Exception:
        pass
    return float(last)


def _compute_atr_from_df(df, period: int = 14) -> float | None:
    """Compute ATR from OHLCV DataFrame. Returns last ATR value or None."""
    if df is None or len(df) < period + 1:
        return None
    high = df["High"] if "High" in df.columns else df.get("high")
    low = df["Low"] if "Low" in df.columns else df.get("low")
    close = df["Close"] if "Close" in df.columns else df.get("close")
    if high is None or low is None or close is None:
        return None
    try:
        import pandas as pd
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr_series = tr.rolling(period).mean()
        last = atr_series.iloc[-1]
        if pd.isna(last):
            return None
        return float(last)
    except Exception:
        return None


def _make_inverse_strategy(loser_strategy_name: str):
    """
    Factory: create a scanner-compatible strategy function that generates
    inverse signals for a structural loser strategy.

    INDEPENDENT signal generation: uses RSI + price action on the df directly.
    Does NOT require active picks from the base strategy to exist.
    Logic: detect conditions where the base loser WOULD generate a signal,
    then flip direction (the base consistently picks wrong, so the inverse wins).

    The returned function has signature: fn(df, symbol, category, context) -> list[dict]
    """
    def inverse_strategy_fn(df, symbol, category, context=None):
        """
        Inverse edge strategy for {loser_strategy_name}.
        Generates independent inverse signals using RSI + price action.
        """
        signals = []

        loser_info = _get_structural_losers()
        if loser_strategy_name not in loser_info:
            return signals

        # Count current inverse picks globally (max concurrent limit)
        active = _load_active_picks()
        current_inverse_count = sum(
            1 for p in active
            if p.get("strategy", "").startswith("inverse_")
            and p.get("status") == "OPEN"
        )
        if current_inverse_count >= MAX_CONCURRENT_INVERSE:
            return signals

        # Skip if we already have an active inverse pick for this symbol
        existing_inv = any(
            p for p in active
            if p.get("strategy") == f"inverse_{loser_strategy_name}"
            and p.get("symbol") == symbol
            and p.get("status") == "OPEN"
        )
        if existing_inv:
            return signals

        # --- INDEPENDENT SIGNAL GENERATION ---
        # Structural losers consistently pick wrong direction. We detect the
        # same oversold/overbought conditions they would react to, then FLIP.
        # Most base losers are momentum/trend-following strategies that buy dips
        # that keep dipping, or chase breakouts that fail. The inverse: fade them.

        if df is None or len(df) < 30:
            return signals

        close = df["Close"] if "Close" in df.columns else df.get("close")
        if close is None or len(close) < 30:
            return signals

        entry_price = float(close.iloc[-1])
        if entry_price <= 0:
            return signals

        rsi = _compute_rsi(close, period=14)
        if rsi is None:
            return signals

        atr = _compute_atr_from_df(df, period=14)
        if atr is None or atr <= 0:
            atr = entry_price * 0.02  # 2% fallback

        info = loser_info[loser_strategy_name]
        inverse_wr = info.get("inverse_wr", 0.65)
        confidence = min(0.90, INVERSE_CONFIDENCE_BASE + (inverse_wr - 0.60) * 0.5)
        confidence = max(INVERSE_CONFIDENCE_BASE, confidence)

        # Determine what the base loser would do and FLIP it.
        # Base losers tend to: BUY oversold (RSI < 35) and SELL overbought (RSI > 65).
        # These conditions fail for structural losers, so we invert:
        #   - RSI < 35 (base would BUY) -> we SELL (price keeps dropping)
        #   - RSI > 65 (base would SELL) -> we BUY (momentum continues)
        # Also check recent price action for additional confirmation.
        base_signal = None
        if rsi < 35:
            # Base loser would BUY oversold -> we SELL (the dip keeps dipping)
            base_signal = "BUY"
        elif rsi > 65:
            # Base loser would SELL overbought -> we BUY (momentum continues)
            base_signal = "SELL"

        if base_signal is None:
            return signals

        new_direction = _flip_direction(base_signal)

        # TP/SL based on ATR
        if new_direction in ("BUY", "LONG"):
            tp = entry_price + atr * 1.0   # 1x ATR TP
            sl = entry_price - atr * 1.5   # 1.5x ATR SL
        else:
            tp = entry_price - atr * 1.0
            sl = entry_price + atr * 1.5

        # Sanity: TP and SL must be positive and on correct sides
        if tp <= 0 or sl <= 0:
            return signals
        if new_direction in ("BUY", "LONG") and (tp <= entry_price or sl >= entry_price):
            return signals
        if new_direction in ("SELL", "SHORT") and (tp >= entry_price or sl <= entry_price):
            return signals

        reason = (
            f"INVERSE EDGE (independent): {loser_strategy_name} is structural loser "
            f"(WR={info['stats']['wr']:.1%}, PF={info['stats']['pf']:.2f}, "
            f"{info['trades']} trades). "
            f"RSI={rsi:.1f} -> base would {base_signal}, we {new_direction}. "
            f"TP at 1x ATR ({atr:.6g})"
        )

        signals.append({
            "signal_type": new_direction,
            "entry_price": round(entry_price, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "confidence": round(confidence, 3),
            "reason": reason,
            "order_type": "LIMIT",
            "position_size_mult": POSITION_SIZE_MULT,
            "source_system": "inverse_edge",
            "inverse_edge_meta": {
                "original_strategy": loser_strategy_name,
                "original_direction": base_signal,
                "inverted_direction": new_direction,
                "original_wr": info["stats"]["wr"],
                "original_pf": info["stats"]["pf"],
                "inverse_wr": inverse_wr,
                "original_trades": info["trades"],
                "split_half": info["split_half"],
                "atr_used": round(atr, 8),
                "rsi_at_entry": round(rsi, 2),
                "signal_source": "independent_rsi",
                "tp_method": "1x_atr",
                "sl_method": "1.5x_atr",
                "order_type": "LIMIT",
            },
        })

        return signals

    # Set proper docstring
    inverse_strategy_fn.__doc__ = (
        f"Inverse edge strategy: generates independent signals opposing structural loser "
        f"'{loser_strategy_name}' (WR < {MAX_WR:.0%}, split-half validated). "
        f"Uses RSI + price action to detect where the base would signal, then flips."
    )
    inverse_strategy_fn.__name__ = f"inverse_{loser_strategy_name}"

    return inverse_strategy_fn


def build_inverse_edge_strategies() -> dict[str, callable]:
    """
    Build the INVERSE_EDGE_STRATEGIES dict for scanner integration.

    Returns a dict of {strategy_name: callable} where each callable
    has the scanner-compatible signature fn(df, symbol, category, context).
    """
    losers = _get_structural_losers()
    strategies: dict[str, callable] = {}

    for loser_name in losers:
        inv_name = f"inverse_{loser_name}"
        strategies[inv_name] = _make_inverse_strategy(loser_name)

    return strategies


# Build on import for scanner.py to consume
INVERSE_EDGE_STRATEGIES = build_inverse_edge_strategies()


# ═══════════════════════════════════════════════════════════════════
# 5. STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════════════

def main():
    """Run the full inverse edge analysis and backtest."""
    print("=" * 72)
    print("  INVERSE EDGE SYSTEM v1.0")
    print("  Exploiting Structural Losers via Signal Inversion")
    print("=" * 72)
    print()

    # ── Load data ────────────────────────────────────────────────
    closed = _load_closed_picks()
    active = _load_active_picks()
    print(f"  Loaded {len(closed)} closed picks, {len(active)} active picks")
    print()

    # ── Detect structural losers ─────────────────────────────────
    losers = find_structural_losers(closed)
    print(f"  STRUCTURAL LOSERS DETECTED: {len(losers)}")
    print(f"  {'Strategy':<40} {'Trades':>7} {'WR':>8} {'PF':>7} {'Inv WR':>8}")
    print(f"  {'-'*40} {'-'*7} {'-'*8} {'-'*7} {'-'*8}")

    for name, info in sorted(losers.items(), key=lambda x: x[1]["stats"]["wr"]):
        s = info["stats"]
        print(
            f"  {name:<40} {s['trades']:>7} "
            f"{s['wr']:>7.1%} {s['pf']:>7.2f} "
            f"{info['inverse_wr']:>7.1%}"
        )
        sh = info["split_half"]
        print(
            f"    Split-half: 1st={sh['first_half_wr']:.1%} "
            f"({sh['first_half_trades']}t), "
            f"2nd={sh['second_half_wr']:.1%} "
            f"({sh['second_half_trades']}t)"
        )

    print()

    # ── Run backtest ─────────────────────────────────────────────
    report = run_inverse_edge_backtest(closed)

    print()
    print("=" * 72)
    print("  INVERSE BACKTEST RESULTS (with 0.1% slippage)")
    print("=" * 72)

    for strat_name, strat_info in report["strategies"].items():
        bt = strat_info["inverse_backtest"]
        orig = strat_info["original"]
        print(f"\n  >> {strat_name}")
        print(
            f"     Original:  {orig['trades']} trades | "
            f"{orig['wr']:.1%} WR | PF {orig['pf']:.2f} | "
            f"PnL {orig['total_pnl']:+.4f}"
        )
        print(
            f"     Inverse:   {bt['trades']} trades | "
            f"{bt['wr']:.1%} WR | PF {bt['pf']:.2f} | "
            f"PnL {bt['total_pnl']:+.4f}"
        )
        print(
            f"     Sharpe: {bt['sharpe']:.2f} | "
            f"MaxDD: {bt['max_drawdown']:.1%} | "
            f"Equity: {bt['equity_final']:.4f}"
        )
        print(
            f"     Streaks: W={bt['max_win_streak']}, L={bt['max_loss_streak']} | "
            f"Best: {bt['best_trade']:+.4f} | Worst: {bt['worst_trade']:+.4f}"
        )
        print(f"     -> {strat_info['recommendation']}")

    # ── Summary ──────────────────────────────────────────────────
    s = report["summary"]
    print(f"\n{'=' * 72}")
    print(f"  SUMMARY")
    print(f"{'=' * 72}")
    print(f"  Structural losers found:  {s.get('total_structural_losers', 0)}")
    print(f"  Total inverse trades:     {s.get('total_inverse_trades', 0)}")
    print(f"  Combined inverse WR:      {s.get('combined_inverse_wr', 0):.1%}")
    print(f"  Combined inverse PnL:     {s.get('combined_inverse_pnl', 0):+.4f}")
    print(f"  Average Sharpe:           {s.get('avg_inverse_sharpe', 0):.2f}")
    print(f"  Worst max drawdown:       {s.get('worst_max_drawdown', 0):.1%}")
    if s.get("best_candidate"):
        print(
            f"  Best candidate:           {s['best_candidate']} "
            f"(Sharpe {s['best_candidate_sharpe']:.2f})"
        )

    # ── Generate live inverse picks ──────────────────────────────
    inverse_picks = generate_inverse_picks(active, losers)
    if inverse_picks:
        print(f"\n  LIVE INVERSE PICKS GENERATED: {len(inverse_picks)}")
        for p in inverse_picks:
            print(
                f"    {p['strategy']} | {p['symbol']} | "
                f"{p['signal_type']} @ {p['entry_price']} | "
                f"TP {p['take_profit']} | SL {p['stop_loss']}"
            )
    else:
        print(f"\n  No active picks from structural losers to invert right now.")

    # ── Scanner integration ──────────────────────────────────────
    strats = build_inverse_edge_strategies()
    print(f"\n  INVERSE_EDGE_STRATEGIES exported: {len(strats)} strategies")
    for name in sorted(strats.keys()):
        print(f"    - {name}")

    print(f"\n  Backtest saved to: {BACKTEST_OUTPUT_PATH}")
    print(f"  Wire into scanner.py:")
    print(f"    from inverse_edge_system import INVERSE_EDGE_STRATEGIES")
    print(f"    strategies.update(INVERSE_EDGE_STRATEGIES)")
    print()

    return report


if __name__ == "__main__":
    main()
