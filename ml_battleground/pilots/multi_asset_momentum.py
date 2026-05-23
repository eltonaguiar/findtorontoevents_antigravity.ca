"""
Multi-Asset Cross-Momentum ML Pilot
Part of ml_battleground/pilots/

Detects cross-asset momentum signals where strength in one asset class
predicts moves in another (gold->BTC, DXY->crypto, etc.)

Modes:
  scan      -- Fetch all assets, compute cross-momentum signals
  backtest  -- Simple historical backtest of cross-asset rules

Usage:
  python multi_asset_momentum.py scan
  python multi_asset_momentum.py backtest
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

import numpy as np
import requests

DATA_DIR = Path(__file__).parent / "data" / "multi_asset_momentum"
PICKS_PATH = DATA_DIR / "picks.json"
HISTORY_PATH = DATA_DIR / "history.json"

logger = logging.getLogger("multi_asset_momentum")

# -- Asset universe --
CRYPTO_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ETF_SYMBOLS = ["SPY", "QQQ", "GLD", "SLV", "VDE", "TLT", "UUP", "COPX"]


# -- Data fetching --

def fetch_binance_daily(pair: str, days: int = 60) -> dict:
    """Fetch daily OHLCV from Binance (no API key required)."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": pair, "interval": "1d", "limit": days}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        closes = [float(row[4]) for row in data]
        highs = [float(row[2]) for row in data]
        lows = [float(row[3]) for row in data]
        volumes = [float(row[5]) for row in data]
        return {"close": closes, "high": highs, "low": lows, "volume": volumes}
    except Exception as e:
        logger.warning("Binance %s failed: %s", pair, e)
        return None


def fetch_yfinance_daily(symbol: str, days: int = 60) -> dict:
    """Fetch daily OHLCV via yfinance (optional dependency)."""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed -- skipping %s (pip install yfinance)", symbol)
        return None
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f"{days}d")
        if hist.empty:
            return None
        return {
            "close": hist["Close"].tolist(),
            "high": hist["High"].tolist(),
            "low": hist["Low"].tolist(),
            "volume": hist["Volume"].tolist(),
        }
    except Exception as e:
        logger.warning("yfinance %s failed: %s", symbol, e)
        return None


def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed Index from Alternative.me with retry."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=30", timeout=10)
            data = resp.json().get("data", [])
            if data:
                values = [int(d["value"]) for d in data]
                return {
                    "current": values[0],
                    "prev_day": values[1] if len(values) > 1 else values[0],
                    "week_avg": round(sum(values[:7]) / min(7, len(values)), 1),
                    "month_avg": round(sum(values) / len(values), 1),
                    "classification": data[0].get("value_classification", ""),
                }
        except Exception as e:
            if attempt == 2:
                logger.warning("Fear & Greed failed after 3 attempts: %s", e)
            else:
                _time.sleep(2 * (attempt + 1))
    return {
        "current": 50, "prev_day": 50, "week_avg": 50,
        "month_avg": 50, "classification": "Neutral",
    }


# -- Indicators --

def _returns(closes, period):
    """N-day return as percentage."""
    if len(closes) < period + 1:
        return 0.0
    return (closes[-1] / closes[-1 - period] - 1) * 100


def _sma(closes, period):
    """Simple moving average of last *period* values."""
    if len(closes) < period:
        return closes[-1] if closes else 0
    return sum(closes[-period:]) / period


