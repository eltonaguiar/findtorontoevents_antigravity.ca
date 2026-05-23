#!/usr/bin/env python3
"""
Regime Flip Detector
====================
Detects when the BTC market regime changes significantly (e.g., BEARISH -> BULLISH)
and triggers dashboard regeneration.

Regime classification (based on BTC 24h change):
  BULLISH  -> BTC 24h change > +2%
  BEARISH  -> BTC 24h change < -2%
  CHOPPY   -> between -2% and +2%

Uses Binance API with 3+ failover chain (API Failover Rule).
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"
REGIME_REPORT_PATH = DATA_DIR / "regime_report.json"
FLIP_ALERT_PATH = DATA_DIR / "regime_flip_alert.json"

# Regime thresholds (BTC 24h % change)
BULLISH_THRESHOLD = 2.0
BEARISH_THRESHOLD = -2.0

# 3+ API failover chain (NEVER use single Binance API)
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
KUCOIN_URL = "https://api.kucoin.com/api/v1/market/stats?symbol=BTC-USDT"
CRYPTOCOMPARE_URL = "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC&tsyms=USD"

# SSL context (for CI environments)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 15) -> dict | list | None:
    """GET JSON from a URL, return parsed data or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[regime_flip] API call failed for {url[:60]}...: {e}")
        return None


# ---------------------------------------------------------------------------
# BTC 24h change fetcher with 3+ failover
# ---------------------------------------------------------------------------

def fetch_btc_24h_change() -> float | None:
    """
    Fetch BTC 24h percentage change with Binance mirror failover + CoinGecko
    + KuCoin + CryptoCompare fallback chain.

    Returns float (percentage) or None if all sources fail.
    """

    # --- Attempt 1: Binance mirrors (ticker/24hr endpoint) ---
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/ticker/24hr?symbol=BTCUSDT"
        data = _http_get_json(url)
        if data and isinstance(data, dict) and "priceChangePercent" in data:
            pct = float(data["priceChangePercent"])
            print(f"[regime_flip] BTC 24h change: {pct:+.2f}% (from {mirror})")
            return pct

    # --- Attempt 2: CoinGecko ---
    data = _http_get_json(COINGECKO_URL)
    if data and isinstance(data, dict) and "bitcoin" in data:
        btc = data["bitcoin"]
        pct = btc.get("usd_24h_change")
        if pct is not None:
            pct = float(pct)
            print(f"[regime_flip] BTC 24h change: {pct:+.2f}% (from CoinGecko)")
            return pct

    # --- Attempt 3: KuCoin ---
    data = _http_get_json(KUCOIN_URL)
    if data and isinstance(data, dict) and data.get("data"):
        stats = data["data"]
        change_rate = stats.get("changeRate")
        if change_rate is not None:
            pct = float(change_rate) * 100  # KuCoin returns decimal (0.02 = 2%)
            print(f"[regime_flip] BTC 24h change: {pct:+.2f}% (from KuCoin)")
            return pct

    # --- Attempt 4: CryptoCompare ---
    data = _http_get_json(CRYPTOCOMPARE_URL)
    if data and isinstance(data, dict):
        raw = data.get("RAW", {}).get("BTC", {}).get("USD", {})
        pct = raw.get("CHANGEPCT24HOUR")
        if pct is not None:
            pct = float(pct)
            print(f"[regime_flip] BTC 24h change: {pct:+.2f}% (from CryptoCompare)")
            return pct

    print("[regime_flip] ERROR: All API sources failed for BTC 24h change")
    return None


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

