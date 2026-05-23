"""
LSTM-inspired price direction predictor — feature generator for XGBoost scorer.

Predicts "will price go up or down in the next 4 hours?" using temporal gating
mechanics inspired by LSTM cells, implemented purely with numpy (no ML frameworks).

This is NOT a trained neural network.  It is a rule-based feature extractor that
uses the same mathematical primitives as an LSTM (forget gate, input gate, cell
state, output gate) to capture momentum, mean-reversion, and volatility-regime
signals from the last 24 hourly closes.

Output: direction probability (0 = strong down, 1 = strong up) plus component
features for downstream XGBoost consumption.

Dependencies: numpy (fallback to pure-Python math if unavailable)
"""

from __future__ import annotations

import math
import sys
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# numpy with graceful fallback
# ---------------------------------------------------------------------------
try:
    import numpy as np  # type: ignore
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ---------------------------------------------------------------------------
# Pure-Python math helpers (used when numpy is missing)
# ---------------------------------------------------------------------------

def _py_mean(xs: list) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def _py_std(xs: list) -> float:
    if len(xs) < 2:
        return 0.0
    m = _py_mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

def _py_exp(x: float) -> float:
    return math.exp(max(-500.0, min(500.0, x)))

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    x = max(-500.0, min(500.0, x))
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ez = math.exp(x)
    return ez / (1.0 + ez)

def _tanh(x: float) -> float:
    x = max(-500.0, min(500.0, x))
    return math.tanh(x)


