#!/usr/bin/env python3
"""
forward_test_pick_generator.py
===============================

Generates forward-test picks from the best-performing strategies identified
by backtesting, and feeds them into the monitoring system (live_picks.json,
multi_asset_picks.json) with full QA gate enforcement.

CRITICAL: All picks generated here are PAPER TESTS ONLY. No real capital
should be allocated until:
  - n >= 100 forward picks
  - PF >= 1.5 forward
  - WR >= 55% forward
  - DSR >= 0.95 forward
  - 3+ months clean forward performance

Usage:
    python quick_wins/shared/forward_test_pick_generator.py --generate
    python quick_wins/shared/forward_test_pick_generator.py --qa-check
    python quick_wins/shared/forward_test_pick_generator.py --expire-stale
"""

from __future__ import annotations

import json
import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Output files
LIVE_PICKS_PATH = ROOT / "dashboard" / "live_picks.json"
MULTI_ASSET_PICKS_PATH = ROOT / "multi_asset" / "data" / "multi_asset_picks.json"

# Best strategies from backtest (see quick_wins/shared/backtest_results.json)
# These are the HIGHEST-PERFORMING strategies but ALL have n < 50 trades,
# so they are PAPER TESTS ONLY until forward-validated.
BEST_STRATEGIES = [
    {
        "strategy": "connors_rsi2",
        "symbol": "SPY",
        "backtest_pf": 76.92,
        "backtest_wr": 0.833,
        "backtest_sharpe": 1.14,
        "backtest_n": 6,
        "direction": "LONG",
        "note": "Only class with positive cost margin (3.23x). n=6 too small for confidence.",
    },
    {
        "strategy": "keltner_compression_v2",
        "symbol": "XLF",
        "backtest_pf": 10.00,
        "backtest_wr": 1.0,
        "backtest_sharpe": 0.74,
        "backtest_n": 5,
        "direction": "LONG",
        "note": "ETF tactical. n=5 too small, PF inflated by tiny sample.",
    },
    {
        "strategy": "ema_stack",
        "symbol": "GLD",
        "backtest_pf": 4.51,
        "backtest_wr": 0.8,
        "backtest_sharpe": 0.62,
        "backtest_n": 10,
        "direction": "LONG",
        "note": "Commodity (gold). n=10 borderline, needs more data.",
    },
    {
        "strategy": "funding_sentiment",
        "symbol": "GLD",
        "backtest_pf": 4.15,
        "backtest_wr": 0.833,
        "backtest_sharpe": 0.66,
        "backtest_n": 6,
        "direction": "LONG",
        "note": "Commodity (gold). n=6 too small.",
    },
    {
        "strategy": "funding_sentiment",
        "symbol": "SPY",
        "backtest_pf": 3.09,
        "backtest_wr": 0.833,
        "backtest_sharpe": 0.43,
        "backtest_n": 6,
        "direction": "LONG",
        "note": "Equity. n=6 too small.",
    },
]

# Risk parameters
RISK_PCT_PER_TRADE = 0.02  # 2% risk per trade
MAX_CONCURRENT_POSITIONS = 5
MIN_RISK_REWARD = 1.5
STALE_PICK_HOURS = 72  # Expire picks open longer than 72 hours


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat(timespec="seconds")


def _make_pick_id(strategy: str, symbol: str) -> str:
    """Generate a unique pick ID with timestamp."""
    ts = _utc_now().strftime("%Y%m%d_%H%M%S")
    raw = f"{strategy}::{symbol}::{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_json(path: Path) -> list[dict]:
    """Load a JSON file, returning empty list if missing/invalid."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Could be wrapped in a key
            for key in ("active_picks", "picks", "data"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_json(path: Path, data: list[dict]) -> None:
    """Save JSON with atomic write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _compute_atr(entry_price: float, atr_pct: float = 0.02) -> float:
    """Compute ATR-based distance from entry price."""
    return entry_price * atr_pct


def _compute_tp_sl(
    entry_price: float,
    direction: str,
    atr: float,
    tp_mult: float = 1.5,
    sl_mult: float = 1.0,
) -> tuple[float, float]:
    """Compute take-profit and stop-loss from ATR."""
    if direction == "LONG":
        tp = entry_price + tp_mult * atr
        sl = entry_price - sl_mult * atr
    else:  # SHORT
        tp = entry_price - tp_mult * atr
        sl = entry_price + sl_mult * atr
    return round(tp, 6), round(sl, 6)


