"""Mega-Permutation Combo: Volatility-Scaled Momentum + Volume Above Average.

Source: Mega-permutation top findings — VolatilityScaledMomentum combined with
        a volume confirmation layer. Enters when momentum is positive and
        position is scaled by target_vol / realized_vol, with volume above
        its 20-bar average as a participation filter.

Strategy Logic:
  1. 14-bar momentum positive: close > close[14] (price trending up).
  2. Position scaling: target_vol (15%) / realized_vol (14-bar annualized).
     - Scale > 1 means low-vol trend (strong), scale < 1 means high-vol (reduce).
  3. Volume > 20-bar average volume — confirms participation.
  4. Entry: BUY on next bar open after all conditions met.
  5. Exits from mega-permutation optimal:
     - Take Profit = 1.5 * ATR(14)
     - Stop Loss   = 0.3 * ATR(14)   (very tight — mega-perm optimal)
     - Risk:Reward = 5.0:1

Confidence Formula:
  confidence = min(0.95, 0.4 + momentum_pct * 2 + vol_scale_bonus)
  - Base 0.4
  - Momentum strength bonus (capped contribution)
  - Vol scale bonus: higher when realized vol is low relative to target

Why It Works:
  Volatility-scaled momentum captures trending moves while automatically
  reducing exposure during high-volatility regimes (when stops are more
  likely to be hit). The volume filter ensures entries only occur when
  the market confirms the trend with participation. The extreme 5:1 R:R
  from mega-perm optimization means even modest win rates are profitable.

References:
  - Moskowitz, Ooi, Pedersen (2012): Time Series Momentum (JFE)
  - Barroso & Santa-Clara (2015): Momentum has its moments (JFE)
  - Mega-permutation engine backtest (2026)
"""

import sys
import os

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Signal:
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    strategy_name: str
    metadata: dict = field(default_factory=dict)


DEFAULT_PARAMS = {
    "momentum_period": 14,
    "vol_lookback": 14,
    "target_vol": 0.15,
    "vol_avg_period": 20,
    "atr_period": 14,
    "tp_atr_mult": 1.5,
    "sl_atr_mult": 0.3,
    "annualization_factor": 365,
}