# ===================================================================
# LSTMPredictor
# ===================================================================
class LSTMPredictor:
    """Lightweight LSTM-inspired direction predictor.

    Uses temporal gating (forget / input / output gates) implemented via
    numpy matrix ops or pure-Python math as a fallback.

    Parameters
    ----------
    hidden_size : int
        Dimension of internal state vectors (default 32).
    lookback : int
        Expected number of hourly closes (default 24).
    momentum_decay : float
        Exponential decay for the momentum (forget-gate) component.
    mean_reversion_window : int
        Window length for the mean-reversion (input-gate) component.
    """

    def __init__(
        self,
        hidden_size: int = 32,
        lookback: int = 24,
        momentum_decay: float = 0.92,
        mean_reversion_window: int = 8,
    ):
        self.hidden_size = hidden_size
        self.lookback = lookback
        self.momentum_decay = momentum_decay
        self.mr_window = mean_reversion_window

    # ------------------------------------------------------------------
    # Internal: compute returns from closes
    # ------------------------------------------------------------------
    @staticmethod
    def _to_returns(closes: List[float]) -> List[float]:
        """Convert price series to simple returns."""
        returns = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            if prev == 0:
                returns.append(0.0)
            else:
                returns.append((closes[i] - prev) / prev)
        return returns

    # ------------------------------------------------------------------
    # Gate 1  — Forget gate / Exponentially-weighted momentum
    # ------------------------------------------------------------------
    def _momentum_gate(self, returns: List[float]) -> float:
        """Exponentially-weighted momentum, analogous to LSTM forget gate.

        Recent returns get higher weight.  Positive → bullish momentum,
        negative → bearish.  Range roughly -1 … +1.
        """
        if not returns:
            return 0.0
        decay = self.momentum_decay
        weighted_sum = 0.0
        weight_total = 0.0
        n = len(returns)
        for i, r in enumerate(returns):
            w = decay ** (n - 1 - i)  # most recent → weight ≈ 1
            weighted_sum += w * r
            weight_total += w
        raw = weighted_sum / weight_total if weight_total else 0.0
        # Scale so that ±5 % average return maps to ±1
        return max(-1.0, min(1.0, raw / 0.05))

    # ------------------------------------------------------------------
    # Gate 2  — Input gate / Mean-reversion signal
    # ------------------------------------------------------------------
    def _mean_reversion_gate(self, returns: List[float]) -> float:
        """Short-window z-score of recent returns vs full window.

        Positive z-score (price ran up) → expect mean reversion down,
        so we INVERT the sign: high z → negative (bearish input gate).
        Range roughly -1 … +1.
        """
        if len(returns) < self.mr_window + 2:
            return 0.0
        full_mean = _py_mean(returns)
        full_std = _py_std(returns)
        if full_std < 1e-12:
            return 0.0
        recent = returns[-self.mr_window:]
        recent_mean = _py_mean(recent)
        z = (recent_mean - full_mean) / full_std
        # Invert: high z → bearish mean-reversion pressure
        inverted = -z
        return max(-1.0, min(1.0, inverted / 2.0))

    # ------------------------------------------------------------------
    # Cell state — Volatility regime detector
    # ------------------------------------------------------------------
    def _volatility_state(self, returns: List[float]) -> float:
        """Volatility regime: 0 = dead quiet, 1 = extremely volatile.

        High volatility regimes tend to favour mean-reversion; low
        volatility favours momentum continuation.
        """
        if len(returns) < 4:
            return 0.5
        std = _py_std(returns)
        # Normalize: daily crypto vol ~2-5 % is "normal"
        # Hourly returns are ~1/sqrt(24) of daily → ~0.4–1 %
        # Map 0 % → 0, 2 % → ~0.7, 5 %+ → 1.0
        vol_score = _sigmoid((std - 0.01) / 0.005)
        return vol_score

    # ------------------------------------------------------------------
    # Output gate — Trend consistency
    # ------------------------------------------------------------------
    def _trend_consistency(self, returns: List[float]) -> float:
        """Fraction of recent returns that agree with the momentum direction.

        High consistency → momentum signal is more trustworthy.
        Range 0 … 1.
        """
        if not returns:
            return 0.5
        mom = self._momentum_gate(returns)
        if abs(mom) < 0.05:
            return 0.5
        direction = 1.0 if mom > 0 else -1.0
        agreements = sum(1 for r in returns[-12:] if r * direction > 0)
        total = min(12, len(returns))
        return agreements / total if total else 0.5

    # ------------------------------------------------------------------
    # Combine gates → direction probability
    # ------------------------------------------------------------------
    def _combine_gates(
        self,
        momentum: float,
        mean_rev: float,
        vol_state: float,
        consistency: float,
    ) -> float:
        """LSTM-style gating combination.

        - In LOW volatility: momentum dominates (forget gate keeps state)
        - In HIGH volatility: mean-reversion dominates (input gate resets)
        - Consistency modulates overall confidence
        """
        # Forget gate weight (momentum) — stronger when vol is low
        forget_w = 1.0 - vol_state  # 0–1
        # Input gate weight (mean reversion) — stronger when vol is high
        input_w = vol_state

        # Cell update: weighted sum of momentum and mean-reversion
        cell = forget_w * momentum + input_w * mean_rev

        # Output gate: scale by trend consistency
        # consistency 0.5 = neutral, 1.0 = very consistent
        output_gate = 0.5 + (consistency - 0.5) * 0.8

        # Final signal: cell * output_gate, mapped through sigmoid
        # Scale factor 3.0 so that moderate signals reach ~0.65–0.75
        raw = cell * output_gate * 3.0
        prob = _sigmoid(raw)
        return prob

    # ==================================================================
    # Public API
    # ==================================================================

    def predict_direction(self, closes_24h: List[float]) -> float:
        """Predict price direction probability for the next 4 hours.

        Parameters
        ----------
        closes_24h : list of float
            Last 24 hourly close prices (oldest first).

        Returns
        -------
        float
            Probability 0.0 (strong down) to 1.0 (strong up).
            Returns 0.5 (neutral) if data is insufficient.
        """
        if not closes_24h or len(closes_24h) < 3:
            return 0.5

        # Pad to at least a few points if short
        returns = self._to_returns(closes_24h)
        if not returns:
            return 0.5

        momentum = self._momentum_gate(returns)
        mean_rev = self._mean_reversion_gate(returns)
        vol_state = self._volatility_state(returns)
        consistency = self._trend_consistency(returns)

        return self._combine_gates(momentum, mean_rev, vol_state, consistency)

    def predict_batch(self, prices_dict: Dict[str, List[float]]) -> Dict[str, float]:
        """Predict direction probability for multiple symbols.

        Parameters
        ----------
        prices_dict : dict
            ``{symbol: [24 hourly closes]}``

        Returns
        -------
        dict
            ``{symbol: direction_probability}``
        """
        results: Dict[str, float] = {}
        for symbol, closes in prices_dict.items():
            try:
                results[symbol] = self.predict_direction(closes)
            except Exception:
                results[symbol] = 0.5
        return results

    def get_lstm_features(
        self, symbol: str, closes_24h: List[float]
    ) -> Dict[str, float]:
        """Return feature dict for XGBoost scorer.

        Parameters
        ----------
        symbol : str
            Coin / ticker symbol (for logging only).
        closes_24h : list of float
            Last 24 hourly close prices.

        Returns
        -------
        dict with keys:
            - ``lstm_direction_prob``: 0–1 probability
            - ``lstm_momentum_gate``: -1 to +1 momentum component
            - ``lstm_volatility_state``: 0–1 volatility regime
        """
        defaults = {
            "lstm_direction_prob": 0.5,
            "lstm_momentum_gate": 0.0,
            "lstm_volatility_state": 0.5,
        }
        if not closes_24h or len(closes_24h) < 3:
            return defaults

        try:
            returns = self._to_returns(closes_24h)
            if not returns:
                return defaults

            momentum = self._momentum_gate(returns)
            mean_rev = self._mean_reversion_gate(returns)
            vol_state = self._volatility_state(returns)
            consistency = self._trend_consistency(returns)
            prob = self._combine_gates(momentum, mean_rev, vol_state, consistency)

            return {
                "lstm_direction_prob": round(prob, 6),
                "lstm_momentum_gate": round(momentum, 6),
                "lstm_volatility_state": round(vol_state, 6),
            }
        except Exception:
            return defaults


