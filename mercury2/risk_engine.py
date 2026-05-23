# -*- coding: utf-8 -*-
"""Mercury 2 — Risk engine: ATR-based TP/SL, cost filter, position sizing.

Offline HF tier / closed-book analytics live in `tools/validate_hf_by_asset_class.py`
and `docs/MERCURY2_HC_VALIDATION_PIPELINE.md` (execution guards stay here).
"""

import logging
from .config import (
    CAPITAL, RISK_PER_TRADE, MIN_CONFIDENCE, MIN_EDGE_MULT,
    MIN_RR, SYMBOL_BLACKLIST, round_trip_cost,
)

log = logging.getLogger("mercury2.risk")



def evaluate_signal(symbol: str, price: float, atr_val: float,
                    prob: float, rsi: float, sma_200: float,
                    above_200: int, fng: int, funding_z: float,
                    strategy: str = "ensemble",
                    atr_avg_30: float = 0.0,
                    vol_ratio: float = 1.0,
                    daily_trend_up: int = -1) -> dict | None:
    """Apply all risk guards and return a trade dict or None.
    
    Guards include trend filter (Price > 200 SMA or F&G < 20) and 
    Daily MTF filter (if daily_trend_up is provided).
    """
    # ── Guard 0: Symbol blacklist ──
    if symbol in SYMBOL_BLACKLIST:
        log.info("BLOCKED %s — in SYMBOL_BLACKLIST (0%% WR)", symbol)
        return None

    total_cost = round_trip_cost(symbol)
    reasons_passed = []

    # ── Guard 1: Confidence (floor from config, e.g. 0.62) ──
    if prob < MIN_CONFIDENCE:
        return None
    reasons_passed.append(f"conf={prob:.3f}≥{MIN_CONFIDENCE}")

    # ── Guard 2: Cost-adjusted edge ──
    cost_threshold = total_cost * MIN_EDGE_MULT
    if prob < cost_threshold:
        return None
    reasons_passed.append(f"edge={prob:.3f}≥{cost_threshold:.4f}")

    # ── Guard 3: Trend / MTF Filter ──
    trend_ok = above_200 == 1
    fear_ok = fng < 20
    if not (trend_ok or fear_ok):
        return None
    
    # Optional MTF Filter: if we have daily trend, it must NOT be bearish unless extreme fear
    if daily_trend_up == 0 and not fear_ok:
        log.info("BLOCKED %s — bearish MTF trend (daily_trend_up=0)", symbol)
        return None

    # ── Guard 4: Funding z-score ──
    if abs(funding_z) > 2.0:
        return None

    # ── Guard 5: ATR-edge ──
    atr_pct = atr_val / price if price > 0 else 0
    if 3 * atr_pct < total_cost * 2:
        return None

    # ── Guard 8: RSI overbought guard ──
    if rsi >= 70:
        log.info("BLOCKED %s — RSI=%.1f >= 70", symbol, rsi)
        return None

    # ── Direction + TP/SL construction ──
    sl_atr_mult = 2.0
    tp_atr_mult = max(3.0, sl_atr_mult * float(MIN_RR))

    direction = "LONG"
    tp = round(price + tp_atr_mult * atr_val, 8)
    tp2 = round(price + (tp_atr_mult * 1.5) * atr_val, 8)
    sl = round(price - sl_atr_mult * atr_val, 8)
    dir_reason = "default_LONG"

    # ── Position sizing ──
    risk_amount = CAPITAL * RISK_PER_TRADE
    sl_dist = abs(price - sl)
    size = risk_amount / sl_dist if sl_dist > 0 else 0
    
    # ── Multipliers ──
    pos_mult = 1.0
    if atr_avg_30 > 0 and atr_val > 1.5 * atr_avg_30:
        pos_mult = 0.5
        size *= pos_mult
        reasons_passed.append("high_ATR_guard→size_halved")

    # ── R:R ratio ──
    tp_dist = abs(tp - price)
    rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": price,
        "take_profit": tp,
        "take_profit_2": tp2,
        "stop_loss": sl,
        "size": round(size, 4),
        "position_multiplier": pos_mult,
        "sizing_multiplier": pos_mult,
        "confidence": round(prob, 4),
        "risk_reward": rr,
        "atr": round(atr_val, 8),
        "rsi_14": round(rsi, 2),
        "vol_ratio": round(vol_ratio, 2),
        "daily_trend_up": daily_trend_up,
        "fng": fng,
        "above_200": above_200,
        "strategy": strategy,
        "status": "ACTIVE",
    }
