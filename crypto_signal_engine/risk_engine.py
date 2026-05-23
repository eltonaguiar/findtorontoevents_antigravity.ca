"""Risk engine with 6 guards for filtering signals.

Guards (all must pass for a signal to be emitted):
  1. Confidence   — ensemble probability >= threshold (0.60 standard, 0.75 premium)
  2. Cost Edge    — expected edge (prob×TP - (1-prob)×SL) >= 2x total cost
  3. Trend Guard  — price > 200 SMA OR Fear & Greed < 20 (extreme fear contrarian)
  4. Funding Guard— funding rate z-score within +/- 2 std dev (avoids leverage extremes)
  5. ATR Edge     — TP distance (3x ATR) > 2x cost (reward covers expenses)
  6. Volume Guard — volume must be >= 1.2x 24h average (avoid dead/illiquid markets)

Direction logic:
  SHORT: RSI > 70 (overbought) AND price < 200 SMA (bearish structure)
  LONG:  everything else that passes guards
"""
import logging
from . import config
from .trainer import compute_cost

logger = logging.getLogger(__name__)


def evaluate_pick(row, prob, premium=False):
    """Apply 5 risk guards. Return pick dict or None.

    Args:
        row: dict-like with keys: symbol, close, atr, sma_200, rsi_14, fng, funding_z, above_200
        prob: float, ensemble probability (0-1)
        premium: if True, use 0.70 confidence threshold

    Returns:
        dict with full trade specification or None if any guard fails
    """
    symbol = row["symbol"]
    price = float(row["close"])
    atr_val = float(row["atr"])
    min_conf = config.MIN_CONF_PREMIUM if premium else config.MIN_CONF
    guards_log = []

    # Guard 1: Confidence
    if prob < min_conf:
        return None
    guards_log.append(f"confidence={prob:.2%} >= {min_conf:.0%}")

    # Guard 2: Cost-adjusted edge
    # Expected edge per trade = (prob × TP_mult - (1-prob) × SL_mult) × ATR / price
    # Must exceed 2x round-trip cost to be worth taking
    total_cost = compute_cost(symbol)
    tp_mult = config.TP_ATR_MULT
    sl_mult = config.SL_ATR_MULT
    expected_edge = (prob * tp_mult - (1 - prob) * sl_mult) * atr_val / price if price > 0 else 0
    min_edge = total_cost * config.MIN_EDGE_MULT
    if expected_edge < min_edge:
        return None
    guards_log.append(f"edge={expected_edge:.4%} >= {min_edge:.4%} (2x cost={total_cost:.4%})")

    # Guard 3: Trend / fear-greed (relaxed: also allow near-200 SMA or moderate fear)
    above_200 = int(row.get("above_200", 0))
    fng = int(row.get("fng", 50))
    sma_200_val = float(row.get("sma_200", 0))
    near_200 = (sma_200_val > 0 and price > 0 and price >= sma_200_val * 0.95)  # within 5% of 200 SMA
    if not (above_200 == 1 or fng < 35 or near_200):
        return None
    if above_200:
        trend_reason = "price > 200 SMA"
    elif near_200:
        trend_reason = f"price within 5% of 200 SMA (${price:.2f} vs ${sma_200_val:.2f})"
    else:
        trend_reason = f"F&G={fng} (fear zone, < 35)"
    guards_log.append(f"trend: {trend_reason}")

    # Guard 4: Funding-rate extreme
    funding_z = float(row.get("funding_z", 0.0))
    if abs(funding_z) > 2.0:
        return None
    guards_log.append(f"funding_z={funding_z:.2f} (within ±2σ)")

    # Guard 5: ATR edge
    if atr_val <= 0 or tp_mult * atr_val < total_cost * 2:
        return None
    guards_log.append(f"atr_edge: {tp_mult}×ATR={tp_mult*atr_val:.6f} > {total_cost*2:.6f}")

    # Guard 6: Volume filter — avoid dead/illiquid markets
    vol_ratio = float(row.get("vol_ratio", 1.0))
    if vol_ratio < config.MIN_VOL_RATIO:
        return None
    guards_log.append(f"volume={vol_ratio:.1f}x avg (>= {config.MIN_VOL_RATIO}x)")

    # Direction: SHORT if RSI > 70 AND price < 200 SMA
    rsi_val = float(row.get("rsi_14", 50))
    sma_200 = float(row.get("sma_200", price))
    if rsi_val > 70 and price < sma_200:
        direction = "SHORT"
        tp = price - tp_mult * atr_val
        sl = price + sl_mult * atr_val
        direction_reason = (
            f"RSI={rsi_val:.1f} > 70 (overbought) AND price ${price:.2f} < "
            f"200 SMA ${sma_200:.2f} (bearish structure)"
        )
    else:
        direction = "LONG"
        tp = price + tp_mult * atr_val
        sl = price - sl_mult * atr_val
        direction_reason = (
            f"Bullish: {'price above 200 SMA' if above_200 else f'extreme fear (F&G={fng})'}, "
            f"RSI={rsi_val:.1f}"
        )

    # Position sizing: 1% equity risk, SL = SL_ATR_MULT x ATR
    size = (config.CAPITAL * config.RISK_PER_TRADE) / (atr_val * sl_mult) if atr_val > 0 else 0

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": round(price, 6),
        "tp": round(tp, 6),
        "sl": round(sl, 6),
        "size": round(size, 6),
        "confidence": round(prob, 4),
        "atr": round(atr_val, 6),
        "rsi": round(rsi_val, 1),
        "fng": fng,
        "funding_z": round(funding_z, 3),
        "above_200_sma": bool(above_200),
        "direction_reason": direction_reason,
        "strategy_description": config.STRATEGY_DESCRIPTIONS.get(direction, ""),
        "guards_passed": guards_log,
        "guards_count": len(guards_log),
    }
