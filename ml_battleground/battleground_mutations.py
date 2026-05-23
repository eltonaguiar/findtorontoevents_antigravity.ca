"""
Battleground Strategy Mutations — Generate relaxed-parameter variants
for higher-frequency pick generation.

Takes the best strategies from Systems A-F and creates mutations with:
1. Wider entry gates (lower confidence thresholds)
2. Relaxed RSI/indicator ranges
3. Multiple TP/SL variants (tight, standard, wide)
4. Cross-pollination between systems

Runs as part of the mutation lab pipeline or standalone.
Outputs picks to genome/data/battleground_mutation_picks.json
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent dirs for imports
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "ml_battleground"))

import numpy as np

# ── Config ──
DATA_DIR = _ROOT / "genome" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "battleground_mutation_picks.json"

# Symbols to scan
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "NEARUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "FETUSDT",
]

# Mutation templates: (name, modifications_dict)
# Each mutation relaxes parameters to increase signal frequency
STRATEGY_MUTATIONS = [
    # ── Connors RSI-2 Mutations ──
    {
        "name": "M_connors_rsi2_relaxed",
        "base": "connors_rsi2",
        "desc": "RSI(2) with wider entry bands (30/70 vs 20/80)",
        "rsi2_buy_threshold": 30,      # was 20
        "rsi2_sell_threshold": 70,     # was 80
        "rsi14_buy_floor": 10,         # was 15
        "rsi14_sell_ceil": 90,         # was 85
        "trend_sma": 100,             # was 200 — faster trend
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.2,
        "min_confidence": 0.45,
    },
    {
        "name": "M_connors_rsi2_aggressive",
        "base": "connors_rsi2",
        "desc": "RSI(2) with very wide bands for max frequency",
        "rsi2_buy_threshold": 35,
        "rsi2_sell_threshold": 65,
        "rsi14_buy_floor": 5,
        "rsi14_sell_ceil": 95,
        "trend_sma": 50,
        "tp_atr_mult": 1.8,
        "sl_atr_mult": 1.0,
        "min_confidence": 0.40,
    },
    # ── EMA Stack Mutations ──
    {
        "name": "M_ema_stack_fast",
        "base": "ema_stack",
        "desc": "Faster EMAs (5/13/34) for quicker signals",
        "ema_fast": 5,      # was 9
        "ema_mid": 13,      # was 21
        "ema_slow": 34,     # was 50
        "proximity_atr": 0.8,  # was 0.5 — wider proximity band
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.3,
        "min_confidence": 0.45,
    },
    {
        "name": "M_ema_stack_ultrafast",
        "base": "ema_stack",
        "desc": "Ultra-fast EMAs (3/8/21) for scalping",
        "ema_fast": 3,
        "ema_mid": 8,
        "ema_slow": 21,
        "proximity_atr": 1.0,
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.0,
        "min_confidence": 0.42,
    },
    # ── RSI+MACD Confluence Mutations ──
    {
        "name": "M_rsi_macd_relaxed",
        "base": "rsi_macd_confluence",
        "desc": "Wider RSI bands (35/65 vs 30/70) for more triggers",
        "rsi_buy_threshold": 35,   # was 30
        "rsi_sell_threshold": 65,  # was 70
        "macd_confirm_bars": 5,    # was 3 — more time to confirm
        "trend_pct": 0.95,         # was 0.98 — relaxed trend filter
        "tp_atr_mult": 2.2,
        "sl_atr_mult": 1.2,
        "min_confidence": 0.45,
    },
    # ── Bollinger Band Mean Reversion Mutations ──
    {
        "name": "M_bb_reversion_tight",
        "base": "bb_mean_reversion",
        "desc": "Tighter BB (1.5 std) for more touch signals",
        "bb_period": 20,
        "bb_std": 1.5,         # was 2.0 — more frequent touches
        "rsi_buy": 40,         # was 35 — wider entry
        "rsi_sell": 60,        # was 65 — wider entry
        "tp_atr_mult": 1.8,
        "sl_atr_mult": 1.0,
        "min_confidence": 0.45,
    },
    {
        "name": "M_bb_reversion_wide",
        "base": "bb_mean_reversion",
        "desc": "Standard BB with very relaxed RSI",
        "bb_period": 20,
        "bb_std": 2.0,
        "rsi_buy": 45,
        "rsi_sell": 55,
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.5,
        "min_confidence": 0.42,
    },
    # ── Swing Failure Pattern Mutations ──
    {
        "name": "M_sfp_sensitive",
        "base": "swing_failure_pattern",
        "desc": "Lower wick threshold (20% vs 30%) for more signals",
        "wick_pct": 0.20,         # was 0.30
        "swing_lookback": 15,      # was 20 — shorter swings
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.2,
        "min_confidence": 0.42,
    },
    # ── Ornstein-Uhlenbeck Mutations ──
    {
        "name": "M_ou_sensitive",
        "base": "ornstein_uhlenbeck",
        "desc": "Lower sigma threshold (0.7 vs 1.0) for more mean-reversion signals",
        "sigma_threshold": 0.7,   # was 1.0
        "half_life_max": 120,     # was 80 — allow slower reversions
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.2,
        "min_confidence": 0.42,
    },
    # ── Keltner Channel Mutations ──
    {
        "name": "M_keltner_sensitive",
        "base": "keltner_channel_breakout",
        "desc": "Narrower Keltner (1.5x ATR vs 2x) for more breakouts",
        "kc_mult": 1.5,           # was 2.0
        "vol_threshold": 1.2,     # was 1.5
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 1.3,
        "min_confidence": 0.42,
    },
    # ── RSI Divergence Mutations ──
    {
        "name": "M_rsi_div_sensitive",
        "base": "rsi_divergence",
        "desc": "Wider RSI bands and lower volume gate",
        "rsi_buy_max": 50,        # was 45
        "rsi_sell_min": 50,       # was 55
        "vol_threshold": 1.2,     # was 1.5
        "swing_bars": 4,          # was 5
        "tp_atr_mult": 2.2,
        "sl_atr_mult": 1.2,
        "min_confidence": 0.42,
    },
    # ── Fear/Greed Contrarian Mutations ──
    {
        "name": "M_fear_buy_relaxed",
        "base": "fear_capitulation_dca",
        "desc": "Wider fear gate (F&G<=25 vs <=15)",
        "fg_threshold": 25,       # was 15
        "consecutive_bars": 2,    # was 3
        "vol_threshold": 0.6,     # was 0.8
        "tp_atr_mult": 3.0,
        "sl_atr_mult": 1.5,
        "min_confidence": 0.45,
    },
    # ── System F Claws of Doom Crossbreeds ──
    {
        "name": "M_claw_momentum_breakout",
        "base": "claws_momentum",
        "desc": "Momentum breakout with tighter TP from Claws",
        "tp_pct": 0.06,           # 6% (Claws uses 8%)
        "sl_pct": 0.04,           # 4% (Claws uses 6%)
        "rsi_min": 55,
        "vol_mult": 1.5,
        "min_confidence": 0.45,
    },
    {
        "name": "M_claw_fear_contrarian",
        "base": "claws_fear",
        "desc": "Extreme fear contrarian with wider trigger",
        "fg_threshold": 20,       # Claws uses extreme only
        "tp_pct": 0.05,
        "sl_pct": 0.04,
        "min_confidence": 0.45,
    },
    {
        "name": "M_claw_funding_carry",
        "base": "claws_funding",
        "desc": "Funding rate carry with lower threshold",
        "funding_threshold": 0.0002,  # Claws uses 0.0003
        "tp_pct": 0.025,
        "sl_pct": 0.015,
        "min_confidence": 0.42,
    },
    # ── NEW: Claws of Doom — Crash Reversal Bounce Mutations ──
    {
        "name": "M_claw_crash_reversal_relaxed",
        "base": "claws_crash_reversal",
        "desc": "Crash reversal with lower drop threshold (5% vs 10%)",
        "drop_threshold": -5.0,       # Claws needs -10% — too strict, rarely triggers
        "rsi_max": 40,                # RSI below 40 = oversold enough
        "tp_pct": 0.05,              # +5% TP
        "sl_pct": 0.04,              # -4% SL
        "min_confidence": 0.45,
    },
    {
        "name": "M_claw_crash_reversal_sensitive",
        "base": "claws_crash_reversal",
        "desc": "Very sensitive crash reversal (3% drop + volume spike)",
        "drop_threshold": -3.0,       # Even more relaxed
        "rsi_max": 45,
        "vol_mult": 1.3,             # Require some volume spike
        "tp_pct": 0.04,
        "sl_pct": 0.03,
        "min_confidence": 0.42,
    },
    # ── NEW: Claws of Doom — RSI Overbought Short Mutations ──
    {
        "name": "M_claw_rsi_short_relaxed",
        "base": "claws_rsi_short",
        "desc": "RSI overbought short with relaxed RSI (65 vs 70+)",
        "rsi_min": 65,                # Claws needs RSI>70 — relaxed to 65
        "sma_period": 50,             # Price below 50-SMA (faster than 200)
        "tp_pct": 0.05,
        "sl_pct": 0.03,
        "min_confidence": 0.45,
    },
    {
        "name": "M_claw_rsi_short_aggressive",
        "base": "claws_rsi_short",
        "desc": "Very aggressive RSI short (60+ with MACD divergence)",
        "rsi_min": 60,
        "sma_period": 20,             # Faster trend
        "require_macd_div": True,     # MACD histogram declining = confirmation
        "tp_pct": 0.04,
        "sl_pct": 0.025,
        "min_confidence": 0.42,
    },
    # ── NEW: Claws of Doom — EMA Bearish Cross Mutations ──
    {
        "name": "M_claw_ema_bearish",
        "base": "claws_ema_bearish",
        "desc": "EMA bearish cross with faster EMAs (9/21 vs 12/26)",
        "ema_fast": 9,
        "ema_slow": 21,
        "rsi_confirm_max": 50,        # RSI below 50 = bearish bias
        "tp_pct": 0.06,
        "sl_pct": 0.04,
        "min_confidence": 0.45,
    },
    {
        "name": "M_claw_ema_bearish_sensitive",
        "base": "claws_ema_bearish",
        "desc": "Ultra-sensitive EMA bearish (5/13, no RSI filter)",
        "ema_fast": 5,
        "ema_slow": 13,
        "rsi_confirm_max": 55,        # Very relaxed RSI gate
        "tp_pct": 0.05,
        "sl_pct": 0.035,
        "min_confidence": 0.42,
    },
    # ── NEW: Claws of Doom — Deep Fear / Hybrid Mutations ──
    {
        "name": "M_claw_fear_deep",
        "base": "claws_fear",
        "desc": "Deep fear only (F&G<=10) with tight TP for quick scalps",
        "fg_threshold": 10,
        "tp_pct": 0.03,              # Tight 3% TP — quick scalp in deep fear
        "sl_pct": 0.02,
        "min_confidence": 0.50,       # Higher confidence for tighter trade
    },
    {
        "name": "M_claw_fear_momentum_hybrid",
        "base": "claws_fear_momentum",
        "desc": "Fear + momentum bounce: F&G<=25 AND RSI<35 AND positive 4h candle",
        "fg_threshold": 25,
        "rsi_max": 35,
        "require_green_candle": True,  # Close > Open = buyers stepping in
        "tp_pct": 0.06,
        "sl_pct": 0.04,
        "min_confidence": 0.48,
    },
    {
        "name": "M_claw_funding_carry_sensitive",
        "base": "claws_funding",
        "desc": "Ultra-sensitive funding carry (0.0001 threshold)",
        "funding_threshold": 0.0001,   # Much lower than 0.0003
        "tp_pct": 0.02,
        "sl_pct": 0.012,
        "min_confidence": 0.42,
    },
]

# ── Binance data fetch ──
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]


def fetch_klines(symbol: str, interval: str = "4h", limit: int = 300) -> list | None:
    """Fetch klines from Binance with mirror rotation."""
    import requests
    for base in BINANCE_MIRRORS:
        try:
            url = f"{base}/api/v3/klines"
            resp = requests.get(url, params={
                "symbol": symbol, "interval": interval, "limit": limit
            }, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return None


def klines_to_arrays(raw_klines: list) -> dict:
    """Convert raw Binance klines to numpy arrays."""
    opens = np.array([float(k[1]) for k in raw_klines])
    highs = np.array([float(k[2]) for k in raw_klines])
    lows = np.array([float(k[3]) for k in raw_klines])
    closes = np.array([float(k[4]) for k in raw_klines])
    volumes = np.array([float(k[5]) for k in raw_klines])
    return {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}


def compute_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Compute RSI."""
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)
    if len(gains) < period:
        return np.full_like(closes, 50.0)

    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])

    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period

    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[:period] = 50.0
    return rsi


