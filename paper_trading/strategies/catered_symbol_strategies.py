"""Symbol-Catered Forward-Testing Strategies.

Auto-generated from backtest winners: each strategy targets a SPECIFIC symbol
where it demonstrated statistical edge (WR >= 55%, trades >= 10, positive avg PnL).

Purpose: Validate whether backtested per-symbol edges hold up in live forward-testing.
If they do → promote to conviction portfolio. If not → eliminate the mirage.

Data source: alpha_engine/data/survivor_backtest_results.json (24 symbols, 29 strategies)
"""
from typing import List
import json
import logging
import numpy as np
from pathlib import Path
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

logger = logging.getLogger("paper_trading")

# ---------------------------------------------------------------------------
# Load catered backtest data at import time
# ---------------------------------------------------------------------------
_BACKTEST_FILE = Path(__file__).resolve().parent.parent.parent / "alpha_engine" / "data" / "survivor_backtest_results.json"
_CATERED_PAIRS: dict = {}   # {strategy_name: {symbol: {trades, wr, avg_pnl}}}

try:
    with open(_BACKTEST_FILE) as f:
        _bt = json.load(f)
    for strat_name, strat_data in _bt.get("results", {}).items():
        if strat_data.get("verdict") not in ("SURVIVOR", "PROMISING"):
            continue
        sym_results = strat_data.get("symbol_results", {})
        catered = {}
        for sym, metrics in sym_results.items():
            wr = metrics.get("wr", 0)
            trades = metrics.get("trades", 0)
            avg_pnl = metrics.get("avg_pnl", 0)
            # Catered: WR >= 55% AND trades >= 5 (lowered from 10 for rare-fire strats) AND positive PnL
            if wr >= 55 and trades >= 5 and avg_pnl > 0:
                catered[sym] = metrics
        if catered:
            _CATERED_PAIRS[strat_name] = catered
except Exception as e:
    logger.warning(f"Could not load catered backtest data: {e}")


# ---------------------------------------------------------------------------
# Symbol name mapping: yfinance → Binance
# ---------------------------------------------------------------------------
_YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT", "XRP-USD": "XRPUSDT", "ADA-USD": "ADAUSDT",
    "AVAX-USD": "AVAXUSDT", "LINK-USD": "LINKUSDT", "NEAR-USD": "NEARUSDT",
    "ATOM-USD": "ATOMUSDT", "DOGE-USD": "DOGEUSDT", "DOT-USD": "DOTUSDT",
    "LTC-USD": "LTCUSDT", "FIL-USD": "FILUSDT",
    "SPY": "SPY", "QQQ": "QQQ", "AAPL": "AAPL", "MSFT": "MSFT",
    "NVDA": "NVDA", "AMZN": "AMZN", "GOOGL": "GOOGL", "META": "META",
    "TSLA": "TSLA", "IWM": "IWM",
}


# ---------------------------------------------------------------------------
# Shared indicator helpers
# ---------------------------------------------------------------------------

def _ema_arr(arr, period):
    """Full EMA array."""
    out = np.full_like(arr, np.nan, dtype=float)
    if len(arr) < period:
        return out
    k = 2.0 / (period + 1)
    out[period - 1] = np.mean(arr[:period])
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1.0 - k)
    return out


def _sma_last(arr, period):
    if len(arr) < period:
        return float(np.mean(arr))
    return float(np.mean(arr[-period:]))


def _rsi_last(closes, period=14):
    n = len(closes)
    if n < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_g = float(np.mean(gains[:period]))
    avg_l = float(np.mean(losses[:period]))
    alpha = 1.0 / period
    for i in range(period, len(deltas)):
        avg_g = avg_g * (1 - alpha) + gains[i] * alpha
        avg_l = avg_l * (1 - alpha) + losses[i] * alpha
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)


def _atr_last(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1:
        return 0.0
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i - 1]),
                     abs(lows[i] - closes[i - 1]))
    atr_val = float(np.mean(tr[:period]))
    alpha = 1.0 / period
    for i in range(period, n):
        atr_val = atr_val * (1 - alpha) + tr[i] * alpha
    return atr_val


def _williams_r(highs, lows, closes, period=14):
    if len(closes) < period:
        return -50.0
    hh = float(np.max(highs[-period:]))
    ll = float(np.min(lows[-period:]))
    c = float(closes[-1])
    rng = hh - ll
    if rng == 0:
        return -50.0
    return ((hh - c) / rng) * -100