def _rsi(closes, period=14):
    """RSI calculation."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.001
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


# -- Cross-asset signal detectors --

def detect_gold_btc_rotation(gold_data, btc_data) -> dict:
    """Gold rallying + BTC lagging = BTC catch-up likely.

    Rationale: Gold and BTC compete as "store of value".  When gold leads
    significantly while BTC lags, capital rotation into BTC often follows.
    """
    if not gold_data or not btc_data:
        return None

    gold_7d = _returns(gold_data["close"], 7)
    btc_7d = _returns(btc_data["close"], 7)
    gold_20d = _returns(gold_data["close"], 20)

    if gold_7d > 2.0 and btc_7d < -3.0:
        strength = min((gold_7d - 2) * 0.1 + abs(btc_7d + 3) * 0.05, 0.3)
        return {
            "signal": "gold_btc_rotation",
            "direction": "long",
            "target": "BTCUSDT",
            "confidence": round(0.55 + strength, 3),
            "reason": (
                f"Gold +{gold_7d:.1f}% (7d) while BTC {btc_7d:+.1f}% (7d) "
                "- rotation expected"
            ),
            "indicators": {
                "gold_7d": round(gold_7d, 2),
                "btc_7d": round(btc_7d, 2),
                "gold_20d": round(gold_20d, 2),
            },
        }
    return None


def detect_dxy_weakness(uup_data, crypto_data_map) -> list:
    """Dollar weakness = crypto strength.

    UUP is a dollar-bull ETF; when it drops, it means the USD is weakening.
    A weak dollar has historically been a tailwind for crypto prices.
    """
    if not uup_data:
        return []

    dxy_5d = _returns(uup_data["close"], 5)
    dxy_20d = _returns(uup_data["close"], 20)

    signals = []
    if dxy_5d < -0.8:
        strength = min(abs(dxy_5d + 0.8) * 0.15, 0.2)
        for pair, data in crypto_data_map.items():
            if data:
                rsi = _rsi(data["close"])
                if rsi < 50:  # Not overbought
                    signals.append({
                        "signal": "dxy_weakness",
                        "direction": "long",
                        "target": pair,
                        "confidence": round(
                            0.52 + strength + (50 - rsi) * 0.002, 3
                        ),
                        "reason": (
                            f"DXY weakening ({dxy_5d:+.1f}% 5d) - crypto "
                            f"tailwind. {pair} RSI={rsi:.0f}"
                        ),
                        "indicators": {
                            "dxy_5d": round(dxy_5d, 2),
                            "dxy_20d": round(dxy_20d, 2),
                            "rsi": round(rsi, 1),
                        },
                    })
    return signals


def detect_risk_on_rotation(spy_data, qqq_data, btc_data) -> dict:
    """SPY + QQQ above moving average + BTC oversold = buy BTC.

    When equities are in a strong uptrend but crypto is lagging / oversold,
    it often signals that risk appetite is high and BTC will catch up.
    """
    if not spy_data or not qqq_data or not btc_data:
        return None

    spy_price = spy_data["close"][-1]
    qqq_price = qqq_data["close"][-1]
    # Use 50d SMA as proxy when we don't have 200 days of data
    spy_sma = _sma(spy_data["close"], 50)
    qqq_sma = _sma(qqq_data["close"], 50)
    btc_rsi = _rsi(btc_data["close"])

    if spy_price > spy_sma and qqq_price > qqq_sma and btc_rsi < 40:
        return {
            "signal": "risk_on_rotation",
            "direction": "long",
            "target": "BTCUSDT",
            "confidence": round(0.58 + (40 - btc_rsi) * 0.005, 3),
            "reason": (
                f"Equities bullish (SPY & QQQ > 50 SMA) but BTC oversold "
                f"(RSI={btc_rsi:.0f})"
            ),
            "indicators": {
                "spy_vs_sma": round((spy_price / spy_sma - 1) * 100, 2),
                "qqq_vs_sma": round((qqq_price / qqq_sma - 1) * 100, 2),
                "btc_rsi": round(btc_rsi, 1),
            },
        }
    return None


def detect_commodity_supercycle(gold_data, silver_data, energy_data,
                                copper_data) -> dict:
    """Multiple commodities trending up = supercycle momentum.

    When 3 or more of gold, silver, energy, and copper are all in 20-day
    uptrends, it signals broad commodity demand (often inflationary).
    """
    datasets = {
        "GLD": gold_data,
        "SLV": silver_data,
        "VDE": energy_data,
        "COPX": copper_data,
    }

    positive_count = 0
    total_momentum = 0
    details = {}

    for name, data in datasets.items():
        if data and len(data["close"]) > 20:
            ret_20d = _returns(data["close"], 20)
            details[name] = round(ret_20d, 2)
            if ret_20d > 0:
                positive_count += 1
                total_momentum += ret_20d

    if positive_count >= 3:
        return {
            "signal": "commodity_supercycle",
            "direction": "long",
            "target": "GLD",  # Primary play is gold
            "confidence": round(0.55 + min(positive_count * 0.05, 0.20), 3),
            "reason": (
                f"{positive_count}/4 commodities positive 20d - "
                "supercycle momentum"
            ),
            "indicators": details,
            "secondary_targets": [
                k for k, v in details.items() if v > 0 and k != "GLD"
            ],
        }
    return None


def detect_flight_to_safety_reversal(tlt_data, fg_data, btc_data) -> dict:
    """TLT spike (fear) + extreme Fear & Greed = contrarian BTC buy.

    When bonds spike (flight to safety) and Fear & Greed is at extreme fear,
    markets are usually near a local bottom -- contrarian long.
    """
    if not tlt_data or not btc_data:
        return None

    tlt_5d = _returns(tlt_data["close"], 5)
    fg = fg_data["current"]

    if tlt_5d > 1.5 and fg < 20:
        return {
            "signal": "safety_reversal",
            "direction": "long",
            "target": "BTCUSDT",
            "confidence": round(
                0.58 + (20 - fg) * 0.005 + min(tlt_5d * 0.02, 0.1), 3
            ),
            "reason": (
                f"Flight to safety (TLT +{tlt_5d:.1f}%) at extreme fear "
                f"(F&G={fg}) - contrarian buy"
            ),
            "indicators": {
                "tlt_5d": round(tlt_5d, 2),
                "fear_greed": fg,
            },
        }
    return None


# -- Composite cross-momentum score --

def compute_cross_momentum_score(signals: list) -> dict:
    """Weighted composite of all active signals into a single score."""
    if not signals:
        return {"score": 0.0, "label": "neutral", "active_signals": 0}

    weights = {
        "gold_btc_rotation": 1.2,
        "dxy_weakness": 1.0,
        "risk_on_rotation": 1.3,
        "commodity_supercycle": 0.8,
        "safety_reversal": 1.1,
    }

    total_weight = 0
    weighted_conf = 0
    for sig in signals:
        w = weights.get(sig["signal"], 1.0)
        weighted_conf += sig["confidence"] * w
        total_weight += w

    score = round(weighted_conf / total_weight, 3) if total_weight else 0
    if score >= 0.65:
        label = "strong_bullish"
    elif score >= 0.55:
        label = "bullish"
    elif score >= 0.45:
        label = "neutral"
    else:
        label = "bearish"

    return {
        "score": score,
        "label": label,
        "active_signals": len(signals),
    }


# -- Scanner --

def scan():
    """Run full cross-asset momentum scan."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching cross-asset data...")

    # Crypto
    crypto_data = {}
    for pair in CRYPTO_PAIRS:
        crypto_data[pair] = fetch_binance_daily(pair, 60)
        time.sleep(0.3)

    # ETFs
    etf_data = {}
    for symbol in ETF_SYMBOLS:
        etf_data[symbol] = fetch_yfinance_daily(symbol, 60)
        time.sleep(0.3)

    # Fear & Greed
    fg = fetch_fear_greed()

    # Run all detectors
    all_signals = []

    # 1. Gold-BTC rotation
    sig = detect_gold_btc_rotation(
        etf_data.get("GLD"), crypto_data.get("BTCUSDT")
    )
    if sig:
        all_signals.append(sig)

    # 2. DXY weakness
    dxy_sigs = detect_dxy_weakness(etf_data.get("UUP"), crypto_data)
    all_signals.extend(dxy_sigs)

    # 3. Risk-on rotation
    sig = detect_risk_on_rotation(
        etf_data.get("SPY"), etf_data.get("QQQ"), crypto_data.get("BTCUSDT")
    )
    if sig:
        all_signals.append(sig)

    # 4. Commodity supercycle
    sig = detect_commodity_supercycle(
        etf_data.get("GLD"), etf_data.get("SLV"),
        etf_data.get("VDE"), etf_data.get("COPX"),
    )
    if sig:
        all_signals.append(sig)

    # 5. Flight to safety reversal
    sig = detect_flight_to_safety_reversal(
        etf_data.get("TLT"), fg, crypto_data.get("BTCUSDT")
    )
    if sig:
        all_signals.append(sig)

    # Sort by confidence descending
    all_signals.sort(key=lambda x: x["confidence"], reverse=True)

    # Composite score
    composite = compute_cross_momentum_score(all_signals)

    # -- Logging --
    logger.info("Fear & Greed: %d (%s)", fg["current"], fg["classification"])

    for pair in CRYPTO_PAIRS:
        d = crypto_data.get(pair)
        if d:
            logger.info(
                "  %s: price=$%.2f, 7d=%+.1f%%, RSI=%.0f",
                pair, d["close"][-1],
                _returns(d["close"], 7), _rsi(d["close"]),
            )

    for sym in ["GLD", "SLV", "SPY", "QQQ", "TLT", "UUP"]:
        d = etf_data.get(sym)
        if d:
            logger.info(
                "  %s: $%.2f, 7d=%+.1f%%",
                sym, d["close"][-1], _returns(d["close"], 7),
            )

    for sig in all_signals:
        logger.info(
            "SIGNAL: %s %s (conf=%.3f) - %s",
            sig["target"], sig["direction"],
            sig["confidence"], sig["reason"],
        )

    if not all_signals:
        logger.info("No cross-asset signals detected")

    logger.info(
        "Composite: score=%.3f label=%s (%d active signals)",
        composite["score"], composite["label"], composite["active_signals"],
    )

    # -- Save output --
    output = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "multi_asset_momentum",
        "fear_greed": fg,
        "asset_summary": {
            "crypto": {
                pair: {
                    "price": round(d["close"][-1], 2),
                    "ret_7d": round(_returns(d["close"], 7), 2),
                    "rsi": round(_rsi(d["close"]), 1),
                }
                for pair, d in crypto_data.items() if d
            },
            "etfs": {
                sym: {
                    "price": round(d["close"][-1], 2),
                    "ret_7d": round(_returns(d["close"], 7), 2),
                }
                for sym, d in etf_data.items() if d
            },
        },
        "composite": composite,
        "signals": all_signals,
    }
    PICKS_PATH.write_text(json.dumps(output, indent=2))

    # Append to rolling history
    history = []
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
        except Exception:
            pass
    history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fear_greed": fg["current"],
        "composite_score": composite["score"],
        "composite_label": composite["label"],
        "signal_count": len(all_signals),
        "signals": [
            {
                "target": s["target"],
                "signal": s["signal"],
                "confidence": s["confidence"],
            }
            for s in all_signals
        ],
    })
    # Keep last 200 entries
    history = history[-200:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2))

    return all_signals


