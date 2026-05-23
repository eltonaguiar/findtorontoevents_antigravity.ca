"""
Backtest-to-ML Bridge -- Convert backtest results into ML training data.
=======================================================================
Converts 55,000+ backtest entries from incubator/backtest_results/ into
pseudo-closed-picks compatible with the Alpha Engine ML Ranker.

Backtest data gets 0.3x weight (lower trust due to possible look-ahead bias).
Live picks keep 1.0 weight. Backtest ratio is capped at 3:1 vs live picks.

Supports these backtest file formats:
  1. real_data_directional_*.json -- daily_pnl per strategy (individual day trades)
  2. vectorized_backtest_results.json -- per-symbol per-strategy summary stats
  3. real_data_sweep_*.json / google_antigravity_*.json -- strategy-level summaries
  4. shortterm_battle_*.json / codex10_*.json / cursor_ai_*.json -- strategy summaries
  5. forward_matches_*.json -- strategy match counts (limited, used for metadata)

Priority: files with daily_pnl trade-level data > summary-level files.
"""

import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Resolve paths relative to this file
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
_BACKTEST_DIR = _PROJECT_ROOT / "incubator" / "backtest_results"
_CLOSED_PICKS_PATH = _THIS_DIR / "data" / "closed_picks.json"
_AUGMENTED_OUTPUT_PATH = _THIS_DIR / "data" / "augmented_training.json"

# Weight for backtest-derived picks (live picks get 1.0)
BACKTEST_WEIGHT = 0.3

# Symbol normalization: map various formats to a standard symbol
_SYMBOL_NORMALIZE = {
    "BTC/USDT": "BTCUSDT", "ETH/USDT": "ETHUSDT", "SOL/USDT": "SOLUSDT",
    "BNB/USDT": "BNBUSDT", "DOGE/USDT": "DOGEUSDT", "XRP/USDT": "XRPUSDT",
    "AVAX/USDT": "AVAXUSDT", "LINK/USDT": "LINKUSDT",
    "BTCUSDT": "BTCUSDT", "ETHUSDT": "ETHUSDT", "SOLUSDT": "SOLUSDT",
}


def _normalize_symbol(raw: str) -> str:
    """Normalize symbol to XXXUSDT format."""
    s = raw.strip().upper()
    if s in _SYMBOL_NORMALIZE:
        return _SYMBOL_NORMALIZE[s]
    # Handle "X-USD" format from closed_picks
    if s.endswith("-USD"):
        base = s.replace("-USD", "")
        return base + "USDT"
    return s


def _safe_float(val, default=0.0):
    """Safe float conversion handling None and NaN."""
    if val is None:
        return default
    try:
        v = float(val)
        if v != v:  # NaN check
            return default
        return v
    except (TypeError, ValueError):
        return default


def _extract_timestamp_from_filename(filename: str) -> Optional[str]:
    """Extract timestamp from backtest filename like forward_matches_20260305_090300.json."""
    m = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
    if m:
        y, mo, d, h, mi, s = m.groups()
        return f"{y}-{mo}-{d}T{h}:{mi}:{s}+00:00"
    return None


