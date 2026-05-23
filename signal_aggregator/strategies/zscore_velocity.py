"""
Z-Score Velocity - Active Strategy
Statistical momentum detection using Z-score velocity
Timeframe: 5m
Activated: 2026-03-02T18:34:29.176551
"""

"""Strategy 36: Z-Score Velocity
Trades z-score reversals confirmed by z-score rate of change (velocity).
"""
import numpy as np, pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str; direction: str; confidence: float; entry_price: float
    take_profit: float; stop_loss: float; reason: str

class ZscoreVelocityStrategy:
    name = "zscore_velocity"
    version = "0.1.0"

    def _atr(self, d, period=14):
        tr = pd.concat([d['high']-d['low'], abs(d['high']-d['close'].shift()), abs(d['low']-d['close'].shift())], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        signals = []
        if len(df) < 40:
            return signals
        atr = self._atr(df)
        window = 30
        closes = df['close'].iloc[-(window + 5):]
        mean = closes.rolling(window).mean()
        std = closes.rolling(window).std()
        zscore = (closes - mean) / std.replace(0, np.nan)
        zscore = zscore.dropna()
        if len(zscore) < 4:
            return signals
        z_now = zscore.iloc[-1]
        z_velocity = zscore.iloc[-1] - zscore.iloc[-3]
        i = len(df) - 1
        price = df['close'].iloc[i]
        a = atr.iloc[i]
        if a <= 0:
            return signals
        if z_now < -1.5 and z_velocity > 0:
            conf = min(0.5 + abs(z_now) * 0.1 + z_velocity * 0.2, 0.95)
            signals.append(Signal(
                symbol=symbol, direction="BUY", confidence=conf,
                entry_price=price, take_profit=price + 2 * a, stop_loss=price - 1.5 * a,
                reason=f"Z-score {z_now:.2f} < -1.5 with positive velocity {z_velocity:.2f}: oversold recovering"
            ))
        elif z_now > 1.5 and z_velocity < 0:
            conf = min(0.5 + abs(z_now) * 0.1 + abs(z_velocity) * 0.2, 0.95)
            signals.append(Signal(
                symbol=symbol, direction="SELL", confidence=conf,
                entry_price=price, take_profit=price - 2 * a, stop_loss=price + 1.5 * a,
                reason=f"Z-score {z_now:.2f} > 1.5 with negative velocity {z_velocity:.2f}: overbought declining"
            ))
        return signals


# Signal Aggregator Integration
def generate_signal(symbol: str = "ETHUSDT", price_data: dict = None) -> dict:
    """
    Generate signal for signal_aggregator integration.
    
    Returns signal dict or None if no signal.
    """
    import pandas as pd
    
    if price_data is None or len(price_data.get('close', [])) < 20:
        return None
    
    df = pd.DataFrame(price_data)
    
    # Use Z-Score Velocity strategy
    strategy = ZscoreVelocityStrategy()
    signals = strategy.generate_signals(df, symbol)
    
    if not signals:
        return None
    
    sig = signals[0]
    return {
        "symbol": sig.symbol,
        "direction": "LONG" if sig.direction in ["BUY", "LONG"] else "SHORT",
        "confidence": min(sig.confidence + 0.08, 0.95),
        "entry_price": sig.entry_price,
        "tp_price": sig.take_profit,
        "sl_price": sig.stop_loss,
        "reason": sig.reason,
        "system": "velocity_z-score_velocity",
        "timeframe": "5m"
    }

if __name__ == "__main__":
    print("Z-Score Velocity is active")
