#!/usr/bin/env python3
"""
Forex Smart Picks — Production Scanner
=======================================
Implements the **winning portfolio variant** from backtesting:
  Portfolio C (Multi-timeframe) — Sharpe 2.06, WR 45.9%, PF 1.30, PnL +20%

Entry condition: Daily SMA(50) + Weekly SMA(20) must agree on trend direction.

Runs 6 academic strategies:
  1. carry_trade_momentum      — Lustig & Verdelhan 2007
  2. forex_rsi2_mean_reversion — Connors RSI-2 (68% WR academic)
  3. forex_mean_reversion_200d — Poterba & Summers
  4. forex_tsmom_12m           — Jegadeesh-Titman cross-sectional momentum
  5. cta_tsmom_blend           — TSMOM 1/3/12 month blend
  6. ig_contrarian_sentiment   — IG RSI-extreme contrarian

TP/SL: 1.2x ATR(14) TP capped at 0.5%, 1.0x ATR(14) SL capped at 0.3%.
Max hold: 2 days (48h). Forex moves 0.3-0.8%/day; edge gone after 2 days.

Output: Appends forex picks to alpha_engine/data/active_picks.json
Standalone: python alpha_engine/forex_smart_picks.py
"""

from __future__ import annotations

import json
import os
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. pip install yfinance")
    sys.exit(1)

# OHLCV provider failover (Tiingo -> Polygon -> AlphaVantage). yfinance is
# hard-blocked from GitHub Actions runner IPs; this fills daily OHLCV gaps so
# a Yahoo outage degrades gracefully instead of silently emptying the scan.
# No-op (transparent) when no provider key is configured. CLAUDE.md API-Failover-Rule.
try:
    from alpha_engine.ohlcv_failover import fetch_ohlcv_failover, failover_available
    _HAS_OHLCV_FAILOVER = True
except ImportError:
    try:
        from ohlcv_failover import fetch_ohlcv_failover, failover_available
        _HAS_OHLCV_FAILOVER = True
    except ImportError:
        _HAS_OHLCV_FAILOVER = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PAIRS = {
    "EURUSD=X": {"name": "EUR/USD", "carry_yield_diff": -0.5},
    "GBPUSD=X": {"name": "GBP/USD", "carry_yield_diff": 0.25},
    "USDJPY=X": {"name": "USD/JPY", "carry_yield_diff": 4.5},
    "AUDUSD=X": {"name": "AUD/USD", "carry_yield_diff": 0.75},
    "USDCAD=X": {"name": "USD/CAD", "carry_yield_diff": 0.5},
    "NZDUSD=X": {"name": "NZD/USD", "carry_yield_diff": 1.0},
    "USDCHF=X": {"name": "USD/CHF", "carry_yield_diff": 3.0},
    "EURJPY=X": {"name": "EUR/JPY", "carry_yield_diff": 4.0},
    "GBPJPY=X": {"name": "GBP/JPY", "carry_yield_diff": 4.75},
    "AUDJPY=X": {"name": "AUD/JPY", "carry_yield_diff": 5.25},
}

TP_MULT = 2.0
SL_MULT = 1.5
TP_CAP_PCT = 0.008  # 0.8% — widened 2026-05-05 (spreads eat 3-6% of tight caps)
SL_CAP_PCT = 0.005  # 0.5% — widened 2026-05-05 for better R:R ratio
MAX_HOLD_DAYS = 2  # 48h max hold — forex moves 0.3-0.8%/day; edge gone after 2 days

DATA_DIR = Path(__file__).parent / "data"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"

