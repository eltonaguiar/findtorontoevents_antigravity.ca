"""S3: Ratio Momentum — SMA-3 flow momentum."""
from typing import Dict, List, Optional
from .base import Signal
from .. import config

def run(symbol: str, recent_rows: List[Dict], current_ratios: Dict) -> Optional[Signal]:
    values = []
    for row in recent_rows:
        val = row.get("global_ratio")
        if val is not None:
            values.append(float(val))
    sma_window = config.MOMENTUM_SMA_WINDOW
    min_consecutive = config.MOMENTUM_CONSECUTIVE_MIN
    if len(values) < sma_window + min_consecutive + 1:
        return None
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    sma_values = []
    for i in range(sma_window - 1, len(deltas)):
        window = deltas[i - sma_window + 1:i + 1]
        sma_values.append(sum(window) / len(window))
    if len(sma_values) < min_consecutive:
        return None
    recent_smas = sma_values[-min_consecutive:]
    all_positive = all(s > 0 for s in recent_smas)
    all_negative = all(s < 0 for s in recent_smas)
    if not all_positive and not all_negative:
        return None
    direction = "LONG" if all_positive else "SHORT"
    consecutive = len(recent_smas)
    conf = 0.50 + 0.05 * min(consecutive, 3)
    conf = round(min(conf, 0.65), 3)
    avg_sma = sum(recent_smas) / len(recent_smas)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_ratio_momentum",
                  confidence=conf, reason=f"Ratio SMA-3 {'positive' if all_positive else 'negative'} for {consecutive} periods (avg delta={avg_sma:.4f})",
                  ratios=current_ratios)
