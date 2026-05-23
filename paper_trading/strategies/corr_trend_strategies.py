"""Correlation Trend Strategies - HMA, KAMA, Triple Crown for paper trading."""
from typing import List
import numpy as np
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


class CorrHMATrend(BaseStrategy):
    name = "corr_hma_trend"
    display_name = "Correlation - HMA Trend"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=100)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _wma(self, values, period):
        if len(values) < period:
            return None
        weights = list(range(1, period + 1))
        wma = sum(v * w for v, w in zip(values[-period:], weights)) / sum(weights)
        return wma

    def _hma(self, closes, period=16):
        half_p = max(int(period / 2), 1)
        sqrt_p = max(int(period ** 0.5), 1)
        if len(closes) < period + sqrt_p:
            return None
        diff_series = []
        for i in range(sqrt_p + 1):
            idx = len(closes) - sqrt_p - 1 + i
            slice_end = idx + 1
            if slice_end > len(closes):
                break
            wma_half = self._wma(closes[:slice_end], half_p)
            wma_full = self._wma(closes[:slice_end], period)
            if wma_half is None or wma_full is None:
                continue
            diff_series.append(2 * wma_half - wma_full)
        if len(diff_series) < sqrt_p:
            return None
        return self._wma(diff_series, sqrt_p)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            hma = self._hma(closes, 16)
            if hma is None:
                continue

            if price > hma:
                direction = "LONG"
                tp = round(price * 1.08, 6)
                sl = round(price * 0.96, 6)
                dist = (price - hma) / hma
                confidence = min(0.85, 0.5 + dist * 5)
                reason = f"HMA Trend BUY: close={price:.2f} > HMA={hma:.2f} (+{dist:.2%})"
            elif price < hma:
                direction = "SHORT"
                tp = round(price * 0.92, 6)
                sl = round(price * 1.04, 6)
                dist = (hma - price) / hma
                confidence = min(0.85, 0.5 + dist * 5)
                reason = f"HMA Trend SELL: close={price:.2f} < HMA={hma:.2f} (-{dist:.2%})"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason, raw_signal={"hma": round(hma, 4), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrKAMAAdaptive(BaseStrategy):
    name = "corr_kama_adaptive"
    display_name = "Correlation - KAMA Adaptive"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=100)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _kama(self, closes, fast=2, slow=30, er_period=10):
        if len(closes) < er_period + 2:
            return None
        fast_sc = 2 / (fast + 1)
        slow_sc = 2 / (slow + 1)
        kama_val = closes[er_period]
        for i in range(er_period + 1, len(closes)):
            change = abs(closes[i] - closes[i - er_period])
            volatility = sum(abs(closes[j] - closes[j - 1]) for j in range(i - er_period + 1, i + 1))
            er = change / volatility if volatility > 0 else 0
            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
            kama_val = kama_val + sc * (closes[i] - kama_val)
        return kama_val

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            kama = self._kama(closes)
            if kama is None:
                continue

            if price > kama:
                direction = "LONG"
                tp = round(price * 1.08, 6)
                sl = round(price * 0.96, 6)
                dist = (price - kama) / kama
                confidence = min(0.85, 0.5 + dist * 5)
                reason = f"KAMA Adaptive BUY: close={price:.2f} > KAMA={kama:.2f}"
            elif price < kama:
                direction = "SHORT"
                tp = round(price * 0.92, 6)
                sl = round(price * 1.04, 6)
                dist = (kama - price) / kama
                confidence = min(0.85, 0.5 + dist * 5)
                reason = f"KAMA Adaptive SELL: close={price:.2f} < KAMA={kama:.2f}"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason, raw_signal={"kama": round(kama, 4), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrTripleCrown(BaseStrategy):
    name = "corr_triple_crown"
    display_name = "Correlation - Triple Crown"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=100)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _wma(self, values, period):
        if len(values) < period:
            return None
        weights = list(range(1, period + 1))
        return sum(v * w for v, w in zip(values[-period:], weights)) / sum(weights)

    def _hma(self, closes, period=16):
        half_p = max(int(period / 2), 1)
        sqrt_p = max(int(period ** 0.5), 1)
        if len(closes) < period + sqrt_p:
            return None
        diff_series = []
        for i in range(sqrt_p + 1):
            idx = len(closes) - sqrt_p - 1 + i
            slice_end = idx + 1
            if slice_end > len(closes):
                break
            wma_half = self._wma(closes[:slice_end], half_p)
            wma_full = self._wma(closes[:slice_end], period)
            if wma_half is None or wma_full is None:
                continue
            diff_series.append(2 * wma_half - wma_full)
        if len(diff_series) < sqrt_p:
            return None
        return self._wma(diff_series, sqrt_p)

    def _kama(self, closes, fast=2, slow=30, er_period=10):
        if len(closes) < er_period + 2:
            return None
        fast_sc = 2 / (fast + 1)
        slow_sc = 2 / (slow + 1)
        kama_val = closes[er_period]
        for i in range(er_period + 1, len(closes)):
            change = abs(closes[i] - closes[i - er_period])
            volatility = sum(abs(closes[j] - closes[j - 1]) for j in range(i - er_period + 1, i + 1))
            er = change / volatility if volatility > 0 else 0
            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
            kama_val = kama_val + sc * (closes[i] - kama_val)
        return kama_val

    def _elton_net(self, closes, highs, lows, volumes):
        """Simplified Elton Net: composite score from sub-strategies."""
        score = 0
        n = len(closes)
        if n < 50:
            return 0
        price = closes[-1]
        # 1. RSI-2
        if n >= 3:
            deltas = [closes[i] - closes[i - 1] for i in range(max(n - 3, 1), n)]
            gains = [d for d in deltas if d > 0]
            losses = [-d for d in deltas if d < 0]
            ag = np.mean(gains) if gains else 0.001
            al = np.mean(losses) if losses else 0.001
            rsi2 = 100 - 100 / (1 + ag / al)
            if rsi2 < 10:
                score += 15
            elif rsi2 > 90:
                score -= 15
        # 2. Supertrend proxy
        atr = np.mean([highs[i] - lows[i] for i in range(max(n - 14, 0), n)])
        mid = (highs[-1] + lows[-1]) / 2
        if price > mid + atr:
            score += 15
        elif price < mid - atr:
            score -= 15
        # 3. SMA trend
        sma50 = np.mean(closes[-50:])
        if price > sma50:
            score += 10
        else:
            score -= 10
        # 4. Volume surge
        avg_vol = np.mean(volumes[-20:])
        if volumes[-1] > avg_vol * 1.5 and price > closes[-2]:
            score += 10
        elif volumes[-1] > avg_vol * 1.5 and price < closes[-2]:
            score -= 10
        return score

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 60:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]

            hma = self._hma(closes)
            kama = self._kama(closes)
            elton = self._elton_net(closes, highs, lows, volumes)

            if hma is None or kama is None:
                continue

            hma_bull = price > hma
            kama_bull = price > kama
            elton_bull = elton > 20

            hma_bear = price < hma
            kama_bear = price < kama
            elton_bear = elton < -20

            if hma_bull and kama_bull and elton_bull:
                direction = "LONG"
                tp = round(price * 1.15, 6)
                sl = round(price * 0.94, 6)
                confidence = min(0.92, 0.65 + elton / 200)
                reason = f"Triple Crown BUY: HMA={hma:.2f}, KAMA={kama:.2f}, EltonNet={elton}"
            elif hma_bear and kama_bear and elton_bear:
                direction = "SHORT"
                tp = round(price * 0.85, 6)
                sl = round(price * 1.06, 6)
                confidence = min(0.92, 0.65 + abs(elton) / 200)
                reason = f"Triple Crown SELL: HMA={hma:.2f}, KAMA={kama:.2f}, EltonNet={elton}"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"hma": round(hma, 4), "kama": round(kama, 4), "elton_net": elton},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:3]