def fetch_btc_momentum() -> dict:
    """Fetch BTC momentum indicators: RSI, SMA slope, drawdown from recent high.

    Returns dict with keys: rsi_4h, sma_slope, drawdown_from_high, price, high_6bar
    or empty dict on failure.
    """
    # Fetch 4H klines for RSI + SMA
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=30"
        data = _http_get_json(url)
        if data and isinstance(data, list) and len(data) >= 20:
            highs = [float(c[2]) for c in data]
            lows = [float(c[3]) for c in data]
            closes = [float(c[4]) for c in data]

            # RSI(14)
            gains, losses = [], []
            for i in range(1, len(closes)):
                d = closes[i] - closes[i - 1]
                gains.append(max(d, 0))
                losses.append(max(-d, 0))
            period = 14
            if len(gains) >= period:
                avg_gain = sum(gains[-period:]) / period
                avg_loss = sum(losses[-period:]) / period
                rsi_val = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
            else:
                rsi_val = 50

            # SMA slope (5 vs 20)
            sma20 = sum(closes[-20:]) / 20
            sma5 = sum(closes[-5:]) / 5
            slope = (sma5 - sma20) / sma20 * 100

            # Drawdown from 6-bar high
            high_6 = max(closes[-6:])
            current = closes[-1]
            dd = (current - high_6) / high_6 * 100

            # ADX(14) — trend strength (per CHATWITHIT.MD recommendation)
            adx_val = 20  # default: no trend
            if len(highs) >= 16:
                plus_dm, minus_dm, tr_list = [], [], []
                for i in range(1, len(highs)):
                    up = highs[i] - highs[i - 1]
                    down = lows[i - 1] - lows[i]
                    plus_dm.append(up if up > down and up > 0 else 0)
                    minus_dm.append(down if down > up and down > 0 else 0)
                    tr_list.append(max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i - 1]),
                        abs(lows[i] - closes[i - 1]),
                    ))
                # Smoothed averages (Wilder's smoothing, period=14)
                p = 14
                if len(tr_list) >= p:
                    atr = sum(tr_list[:p]) / p
                    pdm = sum(plus_dm[:p]) / p
                    mdm = sum(minus_dm[:p]) / p
                    for i in range(p, len(tr_list)):
                        atr = (atr * (p - 1) + tr_list[i]) / p
                        pdm = (pdm * (p - 1) + plus_dm[i]) / p
                        mdm = (mdm * (p - 1) + minus_dm[i]) / p
                    pdi = (pdm / atr * 100) if atr > 0 else 0
                    mdi = (mdm / atr * 100) if atr > 0 else 0
                    dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
                    adx_val = dx  # Simplified: single DX as ADX proxy

            # ATR volatility (for spike detection)
            atr_pct = 0
            if len(highs) >= 15:
                tr_vals = []
                for i in range(1, len(highs)):
                    tr_vals.append(max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i - 1]),
                        abs(lows[i] - closes[i - 1]),
                    ))
                atr_14 = sum(tr_vals[-14:]) / 14
                atr_pct = (atr_14 / current * 100) if current > 0 else 0

            print(f"[regime_flip] Momentum: RSI={rsi_val:.1f} slope={slope:+.3f}% dd={dd:+.2f}% ADX={adx_val:.1f} ATR%={atr_pct:.2f}%")
            return {
                "rsi_4h": rsi_val,
                "sma_slope": slope,
                "drawdown_from_high": dd,
                "price": current,
                "high_6bar": high_6,
                "adx": adx_val,
                "atr_pct": atr_pct,
            }
    return {}


def classify_regime(btc_change_pct: float, momentum: dict | None = None) -> str:
    """Classify market regime using 24h change + momentum confirmation.

    The old detector used ONLY 24h change which caused fakeouts:
    BTC goes +3.65%, detector says BULLISH, we load 10 LONGs,
    then BTC reverses -2% but 24h still shows +1.65%.

    New logic requires momentum confirmation:
    - BULLISH: 24h > +2% AND (RSI > 50 OR slope > 0)
    - BEARISH: 24h < -2% AND (RSI < 50 OR slope < 0)
    - WEAKENING_BULL: 24h > +2% but momentum fading (RSI < 45 or dd > 1.5%)
    - WEAKENING_BEAR: 24h < -2% but momentum recovering
    - CHOPPY: everything else
    """
    mom = momentum or {}
    rsi = mom.get("rsi_4h", 50)
    slope = mom.get("sma_slope", 0)
    dd = mom.get("drawdown_from_high", 0)
    adx = mom.get("adx", 20)
    atr_pct = mom.get("atr_pct", 0)

    # HIGH VOLATILITY SPIKE overrides everything (per CHATWITHIT.MD table)
    if atr_pct > 4.0:
        print(f"[regime_flip] VOLATILITY SPIKE: ATR={atr_pct:.1f}% — move to cash/hedge")
        return "VOLATILE"

    if btc_change_pct > BULLISH_THRESHOLD:
        # 24h says bullish — but is momentum confirming?
        if rsi < 42 or dd < -2.0:
            print(f"[regime_flip] FAKEOUT: 24h={btc_change_pct:+.1f}% but RSI={rsi:.0f}, dd={dd:+.1f}%")
            return "WEAKENING_BULL"
        elif rsi < 50 and slope < -0.1:
            return "WEAKENING_BULL"
        elif adx < 15 and abs(slope) < 0.1:
            # ADX says no trend despite 24h change — likely mean reversion coming
            print(f"[regime_flip] WEAK TREND: ADX={adx:.0f} despite 24h={btc_change_pct:+.1f}%")
            return "WEAKENING_BULL"
        else:
            return "BULLISH"
    elif btc_change_pct < BEARISH_THRESHOLD:
        if rsi > 58 or dd > 2.0:
            print(f"[regime_flip] FAKEOUT: 24h={btc_change_pct:+.1f}% but RSI={rsi:.0f}, dd={dd:+.1f}%")
            return "WEAKENING_BEAR"
        elif rsi > 52 and slope > 0.1:
            return "WEAKENING_BEAR"
        elif adx < 15 and abs(slope) < 0.1:
            print(f"[regime_flip] WEAK TREND: ADX={adx:.0f} despite 24h={btc_change_pct:+.1f}%")
            return "WEAKENING_BEAR"
        else:
            return "BEARISH"
    else:
        # Choppy range — check if momentum or ADX reveals a hidden trend
        if adx > 30 and rsi > 55 and slope > 0.15:
            return "LEANING_BULL"
        elif adx > 30 and rsi < 45 and slope < -0.15:
            return "LEANING_BEAR"
        elif rsi > 60 and slope > 0.2:
            return "LEANING_BULL"
        elif rsi < 40 and slope < -0.2:
            return "LEANING_BEAR"
        return "CHOPPY"


