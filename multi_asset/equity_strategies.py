#!/usr/bin/env python3
"""
EQUITY & ETF DEDICATED STRATEGIES v1.0
=======================================
Stock-specific and ETF-specific strategies that exploit edges unique to
equities (earnings drift, sector rotation, dividend quality, VIX timing).

These strategies are designed to improve the 43.8% equity WR by targeting
well-documented academic anomalies rather than applying crypto-style
momentum to stocks.

Strategies:
  1. Earnings Momentum (PEAD) -- Post-Earnings Announcement Drift
  2. Sector Rotation -- Relative strength rotation across sector ETFs
  3. Blue Chip Mean Reversion -- RSI(2) < 10 on quality large-caps
  4. VIX Market Timing -- Fear/greed-based index ETF entries
  5. Dividend Aristocrat Defense -- Defensive rotation in bear markets

Usage:
  Imported by multi_asset/scanner.py and registered in STRATEGIES dict.
  Each function has signature: (df, symbol, info, **kwargs) -> list[dict]

References:
  - Ball & Brown (1968): Post-Earnings Announcement Drift
  - Jegadeesh & Titman (1993): Momentum
  - Connors & Alvarez (2009): RSI(2) mean reversion
  - Faber (2007): Sector rotation via relative strength
  - Ang et al. (2006): VIX as predictor of returns
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Earnings calendar helpers (for PEAD gate)
# ---------------------------------------------------------------------------

# Cache file path (created on demand). Schema: {"SYMBOL": "YYYY-MM-DD", ...}
_EARNINGS_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "alpha_engine", "data", "earnings_calendar.json",
)

# In-process cache so repeated calls don't hammer disk / network
_EARNINGS_MEM_CACHE: dict[str, Optional[str]] = {}


def _load_earnings_cache_file() -> dict:
    try:
        if os.path.exists(_EARNINGS_CACHE_PATH):
            with open(_EARNINGS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _fetch_earnings_date_yf(symbol: str) -> Optional[datetime]:
    """
    Try to fetch the most recent earnings date via yfinance.
    Returns a tz-aware UTC datetime, or None if unavailable / errors.
    Wrapped to never hang or raise.
    """
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return None
    try:
        ticker = yf.Ticker(symbol)
        # Prefer earnings_dates (DataFrame indexed by date)
        try:
            ed = ticker.earnings_dates  # type: ignore[attr-defined]
        except Exception:
            ed = None
        if ed is not None and hasattr(ed, "index") and len(ed) > 0:
            now = pd.Timestamp.utcnow()
            try:
                idx = ed.index
                if getattr(idx, "tz", None) is not None:
                    past = ed[idx <= now.tz_localize(idx.tz) if now.tz is None else now]
                else:
                    past = ed[idx <= pd.Timestamp.utcnow().tz_localize(None)]
            except Exception:
                past = ed
            if len(past) > 0:
                last = past.index.max()
                ts = pd.Timestamp(last)
                if ts.tz is None:
                    ts = ts.tz_localize("UTC")
                return ts.to_pydatetime()
    except Exception:
        return None
    return None


def days_since_earnings(symbol: str, today: Optional[datetime] = None,
                        ticker_factory=None) -> Optional[int]:
    """
    Return the number of *calendar* days since the symbol's most recent
    earnings announcement, or None if unknown.

    Lookup order:
      1. In-process memoized cache
      2. JSON cache at alpha_engine/data/earnings_calendar.json
      3. yfinance (best-effort, never raises, no retries)

    Args:
      symbol: ticker symbol
      today: reference "now" (UTC); defaults to datetime.now(timezone.utc)
      ticker_factory: optional callable(symbol) -> object exposing
        ``earnings_dates`` (a DataFrame-like with .index). Used for tests
        to inject a mock instead of touching yfinance.
    """
    if not symbol:
        return None
    sym = symbol.upper()
    now = today or datetime.now(timezone.utc)

    # 1. Memo cache
    if sym in _EARNINGS_MEM_CACHE:
        cached = _EARNINGS_MEM_CACHE[sym]
        if cached is None:
            return None
        try:
            dt = datetime.strptime(cached, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return max(0, (now - dt).days)
        except ValueError:
            return None

    # 2. JSON file cache
    file_cache = _load_earnings_cache_file()
    if sym in file_cache:
        try:
            dt = datetime.strptime(str(file_cache[sym]), "%Y-%m-%d").replace(
                tzinfo=timezone.utc)
            _EARNINGS_MEM_CACHE[sym] = file_cache[sym]
            return max(0, (now - dt).days)
        except ValueError:
            pass

    # 3. yfinance / injected factory (best effort)
    earnings_dt: Optional[datetime] = None
    if ticker_factory is not None:
        try:
            tk = ticker_factory(sym)
            ed = getattr(tk, "earnings_dates", None)
            if ed is not None and hasattr(ed, "index") and len(ed) > 0:
                last = pd.Timestamp(ed.index.max())
                if last.tz is None:
                    last = last.tz_localize("UTC")
                earnings_dt = last.to_pydatetime()
        except Exception:
            earnings_dt = None
    else:
        earnings_dt = _fetch_earnings_date_yf(sym)

    if earnings_dt is None:
        _EARNINGS_MEM_CACHE[sym] = None
        return None

    _EARNINGS_MEM_CACHE[sym] = earnings_dt.strftime("%Y-%m-%d")
    return max(0, (now - earnings_dt).days)


# ---------------------------------------------------------------------------
# Indicator helpers (self-contained so this module works standalone)
# ---------------------------------------------------------------------------

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _bollinger_bands(series: pd.Series, period: int = 20,
                     std_mult: float = 2.0):
    mid = _sma(series, period)
    std = series.rolling(period).std()
    return mid, mid + std_mult * std, mid - std_mult * std


def _volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    avg_vol = volume.rolling(period).mean()
    return volume / avg_vol.replace(0, np.nan)


def _safe_float(val) -> float:
    """Extract scalar float from pandas/numpy values safely."""
    if hasattr(val, "item"):
        return float(val.item())
    return float(val)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Symbol universes
# ---------------------------------------------------------------------------

# Blue chips: high-quality large-caps that mean-revert reliably
BLUE_CHIPS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "V", "JNJ", "PG", "UNH", "HD", "MA", "KO",
    "PEP", "MRK", "ABBV", "CRM", "COST", "WMT", "DIS",
}

# Sector ETFs for rotation strategy
SECTOR_ETFS = {
    "XLK": {"name": "Technology",      "sector": "tech"},
    "XLF": {"name": "Financials",      "sector": "financials"},
    "XLE": {"name": "Energy",          "sector": "energy"},
    "XLV": {"name": "Health Care",     "sector": "healthcare"},
    "XLI": {"name": "Industrials",     "sector": "industrials"},
    "XLY": {"name": "Cons. Disc.",     "sector": "consumer_disc"},
    "XLP": {"name": "Cons. Staples",   "sector": "consumer_staples"},
    "XLU": {"name": "Utilities",       "sector": "utilities"},
    "XLB": {"name": "Materials",       "sector": "materials"},
    "XLRE": {"name": "Real Estate",    "sector": "real_estate"},
    "XLC": {"name": "Communication",   "sector": "communication"},
}

# Index ETFs for VIX timing
INDEX_ETFS = {"SPY", "QQQ", "IWM", "DIA"}

# ── Leveraged ETF Universe (3x bull/bear pairs) ──
# High-beta instruments for tactical regime plays. MUST be paired with
# tight stops (1x ATR max) — daily compounding decays unleveraged exposure
# in choppy markets. Only trade in confirmed regime (bull/bear trend).
LEVERAGED_ETFS_3X = {
    # Broad market
    "TQQQ": {"name": "3x Long QQQ (Nasdaq-100)",     "sector": "tech",          "direction": "long",  "pair": "SQQQ"},
    "SQQQ": {"name": "3x Short QQQ (Nasdaq-100)",    "sector": "tech",          "direction": "short", "pair": "TQQQ"},
    "SPXL": {"name": "3x Long S&P 500",              "sector": "broad_market",  "direction": "long",  "pair": "SPXS"},
    "SPXS": {"name": "3x Short S&P 500",             "sector": "broad_market",  "direction": "short", "pair": "SPXL"},
    "UPRO": {"name": "3x Long S&P 500 (ProShares)",  "sector": "broad_market",  "direction": "long",  "pair": "SPXU"},
    "SPXU": {"name": "3x Short S&P 500 (ProShares)", "sector": "broad_market",  "direction": "short", "pair": "UPRO"},
    "TNA":  {"name": "3x Long Russell 2000",         "sector": "small_cap",     "direction": "long",  "pair": "TZA"},
    "TZA":  {"name": "3x Short Russell 2000",        "sector": "small_cap",     "direction": "short", "pair": "TNA"},
    "UDOW": {"name": "3x Long Dow Jones",            "sector": "broad_market",  "direction": "long",  "pair": "SDOW"},
    "SDOW": {"name": "3x Short Dow Jones",           "sector": "broad_market",  "direction": "short", "pair": "UDOW"},
    # Sector leveraged
    "FAS":  {"name": "3x Long Financials",           "sector": "financials",    "direction": "long",  "pair": "FAZ"},
    "FAZ":  {"name": "3x Short Financials",          "sector": "financials",    "direction": "short", "pair": "FAS"},
    "SOXL": {"name": "3x Long Semiconductors",       "sector": "semiconductors","direction": "long",  "pair": "SOXS"},
    "SOXS": {"name": "3x Short Semiconductors",      "sector": "semiconductors","direction": "short", "pair": "SOXL"},
    "ERX":  {"name": "3x Long Energy",               "sector": "energy",        "direction": "long",  "pair": "ERY"},
    "ERY":  {"name": "3x Short Energy",              "sector": "energy",        "direction": "short", "pair": "ERX"},
    "LABU": {"name": "3x Long Biotech (S&P)",        "sector": "biotech",       "direction": "long",  "pair": "LABD"},
    "LABD": {"name": "3x Short Biotech (S&P)",       "sector": "biotech",       "direction": "short", "pair": "LABU"},
    "CURE": {"name": "3x Long Healthcare",           "sector": "healthcare",    "direction": "long",  "pair": None},
    "DRN":  {"name": "3x Long Real Estate",          "sector": "real_estate",   "direction": "long",  "pair": "DRV"},
    "DRV":  {"name": "3x Short Real Estate",         "sector": "real_estate",   "direction": "short", "pair": "DRN"},
    "DPST": {"name": "3x Long Regional Banks",       "sector": "financials",    "direction": "long",  "pair": "WDRW"},
    "WDRW": {"name": "3x Short Regional Banks",      "sector": "financials",    "direction": "short", "pair": "DPST"},
    "RETL": {"name": "3x Long Retail",               "sector": "consumer_disc", "direction": "long",  "pair": None},
    "NAIL": {"name": "3x Long Homebuilders",         "sector": "homebuilders",  "direction": "long",  "pair": None},
    # Commodity leveraged
    "NUGT": {"name": "2x Long Gold Miners",          "sector": "precious_metals","direction":"long",  "pair": "DUST"},
    "DUST": {"name": "2x Short Gold Miners",         "sector": "precious_metals","direction":"short", "pair": "NUGT"},
    "JNUG": {"name": "2x Long Junior Gold Miners",   "sector": "precious_metals","direction":"long",  "pair": "JDST"},
    "JDST": {"name": "2x Short Junior Gold Miners",  "sector": "precious_metals","direction":"short", "pair": "JNUG"},
    "GUSH": {"name": "2x Long Oil & Gas Exploration","sector": "energy",        "direction": "long",  "pair": "DRIP"},
    "DRIP": {"name": "2x Short Oil & Gas Exploration","sector":"energy",        "direction": "short", "pair": "GUSH"},
    # Volatility
    "UVXY": {"name": "1.5x Long VIX Short-Term",     "sector": "volatility",    "direction": "long",  "pair": "SVXY"},
    "SVXY": {"name": "-0.5x Short VIX Short-Term",   "sector": "volatility",    "direction": "short", "pair": "UVXY"},
    "VIXY": {"name": "1x Long VIX Short-Term",       "sector": "volatility",    "direction": "long",  "pair": None},
    # International leveraged
    "YINN": {"name": "3x Long FTSE China 50",        "sector": "china",         "direction": "long",  "pair": "YANG"},
    "YANG": {"name": "3x Short FTSE China 50",       "sector": "china",         "direction": "short", "pair": "YINN"},
    "EDC":  {"name": "3x Long Emerging Markets",     "sector": "emerging_mkt",  "direction": "long",  "pair": "EDZ"},
    "EDZ":  {"name": "3x Short Emerging Markets",    "sector": "emerging_mkt",  "direction": "short", "pair": "EDC"},
}

# Leveraged ETFs are HIGH-RISK — reserved for strong-trend regimes only.
# Risk parameters: tighter stops, shorter hold (daily decay hurts).
LEVERAGED_ETF_RISK = {
    "stop_loss_pct": -0.03,    # -3% (3x leverage = 1% underlying move)
    "take_profit_pct": 0.06,   # +6% (2:1 R:R)
    "max_hold_days": 5,        # Daily-compounded decay means <= 1 week
    "min_adv_usd": 10_000_000, # Minimum $10M average daily volume (liquidity)
}

# Dividend aristocrats (25+ years of consecutive dividend increases)
DIVIDEND_ARISTOCRATS = {
    "PG", "JNJ", "KO", "PEP", "MMM", "ABT", "ABBV",
    "T", "XOM", "CVX", "MCD", "WMT", "CL", "EMR",
    "SHW", "ADP", "BDX", "ITW", "ED", "GPC",
}

# Growth basket for regime switching
GROWTH_BASKET = {
    "NVDA", "TSLA", "META", "AMZN", "CRM", "AMD", "SNOW",
    "NET", "SHOP", "SQ", "DDOG", "CRWD",
}

# Risk parameters: (stop_loss_pct, take_profit_pct, max_hold_days)
EQUITY_RISK = {
    "stock":       (-0.06, 0.12, 10),
    "blue_chip":   (-0.04, 0.08, 7),   # Tighter for blue chips
    "etf":         (-0.05, 0.10, 15),
    "sector_etf":  (-0.05, 0.10, 20),  # Sector rotation holds longer
    "aristocrat":  (-0.04, 0.08, 20),  # Defensive, patient
}


# =========================================================================
# STRATEGY 1: Earnings Momentum (PEAD)
# =========================================================================
# Post-Earnings Announcement Drift: stocks that gap up on volume after
# earnings tend to continue drifting higher for 30-60 days.
# We detect this via: gap up > 3% + volume > 2x average on a single day
# within the last 10 trading days.
# Reference: Ball & Brown (1968), Bernard & Thomas (1989).
# =========================================================================

def earnings_momentum_pead(df: pd.DataFrame, symbol: str,
                           info: dict, **kwargs) -> list[dict]:
    """
    Detect post-earnings drift from price/volume gaps.
    Buy stocks that gapped up 3%+ on 2x+ volume in last 10 days.

    Earnings calendar gate (added 2026-04-12, see
    FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md §Earnings Momentum PEAD):
    if a recent earnings announcement is *known*, the gap must be within
    a small window of it (otherwise the gap is probably not earnings-driven
    and PEAD edge does not apply). If earnings data is unknown, the pick
    passes through with ``earnings_beat_gate=None`` (graceful degradation).
    Max holding period of 10 trading days is tagged on every signal so the
    portfolio manager can enforce time-stops.
    """
    # Optional ticker factory injection (used by unit tests so they never
    # touch yfinance / the network).
    _ticker_factory = kwargs.get("ticker_factory")
    # Allow tests / callers to override the calendar window
    _earnings_window_days = int(kwargs.get("earnings_window_days", 14))
    _max_hold_days = int(kwargs.get("max_hold_days", 10))
    signals = []
    cat = info.get("cat", "stock")
    if cat not in ("stock", "etf"):
        return signals
    if len(df) < 60:
        return signals

    close = df["Close"]
    volume = df["Volume"]
    open_price = df["Open"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # Must be above 50d SMA (healthy uptrend context)
    sma_50 = _safe_float(_sma(close, 50).iloc[-1])
    if not np.isfinite(sma_50) or price < sma_50:
        return signals

    # Scan last 10 trading days for an earnings-like gap
    avg_vol_20 = _safe_float(volume.iloc[-30:-10].mean())
    if avg_vol_20 <= 0:
        return signals

    best_gap = None
    best_gap_pct = 0.0
    best_vol_ratio = 0.0

    for i in range(-10, 0):
        day_open = _safe_float(open_price.iloc[i])
        prev_close = _safe_float(close.iloc[i - 1])
        day_vol = _safe_float(volume.iloc[i])

        if prev_close <= 0 or day_open <= 0:
            continue

        gap_pct = (day_open / prev_close) - 1.0
        vol_ratio = day_vol / avg_vol_20

        # Earnings gap: open gapped up > 3% on 2x+ volume
        if gap_pct > 0.03 and vol_ratio > 2.0:
            if gap_pct > best_gap_pct:
                best_gap_pct = gap_pct
                best_vol_ratio = vol_ratio
                best_gap = i

    if best_gap is None:
        return signals

    # Confirm price held above gap level (no immediate reversal)
    gap_day_open = _safe_float(open_price.iloc[best_gap])
    if price < gap_day_open * 0.98:
        return signals  # Price gave back the gap -- drift failed

    # RSI filter: don't buy if already overbought
    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])
    if not np.isfinite(rsi_val) or rsi_val > 75:
        return signals

    # Entry signal
    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    tp = price + 3.0 * atr_val
    sl = max(gap_day_open * 0.97, price - 2.0 * atr_val)
    rr = (tp - price) / (price - sl) if price > sl else 0
    if rr < 1.3:
        return signals

    conf = min(0.80, 0.55 + best_gap_pct * 2.0 + (best_vol_ratio - 2.0) * 0.02)

    # ------------------------------------------------------------------
    # Earnings calendar gate
    # ------------------------------------------------------------------
    earn_days = days_since_earnings(symbol, ticker_factory=_ticker_factory)
    if earn_days is None:
        earnings_beat_gate: Optional[bool] = None
        earnings_window_tag = "unknown"
    else:
        if earn_days <= _earnings_window_days:
            earnings_beat_gate = True
            earnings_window_tag = "in_window"
        else:
            earnings_beat_gate = False
            earnings_window_tag = "stale"
            # Hard-block only when we *do* have data and it says stale.
            return signals

    signal = {
        "strategy": "earnings_momentum_pead",
        "symbol": symbol,
        "category": cat,
        "direction": "LONG",
        "signal_type": "BUY",
        "entry_price": round(price, 2),
        "take_profit": round(tp, 2),
        "stop_loss": round(sl, 2),
        "confidence": round(conf, 3),
        "risk_reward": round(rr, 2),
        "reason": (f"PEAD: {best_gap_pct*100:.1f}% gap up on "
                   f"{best_vol_ratio:.1f}x vol, price held above gap, "
                   f"RSI={rsi_val:.0f}"),
        "rsi_at_entry": round(rsi_val, 1),
        "earnings_days_ago": earn_days if earn_days is not None else -1,
        "max_hold_days": _max_hold_days,
        "earnings_beat_gate": earnings_beat_gate,
        "earnings_window": earnings_window_tag,
        "extra": {
            "gap_pct": round(best_gap_pct, 4),
            "gap_vol_ratio": round(best_vol_ratio, 2),
            "days_since_gap": abs(best_gap),
            "earnings_days_ago": earn_days,
            "earnings_window_days": _earnings_window_days,
        },
    }
    signals.append(signal)
    return signals


# =========================================================================
# STRATEGY 2: Sector Rotation (Relative Strength)
# =========================================================================
# When a sector ETF's 20d return significantly lags its peers, money
# tends to rotate into it. Go LONG the weakest sector(s) that show
# early reversal signs (RSI turning up from oversold).
# Reference: Faber (2007), Moskowitz & Grinblatt (1999).
# =========================================================================

def sector_rotation(df: pd.DataFrame, symbol: str, info: dict,
                    **kwargs) -> list[dict]:
    """
    Sector rotation: buy lagging sector ETFs showing reversal.
    Requires sector_data kwarg with all sector ETF DataFrames.
    """
    signals = []
    cat = info.get("cat", "etf")
    if symbol not in SECTOR_ETFS:
        return signals
    if len(df) < 60:
        return signals

    # Need peer sector data to compute relative strength
    sector_data: dict = kwargs.get("sector_data", {})
    if len(sector_data) < 5:
        return signals  # Need enough peers for comparison

    close = df["Close"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # Compute 20-day returns for all sectors
    sector_returns = {}
    for sec_sym, sec_df in sector_data.items():
        if sec_sym not in SECTOR_ETFS:
            continue
        if sec_df is None or len(sec_df) < 25:
            continue
        sec_close = sec_df["Close"]
        ret_20d = _safe_float(sec_close.iloc[-1]) / _safe_float(sec_close.iloc[-21]) - 1.0
        if np.isfinite(ret_20d):
            sector_returns[sec_sym] = ret_20d

    if len(sector_returns) < 5:
        return signals

    # This symbol's return
    my_return = sector_returns.get(symbol)
    if my_return is None:
        return signals

    # Rank: 0 = worst, 1 = best
    sorted_rets = sorted(sector_returns.values())
    rank = sorted_rets.index(my_return) / max(1, len(sorted_rets) - 1)

    # Only buy bottom 30% (lagging sectors)
    if rank > 0.30:
        return signals

    # Reversal confirmation: RSI(14) was < 35 recently and is now rising
    rsi_14 = _rsi(close, 14)
    rsi_val = _safe_float(rsi_14.iloc[-1])
    rsi_3d_ago = _safe_float(rsi_14.iloc[-4]) if len(rsi_14) > 4 else rsi_val

    if not np.isfinite(rsi_val):
        return signals

    # Need RSI to be turning up from oversold territory
    if rsi_val > 50:
        return signals  # Already recovered, too late
    if rsi_val <= rsi_3d_ago:
        return signals  # Still falling, wait for reversal

    # Must be above 200d SMA (secular uptrend filter)
    if len(close) >= 200:
        sma_200 = _safe_float(_sma(close, 200).iloc[-1])
        if np.isfinite(sma_200) and price < sma_200:
            return signals  # Broken trend, skip

    # Entry
    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    sl_pct, tp_pct, _ = EQUITY_RISK["sector_etf"]
    tp = price + 3.0 * atr_val
    sl = price * (1 + sl_pct)
    rr = (tp - price) / (price - sl) if price > sl else 0
    if rr < 1.2:
        return signals

    median_ret = float(np.median(sorted_rets))
    conf = min(0.75, 0.50 + abs(my_return - median_ret) * 3.0)

    signals.append({
        "strategy": "sector_rotation",
        "symbol": symbol,
        "category": "etf",
        "direction": "LONG",
        "signal_type": "BUY",
        "entry_price": round(price, 2),
        "take_profit": round(tp, 2),
        "stop_loss": round(sl, 2),
        "confidence": round(conf, 3),
        "risk_reward": round(rr, 2),
        "reason": (f"Sector rotation: {SECTOR_ETFS[symbol]['name']} lagging "
                   f"(20d return={my_return*100:.1f}%, rank bottom {rank*100:.0f}%), "
                   f"RSI reversing up {rsi_3d_ago:.0f}->{rsi_val:.0f}"),
        "rsi_at_entry": round(rsi_val, 1),
        "extra": {
            "sector_return_20d": round(my_return, 4),
            "sector_rank_pct": round(rank, 3),
            "median_sector_return": round(median_ret, 4),
        },
    })
    return signals


# =========================================================================
# STRATEGY 3: Blue Chip Mean Reversion (RSI-2 + Quality Filter)
# =========================================================================
# Connors RSI(2) < 10 on blue chips above their 200d SMA historically
# delivers 75%+ WR. We add quality filters: stock must be in BLUE_CHIPS
# set, must have positive 6-month return (healthy stock, temp dip).
# Also: RSI(2) > 95 SHORT for overextended blue chips below 200d SMA.
# Reference: Connors & Alvarez (2009), "Short Term Trading Strategies
# That Work".
# =========================================================================

def blue_chip_mean_reversion(df: pd.DataFrame, symbol: str,
                             info: dict, **kwargs) -> list[dict]:
    """
    RSI(2) mean reversion specifically for blue-chip stocks.
    Tighter criteria, higher confidence than generic connors_rsi2.
    """
    signals = []
    cat = info.get("cat", "stock")
    if cat not in ("stock", "etf"):
        return signals
    if symbol not in BLUE_CHIPS:
        return signals
    if len(df) < 200:
        return signals

    close = df["Close"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    rsi_2 = _rsi(close, 2)
    rsi_val = _safe_float(rsi_2.iloc[-1])
    if not np.isfinite(rsi_val):
        return signals

    sma_200 = _safe_float(_sma(close, 200).iloc[-1])
    sma_5 = _safe_float(_sma(close, 5).iloc[-1])

    if not all(np.isfinite([sma_200, sma_5])):
        return signals

    # 6-month momentum check: stock must have positive 6m return
    if len(close) >= 126:
        ret_6m = price / _safe_float(close.iloc[-126]) - 1.0
    else:
        ret_6m = 0.0

    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    # Count consecutive down days (streak measure)
    down_days = 0
    for i in range(-1, max(-8, -len(close)), -1):
        if _safe_float(close.iloc[i]) < _safe_float(close.iloc[i - 1]):
            down_days += 1
        else:
            break

    # === BUY: RSI(2) < 10, above 200d SMA, positive 6m momentum ===
    if rsi_val < 10 and price > sma_200 and ret_6m > 0.0:
        # Tighter stop for blue chips (they bounce faster)
        tp = sma_5  # Target: revert to 5d SMA (Connors classic exit)
        sl = price - 2.0 * atr_val

        rr = (tp - price) / (price - sl) if price > sl and tp > price else 0
        if rr < 0.8:  # Lower RR threshold -- high WR compensates
            # Fallback: use fixed percentage targets
            tp = price * 1.04
            sl = price * 0.97
            rr = (tp - price) / (price - sl)

        # Confidence scales with how extreme the RSI is and streak length
        conf = min(0.90, 0.65 + (10 - rsi_val) * 0.03 + down_days * 0.02)

        signals.append({
            "strategy": "blue_chip_mean_reversion",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"Blue chip RSI(2)={rsi_val:.1f}, {down_days} down days, "
                       f"above 200d SMA (${sma_200:.2f}), "
                       f"6m return +{ret_6m*100:.1f}%"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "down_day_streak": down_days,
                "momentum_6m": round(ret_6m, 4),
                "sma_200": round(sma_200, 2),
                "exit_target": "5d SMA reversion",
            },
        })

    # === SHORT: RSI(2) > 95, below 200d SMA, negative 6m momentum ===
    if rsi_val > 95 and price < sma_200 and ret_6m < 0.0:
        tp = sma_5  # Revert down to 5d SMA
        sl = price + 2.0 * atr_val

        rr = (price - tp) / (sl - price) if sl > price and price > tp else 0
        if rr < 0.8:
            tp = price * 0.96
            sl = price * 1.03
            rr = (price - tp) / (sl - price) if sl > price else 0

        conf = min(0.85, 0.60 + (rsi_val - 90) * 0.03)

        signals.append({
            "strategy": "blue_chip_mean_reversion",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"Blue chip RSI(2)={rsi_val:.1f} overbought, "
                       f"below 200d SMA (${sma_200:.2f}), "
                       f"6m return {ret_6m*100:.1f}%"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "momentum_6m": round(ret_6m, 4),
                "sma_200": round(sma_200, 2),
            },
        })

    return signals


# =========================================================================
# STRATEGY 4: VIX Market Timing for Index ETFs
# =========================================================================
# VIX > 30 = extreme fear -> historically excellent time to buy SPY/QQQ
# VIX < 12 = complacency -> reduce exposure, potential hedge
# VIX 20-30 crossing down = fear subsiding -> buy with normal size
# Reference: Ang et al. (2006), Whaley (2000).
# =========================================================================

def vix_market_timing(df: pd.DataFrame, symbol: str, info: dict,
                      **kwargs) -> list[dict]:
    """
    VIX-based market timing for index ETFs.
    Buy index ETFs when VIX signals extreme fear that is reversing.
    """
    signals = []
    cat = info.get("cat", "etf")
    if symbol not in INDEX_ETFS:
        return signals
    if len(df) < 50:
        return signals

    vix_data: Optional[pd.DataFrame] = kwargs.get("vix_data")
    if vix_data is None or len(vix_data) < 20:
        return signals

    close = df["Close"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    vix_close = vix_data["Close"]
    vix_now = _safe_float(vix_close.iloc[-1])
    vix_5d_ago = _safe_float(vix_close.iloc[-6]) if len(vix_close) > 6 else vix_now
    vix_10d_ago = _safe_float(vix_close.iloc[-11]) if len(vix_close) > 11 else vix_now
    vix_sma_20 = _safe_float(_sma(vix_close, 20).iloc[-1])

    if not all(np.isfinite([vix_now, vix_5d_ago, vix_sma_20])):
        return signals

    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])

    sl_pct, tp_pct, _ = EQUITY_RISK["etf"]

    # === REGIME 1: VIX > 30, extreme fear -> buy on VIX reversal ===
    if vix_now > 30 and vix_now < vix_5d_ago:
        # VIX was extreme and is now dropping -> fear subsiding
        vix_drop = (vix_5d_ago - vix_now) / vix_5d_ago
        if vix_drop < 0.05:
            return signals  # Need meaningful VIX drop

        tp = price + 4.0 * atr_val  # Wider TP in high-vol env
        sl = price - 2.5 * atr_val  # Wider SL too

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.2:
            return signals

        conf = min(0.82, 0.60 + (vix_now - 30) * 0.005 + vix_drop * 0.5)

        signals.append({
            "strategy": "vix_market_timing",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"VIX extreme fear ({vix_now:.1f}>{30}) reversing "
                       f"({vix_drop*100:.1f}% drop from {vix_5d_ago:.1f}), "
                       f"buying {symbol}"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "vix_current": round(vix_now, 2),
                "vix_5d_ago": round(vix_5d_ago, 2),
                "vix_drop_pct": round(vix_drop, 4),
                "regime": "extreme_fear_reversal",
            },
        })

    # === REGIME 2: VIX 20-30, elevated fear, crossing below 20d SMA ===
    elif 20 < vix_now < 30 and vix_now < vix_sma_20 and vix_5d_ago > vix_sma_20:
        # VIX just crossed below its 20d average -- fear normalizing
        tp = price + 3.0 * atr_val
        sl = price - 2.0 * atr_val

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            return signals

        conf = min(0.72, 0.55 + (30 - vix_now) * 0.01)

        signals.append({
            "strategy": "vix_market_timing",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"VIX ({vix_now:.1f}) crossed below 20d SMA "
                       f"({vix_sma_20:.1f}), fear normalizing"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "vix_current": round(vix_now, 2),
                "vix_sma_20": round(vix_sma_20, 2),
                "regime": "fear_normalizing",
            },
        })

    # === REGIME 3: VIX < 12, complacency -> SHORT signal (hedge) ===
    elif vix_now < 12 and vix_now > vix_5d_ago:
        # VIX extremely low and rising -> complacency ending
        # Only short if price is also showing distribution (below 10d SMA)
        sma_10 = _safe_float(_sma(close, 10).iloc[-1])
        if not np.isfinite(sma_10) or price > sma_10:
            return signals  # Price still strong, don't short

        tp = price - 2.5 * atr_val
        sl = price + 1.5 * atr_val

        rr = (price - tp) / (sl - price) if sl > price else 0
        if rr < 1.2:
            return signals

        conf = min(0.65, 0.45 + (12 - vix_now) * 0.03)

        signals.append({
            "strategy": "vix_market_timing",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"VIX complacency ({vix_now:.1f}<12) ending, "
                       f"price below 10d SMA, hedging {symbol}"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "vix_current": round(vix_now, 2),
                "regime": "complacency_warning",
            },
        })

    return signals


# =========================================================================
# STRATEGY 5: Dividend Aristocrat Defensive Rotation
# =========================================================================
# In bear/risk-off regimes, dividend aristocrats outperform growth.
# In bull/risk-on regimes, growth outperforms defensives.
# Use SPY's position relative to its 200d SMA + VIX level to determine
# regime, then go LONG the appropriate basket.
# Reference: Ang (2014), O'Shaughnessy (2012).
# =========================================================================

def dividend_aristocrat_defense(df: pd.DataFrame, symbol: str,
                                info: dict, **kwargs) -> list[dict]:
    """
    Rotate into dividend aristocrats during bearish regimes,
    growth stocks during bullish regimes.
    """
    signals = []
    cat = info.get("cat", "stock")
    if cat not in ("stock", "etf"):
        return signals
    if len(df) < 200:
        return signals

    # Determine which basket this symbol belongs to
    is_aristocrat = symbol in DIVIDEND_ARISTOCRATS
    is_growth = symbol in GROWTH_BASKET
    if not is_aristocrat and not is_growth:
        return signals

    close = df["Close"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # Need SPY data for regime detection
    spy_data: Optional[pd.DataFrame] = kwargs.get("spy_data")
    vix_data: Optional[pd.DataFrame] = kwargs.get("vix_data")

    # Determine regime from SPY + VIX
    regime = _detect_regime(spy_data, vix_data)

    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])
    if not np.isfinite(rsi_val):
        return signals

    sma_200 = _safe_float(_sma(close, 200).iloc[-1])
    sma_50 = _safe_float(_sma(close, 50).iloc[-1])
    if not all(np.isfinite([sma_200, sma_50])):
        return signals

    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    # === BEARISH regime: buy aristocrats, avoid growth ===
    if regime == "BEAR" and is_aristocrat:
        # Aristocrat must still be in relative uptrend
        if price < sma_200:
            return signals  # Even defensive stock is broken
        if rsi_val > 70:
            return signals  # Already overbought

        # Relative strength: aristocrat holding up better than market
        if len(close) >= 21:
            stock_ret_20d = price / _safe_float(close.iloc[-21]) - 1.0
        else:
            stock_ret_20d = 0.0

        tp = price + 2.5 * atr_val
        sl = price - 1.5 * atr_val

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.2:
            return signals

        conf = min(0.75, 0.55 + abs(stock_ret_20d) * 2.0)

        signals.append({
            "strategy": "dividend_aristocrat_defense",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"Bear regime defense: {symbol} aristocrat above "
                       f"200d SMA, RSI={rsi_val:.0f}, "
                       f"20d return={stock_ret_20d*100:.1f}%"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "regime": regime,
                "basket": "dividend_aristocrat",
                "stock_return_20d": round(stock_ret_20d, 4),
            },
        })

    # === BULLISH regime: buy growth names on pullback ===
    elif regime == "BULL" and is_growth:
        if price < sma_50:
            return signals  # Growth stock lost momentum
        if rsi_val > 75:
            return signals  # Already extended

        # Need a pullback: RSI < 45 (dip in uptrend)
        if rsi_val > 45:
            return signals  # Not a pullback

        # Must have positive short-term momentum (bouncing)
        if len(close) >= 3:
            bounce = _safe_float(close.iloc[-1]) > _safe_float(close.iloc[-3])
        else:
            bounce = False
        if not bounce:
            return signals

        tp = price + 3.5 * atr_val
        sl = price - 2.0 * atr_val

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            return signals

        conf = min(0.78, 0.52 + (45 - rsi_val) * 0.01)

        signals.append({
            "strategy": "dividend_aristocrat_defense",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": round(price, 2),
            "take_profit": round(tp, 2),
            "stop_loss": round(sl, 2),
            "confidence": round(conf, 3),
            "risk_reward": round(rr, 2),
            "reason": (f"Bull regime growth: {symbol} pullback RSI={rsi_val:.0f}, "
                       f"above 50d SMA, bouncing"),
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "regime": regime,
                "basket": "growth",
            },
        })

    return signals


def _detect_regime(spy_data: Optional[pd.DataFrame],
                   vix_data: Optional[pd.DataFrame]) -> str:
    """
    Determine market regime from SPY + VIX.
    Returns: "BULL", "BEAR", or "CHOP".
    """
    if spy_data is None or len(spy_data) < 200:
        return "CHOP"

    spy_close = spy_data["Close"]
    spy_price = _safe_float(spy_close.iloc[-1])
    spy_sma_200 = _safe_float(_sma(spy_close, 200).iloc[-1])
    spy_sma_50 = _safe_float(_sma(spy_close, 50).iloc[-1])

    if not all(np.isfinite([spy_price, spy_sma_200, spy_sma_50])):
        return "CHOP"

    vix_level = 20.0  # Default
    if vix_data is not None and len(vix_data) > 0:
        vix_level = _safe_float(vix_data["Close"].iloc[-1])
        if not np.isfinite(vix_level):
            vix_level = 20.0

    # BULL: SPY above 200d SMA, 50d > 200d (golden cross), VIX < 25
    if spy_price > spy_sma_200 and spy_sma_50 > spy_sma_200 and vix_level < 25:
        return "BULL"

    # BEAR: SPY below 200d SMA OR VIX > 30
    if spy_price < spy_sma_200 or vix_level > 30:
        return "BEAR"

    return "CHOP"


# =========================================================================
# STRATEGY 6: Gap Fill Reversion (Equity-Specific)
# =========================================================================
# Stocks that gap down 2-5% on low/normal volume (not earnings) tend to
# fill the gap within 3-5 days. This exploits the overnight gap anomaly
# documented by Doran, Peterson & Wright (2008).
# =========================================================================

def gap_fill_reversion(df: pd.DataFrame, symbol: str, info: dict,
                       **kwargs) -> list[dict]:
    """
    Buy stocks that gapped down 2-5% on normal volume (gap fill play).
    Exclude earnings gaps (those are strategy 1 territory).
    """
    signals = []
    cat = info.get("cat", "stock")
    if cat not in ("stock", "etf"):
        return signals
    if len(df) < 50:
        return signals

    close = df["Close"]
    open_price = df["Open"]
    volume = df["Volume"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # Check today's open vs yesterday's close
    today_open = _safe_float(open_price.iloc[-1])
    prev_close = _safe_float(close.iloc[-2])
    if prev_close <= 0:
        return signals

    gap_pct = (today_open / prev_close) - 1.0

    # Gap down between -2% and -5% (too large = likely news-driven)
    if gap_pct > -0.02 or gap_pct < -0.05:
        return signals

    # Volume filter: NOT an earnings gap (volume should be < 2x average)
    vol_ratio = _safe_float(_volume_ratio(volume).iloc[-1])
    if not np.isfinite(vol_ratio) or vol_ratio > 2.0:
        return signals  # High volume gap = real news, not a fill candidate

    # Must be above 200d SMA (healthy stock, not a broken one)
    if len(close) >= 200:
        sma_200 = _safe_float(_sma(close, 200).iloc[-1])
        if np.isfinite(sma_200) and price < sma_200:
            return signals

    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])
    if not np.isfinite(rsi_val):
        return signals

    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    # Target: gap fill (previous close)
    tp = prev_close
    sl = price - 1.5 * atr_val

    rr = (tp - price) / (price - sl) if price > sl and tp > price else 0
    if rr < 1.0:
        return signals

    conf = min(0.72, 0.50 + abs(gap_pct) * 5.0)

    signals.append({
        "strategy": "gap_fill_reversion",
        "symbol": symbol,
        "category": cat,
        "direction": "LONG",
        "signal_type": "BUY",
        "entry_price": round(price, 2),
        "take_profit": round(tp, 2),
        "stop_loss": round(sl, 2),
        "confidence": round(conf, 3),
        "risk_reward": round(rr, 2),
        "reason": (f"Gap down {gap_pct*100:.1f}% on normal vol "
                   f"({vol_ratio:.1f}x), target gap fill to "
                   f"${prev_close:.2f}"),
        "rsi_at_entry": round(rsi_val, 1),
        "extra": {
            "gap_pct": round(gap_pct, 4),
            "volume_ratio": round(vol_ratio, 2),
            "gap_fill_target": round(prev_close, 2),
        },
    })
    return signals


# =========================================================================
# STRATEGY 7: ETF Relative Strength Momentum
# =========================================================================
# Buy the top-performing ETFs by 1-month momentum that are pulling back.
# This is sector-agnostic and works across the full ETF universe.
# Reference: Antonacci (2012) "Dual Momentum".
# =========================================================================

def etf_relative_strength(df: pd.DataFrame, symbol: str, info: dict,
                          **kwargs) -> list[dict]:
    """
    Buy ETFs showing relative strength leadership with pullback entry.
    Requires etf_data kwarg with all ETF DataFrames.
    """
    signals = []
    cat = info.get("cat", "etf")
    if cat != "etf":
        return signals
    if len(df) < 60:
        return signals

    close = df["Close"]
    price = _safe_float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    etf_data: dict = kwargs.get("etf_data", {})
    if len(etf_data) < 4:
        return signals

    # Compute 1-month (21d) return for all ETFs
    etf_returns = {}
    for etf_sym, etf_df in etf_data.items():
        if etf_df is None or len(etf_df) < 25:
            continue
        etf_close = etf_df["Close"]
        ret = _safe_float(etf_close.iloc[-1]) / _safe_float(etf_close.iloc[-22]) - 1.0
        if np.isfinite(ret):
            etf_returns[etf_sym] = ret

    if len(etf_returns) < 4 or symbol not in etf_returns:
        return signals

    # Rank by 1-month return
    sorted_by_ret = sorted(etf_returns.items(), key=lambda x: x[1], reverse=True)
    rank = [s for s, _ in sorted_by_ret].index(symbol)
    rank_pct = rank / max(1, len(sorted_by_ret) - 1)

    # Only buy top 30% performers
    if rank_pct > 0.30:
        return signals

    my_return = etf_returns[symbol]
    if my_return < 0.01:
        return signals  # Need positive momentum

    # Pullback entry: RSI(14) between 30-50 (dip in uptrend)
    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])
    if not np.isfinite(rsi_val):
        return signals
    if rsi_val < 25 or rsi_val > 55:
        return signals  # Either too weak or not pulling back

    # Must be above 50d SMA
    sma_50 = _safe_float(_sma(close, 50).iloc[-1])
    if not np.isfinite(sma_50) or price < sma_50:
        return signals

    atr_val = _safe_float(_atr(df["High"], df["Low"], close).iloc[-1])
    if not np.isfinite(atr_val) or atr_val <= 0:
        return signals

    tp = price + 3.0 * atr_val
    sl = price - 2.0 * atr_val

    rr = (tp - price) / (price - sl) if price > sl else 0
    if rr < 1.2:
        return signals

    conf = min(0.75, 0.50 + my_return * 3.0)

    signals.append({
        "strategy": "etf_relative_strength",
        "symbol": symbol,
        "category": cat,
        "direction": "LONG",
        "signal_type": "BUY",
        "entry_price": round(price, 2),
        "take_profit": round(tp, 2),
        "stop_loss": round(sl, 2),
        "confidence": round(conf, 3),
        "risk_reward": round(rr, 2),
        "reason": (f"ETF relative strength leader "
                   f"(1m return={my_return*100:.1f}%, rank top {rank_pct*100:.0f}%), "
                   f"pullback RSI={rsi_val:.0f}"),
        "rsi_at_entry": round(rsi_val, 1),
        "extra": {
            "return_1m": round(my_return, 4),
            "rank_pct": round(rank_pct, 3),
            "rank": rank,
        },
    })
    return signals


# =========================================================================
# Registry -- all equity/ETF strategies
# =========================================================================

EQUITY_ETF_STRATEGIES = {
    "earnings_momentum_pead": earnings_momentum_pead,
    "sector_rotation": sector_rotation,
    "blue_chip_mean_reversion": blue_chip_mean_reversion,
    "vix_market_timing": vix_market_timing,
    "dividend_aristocrat_defense": dividend_aristocrat_defense,
    "gap_fill_reversion": gap_fill_reversion,
    "etf_relative_strength": etf_relative_strength,
}

# Symbols these strategies cover (for scanner integration)
EQUITY_ETF_SYMBOLS = {
    # Blue chips
    **{s: {"name": s, "cat": "stock"} for s in BLUE_CHIPS},
    # Sector ETFs
    **{s: {"name": v["name"], "cat": "etf"} for s, v in SECTOR_ETFS.items()},
    # Index ETFs
    **{s: {"name": s, "cat": "etf"} for s in INDEX_ETFS},
    # Leveraged ETFs (3x bull/bear pairs) — tactical only, tight stops
    **{s: {"name": v["name"], "cat": "leveraged_etf"} for s, v in LEVERAGED_ETFS_3X.items()},
    # Dividend aristocrats (not already in blue chips)
    **{s: {"name": s, "cat": "stock"} for s in DIVIDEND_ARISTOCRATS - BLUE_CHIPS},
    # Growth basket (not already in blue chips)
    **{s: {"name": s, "cat": "stock"} for s in GROWTH_BASKET - BLUE_CHIPS},
}


def run_all_equity_strategies(data: dict[str, pd.DataFrame],
                              vix_data: Optional[pd.DataFrame] = None,
                              spy_data: Optional[pd.DataFrame] = None,
                              ) -> list[dict]:
    """
    Run all equity/ETF strategies on the provided data.

    Args:
        data: Dict mapping symbol -> DataFrame with OHLCV columns.
        vix_data: Optional VIX DataFrame (^VIX) for VIX-based strategies.
        spy_data: Optional SPY DataFrame for regime detection.

    Returns:
        List of signal dicts ready for the scanner pipeline.
    """
    all_signals = []
    now_iso = _now_iso()

    # Build kwargs for strategies that need cross-asset data
    sector_data = {s: data.get(s) for s in SECTOR_ETFS if s in data}
    etf_data = {s: data.get(s) for s in (set(SECTOR_ETFS) | INDEX_ETFS) if s in data}

    if spy_data is None and "SPY" in data:
        spy_data = data["SPY"]

    common_kwargs = {
        "sector_data": sector_data,
        "etf_data": etf_data,
        "vix_data": vix_data,
        "spy_data": spy_data,
    }

    for symbol, info in EQUITY_ETF_SYMBOLS.items():
        df = data.get(symbol)
        if df is None:
            continue

        for strat_name, strat_fn in EQUITY_ETF_STRATEGIES.items():
            try:
                signals = strat_fn(df, symbol, info, **common_kwargs)
                for sig in signals:
                    sig["timestamp"] = now_iso
                    sig["source_system"] = "equity_etf_strategies"
                    all_signals.append(sig)
            except Exception as exc:
                # Never let one strategy crash the whole scan
                print(f"  [WARN] {strat_name}/{symbol}: {exc}")
                continue

    return all_signals


# ---------------------------------------------------------------------------
# CLI: standalone scan for testing (does NOT overwrite any live files)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance required. pip install yfinance")
        sys.exit(1)

    print("=" * 70)
    print("EQUITY & ETF STRATEGIES v1.0 -- Standalone Scan")
    print("=" * 70)

    # Download data for all symbols
    all_syms = list(EQUITY_ETF_SYMBOLS.keys())
    all_syms_str = " ".join(all_syms)

    # Add VIX
    all_syms.append("^VIX")

    print(f"Downloading data for {len(all_syms)} symbols...")
    raw = yf.download(all_syms, period="1y", group_by="ticker",
                      threads=True, progress=False)

    data = {}
    vix_df = None
    for sym in all_syms:
        try:
            if sym == "^VIX":
                vix_df = raw[sym].dropna()
            else:
                df = raw[sym].dropna()
                if len(df) > 50:
                    data[sym] = df
        except (KeyError, TypeError):
            continue

    print(f"Got data for {len(data)} symbols")

    signals = run_all_equity_strategies(data, vix_data=vix_df)

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(signals)} signals generated")
    print(f"{'='*70}")

    for sig in sorted(signals, key=lambda s: s.get("confidence", 0), reverse=True):
        direction = sig.get("direction", "LONG")
        arrow = "^" if direction == "LONG" else "v"
        print(f"  {arrow} [{sig['strategy']}] {sig['symbol']} "
              f"{direction} @ ${sig['entry_price']:.2f} "
              f"conf={sig['confidence']:.2f} RR={sig['risk_reward']:.1f} "
              f"-- {sig['reason']}")

    # Summary by strategy
    from collections import Counter
    strat_counts = Counter(s["strategy"] for s in signals)
    print(f"\nBy strategy:")
    for strat, count in strat_counts.most_common():
        print(f"  {strat}: {count} signals")