def _make_closed_pick(
    strategy: str,
    symbol: str,
    pnl_pct: float,
    win_rate: float = 0.5,
    sharpe: float = 0.0,
    confidence: float = 0.5,
    entry_date: str = "2025-01-01",
    direction: str = "BUY",
    total_trades: int = 1,
    profit_factor: float = 1.0,
    max_drawdown: float = 0.0,
    source_file: str = "",
) -> dict:
    """Create a pseudo-closed-pick dict compatible with ML ranker training.

    Uses the same field names as closed_picks.json so _build_features() can
    consume them directly.
    """
    # Determine status from PnL
    if pnl_pct > 0.1:
        status = "WON"
        exit_reason = "TAKE_PROFIT"
    elif pnl_pct < -0.1:
        status = "LOST"
        exit_reason = "STOP_LOSS"
    else:
        status = "WON" if pnl_pct >= 0 else "LOST"
        exit_reason = "TIME_EXIT"

    # Estimate entry/exit prices (use BTC-scale for crypto, 1.0 for unknown)
    base_price = 50000.0 if "BTC" in symbol else (3000.0 if "ETH" in symbol else 100.0)
    entry_price = base_price
    exit_price = base_price * (1 + pnl_pct / 100.0)

    # Estimate TP/SL from win_rate and pnl
    tp_distance = abs(pnl_pct) / 100.0 if pnl_pct > 0 else 0.02
    sl_distance = abs(pnl_pct) / 100.0 if pnl_pct < 0 else 0.01

    if direction == "BUY":
        take_profit = entry_price * (1 + tp_distance)
        stop_loss = entry_price * (1 - sl_distance)
    else:
        take_profit = entry_price * (1 - tp_distance)
        stop_loss = entry_price * (1 + sl_distance)

    # Confidence from win_rate and sharpe
    conf = min(0.95, max(0.3, win_rate * 0.6 + min(sharpe, 3.0) / 10.0 + 0.2))

    pick_id = f"bt_{strategy}::{symbol}::{entry_date}"

    return {
        "id": pick_id,
        "strategy": strategy,
        "symbol": symbol,
        "category": "crypto",
        "signal_type": direction,
        "entry_price": round(entry_price, 6),
        "entry_date": entry_date,
        "take_profit": round(take_profit, 6),
        "stop_loss": round(stop_loss, 6),
        "confidence": round(conf, 3),
        "ml_score": None,
        "exit_price": round(exit_price, 6),
        "exit_date": entry_date,  # same day for daily PnL
        "exit_reason": exit_reason,
        "pnl_pct": round(pnl_pct, 4),
        "pnl_dollar": round(pnl_pct * 100, 2),  # assume $10k base
        "high_water_mark": round(max(entry_price, exit_price), 6),
        "status": status,
        "regime_at_entry": "neutral",
        "atr_at_entry": None,
        "rsi_at_entry": None,
        "volume_ratio": None,
        "hold_days": 1,
        "source": "backtest",
        "source_weight": BACKTEST_WEIGHT,
        "source_file": source_file,
        "extra_json": json.dumps({
            "backtest_win_rate": round(win_rate, 4),
            "backtest_sharpe": round(sharpe, 4),
            "backtest_profit_factor": round(profit_factor, 4),
            "backtest_max_drawdown": round(max_drawdown, 4),
            "backtest_total_trades": total_trades,
            "source": "backtest",
            "source_weight": BACKTEST_WEIGHT,
        }),
    }


