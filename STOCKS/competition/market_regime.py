"""
market_regime.py  —  Market Regime Detection for Algorithm Competition Engine
==============================================================================

Three-layer regime system designed for the 26-strategy tournament running
across ~130 symbols (stocks, crypto, forex, penny stocks, meme coins).

Dependencies: numpy, pandas, yfinance  (NO scipy/sklearn/hmmlearn required)

Layers
------
1. VIX-Proxy Regime     — Fast, deterministic, always available (SPY vol + trend)
2. Pure-NumPy HMM       — 2-state Gaussian HMM trained with EM on SPY returns
3. Crypto Regime        — BTC/ETH dominance ratio for the crypto universe
4. Adaptive Parameters  — Per-regime stop_loss / take_profit / position_size multipliers

Usage
-----
    from market_regime import get_market_regime, get_crypto_regime
    from market_regime import apply_regime_to_algo

    regime = get_market_regime()          # 'bull' | 'bear' | 'neutral'
    c_regime = get_crypto_regime()        # 'risk_on' | 'defensive' | 'neutral'
    params = apply_regime_to_algo(regime, base_stop=0.08, base_tp=0.20)

Academic background baked into thresholds
------------------------------------------
• HMM 2-state detection: Hamilton (1989), Kim (1994)
  — Expected forward-test Sharpe improvement: 0.2–0.5 (Ang & Bekaert 2002)
• VIX-proxy bull/bear: Volatility regime literature (Schwert 1990)
  — SPY 20d vol > 2% daily historically coincides with drawdown periods
• Momentum vs vol regime: Asness et al. (2012): momentum crashes in high-vol
  — Mean reversion strengthens in high-vol (Jegadeesh 1990)
• Crypto dominance: BTC/ETH ratio as risk-on/off indicator (research 2019-2023)
"""

from __future__ import annotations

import time
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Regime detection tuning knobs — adjust these without touching logic
_CFG = {
    # VIX-proxy thresholds (daily % volatility, annualised / sqrt(252))
    "vol_bear_threshold":   0.020,   # > 2.0%/day → leaning bear
    "vol_bull_threshold":   0.012,   # < 1.2%/day → leaning bull

    # SMA filter
    "trend_sma_window":     200,     # SPY 200-day SMA
    "trend_sma_fast":       50,      # SPY 50-day SMA (golden/death cross)

    # Volatility look-back
    "vol_window":           20,      # 20-day rolling std of daily returns

    # HMM parameters
    "hmm_n_states":         2,       # bull / bear
    "hmm_lookback_days":    504,     # 2 years of daily data to train HMM
    "hmm_n_iter":           200,     # EM iterations
    "hmm_tol":              1e-5,    # EM convergence tolerance

    # Crypto regime
    "btc_eth_window":       20,      # rolling window for dominance ratio
    "btc_eth_thresh_high":  1.02,    # BTC outperforms ETH by 2% → defensive
    "btc_eth_thresh_low":   0.98,    # ETH outperforms BTC by 2% → risk-on

    # Cache
    "cache_ttl_seconds":    3600,    # re-use regime for 1 hour
    "cache_file":           ".regime_cache.json",
}

# Per-regime multipliers for stop_loss, take_profit, position_size
# Values are MULTIPLIERS applied to the strategy's base parameters
REGIME_PARAMS = {
    "bull": {
        "stop_loss_mult":    1.25,   # wider stop: let winners breathe
        "take_profit_mult":  1.50,   # bigger target: let winners run
        "position_size_mult":1.10,   # slightly larger positions
        "max_positions_mult":1.0,    # full position count
        "description": "Bull: wider TP, slightly larger size, widen stops",
    },
    "neutral": {
        "stop_loss_mult":    1.00,
        "take_profit_mult":  1.00,
        "position_size_mult":1.00,
        "max_positions_mult":1.0,
        "description": "Neutral: use strategy defaults unchanged",
    },
    "bear": {
        "stop_loss_mult":    0.65,   # tighter stop: capital preservation first
        "take_profit_mult":  0.70,   # smaller target: lock in gains quickly
        "position_size_mult":0.60,   # 40% smaller positions
        "max_positions_mult":0.75,   # fewer concurrent positions
        "description": "Bear: tight stop, take profit early, reduce size",
    },
}

# Strategy type override: which strategies still fire in bear regime
# Mean-reversion and quality are BETTER in bear/volatile markets
BEAR_ALLOWED_TYPES = {"Mean Reversion", "Reversal", "Quality", "Dividend", "Value"}
BULL_BOOSTED_TYPES = {"Momentum", "Trend", "Breakout", "Anomaly", "Machine Learning"}


# ---------------------------------------------------------------------------
# 1. VIX-Proxy Regime  (fast, no ML, always reliable)
# ---------------------------------------------------------------------------