# Backtest-proven stats per strategy (from backtest run)
STRATEGY_STATS = {
    "carry_trade_momentum":      {"wr": 0.433, "sharpe": 1.07},
    "forex_rsi2_mean_reversion": {"wr": 0.435, "sharpe": 1.33},
    "forex_mean_reversion_200d": {"wr": 0.396, "sharpe": 0.17},
    "forex_tsmom_12m":           {"wr": 0.340, "sharpe": -1.73},
    "cta_tsmom_blend":           {"wr": 0.310, "sharpe": -2.69},
    "ig_contrarian_sentiment":   {"wr": 0.583, "sharpe": 5.87},
}


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> pd.Series:
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr_vals = calc_atr(high, low, close, period)
    plus_di = 100 * calc_sma(plus_dm, period) / atr_vals.replace(0, np.nan)
    minus_di = 100 * calc_sma(minus_dm, period) / atr_vals.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return calc_sma(dx, period)


# ---------------------------------------------------------------------------
# TP/SL
# ---------------------------------------------------------------------------
def compute_tp_sl(price: float, atr_val: float, direction: str):
    """Return (tp, sl) with ATR-based distances capped."""
    tp_dist = min(TP_MULT * atr_val, price * TP_CAP_PCT)
    sl_dist = min(SL_MULT * atr_val, price * SL_CAP_PCT)
    if direction == "BUY":
        return round(price + tp_dist, 6), round(price - sl_dist, 6)
    else:
        return round(price - tp_dist, 6), round(price + sl_dist, 6)


# ---------------------------------------------------------------------------
# Multi-timeframe filter (Portfolio C — the winner)
# ---------------------------------------------------------------------------
def passes_multi_timeframe_filter(df: pd.DataFrame, direction: str) -> bool:
    """Daily SMA(50) + weekly SMA(20) must agree on trend."""
    close = df["Close"]
    if len(close) < 150:
        return False

    # Daily trend
    sma50 = calc_sma(close, 50)
    if pd.isna(sma50.iloc[-1]):
        return False
    daily_bullish = float(close.iloc[-1]) > float(sma50.iloc[-1])

    # Weekly trend
    weekly = close.resample("W-FRI").last().dropna()
    if len(weekly) < 25:
        return False
    weekly_sma20 = calc_sma(weekly, 20)
    if pd.isna(weekly_sma20.iloc[-1]):
        return False
    weekly_bullish = float(weekly.iloc[-1]) > float(weekly_sma20.iloc[-1])

    if direction == "BUY":
        return daily_bullish and weekly_bullish
    else:
        return (not daily_bullish) and (not weekly_bullish)


# ---------------------------------------------------------------------------
# Strategy signal generators — each returns (direction, confidence, reason) or None
# ---------------------------------------------------------------------------
def check_carry_trade(df: pd.DataFrame, symbol: str) -> tuple[str, float, str] | None:
    """Carry trade momentum."""
    carry = PAIRS[symbol]["carry_yield_diff"]
    close = df["Close"]
    if len(close) < 60:
        return None
    mom_20d = float(close.iloc[-1] / close.iloc[-20] - 1)
    score = carry + mom_20d * 10

    direction = "BUY" if score > 0.5 else ("SELL" if score < -0.5 else None)
    if direction is None:
        return None

    # Lustig 2011 carry-momentum: direction must match carry sign.
    # Long the high-yielder (carry > 0); short the low-yielder (carry < 0).
    # Previously the combined `score = carry + mom_20d*10` could emit BUY on a
    # negative-carry pair when momentum was strong — a wrong-direction carry
    # trade that diverges from `forex_strategies.py::carry_trade` which already
    # rejects carry<=0 entirely. Defense-in-depth for the strategy layer.
    if direction == "BUY" and carry <= 0:
        return None
    if direction == "SELL" and carry >= 0:
        return None

    # Trend filter
    sma50 = float(calc_sma(close, 50).iloc[-1])
    if direction == "BUY" and float(close.iloc[-1]) < sma50:
        return None
    if direction == "SELL" and float(close.iloc[-1]) > sma50:
        return None

    # RSI filter
    r = float(calc_rsi(close, 14).iloc[-1])
    if direction == "BUY" and r > 65:
        return None
    if direction == "SELL" and r < 35:
        return None

    # Vol filter
    returns = close.pct_change()
    vol_20d = float(returns.iloc[-20:].std() * (252 ** 0.5))
    vol_60d = float(returns.iloc[-60:].std() * (252 ** 0.5)) if len(close) >= 60 else vol_20d
    if vol_60d > 0 and vol_20d / vol_60d > 1.5:
        return None

    conf = min(0.72, 0.55 + abs(score) * 0.03)
    reason = f"Carry={carry:+.1f}, mom20d={mom_20d*100:.2f}%, RSI={r:.0f}"
    return direction, conf, reason