# Regime -> approximate directional confidence mapping
# Inspired by Mercury 2's "size = base * bull_prob" pattern
# These are deterministic approximations of Bayesian posterior probabilities
REGIME_CONFIDENCE = {
    "BULLISH": {"long_conf": 0.85, "short_conf": 0.15, "size_mult": 1.0},
    "LEANING_BULL": {"long_conf": 0.65, "short_conf": 0.35, "size_mult": 0.7},
    "WEAKENING_BULL": {"long_conf": 0.45, "short_conf": 0.55, "size_mult": 0.3},
    "CHOPPY": {"long_conf": 0.50, "short_conf": 0.50, "size_mult": 0.5},
    "WEAKENING_BEAR": {"long_conf": 0.55, "short_conf": 0.45, "size_mult": 0.3},
    "LEANING_BEAR": {"long_conf": 0.35, "short_conf": 0.65, "size_mult": 0.7},
    "BEARISH": {"long_conf": 0.15, "short_conf": 0.85, "size_mult": 1.0},
    "VOLATILE": {"long_conf": 0.50, "short_conf": 0.50, "size_mult": 0.2},
}


def get_regime_confidence(regime: str | None = None) -> dict:
    """Get confidence levels for the current or specified regime.

    Returns dict with long_conf, short_conf, size_mult.
    Downstream consumers can use: position_size = base_size * size_mult
    """
    if regime is None:
        regime = load_last_regime() or "CHOPPY"
    return REGIME_CONFIDENCE.get(regime, REGIME_CONFIDENCE["CHOPPY"])


