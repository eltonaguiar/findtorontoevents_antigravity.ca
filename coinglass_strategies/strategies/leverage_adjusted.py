"""S5: Leverage-Adjusted Ratio — squeeze risk detection."""
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
    deviation = glob - 1.0
    leverage_signal = deviation * (1 if funding > 0 else -1)
    if abs(leverage_signal) < 0.10:
        return None
    direction = "SHORT" if leverage_signal > 0 else "LONG"
    severity = min(abs(leverage_signal) / 0.15, 3.0)
    conf = 0.55 + 0.05 * severity
    conf = round(min(conf, 0.70), 3)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_leverage_squeeze",
                  confidence=conf, reason=f"Leverage squeeze: ratio={glob:.3f}, funding={funding:.6f}, signal={leverage_signal:.4f}",
                  ratios=current_ratios)
