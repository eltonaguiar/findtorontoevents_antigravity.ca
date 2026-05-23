"""Leap Baby Strategies - Swing Trail, HTF Momentum, Concentrated R:R,
Harmonic Confluence, Elliott Impulse, Fee Aware Sniper for paper trading."""
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
# Shared fetch helper
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


def _calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    if len(trs) < period:
        return None
    return float(np.mean(trs[-period:]))


# ---------------------------------------------------------------------------
# Strategy classes
# ---------------------------------------------------------------------------

class LeapSwingTrailPT(BaseStrategy):
    name = "leap_swing_trail"
    display_name = "Leap - Swing Trail"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "leap"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 25:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            price = closes[-1]

            # Breakout: close > max(high[-20:])
            recent_highs = highs[-21:-1]  # exclude current bar
            if len(recent_highs) < 20:
                continue
            swing_high = max(recent_highs)
            if price <= swing_high:
                continue

            # SL: min(low[-10:]) swing low trailing
            recent_lows = lows[-10:]
            sl = round(min(recent_lows), 6)
            risk = price - sl
            if risk <= 0:
                continue

            # TP: entry + 3 * risk (3:1 R:R)
            tp = round(price + 3 * risk, 6)

            # Cap TP at +25%
            tp = min(tp, round(price * 1.25, 6))

            breakout_pct = (price - swing_high) / swing_high
            confidence = min(0.85, 0.55 + breakout_pct * 10)

            picks.append(NormalizedPick(
                symbol=symbol, direction="LONG",
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=f"Swing Trail BUY: breakout {price:.2f} > swing high {swing_high:.2f}, SL={sl:.2f}, R:R=3:1",
                raw_signal={"swing_high": swing_high, "sl": sl, "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class LeapHTFMomentumPT(BaseStrategy):
    name = "leap_htf_momentum"
    display_name = "Leap - HTF Momentum"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "leap"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 55:
                continue
            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            sma50 = float(np.mean(closes[-50:]))
            rsi = _calc_rsi(closes, 14)
            if rsi is None:
                continue

            if price > sma50 and rsi < 45:
                direction = "LONG"
                tp = round(price * 1.15, 6)
                sl = round(price * 0.94, 6)
                confidence = min(0.85, 0.55 + (45 - rsi) * 0.007)
                reason = f"HTF Momentum BUY: SMA50={sma50:.2f}, RSI={rsi:.1f} (pullback in uptrend)"
            elif price < sma50 and rsi > 55:
                direction = "SHORT"
                tp = round(price * 0.85, 6)
                sl = round(price * 1.06, 6)
                confidence = min(0.85, 0.55 + (rsi - 55) * 0.007)
                reason = f"HTF Momentum SELL: SMA50={sma50:.2f}, RSI={rsi:.1f} (bounce in downtrend)"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"sma50": round(sma50, 4), "rsi": round(rsi, 2), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class LeapConcentratedRR_PT(BaseStrategy):
    name = "leap_concentrated_rr"
    display_name = "Leap - Concentrated R:R"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "leap"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 30:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            price = closes[-1]

            atr = _calc_atr(highs, lows, closes, 14)
            if atr is None or atr <= 0:
                continue

            sma20 = float(np.mean(closes[-20:]))
            rsi = _calc_rsi(closes, 14)
            if rsi is None:
                continue

            # Long: price above SMA20 trend, RSI not overbought
            if price > sma20 and rsi < 65:
                direction = "LONG"
                sl_raw = price - 1.3 * atr
                tp_raw = price + 4 * atr
                # Cap
                sl = round(max(sl_raw, price * 0.94), 6)
                tp = round(min(tp_raw, price * 1.20), 6)
            elif price < sma20 and rsi > 35:
                direction = "SHORT"
                sl_raw = price + 1.3 * atr
                tp_raw = price - 4 * atr
                sl = round(min(sl_raw, price * 1.06), 6)
                tp = round(max(tp_raw, price * 0.80), 6)
            else:
                continue

            # Verify R:R > 3:1
            reward = abs(tp - price)
            risk = abs(price - sl)
            if risk <= 0 or reward / risk < 3.0:
                continue

            rr = reward / risk
            confidence = min(0.85, 0.55 + (rr - 3) * 0.05)
            reason = f"Concentrated R:R {'BUY' if direction == 'LONG' else 'SELL'}: ATR={atr:.2f}, R:R={rr:.1f}:1"

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"atr": round(atr, 4), "rr_ratio": round(rr, 2), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class LeapHarmonicPT(BaseStrategy):
    name = "leap_harmonic_confluence"
    display_name = "Leap - Harmonic Confluence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "leap"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            price = closes[-1]

            # Find recent swing high and low (last 30 bars)
            recent_high = max(highs[-30:])
            recent_low = min(lows[-30:])
            swing_range = recent_high - recent_low
            if swing_range <= 0:
                continue

            # Check Fibonacci retracement zone (38.2% - 61.8%)
            retrace = (recent_high - price) / swing_range  # 0=at high, 1=at low
            in_fib_zone = 0.382 <= retrace <= 0.618

            if not in_fib_zone:
                continue

            # RSI divergence confirmation
            rsi = _calc_rsi(closes, 14)
            if rsi is None:
                continue

            # Bullish: price in fib zone + RSI showing oversold tendency
            if retrace > 0.45 and rsi < 45:
                direction = "LONG"
                tp = round(price * 1.12, 6)
                sl = round(price * 0.95, 6)
                confidence = min(0.88, 0.60 + (0.618 - retrace) * 2)
                reason = f"Harmonic BUY: Fib retrace={retrace:.1%}, RSI={rsi:.1f}, range=[{recent_low:.2f}-{recent_high:.2f}]"
            elif retrace < 0.45 and rsi > 55:
                direction = "SHORT"
                tp = round(price * 0.88, 6)
                sl = round(price * 1.05, 6)
                confidence = min(0.88, 0.60 + (retrace - 0.382) * 2)
                reason = f"Harmonic SELL: Fib retrace={retrace:.1%}, RSI={rsi:.1f}, range=[{recent_low:.2f}-{recent_high:.2f}]"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"fib_retrace": round(retrace, 4), "rsi": round(rsi, 2),
                            "swing_high": recent_high, "swing_low": recent_low},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:3]


class LeapElliottPT(BaseStrategy):
    name = "leap_elliott_impulse"
    display_name = "Leap - Elliott Impulse"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "leap"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 40:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            price = closes[-1]

            # Wave 1 detection: close > 20-period high (impulse breakout)
            window_high = max(highs[-21:-1]) if len(highs) > 21 else max(highs[:-1])
            window_low = min(lows[-21:-1]) if len(lows) > 21 else min(lows[:-1])

            wave1_range = window_high - window_low
            if wave1_range <= 0:
                continue

            # Wave 2: pullback into 38.2%-61.8% of Wave 1
            retrace_from_high = (window_high - price) / wave1_range

            # Bullish Elliott: Wave 1 breakout happened recently, now in Wave 2 pullback
            if 0.382 <= retrace_from_high <= 0.618:
                # Entry on break above Wave 1 midpoint
                wave1_mid = window_low + wave1_range * 0.5
                if price > wave1_mid:
                    direction = "LONG"
                    tp = round(price * 1.15, 6)
                    sl = round(price * 0.94, 6)
                    confidence = min(0.85, 0.58 + (0.618 - retrace_from_high) * 1.5)
                    reason = (f"Elliott Impulse BUY: W1 range=[{window_low:.2f}-{window_high:.2f}], "
                              f"retrace={retrace_from_high:.1%}, entry > midpoint {wave1_mid:.2f}")

                    picks.append(NormalizedPick(
                        symbol=symbol, direction=direction,
                        entry_price=price, tp=tp, sl=sl,
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category, confidence=round(confidence, 3),
                        reason=reason,
                        raw_signal={"wave1_high": window_high, "wave1_low": window_low,
                                    "retrace": round(retrace_from_high, 4), "price": price},
                    ))

            # Bearish Elliott: inverse
            retrace_from_low = (price - window_low) / wave1_range
            if 0.382 <= retrace_from_low <= 0.618:
                wave1_mid = window_low + wave1_range * 0.5
                if price < wave1_mid:
                    direction = "SHORT"
                    tp = round(price * 0.85, 6)
                    sl = round(price * 1.06, 6)
                    confidence = min(0.85, 0.58 + (0.618 - retrace_from_low) * 1.5)
                    reason = (f"Elliott Impulse SELL: W1 range=[{window_low:.2f}-{window_high:.2f}], "
                              f"retrace={retrace_from_low:.1%}, entry < midpoint {wave1_mid:.2f}")

                    picks.append(NormalizedPick(
                        symbol=symbol, direction=direction,
                        entry_price=price, tp=tp, sl=sl,
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category, confidence=round(confidence, 3),
                        reason=reason,
                        raw_signal={"wave1_high": window_high, "wave1_low": window_low,
                                    "retrace": round(retrace_from_low, 4), "price": price},
                    ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


class LeapFeeAwarePT(BaseStrategy):
    name = "leap_fee_aware_sniper"
    display_name = "Leap - Fee Aware Sniper"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "leap"

    def fetch_data(self) -> dict:
        return _fetch_all(self)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]

            rsi = _calc_rsi(closes, 14)
            if rsi is None:
                continue

            avg_vol = float(np.mean(volumes[-20:]))
            vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0

            sma50 = float(np.mean(closes[-50:]))

            # RSI extreme + volume 2x avg + trend alignment
            if rsi < 25 and vol_ratio >= 2.0 and price > sma50:
                direction = "LONG"
                tp = round(price * 1.18, 6)
                sl = round(price * 0.95, 6)
                confidence = min(0.92, 0.75 + (25 - rsi) * 0.005 + (vol_ratio - 2) * 0.02)
                reason = f"Fee Aware Sniper BUY: RSI={rsi:.1f}, Vol={vol_ratio:.1f}x avg, trend aligned"
            elif rsi > 75 and vol_ratio >= 2.0 and price < sma50:
                direction = "SHORT"
                tp = round(price * 0.82, 6)
                sl = round(price * 1.05, 6)
                confidence = min(0.92, 0.75 + (rsi - 75) * 0.005 + (vol_ratio - 2) * 0.02)
                reason = f"Fee Aware Sniper SELL: RSI={rsi:.1f}, Vol={vol_ratio:.1f}x avg, trend aligned"
            else:
                continue

            # Min confidence gate
            if confidence < 0.75:
                continue

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction,
                entry_price=price, tp=tp, sl=sl,
                strategy=self.name, strategy_name=self.display_name,
                category=self.category, confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"rsi": round(rsi, 2), "vol_ratio": round(vol_ratio, 2),
                            "sma50": round(sma50, 4), "price": price},
            ))
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
