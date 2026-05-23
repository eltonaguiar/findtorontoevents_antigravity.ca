#!/usr/bin/env python3
"""
Regime-Strategy Router
======================
Prevents strategy-regime mismatches that destroy PnL.

Core insight (KIMI Research, Feb 26 2026):
  'The single change that would most improve win rate: implement a
   strict regime-strategy router. Systems are running short-oriented
   strategies during panic (F&G <= 15) and getting destroyed.'

Usage:
    from cross_aggregation.regime_router import should_generate_signal, get_current_regime

    regime = get_current_regime()
    if should_generate_signal("LONG", regime):
        # proceed with pick
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone


# ── Fear & Greed API ────────────────────────────────────────────
FNG_URL = "https://api.alternative.me/fng/?limit=1"

# ── Binance public klines (no auth needed) ──────────────────────
# 4h candles, last 60 bars = 10 days (enough for 50-period EMA)
BINANCE_KLINES_URLS = [
    "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60",
    "https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60",
    "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60",
    "https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60",
]
# Legacy single URL (kept for backward compat)
BINANCE_KLINES_URL = BINANCE_KLINES_URLS[0]
# Bybit fallback (Binance may be geo-blocked in CI)
BYBIT_KLINES_URL = "https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=240&limit=60"

# ── BTC dominance (CoinGecko global) ───────────────────────────
CG_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"


def _fetch_fng() -> int | None:
    """Fetch current Fear & Greed index (0-100) from alternative.me."""
    try:
        req = urllib.request.Request(FNG_URL, headers={"User-Agent": "RegimeRouter/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        return int(data["data"][0]["value"])
    except Exception as e:
        print(f"  [WARN] F&G fetch failed: {e}", file=sys.stderr)
        return None


def _compute_ema(closes: list[float], period: int) -> list[float]:
    """Compute EMA over a list of close prices. Returns list same length as input."""
    if not closes or period < 1:
        return []
    k = 2.0 / (period + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(closes[i] * k + ema[-1] * (1 - k))
    return ema


def _compute_adx(highs: list[float], lows: list[float], closes: list[float],
                 period: int = 14) -> float | None:
    """Compute latest ADX value from OHLC data. Returns 0-100 or None."""
    n = len(closes)
    if n < period + 1:
        return None

    # True Range, +DM, -DM
    tr_list, pdm_list, ndm_list = [], [], []
    for i in range(1, n):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        tr_list.append(max(h - l, abs(h - pc), abs(l - pc)))
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        pdm_list.append(up if up > down and up > 0 else 0)
        ndm_list.append(down if down > up and down > 0 else 0)

    # Wilder smoothing (first value = simple sum, then: prev - prev/period + current)
    def _wilder_smooth(vals: list[float], p: int) -> list[float]:
        if len(vals) < p:
            return []
        smoothed = [sum(vals[:p])]
        for i in range(p, len(vals)):
            smoothed.append(smoothed[-1] - smoothed[-1] / p + vals[i])
        return smoothed

    atr = _wilder_smooth(tr_list, period)
    smooth_pdm = _wilder_smooth(pdm_list, period)
    smooth_ndm = _wilder_smooth(ndm_list, period)

    if not atr or not smooth_pdm or not smooth_ndm:
        return None

    # +DI, -DI, DX
    dx_list = []
    for i in range(len(atr)):
        if atr[i] == 0:
            continue
        pdi = 100 * smooth_pdm[i] / atr[i]
        ndi = 100 * smooth_ndm[i] / atr[i]
        denom = pdi + ndi
        if denom > 0:
            dx_list.append(100 * abs(pdi - ndi) / denom)

    if len(dx_list) < period:
        return None

    # ADX = Wilder-smoothed DX
    adx_smooth = _wilder_smooth(dx_list, period)
    return adx_smooth[-1] if adx_smooth else None


def _fetch_btc_candles() -> list[dict] | None:
    """Fetch BTC 4h candles. Returns list of {open, high, low, close} dicts.

    Tries Binance first, falls back to Bybit if geo-blocked.
    """
    # --- Binance (try all endpoints) ---
    for _burl in BINANCE_KLINES_URLS:
        try:
            req = urllib.request.Request(_burl,
                                         headers={"User-Agent": "RegimeRouter/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode())
            if isinstance(raw, list) and len(raw) > 20:
                return [
                    {"open": float(c[1]), "high": float(c[2]),
                     "low": float(c[3]), "close": float(c[4])}
                    for c in raw
                ]
        except Exception as e:
            print(f"  [WARN] Binance klines failed ({_burl}): {e}", file=sys.stderr)
            continue

    # --- Bybit fallback ---
    try:
        req = urllib.request.Request(BYBIT_KLINES_URL,
                                     headers={"User-Agent": "RegimeRouter/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("retCode") == 0:
            raw_list = data["result"]["list"]
            # Bybit returns newest first, reverse for chronological order
            raw_list = list(reversed(raw_list))
            return [
                {"open": float(c[1]), "high": float(c[2]),
                 "low": float(c[3]), "close": float(c[4])}
                for c in raw_list
            ]
    except Exception as e:
        print(f"  [WARN] Bybit klines failed: {e}", file=sys.stderr)

    return None


def _fetch_btc_dominance_trend() -> str:
    """Fetch BTC dominance trend from CoinGecko global endpoint.

    Returns 'UP', 'DOWN', or 'NEUTRAL'.
    We check btc_dominance_change_24h — positive = UP, negative = DOWN.
    """
    try:
        req = urllib.request.Request(CG_GLOBAL_URL,
                                     headers={"User-Agent": "RegimeRouter/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        change = data.get("data", {}).get("market_cap_change_percentage_24h_usd", 0)
        btc_dom = data.get("data", {}).get("market_cap_percentage", {}).get("btc", 50)

        # Use btc_dom > 55 trending up, < 48 trending down as rough proxy
        # Combined with 24h change direction
        if change > 1.0 or btc_dom > 55:
            return "UP"
        elif change < -1.0 or btc_dom < 48:
            return "DOWN"
        return "NEUTRAL"
    except Exception as e:
        print(f"  [WARN] BTC dominance fetch failed: {e}", file=sys.stderr)
        return "NEUTRAL"


def _compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Compute latest RSI-14 from close prices. Returns 0-100 or None."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    # Wilder smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 1)


def _derive_regime(candles: list[dict]) -> tuple[str, float | None, float | None]:
    """Derive market regime from 4h candle data.

    Returns (regime_str, adx_value, rsi_value):
      - 'TRENDING_UP'   if EMA20 > EMA50
      - 'TRENDING_DOWN' if EMA20 < EMA50
      - 'RANGE_BOUND'   if ADX < 20 (overrides EMA signal)
      - RSI-14 added as 4th signal for momentum exhaustion detection
    """
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    ema20 = _compute_ema(closes, 20)
    ema50 = _compute_ema(closes, 50)
    adx = _compute_adx(highs, lows, closes, 14)
    rsi = _compute_rsi(closes, 14)

    if not ema20 or not ema50:
        return "UNKNOWN", None, rsi

    latest_ema20 = ema20[-1]
    latest_ema50 = ema50[-1]

    # ADX < 20 means no trend — range-bound regardless of EMA
    if adx is not None and adx < 20:
        return "RANGE_BOUND", round(adx, 1), rsi

    if latest_ema20 > latest_ema50:
        return "TRENDING_UP", round(adx, 1) if adx else None, rsi
    else:
        return "TRENDING_DOWN", round(adx, 1) if adx else None, rsi


# ── Public API ──────────────────────────────────────────────────

def get_current_regime() -> dict:
    """Fetch all regime data and return a unified regime dict.

    Returns:
        {
            "fng": 11,
            "fng_classification": "Extreme Fear",
            "regime": "TRENDING_DOWN",
            "adx": 25.3,
            "btc_dom_trend": "UP",
            "shorts_allowed": False,
            "longs_allowed": True,
            "timestamp": "2026-02-26T12:00:00Z"
        }
    """
    fng = _fetch_fng()
    candles = _fetch_btc_candles()

    regime = "UNKNOWN"
    adx = None
    rsi = None
    if candles and len(candles) >= 50:
        regime, adx, rsi = _derive_regime(candles)

    btc_dom = _fetch_btc_dominance_trend()

    # Pre-compute allowed directions for logging/dashboard
    shorts_allowed = should_generate_signal("SHORT", fng, regime, btc_dom, rsi)
    longs_allowed = should_generate_signal("LONG", fng, regime, btc_dom, rsi)

    # F&G classification
    if fng is None:
        fng_class = "Unknown"
    elif fng <= 15:
        fng_class = "Extreme Fear"
    elif fng <= 30:
        fng_class = "Fear"
    elif fng <= 50:
        fng_class = "Neutral"
    elif fng <= 80:
        fng_class = "Greed"
    else:
        fng_class = "Extreme Greed"

    return {
        "fng": fng,
        "fng_classification": fng_class,
        "regime": regime,
        "adx": adx,
        "rsi_14": rsi,
        "btc_dom_trend": btc_dom,
        "shorts_allowed": shorts_allowed,
        "longs_allowed": longs_allowed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def should_generate_signal(direction: str, fng: int | None = None,
                           regime: str = "UNKNOWN",
                           btc_dom_trend: str = "NEUTRAL",
                           rsi: float | None = None) -> bool:
    """Returns True only if strategy direction is aligned with the current regime.

    This is the core gate that prevents strategy-regime mismatches.
    v2.0: Added RSI-14 as 4th signal for momentum exhaustion detection.

    Args:
        direction: 'LONG' or 'SHORT'
        fng: Fear & Greed index 0-100 (None = unknown, treated as 50)
        regime: 'TRENDING_UP', 'TRENDING_DOWN', 'RANGE_BOUND', or 'UNKNOWN'
        btc_dom_trend: 'UP', 'DOWN', or 'NEUTRAL'
        rsi: RSI-14 value (0-100, None = unknown)

    Returns:
        True if the direction is allowed in the current regime.
    """
    direction = direction.upper()
    if direction not in ("LONG", "SHORT"):
        return False

    # If we can't determine regime, allow everything (fail open)
    if fng is None and regime == "UNKNOWN":
        return True

    fng_val = fng if fng is not None else 50
    PANIC = fng_val < 20
    EUPHORIA = fng_val > 80

    # RSI context (4th signal — momentum exhaustion detection)
    rsi_val = rsi if rsi is not None else 50.0
    RSI_OVERBOUGHT = rsi_val > 70
    RSI_OVERSOLD = rsi_val < 30

    if direction == "SHORT":
        # RULE 1: Never short during panic — this kills all current losses
        if PANIC:
            return False

        # RULE 1b (NEW): Never short when RSI is oversold — momentum exhaustion
        if RSI_OVERSOLD:
            return False

        # RULE 2: Short allowed in euphoria + trending up (distribution top)
        if EUPHORIA and regime == "TRENDING_UP":
            return True

        # RULE 2b (NEW): Short allowed when RSI overbought + downtrend starting
        # RSI > 70 in a downtrend = bearish divergence, strong short signal
        if RSI_OVERBOUGHT and regime == "TRENDING_DOWN":
            return True

        # RULE 3: Short allowed in downtrend when NOT panicking
        if regime == "TRENDING_DOWN" and not PANIC:
            return True

        # RULE 4: Range-bound — allow shorts only when F&G > 50 (slight greed)
        if regime == "RANGE_BOUND" and fng_val > 50:
            return True

        # Default: block shorts in uncertain conditions
        return False

    if direction == "LONG":
        # RULE 1: Panic longs — single best signal (contrarian entry)
        if PANIC:
            return True

        # RULE 1b (NEW): Block longs when RSI overbought + euphoria (double top risk)
        if RSI_OVERBOUGHT and EUPHORIA:
            return False

        # RULE 2: Trending up + not euphoric — bread and butter
        if regime == "TRENDING_UP" and not EUPHORIA:
            return True

        # RULE 2b (NEW): Boost longs when RSI oversold in uptrend (pullback buy)
        # This is a high-edge signal: trend is up but RSI shows temporary weakness
        if RSI_OVERSOLD and regime == "TRENDING_UP":
            return True

        # RULE 3: Range-bound — allow longs when F&G < 50 (slight fear = value)
        if regime == "RANGE_BOUND" and fng_val < 50:
            return True

        # RULE 3b (NEW): Range-bound + RSI oversold = value entry
        if regime == "RANGE_BOUND" and RSI_OVERSOLD:
            return True

        # RULE 4: Extreme greed — block longs (distribution phase)
        if EUPHORIA:
            return False

        # RULE 5: Trending down + not panic — block longs (don't catch knives)
        if regime == "TRENDING_DOWN" and not PANIC:
            return False

        # Default: allow in unknown/neutral
        return True

    return False


def get_regime_rr_cap(regime: str = "UNKNOWN") -> float:
    """Get maximum R:R ratio for current regime (Vince 2000).

    Ranging markets need tight TP (1.2x), trending allows wider.
    """
    caps = {
        "RANGE_BOUND": 1.2,
        "TRENDING_UP": 1.5,
        "TRENDING_DOWN": 2.0,  # Shorts in downtrend can run further
        "UNKNOWN": 1.5,
    }
    return caps.get(regime, 1.5)


def get_market_context() -> dict:
    """Get unified market context for all scoring systems.

    Returns a dict with regime info plus scoring multipliers that
    any system can consume directly.
    """
    regime = get_current_regime()
    r_str = regime.get("regime", "UNKNOWN")
    adx = regime.get("adx")

    regime["rr_cap"] = get_regime_rr_cap(r_str)
    regime["direction_bias"] = (
        "SHORT" if r_str == "TRENDING_DOWN"
        else "LONG" if r_str == "TRENDING_UP"
        else "NEUTRAL"
    )
    regime["adx_strong"] = adx is not None and adx >= 15
    return regime


def filter_picks(picks: list[dict], regime: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Filter a list of picks through the regime router.

    Args:
        picks: list of pick dicts (must have 'direction' and optionally 'symbol')
        regime: pre-fetched regime dict (if None, will fetch fresh)

    Returns:
        (passed, filtered) — two lists of picks
    """
    if regime is None:
        regime = get_current_regime()

    fng = regime.get("fng")
    reg = regime.get("regime", "UNKNOWN")
    btc_dom = regime.get("btc_dom_trend", "NEUTRAL")
    rsi = regime.get("rsi_14")

    passed = []
    filtered = []

    for pick in picks:
        direction = pick.get("direction", "").upper()
        if not direction:
            passed.append(pick)  # Can't determine direction, pass through
            continue

        # Only apply regime filter to crypto symbols
        sym = (pick.get("symbol") or pick.get("pair") or "").upper()
        is_crypto = sym.endswith("USDT") or sym.endswith("BTC") or sym.endswith("ETH")

        # TODO(2026-05-14 swarm audit P3-lite): Add non-crypto regime protection.
        # Currently FOREX/EQUITY/COMMODITY picks pass through unfiltered.
        # Needs: VIX data source (for EQUITY), DXY trend (for FOREX/COMMODITY),
        # COT positioning (for COMMODITY). Until then, tag non-crypto picks
        # with a neutral regime_filtered=False so downstream can distinguish.
        # Recommended approach: volatility-based confidence adjustment
        # (reduce conf 30% when VIX>30 for EQUITY LONGs, etc.) rather than
        # hard-blocking trades. See updates/2026-05-14-per-asset-class-prediction-optimization-review.md

        if is_crypto and not should_generate_signal(direction, fng, reg, btc_dom, rsi):
            pick_copy = {**pick, "regime_filtered": True, "regime_reason": _rejection_reason(direction, fng, reg)}
            filtered.append(pick_copy)
        else:
            pick_copy = {**pick, "regime_filtered": False}
            passed.append(pick_copy)

    return passed, filtered


