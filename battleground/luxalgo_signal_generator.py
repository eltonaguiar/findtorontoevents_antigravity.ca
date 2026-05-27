#!/usr/bin/env python3
"""
LuxAlgo-Inspired Signal Generator
===================================

Runs all LuxAlgo-ported strategies (RSI Range Predictor, Breakout Forecaster,
Streak Analyzer, SVM Ranker, Volatility Waterfall) to generate automated picks.

Outputs picks in standard audit format to:
  - battleground/data/luxalgo_active_picks.json
  - battleground/data/luxalgo_closed_picks.json

Designed to run hourly via GitHub Actions or locally via cron.
"""

from __future__ import annotations

import json
import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

# Add incubator strategies to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "battleground" / "incubator" / "strategies"))

try:
    import requests
except ImportError:
    requests = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOTUSDT", "AVAXUSDT", "ENAUSDT", "JUPUSDT", "WIFUSDT",
    "STXUSDT", "RENDERUSDT", "LINKUSDT", "ARBUSDT", "SUIUSDT",
    "NEARUSDT",
]

INTERVALS = ["1h"]  # primary timeframe
KLINE_LIMIT = 500   # enough history for RSI predictor training

ACTIVE_PATH = ROOT / "battleground" / "data" / "luxalgo_active_picks.json"
CLOSED_PATH = ROOT / "battleground" / "data" / "luxalgo_closed_picks.json"
BINANCE_BASE = "https://api.binance.com"
BINANCE_FALLBACKS = [
    "https://api1.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# TP/SL configuration
TP_ATR_MULT = 2.2    # Take-profit = 2.2 × ATR
SL_ATR_MULT = 1.3    # Stop-loss = 1.3 × ATR
MIN_CONFIDENCE = 0.45  # minimum combined confidence to generate a pick
MAX_ACTIVE_PER_SYMBOL = 1  # max 1 active pick per symbol


# ── Data fetching ──────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str = "1h", limit: int = 500) -> Optional[list]:
    """Fetch OHLCV klines from Binance with fallback."""
    if not requests:
        return None

    for base in [BINANCE_BASE] + BINANCE_FALLBACKS:
        try:
            url = f"{base}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return None


def parse_ohlcv(raw_klines: list):
    """Parse Binance klines into separate lists."""
    timestamps, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    for k in raw_klines:
        timestamps.append(int(k[0]))
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return timestamps, opens, highs, lows, closes, volumes


# ── RSI calculation ────────────────────────────────────────────────

def calc_rsi(closes: list, period: int = 14) -> list:
    """Calculate RSI series."""
    rsi = [float('nan')] * len(closes)
    if len(closes) < period + 1:
        return rsi
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rsi[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return rsi


def calc_atr(highs, lows, closes, period=14):
    """Calculate ATR."""
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0
    return sum(trs[-period:]) / period


# ── Signal Generation ──────────────────────────────────────────────

def generate_luxalgo_picks() -> List[dict]:
    """Run all LuxAlgo filters and generate picks."""
    # Import our ported modules
    try:
        from rsi_range_predictor import RSIRangePredictor
        from luxalgo_filters import BreakoutForecaster, StreakAnalyzer, StructuralSVMRanker, VolatilityWaterfall
    except ImportError as e:
        logger.error("Failed to import LuxAlgo modules: %s", e)
        return []

    rsi_pred = RSIRangePredictor(segments=10, forecast_len=50, history_limit=200)
    breakout = BreakoutForecaster(range_len=20, horizon=10, vol_lookback=50)
    streak = StreakAnalyzer()
    vol_wf = VolatilityWaterfall(base_step=10)
    svm = StructuralSVMRanker()

    now_utc = datetime.now(timezone.utc)
    picks = []

    for symbol in SYMBOLS:
        try:
            raw = fetch_klines(symbol, "1h", KLINE_LIMIT)
            if not raw or len(raw) < 100:
                logger.warning("%s: insufficient data (%d bars)", symbol, len(raw) if raw else 0)
                continue

            ts, opens, highs, lows, closes, volumes = parse_ohlcv(raw)
            current_price = closes[-1]

            # ── 1. Train RSI predictor & get forecast ──
            rsi_series = calc_rsi(closes, 14)
            current_rsi = rsi_series[-1]
            if current_rsi != current_rsi:  # NaN
                continue

            rsi_pred_inst = RSIRangePredictor(segments=10, forecast_len=50)
            rsi_pred_inst.train(rsi_series)
            rsi_result = rsi_pred_inst.predict(current_rsi)

            # ── 2. Breakout probability ──
            bo_result = breakout.forecast(closes, highs, lows)

            # ── 3. Streak analysis ──
            streak_result = streak.analyze(closes)

            # ── 4. Volatility waterfall ──
            vol_result = vol_wf.compute(highs, lows, closes)

            # ── 5. ATR for TP/SL ──
            atr = calc_atr(highs, lows, closes, 14)
            if atr <= 0:
                continue

            # ── 6. SVM score for a hypothetical break ──
            avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            svm_score = svm.score_break(volumes[-1], avg_vol_20, current_rsi,
                                        closes[-2], current_price, atr)

            # ── 7. Determine direction from RSI prediction ──
            rsi_direction = rsi_result["direction"]

            # ── 8. Combine filters for confidence ──
            confidence = 0.40  # base

            # RSI prediction boost
            if rsi_result["confidence"] > 0.3:
                confidence += rsi_result["confidence"] * 0.15

            # Breakout probability boost
            if rsi_direction == "BULLISH" and bo_result["bull_prob"] > 50:
                confidence += 0.10
            elif rsi_direction == "BEARISH" and bo_result["bear_prob"] > 50:
                confidence += 0.10

            # Streak analysis
            if streak_result["direction"] == "BULL" and rsi_direction == "BEARISH":
                if streak_result["reversal_probability"] > 0.6:
                    confidence += 0.08  # streak reversal aligns with bearish RSI pred
            if streak_result["direction"] == "BEAR" and rsi_direction == "BULLISH":
                if streak_result["reversal_probability"] > 0.6:
                    confidence += 0.08

            # Volatility regime
            if vol_result["regime"] == "NEUTRAL":
                confidence += 0.05
            elif vol_result["regime"] == "EXPANSION":
                confidence += 0.03

            # SVM score
            if svm_score > 65:
                confidence += 0.08
            elif svm_score > 55:
                confidence += 0.04

            # Squeeze bonus (high squeeze = breakout imminent)
            if bo_result["squeeze"] > 50:
                confidence += 0.05

            confidence = round(min(0.95, max(0.30, confidence)), 4)

            # ── 9. Skip if below threshold ──
            if confidence < MIN_CONFIDENCE:
                logger.info("%s: confidence %.2f < %.2f threshold, skipping",
                           symbol, confidence, MIN_CONFIDENCE)
                continue

            # ── 10. Extreme RSI filter ──
            if current_rsi > 85 or current_rsi < 15:
                logger.info("%s: extreme RSI %.1f, skipping", symbol, current_rsi)
                continue

            # ── 11. Determine signal direction ──
            if rsi_direction == "BULLISH":
                direction = "BUY"
                tp = round(current_price + atr * TP_ATR_MULT, 6)
                sl = round(current_price - atr * SL_ATR_MULT, 6)
            elif rsi_direction == "BEARISH":
                direction = "SELL"
                tp = round(current_price - atr * TP_ATR_MULT, 6)
                sl = round(current_price + atr * SL_ATR_MULT, 6)
            else:
                continue  # NEUTRAL = no signal

            rr = round(abs(tp - current_price) / abs(sl - current_price), 2) if abs(sl - current_price) > 0 else 0
            if rr < 1.2:
                continue

            # ── 12. Build pick ──
            pick_id = hashlib.md5(f"{symbol}{now_utc.isoformat()}{direction}".encode()).hexdigest()[:12]

            reason_parts = []
            reason_parts.append(f"RSI pred: {current_rsi:.0f}→{rsi_result['endpoint']} ({rsi_direction})")
            reason_parts.append(f"Breakout: bull {bo_result['bull_prob']:.0f}% bear {bo_result['bear_prob']:.0f}%")
            reason_parts.append(f"Streak: {streak_result['direction']} x{streak_result['length']} (rev {streak_result['reversal_probability']:.0%})")
            reason_parts.append(f"Vol regime: {vol_result['regime']} ({vol_result['aggregate_heat']:.0f})")
            reason_parts.append(f"SVM: {svm_score:.0f}/100")

            pick = {
                "id": pick_id,
                "symbol": symbol,
                "direction": direction,
                "entry_price": current_price,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "rr_ratio": rr,
                "strategy": "luxalgo_confluence",
                "source_system": "luxalgo_filters",
                "tag": "LuxAlgo RSI-Pred + Breakout + Streak + Vol",
                "status": "active",
                "timeframe": "1h",
                "timestamp": now_utc.isoformat(),
                "created_at": now_utc.isoformat(),
                "reason": " | ".join(reason_parts),
                "metadata": {
                    "rsi_current": round(current_rsi, 1),
                    "rsi_predicted": rsi_result["endpoint"],
                    "rsi_direction": rsi_direction,
                    "rsi_confidence": rsi_result["confidence"],
                    "rsi_segment": list(rsi_result["segment"]),
                    "rsi_samples": rsi_result["sample_count"],
                    "bull_prob": bo_result["bull_prob"],
                    "bear_prob": bo_result["bear_prob"],
                    "squeeze": bo_result["squeeze"],
                    "streak_dir": streak_result["direction"],
                    "streak_len": streak_result["length"],
                    "streak_reversal_prob": streak_result["reversal_probability"],
                    "vol_regime": vol_result["regime"],
                    "vol_heat": vol_result["aggregate_heat"],
                    "svm_score": svm_score,
                    "atr": round(atr, 6),
                    "filters_used": [
                        "rsi_range_prediction",
                        "probabilistic_breakout",
                        "streak_analysis",
                        "volatility_waterfall",
                        "svm_structure_ranker",
                    ],
                },
            }

            picks.append(pick)
            logger.info("%s: %s @ %.6f → TP %.6f / SL %.6f (conf: %.2f, R:R: %.2f)",
                       symbol, direction, current_price, tp, sl, confidence, rr)

        except Exception as e:
            logger.warning("%s: error — %s", symbol, e)

    return picks


# ── Pick management ────────────────────────────────────────────────

def load_picks(path: Path) -> list:
    """Load picks from JSON file."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def save_picks(picks: list, path: Path):
    """Save picks to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(picks, indent=2, default=str), encoding="utf-8")
    logger.info("Saved %d picks to %s", len(picks), path)


def check_tp_sl(pick: dict) -> Optional[str]:
    """Check if a pick has hit TP or SL based on current price."""
    try:
        raw = fetch_klines(pick["symbol"], "1h", 2)
        if not raw:
            return None
        current = float(raw[-1][4])
        tp = pick["take_profit"]
        sl = pick["stop_loss"]

        if pick["direction"] == "BUY":
            if current >= tp:
                return "tp_hit"
            if current <= sl:
                return "sl_hit"
        else:
            if current <= tp:
                return "tp_hit"
            if current >= sl:
                return "sl_hit"
    except Exception:
        pass
    return None


def manage_picks(new_picks: List[dict]):
    """Merge new picks with existing, check TP/SL, move closed picks."""
    active = load_picks(ACTIVE_PATH)
    closed = load_picks(CLOSED_PATH)

    now = datetime.now(timezone.utc)

    # Check existing active picks for TP/SL
    still_active = []
    for pick in active:
        result = check_tp_sl(pick)
        if result:
            pick["status"] = result
            pick["closed_at"] = now.isoformat()
            pick["outcome"] = "WIN" if result == "tp_hit" else "LOSS"
            try:
                raw = fetch_klines(pick["symbol"], "1h", 2)
                if raw:
                    pick["close_price"] = float(raw[-1][4])
                    pnl = ((pick["close_price"] - pick["entry_price"]) / pick["entry_price"]) * 100
                    if pick["direction"] == "SELL":
                        pnl = -pnl
                    pick["pnl_pct"] = round(pnl, 2)
            except Exception:
                pass
            closed.append(pick)
            logger.info("%s: %s → %s (P/L: %.2f%%)", pick["symbol"], result,
                       pick.get("outcome", "?"), pick.get("pnl_pct", 0))
        else:
            # Check max hold time (72h)
            created = pick.get("created_at", pick.get("timestamp", ""))
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if (now - created_dt).total_seconds() > 72 * 3600:
                    pick["status"] = "time_exit"
                    pick["closed_at"] = now.isoformat()
                    pick["outcome"] = "TIME_EXIT"
                    closed.append(pick)
                    logger.info("%s: time exit after 72h", pick["symbol"])
                    continue
            except Exception:
                pass
            still_active.append(pick)

    # Add new picks (avoid duplicates by symbol)
    active_symbols = {p["symbol"] for p in still_active}
    for pick in new_picks:
        if pick["symbol"] not in active_symbols:
            still_active.append(pick)
            active_symbols.add(pick["symbol"])
            logger.info("NEW PICK: %s %s @ %.6f", pick["direction"], pick["symbol"], pick["entry_price"])
        else:
            logger.info("SKIP: %s already active", pick["symbol"])

    save_picks(still_active, ACTIVE_PATH)
    save_picks(closed, CLOSED_PATH)

    return still_active, closed


# ── Main ───────────────────────────────────────────────────────────

def main():
    """Run the LuxAlgo signal generator pipeline."""
    logger.info("=" * 60)
    logger.info("  LUXALGO CONFLUENCE SIGNAL GENERATOR")
    logger.info("  %s", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("=" * 60)

    # Generate new picks
    new_picks = generate_luxalgo_picks()
    logger.info("Generated %d new picks from %d symbols", len(new_picks), len(SYMBOLS))

    # Manage picks (merge, check TP/SL, move closed)
    active, closed = manage_picks(new_picks)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"  LUXALGO PICKS SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Active picks: {len(active)}")
    print(f"  Closed picks: {len(closed)}")

    wins = sum(1 for p in closed if p.get("outcome") == "WIN")
    losses = sum(1 for p in closed if p.get("outcome") == "LOSS")
    if wins + losses > 0:
        print(f"  Win rate: {wins}/{wins+losses} = {wins/(wins+losses):.1%}")

    for p in active:
        print(f"\n  {p['direction']:4s} {p['symbol']}")
        print(f"    Entry: {p['entry_price']}  TP: {p['take_profit']}  SL: {p['stop_loss']}")
        print(f"    Confidence: {p['confidence']:.1%}  R:R: {p['rr_ratio']}")
        print(f"    Reason: {p['reason'][:80]}...")

    print(f"\n{'=' * 60}")

    # Summary for GitHub Actions
    summary = f"LuxAlgo: {len(active)} active, {len(closed)} closed"
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"## LuxAlgo Signal Generator\n\n")
            f.write(f"- **Active picks:** {len(active)}\n")
            f.write(f"- **Closed picks:** {len(closed)}\n")
            if wins + losses > 0:
                f.write(f"- **Win rate:** {wins}/{wins+losses} = {wins/(wins+losses):.1%}\n")
            f.write(f"\n| Symbol | Dir | Entry | TP | SL | Conf | R:R |\n")
            f.write(f"|--------|-----|-------|----|----|------|-----|\n")
            for p in active:
                f.write(f"| {p['symbol']} | {p['direction']} | {p['entry_price']} | {p['take_profit']} | {p['stop_loss']} | {p['confidence']:.1%} | {p['rr_ratio']} |\n")

    return active


if __name__ == "__main__":
    main()
