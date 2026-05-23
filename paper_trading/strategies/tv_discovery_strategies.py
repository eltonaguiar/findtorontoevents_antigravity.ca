"""TradingView Discovery Strategies — Paper trading wrappers.

6 strategies sourced from TradingView Editor's Picks, LuxAlgo, and lesser-known gems.
Each translates a TradingView indicator/strategy into a paper trading baby strategy.

Sources:
- SuperTrend AI Adaptive: DefinedEdge (2026), regime-adaptive SuperTrend + 5-factor scoring
- VCP Minervini Breakout: Mark Minervini VCP, kaspareit-trading v2 (TV open source)
- HMM Regime Detector: UAlgo HMM Reversal Finder (simplified 3-state regime classifier)
- Liquidity Cluster Order Flow: LuxAlgo Liquidity Clusters Magnitude + Order Flow
- Consecutive Candle Streak: LuxAlgo Consecutive Candle Streak Analysis (mean reversion)
- Central Bank Liquidity Gap: Arthur Hayes Fed BS-RRP-TGA (price-based proxy)
"""
import math
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


# ---------------------------------------------------------------------------
# Shared helpers (pure-list math, no pandas dependency)
# ---------------------------------------------------------------------------

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


def _adx(highs, lows, closes, period=14):
    """Simplified ADX — returns list aligned with input."""
    n = len(closes)
    if n < period * 2 + 1:
        return [None] * n
    plus_dm = [0.0]
    minus_dm = [0.0]
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    atr_vals = _atr(highs, lows, closes, period)
    # Smooth +DM, -DM
    sm_plus = [None] * (period - 1)
    sm_minus = [None] * (period - 1)
    sm_plus.append(sum(plus_dm[:period]) / period)
    sm_minus.append(sum(minus_dm[:period]) / period)
    for i in range(period, n):
        sm_plus.append((sm_plus[-1] * (period - 1) + plus_dm[i]) / period)
        sm_minus.append((sm_minus[-1] * (period - 1) + minus_dm[i]) / period)
    dx_vals = [None] * n
    for i in range(period - 1, n):
        if atr_vals[i] is None or sm_plus[i] is None or atr_vals[i] == 0:
            continue
        di_plus = 100 * sm_plus[i] / atr_vals[i]
        di_minus = 100 * sm_minus[i] / atr_vals[i]
        denom = di_plus + di_minus
        dx_vals[i] = 100 * abs(di_plus - di_minus) / denom if denom > 0 else 0
    # Smooth DX into ADX
    adx_vals = [None] * n
    first_dx = [v for v in dx_vals[period - 1:2 * period - 1] if v is not None]
    if len(first_dx) < period:
        return [None] * n
    start_idx = 2 * period - 2
    adx_vals[start_idx] = sum(first_dx) / len(first_dx)
    for i in range(start_idx + 1, n):
        if dx_vals[i] is None or adx_vals[i - 1] is None:
            adx_vals[i] = adx_vals[i - 1]
            continue
        adx_vals[i] = (adx_vals[i - 1] * (period - 1) + dx_vals[i]) / period
    return adx_vals


