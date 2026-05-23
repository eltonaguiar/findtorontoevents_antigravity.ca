"""Volume Breakout - buy on 3x avg volume + price above 20d SMA."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT", "NEARUSDT", "APTUSDT"]

TP_PCT = 0.07
SL_PCT = 0.035


class VolumeBreakout(BaseStrategy):
    name = "volume_breakout"
    display_name = "Volume Breakout"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1d", limit=30)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 21:
                continue

            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            current_price = closes[-1]
            current_vol = volumes[-1]

            sma_20 = sum(closes[-20:]) / 20
            avg_vol = sum(volumes[:-1]) / len(volumes[:-1])

            if current_price > sma_20 and current_vol > avg_vol * 3:
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
                confidence = min(0.9, 0.5 + (vol_ratio - 3) / 20)

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="LONG",
                    entry_price=current_price,
                    tp=round(current_price * (1 + TP_PCT), 6),
                    sl=round(current_price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=f"Volume {vol_ratio:.1f}x avg, price above 20d SMA (${sma_20:.2f})",
                    raw_signal={"vol_ratio": vol_ratio, "sma_20": sma_20, "price": current_price},
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