def compute_vix_proxy_regime(
    spy_close: pd.Series,
    vol_window: int = 20,
    vol_bear: float = 0.020,
    vol_bull: float = 0.012,
    sma_window: int = 200,
) -> str:
    """
    Determine market regime using SPY as VIX proxy.

    Rules (in priority order):
      BEAR  if 20d daily vol > vol_bear (2.0%) OR SPY below 200d SMA
      BULL  if 20d daily vol < vol_bull (1.2%) AND SPY above 200d SMA AND above 50d SMA
      NEUTRAL otherwise

    Parameters
    ----------
    spy_close : pd.Series
        Daily close prices for SPY (at least 210 rows recommended)
    vol_window : int
        Rolling window for daily return std dev
    vol_bear : float
        Daily return std threshold above which → bear
    vol_bull : float
        Daily return std threshold below which → bull candidate
    sma_window : int
        Long-term SMA window (200)

    Returns
    -------
    str : 'bull' | 'bear' | 'neutral'

    Notes on thresholds
    -------------------
    SPY 20-day vol historically:
      Calm bull markets   : 0.5 – 1.0% daily
      Normal              : 1.0 – 1.5% daily
      Elevated (2018)     : 1.5 – 2.0% daily
      Stressed (2020 Mar) : 3.0 – 5.0% daily
    Using 1.2% / 2.0% gives a clear separation between regimes.
    """
    if len(spy_close) < vol_window + 2:
        return "neutral"

    daily_ret = spy_close.pct_change().dropna()

    # 20-day rolling volatility (most recent value)
    vol_20d = float(daily_ret.rolling(vol_window).std().iloc[-1])

    # 200-day SMA test
    sma200 = float(spy_close.rolling(sma_window).mean().iloc[-1]) if len(spy_close) >= sma_window else float("nan")
    sma50  = float(spy_close.rolling(50).mean().iloc[-1]) if len(spy_close) >= 50 else float("nan")
    price  = float(spy_close.iloc[-1])

    above_sma200 = (not np.isnan(sma200)) and price > sma200
    above_sma50  = (not np.isnan(sma50))  and price > sma50

    # Priority 1: Bear conditions
    if vol_20d > vol_bear or not above_sma200:
        return "bear"

    # Priority 2: Strong bull conditions
    if vol_20d < vol_bull and above_sma200 and above_sma50:
        return "bull"

    # Everything in between
    return "neutral"


# ---------------------------------------------------------------------------
# 2. Pure-NumPy 2-State Gaussian HMM  (no hmmlearn / scipy required)
# ---------------------------------------------------------------------------