def _rejection_reason(direction: str, fng: int | None, regime: str) -> str:
    """Human-readable reason why a pick was regime-filtered."""
    fng_val = fng if fng is not None else 50
    if direction == "SHORT" and fng_val < 20:
        return f"SHORT blocked: F&G={fng_val} (panic) — never short during extreme fear"
    if direction == "SHORT" and regime == "TRENDING_UP" and fng_val <= 80:
        return f"SHORT blocked: regime={regime}, F&G={fng_val} — don't short uptrends without euphoria"
    if direction == "LONG" and fng_val > 80:
        return f"LONG blocked: F&G={fng_val} (euphoria) — distribution phase"
    if direction == "LONG" and regime == "TRENDING_DOWN" and fng_val >= 20:
        return f"LONG blocked: regime={regime}, F&G={fng_val} — don't catch knives"
    return f"Direction {direction} misaligned with regime={regime}, F&G={fng_val}"


# ── CLI entry point ─────────────────────────────────────────────

def main():
    """Print current regime status."""
    print("=" * 60)
    print("REGIME-STRATEGY ROUTER — Current Market State")
    print("=" * 60)

    regime = get_current_regime()

    print(f"\n  Fear & Greed:    {regime['fng']} ({regime['fng_classification']})")
    print(f"  BTC Regime:      {regime['regime']} (ADX: {regime['adx']})")
    print(f"  BTC RSI-14:      {regime['rsi_14']}")
    print(f"  BTC Dominance:   {regime['btc_dom_trend']}")
    print(f"  Longs Allowed:   {'YES' if regime['longs_allowed'] else 'NO'}")
    print(f"  Shorts Allowed:  {'YES' if regime['shorts_allowed'] else 'NO'}")
    print(f"  Timestamp:       {regime['timestamp']}")
    print(f"\n{'=' * 60}")

    return regime


if __name__ == "__main__":
    main()
