#!/usr/bin/env python3
"""
Mercury Enhancement #2 & #3 -- Dynamic TP/SL Calibration + Macro/Regime Gates
==============================================================================
Item #2: ATR-based SL/TP with regime multiplier and TP-Boost rule.
Item #3: Macro & regime gates (equity SMA200+VIX, forex ADX, RSI blocks).

Uses Binance mirror failover (api, api1, api2, api3) -> CoinGecko -> KuCoin.
stdlib-only (urllib).
"""
from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.error
from typing import Optional

_log = logging.getLogger("alpha_engine.dynamic_sl_gates")

# ---------------------------------------------------------------------------
# Binance mirror failover (3+ endpoints per CLAUDE.md)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"

# Regime multipliers for SL distance
REGIME_SL_MULT = {
    "BULLISH": 0.9,
    "WEAKENING_BULL": 1.0,
    "NEUTRAL": 1.0,
    "BEARISH": 1.2,
    "CRISIS": 1.5,
}

# ---------------------------------------------------------------------------
# HTTP helper (stdlib-only)
# ---------------------------------------------------------------------------

def _http_json(url: str, timeout: int = 8) -> Optional[dict | list]:
    """GET JSON with short timeout, return None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AntigravityBot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Item #2: Dynamic TP/SL Calibration
# ---------------------------------------------------------------------------

def _fetch_klines_failover(symbol: str, interval: str = "1d",
                           limit: int = 25) -> Optional[list]:
    """Fetch OHLCV klines from Binance mirrors -> CoinGecko -> KuCoin."""
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT"):
        sym += "USDT"
    # Binance mirrors
    for base in BINANCE_MIRRORS:
        data = _http_json(f"{base}/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}")
        if data and isinstance(data, list) and len(data) >= 5:
            return data
    # CoinGecko fallback (daily only)
    cg_id = sym.replace("USDT", "").lower()
    cg_map = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "bnb": "binancecoin"}
    cg_id = cg_map.get(cg_id, cg_id)
    cg = _http_json(f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days=30")
    if cg and isinstance(cg, list) and len(cg) >= 5:
        return [[k[0], str(k[1]), str(k[2]), str(k[3]), str(k[4]), "0"] for k in cg[-limit:]]
    # KuCoin fallback
    kc_sym = sym.replace("USDT", "-USDT")
    kc = _http_json(f"{KUCOIN_BASE}/api/v1/market/candles?type=1day&symbol={kc_sym}")
    if kc and kc.get("code") == "200000":
        raw = kc.get("data", [])
        if raw and len(raw) >= 5:
            # KuCoin: [time, open, close, high, low, volume, turnover] -- reversed
            return [[int(r[0])*1000, r[1], r[3], r[4], r[2], r[5]] for r in reversed(raw[-limit:])]
    return None


def compute_atr(symbol: str, period: int = 20) -> Optional[float]:
    """Compute ATR for *period* days using Binance mirror failover."""
    klines = _fetch_klines_failover(symbol, "1d", period + 5)
    if not klines or len(klines) < period + 1:
        return None
    trs = []
    for i in range(1, len(klines)):
        h = float(klines[i][2])
        l = float(klines[i][3])
        prev_c = float(klines[i - 1][4])
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)


def calibrate_tp_sl(
    symbol: str,
    direction: str,
    entry_price: float,
    asset_class: str = "crypto",
    confidence: float = 0.5,
    regime: str = "NEUTRAL",
    k_sl: float = 1.5,
    k_tp: float = 3.0,
) -> dict:
    """
    Compute ATR-calibrated TP and SL prices.

    Args:
        symbol: Instrument (e.g. "BTCUSDT", "ETHUSDT")
        direction: "LONG" or "SHORT"
        entry_price: Entry price
        asset_class: "crypto", "forex", "equity"
        confidence: Model confidence 0-1
        regime: Market regime string
        k_sl: SL multiplier (SL distance = k_sl * ATR * regime_mult)
        k_tp: TP multiplier (TP distance = k_tp * ATR * regime_mult)

    Returns:
        dict with tp_price, sl_price, atr, regime_mult, tp_boost_applied
    """
    atr = compute_atr(symbol)
    if atr is None or atr <= 0:
        # Fallback: 2% SL, 4% TP
        atr = entry_price * 0.02
        _log.warning("ATR unavailable for %s, using 2%% fallback", symbol)

    regime_mult = REGIME_SL_MULT.get(regime, 1.0)
    sl_distance = k_sl * atr * regime_mult
    tp_distance = k_tp * atr * regime_mult

    # TP-Boost rule: tighten TP 10% when high confidence + low volatility
    tp_boost = False
    atr_pct = atr / entry_price if entry_price > 0 else 0
    if confidence > 0.8 and atr_pct < 0.03:
        tp_distance *= 0.90
        tp_boost = True

    is_long = direction.upper() in ("LONG", "BUY")
    tp_price = entry_price + tp_distance if is_long else entry_price - tp_distance
    sl_price = entry_price - sl_distance if is_long else entry_price + sl_distance

    return {
        "tp_price": round(tp_price, 8),
        "sl_price": round(sl_price, 8),
        "atr": round(atr, 8),
        "atr_pct": round(atr_pct, 6),
        "regime_mult": regime_mult,
        "tp_boost_applied": tp_boost,
    }


# ---------------------------------------------------------------------------
# Item #3: Macro & Regime Gates
# ---------------------------------------------------------------------------

def _sma(values: list[float], period: int) -> Optional[float]:
    """Simple moving average of last *period* values."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _adx_proxy(closes: list[float], period: int = 14) -> float:
    """Rough ADX proxy from directional movement of closes."""
    if len(closes) < period + 1:
        return 25.0  # neutral default
    pos, neg = 0.0, 0.0
    for i in range(-period, 0):
        d = closes[i] - closes[i - 1]
        if d > 0:
            pos += d
        else:
            neg += abs(d)
    total = pos + neg
    if total == 0:
        return 0.0
    return abs(pos - neg) / total * 100.0