def _parse_daily_pnl_files(backtest_dir: Path) -> list[dict]:
    """Parse real_data_directional_*.json files which have daily_pnl per strategy.

    These are the richest source -- each daily_pnl entry represents actual
    simulated trades with date, pnl_pct, wins, and losses.
    """
    picks = []
    pattern = "real_data_directional_*.json"
    for fpath in sorted(backtest_dir.glob(pattern)):
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        profiles = data.get("profiles", [])
        pair = data.get("source", {}).get("pair", "BTC/USDT")
        symbol = _normalize_symbol(pair)
        fname = fpath.name

        for profile in profiles:
            strategy = profile.get("strategy_name", "")
            if not strategy:
                continue

            overall = profile.get("overall", {})
            strat_wr = _safe_float(overall.get("win_rate"), 0.5)
            strat_sharpe = _safe_float(overall.get("sharpe"), 0.0)
            strat_pf = _safe_float(overall.get("profit_factor"), 1.0)
            strat_dd = _safe_float(overall.get("max_drawdown"), 0.0)
            strat_trades = int(_safe_float(overall.get("trades"), 0))

            # Derive direction from long/short trade breakdown in the profile.
            long_stats = profile.get("long", {})
            short_stats = profile.get("short", {})
            long_trades = int(_safe_float(long_stats.get("trades"), 0))
            short_trades = int(_safe_float(short_stats.get("trades"), 0))

            if long_trades + short_trades > 0:
                long_ratio = long_trades / (long_trades + short_trades)
            else:
                long_ratio = 1.0
                logger.debug(
                    "No long/short breakdown for %s in %s; defaulting to BUY",
                    strategy, fpath.name,
                )

            daily_pnl = profile.get("daily_pnl", [])
            if not daily_pnl:
                continue

            for day in daily_pnl:
                date = day.get("date", "2025-01-01")
                pnl_pct = _safe_float(day.get("pnl_pct"), 0.0)
                wins = int(_safe_float(day.get("wins"), 0))
                losses = int(_safe_float(day.get("losses"), 0))
                n_trades = int(_safe_float(day.get("trades"), 1))

                if n_trades == 0:
                    continue

                # Generate individual pseudo-trades from daily aggregates
                # If we have W wins and L losses, create W winning picks and L losing picks
                if wins + losses > 0 and n_trades > 1:
                    # Distribute PnL: wins get positive share, losses get negative
                    if wins > 0 and pnl_pct > 0:
                        win_pnl = pnl_pct / wins
                    elif wins > 0:
                        win_pnl = abs(pnl_pct) * 0.3 / wins  # small win despite net loss
                    else:
                        win_pnl = 0

                    if losses > 0 and pnl_pct < 0:
                        loss_pnl = pnl_pct / losses
                    elif losses > 0:
                        loss_pnl = -abs(pnl_pct) * 0.3 / losses  # small loss despite net win
                    else:
                        loss_pnl = 0

                    n_long_wins = round(wins * long_ratio)
                    for i in range(wins):
                        direction = "BUY" if i < n_long_wins else "SELL"
                        picks.append(_make_closed_pick(
                            strategy=strategy, symbol=symbol,
                            pnl_pct=win_pnl, win_rate=strat_wr,
                            sharpe=strat_sharpe, entry_date=date,
                            direction=direction, total_trades=strat_trades,
                            profit_factor=strat_pf, max_drawdown=strat_dd,
                            source_file=fname,
                        ))

                    n_long_losses = round(losses * long_ratio)
                    for i in range(losses):
                        direction = "BUY" if i < n_long_losses else "SELL"
                        picks.append(_make_closed_pick(
                            strategy=strategy, symbol=symbol,
                            pnl_pct=loss_pnl, win_rate=strat_wr,
                            sharpe=strat_sharpe, entry_date=date,
                            direction=direction, total_trades=strat_trades,
                            profit_factor=strat_pf, max_drawdown=strat_dd,
                            source_file=fname,
                        ))
                else:
                    # Single trade day
                    direction = "BUY" if pnl_pct >= 0 else "SELL"
                    picks.append(_make_closed_pick(
                        strategy=strategy, symbol=symbol,
                        pnl_pct=pnl_pct, win_rate=strat_wr,
                        sharpe=strat_sharpe, entry_date=date,
                        direction=direction, total_trades=strat_trades,
                        profit_factor=strat_pf, max_drawdown=strat_dd,
                        source_file=fname,
                    ))

    return picks


