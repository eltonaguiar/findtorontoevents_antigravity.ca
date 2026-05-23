"""Triple Confirmation - Golden Cross + BB Mean Reversion + Z-Score."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class TripleConfirmation(BaseStrategy):
    name = "triple_confirmation"
    display_name = "Triple Confirmation"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1d", limit=300)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 210:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]

            # 50 SMA and 200 SMA
            sma50 = sum(closes[-50:]) / 50
            sma200 = sum(closes[-200:]) / 200

            # Bollinger Bands (20, 2)
            bb_closes = closes[-20:]
            bb_mid = sum(bb_closes) / 20
            bb_std_val = (sum((c - bb_mid) ** 2 for c in bb_closes) / 20) ** 0.5
            bb_upper = bb_mid + 2 * bb_std_val
            bb_lower = bb_mid - 2 * bb_std_val

            # Z-Score
            zscore = (closes[-1] - bb_mid) / bb_std_val if bb_std_val > 0 else 0

            # ATR(14)
            trs = []
            for i in range(-14, 0):
                hl = highs[i] - lows[i]
                hc = abs(highs[i] - closes[i-1])
                lc = abs(lows[i] - closes[i-1])
                trs.append(max(hl, hc, lc))
            atr_val = sum(trs) / 14

            price = closes[-1]

            # Check Z-Score in last 3 bars
            z_recent = []
            for offset in range(3):
                idx = -(offset + 1)
                if abs(idx) <= len(closes) and bb_std_val > 0:
                    z_recent.append((closes[idx] - bb_mid) / bb_std_val)

            direction = None
            if sma50 > sma200 and price <= bb_lower and min(z_recent, default=0) < -1.5:
                direction = "LONG"
                tp = round(bb_mid, 6)
                sl = round(price - 1.5 * atr_val, 6)
                if tp <= price:
                    tp = round(price + 2.0 * atr_val, 6)
                confidence = min(0.9, 0.5 + abs(zscore) * 0.1)
                reason = f"Triple Confirm LONG: GoldenCross, close<BB_Lower, Z={zscore:.2f}"
            elif sma50 < sma200 and price >= bb_upper and max(z_recent, default=0) > 1.5:
                direction = "SHORT"
                tp = round(bb_mid, 6)
                sl = round(price + 1.5 * atr_val, 6)
                if tp >= price:
                    tp = round(price - 2.0 * atr_val, 6)
                confidence = min(0.9, 0.5 + abs(zscore) * 0.1)
                reason = f"Triple Confirm SHORT: DeathCross, close>BB_Upper, Z={zscore:.2f}"

            if direction:
                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction=direction,
                    entry_price=price,
                    tp=tp,
                    sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={
                        "sma50": sma50, "sma200": sma200,
                        "bb_upper": bb_upper, "bb_mid": bb_mid, "bb_lower": bb_lower,
                        "zscore": zscore, "atr": atr_val,
                    },
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
