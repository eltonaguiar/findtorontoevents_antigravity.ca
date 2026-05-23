#!/usr/bin/env python3
"""
Leveraged ETF Decay Shorts — Live Pick Generator (structural edge)
===================================================================
Exploits volatility drag (mathematical certainty, not a pattern):
  3x leveraged products lose value via daily rebalancing even when the
  underlying is flat. SHORT 3x bear ETFs to harvest this structural decay.

Backtest results (2yr, wide-stop 10% SL / 20% TP):
  LABD: 76.9% WR, PF 2.94, avg +3.38%/trade (39 trades)
  JDST: 69.0% WR, PF 1.86, avg +2.14%/trade (29 trades)
  SOXS: 65.6% WR, PF 1.61, avg +2.10%/trade (32 trades)

Safety gate: do NOT short bear ETFs during actual sector crashes
(underlying in strong downtrend = the bear ETF is WORKING as designed).

Outputs: alpha_engine/data/etf_decay_picks.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "etf_decay_picks.json"

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Target universe: 3x bear ETFs and their underlying sector proxies
# ---------------------------------------------------------------------------
TARGETS = [
    {
        "symbol": "LABD",
        "name": "3x Short Biotech ETF",
        "underlying": "XBI",   # SPDR S&P Biotech
        "leverage": "3x",
        "sl_pct": 0.10,        # 10% stop loss
        "tp_pct": 0.20,        # 20% take profit
        "backtest_wr": 76.9,
        "backtest_pf": 2.94,
        "backtest_avg_pnl": 3.38,
        "backtest_n": 39,
    },
    {
        "symbol": "JDST",
        "name": "3x Short Junior Gold Miners ETF",
        "underlying": "GDXJ",  # VanEck Junior Gold Miners
        "leverage": "3x",
        "sl_pct": 0.10,
        "tp_pct": 0.20,
        "backtest_wr": 69.0,
        "backtest_pf": 1.86,
        "backtest_avg_pnl": 2.14,
        "backtest_n": 29,
    },
    {
        "symbol": "SOXS",
        "name": "3x Short Semiconductors ETF",
        "underlying": "SOXX",  # iShares Semiconductor
        "leverage": "3x",
        "sl_pct": 0.10,
        "tp_pct": 0.20,
        "backtest_wr": 65.6,
        "backtest_pf": 1.61,
        "backtest_avg_pnl": 2.10,
        "backtest_n": 32,
    },
]

# Realized volatility threshold: only fire when vol > 30% (more decay)
MIN_REALIZED_VOL = 0.30

# Underlying downtrend protection: skip if underlying dropped > 15% in 20 days
MAX_UNDERLYING_DROP = -0.15


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _flatten_yf(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _realized_vol(close: pd.Series, window: int = 20) -> float:
    """Annualized realized volatility over `window` trading days."""
    if len(close) < window + 1:
        return 0.0
    log_ret = np.log(close / close.shift(1)).dropna()
    return float(log_ret.tail(window).std() * np.sqrt(252))


def _period_return(close: pd.Series, window: int = 20) -> float:
    """Return over last `window` days."""
    if len(close) < window + 1:
        return 0.0
    return float((close.iloc[-1] / close.iloc[-(window + 1)] - 1))


def _sma(series: pd.Series, period: int) -> float:
    if len(series) < period:
        return float(series.iloc[-1])
    return float(series.rolling(period).mean().iloc[-1])


# ---------------------------------------------------------------------------
# Pick generator
# ---------------------------------------------------------------------------

def generate_picks(verbose: bool = True) -> list[dict]:
    """Generate leveraged ETF decay short picks."""
    if yf is None:
        if verbose:
            print("  ERROR: yfinance not available")
        return []

    now_utc = datetime.now(UTC).isoformat()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    picks: list[dict] = []

    # Fetch all symbols in one call
    all_syms = []
    for t in TARGETS:
        all_syms.extend([t["symbol"], t["underlying"]])

    try:
        raw = yf.download(" ".join(all_syms), period="6mo", interval="1d",
                          group_by="ticker", auto_adjust=True, progress=False)
    except Exception as e:
        if verbose:
            print(f"  ERROR fetching data: {e}")
        return []

    for target in TARGETS:
        sym = target["symbol"]
        und = target["underlying"]

        try:
            # Extract ETF data
            if sym in raw.columns.get_level_values(0):
                etf_df = raw[sym].dropna(subset=["Close"])
            else:
                if verbose:
                    print(f"  SKIP {sym}: no data")
                continue

            if len(etf_df) < 25:
                if verbose:
                    print(f"  SKIP {sym}: insufficient data ({len(etf_df)} bars)")
                continue

            etf_close = etf_df["Close"].squeeze()
            price = float(etf_close.iloc[-1])

            # --- Gate 1: Realized volatility > 30% (high vol = more decay) ---
            rvol = _realized_vol(etf_close, 20)
            if rvol < MIN_REALIZED_VOL:
                if verbose:
                    print(f"  SKIP {sym}: realized vol {rvol:.1%} < {MIN_REALIZED_VOL:.0%} threshold")
                continue

            # --- Gate 2: Underlying NOT in strong downtrend ---
            und_ret = 0.0
            if und in raw.columns.get_level_values(0):
                und_df = raw[und].dropna(subset=["Close"])
                if len(und_df) >= 25:
                    und_close = und_df["Close"].squeeze()
                    und_ret = _period_return(und_close, 20)
                    und_sma50 = _sma(und_close, 50)
                    und_price = float(und_close.iloc[-1])

                    # Skip if underlying crashed > 15% in 20 days (bear ETF is working!)
                    if und_ret < MAX_UNDERLYING_DROP:
                        if verbose:
                            print(f"  SKIP {sym}: underlying {und} down {und_ret:.1%} "
                                  f"(>{MAX_UNDERLYING_DROP:.0%} = strong downtrend, bear ETF is working)")
                        continue

            # --- Confidence based on backtest WR + vol regime ---
            base_conf = target["backtest_wr"] / 100.0
            # Boost confidence if vol is very high (more decay)
            if rvol > 0.50:
                confidence = min(base_conf + 0.05, 0.85)
            else:
                confidence = base_conf

            # TP/SL from calibrated backtest params
            tp = round(price * (1 - target["tp_pct"]), 4)  # SHORT: TP is below entry
            sl = round(price * (1 + target["sl_pct"]), 4)  # SHORT: SL is above entry

            pick = {
                "id": f"etf_decay::{sym}::{today}",
                "symbol": sym,
                "strategy": "leveraged_etf_decay",
                "source_system": "leveraged_etf_decay",
                "signal_type": "SELL",
                "direction": "SHORT",
                "entry_price": round(price, 4),
                "take_profit": tp,
                "stop_loss": sl,
                "sl_pct_from_entry": target["sl_pct"] * 100,
                "tp_pct_from_entry": target["tp_pct"] * 100,
                "confidence": round(confidence, 3),
                "score": round(confidence * 100, 1),
                "leverage_tier": target["leverage"],
                "asset_class": "ETF",
                "category": "etf",
                "status": "OPEN",
                "timestamp": now_utc,
                "entry_date": today,
                "created_at": now_utc,
                "max_hold_days": 5,
                "trust_tier": "DEVELOPING",
                "forward_test_only": True,
                "structural_edge": True,
                "realized_vol_20d": round(rvol, 4),
                "underlying_symbol": und,
                "underlying_20d_return": round(und_ret, 4),
                "strat_fwd_wr": target["backtest_wr"],
                "profit_factor": target["backtest_pf"],
                "avg_pnl_pct": target["backtest_avg_pnl"],
                "backtest_n": target["backtest_n"],
                "reason": (
                    f"{target['name']} - structural decay harvest. "
                    f"{target['leverage']} leveraged products lose value via volatility drag "
                    f"(realized vol={rvol:.0%}). Backtest: {target['backtest_wr']:.1f}% WR, "
                    f"PF {target['backtest_pf']:.2f}, avg +{target['backtest_avg_pnl']:.2f}%/trade "
                    f"on {target['backtest_n']} trades. "
                    f"Underlying {und} 20d return: {und_ret:+.1%} (not in crash)."
                ),
            }
            picks.append(pick)
            if verbose:
                print(f"  >> SHORT {sym} @ ${price:.2f} | vol={rvol:.0%} | "
                      f"conf={confidence:.0%} | {und} 20d={und_ret:+.1%}")

        except Exception as e:
            if verbose:
                print(f"  ERROR {sym}: {e}")
            continue

    # --- Write output ---
    output = {
        "generated_at": now_utc,
        "strategy": "leveraged_etf_decay",
        "description": "SHORT 3x bear ETFs to harvest structural volatility decay",
        "backtest": "LABD 76.9% WR, JDST 69%, SOXS 65.6% (10%SL/20%TP, 2yr)",
        "picks": picks,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, default=str))

    if verbose:
        print(f"  Saved {len(picks)} picks -> {OUTPUT_FILE.name}")
        if not picks:
            print("  (No signals: vol too low or underlying in strong downtrend)")

    return picks


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  ETF DECAY SHORTS — Structural Edge Pick Generator")
    print("=" * 60)
    picks = generate_picks(verbose=True)
    print(f"\nTotal picks: {len(picks)}")