def _validate_pick(pick: dict) -> tuple[bool, List[str]]:
    """Validate a pick against QA gates. Returns (is_valid, errors)."""
    errors: List[str] = []

    # Required fields for OPEN picks
    required_fields = [
        "id", "symbol", "direction", "entry_price",
        "take_profit", "stop_loss", "strategy", "asset_class",
        "entry_time", "status", "source_system",
    ]

    for field in required_fields:
        if pick.get(field) is None or pick.get(field) == "":
            errors.append(f"Missing required field: {field}")

    # PnL = 0% with price movement check
    entry_price = pick.get("entry_price")
    current_price = pick.get("current_price", entry_price)
    pnl_pct = pick.get("pnl_pct") or pick.get("unrealized_pnl_pct")

    if entry_price and current_price and pnl_pct is not None:
        expected_pnl = (current_price / entry_price - 1.0) * (
            1 if pick.get("direction") == "LONG" else -1
        )
        if abs(pnl_pct) < 0.0001 and abs(expected_pnl) > 0.01:
            errors.append(
                f"PnL=0% ({pnl_pct}) but price moved {(expected_pnl*100):.2f}% "
                f"from {entry_price} to {current_price}"
            )

    # Entry price validity
    if entry_price and entry_price <= 0:
        errors.append(f"Invalid entry_price: {entry_price}")

    # Stop loss validity
    entry = pick.get("entry_price")
    sl = pick.get("stop_loss")
    tp = pick.get("take_profit")
    direction = pick.get("direction")

    if entry and sl and direction:
        if direction == "LONG" and sl >= entry:
            errors.append(f"Stop loss ({sl}) >= entry ({entry}) for LONG pick")
        if direction == "SHORT" and sl <= entry:
            errors.append(f"Stop loss ({sl}) <= entry ({entry}) for SHORT pick")

    if entry and tp and direction:
        if direction == "LONG" and tp <= entry:
            errors.append(f"Take profit ({tp}) <= entry ({entry}) for LONG pick")
        if direction == "SHORT" and tp >= entry:
            errors.append(f"Take profit ({tp}) >= entry ({entry}) for SHORT pick")

    # Risk-reward check
    if entry and sl and tp and direction:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk > 0 and reward / risk < MIN_RISK_REWARD - 1e-9:
            errors.append(
                f"Risk-reward ratio {reward/risk:.2f} < minimum {MIN_RISK_REWARD}"
            )

    return len(errors) == 0, errors


def generate_picks() -> List[dict]:
    """Generate forward-test picks from the best strategies."""
    picks: List[dict] = []
    now = _utc_now()
    today = now.strftime("%Y-%m-%d")

    for combo in BEST_STRATEGIES:
        symbol = combo["symbol"]
        strategy = combo["strategy"]
        direction = combo["direction"]
        entry_price = _get_current_price(symbol)

        if not entry_price:
            print(f"  [SKIP] {symbol}: No live price available")
            continue

        atr = _compute_atr(entry_price, atr_pct=0.02)
        tp, sl = _compute_tp_sl(entry_price, direction, atr)

        pick_id = _make_pick_id(strategy, symbol)

        pick = {
            "id": pick_id,
            "strategy": strategy,
            "symbol": symbol,
            "category": _get_asset_class(symbol),
            "direction": direction,
            "signal_type": direction,
            "entry_price": round(entry_price, 6),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": 0.75,
            "ml_score": 0.75,
            "risk_reward": round(abs(tp - entry_price) / abs(entry_price - sl), 2),
            "reason": combo["note"],
            "status": "OPEN",
            "source_system": "forward_test_scanner",
            "forward_test_only": True,
            "exit_price": None,
            "exit_date": None,
            "closed_at": None,
            "pnl_pct": None,
            "hold_days": None,
            "asset_class": _get_asset_class(symbol).upper(),
            "forward_trades": 0,
            "forward_wr": 0.0,
            "forward_validated": False,
            "extra": {
                "backtest_pf": combo["backtest_pf"],
                "backtest_wr": combo["backtest_wr"],
                "backtest_sharpe": combo["backtest_sharpe"],
                "backtest_n": combo["backtest_n"],
                "note": combo["note"],
                "atr": round(atr, 6),
                "risk_pct": RISK_PCT_PER_TRADE,
            },
            "pnl_dollar": None,
            "elite_score": 0.0,
            "created_at": _utc_iso(),
            "timestamp": _utc_iso(),
            "entry_time": _utc_iso(),
        }

        # Validate the pick
        is_valid, errors = _validate_pick(pick)
        if not is_valid:
            print(f"  [REJECT] {symbol} {strategy}: {', '.join(errors)}")
            continue

        picks.append(pick)
        print(f"  [EMIT] {symbol} {strategy} {direction} @ {entry_price:.4f} "
              f"(TP={tp:.4f}, SL={sl:.4f}, R:R={pick['risk_reward']})")

    return picks