def check_rsi2_mean_reversion(df: pd.DataFrame, symbol: str) -> tuple[str, float, str] | None:
    """Connors RSI-2 mean reversion."""
    close = df["Close"]
    if len(close) < 200:
        return None
    rsi2 = calc_rsi(close, 2)
    r2 = float(rsi2.iloc[-1])
    sma200 = float(calc_sma(close, 200).iloc[-1])
    price = float(close.iloc[-1])

    if r2 < 10 and price > sma200:
        conf = min(0.72, 0.60 + (10 - r2) * 0.01)
        return "BUY", conf, f"RSI(2)={r2:.1f} oversold, above 200d SMA"
    elif r2 > 90 and price < sma200:
        conf = min(0.72, 0.60 + (r2 - 90) * 0.01)
        return "SELL", conf, f"RSI(2)={r2:.1f} overbought, below 200d SMA"
    return None


def check_mean_reversion_200d(df: pd.DataFrame, symbol: str) -> tuple[str, float, str] | None:
    """Mean reversion to 200-day SMA."""
    close = df["Close"]
    if len(close) < 200:
        return None
    sma200 = float(calc_sma(close, 200).iloc[-1])
    price = float(close.iloc[-1])
    deviation = (price - sma200) / sma200

    if deviation < -0.02:
        conf = min(0.70, 0.55 + abs(deviation) * 2)
        return "BUY", conf, f"Price {deviation*100:.1f}% below 200d SMA"
    elif deviation > 0.02:
        conf = min(0.70, 0.55 + abs(deviation) * 2)
        return "SELL", conf, f"Price {deviation*100:+.1f}% above 200d SMA"
    return None


# DEPRECATED 2026-05-05: Removed from ALL_STRATEGIES — Sharpe -1.73.
# FX pairs mean-revert due to central bank policy; trend-following fails.
# Kept for historical reference only.
def check_tsmom_12m(df: pd.DataFrame, symbol: str) -> tuple[str, float, str] | None:
    """12-month time-series momentum. DEPRECATED."""
    close = df["Close"]
    if len(close) < 252:
        return None
    ret_12m = float(close.iloc[-1] / close.iloc[-252] - 1)

    if ret_12m > 0.01:
        conf = min(0.65, 0.50 + abs(ret_12m))
        return "BUY", conf, f"12m momentum = {ret_12m*100:+.1f}%"
    elif ret_12m < -0.01:
        conf = min(0.65, 0.50 + abs(ret_12m))
        return "SELL", conf, f"12m momentum = {ret_12m*100:+.1f}%"
    return None


# DEPRECATED 2026-05-05: Removed from ALL_STRATEGIES — Sharpe -2.69.
# CTA trend-following fails on FX (mean-reverting due to central banks).
# Kept for historical reference only.
def check_cta_tsmom_blend(df: pd.DataFrame, symbol: str) -> tuple[str, float, str] | None:
    """CTA-style TSMOM 1/3/12 month blend. DEPRECATED."""
    close = df["Close"]
    if len(close) < 252:
        return None
    ret_1m = float(close.iloc[-1] / close.iloc[-21] - 1)
    ret_3m = float(close.iloc[-1] / close.iloc[-63] - 1)
    ret_12m = float(close.iloc[-1] / close.iloc[-252] - 1)

    vote = (1 if ret_1m > 0 else -1) + (1 if ret_3m > 0 else -1) + (1 if ret_12m > 0 else -1)
    if vote >= 2:
        conf = min(0.65, 0.50 + 0.05 * vote)
        return "BUY", conf, f"TSMOM vote={vote} (1m={ret_1m*100:+.1f}%, 3m={ret_3m*100:+.1f}%, 12m={ret_12m*100:+.1f}%)"
    elif vote <= -2:
        conf = min(0.65, 0.50 + 0.05 * abs(vote))
        return "SELL", conf, f"TSMOM vote={vote} (1m={ret_1m*100:+.1f}%, 3m={ret_3m*100:+.1f}%, 12m={ret_12m*100:+.1f}%)"
    return None


