#!/usr/bin/env python3
"""
Forex Asset-Class Pattern Analyzer
====================================
Loads all forex picks (active + historical), fetches 2-year daily OHLCV from
yfinance for 10 forex pairs, computes forex-specific features, diagnoses WHY
the old 0%-close-rate forex picks failed, generates 5 improved strategy
variations, backtests each on 2y data, and identifies which pairs work best
for which strategy.

Outputs:
  data/forex_asset_analysis.json       -- full feature matrix + failure diagnosis
  data/forex_strategy_variations.json  -- 5 improved variations + backtest results
  data/forex_ml_picks.json             -- actionable ML-scored picks

CRITICAL: Forex TP < 1.5% and SL < 1.0%.  The old system failed because it
used crypto-scale targets (3-5% TP) on instruments that move 0.3-0.8%/day.

source_system = "ml_forex_reverser"
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8",
                      closefd=False, errors="replace")
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8",
                      closefd=False, errors="replace")

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    np = pd = yf = None
    print("[WARN] yfinance/pandas/numpy not installed. pip install yfinance pandas numpy")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

AUDIT_FOREX = BASE_DIR.parent / "audit_dashboard" / "data" / "forex_futures_picks.json"
MULTI_ASSET = DATA_DIR / "multi_asset_picks.json"

# ---------------------------------------------------------------------------
# Forex pair config  (mirrors alpha_engine/config.py FOREX_SYMBOLS)
# ---------------------------------------------------------------------------
FOREX_PAIRS: dict[str, dict[str, Any]] = {
    "EURUSD=X": {"name": "EUR/USD", "base": "EUR", "quote": "USD",
                 "carry_yield_diff": -0.5, "session": "london"},
    "GBPUSD=X": {"name": "GBP/USD", "base": "GBP", "quote": "USD",
                 "carry_yield_diff": 0.25, "session": "london"},
    "USDJPY=X": {"name": "USD/JPY", "base": "USD", "quote": "JPY",
                 "carry_yield_diff": 4.5, "session": "asian"},
    "AUDUSD=X": {"name": "AUD/USD", "base": "AUD", "quote": "USD",
                 "carry_yield_diff": 0.75, "session": "asian"},
    "USDCAD=X": {"name": "USD/CAD", "base": "USD", "quote": "CAD",
                 "carry_yield_diff": 0.5, "session": "newyork"},
    "NZDUSD=X": {"name": "NZD/USD", "base": "NZD", "quote": "USD",
                 "carry_yield_diff": 1.0, "session": "asian"},
    "USDCHF=X": {"name": "USD/CHF", "base": "USD", "quote": "CHF",
                 "carry_yield_diff": 3.0, "session": "london"},
    "EURJPY=X": {"name": "EUR/JPY", "base": "EUR", "quote": "JPY",
                 "carry_yield_diff": 4.0, "session": "london"},
    "GBPJPY=X": {"name": "GBP/JPY", "base": "GBP", "quote": "JPY",
                 "carry_yield_diff": 4.75, "session": "london"},
    "AUDJPY=X": {"name": "AUD/JPY", "base": "AUD", "quote": "JPY",
                 "carry_yield_diff": 5.25, "session": "asian"},
}

# JPY crosses (risk-on/risk-off indicator)
JPY_CROSSES = {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"}

# Carry pairs (positive yield diff > 2%)
CARRY_PAIRS = {sym for sym, cfg in FOREX_PAIRS.items()
               if cfg["carry_yield_diff"] >= 2.0}

# DXY proxy ticker
DXY_TICKER = "DX-Y.NYB"

# Session hours (UTC)
SESSIONS = {
    "london":  (7, 12),   # London open 07-12 UTC
    "newyork": (13, 20),  # NY open 13-20 UTC
    "asian":   (23, 7),   # Tokyo/Sydney 23-07 UTC (wraps midnight)
    "overlap": (13, 16),  # London/NY overlap -- highest liquidity
}


# ---------------------------------------------------------------------------
# Indicator helpers  (self-contained, no external dependency beyond numpy/pandas)
# ---------------------------------------------------------------------------

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, min_periods=period, adjust=False).mean()


def _bollinger(close: pd.Series, period: int = 20,
               num_std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower) Bollinger Bands."""
    mid = _sma(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def _zscore_from_sma(close: pd.Series, period: int = 200) -> pd.Series:
    """Z-score of price distance from SMA."""
    ma = _sma(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    return (close - ma) / std.replace(0, np.nan)


def _bb_position(close: pd.Series, period: int = 20,
                 num_std: float = 2.0) -> pd.Series:
    """Bollinger Band position: 0 = lower band, 1 = upper band."""
    upper, mid, lower = _bollinger(close, period, num_std)
    width = upper - lower
    return (close - lower) / width.replace(0, np.nan)


# ---------------------------------------------------------------------------
# Data fetching (yfinance with rate limiting)
# ---------------------------------------------------------------------------

def _fetch_forex_data(symbols: list[str], period: str = "2y",
                      interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Fetch daily OHLCV for forex pairs from yfinance with rate limiting."""
    if not HAS_DEPS:
        return {}

    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period=period, interval=interval, auto_adjust=True)
            if df is not None and len(df) >= 50:
                # Clean: drop rows with NaN close
                df = df.dropna(subset=["Close"])
                data[sym] = df
                print(f"  [OK] {sym}: {len(df)} bars")
            else:
                print(f"  [SKIP] {sym}: insufficient data ({len(df) if df is not None else 0} bars)")
            time.sleep(0.5)  # rate limit
        except Exception as exc:
            print(f"  [ERR] {sym}: {exc}")
            time.sleep(1.0)
    return data


def _fetch_dxy(period: str = "2y") -> Optional[pd.DataFrame]:
    """Fetch DXY (US Dollar Index) for correlation analysis."""
    if not HAS_DEPS:
        return None
    try:
        ticker = yf.Ticker(DXY_TICKER)
        df = ticker.history(period=period, interval="1d", auto_adjust=True)
        if df is not None and len(df) >= 50:
            print(f"  [OK] DXY: {len(df)} bars")
            return df.dropna(subset=["Close"])
        print(f"  [SKIP] DXY: insufficient data")
    except Exception as exc:
        print(f"  [WARN] DXY not available: {exc}")
    return None


# ---------------------------------------------------------------------------
# Load existing forex picks
# ---------------------------------------------------------------------------

def _load_all_forex_picks() -> list[dict]:
    """Load forex picks from all sources."""
    picks: list[dict] = []

    # 1) audit_dashboard/data/forex_futures_picks.json
    if AUDIT_FOREX.exists():
        try:
            with open(AUDIT_FOREX, "r", encoding="utf-8") as f:
                raw = json.load(f)
            audit_picks = raw.get("picks", []) if isinstance(raw, dict) else raw
            forex_audit = [p for p in audit_picks
                           if p.get("category", "").lower() == "forex"]
            picks.extend(forex_audit)
            print(f"  Loaded {len(forex_audit)} forex picks from audit_dashboard")
        except Exception as exc:
            print(f"  [WARN] Could not load audit forex: {exc}")

    # 2) copy_trader_intel/data/multi_asset_picks.json
    if MULTI_ASSET.exists():
        try:
            with open(MULTI_ASSET, "r", encoding="utf-8") as f:
                raw = json.load(f)
            ma_picks = raw.get("picks", []) if isinstance(raw, dict) else raw
            forex_ma = [p for p in ma_picks
                        if p.get("category", "").lower() == "forex"
                        or p.get("asset_class", "").upper() == "FOREX"]
            picks.extend(forex_ma)
            print(f"  Loaded {len(forex_ma)} forex picks from multi_asset")
        except Exception as exc:
            print(f"  [WARN] Could not load multi_asset: {exc}")

    # 3) copy_trader_intel/data/forex_copytrader_picks.json
    forex_ct = DATA_DIR / "forex_copytrader_picks.json"
    if forex_ct.exists():
        try:
            with open(forex_ct, "r", encoding="utf-8") as f:
                raw = json.load(f)
            ct_picks = raw.get("picks", raw) if isinstance(raw, dict) else raw
            if isinstance(ct_picks, list):
                picks.extend(ct_picks)
                print(f"  Loaded {len(ct_picks)} forex picks from copytrader")
        except Exception as exc:
            print(f"  [WARN] Could not load forex_copytrader_picks: {exc}")

    # Deduplicate by id
    seen_ids: set[str] = set()
    unique: list[dict] = []
    for p in picks:
        pid = p.get("id", "")
        if pid and pid in seen_ids:
            continue
        seen_ids.add(pid)
        unique.append(p)

    print(f"  Total unique forex picks: {len(unique)}")
    return unique


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------

def compute_features(data: dict[str, pd.DataFrame],
                     dxy_df: Optional[pd.DataFrame] = None) -> dict[str, dict]:
    """Compute forex-specific features for each pair.

    Returns dict[symbol -> feature_dict].
    """
    features: dict[str, dict] = {}

    # Prepare DXY returns for correlation
    dxy_ret = None
    if dxy_df is not None and len(dxy_df) > 20:
        dxy_ret = dxy_df["Close"].pct_change().dropna()

    # JPY index (average of JPY crosses) for risk-on/risk-off
    jpy_returns: dict[str, pd.Series] = {}
    for sym in JPY_CROSSES:
        if sym in data:
            jpy_returns[sym] = data[sym]["Close"].pct_change().dropna()

    for sym, df in data.items():
        if len(df) < 200:
            continue

        cfg = FOREX_PAIRS.get(sym, {})
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # Core indicators
        rsi2 = _rsi(close, 2)
        rsi14 = _rsi(close, 14)
        sma200 = _sma(close, 200)
        zscore_200 = _zscore_from_sma(close, 200)
        atr14 = _atr(high, low, close, 14)
        bb_pos = _bb_position(close, 20, 2.0)

        # ATR as % of price (forex typical: 0.3-0.8%)
        atr_pct = float(atr14.iloc[-1]) / current * 100 if current > 0 else 0

        # Weekly momentum
        ret_5d = (current / float(close.iloc[-5]) - 1) * 100 if len(close) >= 5 else 0
        ret_20d = (current / float(close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0

        # Volatility (annualized)
        daily_ret = close.pct_change().dropna()
        vol_20d = float(daily_ret.iloc[-20:].std() * np.sqrt(252)) if len(daily_ret) >= 20 else 0
        vol_60d = float(daily_ret.iloc[-60:].std() * np.sqrt(252)) if len(daily_ret) >= 60 else 0
        vol_ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0

        # DXY correlation (60-day rolling)
        dxy_corr = None
        if dxy_ret is not None and len(daily_ret) >= 60:
            try:
                aligned = pd.concat([daily_ret, dxy_ret], axis=1, join="inner")
                if len(aligned) >= 60:
                    dxy_corr = float(aligned.iloc[-60:].corr().iloc[0, 1])
            except Exception:
                pass

        # JPY cross correlation (risk-on/risk-off)
        jpy_corr = None
        if sym not in JPY_CROSSES and jpy_returns:
            # Correlate with average JPY cross return
            try:
                jpy_avg = pd.concat(list(jpy_returns.values()), axis=1).mean(axis=1)
                aligned = pd.concat([daily_ret, jpy_avg], axis=1, join="inner")
                if len(aligned) >= 60:
                    jpy_corr = float(aligned.iloc[-60:].corr().iloc[0, 1])
            except Exception:
                pass

        # Session analysis: what % of recent moves happened in each session
        session_stats = {}
        if hasattr(df.index, "hour"):
            for sname, (start_h, end_h) in SESSIONS.items():
                if start_h < end_h:
                    mask = (df.index.hour >= start_h) & (df.index.hour < end_h)
                else:
                    mask = (df.index.hour >= start_h) | (df.index.hour < end_h)
                session_bars = mask.sum()
                session_stats[sname] = {
                    "bar_count": int(session_bars),
                    "pct_of_total": round(session_bars / len(df) * 100, 1)
                    if len(df) > 0 else 0,
                }
        # For daily data, session analysis is limited; note this in output
        if not session_stats:
            session_stats = {"note": "daily_data_no_intraday_sessions"}

        features[sym] = {
            "symbol": sym,
            "name": cfg.get("name", sym),
            "current_price": round(current, 5),
            "carry_yield_diff": cfg.get("carry_yield_diff", 0),
            "primary_session": cfg.get("session", "unknown"),
            "rsi2": round(float(rsi2.iloc[-1]), 1) if not np.isnan(rsi2.iloc[-1]) else None,
            "rsi14": round(float(rsi14.iloc[-1]), 1) if not np.isnan(rsi14.iloc[-1]) else None,
            "sma200": round(float(sma200.iloc[-1]), 5) if not np.isnan(sma200.iloc[-1]) else None,
            "zscore_200d": round(float(zscore_200.iloc[-1]), 3) if not np.isnan(zscore_200.iloc[-1]) else None,
            "atr14": round(float(atr14.iloc[-1]), 5),
            "atr_pct": round(atr_pct, 3),
            "bb_position": round(float(bb_pos.iloc[-1]), 3) if not np.isnan(bb_pos.iloc[-1]) else None,
            "return_5d_pct": round(ret_5d, 3),
            "return_20d_pct": round(ret_20d, 3),
            "vol_20d_ann": round(vol_20d, 4),
            "vol_60d_ann": round(vol_60d, 4),
            "vol_ratio": round(vol_ratio, 3),
            "dxy_correlation_60d": round(dxy_corr, 3) if dxy_corr is not None else None,
            "jpy_cross_correlation_60d": round(jpy_corr, 3) if jpy_corr is not None else None,
            "session_analysis": session_stats,
            "data_bars": len(df),
        }

    return features


# ---------------------------------------------------------------------------
# Failure diagnosis: WHY did old forex picks have 0% close rate?
# ---------------------------------------------------------------------------

def diagnose_failures(picks: list[dict],
                      features: dict[str, dict]) -> dict[str, Any]:
    """Analyze historical forex picks to determine failure causes."""
    if not picks:
        return {"error": "no_picks_to_analyze", "diagnoses": []}

    diagnoses: list[dict] = []
    tp_pcts: list[float] = []
    sl_pcts: list[float] = []
    symbols_used: dict[str, int] = {}
    strategies_used: dict[str, int] = {}
    directions: dict[str, int] = {"LONG": 0, "SHORT": 0}
    closed_count = 0
    open_count = 0

    for p in picks:
        entry = p.get("entry_price", 0) or 0
        tp = p.get("take_profit", 0) or p.get("target_price", 0) or 0
        sl = p.get("stop_loss", 0) or p.get("stop_price", 0) or 0
        sym = p.get("symbol", "")
        strat = p.get("strategy", "unknown")
        direction = p.get("direction", "LONG")
        status = p.get("status", "OPEN")

        if status in ("CLOSED", "TP_HIT", "SL_HIT"):
            closed_count += 1
        else:
            open_count += 1

        symbols_used[sym] = symbols_used.get(sym, 0) + 1
        strategies_used[strat] = strategies_used.get(strat, 0) + 1
        directions[direction] = directions.get(direction, 0) + 1

        if entry > 0:
            if tp > 0:
                tp_pct = abs(tp - entry) / entry * 100
                tp_pcts.append(tp_pct)
            if sl > 0:
                sl_pct = abs(sl - entry) / entry * 100
                sl_pcts.append(sl_pct)

    # Diagnosis 1: TP too wide?
    avg_tp_pct = sum(tp_pcts) / len(tp_pcts) if tp_pcts else 0
    avg_sl_pct = sum(sl_pcts) / len(sl_pcts) if sl_pcts else 0
    max_tp_pct = max(tp_pcts) if tp_pcts else 0

    tp_diagnosis = "LIKELY_OK" if avg_tp_pct < 1.5 else "TOO_WIDE"
    if avg_tp_pct >= 2.0:
        tp_diagnosis = "CRYPTO_SCALE_FAILURE"
        diagnoses.append({
            "issue": "TP targets use crypto-scale (avg {:.2f}%)".format(avg_tp_pct),
            "severity": "CRITICAL",
            "fix": "Forex pairs move 0.3-0.8%/day. TP must be < 1.5%, ideally 0.3-0.8%",
        })
    elif avg_tp_pct >= 1.0:
        diagnoses.append({
            "issue": "TP targets borderline wide (avg {:.2f}%)".format(avg_tp_pct),
            "severity": "WARNING",
            "fix": "Consider tighter TP (0.3-0.8%) for intraday, up to 1.2% for swing",
        })

    # Diagnosis 2: Hold times too short for mean-reversion?
    diagnoses.append({
        "issue": "Mean-reversion requires 5-20 day hold for forex (200d SMA pull)",
        "severity": "INFO",
        "fix": "Ensure hold_max >= 10 days for mean-reversion strategies",
    })

    # Diagnosis 3: Session timing
    # Check if picks were generated without session awareness
    session_aware = any("session" in str(p.get("reason", "")).lower()
                        or "london" in str(p.get("reason", "")).lower()
                        or "overlap" in str(p.get("reason", "")).lower()
                        for p in picks)
    if not session_aware:
        diagnoses.append({
            "issue": "No session timing awareness in picks",
            "severity": "MODERATE",
            "fix": "Forex liquidity/volatility peaks at London/NY overlap (13-16 UTC). "
                   "Filter entries to active sessions for the pair's primary market.",
        })

    # Diagnosis 4: Wrong pair selection for strategy type
    # Carry trade on negative-carry pairs?
    carry_picks = [p for p in picks if "carry" in p.get("strategy", "").lower()]
    bad_carry = [p for p in carry_picks
                 if FOREX_PAIRS.get(p.get("symbol", ""), {}).get("carry_yield_diff", 0) < 1.0]
    if bad_carry:
        diagnoses.append({
            "issue": f"{len(bad_carry)} carry trades on low/negative-yield pairs",
            "severity": "MODERATE",
            "fix": "Only apply carry strategy to pairs with yield_diff > 2%: "
                   f"{', '.join(sorted(CARRY_PAIRS))}",
        })

    # Diagnosis 5: 0% close rate itself
    close_rate = closed_count / max(1, closed_count + open_count) * 100
    diagnoses.append({
        "issue": f"Close rate: {close_rate:.1f}% ({closed_count}/{closed_count + open_count})",
        "severity": "CRITICAL" if close_rate < 10 else "WARNING",
        "fix": "Tighter TP/SL + max hold time expiry ensures picks close. "
               "Add trailing stop at 50% of TP distance.",
    })

    return {
        "total_picks_analyzed": len(picks),
        "closed": closed_count,
        "open": open_count,
        "close_rate_pct": round(close_rate, 1),
        "avg_tp_pct": round(avg_tp_pct, 3),
        "avg_sl_pct": round(avg_sl_pct, 3),
        "max_tp_pct": round(max_tp_pct, 3),
        "tp_diagnosis": tp_diagnosis,
        "symbols_distribution": symbols_used,
        "strategies_distribution": strategies_used,
        "direction_distribution": directions,
        "diagnoses": diagnoses,
    }


# ---------------------------------------------------------------------------
# Strategy variations  (5 forex-specific improved strategies)
# ---------------------------------------------------------------------------

def _backtest_strategy(data: dict[str, pd.DataFrame],
                       strategy_fn,
                       strategy_name: str,
                       max_hold_bars: int = 20) -> dict[str, Any]:
    """Walk-forward backtest a strategy on 2y forex data.

    Uses 70% train / 30% test split.  Returns stats.
    """
    all_trades: list[dict] = []

    for sym, df in data.items():
        if len(df) < 252:  # Need at least 1y
            continue

        close = df["Close"].values
        high = df["High"].values
        low = df["Low"].values
        n = len(close)

        # 70/30 split -- backtest on the last 30%
        test_start = int(n * 0.7)

        for i in range(test_start, n - 1):
            # Build a slice up to bar i for signal generation
            close_slice = pd.Series(close[:i + 1])
            high_slice = pd.Series(high[:i + 1])
            low_slice = pd.Series(low[:i + 1])

            signal = strategy_fn(
                sym=sym,
                close=close_slice,
                high=high_slice,
                low=low_slice,
                cfg=FOREX_PAIRS.get(sym, {}),
            )

            if signal is None:
                continue

            direction = signal["direction"]
            entry_price = close[i]
            tp = signal["tp"]
            sl = signal["sl"]

            # Simulate forward
            exit_price = entry_price
            exit_reason = "TIME_EXPIRY"
            hold_bars = 0

            for j in range(i + 1, min(i + 1 + max_hold_bars, n)):
                hold_bars += 1
                bar_high = high[j]
                bar_low = low[j]
                bar_close = close[j]

                if direction == "LONG":
                    if bar_high >= tp:
                        exit_price = tp
                        exit_reason = "TP_HIT"
                        break
                    if bar_low <= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                        break
                else:  # SHORT
                    if bar_low <= tp:
                        exit_price = tp
                        exit_reason = "TP_HIT"
                        break
                    if bar_high >= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                        break

                exit_price = bar_close  # mark to market

            if direction == "LONG":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100

            all_trades.append({
                "symbol": sym,
                "direction": direction,
                "entry_price": round(float(entry_price), 5),
                "tp": round(float(tp), 5),
                "sl": round(float(sl), 5),
                "exit_price": round(float(exit_price), 5),
                "exit_reason": exit_reason,
                "pnl_pct": round(pnl_pct, 4),
                "hold_bars": hold_bars,
            })

    # Compute stats
    if not all_trades:
        return {
            "strategy": strategy_name,
            "total_trades": 0,
            "win_rate": 0,
            "avg_pnl_pct": 0,
            "total_pnl_pct": 0,
            "sharpe": 0,
            "max_drawdown_pct": 0,
            "trades": [],
            "by_pair": {},
        }

    wins = [t for t in all_trades if t["pnl_pct"] > 0]
    losses = [t for t in all_trades if t["pnl_pct"] <= 0]
    pnls = [t["pnl_pct"] for t in all_trades]
    win_rate = len(wins) / len(all_trades) * 100
    avg_pnl = sum(pnls) / len(pnls)
    total_pnl = sum(pnls)

    # Sharpe (annualized, assuming ~252 trading days)
    pnl_arr = np.array(pnls)
    sharpe = 0.0
    if pnl_arr.std() > 0:
        sharpe = float(pnl_arr.mean() / pnl_arr.std() * np.sqrt(252))

    # Max drawdown
    cumulative = np.cumsum(pnl_arr)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = running_max - cumulative
    max_dd = float(drawdowns.max()) if len(drawdowns) > 0 else 0

    # By-pair breakdown
    by_pair: dict[str, dict] = {}
    for sym in set(t["symbol"] for t in all_trades):
        pair_trades = [t for t in all_trades if t["symbol"] == sym]
        pair_wins = [t for t in pair_trades if t["pnl_pct"] > 0]
        pair_pnls = [t["pnl_pct"] for t in pair_trades]
        by_pair[sym] = {
            "trades": len(pair_trades),
            "win_rate": round(len(pair_wins) / max(1, len(pair_trades)) * 100, 1),
            "avg_pnl": round(sum(pair_pnls) / max(1, len(pair_pnls)), 4),
            "total_pnl": round(sum(pair_pnls), 4),
            "tp_hit": len([t for t in pair_trades if t["exit_reason"] == "TP_HIT"]),
            "sl_hit": len([t for t in pair_trades if t["exit_reason"] == "SL_HIT"]),
            "expired": len([t for t in pair_trades if t["exit_reason"] == "TIME_EXPIRY"]),
        }

    # Exit reason breakdown
    tp_hits = len([t for t in all_trades if t["exit_reason"] == "TP_HIT"])
    sl_hits = len([t for t in all_trades if t["exit_reason"] == "SL_HIT"])
    expired = len([t for t in all_trades if t["exit_reason"] == "TIME_EXPIRY"])

    return {
        "strategy": strategy_name,
        "total_trades": len(all_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "avg_pnl_pct": round(avg_pnl, 4),
        "total_pnl_pct": round(total_pnl, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_hold_bars": round(sum(t["hold_bars"] for t in all_trades) / len(all_trades), 1),
        "exit_reasons": {
            "tp_hit": tp_hits,
            "sl_hit": sl_hits,
            "time_expiry": expired,
        },
        "by_pair": by_pair,
        "trades_sample": all_trades[:20],  # keep sample, not all
    }


# -- Strategy v1: Tight Scalp (London session only) --

def _strategy_v1_tight_scalp(sym: str, close: pd.Series, high: pd.Series,
                              low: pd.Series, cfg: dict) -> Optional[dict]:
    """v1: Tight scalp - TP 0.3%, SL 0.2%, max hold 4 bars.
    London session pairs only. RSI(2) extremes."""
    # Only trade London-session pairs for this scalp strategy
    if cfg.get("session") not in ("london",):
        return None

    if len(close) < 20:
        return None

    rsi2_val = float(_rsi(close, 2).iloc[-1])
    price = float(close.iloc[-1])

    if np.isnan(rsi2_val):
        return None

    direction = None
    if rsi2_val < 10:
        direction = "LONG"
    elif rsi2_val > 90:
        direction = "SHORT"

    if direction is None:
        return None

    tp_dist = price * 0.003  # 0.3%
    sl_dist = price * 0.002  # 0.2%

    if direction == "LONG":
        tp = price + tp_dist
        sl = price - sl_dist
    else:
        tp = price - tp_dist
        sl = price + sl_dist

    return {"direction": direction, "tp": tp, "sl": sl}


# -- Strategy v2: Carry + Session (carry pairs during London/NY overlap) --

def _strategy_v2_carry_session(sym: str, close: pd.Series, high: pd.Series,
                                low: pd.Series, cfg: dict) -> Optional[dict]:
    """v2: Carry + session - only trade positive-carry pairs.
    Long high-yield with momentum confirmation. TP 0.8%, SL 0.5%."""
    yield_diff = cfg.get("carry_yield_diff", 0)
    if yield_diff < 2.0:
        return None

    if len(close) < 50:
        return None

    price = float(close.iloc[-1])
    sma20 = float(_sma(close, 20).iloc[-1])
    rsi14_val = float(_rsi(close, 14).iloc[-1])

    if np.isnan(sma20) or np.isnan(rsi14_val):
        return None

    # Momentum: price above 20d SMA + RSI not extreme
    if price <= sma20 or rsi14_val > 72 or rsi14_val < 35:
        return None

    # 5d momentum check
    mom_5d = (price / float(close.iloc[-5]) - 1) if len(close) >= 5 else 0
    if mom_5d <= 0:
        return None

    tp_dist = price * 0.008  # 0.8%
    sl_dist = price * 0.005  # 0.5%

    return {
        "direction": "LONG",
        "tp": price + tp_dist,
        "sl": price - sl_dist,
    }


# -- Strategy v3: Mean Reversion (z-score > 2 from 200d SMA) --

def _strategy_v3_mean_reversion(sym: str, close: pd.Series, high: pd.Series,
                                 low: pd.Series, cfg: dict) -> Optional[dict]:
    """v3: Mean reversion - z-score > 2 from 200d SMA.
    TP = 50% return toward SMA (capped at 1.2%). SL 0.6%. Hold max 20 bars."""
    if len(close) < 210:
        return None

    price = float(close.iloc[-1])
    sma200 = float(_sma(close, 200).iloc[-1])
    z = float(_zscore_from_sma(close, 200).iloc[-1])

    if np.isnan(z) or np.isnan(sma200):
        return None

    direction = None
    if z > 2.0:
        direction = "SHORT"
    elif z < -2.0:
        direction = "LONG"

    if direction is None:
        return None

    # TP: 50% reversion toward 200d SMA, capped at 1.2%
    half_dist = abs(price - sma200) * 0.5
    max_tp_dist = price * 0.012  # 1.2% cap
    tp_dist = min(half_dist, max_tp_dist)
    sl_dist = price * 0.006  # 0.6%

    if direction == "LONG":
        tp = price + tp_dist
        sl = price - sl_dist
    else:
        tp = price - tp_dist
        sl = price + sl_dist

    return {"direction": direction, "tp": tp, "sl": sl}


# -- Strategy v4: JPY Risk-Off (short JPY crosses when VIX proxy rising) --

def _strategy_v4_jpy_riskoff(sym: str, close: pd.Series, high: pd.Series,
                              low: pd.Series, cfg: dict) -> Optional[dict]:
    """v4: JPY risk-off - SHORT JPY crosses when volatility rising.
    Uses vol expansion as VIX proxy. TP 0.6%, SL 0.4%. Hold max 10 bars."""
    if sym not in JPY_CROSSES:
        return None

    if len(close) < 65:
        return None

    price = float(close.iloc[-1])
    daily_ret = close.pct_change().dropna()

    if len(daily_ret) < 60:
        return None

    vol_20d = float(daily_ret.iloc[-20:].std())
    vol_60d = float(daily_ret.iloc[-60:].std())
    vol_ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0

    # Volatility expanding = risk-off environment
    if vol_ratio < 1.3:
        return None  # Need vol expansion for risk-off signal

    # RSI confirmation: JPY pair should be weakening (RSI falling)
    rsi14_val = float(_rsi(close, 14).iloc[-1])
    if np.isnan(rsi14_val) or rsi14_val > 55:
        return None  # Only short if pair already weakening

    # 5d momentum should be negative
    mom_5d = (price / float(close.iloc[-5]) - 1) if len(close) >= 5 else 0
    if mom_5d > 0:
        return None

    tp_dist = price * 0.006  # 0.6%
    sl_dist = price * 0.004  # 0.4%

    return {
        "direction": "SHORT",
        "tp": price - tp_dist,
        "sl": price + sl_dist,
    }


# -- Strategy v5: RSI(2) Daily (Connors adapted for forex) --

def _strategy_v5_rsi2_connors(sym: str, close: pd.Series, high: pd.Series,
                               low: pd.Series, cfg: dict) -> Optional[dict]:
    """v5: RSI(2) daily - buy RSI<5, sell RSI>95. Connors adapted for forex.
    TP 0.5% cap, SL 0.3%. Hold max 5 bars."""
    if len(close) < 20:
        return None

    price = float(close.iloc[-1])
    rsi2_val = float(_rsi(close, 2).iloc[-1])

    if np.isnan(rsi2_val):
        return None

    direction = None
    if rsi2_val < 5:
        direction = "LONG"
    elif rsi2_val > 95:
        direction = "SHORT"

    if direction is None:
        return None

    # Must be near a support/resistance (Bollinger band confirmation)
    bb_pos_val = float(_bb_position(close, 20, 2.0).iloc[-1])
    if not np.isnan(bb_pos_val):
        if direction == "LONG" and bb_pos_val > 0.3:
            return None  # Not near lower band
        if direction == "SHORT" and bb_pos_val < 0.7:
            return None  # Not near upper band

    tp_dist = price * 0.005  # 0.5%
    sl_dist = price * 0.003  # 0.3%

    if direction == "LONG":
        tp = price + tp_dist
        sl = price - sl_dist
    else:
        tp = price - tp_dist
        sl = price + sl_dist

    return {"direction": direction, "tp": tp, "sl": sl}


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

STRATEGY_VARIATIONS = [
    {
        "name": "v1_tight_scalp",
        "description": "Tight scalp: TP 0.3%, SL 0.2%, hold max 4 bars, London session pairs only",
        "fn": _strategy_v1_tight_scalp,
        "max_hold": 4,
        "tp_pct": 0.3,
        "sl_pct": 0.2,
        "pairs": "London session (EURUSD, GBPUSD, USDCHF, EURJPY, GBPJPY)",
    },
    {
        "name": "v2_carry_session",
        "description": "Carry + session: long high-yield pairs with momentum, TP 0.8%, SL 0.5%",
        "fn": _strategy_v2_carry_session,
        "max_hold": 20,
        "tp_pct": 0.8,
        "sl_pct": 0.5,
        "pairs": "Carry pairs (USDJPY, USDCHF, EURJPY, GBPJPY, AUDJPY)",
    },
    {
        "name": "v3_mean_reversion",
        "description": "Mean reversion: z-score >2 from 200d SMA, TP = return to SMA (capped 1.2%), SL 0.6%",
        "fn": _strategy_v3_mean_reversion,
        "max_hold": 20,
        "tp_pct": 1.2,
        "sl_pct": 0.6,
        "pairs": "All 10 forex pairs",
    },
    {
        "name": "v4_jpy_riskoff",
        "description": "JPY risk-off: SHORT JPY crosses when vol expanding, TP 0.6%, SL 0.4%",
        "fn": _strategy_v4_jpy_riskoff,
        "max_hold": 10,
        "tp_pct": 0.6,
        "sl_pct": 0.4,
        "pairs": "JPY crosses (USDJPY, EURJPY, GBPJPY, AUDJPY)",
    },
    {
        "name": "v5_rsi2_connors",
        "description": "RSI(2) daily: buy RSI<5 / sell RSI>95, Connors adapted, TP 0.5%, SL 0.3%",
        "fn": _strategy_v5_rsi2_connors,
        "max_hold": 5,
        "tp_pct": 0.5,
        "sl_pct": 0.3,
        "pairs": "All 10 forex pairs",
    },
]


# ---------------------------------------------------------------------------
# Generate ML picks from best-performing variations
# ---------------------------------------------------------------------------

def generate_ml_picks(data: dict[str, pd.DataFrame],
                      features: dict[str, dict],
                      backtest_results: list[dict]) -> list[dict]:
    """Generate actionable ML-scored forex picks from best strategies."""
    picks: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Rank strategies by Sharpe ratio
    ranked = sorted(backtest_results,
                    key=lambda r: r.get("sharpe", 0), reverse=True)

    for result in ranked:
        strat_name = result["strategy"]
        if result["total_trades"] < 5 or result["win_rate"] < 40:
            continue

        # Find the strategy function
        strat_cfg = next((s for s in STRATEGY_VARIATIONS
                          if s["name"] == strat_name), None)
        if not strat_cfg:
            continue

        fn = strat_cfg["fn"]

        for sym, df in data.items():
            if len(df) < 210:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            cfg = FOREX_PAIRS.get(sym, {})

            signal = fn(sym=sym, close=close, high=high, low=low, cfg=cfg)
            if signal is None:
                continue

            feat = features.get(sym, {})
            price = float(close.iloc[-1])

            # ML confidence: blend backtest win rate + feature quality
            base_conf = result["win_rate"] / 100
            # Boost if z-score is extreme (mean reversion)
            z = feat.get("zscore_200d")
            z_boost = 0.05 if z is not None and abs(z) > 1.5 else 0
            # Boost if RSI(2) extreme
            rsi2 = feat.get("rsi2")
            rsi_boost = 0.05 if rsi2 is not None and (rsi2 < 10 or rsi2 > 90) else 0

            confidence = round(min(0.85, base_conf + z_boost + rsi_boost), 3)

            # TP/SL from signal
            tp = signal["tp"]
            sl = signal["sl"]
            direction = signal["direction"]

            # Enforce forex TP < 1.5%, SL < 1.0% hard caps
            if direction == "LONG":
                tp_pct = (tp - price) / price * 100
                sl_pct = (price - sl) / price * 100
                if tp_pct > 1.5:
                    tp = price * 1.015
                if sl_pct > 1.0:
                    sl = price * 0.99
            else:
                tp_pct = (price - tp) / price * 100
                sl_pct = (sl - price) / price * 100
                if tp_pct > 1.5:
                    tp = price * 0.985
                if sl_pct > 1.0:
                    sl = price * 1.01

            # Risk/reward
            if direction == "LONG":
                rr = (tp - price) / (price - sl) if price > sl else 0
            else:
                rr = (price - tp) / (sl - price) if sl > price else 0

            if rr < 1.0:
                continue

            # Best pair for this strategy?
            pair_stats = result.get("by_pair", {}).get(sym, {})
            pair_wr = pair_stats.get("win_rate", result["win_rate"])

            pick_id = f"ml_forex_reverser::{strat_name}::{sym}::{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}"

            picks.append({
                "id": pick_id,
                "strategy": strat_name,
                "symbol": sym,
                "name": FOREX_PAIRS.get(sym, {}).get("name", sym),
                "category": "forex",
                "asset_class": "FOREX",
                "signal_type": "BUY" if direction == "LONG" else "SELL",
                "direction": direction,
                "entry_price": round(price, 5),
                "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "timestamp": now_iso,
                "take_profit": round(tp, 5),
                "stop_loss": round(sl, 5),
                "confidence": confidence,
                "ml_score": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Strategy {strat_name} (backtest WR={result['win_rate']:.1f}%, "
                    f"Sharpe={result['sharpe']:.2f}). "
                    f"Pair WR={pair_wr:.1f}%. "
                    f"RSI(2)={feat.get('rsi2')}, z-score={feat.get('zscore_200d')}"
                ),
                "status": "OPEN",
                "source_system": "ml_forex_reverser",
                "forward_test_only": True,
                "exit_price": None,
                "exit_date": None,
                "pnl_pct": None,
                "hold_days": None,
                "max_hold_bars": strat_cfg["max_hold"],
                "forward_trades": 0,
                "forward_wr": 0.0,
                "forward_validated": False,
                "extra": {
                    "backtest_trades": result["total_trades"],
                    "backtest_win_rate": result["win_rate"],
                    "backtest_sharpe": result["sharpe"],
                    "pair_win_rate": pair_wr,
                    "rsi2": feat.get("rsi2"),
                    "rsi14": feat.get("rsi14"),
                    "zscore_200d": feat.get("zscore_200d"),
                    "atr_pct": feat.get("atr_pct"),
                    "bb_position": feat.get("bb_position"),
                    "carry_yield_diff": feat.get("carry_yield_diff"),
                    "vol_ratio": feat.get("vol_ratio"),
                    "dxy_correlation": feat.get("dxy_correlation_60d"),
                },
            })

    # Deduplicate: one pick per symbol, keep highest confidence
    best_by_sym: dict[str, dict] = {}
    for p in picks:
        sym = p["symbol"]
        if sym not in best_by_sym or p["confidence"] > best_by_sym[sym]["confidence"]:
            best_by_sym[sym] = p
    picks = sorted(best_by_sym.values(), key=lambda p: p["confidence"], reverse=True)

    return picks


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run() -> dict[str, Any]:
    """Execute full forex asset class analysis pipeline."""
    if not HAS_DEPS:
        return {"error": "Missing dependencies: pip install yfinance pandas numpy"}

    print("=" * 70)
    print("FOREX ASSET CLASS ANALYSIS")
    print("=" * 70)
    start_time = time.time()

    # Step 1: Load all forex picks
    print("\n[1/7] Loading forex picks...")
    picks = _load_all_forex_picks()

    # Step 2: Fetch 2y daily OHLCV
    print("\n[2/7] Fetching 2y daily OHLCV for 10 forex pairs...")
    symbols = list(FOREX_PAIRS.keys())
    data = _fetch_forex_data(symbols, period="2y", interval="1d")
    print(f"  Got data for {len(data)}/{len(symbols)} pairs")

    # Step 3: Fetch DXY for correlation
    print("\n[3/7] Fetching DXY (US Dollar Index)...")
    dxy_df = _fetch_dxy(period="2y")

    # Step 4: Compute features
    print("\n[4/7] Computing forex-specific features...")
    features = compute_features(data, dxy_df)
    print(f"  Computed features for {len(features)} pairs")

    # Step 5: Diagnose failures
    print("\n[5/7] Diagnosing why old forex picks had 0% close rate...")
    diagnosis = diagnose_failures(picks, features)
    for d in diagnosis.get("diagnoses", []):
        print(f"  [{d['severity']}] {d['issue']}")

    # Step 6: Backtest 5 strategy variations
    print("\n[6/7] Backtesting 5 forex strategy variations on 2y data...")
    backtest_results: list[dict] = []
    for strat in STRATEGY_VARIATIONS:
        print(f"  Running {strat['name']}...")
        result = _backtest_strategy(
            data, strat["fn"], strat["name"], strat["max_hold"]
        )
        backtest_results.append(result)
        print(f"    Trades: {result['total_trades']}, "
              f"WR: {result['win_rate']:.1f}%, "
              f"Sharpe: {result['sharpe']:.2f}, "
              f"PnL: {result['total_pnl_pct']:.2f}%")

    # Step 7: Generate ML picks
    print("\n[7/7] Generating ML forex picks from best strategies...")
    ml_picks = generate_ml_picks(data, features, backtest_results)
    print(f"  Generated {len(ml_picks)} ML picks")

    # Pair-strategy matrix: which pairs work best for which strategy
    pair_strategy_matrix: dict[str, dict] = {}
    for result in backtest_results:
        for sym, stats in result.get("by_pair", {}).items():
            if sym not in pair_strategy_matrix:
                pair_strategy_matrix[sym] = {}
            pair_strategy_matrix[sym][result["strategy"]] = {
                "win_rate": stats["win_rate"],
                "avg_pnl": stats["avg_pnl"],
                "trades": stats["trades"],
            }

    elapsed = round(time.time() - start_time, 1)
    now_iso = datetime.now(timezone.utc).isoformat()

    # --- Save outputs ---

    # 1) forex_asset_analysis.json
    analysis_output = {
        "generated_at": now_iso,
        "source_system": "ml_forex_reverser",
        "elapsed_seconds": elapsed,
        "pairs_analyzed": len(features),
        "picks_loaded": len(picks),
        "features": features,
        "failure_diagnosis": diagnosis,
        "pair_strategy_matrix": pair_strategy_matrix,
    }
    out1 = DATA_DIR / "forex_asset_analysis.json"
    with open(out1, "w", encoding="utf-8") as f:
        json.dump(analysis_output, f, indent=2, default=str)
    print(f"\n  Saved: {out1}")

    # 2) forex_strategy_variations.json
    variations_output = {
        "generated_at": now_iso,
        "source_system": "ml_forex_reverser",
        "note": "CRITICAL: Forex TP < 1.5%, SL < 1.0%. Old system used crypto-scale targets.",
        "old_system_diagnosis": {
            "close_rate": f"{diagnosis.get('close_rate_pct', 0)}%",
            "avg_tp_pct": diagnosis.get("avg_tp_pct"),
            "tp_diagnosis": diagnosis.get("tp_diagnosis"),
            "key_issues": [d["issue"] for d in diagnosis.get("diagnoses", [])],
        },
        "variations": [],
    }
    for strat, result in zip(STRATEGY_VARIATIONS, backtest_results):
        variations_output["variations"].append({
            "name": strat["name"],
            "description": strat["description"],
            "tp_pct": strat["tp_pct"],
            "sl_pct": strat["sl_pct"],
            "max_hold_bars": strat["max_hold"],
            "target_pairs": strat["pairs"],
            "backtest": {
                "total_trades": result["total_trades"],
                "win_rate": result["win_rate"],
                "avg_pnl_pct": result["avg_pnl_pct"],
                "total_pnl_pct": result["total_pnl_pct"],
                "sharpe": result["sharpe"],
                "max_drawdown_pct": result["max_drawdown_pct"],
                "avg_hold_bars": result.get("avg_hold_bars", 0),
                "exit_reasons": result.get("exit_reasons", {}),
                "by_pair": result["by_pair"],
            },
        })
    out2 = DATA_DIR / "forex_strategy_variations.json"
    with open(out2, "w", encoding="utf-8") as f:
        json.dump(variations_output, f, indent=2, default=str)
    print(f"  Saved: {out2}")

    # 3) forex_ml_picks.json
    ml_output = {
        "generated_at": now_iso,
        "source_system": "ml_forex_reverser",
        "total_picks": len(ml_picks),
        "note": "All TP < 1.5%, SL < 1.0%. Forward-test-only until validated.",
        "picks": ml_picks,
    }
    out3 = DATA_DIR / "forex_ml_picks.json"
    with open(out3, "w", encoding="utf-8") as f:
        json.dump(ml_output, f, indent=2, default=str)
    print(f"  Saved: {out3}")

    print(f"\nDone in {elapsed}s. Analyzed {len(features)} pairs, "
          f"backtested {len(backtest_results)} strategies, "
          f"generated {len(ml_picks)} ML picks.")
    print("=" * 70)

    return {
        "status": "success",
        "pairs_analyzed": len(features),
        "picks_loaded": len(picks),
        "strategies_backtested": len(backtest_results),
        "ml_picks_generated": len(ml_picks),
        "elapsed_seconds": elapsed,
        "outputs": [str(out1), str(out2), str(out3)],
    }


if __name__ == "__main__":
    result = run()
    if result.get("error"):
        print(f"\nERROR: {result['error']}")
        sys.exit(1)
    print(f"\nResult: {json.dumps(result, indent=2)}")