# ======================================================================
# Standalone integration function (called from scanner / production)
# ======================================================================

_DEFAULT_PREDICTOR = LSTMPredictor()


def inject_lstm_features(
    signals: list,
    prices_dict: Dict[str, List[float]],
) -> list:
    """Inject LSTM-inspired features onto each signal dict.

    Parameters
    ----------
    signals : list[dict]
        Signal dicts (must have ``'symbol'`` key).
    prices_dict : dict
        ``{symbol: [24 hourly closes]}``

    Returns
    -------
    list[dict]
        Same signal list with ``lstm_direction_prob``,
        ``lstm_momentum_gate``, ``lstm_volatility_state`` added.
    """
    if not signals:
        return signals

    prices_dict = prices_dict or {}

    # Pre-compute batch predictions for all symbols present
    symbols_in_signals = {s.get("symbol", "") for s in signals if s.get("symbol")}
    batch_prices = {
        sym: closes
        for sym, closes in prices_dict.items()
        if sym in symbols_in_signals
    }

    # Build feature cache
    feature_cache: Dict[str, Dict[str, float]] = {}
    for sym, closes in batch_prices.items():
        feature_cache[sym] = _DEFAULT_PREDICTOR.get_lstm_features(sym, closes)

    # Default features for symbols without price data
    defaults = {
        "lstm_direction_prob": 0.5,
        "lstm_momentum_gate": 0.0,
        "lstm_volatility_state": 0.5,
    }

    for sig in signals:
        sym = sig.get("symbol", "")
        features = feature_cache.get(sym, defaults)
        sig.update(features)

    return signals


# ======================================================================
# CLI: fetch BTC/ETH/SOL 24h klines from Binance and print predictions
# ======================================================================

def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 25) -> List[float]:
    """Fetch hourly klines from Binance public API."""
    import urllib.request
    import json

    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        # Each kline: [open_time, open, high, low, close, ...]
        closes = [float(k[4]) for k in data]
        return closes
    except Exception as exc:
        print(f"  [WARN] Failed to fetch {symbol}: {exc}")
        return []


def main() -> None:
    """CLI entry point — fetch and predict for BTC, ETH, SOL."""
    predictor = LSTMPredictor()
    symbols = [
        ("BTCUSDT", "BTC"),
        ("ETHUSDT", "ETH"),
        ("SOLUSDT", "SOL"),
    ]

    print("=" * 60)
    print("LSTM-Inspired Price Direction Predictor")
    print("=" * 60)

    prices_dict: Dict[str, List[float]] = {}

    for binance_sym, display in symbols:
        closes = _fetch_klines(binance_sym, "1h", 25)
        if closes:
            prices_dict[display] = closes
            features = predictor.get_lstm_features(display, closes)
            prob = features["lstm_direction_prob"]
            mom = features["lstm_momentum_gate"]
            vol = features["lstm_volatility_state"]

            direction = "UP" if prob > 0.55 else ("DOWN" if prob < 0.45 else "NEUTRAL")
            print(f"\n{display} ({binance_sym})")
            print(f"  Last price   : ${closes[-1]:,.2f}")
            print(f"  Direction     : {direction} (prob={prob:.4f})")
            print(f"  Momentum gate : {mom:+.4f}")
            print(f"  Volatility    : {vol:.4f}")
        else:
            print(f"\n{display}: No data available")

    # Batch prediction demo
    if prices_dict:
        print(f"\n{'─' * 60}")
        print("Batch predictions:")
        batch = predictor.predict_batch(prices_dict)
        for sym, prob in batch.items():
            direction = "UP" if prob > 0.55 else ("DOWN" if prob < 0.45 else "NEUTRAL")
            print(f"  {sym:>5s}: {prob:.4f} ({direction})")

    print(f"\n{'=' * 60}")
    print("Done. These features plug into XGBoost via inject_lstm_features().")


if __name__ == "__main__":
    main()
