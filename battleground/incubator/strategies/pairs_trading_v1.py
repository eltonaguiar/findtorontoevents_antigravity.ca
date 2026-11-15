#!/usr/bin/env python3
"""
Cointegrated Pairs Trading Strategy v1
=======================================

Created by: claude_code
Date: 2026-03-13

Strategy Logic (Engle-Granger two-step method):
1. Fetch 30 days of 1h klines from Binance for BTC, ETH, SOL (public API)
2. Test all pair combinations for cointegration:
   - OLS regression: Y = beta * X + residual
   - ADF test on residuals (Dickey-Fuller t-stat < -2.86 => cointegrated at 5%)
3. For cointegrated pairs, compute rolling z-score of the spread
4. Generate signals:
   - LONG_SPREAD  when z < -2.0 (spread undervalued: buy Y, sell X)
   - SHORT_SPREAD when z >  2.0 (spread overvalued:  sell Y, buy X)
   - EXIT         when z crosses back through 0

Research basis:
- 37 of 90 crypto pairs show cointegration (2025 Journal of Futures Markets)
- BTC/ETH pair yields Sharpe 1.5-2.5 historically
- Engle & Granger (1987), "Co-Integration and Error Correction"

Dependencies: numpy, requests (no statsmodels, no scipy)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
PAIR_COMBINATIONS = [
    ("BTCUSDT", "ETHUSDT"),
    ("BTCUSDT", "SOLUSDT"),
    ("ETHUSDT", "SOLUSDT"),
]

# Pair display names (Y/X convention: Y = dependent, X = independent)
PAIR_NAMES = {
    ("BTCUSDT", "ETHUSDT"): "BTC/ETH",
    ("BTCUSDT", "SOLUSDT"): "BTC/SOL",
    ("ETHUSDT", "SOLUSDT"): "ETH/SOL",
}

# Binance public API
from api_helpers import BINANCE_KLINES_ENDPOINTS

# Strategy parameters
TIMEFRAME = "1h"
LOOKBACK_DAYS = 30
MIN_DATA_POINTS = 720          # 30 days * 24 hours
ZSCORE_WINDOW = 20             # rolling window for z-score (20 periods = ~1 day)
ZSCORE_ENTRY = 2.0             # entry threshold
ZSCORE_EXIT = 0.0              # exit threshold
ADF_CRITICAL_5PCT = -2.86      # Dickey-Fuller 5% critical value (n > 500)
COINT_PVALUE_THRESHOLD = 0.05  # significance level

# Output path
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "pairs_cointegration.json"


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class CointegrationResult:
    """Result of an Engle-Granger cointegration test."""
    pair_name: str
    symbol_x: str          # independent variable
    symbol_y: str          # dependent variable
    beta: float            # hedge ratio (OLS slope)
    alpha: float           # OLS intercept
    adf_tstat: float       # Dickey-Fuller t-statistic on residuals
    adf_critical: float    # critical value used
    is_cointegrated: bool  # t-stat < critical value
    residual_mean: float
    residual_std: float
    n_observations: int
    half_life: float       # mean-reversion half-life in periods


@dataclass
class PairsSignal:
    """A pairs trading signal."""
    symbol: str            # pair name, e.g. "BTC/ETH"
    direction: str         # "LONG_SPREAD" or "SHORT_SPREAD"
    entry_zscore: float
    current_zscore: float
    beta: float            # hedge ratio
    confidence: float
    strategy: str = "pairs_cointegration_v1"
    legs: List[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── Core Strategy ────────────────────────────────────────────────────

class PairsTradingStrategy:
    """
    Cointegrated pairs trading using Engle-Granger method.

    Tests crypto pairs for cointegration, then generates mean-reversion
    signals based on z-score of the spread.
    """

    def __init__(
        self,
        symbols: List[str] = None,
        pairs: List[Tuple[str, str]] = None,
        lookback_days: int = LOOKBACK_DAYS,
        zscore_window: int = ZSCORE_WINDOW,
        zscore_entry: float = ZSCORE_ENTRY,
        zscore_exit: float = ZSCORE_EXIT,
        request_timeout: int = 15,
    ):
        self.symbols = symbols or SYMBOLS
        self.pairs = pairs or PAIR_COMBINATIONS
        self.lookback_days = lookback_days
        self.zscore_window = zscore_window
        self.zscore_entry = zscore_entry
        self.zscore_exit = zscore_exit
        self._request_timeout = request_timeout
        self._price_cache: Dict[str, np.ndarray] = {}

    def generate_signals(self) -> List[PairsSignal]:
        """
        Main entry point: fetch data, test cointegration, generate signals.
        Returns list of PairsSignal for any cointegrated pair with active z-score breach.
        """
        if requests is None:
            logger.error("requests library not available")
            return []

        # 1. Fetch price data for all symbols
        logger.info("Fetching %dh klines for %d symbols...", self.lookback_days * 24, len(self.symbols))
        for symbol in self.symbols:
            prices = self._fetch_klines(symbol)
            if prices is not None and len(prices) >= MIN_DATA_POINTS:
                self._price_cache[symbol] = prices
                logger.info("  %s: %d data points fetched", symbol, len(prices))
            else:
                count = len(prices) if prices is not None else 0
                logger.warning("  %s: insufficient data (%d < %d)", symbol, count, MIN_DATA_POINTS)

        # 2. Test each pair for cointegration and generate signals
        signals = []
        self._coint_results = []

        for sym_x, sym_y in self.pairs:
            if sym_x not in self._price_cache or sym_y not in self._price_cache:
                logger.warning("Skipping %s/%s: missing price data", sym_x, sym_y)
                continue

            prices_x = self._price_cache[sym_x]
            prices_y = self._price_cache[sym_y]

            # Align lengths
            n = min(len(prices_x), len(prices_y))
            px = prices_x[-n:]
            py = prices_y[-n:]

            pair_name = PAIR_NAMES.get((sym_x, sym_y), f"{sym_x}/{sym_y}")

            # 2a. Cointegration test
            coint = self._test_cointegration(px, py, sym_x, sym_y, pair_name)
            self._coint_results.append(coint)

            if not coint.is_cointegrated:
                logger.info("%s: NOT cointegrated (ADF t=%.3f, critical=%.3f)",
                            pair_name, coint.adf_tstat, coint.adf_critical)
                continue

            logger.info("%s: COINTEGRATED (ADF t=%.3f < %.3f, beta=%.4f, half-life=%.1f periods)",
                        pair_name, coint.adf_tstat, coint.adf_critical, coint.beta, coint.half_life)

            # 2b. Generate z-score signal
            signal = self._generate_zscore_signal(px, py, coint, sym_x, sym_y, pair_name)
            if signal is not None:
                signals.append(signal)

        return signals

    # ── Cointegration Testing ────────────────────────────────────────

    def _test_cointegration(
        self,
        prices_x: np.ndarray,
        prices_y: np.ndarray,
        sym_x: str,
        sym_y: str,
        pair_name: str,
    ) -> CointegrationResult:
        """
        Engle-Granger two-step cointegration test.

        Step 1: OLS regression  Y = alpha + beta * X + epsilon
        Step 2: ADF test on residuals epsilon
        """
        n = len(prices_x)

        # Step 1: OLS regression (numpy, no statsmodels)
        # beta = cov(X, Y) / var(X)
        # alpha = mean(Y) - beta * mean(X)
        mean_x = np.mean(prices_x)
        mean_y = np.mean(prices_y)
        cov_xy = np.mean((prices_x - mean_x) * (prices_y - mean_y))
        var_x = np.mean((prices_x - mean_x) ** 2)

        if var_x < 1e-12:
            # Degenerate case
            return CointegrationResult(
                pair_name=pair_name, symbol_x=sym_x, symbol_y=sym_y,
                beta=0.0, alpha=0.0, adf_tstat=0.0, adf_critical=ADF_CRITICAL_5PCT,
                is_cointegrated=False, residual_mean=0.0, residual_std=0.0,
                n_observations=n, half_life=float("inf"),
            )

        beta = cov_xy / var_x
        alpha = mean_y - beta * mean_x
        residuals = prices_y - (alpha + beta * prices_x)

        # Step 2: ADF test on residuals
        # Dickey-Fuller: regress diff(residuals) on lagged residuals
        # delta_e(t) = gamma * e(t-1) + noise
        # t-stat of gamma: if < -2.86, reject unit root at 5%
        adf_tstat = self._adf_test(residuals)

        is_cointegrated = adf_tstat < ADF_CRITICAL_5PCT

        # Half-life of mean reversion: -ln(2) / ln(1 + gamma)
        # where gamma is the ADF regression coefficient
        gamma = self._adf_gamma(residuals)
        if gamma < 0 and abs(1 + gamma) > 1e-10:
            half_life = -np.log(2) / np.log(1 + gamma)
        else:
            half_life = float("inf")

        return CointegrationResult(
            pair_name=pair_name,
            symbol_x=sym_x,
            symbol_y=sym_y,
            beta=float(beta),
            alpha=float(alpha),
            adf_tstat=float(adf_tstat),
            adf_critical=ADF_CRITICAL_5PCT,
            is_cointegrated=is_cointegrated,
            residual_mean=float(np.mean(residuals)),
            residual_std=float(np.std(residuals)),
            n_observations=n,
            half_life=float(half_life),
        )

    def _adf_test(self, residuals: np.ndarray) -> float:
        """
        Augmented Dickey-Fuller test (simplified, no lags).

        Regress: delta_e(t) = gamma * e(t-1) + u(t)
        Return: t-statistic of gamma
        """
        gamma, t_stat = self._dickey_fuller_regression(residuals)
        return t_stat

    def _adf_gamma(self, residuals: np.ndarray) -> float:
        """Return the gamma coefficient from the DF regression."""
        gamma, _ = self._dickey_fuller_regression(residuals)
        return gamma

    def _dickey_fuller_regression(self, residuals: np.ndarray) -> Tuple[float, float]:
        """
        Core Dickey-Fuller regression.

        delta_e(t) = gamma * e(t-1) + u(t)

        Returns (gamma, t_statistic).
        Uses OLS: gamma = sum(e(t-1) * delta_e(t)) / sum(e(t-1)^2)
        SE(gamma) = sqrt(sigma^2 / sum(e(t-1)^2))
        t = gamma / SE(gamma)
        """
        e_lag = residuals[:-1]       # e(t-1)
        delta_e = np.diff(residuals)  # e(t) - e(t-1)

        n = len(delta_e)
        if n < 2:
            return 0.0, 0.0

        # OLS without intercept: gamma = (e_lag' * delta_e) / (e_lag' * e_lag)
        sum_lag_sq = np.sum(e_lag ** 2)
        if sum_lag_sq < 1e-12:
            return 0.0, 0.0

        gamma = np.sum(e_lag * delta_e) / sum_lag_sq

        # Residuals of the DF regression
        u = delta_e - gamma * e_lag
        sigma_sq = np.sum(u ** 2) / (n - 1)

        # Standard error of gamma
        se_gamma = np.sqrt(sigma_sq / sum_lag_sq)
        if se_gamma < 1e-12:
            return float(gamma), 0.0

        t_stat = gamma / se_gamma
        return float(gamma), float(t_stat)

    # ── Z-Score Signal Generation ────────────────────────────────────

    def _generate_zscore_signal(
        self,
        prices_x: np.ndarray,
        prices_y: np.ndarray,
        coint: CointegrationResult,
        sym_x: str,
        sym_y: str,
        pair_name: str,
    ) -> Optional[PairsSignal]:
        """
        Compute rolling z-score of the spread and generate signal if threshold breached.
        """
        # Compute spread: Y - beta * X - alpha
        spread = prices_y - (coint.alpha + coint.beta * prices_x)

        if len(spread) < self.zscore_window:
            logger.warning("%s: spread too short for z-score window", pair_name)
            return None

        # Rolling z-score over last zscore_window periods
        rolling_mean = np.mean(spread[-self.zscore_window:])
        rolling_std = np.std(spread[-self.zscore_window:])

        if rolling_std < 1e-12:
            logger.warning("%s: zero spread variance", pair_name)
            return None

        current_spread = spread[-1]
        current_zscore = (current_spread - rolling_mean) / rolling_std

        # Also compute full z-score series for the last 100 bars (for metadata)
        lookback = min(100, len(spread) - self.zscore_window)
        zscore_series = []
        for i in range(lookback):
            idx = len(spread) - lookback + i
            window_start = idx - self.zscore_window
            if window_start < 0:
                continue
            w_mean = np.mean(spread[window_start:idx])
            w_std = np.std(spread[window_start:idx])
            if w_std > 1e-12:
                zscore_series.append(float((spread[idx] - w_mean) / w_std))

        # Check for signal
        direction = None
        if current_zscore < -self.zscore_entry:
            # Spread is too cheap: buy Y, sell X
            direction = "LONG_SPREAD"
        elif current_zscore > self.zscore_entry:
            # Spread is too expensive: sell Y, buy X
            direction = "SHORT_SPREAD"
        else:
            logger.info("%s: z-score=%.3f (within +/-%.1f band, no signal)",
                        pair_name, current_zscore, self.zscore_entry)
            return None

        # Confidence scoring
        # Factors: strength of cointegration, z-score magnitude, half-life
        adf_strength = min(abs(coint.adf_tstat) / 4.0, 1.0)  # normalize (-4 is very strong)
        zscore_strength = min(abs(current_zscore) / 3.0, 1.0)  # stronger z = more confident
        halflife_score = 1.0 if coint.half_life < 50 else max(0.3, 1.0 - (coint.half_life - 50) / 200)

        confidence = round(
            0.35 * adf_strength + 0.35 * zscore_strength + 0.30 * halflife_score,
            4,
        )
        confidence = max(0.30, min(confidence, 0.95))

        # Build legs
        # Convention: Y is dependent, X is independent
        # LONG_SPREAD  = buy Y, sell X (weight for X = 1/beta to dollar-neutralize)
        # SHORT_SPREAD = sell Y, buy X
        inverse_beta = abs(1.0 / coint.beta) if abs(coint.beta) > 1e-10 else 0.0

        if direction == "LONG_SPREAD":
            legs = [
                {"symbol": sym_y, "direction": "LONG", "weight": 1.0},
                {"symbol": sym_x, "direction": "SHORT", "weight": round(inverse_beta, 6)},
            ]
        else:
            legs = [
                {"symbol": sym_y, "direction": "SHORT", "weight": 1.0},
                {"symbol": sym_x, "direction": "LONG", "weight": round(inverse_beta, 6)},
            ]

        # Current prices for reference
        price_x = float(prices_x[-1])
        price_y = float(prices_y[-1])

        logger.info("%s SIGNAL: %s | z=%.3f | beta=%.4f | conf=%.4f | half-life=%.1f",
                    pair_name, direction, current_zscore, coint.beta, confidence, coint.half_life)

        return PairsSignal(
            symbol=pair_name,
            direction=direction,
            entry_zscore=round(float(current_zscore), 4),
            current_zscore=round(float(current_zscore), 4),
            beta=round(coint.beta, 6),
            confidence=confidence,
            legs=legs,
            metadata={
                "adf_tstat": round(coint.adf_tstat, 4),
                "adf_critical": coint.adf_critical,
                "alpha": round(coint.alpha, 4),
                "half_life_periods": round(coint.half_life, 1),
                "half_life_hours": round(coint.half_life, 1),  # 1h timeframe
                "spread_mean": round(float(rolling_mean), 4),
                "spread_std": round(float(rolling_std), 4),
                "current_spread": round(float(current_spread), 4),
                "n_observations": coint.n_observations,
                "price_x": price_x,
                "price_y": price_y,
                "symbol_x": sym_x,
                "symbol_y": sym_y,
                "zscore_entry_threshold": self.zscore_entry,
                "zscore_exit_threshold": self.zscore_exit,
                "zscore_window": self.zscore_window,
                "recent_zscore_min": round(min(zscore_series[-20:]) if len(zscore_series) >= 20 else min(zscore_series or [0]), 4),
                "recent_zscore_max": round(max(zscore_series[-20:]) if len(zscore_series) >= 20 else max(zscore_series or [0]), 4),
                "timeframe": TIMEFRAME,
                "lookback_days": self.lookback_days,
            },
        )

    # ── Binance API ──────────────────────────────────────────────────

    def _fetch_klines(self, symbol: str) -> Optional[np.ndarray]:
        """
        Fetch 1h klines from Binance spot API (public, no key needed).

        Returns numpy array of close prices, or None on failure.
        Fetches in chunks of 1000 (Binance max) if needed.
        """
        all_closes = []
        total_needed = self.lookback_days * 24  # 1h candles
        end_time = int(time.time() * 1000)  # now in milliseconds
        start_time = end_time - (self.lookback_days * 24 * 60 * 60 * 1000)

        current_start = start_time

        while current_start < end_time:
            params = {
                "symbol": symbol,
                "interval": TIMEFRAME,
                "startTime": current_start,
                "endTime": end_time,
                "limit": 1000,
            }
            klines = None
            for endpoint in BINANCE_KLINES_ENDPOINTS:
                try:
                    resp = requests.get(
                        endpoint,
                        params=params,
                        timeout=self._request_timeout,
                    )
                    if resp.status_code == 451:
                        logger.debug("Geo-blocked at %s, trying next", endpoint)
                        continue
                    resp.raise_for_status()
                    klines = resp.json()
                    if isinstance(klines, list) and len(klines) > 0:
                        break
                    klines = None
                except Exception as e:
                    logger.debug("Klines endpoint %s failed for %s: %s", endpoint, symbol, e)
                    continue

            if not klines or not isinstance(klines, list) or len(klines) == 0:
                break

            for k in klines:
                # kline format: [open_time, open, high, low, close, volume, ...]
                all_closes.append(float(k[4]))  # close price

            # Move start to after last candle
            last_open_time = int(klines[-1][0])
            current_start = last_open_time + 1

            # Rate limiting
            if current_start < end_time:
                time.sleep(0.2)

        if len(all_closes) == 0:
            return None

        return np.array(all_closes, dtype=np.float64)

    # ── Results Serialization ────────────────────────────────────────

    def save_results(
        self,
        signals: List[PairsSignal],
        coint_results: List[CointegrationResult] = None,
    ) -> str:
        """Save cointegration test results and signals to JSON."""
        if coint_results is None:
            coint_results = getattr(self, "_coint_results", [])

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": "pairs_cointegration_v1",
            "parameters": {
                "timeframe": TIMEFRAME,
                "lookback_days": self.lookback_days,
                "zscore_window": self.zscore_window,
                "zscore_entry": self.zscore_entry,
                "zscore_exit": self.zscore_exit,
                "adf_critical_5pct": ADF_CRITICAL_5PCT,
                "min_data_points": MIN_DATA_POINTS,
            },
            "cointegration_tests": [
                {
                    "pair": c.pair_name,
                    "symbol_x": c.symbol_x,
                    "symbol_y": c.symbol_y,
                    "beta": round(c.beta, 6),
                    "alpha": round(c.alpha, 4),
                    "adf_tstat": round(c.adf_tstat, 4),
                    "adf_critical": c.adf_critical,
                    "is_cointegrated": c.is_cointegrated,
                    "residual_mean": round(c.residual_mean, 6),
                    "residual_std": round(c.residual_std, 6),
                    "n_observations": c.n_observations,
                    "half_life_periods": round(c.half_life, 1),
                }
                for c in coint_results
            ],
            "active_signals": [
                {
                    "symbol": s.symbol,
                    "direction": s.direction,
                    "entry_zscore": s.entry_zscore,
                    "current_zscore": s.current_zscore,
                    "beta": s.beta,
                    "confidence": s.confidence,
                    "strategy": s.strategy,
                    "legs": s.legs,
                    "metadata": s.metadata,
                }
                for s in signals
            ],
            "summary": {
                "pairs_tested": len(coint_results),
                "pairs_cointegrated": sum(1 for c in coint_results if c.is_cointegrated),
                "active_signals": len(signals),
            },
        }

        # Ensure output directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_FILE)

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info("Results saved to %s", output_path)
        return output_path


# ── Standalone Runner ────────────────────────────────────────────────

def main():
    """Run the pairs cointegration scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = PairsTradingStrategy()
    signals = strategy.generate_signals()
    coint_results = getattr(strategy, "_coint_results", [])

    print(f"\n{'='*72}")
    print(f"  COINTEGRATED PAIRS SCANNER  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*72}")

    # Print cointegration test results
    print(f"\n  COINTEGRATION TESTS ({len(coint_results)} pairs)")
    print(f"  {'-'*66}")
    print(f"  {'Pair':<12} {'Beta':>10} {'ADF t-stat':>12} {'Critical':>10} {'Coint?':>8} {'Half-life':>10}")
    print(f"  {'-'*66}")

    for c in coint_results:
        hl_str = f"{c.half_life:.1f}h" if c.half_life < 1000 else "inf"
        coint_marker = "YES ***" if c.is_cointegrated else "no"
        print(f"  {c.pair_name:<12} {c.beta:>10.4f} {c.adf_tstat:>12.4f} {c.adf_critical:>10.2f} {coint_marker:>8} {hl_str:>10}")

    cointegrated_count = sum(1 for c in coint_results if c.is_cointegrated)
    print(f"\n  Result: {cointegrated_count}/{len(coint_results)} pairs cointegrated at 5% significance")

    # Print active signals
    if signals:
        print(f"\n  ACTIVE SIGNALS ({len(signals)})")
        print(f"  {'-'*66}")
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}  |  {sig.direction}")
            print(f"  {'-'*40}")
            print(f"  Z-Score:     {sig.current_zscore:+.4f}  (entry at +/-{m['zscore_entry_threshold']:.1f})")
            print(f"  Beta:        {sig.beta:.6f}")
            print(f"  Confidence:  {sig.confidence:.1%}")
            print(f"  Half-life:   {m['half_life_periods']:.1f} hours")
            print(f"  ADF t-stat:  {m['adf_tstat']:.4f}  (critical: {m['adf_critical']:.2f})")
            print(f"  Spread:      {m['current_spread']:.4f}  (mean: {m['spread_mean']:.4f}, std: {m['spread_std']:.4f})")
            print(f"  Prices:      {m['symbol_x']}=${m['price_x']:,.2f}  {m['symbol_y']}=${m['price_y']:,.2f}")
            print(f"  Z range(20): [{m['recent_zscore_min']:+.3f}, {m['recent_zscore_max']:+.3f}]")
            print(f"\n  Legs:")
            for leg in sig.legs:
                print(f"    {leg['direction']:>5} {leg['symbol']:<10} weight={leg['weight']:.6f}")
    else:
        print(f"\n  No active pair trading signals.")
        print(f"  (Z-score within +/-{strategy.zscore_entry:.1f} band for all cointegrated pairs)")

    print(f"\n{'='*72}")
    print(f"  Tested {len(coint_results)} pairs | {cointegrated_count} cointegrated | {len(signals)} active signals")
    print(f"{'='*72}")

    # Save results
    output_path = strategy.save_results(signals)
    print(f"\n  Results saved to: {output_path}\n")

    # Return signals as dicts for pipeline integration
    return [
        {
            "symbol": s.symbol,
            "direction": s.direction,
            "entry_zscore": s.entry_zscore,
            "current_zscore": s.current_zscore,
            "beta": s.beta,
            "confidence": s.confidence,
            "strategy": s.strategy,
            "legs": s.legs,
            "metadata": s.metadata,
        }
        for s in signals
    ]


if __name__ == "__main__":
    main()