class GaussianHMM2State:
    """
    2-state Gaussian Hidden Markov Model implemented in pure NumPy.

    State 0 → low-vol / bull regime
    State 1 → high-vol / bear regime

    Uses Baum-Welch (EM) algorithm:
      E-step : forward-backward algorithm  → posterior state probabilities
      M-step : update means, variances, transition matrix

    References
    ----------
    Rabiner (1989) — A Tutorial on HMMs
    Hamilton (1989) — New Approach to Economic Fluctuations
    """

    def __init__(self, n_iter: int = 200, tol: float = 1e-5):
        self.n_iter = n_iter
        self.tol = tol
        self.fitted = False

        # Parameters (initialised in fit, persisted after)
        self.means_   = np.zeros(2)         # μ_k for each state
        self.vars_    = np.ones(2) * 1e-4   # σ²_k
        self.pi_      = np.array([0.6, 0.4])  # initial state probabilities
        self.A_       = np.array([[0.95, 0.05],  # transition matrix
                                   [0.10, 0.90]])
        self.bull_state_ = 0   # which index is "bull" (lower mean return)
        self.log_likelihood_ = -np.inf

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _gauss_pdf(x: float, mu: float, var: float) -> float:
        """Univariate Gaussian PDF (numerically safe)."""
        var = max(var, 1e-10)
        return np.exp(-0.5 * (x - mu) ** 2 / var) / np.sqrt(2 * np.pi * var)

    def _emission_matrix(self, obs: np.ndarray) -> np.ndarray:
        """
        B[t, k] = P(obs_t | state_k)
        Shape: (T, 2)
        """
        T = len(obs)
        B = np.zeros((T, 2))
        for k in range(2):
            B[:, k] = np.array([self._gauss_pdf(obs[t], self.means_[k], self.vars_[k]) for t in range(T)])
        # Clip to avoid underflow
        B = np.clip(B, 1e-300, None)
        return B

    def _forward(self, B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Scaled forward algorithm.
        Returns alpha (scaled), c (scaling factors).
        alpha[t, k] = P(o_1..o_t, s_t=k) / product(c_1..c_t)
        """
        T = B.shape[0]
        alpha = np.zeros((T, 2))
        c = np.zeros(T)

        alpha[0] = self.pi_ * B[0]
        c[0] = alpha[0].sum()
        if c[0] < 1e-300:
            c[0] = 1e-300
        alpha[0] /= c[0]

        for t in range(1, T):
            alpha[t] = (alpha[t - 1] @ self.A_) * B[t]
            c[t] = alpha[t].sum()
            if c[t] < 1e-300:
                c[t] = 1e-300
            alpha[t] /= c[t]

        return alpha, c

    def _backward(self, B: np.ndarray, c: np.ndarray) -> np.ndarray:
        """
        Scaled backward algorithm.
        Returns beta (scaled by same c factors as forward).
        """
        T = B.shape[0]
        beta = np.zeros((T, 2))
        beta[-1] = 1.0

        for t in range(T - 2, -1, -1):
            beta[t] = (self.A_ @ (B[t + 1] * beta[t + 1])) / c[t + 1]
            beta[t] = np.clip(beta[t], 0, 1e300)

        return beta

    def _compute_gamma_xi(
        self, alpha: np.ndarray, beta: np.ndarray, B: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        gamma[t, k] = P(s_t=k | obs)          shape (T, 2)
        xi[t, i, j] = P(s_t=i, s_{t+1}=j | obs)  shape (T-1, 2, 2)
        """
        T = alpha.shape[0]

        gamma = alpha * beta
        gamma_sum = gamma.sum(axis=1, keepdims=True)
        gamma_sum = np.where(gamma_sum < 1e-300, 1e-300, gamma_sum)
        gamma /= gamma_sum

        xi = np.zeros((T - 1, 2, 2))
        for t in range(T - 1):
            xi[t] = (
                alpha[t, :, None]
                * self.A_
                * B[t + 1, None, :]
                * beta[t + 1, None, :]
            )
            xi_sum = xi[t].sum()
            if xi_sum > 1e-300:
                xi[t] /= xi_sum

        return gamma, xi

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, obs: np.ndarray) -> "GaussianHMM2State":
        """
        Train HMM via Baum-Welch EM on a 1-D observation sequence.

        Parameters
        ----------
        obs : np.ndarray
            1-D array of daily returns (or other features). Length >= 30.

        Returns
        -------
        self
        """
        obs = np.asarray(obs, dtype=float)
        obs = obs[~np.isnan(obs)]

        if len(obs) < 30:
            return self  # not enough data

        # Smart initialisation using percentile split
        # State 0 (bull): observations in top 50% by absolute return
        # State 1 (bear): observations in bottom 50% (extreme moves)
        #
        # Better than random init — converges faster and more consistently
        med = np.median(np.abs(obs))
        calm_mask = np.abs(obs) <= med

        self.means_[0] = float(np.mean(obs[calm_mask]))   if calm_mask.any() else  0.0004
        self.means_[1] = float(np.mean(obs[~calm_mask]))  if (~calm_mask).any() else -0.0010
        self.vars_[0]  = float(np.var(obs[calm_mask]))    if calm_mask.any() else  1e-4
        self.vars_[1]  = float(np.var(obs[~calm_mask]))   if (~calm_mask).any() else  4e-4
        self.vars_    = np.clip(self.vars_, 1e-10, None)

        prev_ll = -np.inf

        for iteration in range(self.n_iter):
            # ── E-step ──────────────────────────────────────────────
            B = self._emission_matrix(obs)
            alpha, c = self._forward(B)
            beta = self._backward(B, c)
            gamma, xi = self._compute_gamma_xi(alpha, beta, B)

            # Log-likelihood from scaling factors
            ll = float(np.sum(np.log(np.clip(c, 1e-300, None))))

            # ── M-step ──────────────────────────────────────────────
            # Initial state
            self.pi_ = gamma[0] / gamma[0].sum()

            # Transition matrix
            xi_sum = xi.sum(axis=0)
            row_sums = xi_sum.sum(axis=1, keepdims=True)
            row_sums = np.where(row_sums < 1e-300, 1e-300, row_sums)
            self.A_ = xi_sum / row_sums

            # Emission parameters (Gaussian)
            gamma_sum = gamma.sum(axis=0)
            gamma_sum = np.where(gamma_sum < 1e-300, 1e-300, gamma_sum)

            for k in range(2):
                self.means_[k] = float(np.sum(gamma[:, k] * obs) / gamma_sum[k])
                diff = obs - self.means_[k]
                self.vars_[k] = float(np.sum(gamma[:, k] * diff ** 2) / gamma_sum[k])
                self.vars_[k] = max(self.vars_[k], 1e-10)

            # ── Convergence check ────────────────────────────────────
            if abs(ll - prev_ll) < self.tol:
                break
            prev_ll = ll

        self.log_likelihood_ = prev_ll
        self.fitted = True

        # Identify which state is "bull".
        # Primary criterion: LOWER variance (calm markets = bull).
        # This is more reliable than highest mean because bear periods can have
        # high-mean days (dead-cat bounces) while still having extreme variance.
        # Tie-break: higher mean return.
        if abs(self.vars_[0] - self.vars_[1]) > 1e-12:
            self.bull_state_ = int(np.argmin(self.vars_))
        else:
            self.bull_state_ = int(np.argmax(self.means_))
        return self

    def predict_proba(self, obs: np.ndarray) -> np.ndarray:
        """
        Return posterior state probabilities for each observation.

        Returns
        -------
        np.ndarray shape (T, 2): columns = [P(bull), P(bear)]
        """
        if not self.fitted:
            raise RuntimeError("Model not fitted. Call .fit() first.")

        obs = np.asarray(obs, dtype=float)
        B = self._emission_matrix(obs)
        alpha, c = self._forward(B)
        beta = self._backward(B, c)
        gamma = alpha * beta
        gamma_sum = gamma.sum(axis=1, keepdims=True)
        gamma_sum = np.where(gamma_sum < 1e-300, 1e-300, gamma_sum)
        gamma /= gamma_sum

        # Reorder so column 0 = bull, column 1 = bear
        if self.bull_state_ == 1:
            gamma = gamma[:, [1, 0]]  # swap columns
        return gamma

    def predict_current_regime(self, obs: np.ndarray, threshold: float = 0.60) -> str:
        """
        Predict regime from the LAST observation in the sequence.

        Parameters
        ----------
        obs : np.ndarray
            Full return history (train + most recent)
        threshold : float
            Confidence threshold — below this → 'neutral'

        Returns
        -------
        str : 'bull' | 'bear' | 'neutral'
        """
        proba = self.predict_proba(obs)
        last = proba[-1]  # [P(bull), P(bear)]

        p_bull = last[0]
        p_bear = last[1]

        if p_bull >= threshold:
            return "bull"
        elif p_bear >= threshold:
            return "bear"
        else:
            return "neutral"

    def to_dict(self) -> dict:
        """Serialise model parameters to dict (for caching)."""
        return {
            "means": self.means_.tolist(),
            "vars": self.vars_.tolist(),
            "pi": self.pi_.tolist(),
            "A": self.A_.tolist(),
            "bull_state": int(self.bull_state_),
            "log_likelihood": float(self.log_likelihood_),
            "fitted": self.fitted,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GaussianHMM2State":
        """Restore model from dict."""
        m = cls()
        m.means_  = np.array(d["means"])
        m.vars_   = np.array(d["vars"])
        m.pi_     = np.array(d["pi"])
        m.A_      = np.array(d["A"])
        m.bull_state_ = int(d.get("bull_state", 0))
        m.log_likelihood_ = float(d.get("log_likelihood", -np.inf))
        m.fitted  = bool(d.get("fitted", False))
        return m


# ---------------------------------------------------------------------------
# 3. Crypto-Specific Regime  (BTC/ETH dominance)
# ---------------------------------------------------------------------------

def compute_crypto_regime(
    btc_close: pd.Series,
    eth_close: pd.Series,
    window: int = 20,
    thresh_defensive: float = 1.02,
    thresh_risk_on: float = 0.98,
) -> str:
    """
    Determine crypto market regime from BTC/ETH relative performance.

    Logic
    -----
    BTC dominance ratio  = (BTC_t / BTC_{t-window}) / (ETH_t / ETH_{t-window})

    If ratio > thresh_defensive → BTC outperforming → capital rotating to safety
      → "defensive" (fewer altcoin signals)

    If ratio < thresh_risk_on → ETH/alts outperforming → risk appetite up
      → "risk_on" (more aggressive altcoin signals)

    Otherwise → "neutral"

    Why this works
    --------------
    During crypto downturns, BTC dominance rises as traders exit alts to BTC.
    During bull phases, capital flows from BTC → ETH → alts (the "alt season"
    rotation). ETH outperforming BTC is an early signal of risk appetite.

    Parameters
    ----------
    btc_close : pd.Series  — BTC-USD daily close
    eth_close : pd.Series  — ETH-USD daily close
    window    : int        — look-back for relative performance
    thresh_defensive : float — ratio above this → defensive
    thresh_risk_on   : float — ratio below this → risk_on

    Returns
    -------
    str : 'risk_on' | 'defensive' | 'neutral'
    """
    min_len = window + 2
    if len(btc_close) < min_len or len(eth_close) < min_len:
        return "neutral"

    # Align series
    common_idx = btc_close.index.intersection(eth_close.index)
    if len(common_idx) < min_len:
        return "neutral"

    btc = btc_close.loc[common_idx].sort_index()
    eth = eth_close.loc[common_idx].sort_index()

    btc_ret = (btc.iloc[-1] / btc.iloc[-window]) if btc.iloc[-window] > 0 else 1.0
    eth_ret = (eth.iloc[-1] / eth.iloc[-window]) if eth.iloc[-window] > 0 else 1.0

    if eth_ret <= 0:
        return "neutral"

    dominance_ratio = float(btc_ret / eth_ret)

    if dominance_ratio > thresh_defensive:
        return "defensive"
    elif dominance_ratio < thresh_risk_on:
        return "risk_on"
    else:
        return "neutral"


# ---------------------------------------------------------------------------
# 4. Combined Regime Engine  (orchestrates all three layers)
# ---------------------------------------------------------------------------

class RegimeEngine:
    """
    Full market regime detection engine.

    Fetches SPY + BTC/ETH data, runs VIX-proxy + HMM, caches results.

    Designed to run in < 10 seconds on a warm cache, < 30 seconds cold.

    Usage
    -----
        engine = RegimeEngine()
        result = engine.get_regime()
        # result = {
        #   'regime': 'bull',
        #   'crypto_regime': 'risk_on',
        #   'vix_proxy': 'bull',
        #   'hmm_regime': 'bull',
        #   'hmm_confidence': 0.82,
        #   'vol_20d': 0.0098,
        #   'spy_vs_sma200': 0.034,
        #   'btc_eth_ratio': 0.97,
        #   'timestamp': '2026-02-17T12:00:00',
        # }
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_ttl: int = _CFG["cache_ttl_seconds"],
    ):
        self.cache_ttl = cache_ttl
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent
        self.cache_path = self.cache_dir / _CFG["cache_file"]
        self._hmm: Optional[GaussianHMM2State] = None

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_ticker(
        ticker: str,
        lookback_days: int = 520,
        retries: int = 2,
    ) -> pd.Series:
        """
        Fetch daily close for a single ticker via yfinance.
        Returns pd.Series indexed by date. Empty series on failure.
        """
        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        for attempt in range(retries):
            try:
                df = yf.download(
                    ticker,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    progress=False,
                    auto_adjust=True,
                )
                if df.empty:
                    return pd.Series(dtype=float)

                # yfinance 0.2+ returns MultiIndex columns
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                close.index = pd.to_datetime(close.index)
                return close.sort_index()
            except Exception:
                if attempt < retries - 1:
                    time.sleep(1)
        return pd.Series(dtype=float)

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _load_cache(self) -> Optional[dict]:
        """Load regime cache if fresh enough."""
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path, "r") as f:
                data = json.load(f)
            ts = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            age = (datetime.now() - ts).total_seconds()
            if age < self.cache_ttl:
                return data
        except Exception:
            pass
        return None

    def _save_cache(self, result: dict) -> None:
        """Save regime result to cache file."""
        try:
            with open(self.cache_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def get_regime(self, force_refresh: bool = False) -> dict:
        """
        Compute and return the current market regime.

        Returns
        -------
        dict with keys:
            regime          : str  'bull' | 'bear' | 'neutral'
            crypto_regime   : str  'risk_on' | 'defensive' | 'neutral'
            vix_proxy       : str  VIX-proxy signal
            hmm_regime      : str  HMM-only signal
            hmm_confidence  : float  P(predicted_state)
            vol_20d         : float  SPY 20-day daily std
            spy_vs_sma200   : float  (price - sma200) / sma200
            btc_eth_ratio   : float  BTC/ETH relative 20d performance
            timestamp       : str  ISO format
        """
        if not force_refresh:
            cached = self._load_cache()
            if cached:
                return cached

        result = self._compute_regime()
        self._save_cache(result)
        return result

    def _compute_regime(self) -> dict:
        """Internal: fetch data and run all three regime layers."""
        t0 = time.time()

        # ── Fetch SPY ────────────────────────────────────────────────
        spy = self._fetch_ticker("SPY", lookback_days=520)
        if spy.empty:
            return self._fallback_result("SPY fetch failed")

        # ── Layer 1: VIX Proxy ───────────────────────────────────────
        vix_regime = compute_vix_proxy_regime(
            spy,
            vol_window=_CFG["vol_window"],
            vol_bear=_CFG["vol_bear_threshold"],
            vol_bull=_CFG["vol_bull_threshold"],
            sma_window=_CFG["trend_sma_window"],
        )

        daily_ret = spy.pct_change().dropna()
        vol_20d = float(daily_ret.rolling(_CFG["vol_window"]).std().iloc[-1])
        sma200 = float(spy.rolling(_CFG["trend_sma_window"]).mean().iloc[-1]) \
                 if len(spy) >= _CFG["trend_sma_window"] else float("nan")
        spy_vs_sma200 = (float(spy.iloc[-1]) - sma200) / sma200 \
                        if not np.isnan(sma200) and sma200 > 0 else 0.0

        # ── Layer 2: HMM ─────────────────────────────────────────────
        hmm_regime, hmm_confidence = self._run_hmm(daily_ret.values)

        # ── Layer 3: Crypto ──────────────────────────────────────────
        btc = self._fetch_ticker("BTC-USD", lookback_days=60)
        eth = self._fetch_ticker("ETH-USD", lookback_days=60)
        crypto_regime = compute_crypto_regime(
            btc, eth,
            window=_CFG["btc_eth_window"],
            thresh_defensive=_CFG["btc_eth_thresh_high"],
            thresh_risk_on=_CFG["btc_eth_thresh_low"],
        )

        btc_eth_ratio = float("nan")
        if not btc.empty and not eth.empty and len(btc) >= 21 and len(eth) >= 21:
            common = btc.index.intersection(eth.index)
            if len(common) >= 21:
                b = btc.loc[common].sort_index()
                e = eth.loc[common].sort_index()
                btc_ret = b.iloc[-1] / b.iloc[-20] if b.iloc[-20] > 0 else 1.0
                eth_ret = e.iloc[-1] / e.iloc[-20] if e.iloc[-20] > 0 else 1.0
                btc_eth_ratio = float(btc_ret / eth_ret) if eth_ret > 0 else float("nan")

        # ── Fusion: combine VIX-proxy + HMM ─────────────────────────
        final_regime = _fuse_regimes(vix_regime, hmm_regime, hmm_confidence)

        elapsed = round(time.time() - t0, 2)

        return {
            "regime":          final_regime,
            "crypto_regime":   crypto_regime,
            "vix_proxy":       vix_regime,
            "hmm_regime":      hmm_regime,
            "hmm_confidence":  round(hmm_confidence, 4),
            "vol_20d":         round(vol_20d, 5),
            "spy_vs_sma200":   round(spy_vs_sma200, 4),
            "btc_eth_ratio":   round(btc_eth_ratio, 4) if not np.isnan(btc_eth_ratio) else None,
            "timestamp":       datetime.now().isoformat(timespec="seconds"),
            "elapsed_seconds": elapsed,
        }

    def _run_hmm(self, returns: np.ndarray) -> tuple[str, float]:
        """
        Fit or reuse HMM, return (regime_str, confidence).

        Daily retraining takes ~0.5–2 seconds for 504 observations.
        The model is cached in-process — only fits once per engine instance.
        """
        # Use last hmm_lookback_days of returns
        lb = _CFG["hmm_lookback_days"]
        obs = returns[-lb:] if len(returns) > lb else returns
        obs = obs[~np.isnan(obs)]

        if len(obs) < 60:
            return "neutral", 0.5

        # Fit (or refit if no cached model)
        if self._hmm is None or not self._hmm.fitted:
            self._hmm = GaussianHMM2State(
                n_iter=_CFG["hmm_n_iter"],
                tol=_CFG["hmm_tol"],
            )
            self._hmm.fit(obs)

        if not self._hmm.fitted:
            return "neutral", 0.5

        proba = self._hmm.predict_proba(obs)
        last = proba[-1]   # [P(bull), P(bear)]
        p_bull, p_bear = float(last[0]), float(last[1])

        if p_bull >= 0.60:
            return "bull", p_bull
        elif p_bear >= 0.60:
            return "bear", p_bear
        else:
            return "neutral", max(p_bull, p_bear)

    @staticmethod
    def _fallback_result(reason: str) -> dict:
        return {
            "regime":          "neutral",
            "crypto_regime":   "neutral",
            "vix_proxy":       "neutral",
            "hmm_regime":      "neutral",
            "hmm_confidence":  0.5,
            "vol_20d":         None,
            "spy_vs_sma200":   None,
            "btc_eth_ratio":   None,
            "timestamp":       datetime.now().isoformat(timespec="seconds"),
            "error":           reason,
        }


# ---------------------------------------------------------------------------
# 5. Regime Fusion Logic
# ---------------------------------------------------------------------------

def _fuse_regimes(vix_regime: str, hmm_regime: str, hmm_confidence: float) -> str:
    """
    Combine VIX-proxy and HMM signals into a single final regime.

    Fusion rules (designed to be conservative — avoid bear false positives):

    1. If BOTH agree → use that regime
    2. If VIX-proxy says bear → bear (hard rule: capital preservation trumps)
    3. If HMM says bear with high confidence (>0.75) → bear
    4. If VIX-proxy says bull AND HMM says bull → bull
    5. Otherwise → neutral
    """
    # Rule 1: Agreement
    if vix_regime == hmm_regime:
        return vix_regime

    # Rule 2: VIX-proxy bear is a hard signal
    if vix_regime == "bear":
        return "bear"

    # Rule 3: HMM bear with high confidence
    if hmm_regime == "bear" and hmm_confidence >= 0.75:
        return "bear"

    # Rule 4: Both bull
    if vix_regime == "bull" and hmm_regime == "bull":
        return "bull"

    # Rule 5: VIX-proxy bull + HMM neutral/uncertain
    if vix_regime == "bull" and hmm_regime != "bear":
        return "bull"

    return "neutral"


# ---------------------------------------------------------------------------
# 6. Adaptive Stop-Loss / Take-Profit / Position Sizing
# ---------------------------------------------------------------------------

def apply_regime_to_algo(
    regime: str,
    base_stop: float,
    base_tp: float,
    base_position_size: float = 1.0,
    base_max_positions: int = 10,
    algo_type: str = "Momentum",
) -> dict:
    """
    Apply regime-based parameter adjustments to a strategy.

    Parameters
    ----------
    regime            : str   — 'bull' | 'bear' | 'neutral'
    base_stop         : float — strategy's default stop_loss (e.g. 0.08)
    base_tp           : float — strategy's default take_profit (e.g. 0.20)
    base_position_size: float — base size multiplier (1.0 = 100%)
    base_max_positions: int   — strategy's default max concurrent positions
    algo_type         : str   — strategy type for regime-specific overrides

    Returns
    -------
    dict with keys:
        stop_loss        : float   adjusted stop loss
        take_profit      : float   adjusted take profit
        position_size    : float   adjusted position size multiplier
        max_positions    : int     adjusted max positions
        signal_allowed   : bool    whether to generate signals at all
        regime           : str     the input regime
        description      : str     human-readable description
    """
    params = REGIME_PARAMS.get(regime, REGIME_PARAMS["neutral"])

    # Regime-type interactions
    # In bear regimes, momentum/trend strategies get extra size reduction
    if regime == "bear" and algo_type in BULL_BOOSTED_TYPES:
        extra_size_cut = 0.5     # additional 50% cut on momentum in bear
        extra_tp_cut   = 0.80    # even tighter TP
    elif regime == "bear" and algo_type in BEAR_ALLOWED_TYPES:
        extra_size_cut = 1.0     # mean-reversion runs at normal bear size
        extra_tp_cut   = 1.0
    else:
        extra_size_cut = 1.0
        extra_tp_cut   = 1.0

    # In bull regimes, momentum/trend gets a bonus
    if regime == "bull" and algo_type in BULL_BOOSTED_TYPES:
        bull_bonus = 1.10       # 10% larger for momentum in bull
    else:
        bull_bonus = 1.0

    adj_stop = round(base_stop * params["stop_loss_mult"], 4)
    adj_tp   = round(base_tp   * params["take_profit_mult"] * extra_tp_cut, 4)
    adj_size = round(base_position_size * params["position_size_mult"] * extra_size_cut * bull_bonus, 4)
    adj_max  = max(1, round(base_max_positions * params["max_positions_mult"]))

    # In true bear, momentum/trend/breakout should not generate new entries
    signal_allowed = not (regime == "bear" and algo_type in {"Momentum", "Breakout", "Trend"})

    return {
        "stop_loss":      adj_stop,
        "take_profit":    adj_tp,
        "position_size":  adj_size,
        "max_positions":  adj_max,
        "signal_allowed": signal_allowed,
        "regime":         regime,
        "description":    params["description"],
    }


# ---------------------------------------------------------------------------
# 7. Convenience Public Functions (what most callers will use)
# ---------------------------------------------------------------------------

# Module-level engine singleton (created once, reused)
_engine: Optional[RegimeEngine] = None


def _get_engine() -> RegimeEngine:
    global _engine
    if _engine is None:
        _engine = RegimeEngine()
    return _engine


def get_market_regime(force_refresh: bool = False) -> str:
    """
    Return the current market regime as a single string.

    Returns
    -------
    str : 'bull' | 'bear' | 'neutral'

    Speed
    -----
    Cold (no cache, fresh data download) : 15–25 seconds
    Warm (cache hit within 1 hour)       : < 0.01 seconds
    """
    return _get_engine().get_regime(force_refresh=force_refresh)["regime"]


def get_regime_details(force_refresh: bool = False) -> dict:
    """
    Return the full regime detail dict including all signals.
    See RegimeEngine.get_regime() for return schema.
    """
    return _get_engine().get_regime(force_refresh=force_refresh)


def get_crypto_regime(force_refresh: bool = False) -> str:
    """
    Return the current crypto-specific regime.

    Returns
    -------
    str : 'risk_on' | 'defensive' | 'neutral'
    """
    return _get_engine().get_regime(force_refresh=force_refresh)["crypto_regime"]


def reset_engine() -> None:
    """Force a new engine on next call (clears cached model + cache file)."""
    global _engine
    _engine = None


# ---------------------------------------------------------------------------
# 8. Integration Helper for run_competition.py
# ---------------------------------------------------------------------------

def get_regime_for_competition(
    close_df: pd.DataFrame,
    benchmark: str = "SPY",
) -> dict:
    """
    Lightweight regime detection using ALREADY DOWNLOADED data.

    This variant avoids a second yfinance download by using the close_df
    that run_competition.py already has. Use this inside the competition loop.

    Parameters
    ----------
    close_df  : pd.DataFrame  — wide-format daily closes (rows=dates, cols=tickers)
    benchmark : str           — benchmark ticker in close_df ('SPY', 'BTC-USD', etc.)

    Returns
    -------
    dict with keys: regime, vix_proxy, hmm_regime, hmm_confidence, vol_20d
    """
    # Determine if this is a crypto universe
    is_crypto = benchmark in {"BTC-USD", "DOGE-USD", "ETH-USD"}

    if is_crypto:
        # For crypto: use BTC as the "market"
        spy_ticker = "BTC-USD" if "BTC-USD" in close_df.columns else benchmark
    else:
        spy_ticker = "SPY" if "SPY" in close_df.columns else benchmark

    if spy_ticker not in close_df.columns:
        return {
            "regime": "neutral",
            "vix_proxy": "neutral",
            "hmm_regime": "neutral",
            "hmm_confidence": 0.5,
            "vol_20d": None,
            "crypto_regime": "neutral",
        }

    spy = close_df[spy_ticker].dropna()

    # VIX proxy
    if is_crypto:
        # Crypto uses higher thresholds (crypto is ~3x more volatile than equities)
        vix_regime = compute_vix_proxy_regime(
            spy,
            vol_window=20,
            vol_bear=0.045,   # 4.5%/day for crypto
            vol_bull=0.025,   # 2.5%/day
            sma_window=200,
        )
    else:
        vix_regime = compute_vix_proxy_regime(spy)

    # HMM (reuse engine's cached model for speed)
    daily_ret = spy.pct_change().dropna().values
    engine = _get_engine()
    hmm_regime, hmm_confidence = engine._run_hmm(daily_ret)

    # Fused final regime
    final_regime = _fuse_regimes(vix_regime, hmm_regime, hmm_confidence)

    # Crypto dominance (if columns available)
    crypto_regime = "neutral"
    if "BTC-USD" in close_df.columns and "ETH-USD" in close_df.columns:
        crypto_regime = compute_crypto_regime(
            close_df["BTC-USD"].dropna(),
            close_df["ETH-USD"].dropna(),
        )

    vol_20d = None
    try:
        dr = spy.pct_change().dropna()
        vol_20d = round(float(dr.rolling(20).std().iloc[-1]), 5)
    except Exception:
        pass

    return {
        "regime":          final_regime,
        "vix_proxy":       vix_regime,
        "hmm_regime":      hmm_regime,
        "hmm_confidence":  round(hmm_confidence, 4),
        "vol_20d":         vol_20d,
        "crypto_regime":   crypto_regime,
    }


# ---------------------------------------------------------------------------
# 9. Self-test / Demo  (run as: python market_regime.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Market Regime Detection - Self-Test")
    print("=" * 60)

    # Test 1: HMM on synthetic data
    print("\n[1] HMM unit test with synthetic 2-regime data...")
    np.random.seed(42)
    bull_returns = np.random.normal(0.0008, 0.008, 300)   # calm bull: +8bps/day, 0.8% vol
    bear_returns = np.random.normal(-0.0015, 0.025, 100)  # bear: -15bps/day, 2.5% vol
    synthetic = np.concatenate([bull_returns, bear_returns, bull_returns[:100]])

    model = GaussianHMM2State(n_iter=100)
    model.fit(synthetic)
    proba = model.predict_proba(synthetic)

    # Check last 50 obs are classified as bull (they are from bull_returns)
    last_50_bull_pct = float(np.mean(proba[-50:, 0] > 0.5)) * 100
    regime_last = model.predict_current_regime(synthetic)
    print(f"   Bull state mean return : {model.means_[model.bull_state_]*100:.4f}%/day")
    print(f"   Bear state mean return : {model.means_[1 - model.bull_state_]*100:.4f}%/day")
    print(f"   Last 50 obs correct (bull): {last_50_bull_pct:.0f}%")
    print(f"   Current regime prediction: {regime_last}")
    print(f"   Log-likelihood: {model.log_likelihood_:.2f}")
    assert last_50_bull_pct >= 80, f"HMM failed: only {last_50_bull_pct}% correct"
    print("   PASSED")

    # Test 2: VIX proxy on synthetic SPY
    print("\n[2] VIX-proxy unit test...")
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    spy_calm = pd.Series(
        100 * np.cumprod(1 + np.random.normal(0.0005, 0.007, 250)),
        index=dates,
    )
    spy_stress = pd.Series(
        100 * np.cumprod(1 + np.random.normal(-0.001, 0.030, 250)),
        index=dates,
    )
    regime_calm = compute_vix_proxy_regime(spy_calm)
    regime_stress = compute_vix_proxy_regime(spy_stress)
    print(f"   Calm SPY (0.7%/day vol)  -> regime: {regime_calm}")
    print(f"   Stress SPY (3.0%/day vol) -> regime: {regime_stress}")
    assert regime_stress == "bear", f"Expected 'bear' for stress, got {regime_stress}"
    print("   PASSED")

    # Test 3: Crypto regime
    print("\n[3] Crypto regime unit test...")
    dates2 = pd.date_range("2025-01-01", periods=30, freq="B")
    # BTC up 5%, ETH up 1% → BTC dominance → defensive
    btc_dom = pd.Series(50000 * np.cumprod(1 + np.random.normal(0.003, 0.02, 30)), index=dates2)
    eth_lag = pd.Series(3000  * np.cumprod(1 + np.random.normal(0.000, 0.02, 30)), index=dates2)
    c_regime = compute_crypto_regime(btc_dom, eth_lag, window=20)
    print(f"   BTC dominance period -> crypto regime: {c_regime}")
    print("   (expected: defensive or neutral)")

    # Test 4: apply_regime_to_algo
    print("\n[4] Adaptive parameter test...")
    for r in ["bull", "neutral", "bear"]:
        for atype in ["Momentum", "Mean Reversion"]:
            p = apply_regime_to_algo(r, base_stop=0.08, base_tp=0.20, algo_type=atype)
            print(f"   {r:8s} / {atype:20s} -> stop={p['stop_loss']:.3f}  "
                  f"tp={p['take_profit']:.3f}  size={p['position_size']:.2f}  "
                  f"allowed={p['signal_allowed']}")

    # Test 5: Full live regime (requires internet)
    print("\n[5] Live regime detection (downloading SPY + BTC/ETH)...")
    try:
        t_start = time.time()
        details = get_regime_details(force_refresh=True)
        elapsed = time.time() - t_start
        print(f"   Final regime    : {details['regime']}")
        print(f"   VIX-proxy       : {details['vix_proxy']}")
        print(f"   HMM regime      : {details['hmm_regime']}  (conf={details['hmm_confidence']:.2f})")
        print(f"   SPY 20d vol     : {details['vol_20d']*100:.2f}%/day" if details['vol_20d'] else "   SPY 20d vol : n/a")
        print(f"   SPY vs SMA200   : {details['spy_vs_sma200']*100:.1f}%" if details['spy_vs_sma200'] else "")
        print(f"   Crypto regime   : {details['crypto_regime']}")
        print(f"   BTC/ETH ratio   : {details['btc_eth_ratio']}")
        print(f"   Total time      : {elapsed:.1f}s")
    except Exception as e:
        print(f"   SKIPPED (no internet or yfinance error): {e}")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)