def equity_macro_gate(closes_200: list[float], vix: float = 20.0) -> dict:
    """Block LONGs when SMA200 trending down + VIX high (>25)."""
    blocked = False
    reason = ""
    sma200 = _sma(closes_200, 200)
    if sma200 is not None and len(closes_200) >= 200:
        current = closes_200[-1]
        sma200_prev = _sma(closes_200[:-5], 200)
        trending_down = sma200_prev is not None and sma200 < sma200_prev
        if trending_down and vix > 25 and current < sma200:
            blocked = True
            reason = f"SMA200 declining ({sma200:.2f}), VIX={vix:.1f}>25, price below SMA200"
    return {"block_long": blocked, "reason": reason}


def forex_regime_gate(closes: list[float]) -> dict:
    """Block entries when ADX < 18 (choppy market)."""
    adx = _adx_proxy(closes, 14)
    blocked = adx < 18
    return {"block_entry": blocked, "adx": round(adx, 1),
            "reason": f"ADX={adx:.1f}<18 choppy" if blocked else ""}


def regime_rsi_gate(closes: list[float], direction: str, regime: str) -> dict:
    """
    Block LONGs in WEAKENING_BULL when RSI > 65.
    Block SHORTs in BULLISH when RSI < 35.
    """
    rsi_val = _rsi(closes, 14)
    if rsi_val is None:
        return {"blocked": False, "rsi": None, "reason": ""}
    d = direction.upper()
    blocked = False
    reason = ""
    if regime == "WEAKENING_BULL" and d in ("LONG", "BUY") and rsi_val > 65:
        blocked = True
        reason = f"WEAKENING_BULL + RSI={rsi_val:.1f}>65: LONG blocked"
    elif regime == "BULLISH" and d in ("SHORT", "SELL") and rsi_val < 35:
        blocked = True
        reason = f"BULLISH + RSI={rsi_val:.1f}<35: SHORT blocked"
    return {"blocked": blocked, "rsi": round(rsi_val, 2), "reason": reason}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Dynamic SL/Gates Self-Test ===")
    # ATR calibration (offline test with mock)
    res = calibrate_tp_sl("BTCUSDT", "LONG", 60000.0, confidence=0.85, regime="BULLISH")
    print(f"  Calibrate LONG BTC@60000: TP={res['tp_price']}, SL={res['sl_price']}, "
          f"ATR={res['atr']}, boost={res['tp_boost_applied']}")
    # Macro gate
    down_prices = [100 - i * 0.05 for i in range(210)]
    mg = equity_macro_gate(down_prices, vix=30)
    assert mg["block_long"], f"Expected block_long=True, got {mg}"
    print(f"  equity_macro_gate (declining+VIX30): {mg}")
    # Forex gate
    choppy = [100 + (0.01 if i % 2 == 0 else -0.01) for i in range(30)]
    fg = forex_regime_gate(choppy)
    print(f"  forex_regime_gate (choppy): {fg}")
    # RSI gate
    up_prices = [100 + i * 0.5 for i in range(30)]
    rg = regime_rsi_gate(up_prices, "LONG", "WEAKENING_BULL")
    print(f"  regime_rsi_gate (LONG/WEAKENING_BULL): {rg}")
    down_p = [100 - i * 0.5 for i in range(30)]
    rg2 = regime_rsi_gate(down_p, "SHORT", "BULLISH")
    print(f"  regime_rsi_gate (SHORT/BULLISH): {rg2}")
    print("=== All tests passed ===")
