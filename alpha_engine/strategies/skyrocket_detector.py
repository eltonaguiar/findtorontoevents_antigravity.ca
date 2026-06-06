"""
Penny Stock Skyrocket Detector
==============================
Detects pre-spike conditions in penny/small-cap stocks based on the SIDU
pattern: volume declining into a tight consolidation, then explosive breakout
on 2x+ average volume.

SIDU reference pattern:
  - $0.63 -> $3.79 in 100 days (+311%)
  - Spike day: opened $2.01, closed $3.09 (+54%) on 66.7M vol (2.4x avg)
  - Pre-spike: volume DECLINING (12.2M vs 27.4M avg), price dipped $2.25->$2.10
  - Post-spike: $3.67 next day (+22%), then $3.79 (+3%)
  - Price under $5, float likely under 20M

Entry: breakout above 3-day high + 2x avg volume + RSI crossing 50
Exit:  +40% TP / -15% SL / 5-day max hold
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("skyrocket_detector")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ALPHA_DIR = _THIS_DIR.parent
_DATA_DIR = _ALPHA_DIR / "data"
_OUTPUT_FILE = _DATA_DIR / "skyrocket_picks.json"

# ---------------------------------------------------------------------------
# Default watchlist -- small/micro-cap tickers known for explosive moves
# Updated 2026-06-06: added validated skyrockets (NVRS/VZZ/WISE) + 2026 runners
# ---------------------------------------------------------------------------
DEFAULT_WATCHLIST = [
    # === 2026 validated skyrockets (NVRS +120%, VZZ +52%, WISE +49%) ===
    "NVRS", "VZZ", "WISE",
    # === 2026 active small-cap movers / AI/quantum theme ===
    "QUBT", "RGTI", "IONQ", "QBTS", "ARQQ", "DMNI",
    "SOUN", "GFAI", "RNAZ", "BTOG", "LASE", "BTAI",
    "NKLA", "FFIE", "WKHS", "SOLO", "IDEX", "AYRO",
    # === Biotech catalysts (FDA dates drive spikes) ===
    "BIOR", "ENVB", "COSM", "TTOO", "MGAM", "NVAX",
    "ACST", "PRAX", "AGEN", "GTHX", "ADTX", "GHSI",
    # === Energy / commodity micro-caps ===
    "INDO", "FAMI", "CEI", "IMPP", "NILE", "SOS",
    "WULF", "CLSK", "BTBT", "EBON", "MARA", "RIOT",
    # === Tech / social / EV still in penny range ===
    "WISH", "CLOV", "SNDL", "APRN", "GOEV",
    "SOFI", "LCID", "RIVN", "OPAL", "VNET",
    # === Legacy runners (may bounce) ===
    "SIDU", "MULN", "GFAI", "ATER", "PROG",
    "BBIG", "HYMC", "RDBX", "TBLT", "MEGL",
    "PRTY", "REV", "PLTR", "BIOR",
]

# ---------------------------------------------------------------------------
# Dynamic universe expansion via Yahoo Finance screener
# ---------------------------------------------------------------------------
def _fetch_dynamic_universe(max_results: int = 40) -> list[str]:
    """
    Pull a dynamic list of small-cap high-volume movers from Yahoo Finance
    screener API (day gainers + most active under $20).
    Falls back silently — callers use DEFAULT_WATCHLIST on failure.
    """
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0"}
        # Yahoo Finance day-gainers screener
        url = ("https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
               "?formatted=false&lang=en-US&region=US&scrIds=day_gainers"
               f"&count={max_results}&corsDomain=finance.yahoo.com")
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        quotes = (data.get("finance", {})
                      .get("result", [{}])[0]
                      .get("quotes", []))
        symbols = []
        for q in quotes:
            sym = q.get("symbol", "")
            price = q.get("regularMarketPrice", 999)
            # Only include sub-$25 movers with decent volume
            if sym and price and price <= 25.0 and q.get("regularMarketVolume", 0) >= 100_000:
                symbols.append(sym)
        logger.info("Dynamic universe: %d symbols from Yahoo screener", len(symbols))
        return symbols[:max_results]
    except Exception as exc:
        logger.debug("Dynamic universe fetch failed: %s", exc)
        return []

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Pre-spike signal thresholds
MAX_PRICE = 20.0            # Raised from $10 — catches NVRS/VZZ/WISE pre-spike range
VOL_DECLINE_DAYS = 3        # Days of declining volume before spike
VOL_BREAKOUT_MULT = 2.0     # Volume >= 2x 20-day avg on breakout
VOL_AVG_WINDOW = 20         # 20-day average volume window
SMA_PERIOD = 50             # 50-day SMA for uptrend context
ATR_PERIOD = 14             # ATR period for volatility
BB_PERIOD = 20              # Bollinger bandwidth period
RSI_PERIOD = 14             # RSI period
RSI_LOWER = 40              # RSI neutral zone lower
RSI_UPPER = 60              # RSI neutral zone upper
BREAKOUT_LOOKBACK = 3       # Break above 3-day high
TP_PCT = 0.40               # +40% take profit
SL_PCT = 0.15               # -15% stop loss
MAX_HOLD_DAYS = 5           # 5 trading day max hold

# Signal scoring weights (must sum to ~100)
W_VOL_DECLINE = 20          # Volume declining into consolidation
W_VOL_BREAKOUT = 25         # Volume spike on breakout day
W_PRICE_RANGE = 15          # Tight consolidation range
W_ABOVE_SMA = 10            # Above 50d SMA (uptrend)
W_BB_SQUEEZE = 15           # Bollinger bandwidth compression
W_RSI_ZONE = 15             # RSI in neutral zone / crossing 50


# ---------------------------------------------------------------------------
# Technical indicator helpers
# ---------------------------------------------------------------------------
def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def _bollinger_bandwidth(close: pd.Series, period: int = 20,
                         num_std: float = 2.0) -> pd.Series:
    """Bollinger Bandwidth = (Upper - Lower) / Middle."""
    mid = _sma(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return (upper - lower) / (mid + 1e-10)


# ---------------------------------------------------------------------------
# Data fetching via yfinance
# ---------------------------------------------------------------------------
def fetch_data(symbols: list[str], period: str = "6mo",
               interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for symbols using yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed -- pip install yfinance")
        return {}

    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period=period, interval=interval)
            if df is not None and len(df) >= 30:
                data[sym] = df
                logger.debug("Fetched %s: %d bars", sym, len(df))
            else:
                logger.debug("Skipping %s: insufficient data (%d bars)",
                             sym, len(df) if df is not None else 0)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", sym, exc)
    logger.info("Fetched data for %d / %d symbols", len(data), len(symbols))
    return data


# ---------------------------------------------------------------------------
# Core signal scoring
# ---------------------------------------------------------------------------
def _score_symbol(symbol: str, df: pd.DataFrame) -> Optional[dict]:
    """
    Score a single symbol for skyrocket pre-spike conditions.

    Returns a pick dict or None if conditions not met.
    """
    if len(df) < max(SMA_PERIOD, VOL_AVG_WINDOW, BB_PERIOD, ATR_PERIOD) + 10:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    current_price = float(close.iloc[-1])

    # ----- Filter 1: Price must be under MAX_PRICE -----
    if current_price > MAX_PRICE or current_price <= 0.01:
        return None

    # ----- Compute indicators -----
    sma_50 = _sma(close, SMA_PERIOD)
    rsi_vals = _rsi(close, RSI_PERIOD)
    atr_vals = _atr(high, low, close, ATR_PERIOD)
    bb_bw = _bollinger_bandwidth(close, BB_PERIOD)
    vol_avg_20 = _sma(volume, VOL_AVG_WINDOW)

    # Current values
    cur_sma50 = float(sma_50.iloc[-1])
    cur_rsi = float(rsi_vals.iloc[-1])
    prev_rsi = float(rsi_vals.iloc[-2]) if len(rsi_vals) > 1 else cur_rsi
    cur_atr = float(atr_vals.iloc[-1])
    cur_bb_bw = float(bb_bw.iloc[-1])
    cur_vol = float(volume.iloc[-1])
    cur_vol_avg = float(vol_avg_20.iloc[-1])

    # Historical BB bandwidth for percentile ranking
    bb_bw_clean = bb_bw.dropna()
    if len(bb_bw_clean) < 10:
        return None

    # ----- Score each condition -----
    score = 0.0
    reasons = []

    # 1. Volume declining for VOL_DECLINE_DAYS before today
    vol_declining = True
    if len(volume) >= VOL_DECLINE_DAYS + 1:
        # Check volume trend in the days BEFORE today (indices -4, -3, -2)
        for i in range(VOL_DECLINE_DAYS, 1, -1):
            if float(volume.iloc[-i]) >= float(volume.iloc[-(i + 1)]):
                vol_declining = False
                break
    else:
        vol_declining = False

    if vol_declining:
        score += W_VOL_DECLINE
        reasons.append("vol declining pre-breakout")

    # 2. Volume spike on today >= 2x average
    vol_ratio = cur_vol / (cur_vol_avg + 1.0)
    if vol_ratio >= VOL_BREAKOUT_MULT:
        vol_score = min(W_VOL_BREAKOUT, W_VOL_BREAKOUT * (vol_ratio / 4.0))
        score += vol_score
        reasons.append(f"vol spike {vol_ratio:.1f}x avg")

    # 3. Tight price consolidation (low range / ATR ratio in last 3 days)
    if len(high) >= BREAKOUT_LOOKBACK and cur_atr > 0:
        recent_range = float(high.iloc[-BREAKOUT_LOOKBACK:].max() -
                             low.iloc[-BREAKOUT_LOOKBACK:].min())
        range_atr_ratio = recent_range / cur_atr
        if range_atr_ratio < 2.0:
            # Tighter = better
            range_score = W_PRICE_RANGE * max(0, (2.0 - range_atr_ratio) / 2.0)
            score += range_score
            reasons.append(f"tight range ({range_atr_ratio:.1f}x ATR)")

    # 4. Price above 50d SMA (uptrend context)
    if cur_sma50 > 0 and current_price > cur_sma50:
        score += W_ABOVE_SMA
        reasons.append("above 50d SMA")

    # 5. Bollinger bandwidth compression (squeeze)
    bb_percentile = float((bb_bw_clean < cur_bb_bw).sum() / len(bb_bw_clean))
    if bb_percentile < 0.30:
        squeeze_score = W_BB_SQUEEZE * (1.0 - bb_percentile / 0.30)
        score += squeeze_score
        reasons.append(f"BB squeeze (pctl={bb_percentile:.0%})")

    # 6. RSI in neutral zone or crossing above 50
    rsi_crossing_50 = prev_rsi < 50 and cur_rsi >= 50
    rsi_in_zone = RSI_LOWER <= cur_rsi <= RSI_UPPER

    if rsi_crossing_50:
        score += W_RSI_ZONE
        reasons.append("RSI crossing above 50")
    elif rsi_in_zone:
        score += W_RSI_ZONE * 0.6
        reasons.append(f"RSI neutral zone ({cur_rsi:.0f})")

    # ----- Breakout confirmation: price above 3-day high -----
    if len(high) >= BREAKOUT_LOOKBACK + 1:
        three_day_high = float(high.iloc[-(BREAKOUT_LOOKBACK + 1):-1].max())
        breakout = current_price > three_day_high
    else:
        breakout = False

    if not breakout:
        # No breakout yet -- reduce score but still report if strong setup
        score *= 0.5

    # ----- Minimum score threshold -----
    # Backtest: score>=50 = break-even/positive. score<35 = all losers.
    # 2026-06-06: lowered to 40 for pre-breakout setups (breakout halves score → 50 pre-breakout = 25 scored).
    # This catches NVRS/VZZ/WISE-type setups earlier (tight consolidation + vol decline before confirmed breakout).
    score = min(100.0, round(score, 1))
    MIN_SCORE = 40.0
    if score < MIN_SCORE:
        return None

    # ----- Compute entry / TP / SL -----
    entry_price = current_price
    take_profit = round(entry_price * (1 + TP_PCT), 4)
    stop_loss = round(entry_price * (1 - SL_PCT), 4)
    risk_reward = TP_PCT / SL_PCT if SL_PCT > 0 else 0.0

    confidence = min(0.90, round(score / 100.0, 2))

    now_iso = datetime.now(timezone.utc).isoformat()

    pick = {
        "id": f"skyrocket_detector::{symbol}::{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}",
        "strategy": "skyrocket_detector",
        "symbol": symbol,
        "category": "penny",
        "signal_type": "BUY",
        "direction": "LONG",
        "entry_price": round(entry_price, 4),
        "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": now_iso,
        "take_profit": round(take_profit, 4),
        "stop_loss": round(stop_loss, 4),
        "confidence": confidence,
        "ml_score": confidence,
        "risk_reward": round(risk_reward, 2),
        "reason": "; ".join(reasons) if reasons else "pre-spike setup",
        "status": "OPEN",
        "source_system": "skyrocket_detector",
        "forward_test_only": True,
        "exit_price": None,
        "exit_date": None,
        "closed_at": None,
        "pnl_pct": None,
        "hold_days": None,
        "asset_class": "EQUITY",
        "forward_trades": 0,
        "forward_wr": 0.0,
        "forward_validated": False,
        "source_strategy_type": "penny_skyrocket",
        "timeframe": "1d",
        "max_hold_days": MAX_HOLD_DAYS,
        "extra": {
            "score": score,
            "breakout_confirmed": breakout,
            "vol_ratio": round(vol_ratio, 2),
            "rsi": round(cur_rsi, 1),
            "prev_rsi": round(prev_rsi, 1),
            "bb_percentile": round(bb_percentile, 3),
            "atr": round(cur_atr, 4),
            "sma_50": round(cur_sma50, 4),
            "vol_declining": vol_declining,
            "current_volume": int(cur_vol),
            "avg_volume_20d": int(cur_vol_avg),
        },
    }
    return pick


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------
def scan(watchlist: Optional[list[str]] = None,
         data: Optional[dict[str, pd.DataFrame]] = None,
         save: bool = True) -> list[dict]:
    """
    Scan watchlist for skyrocket setups.

    Parameters
    ----------
    watchlist : list of ticker strings (defaults to DEFAULT_WATCHLIST)
    data : pre-fetched OHLCV data dict; if None, fetches via yfinance
    save : whether to write results to skyrocket_picks.json

    Returns
    -------
    List of pick dicts sorted by score descending.
    """
    if watchlist is None:
        # Merge static watchlist + dynamic universe (deduped)
        dynamic = _fetch_dynamic_universe(max_results=50)
        combined = list(dict.fromkeys(DEFAULT_WATCHLIST + dynamic))
        watchlist = combined
        logger.info("Watchlist: %d static + %d dynamic = %d total",
                    len(DEFAULT_WATCHLIST), len(dynamic), len(watchlist))

    # Drop delisted / renamed tickers — they return all-NaN from yfinance
    # and spam "possibly delisted; no price data found" warnings.
    try:
        import sys as _sys, os as _os
        _scanners = _os.path.join(_os.path.dirname(__file__),
                                  "..", "..", "STOCKS", "scanners")
        if _scanners not in _sys.path:
            _sys.path.insert(0, _scanners)
        from delisted_symbols import filter_delisted
        watchlist = filter_delisted(watchlist)
    except ImportError:
        pass

    if data is None:
        data = fetch_data(watchlist, period="6mo", interval="1d")

    picks: list[dict] = []
    for sym in watchlist:
        df = data.get(sym)
        if df is None:
            continue
        try:
            pick = _score_symbol(sym, df)
            if pick is not None:
                picks.append(pick)
        except Exception as exc:
            logger.warning("Error scoring %s: %s", sym, exc)

    # Sort by score descending
    picks.sort(key=lambda p: p.get("extra", {}).get("score", 0), reverse=True)

    logger.info("Scan complete: %d picks from %d symbols", len(picks), len(data))

    # Always write the output file when save is requested — including the
    # 0-pick case. A 0-pick cycle (all symbols delisted, or no setups) must
    # still produce a valid {count: 0, picks: []} file: the runner workflow
    # `git add`s this path and hard-fails (exit 128 "did not match any
    # files") if it is absent, and downstream readers get a fresh empty
    # result instead of stale data.
    if save:
        _save_picks(picks)

    return picks


def _save_picks(picks: list[dict]) -> None:
    """Write picks to JSON file."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "strategy": "skyrocket_detector",
                "count": len(picks),
                "picks": picks,
            }, f, indent=2, default=str)
        logger.info("Saved %d picks to %s", len(picks), _OUTPUT_FILE)
    except Exception as exc:
        logger.error("Failed to save picks: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Backtest on historical SIDU data
# ---------------------------------------------------------------------------
def backtest_sidu(data: Optional[dict[str, pd.DataFrame]] = None,
                  verbose: bool = True) -> dict:
    """
    Backtest the skyrocket detector on historical SIDU data.

    Walks through each bar and checks if the detector would have fired
    before the actual spike day. Returns performance metrics.
    """
    if data is None:
        data = fetch_data(["SIDU"], period="1y", interval="1d")

    df = data.get("SIDU")
    if df is None or len(df) < 60:
        logger.error("Cannot backtest: SIDU data not available or too short")
        return {"error": "SIDU data unavailable"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    results = {
        "symbol": "SIDU",
        "total_bars": len(df),
        "signals_fired": 0,
        "trades": [],
        "wins": 0,
        "losses": 0,
        "total_pnl_pct": 0.0,
    }

    # Minimum lookback
    min_lookback = max(SMA_PERIOD, VOL_AVG_WINDOW, BB_PERIOD, ATR_PERIOD) + 10
    i = min_lookback

    active_trade = None

    while i < len(df):
        date_str = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(df.index[i])

        # Check for exit on active trade
        if active_trade is not None:
            cur_close = float(close.iloc[i])
            cur_high_val = float(high.iloc[i])
            cur_low_val = float(low.iloc[i])
            hold_days = i - active_trade["entry_bar"]

            exit_reason = None
            exit_price = None

            # Check stop loss (intrabar)
            if cur_low_val <= active_trade["stop_loss"]:
                exit_price = active_trade["stop_loss"]
                exit_reason = "stop_loss"
            # Check take profit (intrabar)
            elif cur_high_val >= active_trade["take_profit"]:
                exit_price = active_trade["take_profit"]
                exit_reason = "take_profit"
            # Check time exit
            elif hold_days >= MAX_HOLD_DAYS:
                exit_price = cur_close
                exit_reason = "time_exit"

            if exit_reason:
                pnl_pct = (exit_price / active_trade["entry_price"] - 1) * 100
                trade_result = {
                    "entry_date": active_trade["entry_date"],
                    "exit_date": date_str,
                    "entry_price": active_trade["entry_price"],
                    "exit_price": round(exit_price, 4),
                    "pnl_pct": round(pnl_pct, 2),
                    "hold_days": hold_days,
                    "exit_reason": exit_reason,
                    "score": active_trade["score"],
                }
                results["trades"].append(trade_result)
                if pnl_pct > 0:
                    results["wins"] += 1
                else:
                    results["losses"] += 1
                results["total_pnl_pct"] += pnl_pct
                active_trade = None
                if verbose:
                    logger.info("  EXIT %s: %.2f%% (%s)", date_str, pnl_pct, exit_reason)
            i += 1
            continue

        # No active trade -- check for entry signal
        slice_df = df.iloc[:i + 1].copy()
        pick = _score_symbol("SIDU", slice_df)

        if pick is not None and pick.get("extra", {}).get("breakout_confirmed", False):
            entry_price = float(close.iloc[i])
            tp = round(entry_price * (1 + TP_PCT), 4)
            sl = round(entry_price * (1 - SL_PCT), 4)
            score = pick.get("extra", {}).get("score", 0)

            active_trade = {
                "entry_bar": i,
                "entry_date": date_str,
                "entry_price": entry_price,
                "take_profit": tp,
                "stop_loss": sl,
                "score": score,
            }
            results["signals_fired"] += 1
            if verbose:
                logger.info("  ENTRY %s @ $%.2f (score=%.0f)", date_str, entry_price, score)

        i += 1

    # Summary
    total_trades = results["wins"] + results["losses"]
    results["total_trades"] = total_trades
    results["win_rate"] = round(results["wins"] / total_trades * 100, 1) if total_trades > 0 else 0.0
    results["avg_pnl_pct"] = round(results["total_pnl_pct"] / total_trades, 2) if total_trades > 0 else 0.0

    if verbose:
        logger.info("=" * 60)
        logger.info("SIDU BACKTEST RESULTS")
        logger.info("=" * 60)
        logger.info("Signals fired : %d", results["signals_fired"])
        logger.info("Trades closed : %d", total_trades)
        logger.info("Win rate      : %.1f%%", results["win_rate"])
        logger.info("Total PnL     : %.2f%%", results["total_pnl_pct"])
        logger.info("Avg PnL/trade : %.2f%%", results["avg_pnl_pct"])
        for t in results["trades"]:
            logger.info("  %s -> %s  %.2f%% (%s)",
                        t["entry_date"], t["exit_date"],
                        t["pnl_pct"], t["exit_reason"])

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """Run the skyrocket detector scan and optionally backtest SIDU."""
    import argparse

    parser = argparse.ArgumentParser(description="Penny Stock Skyrocket Detector")
    parser.add_argument("--backtest", action="store_true",
                        help="Run backtest on historical SIDU data")
    parser.add_argument("--symbols", nargs="*", default=None,
                        help="Custom watchlist (space-separated tickers)")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not save results to JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.backtest:
        logger.info("Running SIDU backtest...")
        results = backtest_sidu(verbose=True)
        print(json.dumps(results, indent=2, default=str))
        return

    watchlist = args.symbols if args.symbols else DEFAULT_WATCHLIST
    logger.info("Scanning %d symbols for skyrocket setups...", len(watchlist))

    picks = scan(watchlist=watchlist, save=not args.no_save)

    if picks:
        print(f"\n{'='*70}")
        print(f"SKYROCKET DETECTOR -- {len(picks)} picks found")
        print(f"{'='*70}")
        for i, p in enumerate(picks, 1):
            extra = p.get("extra", {})
            print(f"\n#{i} {p['symbol']} @ ${p['entry_price']:.2f}")
            print(f"   Score: {extra.get('score', 0):.0f}/100 | "
                  f"Confidence: {p['confidence']:.0%}")
            print(f"   TP: ${p['take_profit']:.2f} (+{TP_PCT*100:.0f}%) | "
                  f"SL: ${p['stop_loss']:.2f} (-{SL_PCT*100:.0f}%)")
            print(f"   Vol ratio: {extra.get('vol_ratio', 0):.1f}x | "
                  f"RSI: {extra.get('rsi', 0):.0f} | "
                  f"Breakout: {'YES' if extra.get('breakout_confirmed') else 'NO'}")
            print(f"   Reason: {p['reason']}")
    else:
        print("\nNo skyrocket setups found in current scan.")


if __name__ == "__main__":
    main()