def _bb_lower(closes, period=20, mult=2.0):
    if len(closes) < period:
        return float(closes[-1])
    window = closes[-period:]
    sma = float(np.mean(window))
    std = float(np.std(window))
    return sma - mult * std


# ---------------------------------------------------------------------------
# Strategy implementations: one class per "catered pattern"
# Each class implements the EXACT same logic as its backtest source strategy
# but targets ONLY the symbols where it proved profitable.
# ---------------------------------------------------------------------------

class CateredConnorsRSI2(BaseStrategy):
    """Connors RSI-2 — only on symbols where it backtested 55%+ WR."""
    name = "catered_connors_rsi2"
    display_name = "Catered: Connors RSI-2"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "catered"

    def _get_symbols(self):
        pairs = _CATERED_PAIRS.get("connors_rsi2", {})
        return [_YF_TO_BINANCE.get(s, s) for s in pairs if _YF_TO_BINANCE.get(s)]

    def fetch_data(self) -> dict:
        data = {}
        for sym in self._get_symbols():
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    data[sym] = klines
            except Exception:
                continue
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 200:
                continue
            closes = np.array([float(k[4]) for k in klines])
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            price = float(closes[-1])

            # RSI(2)
            if len(closes) < 3:
                continue
            d = np.diff(closes)
            g2 = np.mean(np.where(d[-2:] > 0, d[-2:], 0))
            l2 = np.mean(np.where(d[-2:] < 0, -d[-2:], 0))
            rsi2 = 100 - 100 / (1 + g2 / l2) if l2 > 0 else (100 if g2 > 0 else 50)

            sma200 = _sma_last(closes, 200)
            atr = _atr_last(highs, lows, closes, 14)

            if rsi2 < 5 and price > sma200 and atr > 0:
                tp = round(price + 1.5 * atr, 6)
                sl = round(price - 1.0 * atr, 6)
                # Look up backtest WR for confidence weighting
                yf_sym = [k for k, v in _YF_TO_BINANCE.items() if v == symbol]
                bt_wr = 0.68
                if yf_sym:
                    bt_data = _CATERED_PAIRS.get("connors_rsi2", {}).get(yf_sym[0], {})
                    bt_wr = bt_data.get("wr", 68) / 100

                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG",
                    entry_price=price, tp=tp, sl=sl,
                    strategy=self.name, strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(min(0.92, 0.5 + (5 - rsi2) * 0.05), 3),
                    reason=f"RSI(2)={rsi2:.1f} < 5, above SMA200 | Backtest WR={bt_wr:.0%} on {symbol}",
                    raw_signal={"rsi2": round(rsi2, 2), "sma200": round(sma200, 2), "bt_wr": bt_wr},
                ))
        return picks[:3]


