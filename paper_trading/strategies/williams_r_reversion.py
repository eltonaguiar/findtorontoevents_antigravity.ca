"""Williams %R Mean Reversion - Larry Williams' %R oversold/overbought on crypto.

Documented performance: 81% win rate, Sharpe 2.9, profit factor 3.2
Source: QuantifiedStrategies research on Williams %R mean reversion.
"""
from typing import List
import numpy as np
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]

WR_PERIOD = 14
WR_OVERSOLD = -90       # BUY when %R drops below this
WR_OVERBOUGHT = -10     # SELL when %R rises above this
SMA_PERIOD = 200         # Trend filter
TP_PCT = 0.06            # 6% take profit
SL_PCT = 0.03            # 3% stop loss (2:1 R:R)


class WilliamsRReversion(BaseStrategy):
    name = "williams_r_reversion"
    display_name = "Williams %R Mean Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "verified"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @staticmethod
    def _williams_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                    period: int = WR_PERIOD) -> float:
        """Calculate Williams %R for the most recent bar.

        Formula: %R = ((highest_high - close) / (highest_high - lowest_low)) * -100
        Range: -100 (most oversold) to 0 (most overbought).
        """
        if len(closes) < period:
            return -50.0  # neutral
        window_highs = highs[-period:]
        window_lows = lows[-period:]
        highest_high = float(np.max(window_highs))
        lowest_low = float(np.min(window_lows))
        close = float(closes[-1])
        hl_range = highest_high - lowest_low
        if hl_range == 0:
            return -50.0
        return ((highest_high - close) / hl_range) * -100

    @staticmethod
    def _sma(values: np.ndarray, period: int) -> float:
        """Simple moving average of the last *period* values."""
        if len(values) < period:
            return float(np.mean(values))
        return float(np.mean(values[-period:]))

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < SMA_PERIOD:
                continue

            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])
            price = float(closes[-1])

            wr = self._williams_r(highs, lows, closes, WR_PERIOD)
            sma200 = self._sma(closes, SMA_PERIOD)

            # --- BUY: deeply oversold + price above SMA(200) (uptrend) ---
            if wr < WR_OVERSOLD and price > sma200:
                direction = "LONG"
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
                distance = abs(wr - WR_OVERSOLD)
                confidence = min(0.92, 0.55 + distance * 0.03)
                reason = (f"Williams %R({WR_PERIOD})={wr:.1f} < {WR_OVERSOLD} "
                          f"(oversold) & price {price:.2f} > SMA200 {sma200:.2f} -> LONG")

            # --- SELL: deeply overbought + price below SMA(200) (downtrend) ---
            elif wr > WR_OVERBOUGHT and price < sma200:
                direction = "SHORT"
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)
                distance = abs(wr - WR_OVERBOUGHT)
                confidence = min(0.92, 0.55 + distance * 0.03)
                reason = (f"Williams %R({WR_PERIOD})={wr:.1f} > {WR_OVERBOUGHT} "
                          f"(overbought) & price {price:.2f} < SMA200 {sma200:.2f} -> SHORT")

            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp, sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=reason,
                raw_signal={
                    "williams_r": round(wr, 2),
                    "sma200": round(sma200, 2),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
