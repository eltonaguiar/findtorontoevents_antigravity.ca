"""Correlation Reversion Strategies - VWAP, Z-Score, Elton Net, RSI, and confluence pairs."""
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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fetch_all(self) -> dict:
    all_data = {}
    for sym in SYMBOLS:
        try:
            klines = self.fetch_klines(sym, interval="1h", limit=100)
            if klines:
                all_data[sym] = klines
        except Exception:
            continue
    return all_data


def _calc_vwap(klines):
    """Compute VWAP and std dev of (close - vwap) over all bars."""
    cum_tpv = 0.0
    cum_vol = 0.0
    diffs = []
    for k in klines:
        high, low, close, volume = float(k[2]), float(k[3]), float(k[4]), float(k[5])
        tp = (high + low + close) / 3.0
        cum_tpv += tp * volume
        cum_vol += volume
        if cum_vol > 0:
            vwap = cum_tpv / cum_vol
            diffs.append(close - vwap)
    if cum_vol == 0 or len(diffs) < 10:
        return None, None
    vwap_final = cum_tpv / cum_vol
    std = float(np.std(diffs))
    return vwap_final, std


def _calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = []
    losses = []
    for d in deltas[-period:]:
        gains.append(d if d > 0 else 0)
        losses.append(-d if d < 0 else 0)
    ag = np.mean(gains) if gains else 0.001
    al = np.mean(losses) if losses else 0.001
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def _calc_kama(closes, fast=2, slow=30, er_period=10):
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


def _wma(values, period):
    if len(values) < period:
        return None
    weights = list(range(1, period + 1))
    return sum(v * w for v, w in zip(values[-period:], weights)) / sum(weights)


def _hma(closes, period=16):
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
        wh = _wma(closes[:slice_end], half_p)
        wf = _wma(closes[:slice_end], period)
        if wh is None or wf is None:
            continue
        diff_series.append(2 * wh - wf)
    if len(diff_series) < sqrt_p:
        return None
    return _wma(diff_series, sqrt_p)


def _elton_net(closes, highs, lows, volumes):
    score = 0
    n = len(closes)
    if n < 50:
        return 0
    price = closes[-1]
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
    atr = np.mean([highs[i] - lows[i] for i in range(max(n - 14, 0), n)])
    mid = (highs[-1] + lows[-1]) / 2
    if price > mid + atr:
        score += 15
    elif price < mid - atr:
        score -= 15
    sma50 = np.mean(closes[-50:])
    if price > sma50:
        score += 10
    else:
        score -= 10
    avg_vol = np.mean(volumes[-20:])
    if volumes[-1] > avg_vol * 1.5 and price > closes[-2]:
        score += 10
    elif volumes[-1] > avg_vol * 1.5 and price < closes[-2]:
        score -= 10
    return score


# ---------------------------------------------------------------------------
# Strategy classes
# ---------------------------------------------------------------------------

