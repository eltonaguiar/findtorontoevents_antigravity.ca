#!/usr/bin/env python3
"""macd_rsi_m048 shadow generator — daily emitter for paper-pilot picks.

EAGLE-3 second promotion candidate. The strategy class
(MACDRSIMomentumStrategy at baby_strategies/proven_winners.py:39) has lab
stats PF 3.06 / WR 75.4% on n=65 closed picks but no production caller —
so no live forward stats exist (0 rows in trading_picks tagged
source_system='macd_rsi_m048' as of 2026-06-03 audit).

This script CLOSES the emission gap for SHADOW MODE ONLY:
  - Scans a fixed top-10 CRYPTO universe
  - Fetches daily OHLC via Binance klines (PR #512 helper)
  - Runs MACDRSIMomentumStrategy.generate_signals on each
  - Appends would-be picks to macd_rsi_m048_shadow_picks.jsonl
  - DOES NOT write to trading_picks (no live capital, no live audit pollution)

The companion tracker (macd_rsi_m048_pilot.py) reads these shadow picks +
later resolves them against live spot prices on a 14-day window to compute
forward PF/WR. After 30 days of shadow accumulation with PF≥1.5 / WR≥55%
/ n≥30, the strategy graduates to a real production wire-up.

Wiring Plan (per CLAUDE.md Wire-Up Rule):
  - Today: shadow JSONL only (this file).
  - +30 days, if shadow stats clear thresholds: add to
    audit_trail/promotion_gate.PROMOTED_STRATEGIES + write a production
    emitter that tags trading_picks rows with source_system='macd_rsi_m048'.
  - Caller: this script is invoked once daily from
    .github/workflows/macd-rsi-m048-shadow-daily.yml (to be added in
    follow-up PR; for now run manually via `python verified_strategies/
    paper_pilot/macd_rsi_m048_shadow_generator.py --once`).

Run:
  python verified_strategies/paper_pilot/macd_rsi_m048_shadow_generator.py --once
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baby_strategies.proven_winners import MACDRSIMomentumStrategy  # noqa: E402
from tools.ai_tournament.price_tracker import _fetch_ohlc_crypto_binance  # noqa: E402

PILOT_DIR = Path(__file__).resolve().parent
SHADOW_LOG = PILOT_DIR / "macd_rsi_m048_shadow_picks.jsonl"
STATE_PATH = PILOT_DIR / "macd_rsi_m048_state.json"

# Top-10 CRYPTO universe by Binance volume (mirrors AI tournament fleet)
CRYPTO_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT",
]

# Fetch ~90 daily bars to give MACD(26) + RSI(14) + ATR(14) sufficient warmup
LOOKBACK_DAYS = 90


def _fetch_ohlc_as_df(symbol: str):
    """Wrap _fetch_ohlc_crypto_binance into a pandas DataFrame for the strategy."""
    try:
        import pandas as pd
    except ImportError:
        return None
    start_iso = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    bars = _fetch_ohlc_crypto_binance(symbol, start_iso)
    if not bars:
        return None
    df = pd.DataFrame(bars)
    if df.empty or "close" not in df.columns:
        return None
    # MACDRSIMomentumStrategy reads close/high/low/volume — we don't have
    # volume in the binance daily klines we fetch (only OHLC). Synthesize
    # constant volume so the volume_mult filter passes by default; record
    # this caveat in shadow log so the operator sees it.
    if "volume" not in df.columns:
        df["volume"] = 1_000_000.0
    return df


def scan_universe_once() -> list[dict]:
    """Run the strategy on the full universe once. Returns list of pick dicts."""
    strat = MACDRSIMomentumStrategy()
    out: list[dict] = []
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for symbol in CRYPTO_UNIVERSE:
        df = _fetch_ohlc_as_df(symbol)
        if df is None:
            print(f"  [shadow] {symbol}: SKIP (no OHLC)")
            continue
        try:
            signals = strat.generate_signals(df, symbol=symbol)
        except Exception as exc:
            print(f"  [shadow] {symbol}: strategy error {type(exc).__name__}: {exc}")
            continue
        for s in signals:
            pick = {
                "asof_date": asof,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "symbol": s.symbol,
                "asset_class": "CRYPTO",
                "direction": "LONG" if s.direction.upper() == "BUY" else "SHORT",
                "entry_price": s.entry_price,
                "take_profit": s.take_profit,
                "stop_loss": s.stop_loss,
                "confidence": s.confidence,
                "source_system": "macd_rsi_m048",
                "strategy": "macd_rsi_m048",
                "reason": s.reason,
                "shadow_only": True,
                "volume_synthesized": True,
            }
            out.append(pick)
            print(f"  [shadow] {symbol} {pick['direction']} "
                  f"entry={s.entry_price:.4f} TP={s.take_profit:.4f} SL={s.stop_loss:.4f} "
                  f"conf={s.confidence}")
    return out


def append_shadow_log(picks: list[dict]) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with SHADOW_LOG.open("a", encoding="utf-8") as fh:
        for p in picks:
            fh.write(json.dumps(p, default=str) + "\n")


def update_state(n_picks: int) -> None:
    """Touch macd_rsi_m048_state.json with today's shadow emission count."""
    state: dict
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    else:
        state = {}
    state.setdefault("strategy_id", "macd_rsi_m048")
    state["shadow_emission_last_run_utc"] = datetime.now(timezone.utc).isoformat()
    state.setdefault("shadow_emission_total", 0)
    state["shadow_emission_total"] = int(state.get("shadow_emission_total", 0)) + n_picks
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="Run a single scan and exit (default).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan but do not append to shadow log or state.")
    args = parser.parse_args()

    picks = scan_universe_once()
    print(f"[shadow] generated {len(picks)} would-be pick(s)")

    if args.dry_run:
        print("[shadow] DRY-RUN — not writing shadow log or state.")
        return 0

    if picks:
        append_shadow_log(picks)
        update_state(len(picks))
        print(f"[shadow] appended to {SHADOW_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
