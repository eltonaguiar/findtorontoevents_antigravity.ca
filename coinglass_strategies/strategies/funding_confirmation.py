"""S6: Funding-Rate Confirmation — ratio + funding confluence."""
from typing import Dict, List, Optional
from .base import Signal
from .. import config

def run(symbol: str, recent_rows: List[Dict], current_ratios: Dict) -> Optional[Signal]:
    glob = current_ratios.get("global")
    if glob is None:
        return None
    funding = None
    for row in reversed(recent_rows):
        if row.get("funding_rate") is not None:
            funding = float(row["funding_rate"])
            break
    if funding is None:
        return None
    threshold = config.FUNDING_RATIO_THRESHOLD
    bullish = glob > threshold and funding > 0
    bearish = glob < (2 - threshold) and funding < 0
    if not bullish and not bearish:
        return None
    direction = "LONG" if bullish else "SHORT"
    ratio_strength = abs(glob - 1.0)
    funding_strength = abs(funding) * 10000
    agreement = min(ratio_strength + funding_strength, 1.0)
    conf = 0.60 + 0.05 * min(agreement / 0.2, 3.0)
    conf = round(min(conf, 0.75), 3)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_funding_confluence",
                  confidence=conf, reason=f"Funding confirms ratio: ratio={glob:.3f}, funding={funding:.6f} ({'bullish' if bullish else 'bearish'})",
                  ratios=current_ratios)
