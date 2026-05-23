"""S1: Extreme Ratio Reversion — contrarian Z-score spike reversal."""
import math
from typing import Dict, List, Optional
from .base import Signal
from .. import config

def run(symbol: str, recent_rows: List[Dict], current_ratios: Dict) -> Optional[Signal]:
    values = []
    for row in recent_rows:
        val = row.get("taker_ratio") or row.get("global_ratio")
        if val is not None:
            values.append(float(val))
    if len(values) < 10:
        return None
    current = current_ratios.get("taker") or current_ratios.get("global")
    if current is None:
        return None
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0
    if std == 0:
        return None
    z_score = (current - mean) / std
    threshold = config.EXTREME_REVERSION_Z_THRESHOLD
    if abs(z_score) < threshold:
        return None
    direction = "SHORT" if z_score > 0 else "LONG"
    conf = 0.55 + 0.05 * min(abs(z_score) - threshold, 4.0)
    conf = round(min(conf, 0.75), 3)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_extreme_reversion",
                  confidence=conf, reason=f"Taker ratio Z-score={z_score:.2f} (mean={mean:.3f}, std={std:.3f})",
                  ratios=current_ratios)
