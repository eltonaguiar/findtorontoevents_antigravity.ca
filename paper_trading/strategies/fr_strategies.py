"""FundedRelay Strategies — Paper trading wrappers for 8 FR variations.

Source: FundedRelay (TradingView The Leap Feb 2026, +77.7%)
Base: Advanced Trend Reversal Emoji Indicator + Asset Liquidity Meter
Variations: MTF Aligned, Liquidity Filtered, RSI Divergence, ADX Regime,
            Pullback Entry, Volume Spike, Full Confluence
"""
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


def _ema(values, period):
    """Exponential Moving Average."""
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    ema = [None] * (period - 1)
    ema.append(sum(values[:period]) / period)
    for i in range(period, len(values)):
        ema.append(values[i] * k + ema[-1] * (1 - k))
    return ema


def _rsi(closes, period=14):
    """RSI calculation."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi = [None] * period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - 100 / (1 + rs))
    return [None] + rsi  # pad for alignment with closes


def _atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    atr = [None] * (period - 1)
    atr.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        atr.append((atr[-1] * (period - 1) + trs[i]) / period)
    return atr


def _adx(highs, lows, closes, period=14):
    """ADX calculation."""
    if len(closes) < period * 2 + 1:
        return [None] * len(closes)
    plus_dm = []
    minus_dm = []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    atr_vals = _atr(highs, lows, closes, period)
    result = [None] * len(closes)
    if len(atr_vals) < period * 2:
        return result
    # Smoothed +DI/-DI
    sm_plus = sum(plus_dm[:period])
    sm_minus = sum(minus_dm[:period])
    dx_list = []
    for i in range(period, len(plus_dm)):
        sm_plus = sm_plus - sm_plus / period + plus_dm[i]
        sm_minus = sm_minus - sm_minus / period + minus_dm[i]
        atr_v = atr_vals[i + 1]  # offset by 1 for alignment
        if atr_v and atr_v > 0:
            plus_di = 100 * sm_plus / (atr_v * period)
            minus_di = 100 * sm_minus / (atr_v * period)
            denom = plus_di + minus_di
            dx = 100 * abs(plus_di - minus_di) / denom if denom > 0 else 0
            dx_list.append(dx)
        else:
            dx_list.append(0)
    if len(dx_list) < period:
        return result
    adx_val = sum(dx_list[:period]) / period
    start_idx = period * 2 + 1
    for i in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[i]) / period
        idx = i + period + 1  # map back to closes index
        if idx < len(result):
            result[idx] = adx_val
    return result


def _liquidity_meter(volumes, highs, lows):
    """Asset Liquidity Meter: volume / (high - low)."""
    return [v / max(h - l, 0.0001) for v, h, l in zip(volumes, highs, lows)]


def _sma(values, period):
    """Simple Moving Average for numeric list (handles None)."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1: i + 1]
        if None in window:
            continue
        result[i] = sum(window) / period
    return result