class CorrVWAPReversion(BaseStrategy):
    name = "corr_vwap_reversion"
    display_name = "Correlation - VWAP Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 30:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            vwap, std = _calc_vwap(klines)
            if vwap is None or std <= 0:
                continue

            if price < vwap - 1 * std:
                direction = "LONG"
                tp = round(price * 1.05, 6)
                sl = round(price * 0.97, 6)
                dist = (vwap - price) / std
                confidence = min(0.85, 0.5 + dist * 0.1)
                reason = f"VWAP Reversion BUY: price={price:.2f} < VWAP-1std ({vwap - std:.2f})"
            elif price > vwap + 1 * std:
                direction = "SHORT"
                tp = round(price * 0.95, 6)
                sl = round(price * 1.03, 6)
                dist = (price - vwap) / std
                confidence = min(0.85, 0.5 + dist * 0.1)
                reason = f"VWAP Reversion SELL: price={price:.2f} > VWAP+1std ({vwap + std:.2f})"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"vwap": round(vwap, 4), "std": round(std, 4), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrZScoreExtreme(BaseStrategy):
    name = "corr_zscore_extreme"
    display_name = "Correlation - Z-Score Extreme"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            mean50 = float(np.mean(closes[-50:]))
            std50 = float(np.std(closes[-50:]))
            if std50 <= 0:
                continue
            z = (price - mean50) / std50

            if z < -2.0:
                direction = "LONG"
                tp = round(price * 1.06, 6)
                sl = round(price * 0.97, 6)
                confidence = min(0.88, 0.55 + abs(z) * 0.08)
                reason = f"Z-Score Extreme BUY: Z={z:.2f} (price={price:.2f}, mean={mean50:.2f})"
            elif z > 2.0:
                direction = "SHORT"
                tp = round(price * 0.94, 6)
                sl = round(price * 1.03, 6)
                confidence = min(0.88, 0.55 + abs(z) * 0.08)
                reason = f"Z-Score Extreme SELL: Z={z:.2f} (price={price:.2f}, mean={mean50:.2f})"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"z_score": round(z, 4), "mean50": round(mean50, 4), "std50": round(std50, 4)},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrEltonNetConsensus(BaseStrategy):
    name = "corr_elton_net_consensus"
    display_name = "Correlation - Elton Net Consensus"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

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
            elton = _elton_net(closes, highs, lows, volumes)

            if elton > 50:
                direction = "LONG"
                tp = round(price * 1.10, 6)
                sl = round(price * 0.95, 6)
                confidence = min(0.90, 0.55 + elton / 200)
                reason = f"Elton Net Consensus BUY: score={elton}"
            elif elton < -35:
                direction = "SHORT"
                tp = round(price * 0.90, 6)
                sl = round(price * 1.05, 6)
                confidence = min(0.90, 0.55 + abs(elton) / 200)
                reason = f"Elton Net Consensus SELL: score={elton}"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"elton_net": elton, "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrRSIMomentum(BaseStrategy):
    name = "corr_rsi_momentum"
    display_name = "Correlation - RSI Momentum"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 30:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            rsi = _calc_rsi(closes, 14)
            if rsi is None:
                continue

            if rsi < 30:
                direction = "LONG"
                tp = round(price * 1.08, 6)
                sl = round(price * 0.96, 6)
                confidence = min(0.85, 0.55 + (30 - rsi) * 0.01)
                reason = f"RSI Momentum BUY: RSI={rsi:.1f} (oversold)"
            elif rsi > 70:
                direction = "SHORT"
                tp = round(price * 0.92, 6)
                sl = round(price * 1.04, 6)
                confidence = min(0.85, 0.55 + (rsi - 70) * 0.01)
                reason = f"RSI Momentum SELL: RSI={rsi:.1f} (overbought)"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"rsi": round(rsi, 2), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrHMAEltonConfluence(BaseStrategy):
    name = "corr_hma_elton_confluence"
    display_name = "Correlation - HMA x Elton"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

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

            hma = _hma(closes, 16)
            elton = _elton_net(closes, highs, lows, volumes)
            if hma is None:
                continue

            if price > hma and elton > 35:
                direction = "LONG"
                tp = round(price * 1.12, 6)
                sl = round(price * 0.95, 6)
                confidence = min(0.90, 0.60 + elton / 250)
                reason = f"HMA x Elton BUY: HMA={hma:.2f}, EltonNet={elton}"
            elif price < hma and elton < -35:
                direction = "SHORT"
                tp = round(price * 0.88, 6)
                sl = round(price * 1.05, 6)
                confidence = min(0.90, 0.60 + abs(elton) / 250)
                reason = f"HMA x Elton SELL: HMA={hma:.2f}, EltonNet={elton}"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"hma": round(hma, 4), "elton_net": elton, "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrVWAPZScore(BaseStrategy):
    name = "corr_vwap_zscore_reversion"
    display_name = "Correlation - VWAP x Z-Score"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            vwap, std_vwap = _calc_vwap(klines)
            if vwap is None:
                continue
            mean50 = float(np.mean(closes[-50:]))
            std50 = float(np.std(closes[-50:]))
            if std50 <= 0:
                continue
            z = (price - mean50) / std50

            if price < vwap and z < -1.5:
                direction = "LONG"
                tp = round(price * 1.06, 6)
                sl = round(price * 0.97, 6)
                confidence = min(0.88, 0.55 + abs(z) * 0.08)
                reason = f"VWAP x Z BUY: VWAP={vwap:.2f}, Z={z:.2f}"
            elif price > vwap and z > 1.5:
                direction = "SHORT"
                tp = round(price * 0.94, 6)
                sl = round(price * 1.03, 6)
                confidence = min(0.88, 0.55 + abs(z) * 0.08)
                reason = f"VWAP x Z SELL: VWAP={vwap:.2f}, Z={z:.2f}"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"vwap": round(vwap, 4), "z_score": round(z, 4), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class CorrKAMARSI(BaseStrategy):
    name = "corr_kama_rsi_trend"
    display_name = "Correlation - KAMA x RSI"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "correlation"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            kama = _calc_kama(closes)
            rsi = _calc_rsi(closes, 14)
            if kama is None or rsi is None:
                continue

            if price > kama and rsi < 40:
                direction = "LONG"
                tp = round(price * 1.10, 6)
                sl = round(price * 0.95, 6)
                confidence = min(0.88, 0.55 + (40 - rsi) * 0.008)
                reason = f"KAMA x RSI BUY: KAMA={kama:.2f}, RSI={rsi:.1f} (trend + pullback)"
            elif price < kama and rsi > 60:
                direction = "SHORT"
                tp = round(price * 0.90, 6)
                sl = round(price * 1.05, 6)
                confidence = min(0.88, 0.55 + (rsi - 60) * 0.008)
                reason = f"KAMA x RSI SELL: KAMA={kama:.2f}, RSI={rsi:.1f} (trend + pullback)"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"kama": round(kama, 4), "rsi": round(rsi, 2), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