def check_ig_contrarian(df: pd.DataFrame, symbol: str) -> tuple[str, float, str] | None:
    """IG contrarian sentiment (RSI extreme as proxy)."""
    close = df["Close"]
    if len(close) < 55:
        return None
    rsi14 = calc_rsi(close, 14)
    r = float(rsi14.iloc[-1])
    sma50 = calc_sma(close, 50)
    sma_slope = (float(sma50.iloc[-1]) - float(sma50.iloc[-5])) / float(sma50.iloc[-5])

    if r < 25 and sma_slope > 0:
        conf = min(0.75, 0.65 + (25 - r) * 0.005)
        return "BUY", conf, f"Contrarian BUY: RSI={r:.0f}, SMA slope={sma_slope*100:.2f}%"
    elif r > 75 and sma_slope < 0:
        conf = min(0.75, 0.65 + (r - 75) * 0.005)
        return "SELL", conf, f"Contrarian SELL: RSI={r:.0f}, SMA slope={sma_slope*100:.2f}%"
    return None


ALL_STRATEGIES = {
    "carry_trade_momentum": check_carry_trade,
    "forex_rsi2_mean_reversion": check_rsi2_mean_reversion,
    "forex_mean_reversion_200d": check_mean_reversion_200d,
    # forex_tsmom_12m REMOVED 2026-05-05 — Sharpe -1.73 (FX reverts to mean)
    # cta_tsmom_blend REMOVED 2026-05-05 — Sharpe -2.69 (trend-following fails on FX)
    "ig_contrarian_sentiment": check_ig_contrarian,
}


