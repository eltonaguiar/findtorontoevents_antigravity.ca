"""Williams %R Extreme Reversal — deep oversold/overbought with volume confirmation.

Academic source: Larry Williams (1973), validated by Connors (2008).
Target: 60-68% WR, 20-40 trades/year per symbol.
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
WR_OVERSOLD = -95       # Extreme oversold (deeper than standard -80)
WR_OVERBOUGHT = -5      # Extreme overbought (deeper than standard -20)
SMA_PERIOD = 200
VOL_MULT = 1.2          # Volume must be 1.2x 20-bar average
TP_PCT = 0.06
SL_PCT = 0.03


class WilliamsPercentRExtremePT(BaseStrategy):
    name = "williams_pct_r_extreme"
    display_name = "Williams %R Extreme Reversal"
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
    def _williams_r(highs, lows, closes, period=WR_PERIOD):
        if len(closes) < period:
            return -50.0
        hh = float(np.max(highs[-period:]))
        ll = float(np.min(lows[-period:]))
        c = float(closes[-1])
        rng = hh - ll
        if rng == 0:
            return -50.0
        return ((hh - c) / rng) * -100

    @staticmethod
    def _sma(values, period):
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
            volumes = np.array([float(k[5]) for k in klines])
            price = float(closes[-1])

            wr = self._williams_r(highs, lows, closes, WR_PERIOD)
            sma200 = self._sma(closes, SMA_PERIOD)

            # Volume confirmation
            vol_avg = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else float(np.mean(volumes))
            vol_ratio = float(volumes[-1]) / vol_avg if vol_avg > 0 else 0

            if vol_ratio < VOL_MULT:
                continue

            if wr < WR_OVERSOLD and price > sma200:
                direction = "LONG"
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
                depth = abs(wr + 100)
                confidence = min(0.90, 0.55 + depth * 0.05 + (vol_ratio - 1) * 0.05)
                reason = (f"%R({WR_PERIOD})={wr:.1f} extreme oversold (<{WR_OVERSOLD}), "
                          f"vol {vol_ratio:.1f}x avg, above SMA200")

            elif wr > WR_OVERBOUGHT and price < sma200:
                direction = "SHORT"
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)
                depth = abs(wr)
                confidence = min(0.90, 0.55 + depth * 0.05 + (vol_ratio - 1) * 0.05)
                reason = (f"%R({WR_PERIOD})={wr:.1f} extreme overbought (>{WR_OVERBOUGHT}), "
                          f"vol {vol_ratio:.1f}x avg, below SMA200")
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
                    "vol_ratio": round(vol_ratio, 2),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
