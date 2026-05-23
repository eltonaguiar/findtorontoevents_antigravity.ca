"""
ALPHA_ENGINE -- Regime-Adaptive Position Sizing
================================================
Adjusts position sizes based on market regime classification.
Instead of fixed sizing, scales exposure to match conviction.

Regime multipliers:
  BULL + EXPANSION:    1.0x (full size, trending with momentum)
  BULL + COMPRESSION:  0.7x (breakout anticipation, smaller until confirmed)
  BULL + NORMAL:       1.0x (standard trending)
  BEAR + EXPANSION:    0.3x (high risk, minimal exposure)
  BEAR + COMPRESSION:  0.5x (reversal watch, cautious)
  BEAR + NORMAL:       0.5x (mean reversion only, half size)
  NEUTRAL + EXPANSION: 0.6x (volatile chop, reduce)
  NEUTRAL + COMPRESSION: 0.5x (range trading, smaller)
  NEUTRAL + NORMAL:    0.3x (no edge, minimal)

References:
  - Kelly (1956): Optimal position sizing under uncertainty
  - MenthorQ: Regime-adaptive sizing improves Sharpe by 0.3-0.5
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Inline indicator functions (standalone — no external `indicators` package)
# ---------------------------------------------------------------------------

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    dm_plus = (high - prev_high).clip(lower=0).where(
        (high - prev_high) > (prev_low - low), 0.0)
    dm_minus = (prev_low - low).clip(lower=0).where(
        (prev_low - low) > (high - prev_high), 0.0)
    atr_s = atr(high, low, close, period)
    atr_safe = atr_s.replace(0, np.nan)
    di_plus = 100 * dm_plus.rolling(period, min_periods=1).mean() / atr_safe
    di_minus = 100 * dm_minus.rolling(period, min_periods=1).mean() / atr_safe
    dx = (100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan))
    return dx.rolling(period, min_periods=1).mean().fillna(20.0)


def bollinger_bands(close: pd.Series, window: int = 20) -> dict[str, pd.Series]:
    mid = sma(close, window)
    std = close.rolling(window, min_periods=1).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    bandwidth = ((upper - lower) / mid.replace(0, np.nan)).fillna(0.0)
    return {"mid": mid, "upper": upper, "lower": lower, "bandwidth": bandwidth}


# ---------------------------------------------------------------------------
# Regime size multipliers (3x3 matrix)
# ---------------------------------------------------------------------------

REGIME_SIZE_MULTIPLIERS: dict[str, float] = {
    "BULL_EXPANSION": 1.0,
    "BULL_COMPRESSION": 0.7,
    "BULL_NORMAL": 1.0,
    "BEAR_EXPANSION": 0.3,
    "BEAR_COMPRESSION": 0.5,
    "BEAR_NORMAL": 0.5,
    "NEUTRAL_EXPANSION": 0.6,
    "NEUTRAL_COMPRESSION": 0.5,
    "NEUTRAL_NORMAL": 0.3,
}


# ---------------------------------------------------------------------------
# Simplified regime classification (avoids circular import with regime_router)
# ---------------------------------------------------------------------------

def _classify_trend_simple(close: pd.Series, high: pd.Series,
                           low: pd.Series, lookback: int = 100) -> str:
    """
    Classify trend state: BULL / BEAR / NEUTRAL.
    Simplified port of regime_router._classify_trend to avoid circular import.
    Uses EMA crossover, RSI momentum, and ADX gating.
    """
    if len(close) < lookback:
        return "NEUTRAL"

    # Smoothed log returns (14-bar average)
    log_ret = np.log(close / close.shift(1))
    smoothed_ret = log_ret.rolling(14, min_periods=1).mean()
    current_ret = float(smoothed_ret.iloc[-1]) if not np.isnan(smoothed_ret.iloc[-1]) else 0.0

    # EMA displacement: EMA9 vs EMA21 relative to ATR
    ema9 = ema(close, 9)
    ema21 = ema(close, 21)
    atr_val = atr(high, low, close, 14)
    atr_safe = max(float(atr_val.iloc[-1]), 1e-10)
    displacement = float(ema9.iloc[-1] - ema21.iloc[-1]) / atr_safe

    # RSI momentum
    rsi_val = rsi(close, 14)
    current_rsi = float(rsi_val.iloc[-1]) if not np.isnan(rsi_val.iloc[-1]) else 50.0

    # ADX for trend strength
    adx_val = adx(high, low, close, 14)
    current_adx = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 20.0

    # Scoring
    ret_score = np.clip(current_ret / 0.005, -1.0, 1.0)
    disp_score = np.clip(displacement / 2.0, -1.0, 1.0)
    rsi_score = (current_rsi - 50.0) / 50.0

    trend_score = ret_score * 0.30 + disp_score * 0.35 + rsi_score * 0.35

    # ADX gate: weak trends dampened
    if current_adx < 20:
        trend_score *= 0.5

    if trend_score > 0.15:
        return "BULL"
    elif trend_score < -0.15:
        return "BEAR"
    return "NEUTRAL"


def _classify_volatility_simple(close: pd.Series, high: pd.Series,
                                low: pd.Series, lookback: int = 100) -> str:
    """
    Classify volatility state: EXPANSION / COMPRESSION / NORMAL.
    Simplified port of regime_router._classify_volatility.
    Uses ATR percentile rank and Bollinger bandwidth expansion.
    """
    if len(close) < lookback:
        return "NORMAL"

    atr_series = atr(high, low, close, 14)
    atr_window = atr_series.iloc[-lookback:]
    current_atr = float(atr_series.iloc[-1])

    if np.isnan(current_atr) or atr_window.isna().all():
        return "NORMAL"

    pct_rank = float((atr_window < current_atr).sum()) / len(atr_window)

    # Bollinger bandwidth trend
    bb = bollinger_bands(close, 20)
    bw = bb["bandwidth"]
    bw_sma = sma(bw, 20)
    bw_expanding = False
    if not bw.empty and not bw_sma.empty:
        curr_bw = float(bw.iloc[-1]) if not np.isnan(bw.iloc[-1]) else 0
        avg_bw = float(bw_sma.iloc[-1]) if not np.isnan(bw_sma.iloc[-1]) else 0
        bw_expanding = curr_bw > avg_bw * 1.2

    if pct_rank < 0.25:
        return "COMPRESSION"
    elif pct_rank > 0.75 or bw_expanding:
        return "EXPANSION"
    return "NORMAL"


# ---------------------------------------------------------------------------
# PositionSizer
# ---------------------------------------------------------------------------

class PositionSizer:
    """
    Regime-adaptive position sizing.

    Adjusts position sizes based on the current market regime (trend x volatility).
    Instead of using a fixed percentage risk per trade, the sizer scales exposure
    up in high-conviction regimes (e.g. BULL_EXPANSION) and down in
    low-conviction or dangerous regimes (e.g. BEAR_EXPANSION, NEUTRAL_NORMAL).

    Usage:
        sizer = PositionSizer(base_risk_pct=2.0)
        sized_signals = sizer.size_signals(signals, data)
    """

    def __init__(self, base_risk_pct: float = 2.0, max_risk_pct: float = 5.0):
        """
        Parameters
        ----------
        base_risk_pct : float
            Base risk percentage per trade before regime adjustment (default 2%).
        max_risk_pct : float
            Hard cap on position size regardless of regime/confidence (default 5%).
        """
        self.base_risk_pct = base_risk_pct
        self.max_risk_pct = max_risk_pct

    def size_signals(
        self, signals: list[dict], data: dict[str, pd.DataFrame]
    ) -> list[dict]:
        """
        Add position_size_pct, regime_cell, and regime_multiplier to each signal.

        For each signal:
        1. Look up the symbol's OHLCV DataFrame from *data*.
        2. Classify the regime (trend x volatility).
        3. Apply regime multiplier and signal confidence to base_risk_pct.
        4. Cap at max_risk_pct.

        Parameters
        ----------
        signals : list[dict]
            Each dict must contain at minimum 'symbol' and 'confidence'.
        data : dict[str, pd.DataFrame]
            Map of symbol -> OHLCV DataFrame (columns: open/Open, high/High,
            low/Low, close/Close, volume/Volume).

        Returns
        -------
        list[dict]
            Same signals with added keys: position_size_pct, regime_cell,
            regime_multiplier.
        """
        regime_cache: dict[str, str] = {}
        sized: list[dict] = []

        for sig in signals:
            symbol = sig.get("symbol", "")
            out = dict(sig)

            # Classify regime (cached per symbol)
            if symbol not in regime_cache:
                regime_cache[symbol] = self._classify_regime(data.get(symbol))

            cell = regime_cache[symbol]
            sized_result = self._calculate_size(sig, cell)
            out.update(sized_result)
            sized.append(out)

        return sized

    def _classify_regime(self, df: pd.DataFrame | None) -> str:
        """
        Classify regime for a single symbol's DataFrame.

        Returns a regime cell string like 'BULL_EXPANSION'.
        Falls back to 'NEUTRAL_NORMAL' when data is insufficient.
        """
        if df is None or len(df) < 50:
            return "NEUTRAL_NORMAL"

        # Normalize column names (handle both 'close' and 'Close')
        close = df.get("close", df.get("Close"))
        high = df.get("high", df.get("High"))
        low = df.get("low", df.get("Low"))

        if close is None or high is None or low is None:
            return "NEUTRAL_NORMAL"

        trend = _classify_trend_simple(close, high, low)
        volatility = _classify_volatility_simple(close, high, low)
        return f"{trend}_{volatility}"

    def _calculate_size(self, signal: dict, regime_cell: str) -> dict:
        """
        Calculate position size based on regime and signal confidence.

        Formula:
            position_size = base_risk_pct * regime_multiplier * confidence_factor
            capped at max_risk_pct

        confidence_factor maps the signal's confidence (0-1 or 0-100) to a
        0.5-1.5 range so higher-confidence signals get larger positions.

        Returns dict with position_size_pct, regime_cell, regime_multiplier.
        """
        multiplier = REGIME_SIZE_MULTIPLIERS.get(regime_cell, 0.5)

        # Normalize confidence to [0, 1] range
        raw_conf = float(signal.get("confidence", 0.5))
        if raw_conf > 1.0:
            # Confidence is on 0-100 scale, normalize to 0-1
            raw_conf = raw_conf / 100.0
        raw_conf = max(0.0, min(1.0, raw_conf))

        # Map confidence to a 0.5-1.5 scaling factor
        # 0.0 confidence -> 0.5x, 0.5 confidence -> 1.0x, 1.0 confidence -> 1.5x
        confidence_factor = 0.5 + raw_conf

        # Final position size
        position_size = self.base_risk_pct * multiplier * confidence_factor

        # Beta-aware sizing (Phase 2): scale by beta score and confidence
        beta_score = signal.get("beta_score", 50)
        beta_mult = 0.7 + (beta_score / 100) * 0.6  # 0.7 (score=0) to 1.3 (score=100)
        beta_mult = max(0.5, min(1.5, beta_mult))
        position_size *= beta_mult

        conf = signal.get("confidence", 0.5)
        conf_mult = 0.8 + conf * 0.4  # 0.8 (conf=0) to 1.2 (conf=1.0)
        position_size *= conf_mult

        position_size = round(min(position_size, self.max_risk_pct), 2)

        return {
            "position_size_pct": position_size,
            "regime_cell": regime_cell,
            "regime_multiplier": multiplier,
        }

    # -- Portfolio-Level Kelly Sizing (v1.2) -------------------------
    @staticmethod
    def kelly_fraction(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        half_kelly: bool = True,
    ) -> float:
        """
        Compute Kelly criterion fraction.

        f* = (p * b - q) / b
        where p = win_rate, q = 1 - p, b = avg_win / avg_loss

        Uses half-Kelly by default for safety (full Kelly is too aggressive
        in practice due to estimation error).

        Parameters
        ----------
        win_rate : float  (0 to 1)
        avg_win : float   (positive, e.g., 0.03 for 3%)
        avg_loss : float  (positive, e.g., 0.02 for 2%)
        half_kelly : bool (default True)

        Returns
        -------
        float : Recommended fraction of portfolio to risk (0 to 1).
                Returns 0 if edge is negative.
        """
        if avg_loss <= 0 or avg_win <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        b = avg_win / avg_loss  # Odds ratio
        p = win_rate
        q = 1 - p

        kelly = (p * b - q) / b
        kelly = max(0.0, kelly)  # No negative sizing

        if half_kelly:
            kelly *= 0.5

        return round(min(kelly, 0.25), 4)  # Cap at 25%

    @staticmethod
    def compute_var(
        returns: pd.Series,
        confidence: float = 0.95,
        horizon: int = 1,
    ) -> dict:
        """
        Compute per-symbol Value at Risk (VaR) and Conditional VaR (CVaR).

        Uses historical simulation -- no distributional assumptions.

        Parameters
        ----------
        returns : pd.Series
            Daily/bar returns (e.g., close.pct_change())
        confidence : float
            Confidence level (default 0.95 = 95%)
        horizon : int
            Holding period in bars (scales VaR by sqrt(horizon))

        Returns
        -------
        dict with:
          - var: VaR as a positive number (max expected loss)
          - cvar: CVaR (expected shortfall -- avg loss beyond VaR)
          - worst: Worst historical return
          - n_obs: Number of observations used
        """
        clean = returns.dropna()
        if len(clean) < 20:
            return {"var": 0.0, "cvar": 0.0, "worst": 0.0, "n_obs": 0}

        sorted_returns = np.sort(clean.values)
        alpha = 1 - confidence
        var_idx = int(np.floor(len(sorted_returns) * alpha))
        var_idx = max(0, min(var_idx, len(sorted_returns) - 1))

        # VaR = loss at the alpha percentile (expressed as positive number)
        var_1bar = abs(float(sorted_returns[var_idx]))

        # CVaR = average of losses beyond VaR
        tail = sorted_returns[:var_idx + 1]
        cvar_1bar = abs(float(tail.mean())) if len(tail) > 0 else var_1bar

        # Scale to horizon
        scale = np.sqrt(max(horizon, 1))
        var_h = var_1bar * scale
        cvar_h = cvar_1bar * scale

        return {
            "var": round(var_h, 6),
            "cvar": round(cvar_h, 6),
            "worst": round(abs(float(sorted_returns[0])), 6),
            "n_obs": len(clean),
        }

    def portfolio_kelly_size(
        self,
        signals: list[dict],
        data: dict[str, pd.DataFrame],
        portfolio_value: float = 10000.0,
        max_total_risk_pct: float = 20.0,
    ) -> list[dict]:
        """
        Portfolio-level position sizing with Kelly + VaR constraints.

        For each signal:
        1. Compute per-symbol VaR from historical returns
        2. Compute Kelly fraction from win rate / avg win/loss
        3. Apply regime-adaptive multiplier
        4. Cap total portfolio risk at max_total_risk_pct

        Parameters
        ----------
        signals : list[dict]
            Each dict must have: symbol, confidence, and optionally
            win_rate, avg_win_pct, avg_loss_pct for Kelly.
        data : dict[str, pd.DataFrame]
            OHLCV data per symbol.
        portfolio_value : float
            Total portfolio value in USD.
        max_total_risk_pct : float
            Maximum total portfolio risk as % (default 20%).

        Returns
        -------
        list[dict] : Signals with added: position_size_pct, position_usd,
                     kelly_fraction, var_95, regime_cell
        """
        # First apply regime-based sizing
        sized = self.size_signals(signals, data)

        # Compute VaR and Kelly for each
        total_risk = 0.0
        for sig in sized:
            symbol = sig.get("symbol", "")
            df = data.get(symbol)

            # Compute VaR
            if df is not None and len(df) > 30:
                close = df.get("close", df.get("Close"))
                if close is not None:
                    returns = close.pct_change()
                    var_result = self.compute_var(returns)
                    sig["var_95"] = var_result["var"]
                    sig["cvar_95"] = var_result["cvar"]
                else:
                    sig["var_95"] = 0.0
                    sig["cvar_95"] = 0.0
            else:
                sig["var_95"] = 0.0
                sig["cvar_95"] = 0.0

            # Compute Kelly if performance data available
            wr = sig.get("win_rate", 0.55)
            avg_win = sig.get("avg_win_pct", 0.03)
            avg_loss = sig.get("avg_loss_pct", 0.02)
            kelly = self.kelly_fraction(wr, avg_win, avg_loss)
            sig["kelly_fraction"] = kelly

            # Blend Kelly with regime size: take the more conservative
            regime_size = sig.get("position_size_pct", self.base_risk_pct)
            kelly_size = kelly * 100  # Convert to percentage

            if kelly_size > 0:
                # Use average of regime and Kelly (conservative blend)
                blended = (regime_size + kelly_size) / 2
            else:
                blended = regime_size

            sig["position_size_pct"] = round(min(blended, self.max_risk_pct), 2)
            sig["position_usd"] = round(portfolio_value * sig["position_size_pct"] / 100, 2)

            total_risk += sig["position_size_pct"]

        # Cap total portfolio risk
        if total_risk > max_total_risk_pct and total_risk > 0:
            scale = max_total_risk_pct / total_risk
            for sig in sized:
                sig["position_size_pct"] = round(sig["position_size_pct"] * scale, 2)
                sig["position_usd"] = round(portfolio_value * sig["position_size_pct"] / 100, 2)
            sized[0]["total_risk_capped"] = True

        return sized