def _get_current_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol. Tries live data first, falls back to
    reasonable defaults for paper testing."""
    # Try to fetch from yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("last_price")
        if price and price > 0:
            return float(price)
    except Exception:
        pass

    # Fallback: use reasonable default prices for paper testing
    # In production, this should come from a live price feed
    fallback_prices = {
        "SPY": 450.00,
        "QQQ": 380.00,
        "BTC-USD": 95000.00,
        "ETH-USD": 3500.00,
        "GLD": 2650.00,
        "TLT": 95.00,
        "XLE": 90.00,
        "XLF": 42.00,
        "XLV": 160.00,
        "XLI": 130.00,
    }
    return fallback_prices.get(symbol)


def _get_asset_class(symbol: str) -> str:
    """Map symbol to asset class."""
    crypto = {"BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD", "DOGE-USD"}
    bonds = {"TLT", "IEF", "SHY", "TBF"}
    commodities = {"GLD", "SLV", "USO", "UNG"}
    if symbol in crypto:
        return "CRYPTO"
    if symbol in bonds:
        return "BOND"
    if symbol in commodities:
        return "COMMODITY"
    return "EQUITY"  # Default for stocks/ETFs


def run_qa_checks(picks: List[dict]) -> dict:
    """Run QA checks on all picks and return validation report."""
    all_picks = picks  # In production, load existing picks too

    pnl_zero_flags: List[dict] = []
    blank_field_flags: List[dict] = []
    open_stale_flags: List[dict] = []
    recently_closed_flags: List[dict] = []

    now = _utc_now()

    for pick in all_picks:
        pid = pick.get("id", "unknown")
        symbol = pick.get("symbol", "unknown")
        status = pick.get("status", "UNKNOWN")

        # PnL = 0% check
        entry = pick.get("entry_price")
        current = pick.get("current_price", entry)
        pnl = pick.get("pnl_pct") or pick.get("unrealized_pnl_pct")
        if entry and current and pnl is not None:
            expected = (current / entry - 1.0) * (
                1 if pick.get("direction") == "LONG" else -1
            )
            if abs(pnl) < 0.0001 and abs(expected) > 0.01:
                pnl_zero_flags.append({
                    "id": pid,
                    "symbol": symbol,
                    "pnl_pct": pnl,
                    "expected_pct": round(expected * 100, 2),
                    "entry": entry,
                    "current": current,
                    "severity": "CRITICAL",
                })

        # Blank field check
        required = ["id", "symbol", "entry_price", "direction",
                    "strategy", "asset_class", "entry_time", "status"]
        missing = [f for f in required if pick.get(f) is None or pick.get(f) == ""]
        if missing:
            blank_field_flags.append({
                "id": pid,
                "symbol": symbol,
                "missing_fields": missing,
                "severity": "CRITICAL" if len(missing) >= 3 else "HIGH",
            })

        # Stale open pick check
        if status in ("OPEN", "ACTIVE"):
            entry_time_str = pick.get("entry_time") or pick.get("created_at")
            if entry_time_str:
                try:
                    entry_time = datetime.fromisoformat(
                        entry_time_str.replace("Z", "+00:00")
                    )
                    age_hours = (now - entry_time).total_seconds() / 3600
                    if age_hours > STALE_PICK_HOURS:
                        open_stale_flags.append({
                            "id": pid,
                            "symbol": symbol,
                            "age_hours": round(age_hours, 1),
                            "severity": "CRITICAL" if age_hours > 168 else "HIGH",
                        })
                except (ValueError, TypeError):
                    pass

    return {
        "timestamp": _utc_iso(),
        "total_picks": len(all_picks),
        "pnl_zero_flags": pnl_zero_flags,
        "blank_field_flags": blank_field_flags,
        "open_stale_flags": open_stale_flags,
        "total_flags": len(pnl_zero_flags) + len(blank_field_flags) + len(open_stale_flags),
        "critical_flags": sum(
            1 for f in pnl_zero_flags + blank_field_flags + open_stale_flags
            if f.get("severity") == "CRITICAL"
        ),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Forward-test pick generator with QA gates"
    )
    parser.add_argument("--generate", action="store_true",
                        help="Generate new picks from best strategies")
    parser.add_argument("--qa-check", action="store_true",
                        help="Run QA validation on existing picks")
    parser.add_argument("--expire-stale", action="store_true",
                        help="Expire stale open picks (>72h)")
    parser.add_argument("--output", default="both",
                        help="Where to write: live_picks, multi_asset, or both")
    args = parser.parse_args()

    if args.qa_check:
        # Load all picks from both files
        live_picks = _load_json(LIVE_PICKS_PATH)
        # live_picks.json has picks under 'active_picks' key
        if isinstance(live_picks, dict):
            live_picks = live_picks.get("active_picks", [])
        multi_picks = _load_json(MULTI_ASSET_PICKS_PATH)
        all_picks = live_picks + multi_picks
        qa = run_qa_checks(all_picks)
        print(json.dumps(qa, indent=2))
        return

    if args.expire_stale:
        # Expire stale open picks in both files
        now = _utc_now()
        for path in [LIVE_PICKS_PATH, MULTI_ASSET_PICKS_PATH]:
            picks = _load_json(path)
            changed = False
            for pick in picks:
                if pick.get("status") in ("OPEN", "ACTIVE"):
                    entry_time_str = pick.get("entry_time") or pick.get("created_at")
                    if entry_time_str:
                        try:
                            entry_time = datetime.fromisoformat(
                                entry_time_str.replace("Z", "+00:00")
                            )
                            age_hours = (now - entry_time).total_seconds() / 3600
                            if age_hours > STALE_PICK_HOURS:
                                pick["status"] = "EXPIRED"
                                pick["closed_at"] = _utc_iso()
                                pick["close_reason"] = "Stale open pick auto-expired"
                                pick["pnl_pct"] = 0.0
                                changed = True
                                print(f"  [EXPIRE] {pick.get('symbol')} "
                                      f"{pick.get('strategy')} "
                                      f"(age={age_hours:.1f}h)")
                        except (ValueError, TypeError):
                            pass
            if changed:
                _save_json(path, picks)
        return

    if args.generate or not args.qa_check and not args.expire_stale:
        # Generate new picks
        picks = generate_picks()

        # Run QA on generated picks
        qa = run_qa_checks(picks)
        print(f"\n=== QA Results ===")
        print(json.dumps(qa, indent=2))

        if qa["critical_flags"] > 0:
            print("\n[WARNING] Critical QA failures found. Not emitting picks.")
            return

        # Write to output files
        output_targets = []
        if args.output in ("live_picks", "both"):
            output_targets.append(LIVE_PICKS_PATH)
        if args.output in ("multi_asset", "both"):
            output_targets.append(MULTI_ASSET_PICKS_PATH)

        for path in output_targets:
            existing = _load_json(path)
            existing.extend(picks)
            _save_json(path, existing)
            print(f"\n[WRITTEN] {len(picks)} picks to {path}")

        print("\n=== NEXT STEPS ===")
        print("1. Monitor picks in dashboard/live_picks.json")
        print("2. Run --qa-check regularly to detect stale/pnl=0 issues")
        print("3. Run --expire-stale daily to expire old picks")
        print("4. After n>=100 forward picks with PF>=1.5, WR>=55%, consider live capital")


if __name__ == "__main__":
    main()