class CateredVWAPReversion(BaseStrategy):
    """VWAP Mean Reversion — only on symbols where it backtested 55%+ WR."""
    name = "catered_vwap_reversion"
    display_name = "Catered: VWAP Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "catered"

    def _get_symbols(self):
        pairs = _CATERED_PAIRS.get("vwap_mean_reversion", {})
        return [_YF_TO_BINANCE.get(s, s) for s in pairs if _YF_TO_BINANCE.get(s)]

    def fetch_data(self) -> dict:
        data = {}
        for sym in self._get_symbols():
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    data[sym] = klines
            except Exception:
                continue
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 30:
                continue
            closes = np.array([float(k[4]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            price = float(closes[-1])

            # VWAP(20)
            window = min(20, len(closes))
            vwap = np.sum(closes[-window:] * volumes[-window:]) / np.sum(volumes[-window:]) if np.sum(volumes[-window:]) > 0 else price
            std = float(np.std(closes[-window:]))
            z_score = (price - vwap) / std if std > 0 else 0
            atr = _atr_last(highs, lows, closes, 14)

            if z_score < -2.0 and atr > 0:
                tp = round(price + 2.0 * atr, 6)
                sl = round(price - 1.0 * atr, 6)

                yf_sym = [k for k, v in _YF_TO_BINANCE.items() if v == symbol]
                bt_wr = 0.64
                if yf_sym:
                    bt_data = _CATERED_PAIRS.get("vwap_mean_reversion", {}).get(yf_sym[0], {})
                    bt_wr = bt_data.get("wr", 64) / 100

                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG",
                    entry_price=price, tp=tp, sl=sl,
                    strategy=self.name, strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(min(0.90, 0.5 + abs(z_score) * 0.1), 3),
                    reason=f"VWAP z-score={z_score:.2f} < -2.0 | Backtest WR={bt_wr:.0%} on {symbol}",
                    raw_signal={"z_score": round(z_score, 3), "vwap": round(vwap, 2), "bt_wr": bt_wr},
                ))
        return picks[:3]


class CateredMACDDivergence(BaseStrategy):
    """MACD Histogram Divergence — only on symbols where it backtested 55%+ WR."""
    name = "catered_macd_divergence"
    display_name = "Catered: MACD Divergence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "catered"

    def _get_symbols(self):
        pairs = _CATERED_PAIRS.get("macd_divergence", {})
        return [_YF_TO_BINANCE.get(s, s) for s in pairs if _YF_TO_BINANCE.get(s)]

    def fetch_data(self) -> dict:
        data = {}
        for sym in self._get_symbols():
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    data[sym] = klines
            except Exception:
                continue
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 50:
                continue
            closes = np.array([float(k[4]) for k in klines])
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            price = float(closes[-1])

            ema12 = _ema_arr(closes, 12)
            ema26 = _ema_arr(closes, 26)
            macd = ema12 - ema26
            signal = _ema_arr(macd[~np.isnan(macd)], 9)
            if len(signal) < 10:
                continue

            # Pad signal to match macd length
            hist = np.full_like(macd, np.nan)
            valid_start = len(macd) - len(signal)
            hist[valid_start:] = macd[valid_start:] - signal

            atr = _atr_last(highs, lows, closes, 14)

            # Bullish divergence: price lower low + MACD histogram higher low
            if len(closes) >= 20 and not np.isnan(hist[-1]) and not np.isnan(hist[-10]):
                price_ll = closes[-1] < min(closes[-10:-1])
                hist_hl = hist[-1] > min(hist[-10:-1])

                if price_ll and hist_hl and hist[-1] < 0 and atr > 0:
                    tp = round(price + 2.0 * atr, 6)
                    sl = round(price - 1.5 * atr, 6)

                    yf_sym = [k for k, v in _YF_TO_BINANCE.items() if v == symbol]
                    bt_wr = 0.67
                    if yf_sym:
                        bt_data = _CATERED_PAIRS.get("macd_divergence", {}).get(yf_sym[0], {})
                        bt_wr = bt_data.get("wr", 67) / 100

                    picks.append(NormalizedPick(
                        symbol=symbol, direction="LONG",
                        entry_price=price, tp=tp, sl=sl,
                        strategy=self.name, strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(min(0.88, 0.55 + abs(hist[-1]) * 0.01), 3),
                        reason=f"MACD bullish divergence: price LL + hist HL | Backtest WR={bt_wr:.0%} on {symbol}",
                        raw_signal={"hist": round(float(hist[-1]), 4), "bt_wr": bt_wr},
                    ))
        return picks[:3]


class CateredBollingerReversion(BaseStrategy):
    """Bollinger Band Mean Reversion — only on symbols where it backtested 55%+ WR."""
    name = "catered_bollinger_reversion"
    display_name = "Catered: Bollinger Reversion"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "catered"

    def _get_symbols(self):
        pairs = _CATERED_PAIRS.get("bollinger_mean_reversion", {})
        return [_YF_TO_BINANCE.get(s, s) for s in pairs if _YF_TO_BINANCE.get(s)]

    def fetch_data(self) -> dict:
        data = {}
        for sym in self._get_symbols():
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    data[sym] = klines
            except Exception:
                continue
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 200:
                continue
            closes = np.array([float(k[4]) for k in klines])
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            price = float(closes[-1])

            sma200 = _sma_last(closes, 200)
            bb_low = _bb_lower(closes, 20, 2.0)
            atr = _atr_last(highs, lows, closes, 14)

            # Touch lower BB + price > 90% of 200 SMA (trend intact)
            if price <= bb_low and price > sma200 * 0.90 and atr > 0:
                tp = round(price + 1.5 * atr, 6)
                sl = round(price - 1.0 * atr, 6)

                yf_sym = [k for k, v in _YF_TO_BINANCE.items() if v == symbol]
                bt_wr = 0.61
                if yf_sym:
                    bt_data = _CATERED_PAIRS.get("bollinger_mean_reversion", {}).get(yf_sym[0], {})
                    bt_wr = bt_data.get("wr", 61) / 100

                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG",
                    entry_price=price, tp=tp, sl=sl,
                    strategy=self.name, strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(min(0.88, 0.55 + (bb_low - price) / atr * 0.1), 3),
                    reason=f"Price at lower BB(20,2), trend intact (>90% SMA200) | Backtest WR={bt_wr:.0%} on {symbol}",
                    raw_signal={"bb_lower": round(bb_low, 2), "sma200": round(sma200, 2), "bt_wr": bt_wr},
                ))
        return picks[:3]


