"""Verified Research Strategies — Paper trading wrappers for 8 backtested strategies.

Sources:
- SuperTrend AI: TradeSearcher, PF 1.94, 154 trades, 10-year BTC backtest
- WaveTrend: PickMyTrade, 58% WR, PF 1.9, 1000+ trades
- EMA Stack: PickMyTrade, 59% WR, PF 1.7
- Stoch RSI: QuantifiedStrategies, 78% WR, 228 trades
- Keltner Breakout: QuantifiedStrategies, 77% WR, PF 2.0, 288 trades
- Donchian Turtle: Gate Research, 62.71% annualized
- Williams %R: QuantifiedStrategies, 78-81% WR, PF 2.2-3.2, 598 trades
- BTC 50MA Momentum: Grayscale Research, Sharpe 1.9
"""
from typing import List
import math
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


def _ema(values, period):
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    result.append(sum(values[:period]) / period)
    for i in range(period, len(values)):
        result.append(values[i] * k + result[-1] * (1 - k))
    return result


def _sma(values, period):
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1:i + 1]) / period
    return result


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_vals = [None] * period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_vals.append(100.0)
        else:
            rsi_vals.append(100 - 100 / (1 + avg_gain / avg_loss))
    return [None] + rsi_vals


def _atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    result = [None] * (period - 1)
    result.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        result.append((result[-1] * (period - 1) + trs[i]) / period)
    return result


class _VerifiedBase(BaseStrategy):
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "verified"
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

    def _parse(self, klines):
        return (
            [float(k[1]) for k in klines],  # opens
            [float(k[2]) for k in klines],  # highs
            [float(k[3]) for k in klines],  # lows
            [float(k[4]) for k in klines],  # closes
            [float(k[5]) for k in klines],  # volumes
        )

    def _pick(self, symbol, direction, confidence, price, tp_pct=None, sl_pct=None, reason=""):
        tp_p = tp_pct or self.tp_pct
        sl_p = sl_pct or self.sl_pct
        if direction == "LONG":
            tp = round(price * (1 + tp_p), 6)
            sl = round(price * (1 - sl_p), 6)
        else:
            tp = round(price * (1 - tp_p), 6)
            sl = round(price * (1 + sl_p), 6)
        return NormalizedPick(
            symbol=symbol, direction=direction, entry_price=price,
            tp=tp, sl=sl, strategy=self.name, strategy_name=self.display_name,
            category="crypto", confidence=round(min(confidence, 0.95), 3), reason=reason,
        )