class _FRBase(BaseStrategy):
    """Common base for all FundedRelay strategy wrappers."""
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "verified"  # New portfolio for verified strategies

    # Subclasses override these
    tp_pct = 0.12
    sl_pct = 0.05

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="4h", limit=300)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _parse_klines(self, klines):
        """Parse Binance klines into arrays."""
        opens = [float(k[1]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        closes = [float(k[4]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        return opens, highs, lows, closes, volumes

    def _base_signal(self, closes, highs, lows, volumes):
        """Core FundedRelay signal: EMA21/55 cross + EMA200 alignment + RSI + ATR expansion."""
        if len(closes) < 210:
            return None, None

        ema21 = _ema(closes, 21)
        ema55 = _ema(closes, 55)
        ema200 = _ema(closes, 200)
        rsi = _rsi(closes, 14)
        atr = _atr(highs, lows, closes, 14)

        if any(v is None for v in [ema21[-1], ema55[-1], ema200[-1], rsi[-1], atr[-1], atr[-2]]):
            return None, None

        price = closes[-1]

        # EMA cross direction
        ema_bull = ema21[-1] > ema55[-1] and ema21[-2] <= ema55[-2] if ema21[-2] and ema55[-2] else ema21[-1] > ema55[-1]
        ema_bear = ema21[-1] < ema55[-1] and ema21[-2] >= ema55[-2] if ema21[-2] and ema55[-2] else ema21[-1] < ema55[-1]

        # Recent cross (within last 3 bars) OR strong trend
        recent_bull = ema21[-1] > ema55[-1]
        recent_bear = ema21[-1] < ema55[-1]

        # 200 EMA alignment
        above_200 = price > ema200[-1]
        below_200 = price < ema200[-1]

        # RSI confirmation
        rsi_bull = rsi[-1] is not None and rsi[-1] > 55
        rsi_bear = rsi[-1] is not None and rsi[-1] < 45

        # ATR expansion (current > previous)
        atr_expanding = atr[-1] > atr[-2]

        info = {
            "ema21": ema21[-1], "ema55": ema55[-1], "ema200": ema200[-1],
            "rsi": rsi[-1], "atr": atr[-1], "atr_prev": atr[-2],
            "price": price,
        }

        if recent_bull and above_200 and rsi_bull and atr_expanding:
            return "LONG", info
        elif recent_bear and below_200 and rsi_bear and atr_expanding:
            return "SHORT", info
        return None, info

    def _make_pick(self, symbol, direction, confidence, info, reason_extra=""):
        price = info["price"]
        if direction == "LONG":
            tp = round(price * (1 + self.tp_pct), 6)
            sl = round(price * (1 - self.sl_pct), 6)
        else:
            tp = round(price * (1 - self.tp_pct), 6)
            sl = round(price * (1 + self.sl_pct), 6)

        reason = (f"FR {self.display_name}: EMA21={info['ema21']:.2f} EMA55={info['ema55']:.2f} "
                  f"EMA200={info['ema200']:.2f} RSI={info['rsi']:.1f} ATR={info['atr']:.4f}")
        if reason_extra:
            reason += f" | {reason_extra}"

        return NormalizedPick(
            symbol=symbol,
            direction=direction,
            entry_price=price,
            tp=tp,
            sl=sl,
            strategy=self.name,
            strategy_name=self.display_name,
            category="crypto",
            confidence=round(min(confidence, 0.95), 3),
            reason=reason,
        )


class FRBaseReversalPT(_FRBase):
    name = "fr_base_reversal"
    display_name = "FR Base Reversal"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if direction and info:
                picks.append(self._make_pick(symbol, direction, 0.60, info))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRMtfAlignedPT(_FRBase):
    name = "fr_mtf_aligned"
    display_name = "FR MTF Aligned"
    tp_pct = 0.15
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if not direction or not info:
                continue
            # Simulate daily trend: 200-bar EMA on 4H ≈ 50-day trend
            ema200 = _ema(closes, 200)
            if ema200[-1] is None:
                continue
            # Additional: require price making higher lows (last 3 swing lows)
            recent_lows = [min(lows[i - 5:i + 1]) for i in range(max(len(lows) - 20, 5), len(lows), 5)]
            if direction == "LONG" and closes[-1] > ema200[-1]:
                if len(recent_lows) >= 2 and recent_lows[-1] > recent_lows[-2]:
                    picks.append(self._make_pick(symbol, direction, 0.70, info, "MTF aligned + higher lows"))
            elif direction == "SHORT" and closes[-1] < ema200[-1]:
                if len(recent_lows) >= 2 and recent_lows[-1] < recent_lows[-2]:
                    picks.append(self._make_pick(symbol, direction, 0.70, info, "MTF aligned + lower highs"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRLiquidityFilteredPT(_FRBase):
    name = "fr_liquidity_filtered"
    display_name = "FR Liquidity Filtered"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if not direction or not info:
                continue
            liq = _liquidity_meter(volumes, highs, lows)
            liq_sma = _sma(liq, 20)
            if liq_sma[-1] is None or len(liq) < 3:
                continue
            # Liquidity > 20-SMA AND rising for 3 bars
            if liq[-1] > liq_sma[-1] and liq[-1] > liq[-2] > liq[-3]:
                picks.append(self._make_pick(symbol, direction, 0.65, info,
                             f"Liq={liq[-1]:.0f} > SMA20={liq_sma[-1]:.0f}, rising"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRRsiDivergencePT(_FRBase):
    name = "fr_rsi_divergence"
    display_name = "FR RSI Divergence"
    tp_pct = 0.15
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if not direction or not info:
                continue
            rsi_vals = _rsi(closes, 14)
            # Simple divergence: compare last two swing lows/highs (20-bar lookback)
            if len(closes) < 40 or rsi_vals[-1] is None:
                continue
            # Find recent pivots
            recent = closes[-20:]
            rsi_recent = [r for r in rsi_vals[-20:] if r is not None]
            if len(rsi_recent) < 10:
                continue
            if direction == "LONG":
                # Bullish divergence: price lower low, RSI higher low
                price_low1 = min(recent[:10])
                price_low2 = min(recent[10:])
                rsi_low1 = min(rsi_recent[:10])
                rsi_low2 = min(rsi_recent[10:])
                if price_low2 < price_low1 and rsi_low2 > rsi_low1:
                    picks.append(self._make_pick(symbol, direction, 0.72, info,
                                 f"Bullish divergence: price LL, RSI HL"))
            elif direction == "SHORT":
                price_high1 = max(recent[:10])
                price_high2 = max(recent[10:])
                rsi_high1 = max(rsi_recent[:10])
                rsi_high2 = max(rsi_recent[10:])
                if price_high2 > price_high1 and rsi_high2 < rsi_high1:
                    picks.append(self._make_pick(symbol, direction, 0.72, info,
                                 f"Bearish divergence: price HH, RSI LH"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRAdxRegimePT(_FRBase):
    name = "fr_adx_regime"
    display_name = "FR ADX Regime"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if not direction or not info:
                continue
            adx_vals = _adx(highs, lows, closes, 14)
            atr_vals = _atr(highs, lows, closes, 14)
            if adx_vals[-1] is None or atr_vals[-1] is None:
                continue
            # ADX > 25 (trending)
            if adx_vals[-1] <= 25:
                continue
            # ATR > 50th percentile of last 100 bars
            recent_atr = [a for a in atr_vals[-100:] if a is not None]
            if len(recent_atr) < 20:
                continue
            sorted_atr = sorted(recent_atr)
            p50 = sorted_atr[len(sorted_atr) // 2]
            if atr_vals[-1] > p50:
                picks.append(self._make_pick(symbol, direction, 0.68, info,
                             f"ADX={adx_vals[-1]:.1f} > 25, ATR > P50"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRPullbackEntryPT(_FRBase):
    name = "fr_pullback_entry"
    display_name = "FR Pullback Entry"
    tp_pct = 0.15
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            if len(closes) < 210:
                continue
            ema21 = _ema(closes, 21)
            ema55 = _ema(closes, 55)
            ema200 = _ema(closes, 200)
            rsi_vals = _rsi(closes, 14)
            if any(v is None for v in [ema21[-1], ema55[-1], ema200[-1], rsi_vals[-1]]):
                continue
            price = closes[-1]
            # Check for recent EMA cross (within last 10 bars) then pullback to zone
            ema_bull_zone = ema21[-1] > ema55[-1] and price > ema200[-1]
            ema_bear_zone = ema21[-1] < ema55[-1] and price < ema200[-1]
            # Price pulled back to EMA21-55 zone
            ema_mid = (ema21[-1] + ema55[-1]) / 2
            in_zone = abs(price - ema_mid) / ema_mid < 0.02  # Within 2% of zone
            # Bullish engulfing: close > open AND current close > prev high
            bullish_engulf = closes[-1] > opens[-1] and closes[-1] > highs[-2] if len(opens) > 1 else False
            bearish_engulf = closes[-1] < opens[-1] and closes[-1] < lows[-2] if len(opens) > 1 else False

            info = {"ema21": ema21[-1], "ema55": ema55[-1], "ema200": ema200[-1],
                    "rsi": rsi_vals[-1], "atr": 0, "atr_prev": 0, "price": price}

            if ema_bull_zone and in_zone and bullish_engulf and rsi_vals[-1] > 50:
                picks.append(self._make_pick(symbol, "LONG", 0.72, info,
                             "Pullback to EMA zone + bullish engulfing"))
            elif ema_bear_zone and in_zone and bearish_engulf and rsi_vals[-1] < 50:
                picks.append(self._make_pick(symbol, "SHORT", 0.72, info,
                             "Pullback to EMA zone + bearish engulfing"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRVolumeSpikePT(_FRBase):
    name = "fr_volume_spike"
    display_name = "FR Volume Spike"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if not direction or not info:
                continue
            if len(volumes) < 21:
                continue
            avg_vol = sum(volumes[-21:-1]) / 20
            if volumes[-1] > 1.5 * avg_vol:
                picks.append(self._make_pick(symbol, direction, 0.65, info,
                             f"Vol={volumes[-1]:.0f} > 1.5x avg={avg_vol:.0f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class FRFullConfluencePT(_FRBase):
    name = "fr_full_confluence"
    display_name = "FR Full Confluence"
    tp_pct = 0.20
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse_klines(klines)
            direction, info = self._base_signal(closes, highs, lows, volumes)
            if not direction or not info:
                continue
            # All filters must pass
            # 1. ADX > 25
            adx_vals = _adx(highs, lows, closes, 14)
            if adx_vals[-1] is None or adx_vals[-1] <= 25:
                continue
            # 2. Liquidity rising
            liq = _liquidity_meter(volumes, highs, lows)
            liq_sma = _sma(liq, 20)
            if liq_sma[-1] is None or liq[-1] <= liq_sma[-1]:
                continue
            # 3. Volume spike
            if len(volumes) < 21:
                continue
            avg_vol = sum(volumes[-21:-1]) / 20
            if volumes[-1] <= 1.5 * avg_vol:
                continue
            # 4. Higher lows / lower highs (MTF-like check)
            ema200 = _ema(closes, 200)
            if ema200[-1] is None:
                continue
            if direction == "LONG" and closes[-1] <= ema200[-1]:
                continue
            if direction == "SHORT" and closes[-1] >= ema200[-1]:
                continue

            filters = f"ADX={adx_vals[-1]:.1f} Liq={liq[-1]:.0f} Vol={volumes[-1]:.0f}/{avg_vol:.0f}"
            picks.append(self._make_pick(symbol, direction, 0.82, info,
                         f"Full confluence: {filters}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]