# -- Simple backtest --

def backtest():
    """Simple backtest: BTC RSI<30 oversold bounce over last year of data."""
    logger.info("Fetching extended history for backtest...")

    btc = fetch_binance_daily("BTCUSDT", 365)
    if not btc:
        logger.error("Cannot fetch BTC data for backtest")
        return

    closes = btc["close"]
    trades = []

    for i in range(30, len(closes) - 7):
        window = closes[max(0, i - 14) : i + 1]
        rsi = _rsi(window)
        if rsi < 30:
            entry = closes[i]
            exit_price = closes[i + 7]
            ret = (exit_price / entry - 1) * 100
            trades.append({
                "entry_idx": i,
                "entry": round(entry, 2),
                "exit": round(exit_price, 2),
                "return_pct": round(ret, 2),
                "rsi": round(rsi, 1),
            })

    if trades:
        returns = [t["return_pct"] for t in trades]
        wins = sum(1 for r in returns if r > 0)
        logger.info("Backtest: BTC RSI<30 buy-and-hold 7 days")
        logger.info(
            "  Trades: %d | Win rate: %.1f%% | Avg return: %.2f%%",
            len(trades), wins / len(trades) * 100,
            sum(returns) / len(returns),
        )
        logger.info(
            "  Best: %+.2f%% | Worst: %+.2f%%",
            max(returns), min(returns),
        )
    else:
        logger.info("No RSI<30 events found in BTC history")

    return trades


# -- Main --

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if mode == "scan":
        signals = scan()
        if signals:
            print(json.dumps(signals, indent=2))
        else:
            print("No cross-asset signals detected")
    elif mode == "backtest":
        trades = backtest()
        if trades:
            print(json.dumps(trades[-5:], indent=2))
    else:
        print(f"Usage: {sys.argv[0]} [scan|backtest]")
