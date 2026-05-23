"""Stochastic RSI Divergence — StochRSI crossover in extreme zones with trend filter.

Academic source: Chande & Kroll (1994) "The New Technical Trader".
Target: 58-65% WR, 15-35 trades/year per symbol.
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

RSI_PERIOD = 14
STOCH_PERIOD = 14
SMOOTH_K = 3
SMOOTH_D = 3
SMA_PERIOD = 100
TP_PCT = 0.07       # 7% take profit (higher conviction trades)
SL_PCT = 0.035       # 3.5% stop loss (2:1 R:R)


class StochasticRSIDivergencePT(BaseStrategy):
    name = "stoch_rsi_divergence"
    display_name = "Stochastic RSI Divergence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

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
    def _rsi(closes, period=RSI_PERIOD):
        """Wilder RSI."""
        n = len(closes)
        if n < period + 1:
            return np.full(n, 50.0)
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        rsi_arr = np.full(n, 50.0)
        alpha = 1.0 / period
        for i in range(period, n - 1):
            avg_gain = avg_gain * (1 - alpha) + gains[i] * alpha
            avg_loss = avg_loss * (1 - alpha) + losses[i] * alpha
            if avg_loss == 0:
                rsi_arr[i + 1] = 100.0
            else:
                rsi_arr[i + 1] = 100 - 100 / (1 + avg_gain / avg_loss)
        return rsi_arr

    @staticmethod
    def _stoch_rsi(rsi_arr, stoch_period=STOCH_PERIOD, smooth_k=SMOOTH_K, smooth_d=SMOOTH_D):
        """StochRSI %K and %D."""
        n = len(rsi_arr)
        raw = np.full(n, 50.0)
        for i in range(stoch_period, n):
            window = rsi_arr[i - stoch_period + 1: i + 1]
            mn = np.min(window)
            mx = np.max(window)
            if mx - mn == 0:
                raw[i] = 50.0
            else:
                raw[i] = (rsi_arr[i] - mn) / (mx - mn) * 100

        # Smooth %K and %D
        k = np.full(n, 50.0)
        d = np.full(n, 50.0)
        for i in range(smooth_k - 1, n):
            k[i] = np.mean(raw[i - smooth_k + 1: i + 1])
        for i in range(smooth_k + smooth_d - 2, n):
            d[i] = np.mean(k[i - smooth_d + 1: i + 1])
        return k, d

    @staticmethod
    def _sma(values, period):
        if len(values) < period:
            return float(np.mean(values))
        return float(np.mean(values[-period:]))

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < SMA_PERIOD + STOCH_PERIOD + RSI_PERIOD:
                continue

            closes = np.array([float(k[4]) for k in klines])
            price = float(closes[-1])
            sma100 = self._sma(closes, SMA_PERIOD)

            rsi_arr = self._rsi(closes, RSI_PERIOD)
            k_arr, d_arr = self._stoch_rsi(rsi_arr)

            curr_rsi = float(rsi_arr[-1])
            curr_k = float(k_arr[-1])
            curr_d = float(d_arr[-1])
            prev_k = float(k_arr[-2])
            prev_d = float(d_arr[-2])

            # LONG: RSI < 35, StochRSI %K crosses above %D in oversold (<20), above 100 SMA
            if (curr_rsi < 35 and curr_k < 20 and curr_d < 20
                    and curr_k > curr_d and prev_k <= prev_d
                    and price > sma100):
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
                confidence = min(0.88, 0.55 + (35 - curr_rsi) * 0.01 + (20 - curr_k) * 0.005)
                reason = (f"StochRSI %K crossed %D in oversold ({curr_k:.1f}/{curr_d:.1f}), "
                          f"RSI={curr_rsi:.1f} < 35, above SMA100")

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="LONG",
                    entry_price=price,
                    tp=tp, sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={
                        "rsi": round(curr_rsi, 2),
                        "stoch_k": round(curr_k, 2),
                        "stoch_d": round(curr_d, 2),
                        "sma100": round(sma100, 2),
                    },
                ))

            # SHORT: RSI > 65, StochRSI %K crosses below %D in overbought (>80), below 100 SMA
            elif (curr_rsi > 65 and curr_k > 80 and curr_d > 80
                  and curr_k < curr_d and prev_k >= prev_d
                  and price < sma100):
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)
                confidence = min(0.88, 0.55 + (curr_rsi - 65) * 0.01 + (curr_k - 80) * 0.005)
                reason = (f"StochRSI %K crossed %D in overbought ({curr_k:.1f}/{curr_d:.1f}), "
                          f"RSI={curr_rsi:.1f} > 65, below SMA100")

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="SHORT",
                    entry_price=price,
                    tp=tp, sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={
                        "rsi": round(curr_rsi, 2),
                        "stoch_k": round(curr_k, 2),
                        "stoch_d": round(curr_d, 2),
                        "sma100": round(sma100, 2),
                    },
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
