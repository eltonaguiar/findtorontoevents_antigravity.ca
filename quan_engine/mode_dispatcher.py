import numpy as np
from dataclasses import dataclass
from typing import Optional
from quan_engine import config

@dataclass
class TradeSetup:
    symbol: str
    direction: str      # BUY or SELL
    mode: str           # SCALP, SWING, POSITION
    entry_price: float
    take_profit: float
    stop_loss: float
    trailing_stop: Optional[float]
    max_hold_bars: int
    rr_ratio: float
    atr: float
    confidence: float
    consensus_pct: float
    strategies_agreed: list

class ModeDispatcher:
    def __init__(self):
        self.modes = config.MODES

    def select_mode(self, hurst_value: float, atr_pct: float) -> str:
        """Select mode based on regime strength and volatility.

        - High Hurst (>0.65) + high ATR → POSITION (strong trend)
        - Medium Hurst or medium ATR → SWING (default)
        - Low ATR (<2%) → SCALP (tight range, quick trades)
        """
        if hurst_value > 0.65 and atr_pct > 3.0:
            return "POSITION"
        elif atr_pct < 2.0:
            return "SCALP"
        else:
            return "SWING"

    def create_setup(self, symbol, direction, entry_price, confidence,
                     consensus_pct, strategies_agreed, atr, hurst_value, atr_pct) -> TradeSetup:
        mode = self.select_mode(hurst_value, atr_pct)
        mode_cfg = self.modes[mode]

        # ATR-based TP/SL
        if direction == "BUY":
            tp = entry_price + atr * mode_cfg["atr_tp_mult"]
            sl = entry_price - atr * mode_cfg["atr_sl_mult"]
        else:
            tp = entry_price - atr * mode_cfg["atr_tp_mult"]
            sl = entry_price + atr * mode_cfg["atr_sl_mult"]

        # Trailing stop
        trailing = None
        if mode_cfg["trailing_activation"]:
            if direction == "BUY":
                trailing = entry_price + atr * mode_cfg["trailing_activation"]
            else:
                trailing = entry_price - atr * mode_cfg["trailing_activation"]

        rr = abs(tp - entry_price) / abs(sl - entry_price) if abs(sl - entry_price) > 0 else 0

        return TradeSetup(
            symbol=symbol, direction=direction, mode=mode,
            entry_price=round(entry_price, 8), take_profit=round(tp, 8),
            stop_loss=round(sl, 8), trailing_stop=round(trailing, 8) if trailing else None,
            max_hold_bars=mode_cfg["max_hold_bars"], rr_ratio=round(rr, 2),
            atr=round(atr, 8), confidence=confidence, consensus_pct=consensus_pct,
            strategies_agreed=strategies_agreed
        )
