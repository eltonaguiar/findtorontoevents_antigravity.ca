"""Alpha Arena Competition Strategies — Paper trading wrappers.

Sources:
- Aggressive Patience: Alpha Arena — Qwen 3 Max (+22.32%), BTC-only EMA/MACD/RSI confluence
- Risk-Parity: Alpha Arena — DeepSeek V3.1 (+125% peak), inverse-vol multi-asset weighting
- Four-Layer Confluence: Alpha Arena — Unified methodology, EMA+RSI+BB+Momentum layers
- Regime Switcher: Alpha Arena — DeepSeek adaptation mechanism, ADX-based regime detection
- Drawdown-Responsive: Alpha Arena — dual winner risk architecture, vol-scaled momentum
- Partial Scale-Out: Alpha Arena — Qwen execution model, EMA stack + tiered exits
"""
import math
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


# ── Technical indicator helpers ──────────────────────────────────────

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


def _adx(highs, lows, closes, period=14):
    """ADX with +DI/-DI/DX smoothing."""
    n = len(closes)
    if n < period * 2 + 1:
        return [None] * n
    # True Range
    trs = [highs[0] - lows[0]]
    plus_dm = [0.0]
    minus_dm = [0.0]
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    # Wilder smoothing for ATR, +DM, -DM
    atr_s = sum(trs[:period])
    pdm_s = sum(plus_dm[:period])
    mdm_s = sum(minus_dm[:period])
    result = [None] * (period - 1)
    # First DX
    plus_di = 100 * pdm_s / max(atr_s, 1e-10)
    minus_di = 100 * mdm_s / max(atr_s, 1e-10)
    di_sum = plus_di + minus_di
    dx_vals = [abs(plus_di - minus_di) / max(di_sum, 1e-10) * 100 if di_sum > 0 else 0]
    for i in range(period, n):
        atr_s = atr_s - atr_s / period + trs[i]
        pdm_s = pdm_s - pdm_s / period + plus_dm[i]
        mdm_s = mdm_s - mdm_s / period + minus_dm[i]
        plus_di = 100 * pdm_s / max(atr_s, 1e-10)
        minus_di = 100 * mdm_s / max(atr_s, 1e-10)
        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / max(di_sum, 1e-10) * 100 if di_sum > 0 else 0
        dx_vals.append(dx)
    # ADX = smoothed DX over `period` bars
    if len(dx_vals) < period:
        return [None] * n
    adx_val = sum(dx_vals[:period]) / period
    adx_result = [None] * (period - 1 + period - 1)
    adx_result.append(adx_val)
    for i in range(period, len(dx_vals)):
        adx_val = (adx_val * (period - 1) + dx_vals[i]) / period
        adx_result.append(adx_val)
    # Pad to length n
    while len(adx_result) < n:
        adx_result.append(adx_result[-1] if adx_result else None)
    return adx_result[:n]


def _macd(closes, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram) as lists."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = []
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(ema_fast[i] - ema_slow[i])
        else:
            macd_line.append(None)
    # Signal line = EMA of MACD values (skip Nones)
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        return macd_line, [None] * len(closes), [None] * len(closes)
    sig_ema = _ema(valid_macd, signal)
    # Map signal back to full length
    signal_line = [None] * len(closes)
    valid_idx = 0
    for i in range(len(closes)):
        if macd_line[i] is not None:
            if valid_idx < len(sig_ema):
                signal_line[i] = sig_ema[valid_idx]
            valid_idx += 1
    histogram = []
    for i in range(len(closes)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram.append(macd_line[i] - signal_line[i])
        else:
            histogram.append(None)
    return macd_line, signal_line, histogram


# ── Base class ───────────────────────────────────────────────────────

class _AlphaArenaBase(BaseStrategy):
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "verified"
    tp_pct = 0.12
    sl_pct = 0.05

    def fetch_data(self, symbol=None):
        if symbol:
            return self.fetch_klines(symbol, interval="4h", limit=200)
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="4h", limit=200)
                if klines:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def _parse(self, klines):
        return (
            [float(k[1]) for k in klines],   # opens
            [float(k[2]) for k in klines],   # highs
            [float(k[3]) for k in klines],   # lows
            [float(k[4]) for k in klines],   # closes
            [float(k[5]) for k in klines],   # volumes
        )

    def _pick(self, symbol, direction, confidence, price, tp_pct=None, sl_pct=None, reason=""):
        tp = tp_pct or self.tp_pct
        sl = sl_pct or self.sl_pct
        if direction == "LONG":
            tp_price = price * (1 + tp / 100) if tp > 1 else price * (1 + tp)
            sl_price = price * (1 - sl / 100) if sl > 1 else price * (1 - sl)
        else:
            tp_price = price * (1 - tp / 100) if tp > 1 else price * (1 - tp)
            sl_price = price * (1 + sl / 100) if sl > 1 else price * (1 + sl)
        return NormalizedPick(
            symbol=symbol, direction=direction, confidence=round(min(confidence, 0.95), 3),
            entry_price=price, tp=round(tp_price, 6), sl=round(sl_price, 6),
            strategy=self.name, strategy_name=self.display_name,
            reason=reason, category="crypto",
        )