# ---------------------------------------------------------------------------
# Data download with fallback
# ---------------------------------------------------------------------------
def download_forex_data() -> dict[str, pd.DataFrame]:
    """Download ~1 year of daily forex data via yfinance."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=400)
    data = {}
    symbols = list(PAIRS.keys())

    print(f"Downloading forex data ({len(symbols)} pairs)...")
    for symbol in symbols:
        df = None
        try:
            df = yf.download(symbol, start=start.strftime("%Y-%m-%d"),
                             end=end.strftime("%Y-%m-%d"),
                             progress=False, auto_adjust=True)
            if df is not None and len(df) > 50:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            else:
                df = None
        except Exception as e:
            print(f"  {symbol}: yfinance ERROR - {e}")
            df = None

        # Provider failover: yfinance returned nothing for this pair (Yahoo
        # outage / CI IP block). Try Tiingo -> Polygon -> AlphaVantage on the
        # plain pair code (strip Yahoo's `=X` suffix). Fail-open: any failure
        # leaves `df` as None and the pair is simply skipped, exactly as
        # before. (CLAUDE.md API-Failover-Rule)
        if df is None and _HAS_OHLCV_FAILOVER:
            try:
                if failover_available():
                    plain = symbol.replace("=X", "")
                    fo_df, provider = fetch_ohlcv_failover(plain)
                    if fo_df is not None and len(fo_df) > 50:
                        if isinstance(fo_df.columns, pd.MultiIndex):
                            fo_df.columns = fo_df.columns.get_level_values(0)
                        df = fo_df
                        print(f"  {symbol}: recovered {len(df)} bars via {provider}")
            except Exception as e:  # noqa: BLE001
                print(f"  {symbol}: failover error - {e}")

        if df is not None and len(df) > 50:
            data[symbol] = df
            print(f"  {symbol}: {len(df)} bars OK")
        else:
            print(f"  {symbol}: insufficient data")
    return data


# ---------------------------------------------------------------------------
# Pick generator
# ---------------------------------------------------------------------------
def generate_smart_picks(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Generate forex smart picks using Portfolio C (multi-timeframe) filter."""
    # Defensive import of pre-emission policy gates. Fail-open if broken.
    try:
        from alpha_engine.non_crypto_policy import passes_non_crypto_policy
        _policy_available = True
    except Exception:
        _policy_available = False

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    picks = []

    for symbol, df in data.items():
        if len(df) < 200:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        atr_series = calc_atr(high, low, close, 14)
        current_atr = float(atr_series.iloc[-1])
        current_price = float(close.iloc[-1])

        if pd.isna(current_atr) or current_atr <= 0:
            continue

        for strat_name, strat_fn in ALL_STRATEGIES.items():
            result = strat_fn(df, symbol)
            if result is None:
                continue

            direction, confidence, reason = result

            # Portfolio C filter: multi-timeframe confirmation
            if not passes_multi_timeframe_filter(df, direction):
                continue

            # Compute TP/SL
            tp, sl = compute_tp_sl(current_price, current_atr, direction)

            # Risk/reward
            tp_dist = abs(tp - current_price)
            sl_dist = abs(sl - current_price)
            rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.2

            # Backtest-adjusted confidence: skip strategies with negative Sharpe entirely.
            # A 20% confidence penalty is insufficient to neutralize a Sharpe of -2.69 or -1.73.
            # These strategies destroy capital — they generate no actionable picks.
            bt_stats = STRATEGY_STATS.get(strat_name, {"sharpe": 0})
            if bt_stats["sharpe"] < 0:
                print(f"  SKIP: {strat_name} has negative Sharpe={bt_stats['sharpe']:.2f} — not generating picks")
                continue

            # Generate unique ID
            id_str = f"fx_smart_{symbol}_{strat_name}_{int(datetime.now(timezone.utc).timestamp())}"
            pick_id = hashlib.md5(id_str.encode()).hexdigest()[:12]

            pick = {
                "id": f"fx_smart_{pick_id}",
                "symbol": symbol,
                "strategy": f"fx_smart_{strat_name}",
                "signal_type": direction,
                "direction": "LONG" if direction == "BUY" else "SHORT",
                "entry_price": round(current_price, 6),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 4),
                "risk_reward": rr,
                "category": "forex",
                "asset_class": "FOREX",
                "source_system": "alpha_engine",
                "status": "ACTIVE",
                "created_at": now_iso,
                "forward_validated": False,
                # Top-level ATR + hold fields so the ATR-reachability gate can
                # read them directly without diving into `extra`.
                "atr_14": round(current_atr, 6),
                "max_hold_days": MAX_HOLD_DAYS,
                "extra": {
                    "portfolio_variant": "C_Multi_timeframe",
                    "backtest_sharpe": bt_stats["sharpe"],
                    "backtest_wr": bt_stats.get("wr", 0),
                    "atr_14": round(current_atr, 6),
                    "tp_pct": round(tp_dist / current_price * 100, 4),
                    "sl_pct": round(sl_dist / current_price * 100, 4),
                    "max_hold_days": MAX_HOLD_DAYS,
                    "reason": reason,
                    "multi_tf_confirmed": True,
                },
            }

            # Pre-emission policy gates (FX session / ATR reachability).
            if _policy_available:
                try:
                    ok, policy_reason = passes_non_crypto_policy(pick)
                    if not ok:
                        print(f"  POLICY BLOCK: {symbol} via {strat_name}: {policy_reason}")
                        continue
                except Exception:
                    # Fail-open on unexpected gate errors.
                    pass

            picks.append(pick)
            print(f"  PICK: {symbol} {direction} via {strat_name} "
                  f"(conf={confidence:.2f}, TP={tp_dist/current_price*100:.3f}%, "
                  f"SL={sl_dist/current_price*100:.3f}%)")

    return picks


