#!/usr/bin/env python3
"""
Crypto Smart Picks — Live Scanner
===================================
Implements ALL 4 portfolio strategies from the A/B/C/D backtest system,
weighted by their backtest scores. The winning portfolio gets highest
allocation, but all valid signals are emitted.

Reads backtest results from data/crypto_portfolio_backtest.json to
determine portfolio weights. Falls back to equal weights if no backtest
results exist.

Output: data/crypto_smart_picks.json — consumed by the Alpha Engine dashboard.

Usage:
    python crypto_smart_picks.py          # full scan
    python crypto_smart_picks.py --dry    # dry run, no file write
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from api_failover import fetch_klines, fetch_price
except ImportError:
    print("ERROR: api_failover.py not found. Cannot run scanner.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("crypto_smart_picks")

# ============================================================================
# Constants
# ============================================================================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT", "FETUSDT", "RENDERUSDT",
]

DATA_DIR = Path(__file__).resolve().parent / "data"
BACKTEST_FILE = DATA_DIR / "crypto_portfolio_backtest.json"
OUTPUT_FILE = DATA_DIR / "crypto_smart_picks.json"

# Default portfolio weights (overridden by backtest results)
DEFAULT_WEIGHTS = {
    "A_golden_filter": 0.35,
    "B_copy_trader": 0.30,
    "C_momentum_volume": 0.20,
    "D_mean_reversion": 0.15,
}

MAX_OPEN_PICKS = 6  # max simultaneous picks


# ============================================================================
# Technical Indicators (same as backtest module)
# ============================================================================
def _to_floats(klines, idx):
    return [float(k[idx]) if k[idx] else 0.0 for k in klines]


def ema(data, period):
    if len(data) < period:
        return [None] * len(data)
    result = [None] * (period - 1)
    k = 2.0 / (period + 1)
    sma_val = sum(data[:period]) / period
    result.append(sma_val)
    for i in range(period, len(data)):
        val = data[i] * k + result[-1] * (1 - k)
        result.append(val)
    return result


def sma(data, period):
    result = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        result.append(sum(data[i - period + 1:i + 1]) / period)
    return result


def rsi(data, period=14):
    if len(data) < period + 1:
        return [None] * len(data)
    deltas = [data[i] - data[i - 1] for i in range(1, len(data))]
    gains = [max(0, d) for d in deltas]
    losses = [max(0, -d) for d in deltas]
    result = [None] * period
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1.0 + rs))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1.0 + rs))
    return result


def atr(highs, lows, closes, period=14):
    if len(closes) < 2:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    result = [None] * (period - 1)
    atr_val = sum(trs[:period]) / period
    result.append(atr_val)
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        result.append(atr_val)
    return result


def volume_sma(volumes, period=20):
    return sma(volumes, period)


# ============================================================================
# Portfolio Weights Loader
# ============================================================================
def load_portfolio_weights() -> dict:
    """Load weights from backtest results. Higher score = higher weight."""
    if not BACKTEST_FILE.exists():
        log.warning("No backtest results found, using default weights")
        return DEFAULT_WEIGHTS

    try:
        with open(BACKTEST_FILE, "r", encoding="utf-8") as f:
            bt = json.load(f)
        portfolios = bt.get("portfolios", {})
        scores = {}
        for key, val in portfolios.items():
            scores[key] = val.get("score", 1.0)

        total = sum(scores.values())
        if total <= 0:
            return DEFAULT_WEIGHTS

        weights = {k: round(v / total, 4) for k, v in scores.items()}
        log.info("Loaded portfolio weights from backtest: %s", weights)
        return weights
    except Exception as e:
        log.warning("Failed to load backtest results: %s", e)
        return DEFAULT_WEIGHTS


# ============================================================================
# Signal Generation (one per portfolio strategy)
# ============================================================================
def scan_golden_filter(sym, closes, highs, lows, volumes, current_price):
    """Portfolio A: Golden Filter signals."""
    n = len(closes)
    if n < 55:
        return None

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    i = n - 1

    if any(x is None for x in [ema20[i], ema50[i], rsi14[i], atr14[i]]):
        return None

    trending = closes[i] > ema20[i] and ema20[i] > ema50[i]
    not_overbought = 30 < rsi14[i] < 70
    momentum = closes[i] > closes[max(0, i - 4)]

    confidence = 0.0
    if trending:
        confidence += 0.35
    if not_overbought:
        confidence += 0.25
    if momentum:
        confidence += 0.20
    if i >= 1 and volumes[i] > volumes[i - 1]:
        confidence += 0.15
    if rsi14[i] and 45 < rsi14[i] < 60:
        confidence += 0.05

    if confidence < 0.70:
        return None

    tp_dist = 1.5 * atr14[i]
    sl_dist = 1.0 * atr14[i]
    rr = tp_dist / sl_dist if sl_dist > 0 else 0
    if rr < 1.0 or rr >= 2.0:
        return None

    return {
        "symbol": sym,
        "direction": "LONG",
        "strategy": "golden_filter",
        "portfolio": "A",
        "entry_price": round(current_price, 6),
        "tp_price": round(current_price + tp_dist, 6),
        "sl_price": round(current_price - sl_dist, 6),
        "confidence": round(confidence, 3),
        "rsi": round(rsi14[i], 2),
        "rr_ratio": round(rr, 2),
    }


def scan_copy_trader(sym, closes, highs, lows, volumes, current_price):
    """Portfolio B: Copy Trader signals."""
    n = len(closes)
    if n < 25:
        return None

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    vol_avg = volume_sma(volumes, 20)
    i = n - 1

    if any(x is None for x in [ema9[i], ema21[i], rsi14[i], atr14[i]]):
        return None
    if vol_avg[i] is None or vol_avg[i] <= 0:
        return None

    # NMTD signal
    if (ema9[i] > ema21[i] and i >= 1 and ema9[i - 1] is not None
            and ema21[i - 1] is not None
            and rsi14[i] > 50 and rsi14[i] < 75
            and volumes[i] > vol_avg[i] * 1.3):
        if ema9[i - 1] <= ema21[i - 1] or (ema9[i] - ema21[i]) > (ema9[i - 1] - ema21[i - 1]):
            return {
                "symbol": sym,
                "direction": "LONG",
                "strategy": "copy_hl_NMTD_25M",
                "portfolio": "B",
                "entry_price": round(current_price, 6),
                "tp_price": round(current_price * 1.02, 6),
                "sl_price": round(current_price * 0.99, 6),
                "confidence": 0.81,
                "rsi": round(rsi14[i], 2),
                "rr_ratio": 2.0,
            }

    # Smart money signal -- KILLED Mar 25 2026
    # binance_smart_money: 45.8% WR, 44% of copy volume picking illiquid alts, -0.21% PnL.
    # Strategy permanently disabled at generator level. Signal generation blocked.
    # if (volumes[i] > vol_avg[i] * 2.5 ...):  # REMOVED

    return None


def scan_momentum_volume(sym, closes, highs, lows, volumes, current_price):
    """Portfolio C: Momentum + Volume signals."""
    n = len(closes)
    if n < 205:
        return None

    ema20 = ema(closes, 20)
    rsi14 = rsi(closes, 14)
    vol_avg = volume_sma(volumes, 20)
    sma200 = sma(closes, 200)
    i = n - 1

    if any(x is None for x in [ema20[i], rsi14[i], sma200[i]]):
        return None
    if vol_avg[i] is None or vol_avg[i] <= 0:
        return None

    vol_spike = volumes[i] > 2.0 * vol_avg[i]
    if not vol_spike:
        return None

    bull_regime = closes[i] > sma200[i]

    if bull_regime and closes[i] > ema20[i] and 40 <= rsi14[i] <= 65:
        return {
            "symbol": sym,
            "direction": "LONG",
            "strategy": "momentum_volume",
            "portfolio": "C",
            "entry_price": round(current_price, 6),
            "tp_price": round(current_price * 1.05, 6),
            "sl_price": round(current_price * 0.97, 6),
            "confidence": round(0.5 + (volumes[i] / vol_avg[i] - 2) * 0.1, 3),
            "rsi": round(rsi14[i], 2),
            "rr_ratio": round(5.0 / 3.0, 2),
            "trailing_stop_pct": 3.0,
        }

    if not bull_regime and closes[i] < ema20[i] and 40 <= rsi14[i] <= 65:
        return {
            "symbol": sym,
            "direction": "SHORT",
            "strategy": "momentum_volume",
            "portfolio": "C",
            "entry_price": round(current_price, 6),
            "tp_price": round(current_price * 0.95, 6),
            "sl_price": round(current_price * 1.03, 6),
            "confidence": round(0.5 + (volumes[i] / vol_avg[i] - 2) * 0.1, 3),
            "rsi": round(rsi14[i], 2),
            "rr_ratio": round(5.0 / 3.0, 2),
            "trailing_stop_pct": 3.0,
        }

    return None


def scan_mean_reversion(sym, closes, highs, lows, current_price):
    """Portfolio D: Mean Reversion signals."""
    n = len(closes)
    if n < 205:
        return None

    rsi2 = rsi(closes, 2)
    sma200 = sma(closes, 200)
    i = n - 1

    if rsi2[i] is None or sma200[i] is None:
        return None

    if rsi2[i] < 10 and closes[i] > sma200[i]:
        return {
            "symbol": sym,
            "direction": "LONG",
            "strategy": "mean_reversion_rsi2",
            "portfolio": "D",
            "entry_price": round(current_price, 6),
            "tp_price": round(current_price * 1.05, 6),  # RSI exit handled separately
            "sl_price": round(current_price * 0.97, 6),
            "confidence": round(0.7 + (10 - rsi2[i]) * 0.03, 3),
            "rsi2": round(rsi2[i], 2),
            "rr_ratio": round(5.0 / 3.0, 2),
            "exit_condition": "RSI(2) > 60",
        }

    return None


# ============================================================================
# Main Scanner
# ============================================================================
def scan_all() -> dict:
    """Run all portfolio scanners on all symbols."""
    log.info("=" * 60)
    log.info("CRYPTO SMART PICKS SCANNER")
    log.info("Symbols: %d | Strategies: 4 portfolios", len(SYMBOLS))
    log.info("=" * 60)

    weights = load_portfolio_weights()

    # Load existing picks to avoid duplicates
    existing_picks = []
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                prev = json.load(f)
                existing_picks = prev.get("active_picks", [])
        except Exception:
            pass

    existing_syms = {p["symbol"] for p in existing_picks if p.get("status") == "ACTIVE"}

    all_signals = []

    for sym in SYMBOLS:
        log.info("Scanning %s...", sym)

        # Download 4H candles (250 bars covers indicators needing 200-period lookback)
        klines = fetch_klines(sym, "4h", 250)
        if not klines or len(klines) < 50:
            log.warning("  %s: insufficient data (%d bars)", sym,
                        len(klines) if klines else 0)
            continue

        closes = _to_floats(klines, 4)
        highs = _to_floats(klines, 2)
        lows = _to_floats(klines, 3)
        volumes = _to_floats(klines, 5)

        # Get current price
        current_price = fetch_price(sym)
        if not current_price:
            current_price = closes[-1]

        # Run all 4 scanners
        signals = []
        sig_a = scan_golden_filter(sym, closes, highs, lows, volumes, current_price)
        if sig_a:
            sig_a["weight"] = weights.get("A_golden_filter", 0.25)
            signals.append(sig_a)

        sig_b = scan_copy_trader(sym, closes, highs, lows, volumes, current_price)
        if sig_b:
            sig_b["weight"] = weights.get("B_copy_trader", 0.25)
            signals.append(sig_b)

        sig_c = scan_momentum_volume(sym, closes, highs, lows, volumes, current_price)
        if sig_c:
            sig_c["weight"] = weights.get("C_momentum_volume", 0.25)
            signals.append(sig_c)

        sig_d = scan_mean_reversion(sym, closes, highs, lows, current_price)
        if sig_d:
            sig_d["weight"] = weights.get("D_mean_reversion", 0.25)
            signals.append(sig_d)

        for sig in signals:
            sig["scan_time"] = datetime.now(timezone.utc).isoformat()
            sig["status"] = "ACTIVE"
            all_signals.append(sig)
            log.info("  SIGNAL: %s %s %s (conf=%.2f, portfolio=%s)",
                     sig["direction"], sym, sig["strategy"],
                     sig["confidence"], sig["portfolio"])

        time.sleep(0.3)

    # Sort by weighted confidence
    for sig in all_signals:
        sig["weighted_score"] = round(sig["confidence"] * sig.get("weight", 0.25), 4)

    all_signals.sort(key=lambda x: x["weighted_score"], reverse=True)

    # Limit picks (keep top N that aren't already active)
    new_picks = []
    for sig in all_signals:
        if sig["symbol"] not in existing_syms and len(new_picks) < MAX_OPEN_PICKS:
            new_picks.append(sig)
        elif sig["symbol"] in existing_syms:
            # Update existing
            new_picks.append(sig)

    # Merge with existing (keep existing that are still valid)
    final_picks = new_picks

    # Build output
    output = {
        "scanner": "crypto_smart_picks",
        "version": "1.0.0",
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "symbols_scanned": len(SYMBOLS),
        "signals_found": len(all_signals),
        "active_picks": final_picks,
        "portfolio_weights": weights,
        "all_signals": all_signals,
        "summary": {
            "portfolio_A_signals": len([s for s in all_signals if s["portfolio"] == "A"]),
            "portfolio_B_signals": len([s for s in all_signals if s["portfolio"] == "B"]),
            "portfolio_C_signals": len([s for s in all_signals if s["portfolio"] == "C"]),
            "portfolio_D_signals": len([s for s in all_signals if s["portfolio"] == "D"]),
            "long_signals": len([s for s in all_signals if s["direction"] == "LONG"]),
            "short_signals": len([s for s in all_signals if s["direction"] == "SHORT"]),
        }
    }

    return output


def main():
    dry_run = "--dry" in sys.argv

    output = scan_all()

    if dry_run:
        log.info("DRY RUN — not writing output file")
        print(json.dumps(output, indent=2, default=str))
    else:
        DATA_DIR.mkdir(exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        log.info("Picks saved to %s", OUTPUT_FILE)

    log.info("\nScan complete: %d signals from %d symbols",
             output["signals_found"], output["symbols_scanned"])
    for key, val in output["summary"].items():
        log.info("  %s: %s", key, val)


if __name__ == "__main__":
    main()