# ── Strategy 1: Aggressive Patience (BTC-only) ──────────────────────

class AlphaAggressivePatience_PT(_AlphaArenaBase):
    """BTC-only: EMA(50)>EMA(200) + MACD histogram expanding + RSI 40-65 upward slope.
    Source: Alpha Arena — Qwen 3 Max (+22.32%).
    """
    name = "alpha_aggressive_patience"
    display_name = "Alpha Aggressive Patience"
    source = "Alpha Arena — Qwen 3 Max (+22.32%)"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        # BTC-only
        klines = data.get("BTCUSDT")
        if not klines or len(klines) < 200:
            return []
        _, highs, lows, closes, _ = self._parse(klines)
        price = closes[-1]

        ema50 = _ema(closes, 50)
        ema200 = _ema(closes, 200)
        if ema50[-1] is None or ema200[-1] is None:
            return []
        if ema50[-1] <= ema200[-1]:
            return []  # Trend filter: EMA50 must be above EMA200

        # MACD histogram expanding
        _, _, hist = _macd(closes)
        if hist[-1] is None or hist[-2] is None or hist[-3] is None:
            return []
        hist_expanding = hist[-1] > hist[-2] > hist[-3] and hist[-1] > 0

        if not hist_expanding:
            return []

        # RSI 40-65 with upward slope
        rsi_vals = _rsi(closes, 14)
        if rsi_vals[-1] is None or rsi_vals[-2] is None:
            return []
        rsi_now = rsi_vals[-1]
        rsi_prev = rsi_vals[-2]
        if not (40 <= rsi_now <= 65 and rsi_now > rsi_prev):
            return []

        # ATR for TP/SL
        atr_vals = _atr(highs, lows, closes, 14)
        atr_now = atr_vals[-1]
        if atr_now is None or atr_now == 0:
            return []

        # TP: 3x ATR, SL: min(swing_low_10, 2x ATR)
        tp_price = price + 3 * atr_now
        swing_low_10 = min(lows[-10:])
        sl_from_swing = price - swing_low_10
        sl_from_atr = 2 * atr_now
        sl_dist = min(sl_from_swing, sl_from_atr) if sl_from_swing > 0 else sl_from_atr
        sl_price = price - sl_dist

        # Min R:R 2.5:1
        reward = tp_price - price
        risk = price - sl_price
        if risk <= 0 or reward / risk < 2.5:
            return []

        confidence = min(0.60 + (rsi_now - 40) / 100 + (hist[-1] / price) * 100, 0.90)
        picks.append(NormalizedPick(
            symbol="BTCUSDT", direction="LONG", entry_price=price,
            tp=round(tp_price, 6), sl=round(sl_price, 6),
            strategy=self.name, strategy_name=self.display_name,
            category="crypto", confidence=round(min(confidence, 0.95), 3),
            reason=f"EMA50>{ema50[-1]:.0f}>EMA200={ema200[-1]:.0f}, MACD hist expanding={hist[-1]:.2f}, RSI={rsi_now:.1f} slope+, R:R={reward/risk:.1f}:1",
        ))
        return picks[:1]


# ── Strategy 2: Risk-Parity (multi-asset inverse-vol) ────────────────

