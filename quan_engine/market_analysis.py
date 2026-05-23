"""
QuanEngine Market Analysis — Extended Universe Scanner
========================================================
Scans ~40 crypto pairs and produces a ranked "next best picks"
report alongside full market overview.

Output: quan_engine/data/market_analysis.json
  - active_signals (from core scanner)
  - next_best_picks (ranked by composite score)
  - market_overview (all ~40 pairs with technicals)
  - market_summary (aggregate statistics)
"""
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from quan_engine import config
from quan_engine.regime_router import RegimeRouter

logger = logging.getLogger("QuanEngine.MarketAnalysis")


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch klines from Binance REST API with geo-restriction fallbacks."""
    bases = [config.BINANCE_BASE] + getattr(config, "BINANCE_FALLBACK_URLS", [])
    last_err = None
    for base in bases:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode())
            df = pd.DataFrame(raw, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore",
            ])
            for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
                df[col] = df[col].astype(float)
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df.set_index("timestamp")
            return df[["open", "high", "low", "close", "volume", "quote_volume"]]
        except Exception as e:
            last_err = e
            continue
    logger.warning(f"Failed to fetch {symbol} (all endpoints): {last_err}")
    return pd.DataFrame()


def fetch_fear_greed() -> int:
    try:
        req = urllib.request.Request(config.FEAR_GREED_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return int(data["data"][0]["value"])
    except Exception:
        return 50


def compute_technicals(df: pd.DataFrame) -> dict:
    """Compute a full technical snapshot for a single pair."""
    if df.empty or len(df) < 200:
        return {}

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values
    current = close[-1]

    # --- RSI (14) ---
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    period = 14
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi_14 = round(100 - (100 / (1 + rs)), 2)

    # --- RSI (2) for mean-reversion ---
    p2 = 2
    ag2 = np.mean(gains[:p2]) if len(gains) >= p2 else 0
    al2 = np.mean(losses[:p2]) if len(losses) >= p2 else 0
    for i in range(p2, len(gains)):
        ag2 = (ag2 * (p2 - 1) + gains[i]) / p2
        al2 = (al2 * (p2 - 1) + losses[i]) / p2
    rs2 = ag2 / al2 if al2 > 0 else 100
    rsi_2 = round(100 - (100 / (1 + rs2)), 2)

    # --- ATR (14) ---
    tr = np.zeros(len(close))
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.mean(tr[-14:])
    atr_pct = round((atr / current) * 100, 3) if current > 0 else 0

    # --- EMAs ---
    def ema(data, period):
        out = np.zeros(len(data))
        k = 2 / (period + 1)
        out[0] = data[0]
        for i in range(1, len(data)):
            out[i] = data[i] * k + out[i - 1] * (1 - k)
        return out

    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    ema50 = ema(close, 50)
    sma200 = np.mean(close[-200:])

    # --- MACD ---
    ema12 = ema(close, 12)
    ema26 = ema(close, 26)
    macd_line = ema12[-1] - ema26[-1]
    macd_signal = ema(ema12 - ema26, 9)[-1]
    macd_hist = macd_line - macd_signal

    # --- Bollinger Bands ---
    bb_period = 20
    bb_sma = np.mean(close[-bb_period:])
    bb_std = np.std(close[-bb_period:])
    bb_upper = bb_sma + 2 * bb_std
    bb_lower = bb_sma - 2 * bb_std
    bb_pct = round((current - bb_lower) / (bb_upper - bb_lower), 3) if (bb_upper - bb_lower) > 0 else 0.5

    # --- Volume analysis ---
    vol_avg_20 = np.mean(volume[-20:])
    vol_ratio = round(volume[-1] / vol_avg_20, 2) if vol_avg_20 > 0 else 1.0

    # --- Price changes ---
    pct_1h = round((current / close[-2] - 1) * 100, 3) if len(close) > 1 else 0
    pct_4h = round((current / close[-5] - 1) * 100, 3) if len(close) > 4 else 0
    pct_24h = round((current / close[-25] - 1) * 100, 3) if len(close) > 24 else 0
    pct_7d = round((current / close[-169] - 1) * 100, 3) if len(close) > 168 else 0

    # --- Consecutive down bars ---
    consec_down = 0
    for i in range(len(close) - 1, 0, -1):
        if close[i] < close[i - 1]:
            consec_down += 1
        else:
            break

    consec_up = 0
    for i in range(len(close) - 1, 0, -1):
        if close[i] > close[i - 1]:
            consec_up += 1
        else:
            break

    # --- EMA trend structure ---
    ema_bullish_stack = ema9[-1] > ema21[-1] > ema50[-1]
    ema_bearish_stack = ema9[-1] < ema21[-1] < ema50[-1]
    above_200 = current > sma200

    # --- Support / Resistance (simple 20-bar high/low) ---
    resist_20 = round(float(np.max(high[-20:])), 8)
    support_20 = round(float(np.min(low[-20:])), 8)
    dist_to_resist = round((resist_20 / current - 1) * 100, 2) if current > 0 else 0
    dist_to_support = round((1 - support_20 / current) * 100, 2) if current > 0 else 0

    return {
        "price": round(float(current), 8),
        "rsi_14": rsi_14,
        "rsi_2": rsi_2,
        "atr_pct": atr_pct,
        "atr_abs": round(float(atr), 8),
        "ema_9": round(float(ema9[-1]), 8),
        "ema_21": round(float(ema21[-1]), 8),
        "ema_50": round(float(ema50[-1]), 8),
        "sma_200": round(float(sma200), 8),
        "macd_hist": round(float(macd_hist), 8),
        "bb_pct": bb_pct,
        "bb_upper": round(float(bb_upper), 8),
        "bb_lower": round(float(bb_lower), 8),
        "volume_ratio": vol_ratio,
        "pct_1h": pct_1h,
        "pct_4h": pct_4h,
        "pct_24h": pct_24h,
        "pct_7d": pct_7d,
        "consec_down": consec_down,
        "consec_up": consec_up,
        "ema_bullish_stack": bool(ema_bullish_stack),
        "ema_bearish_stack": bool(ema_bearish_stack),
        "above_sma200": bool(above_200),
        "resistance_20": resist_20,
        "support_20": support_20,
        "dist_to_resistance_pct": dist_to_resist,
        "dist_to_support_pct": dist_to_support,
    }


def compute_composite_score(tech: dict, regime: str, fng: int) -> dict:
    """Score a symbol 0-100 on BUY/SELL potential using multiple factors.

    Returns: {"buy_score": float, "sell_score": float, "verdict": str, "factors": list}
    """
    buy_score = 50.0
    sell_score = 50.0
    factors = []

    if not tech:
        return {"buy_score": 0, "sell_score": 0, "verdict": "NO_DATA", "factors": []}

    # --- RSI factor ---
    rsi = tech.get("rsi_14", 50)
    if rsi < 30:
        buy_score += 15
        factors.append(f"RSI oversold ({rsi:.0f})")
    elif rsi < 40:
        buy_score += 8
        factors.append(f"RSI nearing oversold ({rsi:.0f})")
    elif rsi > 70:
        sell_score += 15
        factors.append(f"RSI overbought ({rsi:.0f})")
    elif rsi > 60:
        sell_score += 5

    # RSI(2) extreme — strong mean-reversion signal
    rsi2 = tech.get("rsi_2", 50)
    if rsi2 < 10:
        buy_score += 12
        factors.append(f"RSI(2) extreme oversold ({rsi2:.0f})")
    elif rsi2 > 90:
        sell_score += 12
        factors.append(f"RSI(2) extreme overbought ({rsi2:.0f})")

    # --- Trend structure ---
    if tech.get("ema_bullish_stack"):
        buy_score += 10
        factors.append("EMA 9>21>50 bullish stack")
    elif tech.get("ema_bearish_stack"):
        sell_score += 10
        factors.append("EMA 9<21<50 bearish stack")

    if tech.get("above_sma200"):
        buy_score += 5
        factors.append("Above SMA200")
    else:
        sell_score += 5
        factors.append("Below SMA200")

    # --- MACD ---
    macd = tech.get("macd_hist", 0)
    if macd > 0:
        buy_score += 5
        factors.append("MACD histogram positive")
    elif macd < 0:
        sell_score += 5
        factors.append("MACD histogram negative")

    # --- Bollinger Bands ---
    bb = tech.get("bb_pct", 0.5)
    if bb < 0.1:
        buy_score += 10
        factors.append(f"Near lower BB ({bb:.0%})")
    elif bb > 0.9:
        sell_score += 10
        factors.append(f"Near upper BB ({bb:.0%})")

    # --- Momentum (24h change) ---
    pct_24h = tech.get("pct_24h", 0)
    if pct_24h < -5:
        buy_score += 8  # Mean reversion opportunity
        factors.append(f"24h down {pct_24h:.1f}% (bounce potential)")
    elif pct_24h > 5:
        buy_score += 5  # Momentum
        sell_score += 3  # Potential exhaustion
        factors.append(f"24h up {pct_24h:+.1f}% (momentum)")

    # --- Volume confirmation ---
    vol = tech.get("volume_ratio", 1.0)
    if vol > 1.5:
        buy_score += 5 if pct_24h < 0 else 3
        factors.append(f"Volume spike ({vol:.1f}x avg)")

    # --- Consecutive bars ---
    consec_down = tech.get("consec_down", 0)
    if consec_down >= 3:
        buy_score += 8
        factors.append(f"{consec_down} consecutive down bars (bounce)")
    consec_up = tech.get("consec_up", 0)
    if consec_up >= 3:
        sell_score += 5
        factors.append(f"{consec_up} consecutive up bars")

    # --- Regime factor ---
    if regime == "MEAN_REVERSION":
        buy_score += 5 if rsi < 45 else 0
        factors.append(f"Regime: Mean-Reverting")
    elif regime == "TRENDING":
        if pct_24h > 0:
            buy_score += 5
        else:
            sell_score += 5
        factors.append(f"Regime: Trending")
    else:
        factors.append(f"Regime: Random Walk")

    # --- Fear & Greed ---
    if fng <= 20:
        buy_score += 10
        factors.append(f"Extreme Fear (F&G={fng})")
    elif fng >= 80:
        sell_score += 10
        factors.append(f"Extreme Greed (F&G={fng})")

    # --- Risk proximity (support/resistance) ---
    dist_resist = tech.get("dist_to_resistance_pct", 0)
    dist_support = tech.get("dist_to_support_pct", 0)
    if dist_support < 1.0:
        buy_score += 5
        factors.append(f"Near support ({dist_support:.1f}% away)")
    if dist_resist < 1.0:
        sell_score += 5
        factors.append(f"Near resistance ({dist_resist:.1f}% away)")

    # Normalize to 0-100
    buy_score = max(0, min(100, buy_score))
    sell_score = max(0, min(100, sell_score))

    # Determine verdict
    spread = buy_score - sell_score
    if spread > 15:
        verdict = "STRONG_BUY"
    elif spread > 5:
        verdict = "BUY"
    elif spread < -15:
        verdict = "STRONG_SELL"
    elif spread < -5:
        verdict = "SELL"
    else:
        verdict = "NEUTRAL"

    return {
        "buy_score": round(buy_score, 1),
        "sell_score": round(sell_score, 1),
        "verdict": verdict,
        "factors": factors,
    }


def run_market_analysis() -> dict:
    """Scan extended universe and produce full market analysis."""
    logger.info("=" * 60)
    logger.info(f"QuanEngine Market Analysis — {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    router = RegimeRouter()
    fng = fetch_fear_greed()
    logger.info(f"Fear & Greed Index: {fng}")

    # De-duplicate symbols
    all_symbols = list(dict.fromkeys(config.SYMBOLS_EXTENDED))
    logger.info(f"Scanning {len(all_symbols)} pairs...")

    # Load existing active signals
    active_picks = []
    if os.path.exists(config.SIGNALS_PATH):
        try:
            with open(config.SIGNALS_PATH) as f:
                data = json.load(f)
            active_picks = data.get("active_picks", [])
        except Exception:
            pass

    active_symbols = {p.get("symbol") for p in active_picks}

    market_overview = []

    for symbol in all_symbols:
        try:
            df = fetch_klines(symbol, "1h", 500)
            if df.empty or len(df) < 200:
                logger.warning(f"{symbol}: insufficient data")
                continue

            # Technicals
            tech = compute_technicals(df)
            if not tech:
                continue

            # Regime
            regime = router.classify(df["close"].values)
            hurst = router._hurst._compute_hurst(df["close"].values[-config.HURST_WINDOW:])

            # Composite score
            score = compute_composite_score(tech, regime, fng)

            # 24h volume in USD
            vol_24h_usd = round(float(df["quote_volume"].iloc[-24:].sum()), 0) if len(df) >= 24 else 0

            entry = {
                "symbol": symbol,
                "regime": regime,
                "hurst": round(hurst, 4),
                "is_active_pick": symbol in active_symbols,
                "technicals": tech,
                "score": score,
                "volume_24h_usd": vol_24h_usd,
            }
            market_overview.append(entry)
            logger.info(
                f"{symbol}: {score['verdict']} (buy={score['buy_score']}, sell={score['sell_score']}) "
                f"regime={regime} H={hurst:.3f}"
            )

        except Exception as e:
            logger.error(f"{symbol}: {e}")
            continue

    # --- Rank next-best picks ---
    # Exclude already-active symbols, rank by buy_score descending
    candidates = [
        m for m in market_overview
        if not m["is_active_pick"] and m["score"]["verdict"] in ("STRONG_BUY", "BUY")
    ]
    candidates.sort(key=lambda x: x["score"]["buy_score"], reverse=True)
    next_best_picks = candidates[:15]  # Top 15

    # Also include sell candidates
    sell_candidates = [
        m for m in market_overview
        if not m["is_active_pick"] and m["score"]["verdict"] in ("STRONG_SELL", "SELL")
    ]
    sell_candidates.sort(key=lambda x: x["score"]["sell_score"], reverse=True)
    next_best_sells = sell_candidates[:10]

    # --- Market summary ---
    verdicts = [m["score"]["verdict"] for m in market_overview]
    regimes = [m["regime"] for m in market_overview]
    avg_rsi = np.mean([m["technicals"]["rsi_14"] for m in market_overview]) if market_overview else 50
    avg_24h = np.mean([m["technicals"]["pct_24h"] for m in market_overview]) if market_overview else 0
    avg_buy = np.mean([m["score"]["buy_score"] for m in market_overview]) if market_overview else 50
    avg_sell = np.mean([m["score"]["sell_score"] for m in market_overview]) if market_overview else 50

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "fear_greed": fng,
        "symbols_scanned": len(market_overview),
        "verdict_distribution": {
            "STRONG_BUY": verdicts.count("STRONG_BUY"),
            "BUY": verdicts.count("BUY"),
            "NEUTRAL": verdicts.count("NEUTRAL"),
            "SELL": verdicts.count("SELL"),
            "STRONG_SELL": verdicts.count("STRONG_SELL"),
        },
        "regime_distribution": {
            "TRENDING": regimes.count("TRENDING"),
            "MEAN_REVERSION": regimes.count("MEAN_REVERSION"),
            "RANDOM": regimes.count("RANDOM"),
        },
        "avg_rsi_14": round(float(avg_rsi), 1),
        "avg_24h_change": round(float(avg_24h), 2),
        "avg_buy_score": round(float(avg_buy), 1),
        "avg_sell_score": round(float(avg_sell), 1),
        "market_bias": "BULLISH" if avg_buy > avg_sell + 5 else ("BEARISH" if avg_sell > avg_buy + 5 else "MIXED"),
        "active_signals_count": len(active_picks),
    }

    # --- Build output ---
    # Generate EST timestamp
    from datetime import timezone
    utc_now = datetime.now(timezone.utc)
    est_offset = timezone(timedelta(hours=-5))
    est_now = utc_now.astimezone(est_offset)
    est_readable = est_now.strftime("%b %-d, %-I:%M %p EST")
    # Windows strftime doesn't support %-d, fallback
    try:
        est_readable = est_now.strftime("%b %-d, %-I:%M %p EST")
    except ValueError:
        est_readable = est_now.strftime("%b %d, %I:%M %p EST").replace(" 0", " ")

    output = {
        "updated_at": datetime.utcnow().isoformat(),
        "updated_at_est": est_readable,
        "engine": "QuanEngine v1.0 — Market Analysis",
        "market_summary": summary,
        "active_signals": active_picks,
        "next_best_buys": [
            _format_pick(p) for p in next_best_picks
        ],
        "next_best_sells": [
            _format_pick(p) for p in next_best_sells
        ],
        "market_overview": [
            _format_overview(m) for m in sorted(
                market_overview,
                key=lambda x: x["score"]["buy_score"],
                reverse=True,
            )
        ],
    }

    # Export
    output_path = os.path.join(config.DATA_DIR, "market_analysis.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("=" * 60)
    logger.info(f"Analysis complete: {len(market_overview)} pairs scanned")
    logger.info(f"Next best buys: {len(next_best_picks)}")
    logger.info(f"Market bias: {summary['market_bias']}")
    logger.info(f"Exported to {output_path}")
    logger.info("=" * 60)

    return output


def _format_pick(entry: dict) -> dict:
    """Format a market overview entry as a pick recommendation."""
    t = entry["technicals"]
    s = entry["score"]
    return {
        "symbol": entry["symbol"],
        "verdict": s["verdict"],
        "buy_score": s["buy_score"],
        "sell_score": s["sell_score"],
        "price": t["price"],
        "rsi_14": t["rsi_14"],
        "rsi_2": t["rsi_2"],
        "atr_pct": t["atr_pct"],
        "pct_24h": t["pct_24h"],
        "pct_7d": t["pct_7d"],
        "regime": entry["regime"],
        "hurst": entry["hurst"],
        "volume_24h_usd": entry.get("volume_24h_usd", 0),
        "ema_bullish_stack": t.get("ema_bullish_stack", False),
        "above_sma200": t.get("above_sma200", False),
        "bb_pct": t["bb_pct"],
        "support_20": t["support_20"],
        "resistance_20": t["resistance_20"],
        "factors": s["factors"],
    }


def _format_overview(entry: dict) -> dict:
    """Compact format for the full overview table."""
    t = entry["technicals"]
    s = entry["score"]
    return {
        "symbol": entry["symbol"],
        "price": t["price"],
        "verdict": s["verdict"],
        "buy_score": s["buy_score"],
        "sell_score": s["sell_score"],
        "rsi_14": t["rsi_14"],
        "pct_24h": t["pct_24h"],
        "pct_7d": t["pct_7d"],
        "atr_pct": t["atr_pct"],
        "regime": entry["regime"],
        "hurst": entry["hurst"],
        "volume_ratio": t["volume_ratio"],
        "above_sma200": t.get("above_sma200", False),
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    run_market_analysis()
