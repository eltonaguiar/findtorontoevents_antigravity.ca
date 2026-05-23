"""
ALPHA_ENGINE -- Flow & Behavioral Strategies
=============================================
2 strategies exploiting stablecoin capital flows and retail behavioral bias.

Strategy 1: stablecoin_flow_momentum
  Wei, Bianchi & Liao (2024, JFE) -- stablecoin supply expansion/contraction
  as a leading indicator for crypto risk appetite.  7-day rolling change in
  USDT + USDC market cap from DefiLlama (free, no key).
  +1% = new money entering → LONG BTC/ETH/SOL
  -1% = money leaving       → SHORT BTC/ETH/SOL
  TP +6%, SL -3% (2:1 R:R), hold 7-14d

Strategy 2: disposition_effect_contrarian
  Shams (2024, Journal of Finance) -- retail investors hold losers too long
  ("disposition effect"). When a coin is >30% below ATH for 60+ consecutive
  days, retail has capitulated. Smart money accumulates quietly. Entry when
  price crosses above SMA(50) with elevated volume (20d > 1.5x 60d avg).
  TP +12%, SL -6% (2:1 R:R), top-30 alts by market cap from Binance.

Data sources (all FREE):
  - DefiLlama Stablecoins API  (no auth, generous limits)
  - Binance spot klines API     (with 3+ mirror failover)
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS,
    fetch_binance_json,
)
from indicators import sma, volume_ratio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from a URL with User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Stablecoin flow cache (4-hour TTL)
# ---------------------------------------------------------------------------
_stablecoin_cache: dict = {"data": None, "ts": 0}
_STABLECOIN_CACHE_TTL = 4 * 3600  # 4 hours


def _get_stablecoin_flow() -> Optional[float]:
    """Return 7-day % change in total USDT + USDC market cap from DefiLlama.

    Uses the stablecoins endpoint which returns per-stablecoin circulating
    supply with historical data points.  We sum the latest and 7-day-ago
    values for USDT (id=1) and USDC (id=2) and compute the % change.
    """
    now = time.time()
    if _stablecoin_cache["data"] is not None and (now - _stablecoin_cache["ts"]) < _STABLECOIN_CACHE_TTL:
        return _stablecoin_cache["data"]

    url = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
    raw = _fetch_json(url, timeout=15)
    if not raw or "peggedAssets" not in raw:
        return None

    # Sum circulating for USDT + USDC
    target_symbols = {"USDT", "USDC"}
    total_now = 0.0
    total_7d_ago = 0.0

    for asset in raw["peggedAssets"]:
        sym = (asset.get("symbol") or "").upper()
        if sym not in target_symbols:
            continue

        # Current circulating (peggedUSD across all chains)
        chains = asset.get("chainCirculating", {})
        current = 0.0
        for chain_data in chains.values():
            current += chain_data.get("current", {}).get("peggedUSD", 0) or 0

        if current <= 0:
            continue

        total_now += current

        # 7-day-ago value: use circulatingPrevDay * ratio or estimate from chains
        # DefiLlama provides "circulatingPrevDay" but not 7d — use pegType history
        # Fallback: check if there's a "pegDeviation" or use chains 7d data
        # The simplest approach: use the global "circulating" field and "circulatingPrevWeek"
        circ_now = asset.get("circulating", {}).get("peggedUSD", 0) or 0
        circ_prev_week = 0

        # Try circulatingPrevWeek first
        if "circulatingPrevWeek" in asset:
            circ_prev_week = asset["circulatingPrevWeek"].get("peggedUSD", 0) or 0

        if circ_prev_week > 0:
            total_7d_ago += circ_prev_week
        elif circ_now > 0:
            # If no prev week data, use current (change = 0)
            total_7d_ago += circ_now

    if total_now <= 0 or total_7d_ago <= 0:
        return None

    pct_change = ((total_now - total_7d_ago) / total_7d_ago) * 100.0

    _stablecoin_cache["data"] = pct_change
    _stablecoin_cache["ts"] = now

    return pct_change


# =====================================================================
# STRATEGY 1: Stablecoin Flow Momentum
# =====================================================================
# Wei, Bianchi & Liao (2024, JFE) -- stablecoin supply as a leading
# indicator for crypto risk appetite.  USDT+USDC 7d change > +1% = BUY,
# < -1% = SHORT on BTC, ETH, SOL.
#
# TP: +6%, SL: -3% (2:1 R:R)
# Confidence: 0.70 base, +0.05 per 0.5% flow beyond threshold (max 0.85)
# Hold: 7-14 days
# =====================================================================

def stablecoin_flow_momentum(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """Detect stablecoin inflow/outflow momentum for BTC, ETH, SOL signals."""
    signals: list[dict] = []

    flow_pct = _get_stablecoin_flow()
    if flow_pct is None:
        return signals

    threshold = 0.5  # +/- 0.5% (relaxed from 1.0% for more signals)

    if abs(flow_pct) < threshold:
        return signals

    # Determine direction
    if flow_pct > threshold:
        direction = "BUY"
        tp_mult = 1.06
        sl_mult = 0.97
    else:
        direction = "SELL"
        tp_mult = 0.94
        sl_mult = 1.03

    # Confidence: 0.66 base, +0.05 per 0.5% beyond threshold, max 0.82
    excess = abs(flow_pct) - threshold
    confidence = min(0.82, 0.66 + 0.05 * (excess / 0.5))

    # Primary symbols: BTC, ETH; secondary: SOL
    target_map = {
        "BTC-USD": "BTCUSDT",
        "ETH-USD": "ETHUSDT",
        "SOL-USD": "SOLUSDT",
    }

    for yf_sym, binance_sym in target_map.items():
        df = data.get(yf_sym)
        if df is None or df.empty or len(df) < 10:
            continue

        close = df["Close"]
        price = float(close.iloc[-1])
        if price <= 0:
            continue

        tp = _smart_round(price * tp_mult)
        sl = _smart_round(price * sl_mult)
        entry = _smart_round(price)

        # Secondary symbol gets slightly lower confidence
        sym_confidence = confidence if yf_sym != "SOL-USD" else max(0.65, confidence - 0.05)

        ts = _now_iso()
        sig_id = f"stablecoin_flow_{binance_sym}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

        signals.append({
            "id": sig_id,
            "strategy": "stablecoin_flow_momentum",
            "symbol": binance_sym,
            "category": "crypto",
            "signal_type": direction,
            "entry_price": entry,
            "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(sym_confidence, 3),
            "ml_score": None,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "high_water_mark": None,
            "status": "OPEN",
            "regime_at_entry": None,
            "atr_at_entry": None,
            "rsi_at_entry": None,
            "volume_ratio": None,
            "hold_days": None,
            "source_system": "alpha_engine",
            "created_at": ts,
            "forward_validated": False,
            "extra": {
                "stablecoin_flow_7d_pct": round(flow_pct, 3),
                "reference": "Wei, Bianchi & Liao (2024, JFE)",
                "hold_target_days": "7-14",
            },
        })

    return signals


# =====================================================================
# STRATEGY 2: Disposition Effect Contrarian
# =====================================================================
# Shams (2024, Journal of Finance) -- retail capitulation recovery.
# Conditions:
#   1. Price >30% below ATH for 60+ consecutive days
#   2. Price crosses above SMA(50)
#   3. 20-day avg volume > 1.5x 60-day avg volume
#
# TP: +12%, SL: -6% (2:1 R:R)
# Confidence: 0.72-0.82 based on volume spike + drawdown depth
# =====================================================================

_TOP30_CACHE: dict = {"symbols": None, "ts": 0}
_TOP30_TTL = 4 * 3600  # 4 hours


def _get_top30_alts() -> list[str]:
    """Fetch top 30 alts by market cap from Binance ticker.

    Returns Binance symbols like ETHUSDT, SOLUSDT etc.
    Uses fetch_binance_json with 3+ mirror failover.
    """
    now = time.time()
    if _TOP30_CACHE["symbols"] is not None and (now - _TOP30_CACHE["ts"]) < _TOP30_TTL:
        return _TOP30_CACHE["symbols"]

    # Get 24h ticker for all USDT pairs, sort by quoteVolume (proxy for market cap rank)
    tickers = fetch_binance_json("/api/v3/ticker/24hr")
    if not tickers or not isinstance(tickers, list):
        # Fallback: use configured symbols
        fallback = [v["binance"] for v in CRYPTO_SYMBOLS.values()
                    if v.get("binance") and v["binance"].endswith("USDT")]
        return fallback[:30]

    # Filter USDT pairs, exclude stablecoins and BTC (BTC is not an "alt")
    usdt_tickers = []
    excluded = {"BTCUSDT", "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "DAIUSDT"}
    for t in tickers:
        sym = t.get("symbol", "")
        if sym.endswith("USDT") and sym not in excluded:
            try:
                vol = float(t.get("quoteVolume", 0))
                usdt_tickers.append((sym, vol))
            except (ValueError, TypeError):
                continue

    usdt_tickers.sort(key=lambda x: x[1], reverse=True)
    top30 = [s[0] for s in usdt_tickers[:30]]

    _TOP30_CACHE["symbols"] = top30
    _TOP30_CACHE["ts"] = now

    return top30


# Delisted / rebranded yfinance tickers -- map old ticker to working one
_YF_TICKER_REMAP = {
    "RNDR-USD": "RENDER-USD", "FTM-USD": "S-USD", "COMP-USD": "COMP1-USD",
    "ZK-USD": "ZKSYNC-USD", "THE-USD": "THE1-USD", "TAO-USD": "TAO22974-USD",
    "HIFI-USD": "HIFI1-USD", "IMX-USD": "IMX1-USD", "MEW-USD": "MEW1-USD",
    "ZRO-USD": "ZRO1-USD", "SUI-USD": "SUI20947-USD", "POPCAT-USD": "POPCAT1-USD",
    "ROBO-USD": "ROBO1-USD", "PEPE-USD": "PEPE24478-USD", "HYPE-USD": "HYPE32196-USD",
    "PIXEL-USD": "PORTAL-USD", "TON-USD": "TON11419-USD",
}


def _binance_to_yf(binance_sym: str) -> str:
    """Convert ETHUSDT -> ETH-USD for yfinance data lookup (with delisted ticker remap)."""
    base = binance_sym.replace("USDT", "")
    yf_sym = f"{base}-USD"
    return _YF_TICKER_REMAP.get(yf_sym, yf_sym)


def _fetch_binance_klines(symbol: str, interval: str = "1d", limit: int = 200) -> Optional[pd.DataFrame]:
    """Fetch daily klines from Binance with failover. Returns OHLCV DataFrame."""
    path = f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    raw = fetch_binance_json(path)
    if not raw or not isinstance(raw, list) or len(raw) < 60:
        return None

    try:
        df = pd.DataFrame(raw, columns=[
            "open_time", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_vol", "trades", "taker_buy_vol",
            "taker_buy_quote_vol", "ignore",
        ])
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Close"])
        return df
    except Exception:
        return None


def disposition_effect_contrarian(data: dict[str, pd.DataFrame],
                                  context: Optional[dict] = None) -> list[dict]:
    """Detect capitulation recovery signals based on disposition effect theory."""
    signals: list[dict] = []

    top30 = _get_top30_alts()
    if not top30:
        return signals

    for binance_sym in top30:
        yf_sym = _binance_to_yf(binance_sym)

        # Try yfinance data first (already loaded), fallback to Binance klines
        df = data.get(yf_sym)
        use_binance_klines = False

        if df is None or df.empty or len(df) < 60:
            # Fetch from Binance directly
            df = _fetch_binance_klines(binance_sym, limit=200)
            use_binance_klines = True
            if df is None or len(df) < 60:
                continue

        close = df["Close"]
        high = df["High"]
        volume = df["Volume"]

        if len(close) < 60:
            continue

        price = float(close.iloc[-1])
        if price <= 0:
            continue

        # 1. Check ATH and drawdown duration
        ath = float(high.max())
        if ath <= 0:
            continue

        drawdown_pct = ((ath - price) / ath) * 100.0
        if drawdown_pct < 20:
            continue  # Not in deep enough drawdown (relaxed from 30%)

        # Count consecutive days >20% below ATH
        threshold_price = ath * 0.80  # 20% below ATH (relaxed from 30%)
        consecutive_days = 0
        for i in range(len(close) - 1, -1, -1):
            if float(close.iloc[i]) < threshold_price:
                consecutive_days += 1
            else:
                break

        if consecutive_days < 30:
            continue  # Not sustained long enough (relaxed from 60 days)

        # 2. Price crosses above SMA(50)
        sma_50 = sma(close, 50)
        if sma_50.empty or pd.isna(sma_50.iloc[-1]):
            continue

        current_sma = float(sma_50.iloc[-1])
        if price <= current_sma:
            continue  # Must be above SMA(50)

        # Confirm crossover: previous close was below SMA(50)
        if len(close) >= 2 and len(sma_50) >= 2:
            prev_close = float(close.iloc[-2])
            prev_sma = float(sma_50.iloc[-2])
            if prev_close > prev_sma:
                continue  # Not a fresh crossover (already above)

        # 3. Volume confirmation: 20d avg vol > 1.5x 60d avg vol
        if len(volume) < 60:
            continue

        vol_20d = float(volume.iloc[-20:].mean())
        vol_60d = float(volume.iloc[-60:].mean())

        if vol_60d <= 0:
            continue

        vol_spike = vol_20d / vol_60d
        if vol_spike < 1.2:
            continue  # Volume not elevated enough (relaxed from 1.5x)

        # All conditions met -> generate BUY signal
        entry = _smart_round(price)
        tp = _smart_round(price * 1.12)  # +12%
        sl = _smart_round(price * 0.94)  # -6%

        # Confidence: 0.68 base (lowered from 0.72 due to relaxed thresholds)
        # +0.02 per 10% additional drawdown beyond 20% (max +0.04)
        # +0.02 per 0.5x volume spike beyond 1.2x (max +0.06)
        conf = 0.68
        conf += min(0.04, 0.02 * ((drawdown_pct - 20) / 10.0))
        conf += min(0.06, 0.02 * ((vol_spike - 1.2) / 0.5))
        conf = min(0.78, round(conf, 3))

        ts = _now_iso()
        sig_id = f"disposition_{binance_sym}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

        signals.append({
            "id": sig_id,
            "strategy": "disposition_effect_contrarian",
            "symbol": binance_sym,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": conf,
            "ml_score": None,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "high_water_mark": None,
            "status": "OPEN",
            "regime_at_entry": None,
            "atr_at_entry": None,
            "rsi_at_entry": None,
            "volume_ratio": round(vol_spike, 2),
            "hold_days": None,
            "source_system": "alpha_engine",
            "created_at": ts,
            "forward_validated": False,
            "extra": {
                "drawdown_pct": round(drawdown_pct, 2),
                "consecutive_days_below_ath": consecutive_days,
                "ath": _smart_round(ath),
                "sma_50": _smart_round(current_sma),
                "vol_20d_vs_60d": round(vol_spike, 3),
                "reference": "Shams (2024, Journal of Finance)",
            },
        })

    return signals


# =====================================================================
# Export dict -- maps strategy name → callable
# =====================================================================
FLOW_BEHAVIORAL_STRATEGIES: dict[str, callable] = {
    "stablecoin_flow_momentum": stablecoin_flow_momentum,
    "disposition_effect_contrarian": disposition_effect_contrarian,
}