def compute_ema(data: np.ndarray, period: int) -> np.ndarray:
    """Compute EMA."""
    ema = np.zeros_like(data)
    ema[0] = data[0]
    mult = 2.0 / (period + 1)
    for i in range(1, len(data)):
        ema[i] = data[i] * mult + ema[i-1] * (1 - mult)
    return ema


def compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Compute ATR."""
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )
    atr = np.zeros(len(closes))
    if len(tr) < period:
        return atr
    atr[period] = np.mean(tr[:period])
    for i in range(period + 1, len(closes)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i-1]) / period
    return atr


def compute_bb(closes: np.ndarray, period: int = 20, std_mult: float = 2.0):
    """Compute Bollinger Bands."""
    sma = np.convolve(closes, np.ones(period)/period, mode='full')[:len(closes)]
    sma[:period-1] = closes[:period-1]
    std = np.zeros_like(closes)
    for i in range(period-1, len(closes)):
        std[i] = np.std(closes[i-period+1:i+1])
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    pctb = np.where(upper != lower, (closes - lower) / (upper - lower), 0.5)
    return upper, lower, sma, pctb


def compute_macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """Compute MACD."""
    ema_fast = compute_ema(closes, fast)
    ema_slow = compute_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def get_fear_greed() -> int:
    """Fetch Fear & Greed index with retry."""
    import requests
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            if resp.ok:
                return int(resp.json()["data"][0]["value"])
        except Exception:
            pass
        if attempt < 2:
            _time.sleep(2 * (attempt + 1))
    return 50  # default neutral


def run_mutation(mutation: dict, data: dict, symbol: str, current_price: float,
                 atr_val: float, rsi14: float, rsi2: float, ema_fast: np.ndarray,
                 ema_mid: np.ndarray, ema_slow: np.ndarray, bb_upper: np.ndarray,
                 bb_lower: np.ndarray, bb_pctb: np.ndarray, macd_hist: np.ndarray,
                 fear_greed: int) -> list[dict]:
    """Run a single mutation against current market data. Returns list of picks."""
    picks = []
    name = mutation["name"]
    base = mutation["base"]
    closes = data["close"]
    now = datetime.now(timezone.utc)
    min_conf = mutation.get("min_confidence", 0.45)

    # ── RSI-2 based mutations ──
    if base == "connors_rsi2":
        buy_thresh = mutation.get("rsi2_buy_threshold", 20)
        sell_thresh = mutation.get("rsi2_sell_threshold", 80)
        trend_period = mutation.get("trend_sma", 200)
        trend_sma = np.mean(closes[-min(trend_period, len(closes)):])

        if rsi2 < buy_thresh and current_price > trend_sma:
            conf = min(0.80, 0.50 + (buy_thresh - rsi2) * 0.01)
            if conf >= min_conf:
                tp_mult = mutation.get("tp_atr_mult", 2.0)
                sl_mult = mutation.get("sl_atr_mult", 1.2)
                picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                       tp_mult, sl_mult, conf, name, now))
        elif rsi2 > sell_thresh and current_price < trend_sma:
            conf = min(0.80, 0.50 + (rsi2 - sell_thresh) * 0.01)
            if conf >= min_conf:
                tp_mult = mutation.get("tp_atr_mult", 2.0)
                sl_mult = mutation.get("sl_atr_mult", 1.2)
                picks.append(_make_pick(symbol, "SELL", current_price, atr_val,
                                       tp_mult, sl_mult, conf, name, now))

    # ── EMA Stack based mutations ──
    elif base == "ema_stack":
        ef, em, es = ema_fast[-1], ema_mid[-1], ema_slow[-1]
        prox = mutation.get("proximity_atr", 0.5)
        if ef > em > es and abs(current_price - ef) < prox * atr_val:
            spread = (ef - es) / es * 100
            conf = min(0.82, 0.50 + spread * 0.01)
            if conf >= min_conf:
                picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                       mutation.get("tp_atr_mult", 2.5),
                                       mutation.get("sl_atr_mult", 1.3),
                                       conf, name, now))
        elif ef < em < es and abs(current_price - ef) < prox * atr_val:
            spread = (es - ef) / es * 100
            conf = min(0.82, 0.50 + spread * 0.01)
            if conf >= min_conf:
                picks.append(_make_pick(symbol, "SELL", current_price, atr_val,
                                       mutation.get("tp_atr_mult", 2.5),
                                       mutation.get("sl_atr_mult", 1.3),
                                       conf, name, now))

    # ── RSI+MACD Confluence mutations ──
    elif base == "rsi_macd_confluence":
        buy_thresh = mutation.get("rsi_buy_threshold", 30)
        sell_thresh = mutation.get("rsi_sell_threshold", 70)
        if rsi14 < buy_thresh and macd_hist[-1] > macd_hist[-2]:
            conf = min(0.82, 0.55 + (buy_thresh - rsi14) * 0.01)
            if conf >= min_conf:
                picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                       mutation.get("tp_atr_mult", 2.2),
                                       mutation.get("sl_atr_mult", 1.2),
                                       conf, name, now))
        elif rsi14 > sell_thresh and macd_hist[-1] < macd_hist[-2]:
            conf = min(0.82, 0.55 + (rsi14 - sell_thresh) * 0.01)
            if conf >= min_conf:
                picks.append(_make_pick(symbol, "SELL", current_price, atr_val,
                                       mutation.get("tp_atr_mult", 2.2),
                                       mutation.get("sl_atr_mult", 1.2),
                                       conf, name, now))

    # ── Bollinger Band Mean Reversion mutations ──
    elif base == "bb_mean_reversion":
        rsi_buy = mutation.get("rsi_buy", 35)
        rsi_sell = mutation.get("rsi_sell", 65)
        if bb_pctb[-1] <= 0.0 and rsi14 < rsi_buy:
            conf = min(0.85, 0.55 + (rsi_buy - rsi14) * 0.005 + (0 - bb_pctb[-1]) * 0.08)
            if conf >= min_conf:
                picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                       mutation.get("tp_atr_mult", 1.8),
                                       mutation.get("sl_atr_mult", 1.0),
                                       conf, name, now))
        elif bb_pctb[-1] >= 1.0 and rsi14 > rsi_sell:
            conf = min(0.85, 0.55 + (rsi14 - rsi_sell) * 0.005 + (bb_pctb[-1] - 1.0) * 0.08)
            if conf >= min_conf:
                picks.append(_make_pick(symbol, "SELL", current_price, atr_val,
                                       mutation.get("tp_atr_mult", 1.8),
                                       mutation.get("sl_atr_mult", 1.0),
                                       conf, name, now))

    # ── O-U Mean Reversion mutations ──
    elif base == "ornstein_uhlenbeck":
        sigma_thresh = mutation.get("sigma_threshold", 1.0)
        lookback = min(30, len(closes))
        mean_price = np.mean(closes[-lookback:])
        std_price = np.std(closes[-lookback:])
        if std_price > 0:
            zscore = (current_price - mean_price) / std_price
            if zscore < -sigma_thresh:
                conf = min(0.85, 0.50 + abs(zscore) * 0.1)
                if conf >= min_conf:
                    picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                           mutation.get("tp_atr_mult", 2.0),
                                           mutation.get("sl_atr_mult", 1.2),
                                           conf, name, now))
            elif zscore > sigma_thresh:
                conf = min(0.85, 0.50 + abs(zscore) * 0.1)
                if conf >= min_conf:
                    picks.append(_make_pick(symbol, "SELL", current_price, atr_val,
                                           mutation.get("tp_atr_mult", 2.0),
                                           mutation.get("sl_atr_mult", 1.2),
                                           conf, name, now))

    # ── Swing Failure Pattern mutations ──
    elif base == "swing_failure_pattern":
        wick_pct = mutation.get("wick_pct", 0.30)
        lookback = mutation.get("swing_lookback", 20)
        lb = min(lookback, len(data["low"]) - 1)
        swing_low = np.min(data["low"][-lb:])
        swing_high = np.max(data["high"][-lb:])
        bar_range = data["high"][-1] - data["low"][-1]
        if bar_range > 0:
            lower_wick = (min(data["open"][-1], data["close"][-1]) - data["low"][-1]) / bar_range
            upper_wick = (data["high"][-1] - max(data["open"][-1], data["close"][-1])) / bar_range
            if lower_wick >= wick_pct and data["low"][-1] < swing_low and data["close"][-1] > swing_low:
                conf = min(0.82, 0.52 + lower_wick * 0.2)
                if conf >= min_conf:
                    picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                           mutation.get("tp_atr_mult", 2.0),
                                           mutation.get("sl_atr_mult", 1.2),
                                           conf, name, now))
            elif upper_wick >= wick_pct and data["high"][-1] > swing_high and data["close"][-1] < swing_high:
                conf = min(0.82, 0.52 + upper_wick * 0.2)
                if conf >= min_conf:
                    picks.append(_make_pick(symbol, "SELL", current_price, atr_val,
                                           mutation.get("tp_atr_mult", 2.0),
                                           mutation.get("sl_atr_mult", 1.2),
                                           conf, name, now))

    # ── Keltner Channel mutations ──
    elif base == "keltner_channel_breakout":
        # ATR volatility regime gate (v93/v95 crash stress test)
        # Keltner WR drops 72.9% -> 42.1% during crashes.
        # ATR > 2x 30-bar mean -> half size; ATR > 3x -> skip.
        atr_series = compute_atr(data["high"], data["low"], closes)
        atr_mean_30 = float(np.mean(atr_series[max(0, len(atr_series)-30):])) if len(atr_series) > 30 else atr_val
        atr_ratio = atr_val / atr_mean_30 if atr_mean_30 > 0 else 1.0
        if atr_ratio > 3.0:
            print(f"    [mutation/{name}] {symbol}: SKIP — extreme volatility "
                  f"(ATR ratio {atr_ratio:.2f}x > 3x mean)")
        else:
            kc_mult = mutation.get("kc_mult", 2.0)
            vol_thresh = mutation.get("vol_threshold", 1.5)
            ema20 = compute_ema(closes, 20)
            kc_upper = ema20[-1] + kc_mult * atr_val
            kc_lower = ema20[-1] - kc_mult * atr_val
            vol_ratio = data["volume"][-1] / np.mean(data["volume"][-20:]) if np.mean(data["volume"][-20:]) > 0 else 1.0
            high_vol = atr_ratio > 2.0
            pos_scale = 0.5 if high_vol else 1.0
            if current_price > kc_upper and vol_ratio > vol_thresh and rsi14 > 50:
                conf = min(0.75, 0.55 + (current_price - kc_upper) / atr_val * 0.05)
                if high_vol:
                    conf *= 0.85
                    print(f"    [mutation/{name}] {symbol}: HIGH VOL regime "
                          f"(ATR {atr_ratio:.2f}x) — conf reduced, half size")
                if conf >= min_conf:
                    pick = _make_pick(symbol, "BUY", current_price, atr_val,
                                     mutation.get("tp_atr_mult", 2.5),
                                     mutation.get("sl_atr_mult", 1.3),
                                     conf, name, now)
                    pick["position_scale"] = pos_scale
                    pick["high_volatility_regime"] = high_vol
                    pick["atr_ratio"] = round(atr_ratio, 3)
                    picks.append(pick)

    # ── RSI Divergence mutations ──
    elif base == "rsi_divergence":
        rsi_buy_max = mutation.get("rsi_buy_max", 45)
        vol_thresh = mutation.get("vol_threshold", 1.5)
        vol_ratio = data["volume"][-1] / np.mean(data["volume"][-20:]) if np.mean(data["volume"][-20:]) > 0 else 1.0
        sb = mutation.get("swing_bars", 5)
        if len(closes) > sb * 2 and rsi14 < rsi_buy_max and vol_ratio > vol_thresh:
            price_low1 = np.min(closes[-sb*2:-sb])
            price_low2 = np.min(closes[-sb:])
            rsi_arr = compute_rsi(closes, 14)
            rsi_low1 = np.min(rsi_arr[-sb*2:-sb])
            rsi_low2 = np.min(rsi_arr[-sb:])
            if price_low2 < price_low1 and rsi_low2 > rsi_low1:  # bullish divergence
                conf = min(0.82, 0.60 + (rsi_low2 - rsi_low1) * 0.005)
                if conf >= min_conf:
                    picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                           mutation.get("tp_atr_mult", 2.2),
                                           mutation.get("sl_atr_mult", 1.2),
                                           conf, name, now))

    # ── Fear/Greed Contrarian mutations ──
    elif base == "fear_capitulation_dca":
        fg_thresh = mutation.get("fg_threshold", 15)
        if fear_greed <= fg_thresh:
            vol_ratio = data["volume"][-1] / np.mean(data["volume"][-20:]) if np.mean(data["volume"][-20:]) > 0 else 1.0
            vol_min = mutation.get("vol_threshold", 0.8)
            if vol_ratio > vol_min:
                conf = min(0.75, 0.50 + (fg_thresh - fear_greed) * 0.01)
                if conf >= min_conf:
                    picks.append(_make_pick(symbol, "BUY", current_price, atr_val,
                                           mutation.get("tp_atr_mult", 3.0),
                                           mutation.get("sl_atr_mult", 1.5),
                                           conf, name, now))

    # ── Claws of Doom crossbreeds ──
    elif base.startswith("claws_"):
        if base == "claws_momentum":
            if rsi14 >= mutation.get("rsi_min", 55):
                vol_ratio = data["volume"][-1] / np.mean(data["volume"][-20:]) if np.mean(data["volume"][-20:]) > 0 else 1.0
                if vol_ratio >= mutation.get("vol_mult", 1.5):
                    tp_pct = mutation.get("tp_pct", 0.06)
                    sl_pct = mutation.get("sl_pct", 0.04)
                    picks.append(_make_claw_pick(symbol, "BUY", current_price, tp_pct, sl_pct,
                                                 min(0.78, min_conf + vol_ratio * 0.05), name, now))

        elif base == "claws_fear":
            fg_thresh = mutation.get("fg_threshold", 20)
            if fear_greed <= fg_thresh:
                tp_pct = mutation.get("tp_pct", 0.05)
                sl_pct = mutation.get("sl_pct", 0.04)
                conf = min(0.75, 0.50 + (fg_thresh - fear_greed) * 0.01)
                picks.append(_make_claw_pick(symbol, "BUY", current_price, tp_pct, sl_pct,
                                             conf, name, now))

        elif base == "claws_fear_momentum":
            # Hybrid: fear + RSI oversold + green candle = bounce signal
            fg_thresh = mutation.get("fg_threshold", 25)
            rsi_max = mutation.get("rsi_max", 35)
            if fear_greed <= fg_thresh and rsi14 < rsi_max:
                # Check for green candle (close > open)
                if mutation.get("require_green_candle") and data["close"][-1] <= data["open"][-1]:
                    pass  # Red candle — no signal
                else:
                    tp_pct = mutation.get("tp_pct", 0.06)
                    sl_pct = mutation.get("sl_pct", 0.04)
                    conf = min(0.80, 0.50 + (fg_thresh - fear_greed) * 0.008 + (rsi_max - rsi14) * 0.005)
                    picks.append(_make_claw_pick(symbol, "BUY", current_price, tp_pct, sl_pct,
                                                 conf, name, now))

        elif base == "claws_crash_reversal":
            # Crash Reversal Bounce: big drop + oversold RSI = bounce
            drop_thresh = mutation.get("drop_threshold", -5.0)
            rsi_max = mutation.get("rsi_max", 40)
            # Estimate 24h change from last 6 bars (4h candles)
            if len(closes) >= 7:
                change_24h = (closes[-1] - closes[-7]) / closes[-7] * 100
            else:
                change_24h = 0
            if change_24h <= drop_thresh and rsi14 < rsi_max:
                vol_min = mutation.get("vol_mult", 1.0)
                vol_ratio = data["volume"][-1] / np.mean(data["volume"][-20:]) if np.mean(data["volume"][-20:]) > 0 else 1.0
                if vol_ratio >= vol_min:
                    tp_pct = mutation.get("tp_pct", 0.05)
                    sl_pct = mutation.get("sl_pct", 0.04)
                    conf = min(0.82, 0.50 + abs(change_24h) * 0.01 + (rsi_max - rsi14) * 0.005)
                    picks.append(_make_claw_pick(symbol, "BUY", current_price, tp_pct, sl_pct,
                                                 conf, name, now))

        elif base == "claws_rsi_short":
            # RSI Overbought + SMA Breakdown: short when exhaustion rally
            rsi_min = mutation.get("rsi_min", 65)
            sma_period = mutation.get("sma_period", 50)
            sma_val = np.mean(closes[-min(sma_period, len(closes)):])
            if rsi14 >= rsi_min and current_price < sma_val:
                # Optional MACD divergence confirmation
                if mutation.get("require_macd_div") and not (macd_hist[-1] < macd_hist[-2]):
                    pass  # MACD not confirming — skip
                else:
                    tp_pct = mutation.get("tp_pct", 0.05)
                    sl_pct = mutation.get("sl_pct", 0.03)
                    conf = min(0.80, 0.50 + (rsi14 - rsi_min) * 0.008)
                    picks.append(_make_claw_pick(symbol, "SELL", current_price, tp_pct, sl_pct,
                                                 conf, name, now))

        elif base == "claws_ema_bearish":
            # EMA Bearish Cross: fast EMA crosses below slow EMA
            fast_p = mutation.get("ema_fast", 9)
            slow_p = mutation.get("ema_slow", 21)
            ema_f = compute_ema(closes, fast_p)
            ema_s = compute_ema(closes, slow_p)
            rsi_max = mutation.get("rsi_confirm_max", 50)
            # Cross: fast was above slow 2 bars ago, now below
            if (len(ema_f) >= 3 and ema_f[-1] < ema_s[-1]
                    and ema_f[-3] >= ema_s[-3] and rsi14 < rsi_max):
                tp_pct = mutation.get("tp_pct", 0.06)
                sl_pct = mutation.get("sl_pct", 0.04)
                cross_strength = abs(ema_s[-1] - ema_f[-1]) / ema_s[-1] * 100
                conf = min(0.80, 0.50 + cross_strength * 0.05)
                picks.append(_make_claw_pick(symbol, "SELL", current_price, tp_pct, sl_pct,
                                             conf, name, now))

        elif base == "claws_funding":
            # Funding Rate Carry: fetch current funding and trade against crowd
            _fetch_funding_for_mutation(symbol, mutation, current_price, name, now, min_conf, picks)

    return picks


def _make_claw_pick(symbol, direction, price, tp_pct, sl_pct, conf, strategy, now):
    """Create a standardized Claws-style pick using percentage TP/SL."""
    if direction == "BUY":
        tp = round(price * (1 + tp_pct), 8)
        sl = round(price * (1 - sl_pct), 8)
    else:
        tp = round(price * (1 - tp_pct), 8)
        sl = round(price * (1 + sl_pct), 8)
    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(conf, 4),
        "strategy": strategy,
        "source_system": "battleground_mutations",
        "trust_tier": "SANDBOX",
        "mutation_type": "claws_variant",
        "timestamp": now.isoformat(),
    }


def _fetch_funding_for_mutation(symbol, mutation, current_price, name, now, min_conf, picks):
    """Fetch funding rate and generate carry signal for Claws funding mutation."""
    import requests as _req
    funding_thresh = mutation.get("funding_threshold", 0.0002)
    tp_pct = mutation.get("tp_pct", 0.025)
    sl_pct = mutation.get("sl_pct", 0.015)

    # Multi-source funding rate fetch: OKX → Binance → Bybit
    current_rate = None
    pair = symbol  # e.g. BTCUSDT

    # 1. OKX (no geo-block)
    try:
        inst_id = pair.replace("USDT", "-USDT-SWAP")
        resp = _req.get("https://www.okx.com/api/v5/public/funding-rate",
                        params={"instId": inst_id}, timeout=10)
        if resp.ok:
            data = resp.json().get("data", [])
            if data:
                current_rate = float(data[0].get("fundingRate", 0))
    except Exception:
        pass

    # 2. Binance (may be geo-blocked)
    if current_rate is None:
        try:
            resp = _req.get("https://fapi.binance.com/fapi/v1/premiumIndex",
                            params={"symbol": pair}, timeout=10)
            if resp.ok:
                d = resp.json()
                if isinstance(d, dict):
                    current_rate = float(d.get("lastFundingRate", 0))
                elif isinstance(d, list) and d:
                    current_rate = float(d[0].get("lastFundingRate", 0))
        except Exception:
            pass

    # 3. Bybit
    if current_rate is None:
        try:
            resp = _req.get("https://api.bybit.com/v5/market/tickers",
                            params={"category": "linear", "symbol": pair}, timeout=10)
            if resp.ok:
                items = resp.json().get("result", {}).get("list", [])
                if items:
                    current_rate = float(items[0].get("fundingRate", 0))
        except Exception:
            pass

    if current_rate is None:
        return

    # Generate signal: SHORT when funding very positive, LONG when very negative
    if current_rate > funding_thresh:
        conf = min(0.78, 0.50 + abs(current_rate) * 500)
        if conf >= min_conf:
            picks.append(_make_claw_pick(symbol, "SELL", current_price, tp_pct, sl_pct,
                                         conf, name, now))
    elif current_rate < -funding_thresh:
        conf = min(0.78, 0.50 + abs(current_rate) * 500)
        if conf >= min_conf:
            picks.append(_make_claw_pick(symbol, "BUY", current_price, tp_pct, sl_pct,
                                         conf, name, now))


def _make_pick(symbol, direction, price, atr, tp_mult, sl_mult, conf, strategy, now):
    """Create a standardized pick dict."""
    if direction == "BUY":
        tp = round(price + tp_mult * atr, 8)
        sl = round(price - sl_mult * atr, 8)
    else:
        tp = round(price - tp_mult * atr, 8)
        sl = round(price + sl_mult * atr, 8)
    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": round(price, 8),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(conf, 4),
        "strategy": strategy,
        "source_system": "battleground_mutations",
        "trust_tier": "SANDBOX",
        "mutation_type": "battleground_variant",
        "timestamp": now.isoformat(),
    }


def run_battleground_mutations():
    """Main entry: scan all symbols with all mutations, output picks."""
    print("=" * 70)
    print("  BATTLEGROUND MUTATIONS — Strategy Variant Scanner")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Mutations: {len(STRATEGY_MUTATIONS)} | Symbols: {len(SYMBOLS)}")
    print("=" * 70)

    fear_greed = get_fear_greed()
    print(f"  Fear & Greed: {fear_greed}")

    all_picks = []
    symbols_scanned = 0

    for symbol in SYMBOLS:
        print(f"\n  Scanning {symbol}...")
        raw = fetch_klines(symbol, "4h", 300)
        if not raw or len(raw) < 50:
            print(f"    [skip] insufficient data")
            continue

        data = klines_to_arrays(raw)
        closes = data["close"]
        current_price = closes[-1]
        symbols_scanned += 1

        # Compute indicators once per symbol
        rsi14 = compute_rsi(closes, 14)[-1]
        rsi2 = compute_rsi(closes, 2)[-1]
        atr = compute_atr(data["high"], data["low"], closes, 14)
        atr_val = atr[-1] if atr[-1] > 0 else current_price * 0.02

        # Multiple EMA sets for different mutations
        ema5 = compute_ema(closes, 5)
        ema8 = compute_ema(closes, 8)
        ema9 = compute_ema(closes, 9)
        ema13 = compute_ema(closes, 13)
        ema21 = compute_ema(closes, 21)
        ema34 = compute_ema(closes, 34)
        ema50 = compute_ema(closes, 50)

        bb_upper, bb_lower, bb_sma, bb_pctb = compute_bb(closes, 20, 2.0)
        _, _, macd_hist = compute_macd(closes)

        print(f"    Price: ${current_price:.4f} | RSI14: {rsi14:.1f} | RSI2: {rsi2:.1f} | ATR: {atr_val:.6f}")

        for mutation in STRATEGY_MUTATIONS:
            # Select appropriate EMAs for this mutation
            base = mutation["base"]
            if base == "ema_stack":
                ef_period = mutation.get("ema_fast", 9)
                if ef_period <= 5:
                    ef, em, es = ema5, ema8, ema21
                elif ef_period <= 5:
                    ef, em, es = ema5, ema13, ema34
                else:
                    ef, em, es = ema9, ema21, ema50
            else:
                ef, em, es = ema9, ema21, ema50

            # Recompute BB if mutation uses different params
            if base == "bb_mean_reversion":
                bb_std = mutation.get("bb_std", 2.0)
                if bb_std != 2.0:
                    _, _, _, bb_pctb_mut = compute_bb(closes, 20, bb_std)
                else:
                    bb_pctb_mut = bb_pctb
            else:
                bb_pctb_mut = bb_pctb

            try:
                picks = run_mutation(
                    mutation, data, symbol, current_price,
                    atr_val, rsi14, rsi2, ef, em, es,
                    bb_upper, bb_lower, bb_pctb_mut, macd_hist, fear_greed
                )
                if picks:
                    print(f"    [+] {mutation['name']}: {len(picks)} pick(s)")
                    all_picks.extend(picks)
            except Exception as e:
                print(f"    [!] {mutation['name']} error: {e}")

    # Deduplicate by symbol+direction (keep highest confidence)
    seen = {}
    for p in all_picks:
        key = f"{p['symbol']}_{p['direction']}_{p['strategy']}"
        if key not in seen or p["confidence"] > seen[key]["confidence"]:
            seen[key] = p
    deduped = list(seen.values())

    # Sort by confidence
    deduped.sort(key=lambda x: x["confidence"], reverse=True)

    output = {
        "system": "battleground_mutations",
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fear_greed": fear_greed,
        "symbols_scanned": symbols_scanned,
        "mutations_run": len(STRATEGY_MUTATIONS),
        "total_raw_signals": len(all_picks),
        "total_picks": len(deduped),
        "active_picks": deduped,
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {len(deduped)} picks from {len(all_picks)} raw signals")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'=' * 70}")

    return deduped


if __name__ == "__main__":
    picks = run_battleground_mutations()
    if picks:
        print(f"\nTop 5 picks:")
        for p in picks[:5]:
            print(f"  {p['symbol']} {p['direction']} @ ${p['entry_price']:.4f} "
                  f"conf={p['confidence']:.2f} [{p['strategy']}]")
