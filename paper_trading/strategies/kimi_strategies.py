"""Kimi Claw + Perplexity Academic Strategies — Paper trading wrappers.

Sources:
- VPIN Mean Reversion: Easley/O'Hara 2012, Renaissance-style statistical arbitrage
- EMA 600-40 Momentum: Jaaskellainen 2022, Lappeenranta University thesis
- LGBM Feature Proxy: G-Research Crypto Competition winners ($85K prize pool)
- Vol-Momentum Blend: Briplotnik systematic crypto research, Sharpe 1.71
- TSMOM 28/5: AUT NZ 2024-2025, time-series momentum, Sharpe 1.51
- Risk-Managed Momentum: Barroso & Santa-Clara 2015 adapted for crypto, Sharpe 1.42
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


class _KimiBase(BaseStrategy):
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
            [float(k[1]) for k in klines],
            [float(k[2]) for k in klines],
            [float(k[3]) for k in klines],
            [float(k[4]) for k in klines],
            [float(k[5]) for k in klines],
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


class KimiVPINReversionPT(_KimiBase):
    name = "kimi_vpin_reversion"
    display_name = "Kimi VPIN Reversion"
    tp_pct = 0.06
    sl_pct = 0.03

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, volumes = self._parse(klines)
            if len(closes) < 30:
                continue
            price = closes[-1]
            # VPIN approximation: |buy_vol - sell_vol| / total_vol
            vpins = []
            for i in range(len(closes)):
                if highs[i] - lows[i] > 0:
                    buy_frac = (closes[i] - lows[i]) / (highs[i] - lows[i])
                else:
                    buy_frac = 0.5
                buy_vol = volumes[i] * buy_frac
                sell_vol = volumes[i] * (1 - buy_frac)
                vpins.append(abs(buy_vol - sell_vol) / max(volumes[i], 1))
            # Rolling 20-bar VPIN
            vpin_20 = _sma(vpins, 20)
            # Z-Score: (close - EMA20) / std
            ema20 = _ema(closes, 20)
            if ema20[-1] is None or vpin_20[-1] is None:
                continue
            recent = closes[-20:]
            std = (sum((c - sum(recent) / len(recent)) ** 2 for c in recent) / len(recent)) ** 0.5
            if std == 0:
                continue
            z_score = (price - ema20[-1]) / std
            vpin = vpin_20[-1]
            # Trade logic
            if z_score < -2.0 and vpin < 0.5:
                picks.append(self._pick(symbol, "LONG", 0.70, price,
                    reason=f"VPIN reversion: Z={z_score:.2f}, VPIN={vpin:.3f} (clean flow, oversold)"))
            elif z_score > 2.0 and vpin < 0.5:
                picks.append(self._pick(symbol, "SHORT", 0.70, price,
                    reason=f"VPIN reversion: Z={z_score:.2f}, VPIN={vpin:.3f} (clean flow, overbought)"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class KimiEMA600MomentumPT(_KimiBase):
    name = "kimi_ema600_40"
    display_name = "Kimi EMA600-40 Momentum"
    tp_pct = 0.15
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = self._parse(klines)
            if len(closes) < 250:
                continue
            # On 4H: EMA40 ≈ 6.5 days, EMA150 ≈ 25 days (600h/4h=150)
            fast = _ema(closes, 40)
            slow = _ema(closes, 150)
            if fast[-1] is None or slow[-1] is None or fast[-2] is None or slow[-2] is None:
                continue
            price = closes[-1]
            cross_up = fast[-2] <= slow[-2] and fast[-1] > slow[-1]
            cross_down = fast[-2] >= slow[-2] and fast[-1] < slow[-1]
            trending_up = fast[-1] > slow[-1]
            trending_down = fast[-1] < slow[-1]
            if cross_up or (trending_up and fast[-1] > fast[-2]):
                conf = 0.70 if cross_up else 0.60
                picks.append(self._pick(symbol, "LONG", conf, price,
                    reason=f"EMA600-40: fast={fast[-1]:.2f} > slow={slow[-1]:.2f}{'(CROSS)' if cross_up else ''}"))
            elif cross_down or (trending_down and fast[-1] < fast[-2]):
                conf = 0.70 if cross_down else 0.60
                picks.append(self._pick(symbol, "SHORT", conf, price,
                    reason=f"EMA600-40: fast={fast[-1]:.2f} < slow={slow[-1]:.2f}{'(CROSS)' if cross_down else ''}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class KimiLGBMFeatureProxyPT(_KimiBase):
    name = "kimi_lgbm_features"
    display_name = "Kimi LGBM Feature Proxy"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, volumes = self._parse(klines)
            if len(closes) < 105:
                continue
            price = closes[-1]
            # Feature 1: Lagged return rank (normalized momentum)
            ret_1h = (closes[-1] / closes[-2] - 1) if closes[-2] else 0
            ret_4h = (closes[-1] / closes[-4] - 1) if len(closes) > 4 and closes[-4] else 0
            ret_24h = (closes[-1] / closes[-6] - 1) if len(closes) > 6 and closes[-6] else 0
            # Normalize returns to 0-1 range using percentile over last 100 bars
            returns_100 = [(closes[i] / closes[i - 1] - 1) for i in range(max(1, len(closes) - 100), len(closes))]
            if not returns_100:
                continue
            sorted_ret = sorted(returns_100)
            ret_pctile = sum(1 for r in sorted_ret if r <= ret_24h) / len(sorted_ret)

            # Feature 2: Volume ratio
            vol_sma = sum(volumes[-21:-1]) / 20 if len(volumes) > 21 else sum(volumes) / len(volumes)
            vol_ratio = min(volumes[-1] / max(vol_sma, 1), 3.0) / 3.0

            # Feature 3: Volatility rank (ATR percentile)
            atr_vals = _atr(highs, lows, closes, 14)
            if atr_vals[-1] is None:
                continue
            recent_atr = [a for a in atr_vals[-100:] if a is not None]
            atr_pctile = sum(1 for a in recent_atr if a <= atr_vals[-1]) / max(len(recent_atr), 1)

            # Feature 4: RSI normalized
            rsi_vals = _rsi(closes, 14)
            rsi_norm = (rsi_vals[-1] / 100) if rsi_vals[-1] is not None else 0.5

            # Feature 5: Trend alignment (correlation to own 50-EMA)
            ema50 = _ema(closes, 50)
            if ema50[-1] is not None and ema50[-1] > 0:
                trend_score = min(max((price / ema50[-1] - 0.95) / 0.10, 0), 1)
            else:
                trend_score = 0.5

            # Composite score
            score = (0.30 * ret_pctile + 0.20 * vol_ratio + 0.15 * (1 - atr_pctile)
                     + 0.20 * rsi_norm + 0.15 * trend_score)

            if score > 0.65:
                picks.append(self._pick(symbol, "LONG", min(0.55 + score * 0.4, 0.90), price,
                    reason=f"LGBM features: score={score:.3f} (ret={ret_pctile:.2f} vol={vol_ratio:.2f} rsi={rsi_norm:.2f})"))
            elif score < 0.35:
                picks.append(self._pick(symbol, "SHORT", min(0.55 + (1 - score) * 0.4, 0.90), price,
                    reason=f"LGBM features: score={score:.3f} (ret={ret_pctile:.2f} vol={vol_ratio:.2f} rsi={rsi_norm:.2f})"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class KimiVolMomentumBlendPT(_KimiBase):
    name = "kimi_vol_momentum_blend"
    display_name = "Kimi Vol-Momentum Blend"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, volumes = self._parse(klines)
            if len(closes) < 80:
                continue
            price = closes[-1]
            # Momentum Z-score of 14-bar returns
            returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
            if len(returns) < 60:
                continue
            recent_14 = returns[-14:]
            ret_mean = sum(recent_14) / len(recent_14)
            ret_std = (sum((r - ret_mean) ** 2 for r in recent_14) / len(recent_14)) ** 0.5
            if ret_std == 0:
                continue
            cumulative_14 = sum(recent_14)
            rolling_std = (sum((r - sum(returns[-60:]) / 60) ** 2 for r in returns[-60:]) / 60) ** 0.5
            mom_z = cumulative_14 / max(rolling_std, 0.001)

            # Volatility filter: realized vol < 2x its 60-bar MA
            realized_vol = ret_std * math.sqrt(252 * 6)  # annualize from 4H bars
            vol_60 = []
            for i in range(max(14, len(returns) - 60), len(returns)):
                window = returns[max(0, i - 14):i]
                if window:
                    vol_60.append((sum((r - sum(window) / len(window)) ** 2 for r in window) / len(window)) ** 0.5 * math.sqrt(252 * 6))
            avg_vol = sum(vol_60) / max(len(vol_60), 1) if vol_60 else realized_vol
            vol_ok = realized_vol < 2 * avg_vol

            if not vol_ok:
                continue  # Skip extreme volatility regime

            if mom_z > 1.0:
                picks.append(self._pick(symbol, "LONG", min(0.55 + mom_z * 0.1, 0.85), price,
                    reason=f"Vol-Mom: Z={mom_z:.2f}, vol={realized_vol:.1%} (filter OK)"))
            elif mom_z < -1.0:
                picks.append(self._pick(symbol, "SHORT", min(0.55 + abs(mom_z) * 0.1, 0.85), price,
                    reason=f"Vol-Mom: Z={mom_z:.2f}, vol={realized_vol:.1%} (filter OK)"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class AcademicTSMOMPT(_KimiBase):
    """Time-Series Momentum (28-day lookback, 5-day hold).
    Source: AUT NZ 2024-2025, Sharpe 1.51, outperforms buy-and-hold across 31 coins.
    """
    name = "academic_tsmom_28_5"
    display_name = "Academic TSMOM 28/5"
    tp_pct = 0.15
    sl_pct = 0.06

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = self._parse(klines)
            if len(closes) < 200:
                continue
            price = closes[-1]
            # 28-day return on 4H bars: 28*6=168 bars
            lookback = 168
            if len(closes) < lookback + 50:
                continue
            ret_28d = (closes[-1] / closes[-lookback] - 1) if closes[-lookback] > 0 else 0
            # Build distribution of 28-day returns (rolling over last ~200 bars)
            hist_returns = []
            for i in range(lookback, len(closes)):
                r = (closes[i] / closes[i - lookback] - 1)
                hist_returns.append(r)
            if len(hist_returns) < 10:
                continue
            sorted_hist = sorted(hist_returns)
            percentile = sum(1 for r in sorted_hist if r <= ret_28d) / len(sorted_hist)
            # ATR for TP/SL
            atr_vals = _atr(highs, lows, closes, 14)
            atr_v = atr_vals[-1] if atr_vals[-1] is not None else price * 0.03

            if percentile >= 0.66:  # Top third → LONG
                sl_price = round(price - 3 * atr_v, 6)
                tp_price = round(price + 6 * atr_v, 6)
                conf = min(0.55 + (percentile - 0.66) * 3, 0.85)
                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG", entry_price=price,
                    tp=tp_price, sl=sl_price, strategy=self.name,
                    strategy_name=self.display_name, category="crypto",
                    confidence=round(conf, 3),
                    reason=f"TSMOM 28d: ret={ret_28d:+.2%}, pctile={percentile:.0%}, ATR-based SL/TP",
                ))
            elif percentile <= 0.33:  # Bottom third → SHORT (optional)
                sl_price = round(price + 3 * atr_v, 6)
                tp_price = round(price - 6 * atr_v, 6)
                conf = min(0.55 + (0.33 - percentile) * 3, 0.85)
                picks.append(NormalizedPick(
                    symbol=symbol, direction="SHORT", entry_price=price,
                    tp=tp_price, sl=sl_price, strategy=self.name,
                    strategy_name=self.display_name, category="crypto",
                    confidence=round(conf, 3),
                    reason=f"TSMOM 28d: ret={ret_28d:+.2%}, pctile={percentile:.0%}, ATR-based SL/TP",
                ))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


class RiskManagedMomentumPT(_KimiBase):
    """Risk-Managed Momentum (Barroso & Santa-Clara for crypto).
    Source: ScienceDirect 2025, 3.47% avg weekly return, Sharpe 1.42.
    """
    name = "risk_managed_momentum"
    display_name = "Risk-Managed Momentum"
    tp_pct = 0.12
    sl_pct = 0.05

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            _, highs, lows, closes, _ = self._parse(klines)
            if len(closes) < 100:
                continue
            price = closes[-1]
            # 14-day momentum (14*6=84 bars on 4H)
            lookback = 84
            if len(closes) < lookback + 10:
                continue
            ret_14d = (closes[-1] / closes[-lookback] - 1) if closes[-lookback] > 0 else 0
            # Realized vol (20-day, 4H)
            returns = [(closes[i] / closes[i - 1] - 1) for i in range(max(1, len(closes) - 120), len(closes))]
            if len(returns) < 20:
                continue
            vol_20d = (sum(r ** 2 for r in returns[-120:]) / len(returns[-120:])) ** 0.5
            if vol_20d == 0:
                continue
            # Volatility-scaled signal
            target_vol = 0.30  # 30% annualized target
            vol_annualized = vol_20d * math.sqrt(252 * 6)
            vol_scalar = min(target_vol / max(vol_annualized, 0.01), 3.0)
            # Momentum signal strength
            signal_strength = ret_14d * vol_scalar
            if signal_strength > 0.05:  # Positive risk-adjusted momentum
                conf = min(0.55 + signal_strength * 2, 0.85)
                picks.append(self._pick(symbol, "LONG", conf, price,
                    reason=f"Risk-Mgd Mom: ret14d={ret_14d:+.2%}, vol_scalar={vol_scalar:.2f}, signal={signal_strength:.3f}"))
            elif signal_strength < -0.05:
                conf = min(0.55 + abs(signal_strength) * 2, 0.85)
                picks.append(self._pick(symbol, "SHORT", conf, price,
                    reason=f"Risk-Mgd Mom: ret14d={ret_14d:+.2%}, vol_scalar={vol_scalar:.2f}, signal={signal_strength:.3f}"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]


# ── VPIN + LightGBM Ensemble (per-symbol configs) ──────────────────

class KimiVPINLGBMEnsemblePT(_KimiBase):
    """Full VPIN + LightGBM ensemble with per-symbol Z-score/ATR configs."""

    name = "kimi_vpin_lgbm_ensemble"
    display_name = "Kimi VPIN+LGBM Ensemble"
    source = "Kimi Claw workspace — Easley/O'Hara 2012 + G-Research winners"
    category = "stat_arb"

    # Per-symbol: (z_threshold, atr_sl_mult, atr_tp_mult, size_scalar)
    _SYM_CFG = {
        "BTCUSDT": (2.0, 2.0, 3.0, 1.0),
        "ETHUSDT": (1.8, 2.0, 3.0, 1.2),
        "SOLUSDT": (2.2, 2.5, 4.0, 0.8),
        "LTCUSDT": (2.0, 2.0, 3.0, 1.0),
        "DOGEUSDT": (2.5, 3.0, 5.0, 0.5),
        "XRPUSDT": (2.0, 2.0, 3.0, 1.0),
    }

    @staticmethod
    def _vpin(closes, volumes, window=50):
        """VPIN via tick-rule classification."""
        n = len(closes)
        if n < window + 1:
            return None
        buy = []
        sell = []
        for i in range(1, n):
            diff = closes[i] - closes[i - 1]
            if diff > 0:
                buy.append(volumes[i])
                sell.append(0)
            elif diff < 0:
                buy.append(0)
                sell.append(volumes[i])
            else:
                buy.append(volumes[i] * 0.5)
                sell.append(volumes[i] * 0.5)
        b_sum = sum(buy[-window:])
        s_sum = sum(sell[-window:])
        total = b_sum + s_sum
        if total == 0:
            return 0.5
        return abs(b_sum - s_sum) / total

    @staticmethod
    def _z_score(closes, ema_period=20, lookback=50):
        e = _ema(closes, ema_period)
        if e[-1] is None or len(closes) < lookback:
            return None
        devs = []
        for i in range(max(0, len(closes) - lookback), len(closes)):
            if e[i] is not None:
                devs.append(closes[i] - e[i])
        if len(devs) < 10:
            return None
        dev_now = closes[-1] - e[-1]
        std = (sum(d ** 2 for d in devs) / len(devs)) ** 0.5
        if std == 0:
            return 0
        return dev_now / std

    @staticmethod
    def _rsi_val(closes, period=14):
        if len(closes) < period + 1:
            return 50
        gains, losses = 0, 0
        for i in range(len(closes) - period, len(closes)):
            d = closes[i] - closes[i - 1]
            if d > 0:
                gains += d
            else:
                losses -= d
        gains /= period
        losses /= period
        if losses == 0:
            return 100
        rs = gains / losses
        return 100 - 100 / (1 + rs)

    @staticmethod
    def _composite(closes, volumes):
        """5-feature composite (LightGBM proxy)."""
        n = len(closes)
        if n < 50:
            return 0

        rsi = KimiVPINLGBMEnsemblePT._rsi_val(closes)
        rsi_sig = abs(50 - rsi) / 50.0

        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        if ema12[-1] is not None and ema26[-1] is not None:
            macd = ema12[-1] - ema26[-1]
            macd_sig = min(abs(macd) / (closes[-1] * 0.02 + 1e-10), 1.0)
        else:
            macd_sig = 0

        sma20 = _sma(closes, 20)
        if sma20[-1] is not None:
            std20 = (sum((closes[i] - sma20[i]) ** 2
                         for i in range(max(0, n - 20), n) if sma20[i] is not None) / 20) ** 0.5
            if std20 > 0:
                bb_pos = (closes[-1] - (sma20[-1] - 2 * std20)) / (4 * std20 + 1e-10)
                bb_sig = abs(bb_pos - 0.5) * 2
            else:
                bb_sig = 0
        else:
            bb_sig = 0

        avg_vol = sum(volumes[-24:]) / min(24, len(volumes))
        vol_sig = min(max(volumes[-1] / (avg_vol + 1e-10) - 1, 0) / 3, 1.0)

        if n > 24 and closes[-25] > 0:
            mom = abs(closes[-1] / closes[-25] - 1)
            mom_sig = min(mom / 0.10, 1.0)
        else:
            mom_sig = 0

        return 0.25 * rsi_sig + 0.20 * macd_sig + 0.20 * bb_sig + 0.20 * vol_sig + 0.15 * mom_sig

    def generate_picks(self, _data=None) -> List[NormalizedPick]:
        picks = []
        for symbol in self._SYM_CFG:
            data = self.fetch_klines(symbol, interval="4h", limit=300)
            if not data or len(data) < 100:
                continue
            closes = [float(k[4]) for k in data]
            highs = [float(k[2]) for k in data]
            lows = [float(k[3]) for k in data]
            volumes = [float(k[5]) for k in data]
            price = closes[-1]

            cfg = self._SYM_CFG[symbol]
            z_thresh, atr_sl_m, atr_tp_m, size_scalar = cfg

            v = self._vpin(closes, volumes, 50)
            zs = self._z_score(closes, 20, 50)
            atr_vals = _atr(highs, lows, closes, 14)
            atr_now = atr_vals[-1] if atr_vals[-1] is not None else 0
            comp = self._composite(closes, volumes)

            if v is None or zs is None or atr_now == 0:
                continue
            if v > 0.6:
                continue
            if comp < 0.35:
                continue

            if zs < -z_thresh and v < 0.5:
                conf = min(abs(zs) / 4.0, 1.0) * (0.6 - v) / 0.6 * min(comp * 1.5, 1.0)
                conf = max(0.50, min(conf, 0.90))
                tp_pct = (atr_now * atr_tp_m / price) * 100
                sl_pct = (atr_now * atr_sl_m / price) * 100
                picks.append(self._pick(symbol, "LONG", round(conf, 2), price,
                    tp_pct=round(tp_pct, 1), sl_pct=round(sl_pct, 1),
                    reason=f"VPIN={v:.2f} Z={zs:.2f}<-{z_thresh} comp={comp:.2f} sz={size_scalar}x"))
            elif zs > z_thresh and v < 0.5:
                conf = min(zs / 4.0, 1.0) * (0.6 - v) / 0.6 * min(comp * 1.5, 1.0)
                conf = max(0.50, min(conf, 0.90))
                tp_pct = (atr_now * atr_tp_m / price) * 100
                sl_pct = (atr_now * atr_sl_m / price) * 100
                picks.append(self._pick(symbol, "SHORT", round(conf, 2), price,
                    tp_pct=round(tp_pct, 1), sl_pct=round(sl_pct, 1),
                    reason=f"VPIN={v:.2f} Z={zs:.2f}>+{z_thresh} comp={comp:.2f} sz={size_scalar}x"))
        return sorted(picks, key=lambda p: p.confidence, reverse=True)[:3]