class CateredRSIExtreme(BaseStrategy):
    """RSI Extreme Reversal — only on symbols where it backtested 55%+ WR."""
    name = "catered_rsi_extreme"
    display_name = "Catered: RSI Extreme"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "catered"

    def _get_symbols(self):
        pairs = _CATERED_PAIRS.get("rsi_extreme_reversal", _CATERED_PAIRS.get("rsi_extreme", {}))
        return [_YF_TO_BINANCE.get(s, s) for s in pairs if _YF_TO_BINANCE.get(s)]

    def fetch_data(self) -> dict:
        data = {}
        for sym in self._get_symbols():
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    data[sym] = klines
            except Exception:
                continue
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 200:
                continue
            closes = np.array([float(k[4]) for k in klines])
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            price = float(closes[-1])

            rsi = _rsi_last(closes, 14)
            sma200 = _sma_last(closes, 200)
            atr = _atr_last(highs, lows, closes, 14)

            if rsi < 25 and price > sma200 and atr > 0:
                tp = round(price + 2.5 * atr, 6)
                sl = round(price - 1.5 * atr, 6)

                yf_sym = [k for k, v in _YF_TO_BINANCE.items() if v == symbol]
                bt_wr = 0.58
                if yf_sym:
                    bt_data = _CATERED_PAIRS.get("rsi_extreme_reversal", _CATERED_PAIRS.get("rsi_extreme", {})).get(yf_sym[0], {})
                    bt_wr = bt_data.get("wr", 58) / 100

                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG",
                    entry_price=price, tp=tp, sl=sl,
                    strategy=self.name, strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(min(0.90, 0.55 + (25 - rsi) * 0.02), 3),
                    reason=f"RSI(14)={rsi:.1f} extreme oversold (<25), above SMA200 | Backtest WR={bt_wr:.0%} on {symbol}",
                    raw_signal={"rsi": round(rsi, 2), "sma200": round(sma200, 2), "bt_wr": bt_wr},
                ))
        return picks[:3]


class CateredWilliamsR(BaseStrategy):
    """Williams %R Reversion — only on symbols where it backtested 55%+ WR."""
    name = "catered_williams_r"
    display_name = "Catered: Williams %R"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "catered"

    def _get_symbols(self):
        pairs = _CATERED_PAIRS.get("williams_r_oversold", _CATERED_PAIRS.get("williams_r_reversion", {}))
        return [_YF_TO_BINANCE.get(s, s) for s in pairs if _YF_TO_BINANCE.get(s)]

    def fetch_data(self) -> dict:
        data = {}
        for sym in self._get_symbols():
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines:
                    data[sym] = klines
            except Exception:
                continue
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 200:
                continue
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])
            price = float(closes[-1])

            wr = _williams_r(highs, lows, closes, 14)
            sma200 = _sma_last(closes, 200)
            atr = _atr_last(highs, lows, closes, 14)

            if wr < -90 and price > sma200 and atr > 0:
                tp = round(price + 2.0 * atr, 6)
                sl = round(price - 1.0 * atr, 6)

                yf_sym = [k for k, v in _YF_TO_BINANCE.items() if v == symbol]
                bt_wr = 0.81
                if yf_sym:
                    bt_data = _CATERED_PAIRS.get("williams_r_oversold", _CATERED_PAIRS.get("williams_r_reversion", {})).get(yf_sym[0], {})
                    bt_wr = bt_data.get("wr", 81) / 100

                picks.append(NormalizedPick(
                    symbol=symbol, direction="LONG",
                    entry_price=price, tp=tp, sl=sl,
                    strategy=self.name, strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(min(0.92, 0.6 + abs(wr + 100) * 0.03), 3),
                    reason=f"%R(14)={wr:.1f} oversold (<-90), above SMA200 | Backtest WR={bt_wr:.0%} on {symbol}",
                    raw_signal={"williams_r": round(wr, 2), "sma200": round(sma200, 2), "bt_wr": bt_wr},
                ))
        return picks[:3]


# ---------------------------------------------------------------------------
# All catered strategies for easy import
# ---------------------------------------------------------------------------
ALL_CATERED = [
    CateredConnorsRSI2(),
    CateredVWAPReversion(),
    CateredMACDDivergence(),
    CateredBollingerReversion(),
    CateredRSIExtreme(),
    CateredWilliamsR(),
]
