"""
ALPHA_ENGINE -- GARCH Volatility Forecaster
=============================================
Forecasts next-period volatility using GARCH(1,1) model.
Used for:
  1. Dynamic TP/SL scaling (wider in high vol, tighter in low vol)
  2. Position sizing (inverse volatility weighting)
  3. Regime-adaptive risk management
  4. Volatility breakout signal generation

Why GARCH works for crypto/forex:
  - Volatility clustering: high vol periods persist (Mandelbrot 1963)
  - Mean-reverting vol: extreme vol reverts to long-term average
  - Asymmetric response: bad news increases vol more than good news

Model: GARCH(1,1) -- the workhorse of volatility forecasting
  σ²(t) = ω + α·ε²(t-1) + β·σ²(t-1)
  where:
    ω = long-run variance weight
    α = ARCH coefficient (reaction to shocks)
    β = GARCH coefficient (persistence)
    α + β < 1 for stationarity

References:
  - Engle (1982), "Autoregressive Conditional Heteroscedasticity" -- Nobel Prize 2003
  - Bollerslev (1986), "Generalized ARCH" -- the GARCH(1,1) model
  - Hansen & Lunde (2005), "A Forecast Comparison of Volatility Models" --
    GARCH(1,1) hard to beat for daily/4H data

Implementation: Pure numpy (no arch library dependency for CI compatibility).
Falls back to exponentially weighted moving vol if GARCH fitting fails.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CACHE_FILE = _DATA_DIR / "garch_forecasts.json"


# ---------------------------------------------------------------------------
# GARCH(1,1) -- Pure numpy implementation
# ---------------------------------------------------------------------------

class GARCHModel:
    """
    GARCH(1,1) volatility model.

    Fits parameters (omega, alpha, beta) via maximum likelihood estimation
    using scipy.optimize (if available) or grid search fallback.

    Usage:
        model = GARCHModel()
        model.fit(returns)  # array of log returns
        forecast = model.forecast(horizon=1)  # next-period vol forecast
    """

    def __init__(self, omega: float = 0.0, alpha: float = 0.1, beta: float = 0.85):
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.fitted = False
        self.sigma2 = None  # conditional variance series
        self.long_run_var = None

    def fit(self, returns: np.ndarray, method: str = "mle") -> dict:
        """
        Fit GARCH(1,1) to return series.

        Args:
            returns: Array of log returns (or simple returns)
            method: 'mle' (scipy optimize) or 'grid' (grid search fallback)

        Returns:
            dict with omega, alpha, beta, log_likelihood, long_run_var
        """
        r = np.asarray(returns, dtype=np.float64)
        r = r[~np.isnan(r)]

        if len(r) < 50:
            logger.warning("GARCH: insufficient data (%d < 50), using EWMA fallback", len(r))
            return self._ewma_fallback(r)

        # Demean returns
        r = r - r.mean()
        sample_var = float(np.var(r))

        if sample_var <= 0:
            return self._ewma_fallback(r)

        if method == "mle":
            result = self._fit_mle(r, sample_var)
        else:
            result = self._fit_grid(r, sample_var)

        if result is None:
            return self._ewma_fallback(r)

        self.omega, self.alpha, self.beta = result["omega"], result["alpha"], result["beta"]

        # Compute conditional variance series
        self.sigma2 = self._compute_sigma2(r, self.omega, self.alpha, self.beta, sample_var)
        self.long_run_var = self.omega / max(1e-10, 1 - self.alpha - self.beta)
        self.fitted = True

        return {
            "omega": round(self.omega, 8),
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "persistence": round(self.alpha + self.beta, 4),
            "long_run_vol": round(math.sqrt(self.long_run_var) * 100, 2),
            "current_vol": round(math.sqrt(float(self.sigma2[-1])) * 100, 2),
            "log_likelihood": round(result.get("ll", 0), 2),
            "method": result.get("method", "unknown"),
        }

    def forecast(self, horizon: int = 1) -> dict:
        """
        Forecast volatility for next `horizon` periods.

        Returns:
            dict with vol_forecast (annualized %), vol_ratio (vs long-run),
            regime suggestion, and TP/SL multiplier recommendation
        """
        if not self.fitted or self.sigma2 is None:
            return {"vol_forecast": None, "regime": "unknown", "tp_sl_mult": 1.0}

        # h-step ahead forecast: σ²(h) = ω·Σ(α+β)^i + (α+β)^h · σ²(current)
        current_var = float(self.sigma2[-1])
        persistence = self.alpha + self.beta

        if horizon == 1:
            forecast_var = self.omega + self.alpha * (current_var) + self.beta * current_var
        else:
            forecast_var = self.long_run_var + (persistence ** horizon) * (current_var - self.long_run_var)

        forecast_vol = math.sqrt(max(forecast_var, 1e-12))
        long_run_vol = math.sqrt(max(self.long_run_var, 1e-12))

        # Vol ratio: how does forecast compare to long-run average?
        vol_ratio = forecast_vol / long_run_vol if long_run_vol > 0 else 1.0

        # Regime classification based on vol ratio
        if vol_ratio > 1.5:
            regime = "high_volatility"
            tp_sl_mult = 1.5  # Widen TP/SL in high vol
            position_mult = 0.6  # Reduce position size
        elif vol_ratio > 1.2:
            regime = "elevated_volatility"
            tp_sl_mult = 1.2
            position_mult = 0.8
        elif vol_ratio < 0.7:
            regime = "low_volatility"
            tp_sl_mult = 0.7  # Tighten TP/SL in low vol
            position_mult = 1.2  # Can take larger positions
        elif vol_ratio < 0.5:
            regime = "compressed_volatility"
            tp_sl_mult = 0.6
            position_mult = 1.3  # Breakout likely coming
        else:
            regime = "normal_volatility"
            tp_sl_mult = 1.0
            position_mult = 1.0

        return {
            "vol_forecast_pct": round(forecast_vol * 100, 4),
            "long_run_vol_pct": round(long_run_vol * 100, 4),
            "vol_ratio": round(vol_ratio, 3),
            "vol_regime": regime,
            "tp_sl_multiplier": tp_sl_mult,
            "position_size_multiplier": round(position_mult, 2),
            "persistence": round(persistence, 4),
            "horizon": horizon,
        }

    # -----------------------------------------------------------------------
    # Internal methods
    # -----------------------------------------------------------------------

    @staticmethod
    def _compute_sigma2(r: np.ndarray, omega: float, alpha: float, beta: float,
                        initial_var: float) -> np.ndarray:
        """Compute conditional variance series given parameters."""
        n = len(r)
        sigma2 = np.zeros(n)
        sigma2[0] = initial_var

        for t in range(1, n):
            sigma2[t] = omega + alpha * r[t - 1] ** 2 + beta * sigma2[t - 1]
            # Floor to prevent numerical issues
            if sigma2[t] < 1e-12:
                sigma2[t] = 1e-12

        return sigma2

    @staticmethod
    def _log_likelihood(r: np.ndarray, sigma2: np.ndarray) -> float:
        """Gaussian log-likelihood for GARCH model."""
        n = len(r)
        # LL = -0.5 * Σ [log(2π) + log(σ²_t) + r²_t/σ²_t]
        ll = -0.5 * np.sum(np.log(2 * np.pi) + np.log(sigma2 + 1e-12) + r ** 2 / (sigma2 + 1e-12))
        return float(ll) if np.isfinite(ll) else -1e10

    def _fit_mle(self, r: np.ndarray, sample_var: float) -> Optional[dict]:
        """Fit via scipy MLE optimization."""
        try:
            from scipy.optimize import minimize
        except ImportError:
            logger.info("GARCH: scipy not available, falling back to grid search")
            return self._fit_grid(r, sample_var)

        def neg_ll(params):
            o, a, b = params
            if o <= 0 or a < 0.01 or b < 0.01 or a + b >= 0.999:
                return 1e10
            s2 = self._compute_sigma2(r, o, a, b, sample_var)
            return -self._log_likelihood(r, s2)

        # Initial guess: moderate persistence
        x0 = [sample_var * 0.05, 0.08, 0.88]
        bounds = [(1e-8, sample_var * 10), (0.01, 0.5), (0.3, 0.98)]

        try:
            result = minimize(neg_ll, x0, method="L-BFGS-B", bounds=bounds,
                              options={"maxiter": 500, "ftol": 1e-8})
            if result.success and result.fun < 1e9:
                o, a, b = result.x
                return {"omega": o, "alpha": a, "beta": b,
                        "ll": -result.fun, "method": "mle"}
        except Exception as e:
            logger.debug("GARCH MLE failed: %s", e)

        return self._fit_grid(r, sample_var)

    def _fit_grid(self, r: np.ndarray, sample_var: float) -> Optional[dict]:
        """Fit via grid search (fallback when scipy unavailable)."""
        best_ll = -1e10
        best_params = None

        for alpha in [0.03, 0.06, 0.09, 0.12, 0.15, 0.20]:
            for beta in [0.75, 0.80, 0.85, 0.88, 0.90, 0.93]:
                if alpha + beta >= 0.999:
                    continue
                omega = sample_var * (1 - alpha - beta)
                if omega <= 0:
                    continue

                sigma2 = self._compute_sigma2(r, omega, alpha, beta, sample_var)
                ll = self._log_likelihood(r, sigma2)

                if ll > best_ll:
                    best_ll = ll
                    best_params = {"omega": omega, "alpha": alpha, "beta": beta,
                                   "ll": ll, "method": "grid"}

        return best_params

    def _ewma_fallback(self, r: np.ndarray) -> dict:
        """EWMA volatility as fallback when GARCH fails."""
        decay = 0.94  # RiskMetrics standard
        var_series = np.zeros(len(r))
        var_series[0] = float(np.var(r[:20])) if len(r) >= 20 else float(np.var(r))

        for t in range(1, len(r)):
            var_series[t] = decay * var_series[t - 1] + (1 - decay) * r[t - 1] ** 2

        self.sigma2 = var_series
        self.long_run_var = float(np.var(r))
        self.omega = self.long_run_var * 0.06
        self.alpha = 1 - decay
        self.beta = decay
        self.fitted = True

        return {
            "omega": round(self.omega, 8),
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "persistence": round(self.alpha + self.beta, 4),
            "long_run_vol": round(math.sqrt(self.long_run_var) * 100, 2),
            "current_vol": round(math.sqrt(float(var_series[-1])) * 100, 2),
            "log_likelihood": 0,
            "method": "ewma_fallback",
        }


# ---------------------------------------------------------------------------
# Scanner integration: GARCH-based volatility signal
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def garch_volatility_signal(data: dict, context: dict = None) -> list[dict]:
    """
    GARCH-based volatility strategy:
      - Fit GARCH(1,1) to each symbol's returns
      - Generate signals when volatility is compressed (breakout expected)
        OR when volatility is extremely elevated (mean reversion expected)

    Compressed vol (vol_ratio < 0.5):
      → BUY if trend is bullish (breakout long)
      → SELL if trend is bearish (breakout short)

    Extreme vol (vol_ratio > 2.0):
      → Contrarian: fade the move (vol will revert to mean)

    Based on:
      - Engle (1982): ARCH model, volatility clustering
      - Bollerslev (1986): GARCH(1,1) -- persistence + mean reversion
      - Garman & Klass (1980): vol compression precedes breakouts
    """
    signals = []

    # Target symbols: major crypto pairs
    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("ADA-USD", "crypto"), ("AVAX-USD", "crypto"),
        ("DOT-USD", "crypto"), ("LINK-USD", "crypto"), ("DOGE-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("APT-USD", "crypto"), ("ARB-USD", "crypto"),
    ]

    for symbol, category in targets:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue

        try:
            close = df["Close"].values.astype(float)
            high = df["High"].values.astype(float)
            low = df["Low"].values.astype(float)
        except (KeyError, TypeError):
            continue

        current_price = float(close[-1])
        if current_price <= 0:
            continue

        # Compute log returns
        log_returns = np.diff(np.log(close + 1e-10))
        if len(log_returns) < 60:
            continue

        # Fit GARCH(1,1)
        model = GARCHModel()
        fit_result = model.fit(log_returns)

        if not model.fitted:
            continue

        # Forecast next-period volatility
        forecast = model.forecast(horizon=1)
        vol_ratio = forecast.get("vol_ratio", 1.0)
        vol_regime = forecast.get("vol_regime", "normal_volatility")
        tp_sl_mult = forecast.get("tp_sl_multiplier", 1.0)

        # ATR for TP/SL base
        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        atr_14 = float(np.mean(tr[-14:])) if len(tr) >= 14 else current_price * 0.03

        # Simple trend: 20-bar SMA direction
        sma_20 = float(np.mean(close[-20:]))
        sma_50 = float(np.mean(close[-50:])) if len(close) >= 50 else sma_20
        trend_bullish = sma_20 > sma_50

        # --- COMPRESSED VOLATILITY: breakout expected ---
        if vol_ratio < 0.5:
            direction = "BUY" if trend_bullish else "SELL"
            dir_label = "long" if trend_bullish else "short"

            if direction == "BUY":
                tp = current_price + atr_14 * 4.0 * tp_sl_mult
                sl = current_price - atr_14 * 1.5 * tp_sl_mult
            else:
                tp = current_price - atr_14 * 4.0 * tp_sl_mult
                sl = current_price + atr_14 * 1.5 * tp_sl_mult

            rr = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0
            if rr < 1.5:
                continue

            conf = min(0.78, 0.58 + (0.5 - vol_ratio) * 0.3)

            signals.append({
                "strategy": "garch_vol_breakout",
                "symbol": symbol.replace("-USD", "USDT"),
                "category": category,
                "signal_type": direction,
                "direction": dir_label,
                "entry_price": round(current_price, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"GARCH vol breakout: vol compressed {vol_ratio:.2f}x long-run "
                    f"(regime: {vol_regime}). Trend: {'bullish' if trend_bullish else 'bearish'}. "
                    f"Forecast vol: {forecast['vol_forecast_pct']:.2f}%, "
                    f"long-run: {forecast['long_run_vol_pct']:.2f}%. "
                    f"Persistence: {forecast['persistence']:.3f}. "
                    f"Engle (1982) / Bollerslev (1986)."
                ),
                "timeframe": "1d",
                "extra": {
                    "garch_vol_ratio": round(vol_ratio, 3),
                    "garch_vol_regime": vol_regime,
                    "garch_forecast_vol": forecast["vol_forecast_pct"],
                    "garch_long_run_vol": forecast["long_run_vol_pct"],
                    "garch_persistence": forecast["persistence"],
                    "garch_alpha": fit_result.get("alpha", 0),
                    "garch_beta": fit_result.get("beta", 0),
                    "garch_method": fit_result.get("method", ""),
                    "tp_sl_multiplier": tp_sl_mult,
                    "source": "GARCH(1,1) -- Engle 1982, Bollerslev 1986",
                },
                "timestamp": _now_iso(),
            })

        # --- EXTREME VOLATILITY: mean reversion of vol expected ---
        elif vol_ratio > 2.0:
            # Fade the move: if vol spiked on a drop, buy the dip
            # If vol spiked on a pump, short the exhaustion
            recent_return = (close[-1] - close[-5]) / close[-5] if len(close) >= 5 else 0
            direction = "BUY" if recent_return < -0.05 else ("SELL" if recent_return > 0.05 else None)

            if direction is None:
                continue

            dir_label = "long" if direction == "BUY" else "short"

            if direction == "BUY":
                tp = current_price + atr_14 * 2.5 * tp_sl_mult
                sl = current_price - atr_14 * 2.0 * tp_sl_mult
            else:
                tp = current_price - atr_14 * 2.5 * tp_sl_mult
                sl = current_price + atr_14 * 2.0 * tp_sl_mult

            rr = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0
            if rr < 1.2:
                continue

            conf = min(0.72, 0.50 + (vol_ratio - 2.0) * 0.05)

            signals.append({
                "strategy": "garch_vol_meanrev",
                "symbol": symbol.replace("-USD", "USDT"),
                "category": category,
                "signal_type": direction,
                "direction": dir_label,
                "entry_price": round(current_price, 2),
                "take_profit": round(tp, 2),
                "stop_loss": round(sl, 2),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"GARCH vol mean-reversion: vol elevated {vol_ratio:.2f}x long-run "
                    f"(regime: {vol_regime}). 5d return: {recent_return*100:.1f}% -- "
                    f"fading the move. Forecast vol: {forecast['vol_forecast_pct']:.2f}%. "
                    f"Vol reverts to {forecast['long_run_vol_pct']:.2f}% long-run. "
                    f"Engle (1982) / Bollerslev (1986)."
                ),
                "timeframe": "1d",
                "extra": {
                    "garch_vol_ratio": round(vol_ratio, 3),
                    "garch_vol_regime": vol_regime,
                    "garch_forecast_vol": forecast["vol_forecast_pct"],
                    "garch_long_run_vol": forecast["long_run_vol_pct"],
                    "garch_persistence": forecast["persistence"],
                    "recent_5d_return": round(recent_return * 100, 2),
                    "tp_sl_multiplier": tp_sl_mult,
                    "source": "GARCH(1,1) vol mean-reversion",
                },
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# Utility: get GARCH forecast for a symbol (used by other modules)
# ---------------------------------------------------------------------------

def get_garch_forecast(close_prices: np.ndarray, horizon: int = 1) -> dict:
    """
    Convenience function: fit GARCH and return forecast for any price series.
    Used by dynamic TP/SL engine, position sizer, and regime router.
    """
    if len(close_prices) < 50:
        return {"vol_forecast_pct": None, "vol_ratio": 1.0, "tp_sl_multiplier": 1.0,
                "vol_regime": "unknown", "position_size_multiplier": 1.0}

    log_returns = np.diff(np.log(close_prices.astype(float) + 1e-10))
    model = GARCHModel()
    model.fit(log_returns)

    if not model.fitted:
        return {"vol_forecast_pct": None, "vol_ratio": 1.0, "tp_sl_multiplier": 1.0,
                "vol_regime": "unknown", "position_size_multiplier": 1.0}

    return model.forecast(horizon=horizon)


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

GARCH_STRATEGIES: dict[str, callable] = {
    "garch_vol_breakout": garch_volatility_signal,
    "garch_vol_meanrev": garch_volatility_signal,
}
