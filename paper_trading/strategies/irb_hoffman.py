"""IRB Hoffman — Inventory Retracement Bar (Rob Hoffman, 23x competition winner)."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.multi_source import fetch_klines

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class IRBHoffman(BaseStrategy):
    name = "irb_hoffman"
    display_name = "IRB Hoffman"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

    WICK_PCT = 0.45       # 45% wick threshold
    TEMPORAL_DECAY = 20   # Max bars to wait for breakout
    RR_RATIO = 1.5        # Risk:reward

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @staticmethod
    def _ema(values: list, span: int) -> list:
        if not values:
            return []
        alpha = 2.0 / (span + 1)
        ema = [values[0]]
        for v in values[1:]:
            ema.append(alpha * v + (1 - alpha) * ema[-1])
        return ema

    @staticmethod
    def _sma(values: list, period: int) -> list:
        result = [None] * (period - 1)
        for i in range(period - 1, len(values)):
            result.append(sum(values[i - period + 1:i + 1]) / period)
        return result

    @staticmethod
    def _atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
        if len(closes) < 2:
            return [0.0] * len(closes)
        tr_list = [highs[0] - lows[0]]
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]),
                     abs(lows[i] - closes[i - 1]))
            tr_list.append(tr)
        if len(tr_list) < period:
            return tr_list
        atr_vals = [0.0] * (period - 1)
        atr_vals.append(sum(tr_list[:period]) / period)
        for i in range(period, len(tr_list)):
            atr_vals.append((atr_vals[-1] * (period - 1) + tr_list[i]) / period)
        return atr_vals

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []

        for symbol, klines in data.items():
            if len(klines) < 60:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            opens = [float(k[1]) for k in klines]

            ema5 = self._ema(closes, 5)
            ema20 = self._ema(closes, 20)
            sma50 = self._sma(closes, 50)
            atr_vals = self._atr(highs, lows, closes, 14)

            # Scan for pending IRB setups
            pending_setups = []

            for i in range(50, len(closes)):
                if sma50[i] is None or atr_vals[i] <= 0:
                    continue

                candle_range = highs[i] - lows[i]
                if candle_range < 0.1 * atr_vals[i]:
                    continue

                body = abs(closes[i] - opens[i])
                top_body = max(opens[i], closes[i])
                bot_body = min(opens[i], closes[i])

                bullish_ribbon = ema5[i] > ema20[i] > sma50[i]
                bearish_ribbon = ema5[i] < ema20[i] < sma50[i]

                body_small = body < self.WICK_PCT * candle_range

                if body_small:
                    y_thresh = highs[i] - self.WICK_PCT * candle_range
                    x_thresh = lows[i] + self.WICK_PCT * candle_range

                    if closes[i] < y_thresh and opens[i] < y_thresh and bullish_ribbon:
                        wick_pct = (highs[i] - top_body) / candle_range
                        pending_setups.append({
                            'side': 'LONG', 'bar': i, 'irb_high': highs[i],
                            'irb_low': lows[i], 'wick_pct': wick_pct,
                        })
                    elif closes[i] > x_thresh and opens[i] > x_thresh and bearish_ribbon:
                        wick_pct = (bot_body - lows[i]) / candle_range
                        pending_setups.append({
                            'side': 'SHORT', 'bar': i, 'irb_high': highs[i],
                            'irb_low': lows[i], 'wick_pct': wick_pct,
                        })

            # Check setups for breakout — scan bars AFTER IRB for entry trigger
            last_bar = len(closes) - 1
            seen_symbols = set()  # One pick per symbol per direction
            for setup in pending_setups:
                bars_elapsed = last_bar - setup['bar']
                if bars_elapsed < 1 or bars_elapsed > self.TEMPORAL_DECAY:
                    continue

                # Check if ANY bar after the IRB broke out (not just the last bar)
                breakout_bar = None
                if setup['side'] == 'LONG':
                    for b in range(setup['bar'] + 1, last_bar + 1):
                        if highs[b] > setup['irb_high']:
                            breakout_bar = b
                            break
                elif setup['side'] == 'SHORT':
                    for b in range(setup['bar'] + 1, last_bar + 1):
                        if lows[b] < setup['irb_low']:
                            breakout_bar = b
                            break

                if breakout_bar is None:
                    continue

                # Only take the most recent breakout per symbol+direction
                pick_key = f"{symbol}_{setup['side']}"
                if pick_key in seen_symbols:
                    continue

                breakout_elapsed = breakout_bar - setup['bar']

                if setup['side'] == 'LONG':
                    entry = closes[last_bar]  # Use current price as entry
                    sl = setup['irb_low']
                    risk = entry - sl
                    if risk <= 0:
                        continue
                    tp = entry + self.RR_RATIO * risk
                    confidence = min(0.9, 0.5 + setup['wick_pct'] * 0.4)

                    seen_symbols.add(pick_key)
                    picks.append(NormalizedPick(
                        symbol=symbol, direction="LONG",
                        entry_price=round(entry, 6), tp=round(tp, 6), sl=round(sl, 6),
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(confidence, 3),
                        reason=(f"IRB Hoffman LONG | Bullish ribbon | "
                                f"wick={setup['wick_pct']:.0%} | "
                                f"breakout after {breakout_elapsed} bars | R:R=1:{self.RR_RATIO}"),
                        raw_signal={
                            "irb_high": setup['irb_high'], "irb_low": setup['irb_low'],
                            "wick_pct": round(setup['wick_pct'], 3),
                            "bars_elapsed": breakout_elapsed,
                        },
                    ))

                elif setup['side'] == 'SHORT':
                    entry = closes[last_bar]
                    sl = setup['irb_high']
                    risk = sl - entry
                    if risk <= 0:
                        continue
                    tp = entry - self.RR_RATIO * risk
                    confidence = min(0.9, 0.5 + setup['wick_pct'] * 0.4)

                    seen_symbols.add(pick_key)
                    picks.append(NormalizedPick(
                        symbol=symbol, direction="SHORT",
                        entry_price=round(entry, 6), tp=round(tp, 6), sl=round(sl, 6),
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(confidence, 3),
                        reason=(f"IRB Hoffman SHORT | Bearish ribbon | "
                                f"wick={setup['wick_pct']:.0%} | "
                                f"breakout after {breakout_elapsed} bars | R:R=1:{self.RR_RATIO}"),
                        raw_signal={
                            "irb_high": setup['irb_high'], "irb_low": setup['irb_low'],
                            "wick_pct": round(setup['wick_pct'], 3),
                            "bars_elapsed": breakout_elapsed,
                        },
                    ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