# ---------------------------------------------------------------------------
# Active picks file management
# ---------------------------------------------------------------------------
def load_active_picks() -> list[dict]:
    """Load existing active picks."""
    if ACTIVE_PICKS_FILE.exists():
        try:
            with open(ACTIVE_PICKS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_active_picks(picks: list[dict]):
    """Save picks to active_picks.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_PICKS_FILE, "w") as f:
        json.dump(picks, f, indent=2, default=str)


def merge_picks(existing: list[dict], new_picks: list[dict]) -> list[dict]:
    """Merge new forex smart picks into existing picks.

    - Remove old fx_smart picks that are stale (>MAX_HOLD_DAYS old)
    - Don't duplicate: skip if same symbol+strategy already active
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_HOLD_DAYS + 1)

    # Partition existing picks
    non_fx_smart = []
    fx_smart_active = []
    for p in existing:
        strat = p.get("strategy", "")
        if strat.startswith("fx_smart_"):
            created = p.get("created_at", "")
            try:
                ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if ct > cutoff and p.get("status") == "ACTIVE":
                    fx_smart_active.append(p)
                # else: expired, drop it
            except (ValueError, TypeError):
                fx_smart_active.append(p)  # keep if can't parse
        else:
            non_fx_smart.append(p)

    # Build set of active symbol+strategy
    active_keys = {(p["symbol"], p["strategy"]) for p in fx_smart_active}

    # Add only non-duplicate new picks
    added = 0
    for p in new_picks:
        key = (p["symbol"], p["strategy"])
        if key not in active_keys:
            fx_smart_active.append(p)
            active_keys.add(key)
            added += 1

    print(f"  Merged: {added} new picks added, {len(fx_smart_active)} total fx_smart active")
    return non_fx_smart + fx_smart_active


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("FOREX SMART PICKS — Portfolio C (Multi-timeframe)")
    print(f"Backtest: Sharpe 2.06 | WR 45.9% | PF 1.30 | PnL +20%")
    print("=" * 60)

    # Check if it's a weekday
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Saturday or Sunday
        print("Weekend — forex markets closed. Skipping.")
        return

    # Session filter: generate picks 07-16 UTC (Asian close + London + NY overlap)
    # 2026-05-05 fix: widened from 13-16 to 07-16 UTC.
    # Asian close 07:00 + London open 08:00 provide optimal entry signals.
    # NY overlap (13-16) still within window for peak liquidity.
    if not (7 <= now.hour < 16):
        print(f"Outside active forex window (current: {now.hour}:00 UTC, required: 07-16 UTC). Skipping.")
        print("Forex signals generated during Asian close through NY overlap (07-16 UTC).")
        return

    data = download_forex_data()
    if len(data) < 5:
        print("ERROR: Not enough data. Exiting.")
        sys.exit(1)

    print(f"\nScanning {len(data)} pairs with 6 strategies + Portfolio C filter...")
    new_picks = generate_smart_picks(data)

    if not new_picks:
        print("\nNo picks passed all filters. Market conditions may not be favorable.")
        print("This is expected — Portfolio C is selective (Sharpe 2.06 comes from quality).")
    else:
        print(f"\n{len(new_picks)} smart picks generated.")

    # Merge with existing picks
    existing = load_active_picks()
    merged = merge_picks(existing, new_picks)
    save_active_picks(merged)
    print(f"Saved to {ACTIVE_PICKS_FILE}")

    # Summary
    fx_count = sum(1 for p in merged if p.get("strategy", "").startswith("fx_smart_"))
    print(f"\nTotal active fx_smart picks: {fx_count}")
    print("Done.")


if __name__ == "__main__":
    main()