def load_last_regime() -> str | None:
    """Load the last known regime from regime_report.json."""
    try:
        if REGIME_REPORT_PATH.exists():
            with open(REGIME_REPORT_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
            return report.get("regime")
    except Exception as e:
        print(f"[regime_flip] Could not load last regime: {e}")
    return None


def load_pending_regime() -> tuple[str | None, int]:
    """Load pending regime change and its confirmation count.

    Returns (pending_regime, confirm_count). If no pending change, returns (None, 0).
    """
    try:
        if REGIME_REPORT_PATH.exists():
            with open(REGIME_REPORT_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
            return report.get("_pending_regime"), report.get("_pending_count", 0)
    except Exception:
        pass
    return None, 0


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def check_flip() -> bool:
    """
    Check if a regime flip has occurred.

    Returns True if regime changed (e.g., BEARISH -> BULLISH), False otherwise.
    Side effects:
      - Updates regime_report.json with new regime
      - Writes regime_flip_alert.json on flip
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    btc_change = fetch_btc_24h_change()
    if btc_change is None:
        print("[regime_flip] Cannot determine regime - API failure. No flip assumed.")
        return False

    momentum = fetch_btc_momentum()
    raw_regime = classify_regime(btc_change, momentum)
    last_regime = load_last_regime()
    pending_regime, pending_count = load_pending_regime()

    # Hysteresis: require 2 consecutive confirmations before flipping
    # (Practice #8 from CHATWITHIT.MD: "Force persistence")
    # Exception: VOLATILE always takes effect immediately (emergency)
    CONFIRM_THRESHOLD = 2

    if last_regime is None:
        # First run — accept immediately
        current_regime = raw_regime
    elif raw_regime == last_regime:
        # No change — clear any pending flip
        current_regime = raw_regime
        pending_regime = None
        pending_count = 0
    elif raw_regime == "VOLATILE":
        # Emergency — bypass hysteresis
        current_regime = raw_regime
        pending_regime = None
        pending_count = 0
        print(f"[regime_flip] VOLATILE override — bypassing hysteresis")
    elif raw_regime == pending_regime:
        # Same pending regime seen again — increment confirmation
        pending_count += 1
        if pending_count >= CONFIRM_THRESHOLD:
            current_regime = raw_regime
            pending_regime = None
            pending_count = 0
            print(f"[regime_flip] Regime change CONFIRMED after {CONFIRM_THRESHOLD} consecutive checks")
        else:
            current_regime = last_regime  # Hold old regime
            print(f"[regime_flip] Pending flip {last_regime}->{raw_regime} ({pending_count}/{CONFIRM_THRESHOLD} confirmations)")
    else:
        # New different regime — start pending counter
        current_regime = last_regime  # Hold old regime
        pending_regime = raw_regime
        pending_count = 1
        print(f"[regime_flip] New pending flip {last_regime}->{raw_regime} (1/{CONFIRM_THRESHOLD} confirmations)")

    print(f"[regime_flip] Raw: {raw_regime} | Confirmed: {current_regime} | Last: {last_regime or 'NONE'}")

    # Determine if a confirmed flip occurred
    flipped = False
    if last_regime is not None and last_regime != current_regime:
        flipped = True
        print(f"[regime_flip] *** WARNING: REGIME FLIP DETECTED ***")
        print(f"[regime_flip] {last_regime} -> {current_regime} (BTC 24h: {btc_change:+.2f}%)")

        # Write flip alert
        alert = {
            "old_regime": last_regime,
            "new_regime": current_regime,
            "btc_24h_change_pct": round(btc_change, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_needed": f"Dashboard regeneration triggered: regime changed from {last_regime} to {current_regime}",
        }
        try:
            with open(FLIP_ALERT_PATH, "w", encoding="utf-8") as f:
                json.dump(alert, f, indent=2)
            print(f"[regime_flip] Alert written to {FLIP_ALERT_PATH}")
        except Exception as e:
            print(f"[regime_flip] Failed to write alert: {e}")

    elif last_regime is None:
        print(f"[regime_flip] First run - initializing regime to {current_regime}")
    else:
        print(f"[regime_flip] No regime change. Staying {current_regime}.")

    # Always update regime_report.json with current regime info
    try:
        # Preserve existing report data, just update the regime field
        existing = {}
        if REGIME_REPORT_PATH.exists():
            try:
                with open(REGIME_REPORT_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["regime"] = current_regime
        existing["regime_raw"] = raw_regime
        existing["btc_24h_change_pct"] = round(btc_change, 2)
        existing["regime_flip_detected"] = flipped
        existing["regime_last_checked"] = datetime.now(timezone.utc).isoformat()
        # Hysteresis state
        existing["_pending_regime"] = pending_regime
        existing["_pending_count"] = pending_count
        # Include momentum data for downstream consumers.
        # Always stamp momentum_fresh + momentum_last_updated so downstream
        # consumers can detect asymmetric staleness — prior bug: if
        # fetch_btc_momentum() returned {} on API failure, the conditional
        # below skipped the momentum-field writes, leaving stale RSI/ATR/
        # drawdown values alongside a fresh regime_last_checked timestamp.
        # Production data on 2026-05-13 showed btc_price=$70,115 from a
        # 51-day-old timestamp while regime_last_checked claimed current.
        if momentum:
            existing["rsi_4h"] = round(momentum.get("rsi_4h", 50), 1)
            existing["sma_slope"] = round(momentum.get("sma_slope", 0), 3)
            existing["drawdown_from_high"] = round(momentum.get("drawdown_from_high", 0), 2)
            existing["btc_price"] = momentum.get("price")
            existing["btc_6bar_high"] = momentum.get("high_6bar")
            existing["adx"] = round(momentum.get("adx", 20), 1)
            existing["atr_pct"] = round(momentum.get("atr_pct", 0), 2)
            existing["momentum_fresh"] = True
            existing["momentum_last_updated"] = datetime.now(timezone.utc).isoformat()
        else:
            # API failure path. Do NOT silently retain stale momentum from
            # the previous run with a fresh timestamp — flag staleness
            # explicitly so downstream consumers can refuse to act on it.
            existing["momentum_fresh"] = False
            existing.setdefault("momentum_last_updated", None)
        # Add confidence mapping for downstream position sizing
        conf = get_regime_confidence(current_regime)
        existing["long_confidence"] = conf["long_conf"]
        existing["short_confidence"] = conf["short_conf"]
        existing["size_multiplier"] = conf["size_mult"]

        with open(REGIME_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"[regime_flip] Failed to update regime report: {e}")

    return flipped


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def run():
    """Run regime flip detection standalone."""
    print("=" * 60)
    print("  Regime Flip Detector")
    print("=" * 60)

    flipped = check_flip()

    if flipped:
        print("\nResult: REGIME FLIP DETECTED - dashboard regeneration recommended")
    else:
        print("\nResult: No regime flip - no action needed")

    return flipped


if __name__ == "__main__":
    run()