class AlphaRiskParity_PT(_AlphaArenaBase):
    """Multi-asset inverse-vol weighting. Entry: close > EMA(50) AND weight > 0.10.
    Source: Alpha Arena — DeepSeek V3.1 (+125% peak).
    """
    name = "alpha_risk_parity"
    display_name = "Alpha Risk-Parity"
    source = "Alpha Arena — DeepSeek V3.1 (+125% peak)"
    tp_pct = 0.10
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []

        # Step 1: compute inverse-vol weights for all symbols
        vol_data = {}  # symbol -> (1/std, closes, highs, lows, price)
        for symbol, klines in data.items():
            if not klines or len(klines) < 60:
                continue
            _, highs, lows, closes, _ = self._parse(klines)
            price = closes[-1]
            # 20-bar return std
            returns = [(closes[i] / closes[i - 1] - 1) for i in range(max(1, len(closes) - 20), len(closes))]
            if len(returns) < 10:
                continue
            std = (sum(r ** 2 for r in returns) / len(returns)) ** 0.5
            if std <= 0:
                continue
            vol_data[symbol] = (1.0 / std, closes, highs, lows, price)

        if not vol_data:
            return []

        # Normalize weights
        total_inv_vol = sum(v[0] for v in vol_data.values())
        if total_inv_vol <= 0:
            return []

        for symbol, (inv_vol, closes, highs, lows, price) in vol_data.items():
            weight = inv_vol / total_inv_vol

            if weight < 0.10:
                continue  # Too little allocation

            ema50 = _ema(closes, 50)
            if ema50[-1] is None:
                continue
            if price <= ema50[-1]:
                continue  # Must be above EMA50

            confidence = min(0.50 + weight * 2.0, 0.90)
            picks.append(self._pick(
                symbol, "LONG", confidence, price,
                tp_pct=self.tp_pct, sl_pct=self.sl_pct,
                reason=f"Risk-Parity: weight={weight:.1%}, close={price:.2f} > EMA50={ema50[-1]:.2f}",
            ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── Strategy 3: Four-Layer Confluence ────────────────────────────────

class AlphaFourLayerConfluence_PT(_AlphaArenaBase):
    """All 4 layers must confirm: EMA trend + RSI zone + BB squeeze + Momentum composite.
    Source: Alpha Arena — Unified methodology.
    """
    name = "alpha_four_layer"
    display_name = "Alpha Four-Layer Confluence"
    source = "Alpha Arena — Unified methodology"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if not klines or len(klines) < 200:
                continue
            _, highs, lows, closes, volumes = self._parse(klines)
            price = closes[-1]

            # Layer 1: EMA(50) > EMA(200) — trend
            ema50 = _ema(closes, 50)
            ema200 = _ema(closes, 200)
            if ema50[-1] is None or ema200[-1] is None:
                continue
            layer1 = ema50[-1] > ema200[-1]
            if not layer1:
                continue

            # Layer 2: RSI(14) 30-70 + slope > 0
            rsi_vals = _rsi(closes, 14)
            if rsi_vals[-1] is None or rsi_vals[-2] is None:
                continue
            rsi_now = rsi_vals[-1]
            layer2 = 30 <= rsi_now <= 70 and rsi_vals[-1] > rsi_vals[-2]
            if not layer2:
                continue

            # Layer 3: Bollinger Band squeeze breakout
            sma20 = _sma(closes, 20)
            if sma20[-1] is None:
                continue
            # Compute bandwidth over last 100 bars
            bandwidths = []
            for i in range(max(20, len(closes) - 100), len(closes)):
                if sma20[i] is None:
                    continue
                window = closes[i - 19:i + 1]
                std = (sum((c - sma20[i]) ** 2 for c in window) / 20) ** 0.5
                bw = (4 * std) / max(sma20[i], 1e-10)
                bandwidths.append(bw)
            if len(bandwidths) < 10:
                continue
            current_bw = bandwidths[-1]
            sorted_bw = sorted(bandwidths)
            bw_percentile = sum(1 for b in sorted_bw if b <= current_bw) / len(sorted_bw)
            layer3 = bw_percentile < 0.20  # Squeeze: bandwidth in bottom 20th percentile
            if not layer3:
                continue

            # Layer 4: Momentum composite (price > EMA20 + MACD > signal + vol > 1.2x avg)
            ema20 = _ema(closes, 20)
            if ema20[-1] is None:
                continue
            macd_line, sig_line, _ = _macd(closes)
            if macd_line[-1] is None or sig_line[-1] is None:
                continue
            vol_avg = sum(volumes[-20:]) / 20
            layer4 = (price > ema20[-1] and macd_line[-1] > sig_line[-1] and volumes[-1] > 1.2 * vol_avg)
            if not layer4:
                continue

            # All 4 layers confirmed — compute ATR-based TP/SL
            atr_vals = _atr(highs, lows, closes, 14)
            atr_now = atr_vals[-1]
            if atr_now is None or atr_now == 0:
                continue
            tp_price = price + 2.5 * atr_now
            sl_price = price - 1.5 * atr_now

            confidence = min(0.70 + (rsi_now - 30) / 200, 0.90)
            picks.append(NormalizedPick(
                symbol=symbol, direction="LONG", entry_price=price,
                tp=round(tp_price, 6), sl=round(sl_price, 6),
                strategy=self.name, strategy_name=self.display_name,
                category="crypto", confidence=round(min(confidence, 0.95), 3),
                reason=f"4-Layer: EMA50>200, RSI={rsi_now:.1f} slope+, BB squeeze pct={bw_percentile:.0%}, MACD>sig vol={volumes[-1]/vol_avg:.1f}x",
            ))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── Strategy 4: Regime Switcher (ADX-based) ──────────────────────────

class AlphaRegimeSwitcher_PT(_AlphaArenaBase):
    """ADX(14) > 25 → trending (EMA 21/55 crossover); ADX <= 25 → ranging (RSI).
    Source: Alpha Arena — DeepSeek adaptation mechanism.
    """
    name = "alpha_regime_switcher"
    display_name = "Alpha Regime Switcher"
    source = "Alpha Arena — DeepSeek adaptation mechanism"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if not klines or len(klines) < 100:
                continue
            _, highs, lows, closes, _ = self._parse(klines)
            price = closes[-1]

            adx_vals = _adx(highs, lows, closes, 14)
            if adx_vals[-1] is None:
                continue
            adx_now = adx_vals[-1]

            if adx_now > 25:
                # ── Trending regime: EMA(21/55) crossover ──
                ema21 = _ema(closes, 21)
                ema55 = _ema(closes, 55)
                if ema21[-1] is None or ema55[-1] is None or ema21[-2] is None or ema55[-2] is None:
                    continue

                cross_up = ema21[-2] <= ema55[-2] and ema21[-1] > ema55[-1]
                cross_down = ema21[-2] >= ema55[-2] and ema21[-1] < ema55[-1]
                trending_up = ema21[-1] > ema55[-1]
                trending_down = ema21[-1] < ema55[-1]

                if cross_up or trending_up:
                    conf = 0.72 if cross_up else 0.62
                    picks.append(self._pick(
                        symbol, "LONG", conf, price,
                        tp_pct=0.15, sl_pct=0.06,
                        reason=f"Trending regime ADX={adx_now:.1f}: EMA21={ema21[-1]:.2f}>EMA55={ema55[-1]:.2f}{'(CROSS)' if cross_up else ''}",
                    ))
                elif cross_down or trending_down:
                    conf = 0.72 if cross_down else 0.62
                    picks.append(self._pick(
                        symbol, "SHORT", conf, price,
                        tp_pct=0.15, sl_pct=0.06,
                        reason=f"Trending regime ADX={adx_now:.1f}: EMA21={ema21[-1]:.2f}<EMA55={ema55[-1]:.2f}{'(CROSS)' if cross_down else ''}",
                    ))
            else:
                # ── Ranging regime: RSI oversold/overbought ──
                rsi_vals = _rsi(closes, 14)
                if rsi_vals[-1] is None:
                    continue
                rsi_now = rsi_vals[-1]

                if rsi_now < 30:
                    conf = min(0.55 + (30 - rsi_now) / 50, 0.85)
                    picks.append(self._pick(
                        symbol, "LONG", conf, price,
                        tp_pct=0.08, sl_pct=0.04,
                        reason=f"Ranging regime ADX={adx_now:.1f}: RSI={rsi_now:.1f} oversold",
                    ))
                elif rsi_now > 70:
                    conf = min(0.55 + (rsi_now - 70) / 50, 0.85)
                    picks.append(self._pick(
                        symbol, "SHORT", conf, price,
                        tp_pct=0.08, sl_pct=0.04,
                        reason=f"Ranging regime ADX={adx_now:.1f}: RSI={rsi_now:.1f} overbought",
                    ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── Strategy 5: Drawdown-Responsive ──────────────────────────────────

class AlphaDrawdownResponsive_PT(_AlphaArenaBase):
    """Vol-scaled momentum with drawdown penalty.
    Source: Alpha Arena — dual winner risk architecture.
    """
    name = "alpha_drawdown_responsive"
    display_name = "Alpha Drawdown-Responsive"
    source = "Alpha Arena — dual winner risk architecture"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if not klines or len(klines) < 60:
                continue
            _, highs, lows, closes, _ = self._parse(klines)
            price = closes[-1]

            if len(closes) < 50:
                continue

            # 14-bar return
            ret_14 = (closes[-1] / closes[-14] - 1) if closes[-14] > 0 else 0

            # 20-bar realized volatility
            returns = [(closes[i] / closes[i - 1] - 1) for i in range(max(1, len(closes) - 20), len(closes))]
            if len(returns) < 10:
                continue
            vol_20 = (sum(r ** 2 for r in returns) / len(returns)) ** 0.5
            if vol_20 <= 0:
                continue

            # Vol-scaled momentum signal
            signal = ret_14 / vol_20

            # Drawdown penalty: if price < 0.95 * max(close, 50), reduce conf by 30%
            recent_high = max(closes[-50:])
            in_drawdown = price < 0.95 * recent_high

            # ATR for TP/SL
            atr_vals = _atr(highs, lows, closes, 14)
            atr_now = atr_vals[-1]
            if atr_now is None or atr_now == 0:
                continue

            tp_price_long = price + 2 * atr_now
            sl_price_long = price - 1.5 * atr_now
            tp_price_short = price - 2 * atr_now
            sl_price_short = price + 1.5 * atr_now

            if signal > 1.0:
                conf = min(0.55 + signal * 0.08, 0.88)
                if in_drawdown:
                    conf *= 0.70  # 30% penalty
                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG", entry_price=price,
                    tp=round(tp_price_long, 6), sl=round(sl_price_long, 6),
                    strategy=self.name, strategy_name=self.display_name,
                    category="crypto", confidence=round(min(conf, 0.95), 3),
                    reason=f"Vol-Mom signal={signal:.2f}, vol20={vol_20:.4f}, dd={'YES -30%' if in_drawdown else 'NO'}, TP=2xATR SL=1.5xATR",
                ))
            elif signal < -1.0:
                conf = min(0.55 + abs(signal) * 0.08, 0.88)
                if in_drawdown:
                    conf *= 0.70
                picks.append(NormalizedPick(
                    symbol=symbol, direction="SHORT", entry_price=price,
                    tp=round(tp_price_short, 6), sl=round(sl_price_short, 6),
                    strategy=self.name, strategy_name=self.display_name,
                    category="crypto", confidence=round(min(conf, 0.95), 3),
                    reason=f"Vol-Mom signal={signal:.2f}, vol20={vol_20:.4f}, dd={'YES -30%' if in_drawdown else 'NO'}, TP=2xATR SL=1.5xATR",
                ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── Strategy 6: Partial Scale-Out ────────────────────────────────────

class AlphaPartialScaleOut_PT(_AlphaArenaBase):
    """EMA 9>21>50 stack + RSI 45-65 + volume > 1.3x avg. Tiered exit plan.
    Source: Alpha Arena — Qwen execution model.
    """
    name = "alpha_partial_scaleout"
    display_name = "Alpha Partial Scale-Out"
    source = "Alpha Arena — Qwen execution model"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if not klines or len(klines) < 60:
                continue
            _, highs, lows, closes, volumes = self._parse(klines)
            price = closes[-1]

            # EMA stack: 9 > 21 > 50
            ema9 = _ema(closes, 9)
            ema21 = _ema(closes, 21)
            ema50 = _ema(closes, 50)
            if ema9[-1] is None or ema21[-1] is None or ema50[-1] is None:
                continue
            ema_stack = ema9[-1] > ema21[-1] > ema50[-1]
            if not ema_stack:
                continue

            # RSI 45-65
            rsi_vals = _rsi(closes, 14)
            if rsi_vals[-1] is None:
                continue
            rsi_now = rsi_vals[-1]
            if not (45 <= rsi_now <= 65):
                continue

            # Volume > 1.3x 20-bar average
            vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            if volumes[-1] <= 1.3 * vol_avg:
                continue

            # ATR for TP/SL
            atr_vals = _atr(highs, lows, closes, 14)
            atr_now = atr_vals[-1]
            if atr_now is None or atr_now == 0:
                continue

            tp_price = price + 3 * atr_now
            sl_price = price - 1 * atr_now

            vol_ratio = volumes[-1] / max(vol_avg, 1)
            confidence = min(0.60 + (rsi_now - 45) / 100 + (vol_ratio - 1.3) * 0.1, 0.90)

            picks.append(NormalizedPick(
                symbol=symbol, direction="LONG", entry_price=price,
                tp=round(tp_price, 6), sl=round(sl_price, 6),
                strategy=self.name, strategy_name=self.display_name,
                category="crypto", confidence=round(min(confidence, 0.95), 3),
                reason=f"EMA stack 9>{ema9[-1]:.0f}>21>{ema21[-1]:.0f}>50>{ema50[-1]:.0f}, RSI={rsi_now:.1f}, vol={vol_ratio:.1f}x avg. Scale: 50%@2R, 25%@3R, 25% trail",
            ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]