def _parse_vectorized_backtest(backtest_dir: Path) -> list[dict]:
    """Parse vectorized_backtest_results.json -- per-symbol per-strategy stats.

    These have summary-level data (total_trades, win_rate, avg_pnl_pct) but
    no individual trades. We synthesize pseudo-trades from the aggregates.
    """
    picks = []
    vbt_path = _THIS_DIR / "data" / "vectorized_backtest_results.json"
    if not vbt_path.exists():
        return picks

    try:
        with open(vbt_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return picks

    results_by_symbol = data.get("results_by_symbol", {})
    gen_at = data.get("generated_at", "2026-03-01T00:00:00+00:00")
    # Extract date from generated_at
    base_date = gen_at[:10] if len(gen_at) >= 10 else "2026-03-01"

    for symbol_raw, strategies in results_by_symbol.items():
        symbol = _normalize_symbol(symbol_raw)
        for strat_name, test_types in strategies.items():
            for test_type, stats in test_types.items():
                total_trades = int(_safe_float(stats.get("total_trades"), 0))
                if total_trades < 2:
                    continue

                win_rate = _safe_float(stats.get("win_rate"), 50.0) / 100.0
                avg_pnl = _safe_float(stats.get("avg_pnl_pct"), 0.0)
                sharpe = _safe_float(stats.get("sharpe_ratio"), 0.0)
                pf = _safe_float(stats.get("profit_factor"), 1.0)
                max_dd = abs(_safe_float(stats.get("max_drawdown_pct"), 0.0)) / 100.0
                best_trade = _safe_float(stats.get("best_trade_pct"), 0.0)
                worst_trade = _safe_float(stats.get("worst_trade_pct"), 0.0)

                # Tag inverse strategies
                is_inverse = "inverse" in test_type
                effective_strat = f"{strat_name}_inv" if is_inverse else strat_name

                # Synthesize trades: create wins and losses based on win_rate
                n_wins = max(1, int(total_trades * win_rate))
                n_losses = max(0, total_trades - n_wins)

                # Estimate per-trade PnL for wins and losses
                if n_wins > 0 and best_trade > 0:
                    win_pnl = min(best_trade, avg_pnl * 2) if avg_pnl > 0 else best_trade * 0.5
                else:
                    win_pnl = abs(avg_pnl) if avg_pnl > 0 else 0.5

                if n_losses > 0 and worst_trade < 0:
                    loss_pnl = max(worst_trade, avg_pnl * 2) if avg_pnl < 0 else worst_trade * 0.5
                else:
                    loss_pnl = -abs(avg_pnl) if avg_pnl < 0 else -0.5

                # Cap to avoid extreme outliers
                win_pnl = min(win_pnl, 15.0)
                loss_pnl = max(loss_pnl, -15.0)

                # Sample a subset -- don't create thousands from a single summary
                sample_wins = min(n_wins, 10)
                sample_losses = min(n_losses, 10)

                for i in range(sample_wins):
                    picks.append(_make_closed_pick(
                        strategy=effective_strat, symbol=symbol,
                        pnl_pct=win_pnl, win_rate=win_rate,
                        sharpe=sharpe, entry_date=base_date,
                        direction="BUY", total_trades=total_trades,
                        profit_factor=pf, max_drawdown=max_dd,
                        source_file="vectorized_backtest_results.json",
                    ))

                for i in range(sample_losses):
                    picks.append(_make_closed_pick(
                        strategy=effective_strat, symbol=symbol,
                        pnl_pct=loss_pnl, win_rate=win_rate,
                        sharpe=sharpe, entry_date=base_date,
                        direction="BUY", total_trades=total_trades,
                        profit_factor=pf, max_drawdown=max_dd,
                        source_file="vectorized_backtest_results.json",
                    ))

    return picks


def _parse_sweep_files(backtest_dir: Path) -> list[dict]:
    """Parse real_data_sweep_*.json, google_antigravity_*.json, codex10_*.json,
    cursor_ai_*.json, shortterm_battle_*.json -- strategy-level summaries.

    These only have aggregate stats per strategy. We synthesize a small number
    of pseudo-trades from each strategy's summary.
    """
    picks = []

    # Patterns that match sweep/summary files
    patterns = [
        "real_data_sweep_*.json",
        "google_antigravity_*.json",
        "codex10_*.json",
        "cursor_ai_*.json",
        "shortterm_battle_*.json",
        "tiered_test_results.json",
        "realism_audit_*.json",
    ]

    for pattern in patterns:
        for fpath in sorted(backtest_dir.glob(pattern)):
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            fname = fpath.name
            ts = _extract_timestamp_from_filename(fname)
            base_date = ts[:10] if ts else "2026-02-26"

            # Try different keys where results might live
            results = data.get("results", data.get("rows", []))
            if not isinstance(results, list):
                continue

            for entry in results:
                strategy = entry.get("strategy_name", "")
                if not strategy:
                    continue

                total_trades = int(_safe_float(entry.get("total_trades"), 0))
                if total_trades < 2:
                    continue

                # Normalize win_rate (some files use 0-1, others 0-100)
                wr_raw = _safe_float(entry.get("win_rate"), 0.5)
                win_rate = wr_raw if wr_raw <= 1.0 else wr_raw / 100.0

                sharpe = _safe_float(entry.get("sharpe"), 0.0)
                pf = _safe_float(entry.get("profit_factor"), 1.0)
                total_return = _safe_float(entry.get("total_return"), 0.0)
                max_dd = abs(_safe_float(entry.get("max_drawdown"), 0.0))

                # Get pair/symbol
                pair = entry.get("pair", "BTC/USDT")
                symbol = _normalize_symbol(pair)

                # Skip errored/timeout strategies
                status = entry.get("status", "")
                if status in ("timeout", "error", "crashed"):
                    continue

                # Estimate avg PnL per trade
                avg_pnl = (total_return / total_trades * 100) if total_trades > 0 else 0.0

                # Synthesize limited pseudo-trades
                n_wins = max(1, int(min(total_trades, 20) * win_rate))
                n_losses = max(0, min(total_trades, 20) - n_wins)

                # Win/loss PnL estimates
                win_pnl = abs(avg_pnl) * 1.5 if avg_pnl > 0 else 0.3
                loss_pnl = -(abs(avg_pnl) * 1.5) if avg_pnl < 0 else -0.3

                # Cap extremes
                win_pnl = min(win_pnl, 10.0)
                loss_pnl = max(loss_pnl, -10.0)

                sample_wins = min(n_wins, 5)
                sample_losses = min(n_losses, 5)

                for _ in range(sample_wins):
                    picks.append(_make_closed_pick(
                        strategy=strategy, symbol=symbol,
                        pnl_pct=win_pnl, win_rate=win_rate,
                        sharpe=sharpe, entry_date=base_date,
                        direction="BUY", total_trades=total_trades,
                        profit_factor=pf, max_drawdown=max_dd,
                        source_file=fname,
                    ))

                for _ in range(sample_losses):
                    picks.append(_make_closed_pick(
                        strategy=strategy, symbol=symbol,
                        pnl_pct=loss_pnl, win_rate=win_rate,
                        sharpe=sharpe, entry_date=base_date,
                        direction="BUY", total_trades=total_trades,
                        profit_factor=pf, max_drawdown=max_dd,
                        source_file=fname,
                    ))

    return picks


def convert_backtest_to_training(backtest_dir: str = "") -> list[dict]:
    """Convert backtest results into ML training format.

    For each backtest file:
    1. Parse the results (format varies by file type)
    2. Extract: symbol, strategy, direction, entry_price, exit_price, pnl_pct,
       take_profit, stop_loss, confidence, timestamp (estimated)
    3. Convert to closed_picks format
    4. Add a 'source' field: 'backtest' (vs 'live' for real trades)
    5. Apply lower weight: 0.3x (backtest data is less reliable than live)

    Returns list of pseudo-closed-picks dicts.
    """
    bt_dir = Path(backtest_dir) if backtest_dir else _BACKTEST_DIR

    if not bt_dir.exists():
        print(f"  [Bridge] Backtest directory not found: {bt_dir}")
        return []

    all_picks = []

    # Priority 1: daily_pnl files (richest trade-level data)
    daily_picks = _parse_daily_pnl_files(bt_dir)
    print(f"  [Bridge] daily_pnl files: {len(daily_picks)} pseudo-trades")
    all_picks.extend(daily_picks)

    # Priority 2: vectorized backtest results
    vbt_picks = _parse_vectorized_backtest(bt_dir)
    print(f"  [Bridge] vectorized backtest: {len(vbt_picks)} pseudo-trades")
    all_picks.extend(vbt_picks)

    # Priority 3: sweep/summary files
    sweep_picks = _parse_sweep_files(bt_dir)
    print(f"  [Bridge] sweep/summary files: {len(sweep_picks)} pseudo-trades")
    all_picks.extend(sweep_picks)

    # Deduplicate by pick ID
    seen_ids = set()
    unique_picks = []
    for p in all_picks:
        pid = p["id"]
        if pid not in seen_ids:
            seen_ids.add(pid)
            unique_picks.append(p)

    print(f"  [Bridge] Total unique backtest pseudo-trades: {len(unique_picks)}")
    return unique_picks


def augment_training_data(
    closed_picks: list[dict],
    backtest_picks: list[dict],
    max_backtest_ratio: float = 3.0,
) -> list[dict]:
    """Merge live closed picks with backtest picks for training.

    Rules:
    - Live picks get weight 1.0
    - Backtest picks get weight 0.3 (lower trust -- possible look-ahead bias)
    - Cap backtest ratio: max 3x backtest per 1x live (don't let backtest dominate)
    - Shuffle but maintain chronological order within each source

    Returns augmented training list.
    """
    # Tag live picks
    live = []
    for p in closed_picks:
        cp = dict(p)
        cp.setdefault("source", "live")
        cp.setdefault("source_weight", 1.0)
        live.append(cp)

    n_live = len(live)
    max_bt = int(n_live * max_backtest_ratio)

    # Cap backtest picks
    bt = list(backtest_picks)
    if len(bt) > max_bt and max_bt > 0:
        # Prioritize by diversity: sample across strategies
        strategies = {}
        for p in bt:
            s = p.get("strategy", "unknown")
            strategies.setdefault(s, []).append(p)

        # Round-robin sample from each strategy
        sampled = []
        strat_lists = list(strategies.values())
        random.shuffle(strat_lists)
        idx = 0
        while len(sampled) < max_bt:
            added_any = False
            for sl in strat_lists:
                if idx < len(sl) and len(sampled) < max_bt:
                    sampled.append(sl[idx])
                    added_any = True
            idx += 1
            if not added_any:
                break
        bt = sampled

    print(f"  [Bridge] Augmentation: {n_live} live + {len(bt)} backtest "
          f"(capped from {len(backtest_picks)}, ratio={max_backtest_ratio}x)")

    # Merge: live first, then backtest (both in chronological order internally)
    augmented = live + bt
    return augmented


def _load_closed_picks() -> list[dict]:
    """Load live closed picks from JSON."""
    if not _CLOSED_PICKS_PATH.exists():
        print(f"  [Bridge] closed_picks.json not found at {_CLOSED_PICKS_PATH}")
        return []
    try:
        with open(_CLOSED_PICKS_PATH, "r", encoding="utf-8", errors="replace") as f:
            picks = json.load(f)
        return picks if isinstance(picks, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [Bridge] Error loading closed_picks.json: {e}")
        return []


def save_augmented_training_data(
    output_path: str = "",
) -> dict:
    """Run the full pipeline and save augmented data.

    Returns summary dict with counts.
    """
    out_path = Path(output_path) if output_path else _AUGMENTED_OUTPUT_PATH

    # Load live closed picks
    live_picks = _load_closed_picks()
    print(f"  [Bridge] Loaded {len(live_picks)} live closed picks")

    # Convert backtest data
    bt_picks = convert_backtest_to_training()

    # Augment
    augmented = augment_training_data(live_picks, bt_picks)

    # Save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(augmented, f, indent=2, default=str)

    summary = {
        "live_picks": len(live_picks),
        "backtest_picks_raw": len(bt_picks),
        "backtest_picks_used": len(augmented) - len(live_picks),
        "augmented_total": len(augmented),
        "output_path": str(out_path),
        "backtest_weight": BACKTEST_WEIGHT,
    }
    print(f"\n  [Bridge] === SUMMARY ===")
    print(f"  [Bridge] Live picks:      {summary['live_picks']}")
    print(f"  [Bridge] Backtest raw:    {summary['backtest_picks_raw']}")
    print(f"  [Bridge] Backtest used:   {summary['backtest_picks_used']}")
    print(f"  [Bridge] Augmented total: {summary['augmented_total']}")
    print(f"  [Bridge] Output: {out_path}")
    return summary


if __name__ == "__main__":
    print("=" * 60)
    print("  Backtest-to-ML Bridge -- Alpha Engine")
    print("=" * 60)
    summary = save_augmented_training_data()
    print("\nDone.")