def _stdev(values, period):
    """Rolling standard deviation."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        result[i] = math.sqrt(var)
    return result


# ---------------------------------------------------------------------------
# Base class for all TV Discovery strategies
# ---------------------------------------------------------------------------

class _TVDiscoveryBase(BaseStrategy):
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "tv_discovery"
    interval = "4h"
    limit = 300
    tp_pct = 0.12
    sl_pct = 0.05

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval=self.interval, limit=self.limit)
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

    def _atr_pick(self, symbol, direction, confidence, price, atr_val, tp_mult, sl_mult, reason=""):
        """Create pick using ATR-based TP/SL."""
        if direction == "LONG":
            tp = round(price + atr_val * tp_mult, 6)
            sl = round(price - atr_val * sl_mult, 6)
        else:
            tp = round(price - atr_val * tp_mult, 6)
            sl = round(price + atr_val * sl_mult, 6)
        return NormalizedPick(
            symbol=symbol, direction=direction, entry_price=price,
            tp=tp, sl=sl, strategy=self.name, strategy_name=self.display_name,
            category="crypto", confidence=round(min(confidence, 0.95), 3), reason=reason,
        )


# ===========================================================================
# 1. SuperTrend AI Adaptive
# ===========================================================================

class TVSuperTrendAIPT(_TVDiscoveryBase):
    """Regime-adaptive SuperTrend + 5-factor AI scoring.

    Source: DefinedEdge (Feb 2026), +2,091% on BTC 4H (2015-2026).
    Logic: SuperTrend with dynamic ATR multiplier per regime (trending/volatile/ranging).
    5-factor score (volume, displacement, EMA alignment, regime quality, band distance).
    Only enters when score >= 65 (75 in ranging regimes).
    """
    name = "tv_supertrend_ai"
    display_name = "TV SuperTrend AI Adaptive"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse(klines)
            n = len(closes)
            if n < 60:
                continue
            price = closes[-1]
            atr_vals = _atr(highs, lows, closes, 10)
            ema9 = _ema(closes, 9)
            ema21 = _ema(closes, 21)
            ema50 = _ema(closes, 50)
            adx_vals = _adx(highs, lows, closes, 14)
            avg_vol = _sma(volumes, 20)
            avg_atr = _sma([v for v in atr_vals if v is not None], 50)

            if any(v is None for v in [atr_vals[-1], ema9[-1], ema21[-1], ema50[-1], adx_vals[-1], avg_vol[-1]]):
                continue
            if not avg_atr or avg_atr[-1] is None or avg_atr[-1] == 0:
                continue

            cur_atr = atr_vals[-1]
            cur_adx = adx_vals[-1] or 0

            # Regime detection
            if cur_adx > 25:
                regime = "trending"
                mult = 3.0
                min_score = 65
            elif cur_atr > 2 * avg_atr[-1]:
                regime = "volatile"
                mult = 4.5
                min_score = 65
            else:
                regime = "ranging"
                mult = 2.0
                min_score = 75

            # SuperTrend calculation
            mid = (highs[-1] + lows[-1]) / 2
            upper_band = mid + mult * cur_atr
            lower_band = mid - mult * cur_atr
            prev_mid = (highs[-2] + lows[-2]) / 2
            prev_upper = prev_mid + mult * (atr_vals[-2] or cur_atr)
            prev_lower = prev_mid - mult * (atr_vals[-2] or cur_atr)

            # Direction: bullish if close > upper band flipped
            cur_bullish = closes[-1] > prev_lower
            prev_bullish = closes[-2] > (prev_lower if len(closes) > 2 else prev_lower)

            # Detect flip
            flip_bull = cur_bullish and not prev_bullish
            flip_bear = not cur_bullish and prev_bullish

            if not flip_bull and not flip_bear:
                continue

            # 5-Factor AI scoring (each 0-20)
            vol_ratio = volumes[-1] / avg_vol[-1] if avg_vol[-1] > 0 else 1
            score_volume = min(20, vol_ratio * 10)

            band_dist = abs(closes[-1] - (lower_band if cur_bullish else upper_band))
            score_displacement = min(20, (band_dist / cur_atr) * 10) if cur_atr > 0 else 0

            if ema9[-1] > ema21[-1] > ema50[-1]:
                score_ema = 20
            elif ema9[-1] > ema21[-1] or ema9[-1] > ema50[-1]:
                score_ema = 10
            else:
                score_ema = 0
            if not cur_bullish:
                score_ema = 20 - score_ema  # Invert for short

            score_regime = min(20, cur_adx * 0.8) if regime == "trending" else 10

            score_band = min(20, (band_dist / (mult * cur_atr)) * 20) if mult * cur_atr > 0 else 0

            total_score = score_volume + score_displacement + score_ema + score_regime + score_band

            if total_score < min_score:
                continue

            direction = "LONG" if flip_bull else "SHORT"
            conf = min(0.95, 0.55 + total_score / 200)
            if regime == "trending":
                conf += 0.05

            picks.append(self._atr_pick(
                symbol, direction, conf, price, cur_atr, 3.0, 2.25,
                reason=f"SuperTrend AI flip {direction}: score={total_score:.0f}/100, "
                       f"regime={regime}, ADX={cur_adx:.0f}, vol={vol_ratio:.1f}x"
            ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ===========================================================================
# 2. VCP Minervini Breakout
# ===========================================================================

class TVVCPMinerviniPT(_TVDiscoveryBase):
    """Volatility Contraction Pattern — Mark Minervini breakout detection.

    Source: kaspareit-trading VCP-Minervini v2 (open source, TV).
    Logic: ATR contraction (40%+) + tighter successive swings + pivot break
    + volume surge + EMA trend filter. Classic stock strategy adapted for crypto.
    """
    name = "tv_vcp_minervini"
    display_name = "TV VCP Minervini Breakout"
    interval = "4h"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse(klines)
            n = len(closes)
            if n < 60:
                continue
            price = closes[-1]
            atr_vals = _atr(highs, lows, closes, 14)
            ema50 = _ema(closes, 50)
            avg_vol = _sma(volumes, 20)

            if any(v is None for v in [atr_vals[-1], ema50[-1], avg_vol[-1]]):
                continue
            cur_atr = atr_vals[-1]

            # 1. ATR contraction: compare current ATR to 30 bars ago
            lookback = 30
            if n < lookback + 14:
                continue
            old_atr = atr_vals[-lookback] if atr_vals[-lookback] is not None else cur_atr
            if old_atr == 0:
                continue
            contraction_ratio = cur_atr / old_atr
            if contraction_ratio > 0.6:
                continue  # Need 40%+ contraction

            # 2. Tighter successive swings (3 windows of 10 bars)
            swing_ranges = []
            for j in range(3):
                start = n - (3 - j) * 10
                end = start + 10
                if start < 0 or end > n:
                    break
                w_high = max(highs[start:end])
                w_low = min(lows[start:end])
                swing_ranges.append(w_high - w_low)
            if len(swing_ranges) < 3:
                continue
            tighter = swing_ranges[0] > swing_ranges[1] > swing_ranges[2]
            if not tighter:
                continue

            # 3. Pivot resistance breakout
            contraction_high = max(highs[n - lookback:n - 1])
            buffer = contraction_high * 0.001
            broke_pivot = closes[-1] > contraction_high + buffer and closes[-2] <= contraction_high + buffer

            if not broke_pivot:
                continue

            # 4. Volume confirmation
            if avg_vol[-1] is None or avg_vol[-1] == 0:
                continue
            vol_ratio = volumes[-1] / avg_vol[-1]
            if vol_ratio < 2.0:
                continue

            # 5. EMA trend filter
            if price < ema50[-1]:
                continue

            # Compute TP/SL
            contraction_low = min(lows[n - lookback:n])
            base_height = contraction_high - contraction_low
            tp_measured = price + base_height
            tp_atr = price + cur_atr * 3.0
            tp = max(tp_measured, tp_atr)
            sl = max(contraction_low, price - cur_atr * 1.5)

            rr = (tp - price) / (price - sl) if price > sl else 0
            conf = min(0.90, 0.60 + 0.05 * min(vol_ratio / 3, 1) + 0.05 * (1 - contraction_ratio))

            picks.append(NormalizedPick(
                symbol=symbol, direction="LONG", entry_price=price,
                tp=round(tp, 6), sl=round(sl, 6),
                strategy=self.name, strategy_name=self.display_name,
                category="crypto", confidence=round(conf, 3),
                reason=f"VCP breakout: contraction {contraction_ratio:.2f}, "
                       f"3 tighter swings, vol {vol_ratio:.1f}x, R:R {rr:.1f}:1"
            ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ===========================================================================
# 3. HMM Regime Detector
# ===========================================================================

class TVHMMRegimePT(_TVDiscoveryBase):
    """3-state regime classifier: Bull / Bear / Range.

    Source: UAlgo HMM Regime Detector (simplified proxy without hmmlearn).
    Logic: Classify regime via returns SMA + volatility + EMA position.
    Trade regime transitions (BEAR→BULL or RANGE→BULL) with RSI + volume + ADX confirmation.
    """
    name = "tv_hmm_regime"
    display_name = "TV HMM Regime Detector"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse(klines)
            n = len(closes)
            if n < 60:
                continue
            price = closes[-1]

            # Features
            returns = [0.0] + [closes[i] / closes[i - 1] - 1 for i in range(1, n)]
            ret_sma = _sma(returns, 10)
            vol_std = _stdev(returns, 20)
            ema50 = _ema(closes, 50)
            rsi_vals = _rsi(closes, 14)
            adx_vals = _adx(highs, lows, closes, 14)
            avg_vol = _sma(volumes, 20)
            avg_std = _sma([v for v in vol_std if v is not None], 50)

            if any(v is None for v in [ret_sma[-1], ret_sma[-2], vol_std[-1], ema50[-1],
                                        rsi_vals[-1], adx_vals[-1], avg_vol[-1]]):
                continue

            # Regime classification
            def classify(idx):
                if ret_sma[idx] is None or vol_std[idx] is None or ema50[idx] is None:
                    return "RANGE"
                avg_v = avg_std[-1] if avg_std and avg_std[-1] is not None else vol_std[idx]
                if ret_sma[idx] > 0 and vol_std[idx] < 1.5 * avg_v and closes[idx] > ema50[idx]:
                    return "BULL"
                elif ret_sma[idx] < 0 and closes[idx] < ema50[idx]:
                    return "BEAR"
                return "RANGE"

            cur_regime = classify(-1)
            prev_regime = classify(-2)

            # Transition detection
            bull_transition = cur_regime == "BULL" and prev_regime in ("BEAR", "RANGE")
            bear_transition = cur_regime == "BEAR" and prev_regime in ("BULL", "RANGE")

            if not bull_transition and not bear_transition:
                continue

            cur_rsi = rsi_vals[-1]
            cur_adx = adx_vals[-1] or 0
            vol_ratio = volumes[-1] / avg_vol[-1] if avg_vol[-1] > 0 else 1

            atr_vals = _atr(highs, lows, closes, 14)
            cur_atr = atr_vals[-1] if atr_vals[-1] is not None else price * 0.02

            if bull_transition:
                if not (40 <= cur_rsi <= 65):
                    continue
                if vol_ratio < 1.5:
                    continue
                # ADX rising
                prev_adx = adx_vals[-2] if adx_vals[-2] is not None else 0
                if cur_adx < prev_adx:
                    continue
                conf = min(0.90, 0.55 + cur_adx / 200 + min(vol_ratio / 10, 0.1))
                picks.append(self._atr_pick(
                    symbol, "LONG", conf, price, cur_atr, 3.0, 2.0,
                    reason=f"HMM regime shift {prev_regime}→BULL: RSI={cur_rsi:.0f}, "
                           f"ADX={cur_adx:.0f}, vol={vol_ratio:.1f}x"
                ))

            elif bear_transition:
                if not (35 <= cur_rsi <= 60):
                    continue
                if vol_ratio < 1.5:
                    continue
                prev_adx = adx_vals[-2] if adx_vals[-2] is not None else 0
                if cur_adx < prev_adx:
                    continue
                conf = min(0.90, 0.55 + cur_adx / 200 + min(vol_ratio / 10, 0.1))
                picks.append(self._atr_pick(
                    symbol, "SHORT", conf, price, cur_atr, 3.0, 2.0,
                    reason=f"HMM regime shift {prev_regime}→BEAR: RSI={cur_rsi:.0f}, "
                           f"ADX={cur_adx:.0f}, vol={vol_ratio:.1f}x"
                ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ===========================================================================
# 4. Liquidity Cluster + Order Flow
# ===========================================================================

class TVLiquidityClusterPT(_TVDiscoveryBase):
    """Volume profile POC + delta divergence + cluster detection.

    Source: LuxAlgo Liquidity Clusters Magnitude + Liquidity Structure & Order Flow.
    Logic: Build volume profile, find POC. Detect delta (buy/sell pressure).
    Long when price reclaims POC with positive delta and volume spike.
    """
    name = "tv_liquidity_cluster"
    display_name = "TV Liquidity Cluster Order Flow"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse(klines)
            n = len(closes)
            if n < 60:
                continue
            price = closes[-1]

            # Volume profile: last 50 bars
            lookback = min(50, n)
            slice_h = highs[n - lookback:n]
            slice_l = lows[n - lookback:n]
            slice_c = closes[n - lookback:n]
            slice_v = volumes[n - lookback:n]

            price_min = min(slice_l)
            price_max = max(slice_h)
            if price_max == price_min:
                continue
            num_bins = 20
            bin_size = (price_max - price_min) / num_bins
            bins = [0.0] * num_bins
            for i in range(lookback):
                idx = int((slice_c[i] - price_min) / bin_size)
                idx = min(idx, num_bins - 1)
                bins[idx] += slice_v[i]

            poc_idx = bins.index(max(bins))
            poc_price = price_min + (poc_idx + 0.5) * bin_size

            # Delta: approximate buy vs sell pressure
            deltas = []
            for i in range(n):
                rng = highs[i] - lows[i]
                if rng > 0:
                    buy_frac = (closes[i] - lows[i]) / rng
                else:
                    buy_frac = 0.5
                deltas.append(volumes[i] * (2 * buy_frac - 1))
            cum_delta_5 = sum(deltas[-5:])

            avg_vol = _sma(volumes, 20)
            atr_vals = _atr(highs, lows, closes, 14)

            if avg_vol[-1] is None or avg_vol[-1] == 0 or atr_vals[-1] is None:
                continue
            cur_atr = atr_vals[-1]
            vol_ratio = volumes[-1] / avg_vol[-1]

            # POC reclaim detection
            poc_dist = abs(price - poc_price) / cur_atr if cur_atr > 0 else 999
            reclaimed_from_below = closes[-1] > poc_price and closes[-2] < poc_price
            lost_from_above = closes[-1] < poc_price and closes[-2] > poc_price

            if reclaimed_from_below and cum_delta_5 > 0 and vol_ratio > 1.8:
                conf = min(0.90, 0.55 + min(vol_ratio / 8, 0.15) + min(cum_delta_5 / (avg_vol[-1] * 5 + 1), 0.15))
                picks.append(self._atr_pick(
                    symbol, "LONG", conf, price, cur_atr, 2.5, 1.5,
                    reason=f"Liquidity POC reclaim: POC={poc_price:.2f}, delta=+{cum_delta_5:.0f}, "
                           f"vol={vol_ratio:.1f}x"
                ))
            elif lost_from_above and cum_delta_5 < 0 and vol_ratio > 1.8:
                conf = min(0.90, 0.55 + min(vol_ratio / 8, 0.15) + min(abs(cum_delta_5) / (avg_vol[-1] * 5 + 1), 0.15))
                picks.append(self._atr_pick(
                    symbol, "SHORT", conf, price, cur_atr, 2.5, 1.5,
                    reason=f"Liquidity POC lost: POC={poc_price:.2f}, delta={cum_delta_5:.0f}, "
                           f"vol={vol_ratio:.1f}x"
                ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ===========================================================================
# 5. Consecutive Candle Streak Mean Reversion
# ===========================================================================

class TVCandleStreakPT(_TVDiscoveryBase):
    """Mean reversion on statistically overextended candle streaks.

    Source: LuxAlgo Consecutive Candle Streak Analysis.
    Logic: Count consecutive up/down closes. Compute z-score vs historical distribution.
    When |z| > 2.0 + RSI confirms exhaustion + volume declining → mean reversion entry.
    """
    name = "tv_candle_streak"
    display_name = "TV Candle Streak Reversion"

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            opens, highs, lows, closes, volumes = self._parse(klines)
            n = len(closes)
            if n < 220:
                continue
            price = closes[-1]

            # Compute streaks
            streaks = [0]
            for i in range(1, n):
                if closes[i] > closes[i - 1]:
                    streaks.append(streaks[-1] + 1 if streaks[-1] > 0 else 1)
                elif closes[i] < closes[i - 1]:
                    streaks.append(streaks[-1] - 1 if streaks[-1] < 0 else -1)
                else:
                    streaks.append(0)

            cur_streak = streaks[-1]
            # Historical streak distribution (last 200 bars)
            hist = [abs(s) for s in streaks[-200:]]
            if len(hist) < 50:
                continue
            mean_s = sum(hist) / len(hist)
            var_s = sum((x - mean_s) ** 2 for x in hist) / len(hist)
            std_s = math.sqrt(var_s) if var_s > 0 else 1
            z_score = (abs(cur_streak) - mean_s) / std_s

            if z_score < 2.0:
                continue

            rsi_vals = _rsi(closes, 14)
            atr_vals = _atr(highs, lows, closes, 14)
            avg_vol = _sma(volumes, 20)

            if any(v is None for v in [rsi_vals[-1], atr_vals[-1], avg_vol[-1]]):
                continue
            cur_rsi = rsi_vals[-1]
            cur_atr = atr_vals[-1]

            # Volume declining (momentum fading)
            vol_declining = volumes[-1] < volumes[-2] * 0.8

            # ATR not expanding (not genuine breakout)
            avg_atr = _sma([v for v in atr_vals if v is not None], 50)
            atr_not_expanding = True
            if avg_atr and avg_atr[-1] is not None:
                atr_not_expanding = cur_atr < avg_atr[-1] * 1.3

            if cur_streak > 0 and cur_rsi > 75 and vol_declining and atr_not_expanding:
                # Overextended bullish streak → SHORT (mean reversion)
                conf = min(0.85, 0.55 + z_score / 20 + (cur_rsi - 75) / 100)
                picks.append(self._atr_pick(
                    symbol, "SHORT", conf, price, cur_atr, 2.0, 1.5,
                    reason=f"Streak reversion SHORT: {cur_streak} up bars, z={z_score:.1f}, "
                           f"RSI={cur_rsi:.0f}, vol declining"
                ))
            elif cur_streak < 0 and cur_rsi < 25 and vol_declining and atr_not_expanding:
                # Overextended bearish streak → LONG (mean reversion)
                conf = min(0.85, 0.55 + z_score / 20 + (25 - cur_rsi) / 100)
                picks.append(self._atr_pick(
                    symbol, "LONG", conf, price, cur_atr, 2.0, 1.5,
                    reason=f"Streak reversion LONG: {abs(cur_streak)} down bars, z={z_score:.1f}, "
                           f"RSI={cur_rsi:.0f}, vol declining"
                ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ===========================================================================
# 6. Central Bank Liquidity Gap
# ===========================================================================

class TVCentralBankLiquidityPT(_TVDiscoveryBase):
    """Hayes Net Liquidity framework via price-based proxy.

    Source: Arthur Hayes (BitMEX founder) — Fed Balance Sheet - RRP - TGA.
    Since real-time FRED data isn't available, uses a 5-component liquidity score:
    price vs 200 SMA (+30), price vs 50 SMA (+20), ROC of 50 SMA (+20),
    volume expansion (+15), RSI 40-70 not overheated (+15).
    Macro-style trades with wide TP/SL.
    """
    name = "tv_central_bank_liq"
    display_name = "TV Central Bank Liquidity Gap"
    interval = "1d"   # Daily for macro signals
    limit = 250

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        # Only trade majors for macro signals
        macro_symbols = ["BTCUSDT", "ETHUSDT"]
        for symbol, klines in data.items():
            if symbol not in macro_symbols:
                continue
            opens, highs, lows, closes, volumes = self._parse(klines)
            n = len(closes)
            if n < 210:
                continue
            price = closes[-1]

            sma200 = _sma(closes, 200)
            sma50 = _sma(closes, 50)
            vol20 = _sma(volumes, 20)
            vol50 = _sma(volumes, 50)
            rsi_vals = _rsi(closes, 14)
            atr_vals = _atr(highs, lows, closes, 14)

            if any(v is None for v in [sma200[-1], sma50[-1], sma50[-11],
                                        vol20[-1], vol50[-1], rsi_vals[-1], atr_vals[-1]]):
                continue

            # 5-component liquidity score
            score = 0
            if price > sma200[-1]:
                score += 30
            if price > sma50[-1]:
                score += 20
            # ROC of 50 SMA over 10 bars
            roc = (sma50[-1] - sma50[-11]) / sma50[-11] if sma50[-11] and sma50[-11] > 0 else 0
            if roc > 0:
                score += 20
            if vol20[-1] and vol50[-1] and vol20[-1] > vol50[-1]:
                score += 15
            cur_rsi = rsi_vals[-1]
            if 40 <= cur_rsi <= 70:
                score += 15

            cur_atr = atr_vals[-1]

            # Check for regime transition (score direction changed in last 5 bars)
            prev_scores = []
            for offset in range(2, 7):
                if n - offset < 210:
                    break
                ps = 0
                if closes[-offset] > sma200[-offset]:
                    ps += 30
                if sma50[-offset] is not None and closes[-offset] > sma50[-offset]:
                    ps += 20
                prev_scores.append(ps)

            if not prev_scores:
                continue
            avg_prev = sum(prev_scores) / len(prev_scores)
            transitioning = abs(score - avg_prev) > 15

            if not transitioning:
                continue

            # Cross above 50 SMA
            cross_up = closes[-1] > sma50[-1] and closes[-2] <= sma50[-2] if sma50[-2] is not None else False
            cross_down = closes[-1] < sma50[-1] and closes[-2] >= sma50[-2] if sma50[-2] is not None else False

            if score >= 70 and cross_up:
                conf = min(0.85, 0.50 + score / 200)
                picks.append(self._atr_pick(
                    symbol, "LONG", conf, price, cur_atr, 4.0, 2.5,
                    reason=f"Liquidity expansion: score={score}/100, 50SMA cross-up, "
                           f"RSI={cur_rsi:.0f}, ROC={roc:.3f}"
                ))
            elif score <= 30 and cross_down:
                conf = min(0.85, 0.50 + (100 - score) / 200)
                picks.append(self._atr_pick(
                    symbol, "SHORT", conf, price, cur_atr, 4.0, 2.5,
                    reason=f"Liquidity contraction: score={score}/100, 50SMA cross-down, "
                           f"RSI={cur_rsi:.0f}, ROC={roc:.3f}"
                ))

        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:2]