class VerifiedSuperTrendPT(_VerifiedBase):
    name = "verified_supertrend_ai"
    display_name = "Verified SuperTrend AI"
    tp_pct = 0.15
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse(klines)
            if len(closes) < 50:
                continue
            atr = _atr(highs, lows, closes, 10)
            vol_sma = _sma(volumes, 20)
            if atr[-1] is None or atr[-2] is None or vol_sma[-1] is None:
                continue
            price = closes[-1]
            mult = 3.0
            # SuperTrend calculation
            mid = (highs[-1] + lows[-1]) / 2
            upper = mid + mult * atr[-1]
            lower = mid - mult * atr[-1]
            prev_mid = (highs[-2] + lows[-2]) / 2
            prev_upper = prev_mid + mult * atr[-2]
            prev_lower = prev_mid - mult * atr[-2]
            # Flip detection
            bullish_flip = closes[-2] <= prev_upper and closes[-1] > upper
            bearish_flip = closes[-2] >= prev_lower and closes[-1] < lower
            # Simpler: price vs SuperTrend bands
            above_upper = price > upper
            below_lower = price < lower
            vol_ok = volumes[-1] > vol_sma[-1]

            if (price > lower and closes[-2] < prev_lower) and vol_ok:
                picks.append(self._pick(symbol, "LONG", 0.65, price,
                    reason=f"SuperTrend flip bullish, ATR={atr[-1]:.4f}, vol OK"))
            elif (price < upper and closes[-2] > prev_upper) and vol_ok:
                picks.append(self._pick(symbol, "SHORT", 0.65, price,
                    reason=f"SuperTrend flip bearish, ATR={atr[-1]:.4f}, vol OK"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedWaveTrendPT(_VerifiedBase):
    name = "verified_wavetrend"
    display_name = "Verified WaveTrend"
    tp_pct = 0.10
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, _, _, closes, _ = self._parse(klines)
            if len(closes) < 40:
                continue
            # WaveTrend: ap = hlc3 proxy (use close), esa = EMA(close, 10)
            esa = _ema(closes, 10)
            # d = EMA(|close - esa|, 10)
            diffs = []
            for i, c in enumerate(closes):
                if esa[i] is not None:
                    diffs.append(abs(c - esa[i]))
                else:
                    diffs.append(0)
            d = _ema(diffs, 10)
            # ci = (close - esa) / (0.015 * d)
            ci = []
            for i in range(len(closes)):
                if esa[i] is not None and d[i] is not None and d[i] > 0:
                    ci.append((closes[i] - esa[i]) / (0.015 * d[i]))
                else:
                    ci.append(0)
            # wt1 = EMA(ci, 21), wt2 = SMA(wt1, 4)
            wt1 = _ema(ci, 21)
            wt2 = _sma([w if w is not None else 0 for w in wt1], 4)
            if wt1[-1] is None or wt2[-1] is None or wt1[-2] is None or wt2[-2] is None:
                continue
            price = closes[-1]
            # Cross detection
            cross_up = wt1[-2] <= wt2[-2] and wt1[-1] > wt2[-1]
            cross_down = wt1[-2] >= wt2[-2] and wt1[-1] < wt2[-1]
            if cross_up and wt1[-1] < -60:
                picks.append(self._pick(symbol, "LONG", 0.68, price,
                    reason=f"WaveTrend cross up in oversold: WT1={wt1[-1]:.1f}"))
            elif cross_down and wt1[-1] > 60:
                picks.append(self._pick(symbol, "SHORT", 0.68, price,
                    reason=f"WaveTrend cross down in overbought: WT1={wt1[-1]:.1f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedEMAStackPT(_VerifiedBase):
    name = "verified_ema_stack"
    display_name = "Verified EMA Stack"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, _, _, closes, _ = self._parse(klines)
            if len(closes) < 55:
                continue
            ema9 = _ema(closes, 9)
            ema21 = _ema(closes, 21)
            ema50 = _ema(closes, 50)
            if any(v is None for v in [ema9[-1], ema21[-1], ema50[-1]]):
                continue
            price = closes[-1]
            if ema9[-1] > ema21[-1] > ema50[-1] and price > ema9[-1]:
                dist = (price - ema50[-1]) / ema50[-1]
                conf = min(0.55 + dist * 3, 0.85)
                picks.append(self._pick(symbol, "LONG", conf, price,
                    reason=f"EMA stack bullish: 9={ema9[-1]:.2f}>21={ema21[-1]:.2f}>50={ema50[-1]:.2f}"))
            elif ema9[-1] < ema21[-1] < ema50[-1] and price < ema9[-1]:
                dist = (ema50[-1] - price) / ema50[-1]
                conf = min(0.55 + dist * 3, 0.85)
                picks.append(self._pick(symbol, "SHORT", conf, price,
                    reason=f"EMA stack bearish: 9={ema9[-1]:.2f}<21={ema21[-1]:.2f}<50={ema50[-1]:.2f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedStochRsiPT(_VerifiedBase):
    name = "verified_stoch_rsi"
    display_name = "Verified Stoch RSI"
    tp_pct = 0.08
    sl_pct = 0.04

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, _, _, closes, _ = self._parse(klines)
            if len(closes) < 40:
                continue
            rsi_vals = _rsi(closes, 14)
            valid_rsi = [r for r in rsi_vals if r is not None]
            if len(valid_rsi) < 18:
                continue
            # Stochastic of RSI
            period = 14
            rsi_clean = valid_rsi[-period - 4:]
            if len(rsi_clean) < period + 4:
                continue
            # K values
            k_vals = []
            for i in range(period - 1, len(rsi_clean)):
                window = rsi_clean[i - period + 1:i + 1]
                mn, mx = min(window), max(window)
                k = ((rsi_clean[i] - mn) / (mx - mn) * 100) if mx > mn else 50
                k_vals.append(k)
            if len(k_vals) < 7:
                continue
            # Smooth K (3-period SMA) and D (3-period SMA of smoothed K)
            sk = [sum(k_vals[i - 2:i + 1]) / 3 for i in range(2, len(k_vals))]
            sd = [sum(sk[i - 2:i + 1]) / 3 for i in range(2, len(sk))]
            if len(sk) < 2 or len(sd) < 2:
                continue
            price = closes[-1]
            # Cross detection
            cross_up = sk[-2] <= sd[-2] and sk[-1] > sd[-1]
            cross_down = sk[-2] >= sd[-2] and sk[-1] < sd[-1]
            if cross_up and sk[-1] < 20:
                picks.append(self._pick(symbol, "LONG", 0.72, price,
                    reason=f"StochRSI cross up in oversold: K={sk[-1]:.1f}"))
            elif cross_down and sk[-1] > 80:
                picks.append(self._pick(symbol, "SHORT", 0.72, price,
                    reason=f"StochRSI cross down in overbought: K={sk[-1]:.1f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedKeltnerPT(_VerifiedBase):
    name = "verified_keltner_breakout"
    display_name = "Verified Keltner Breakout"
    tp_pct = 0.10
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = self._parse(klines)
            if len(closes) < 30:
                continue
            ema20 = _ema(closes, 20)
            atr10 = _atr(highs, lows, closes, 10)
            if ema20[-1] is None or atr10[-1] is None:
                continue
            price = closes[-1]
            upper = ema20[-1] + 2 * atr10[-1]
            lower = ema20[-1] - 2 * atr10[-1]
            if price > upper:
                dist = (price - upper) / upper
                picks.append(self._pick(symbol, "LONG", min(0.60 + dist * 5, 0.85), price,
                    reason=f"Keltner breakout up: price={price:.2f} > upper={upper:.2f}"))
            elif price < lower:
                dist = (lower - price) / lower
                picks.append(self._pick(symbol, "SHORT", min(0.60 + dist * 5, 0.85), price,
                    reason=f"Keltner breakout down: price={price:.2f} < lower={lower:.2f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedDonchianPT(_VerifiedBase):
    name = "verified_donchian_turtle"
    display_name = "Verified Donchian Turtle"
    tp_pct = 0.15
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = self._parse(klines)
            if len(closes) < 25:
                continue
            price = closes[-1]
            high_20 = max(highs[-21:-1])
            low_20 = min(lows[-21:-1])
            atr_vals = _atr(highs, lows, closes, 14)
            if atr_vals[-1] is None:
                continue
            if price > high_20:
                picks.append(self._pick(symbol, "LONG", 0.65, price,
                    reason=f"Donchian breakout: price={price:.2f} > 20-bar high={high_20:.2f}"))
            elif price < low_20:
                picks.append(self._pick(symbol, "SHORT", 0.65, price,
                    reason=f"Donchian breakdown: price={price:.2f} < 20-bar low={low_20:.2f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedWilliamsRPT(_VerifiedBase):
    name = "verified_williams_r"
    display_name = "Verified Williams %R"
    tp_pct = 0.06
    sl_pct = 0.03

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = self._parse(klines)
            if len(closes) < 5:
                continue
            price = closes[-1]
            hh = max(highs[-2:])
            ll = min(lows[-2:])
            wr = ((hh - price) / (hh - ll) * -100) if (hh - ll) > 0 else -50
            if wr < -90:
                picks.append(self._pick(symbol, "LONG", 0.72, price,
                    reason=f"Williams %R oversold: WR={wr:.1f} < -90"))
            elif wr > -10:
                picks.append(self._pick(symbol, "SHORT", 0.72, price,
                    reason=f"Williams %R overbought: WR={wr:.1f} > -10"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class VerifiedBTC50MAPT(_VerifiedBase):
    name = "verified_btc_50ma"
    display_name = "Verified BTC 50MA Momentum"
    tp_pct = 0.20
    sl_pct = 0.08

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        # Only applies to BTC
        for symbol in ["BTCUSDT"]:
            klines = data.get(symbol)
            if not klines or len(klines) < 300:
                continue
            _, _, _, closes, _ = self._parse(klines)
            price = closes[-1]
            # 50-day MA simulated on 4H: 50*6=300 bars
            sma_300 = sum(closes) / len(closes) if len(closes) >= 300 else sum(closes[-200:]) / min(len(closes), 200)
            if price > sma_300:
                dist = (price - sma_300) / sma_300
                picks.append(self._pick(symbol, "LONG", min(0.55 + dist * 3, 0.85), price,
                    reason=f"BTC above 50d MA proxy: price={price:.2f} > SMA={sma_300:.2f}"))
            else:
                dist = (sma_300 - price) / sma_300
                picks.append(self._pick(symbol, "SHORT", min(0.55 + dist * 3, 0.85), price,
                    reason=f"BTC below 50d MA proxy: price={price:.2f} < SMA={sma_300:.2f}"))
        return picks