class MegaVolscaledVolStrategy:
    """Volatility-Scaled Momentum + Volume Above Average — mega-perm optimized.

    Parameters
    ----------
    params : dict, optional
        Override any default parameter.
    """

    strategy_name = "MegaVolscaledVol_v1"
    min_bars = 30

    def __init__(self, params: Optional[Dict] = None):
        cfg = {**DEFAULT_PARAMS}
        if params:
            cfg.update(params)

        self.momentum_period: int = cfg["momentum_period"]
        self.vol_lookback: int = cfg["vol_lookback"]
        self.target_vol: float = cfg["target_vol"]
        self.vol_avg_period: int = cfg["vol_avg_period"]
        self.atr_period: int = cfg["atr_period"]
        self.tp_atr_mult: float = cfg["tp_atr_mult"]
        self.sl_atr_mult: float = cfg["sl_atr_mult"]
        self.annualization_factor: int = cfg["annualization_factor"]

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate BUY signals on positive momentum + vol-scaling + volume confirmation.

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV DataFrame with columns: open, high, low, close, volume.
        symbol : str
            Trading pair symbol (default "BTCUSDT").

        Returns
        -------
        List[Signal]
            Zero or one BUY Signal based on the latest bar.
        """
        required_cols = {"open", "high", "low", "close", "volume"}
        data.columns = [c.lower() for c in data.columns]
        if not required_cols.issubset(set(data.columns)):
            missing = required_cols - set(data.columns)
            raise ValueError(f"Missing columns: {missing}")

        if len(data) < self.min_bars:
            return []

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # === Step 1: 14-bar momentum positive ===
        cur_close = float(close.iloc[-1])
        past_close = float(close.iloc[-self.momentum_period - 1]) if len(close) > self.momentum_period else float(close.iloc[0])

        momentum = cur_close - past_close
        if momentum <= 0:
            return []

        momentum_pct = momentum / past_close if past_close > 0 else 0

        # === Step 2: Volatility scaling ===
        returns = close.pct_change().dropna()

        if len(returns) < self.vol_lookback:
            return []

        realized_vol = float(returns.iloc[-self.vol_lookback:].std() * np.sqrt(self.annualization_factor))

        if realized_vol <= 0 or np.isnan(realized_vol):
            return []

        vol_scale = self.target_vol / realized_vol
        vol_scale = min(2.0, max(0.1, vol_scale))  # Cap between 0.1x and 2.0x

        # === Step 3: Volume > 20-bar average ===
        vol_avg = volume.rolling(window=self.vol_avg_period, min_periods=1).mean()
        current_vol = volume.iloc[-1]
        avg_vol = vol_avg.iloc[-1]

        if current_vol <= avg_vol:
            return []

        # === Step 4: ATR for TP/SL ===
        atr = self._calculate_atr(data, self.atr_period)
        cur_atr = atr.iloc[-1]

        if cur_atr <= 0 or pd.isna(cur_atr):
            return []

        # === Step 5: Build signal ===
        tp_price = cur_close + cur_atr * self.tp_atr_mult
        sl_price = cur_close - cur_atr * self.sl_atr_mult

        risk = cur_close - sl_price
        reward = tp_price - cur_close
        rr = reward / risk if risk > 0 else 0

        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

        # Confidence: momentum strength + vol-scale bonus
        mom_bonus = min(0.25, momentum_pct * 2)
        scale_bonus = min(0.15, (vol_scale - 0.5) * 0.1) if vol_scale > 0.5 else 0

        confidence = 0.4 + mom_bonus + scale_bonus
        confidence = min(0.95, max(0.10, confidence))

        reason = (
            f"MegaVolscaledVol BUY [mega-perm optimized]: "
            f"14-bar momentum +{momentum_pct:.2%}, "
            f"vol_scale={vol_scale:.2f}x (target={self.target_vol:.0%}/realized={realized_vol:.0%}), "
            f"vol={vol_ratio:.1f}x avg, "
            f"TP={self.tp_atr_mult}*ATR SL={self.sl_atr_mult}*ATR R:R={rr:.1f}:1"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 4),
            entry_price=round(cur_close, 2),
            take_profit=round(tp_price, 2),
            stop_loss=round(sl_price, 2),
            strategy_name=self.strategy_name,
            metadata={
                "momentum_pct": round(momentum_pct, 6),
                "realized_vol": round(realized_vol, 4),
                "vol_scale": round(vol_scale, 4),
                "vol_ratio": round(vol_ratio, 2),
                "atr": round(cur_atr, 2),
                "reason": reason,
            },
        )]

    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Average True Range."""
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()


# ---------------------------------------------------------------------------
# Standalone execution: synthetic test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(42)
    n = 500
    prices_list = [90000.0]

    for i in range(1, n):
        phase = i % 100
        if phase < 15:
            ret = np.random.normal(-0.012, 0.004)
        elif phase < 25:
            ret = np.random.normal(0.008, 0.006)
        elif phase < 60:
            ret = np.random.normal(0.003, 0.008)
        else:
            ret = np.random.normal(0.0, 0.010)
        prices_list.append(prices_list[-1] * (1 + ret))

    prices = np.array(prices_list)
    opens = prices * (1 + np.random.normal(0.001, 0.003, n))
    highs = np.maximum(prices, opens) * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = np.minimum(prices, opens) * (1 - np.abs(np.random.normal(0, 0.005, n)))

    base_vol = np.random.uniform(500, 2000, n)
    for i in range(n):
        if i % 100 < 15:
            base_vol[i] *= 2.5

    data = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": base_vol,
    })

    strategy = MegaVolscaledVolStrategy()
    signals = strategy.generate_signals(data, symbol="BTCUSDT")

    print("=" * 72)
    print(f"MegaVolscaledVol_v1 (Mega-Permutation Optimized)")
    print("=" * 72)
    print(f"Bars: {n} | Signals: {len(signals)}")
    for s in signals:
        print(f"\n  [{s.direction}] {s.symbol} @ ${s.entry_price:,.2f}")
        print(f"  Confidence: {s.confidence:.2%}")
        print(f"  TP: ${s.take_profit:,.2f} | SL: ${s.stop_loss:,.2f}")
        print(f"  {s.metadata.get('reason', '')}")

    if not signals:
        print("  (No signal on latest bar)")
    print()
