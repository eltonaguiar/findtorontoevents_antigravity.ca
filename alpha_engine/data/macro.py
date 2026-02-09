"""
Macro / Rates Data Loader

Fetches macro indicators: VIX, DXY, Treasury yields, Gold, Oil.
Computes regime classifications for strategy allocation.
"""
import logging
from typing import Dict, Optional
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MacroLoader:
    """Load macro indicators and compute regime classifications."""

    def __init__(self):
        from .. import config
        self.macro_tickers = config.MACRO_TICKERS
        self._cache: Dict[str, pd.Series] = {}

    def load(self, start: str = "2015-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """
        Load all macro indicators into a single DataFrame.

        Columns: VIX, TNX (10Y yield), DXY, GOLD, OIL, SPY
        """
        import yfinance as yf

        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        frames = {}
        for name, ticker in self.macro_tickers.items():
            try:
                df = yf.download(ticker, start=start, end=end, progress=False)
                if not df.empty:
                    if "Adj Close" in df.columns:
                        frames[name] = df["Adj Close"]
                    elif "Close" in df.columns:
                        frames[name] = df["Close"]
            except Exception as e:
                logger.warning(f"Failed to load macro ticker {name} ({ticker}): {e}")

        macro = pd.DataFrame(frames)
        macro.index = pd.to_datetime(macro.index)
        macro = macro.sort_index()

        # Forward-fill macro data (some series don't trade every day)
        macro = macro.ffill()

        self._macro_df = macro
        return macro

    def compute_regimes(self, macro_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Compute market regime classifications.

        Returns DataFrame with columns:
        - vol_regime: low_vol, normal_vol, high_vol, extreme_vol
        - trend_regime: strong_bull, bull, neutral, bear, strong_bear
        - rate_regime: rates_falling, rates_stable, rates_rising
        - dollar_regime: dollar_weak, dollar_neutral, dollar_strong
        - composite_regime: risk_on, neutral, risk_off, crisis
        """
        if macro_df is None:
            macro_df = self.load()

        regimes = pd.DataFrame(index=macro_df.index)

        # ── Volatility Regime (VIX-based) ─────────────────────────────────
        if "VIX" in macro_df.columns:
            vix = macro_df["VIX"]
            regimes["vol_regime"] = pd.cut(
                vix,
                bins=[0, 16, 20, 25, 35, 100],
                labels=["low_vol", "normal_vol", "moderate_vol", "high_vol", "extreme_vol"],
            )
            regimes["vix_zscore"] = (vix - vix.rolling(252).mean()) / vix.rolling(252).std()
            regimes["vix_percentile"] = vix.rolling(252).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
            )

        # ── Trend Regime (SPY moving averages) ────────────────────────────
        if "SPY" in macro_df.columns:
            spy = macro_df["SPY"]
            sma50 = spy.rolling(50).mean()
            sma200 = spy.rolling(200).mean()
            spy_ret_3m = spy.pct_change(63)

            conditions = [
                (spy > sma50) & (sma50 > sma200) & (spy_ret_3m > 0.05),
                (spy > sma200) & (spy_ret_3m > 0),
                (spy > sma200 * 0.98) & (spy < sma200 * 1.02),
                (spy < sma200) & (spy_ret_3m < 0),
                (spy < sma50) & (sma50 < sma200) & (spy_ret_3m < -0.05),
            ]
            choices = ["strong_bull", "bull", "neutral", "bear", "strong_bear"]
            regimes["trend_regime"] = np.select(conditions, choices, default="neutral")

            # Breadth: SPY distance from 200 SMA
            regimes["spy_sma200_dist"] = (spy - sma200) / sma200

        # ── Rate Regime (10Y Treasury) ────────────────────────────────────
        if "TNX" in macro_df.columns:
            tnx = macro_df["TNX"]
            tnx_sma50 = tnx.rolling(50).mean()
            tnx_change_3m = tnx.diff(63)

            conditions = [
                tnx_change_3m < -0.5,
                (tnx_change_3m >= -0.5) & (tnx_change_3m <= 0.5),
                tnx_change_3m > 0.5,
            ]
            choices = ["rates_falling", "rates_stable", "rates_rising"]
            regimes["rate_regime"] = np.select(conditions, choices, default="rates_stable")

            # Yield curve proxy: 10Y level
            regimes["tnx_level"] = tnx

        # ── Dollar Regime (DXY) ───────────────────────────────────────────
        if "DXY" in macro_df.columns:
            dxy = macro_df["DXY"]
            dxy_sma50 = dxy.rolling(50).mean()
            dxy_pct_above = (dxy - dxy_sma50) / dxy_sma50

            conditions = [
                dxy_pct_above < -0.02,
                (dxy_pct_above >= -0.02) & (dxy_pct_above <= 0.02),
                dxy_pct_above > 0.02,
            ]
            choices = ["dollar_weak", "dollar_neutral", "dollar_strong"]
            regimes["dollar_regime"] = np.select(conditions, choices, default="dollar_neutral")
            regimes["dxy_sma50_dist"] = dxy_pct_above

        # ── Composite Regime ──────────────────────────────────────────────
        regimes["composite_regime"] = self._compute_composite_regime(regimes)

        return regimes

    def _compute_composite_regime(self, regimes: pd.DataFrame) -> pd.Series:
        """
        Combine individual regime signals into a composite.
        crisis > risk_off > neutral > risk_on
        """
        score = pd.Series(0.0, index=regimes.index)

        # Vol contribution
        if "vol_regime" in regimes.columns:
            vol_map = {"low_vol": 2, "normal_vol": 1, "moderate_vol": 0, "high_vol": -1, "extreme_vol": -2}
            score += regimes["vol_regime"].map(vol_map).fillna(0)

        # Trend contribution
        if "trend_regime" in regimes.columns:
            trend_map = {"strong_bull": 2, "bull": 1, "neutral": 0, "bear": -1, "strong_bear": -2}
            score += regimes["trend_regime"].map(trend_map).fillna(0)

        # Rate contribution (rising rates = slight negative for growth)
        if "rate_regime" in regimes.columns:
            rate_map = {"rates_falling": 1, "rates_stable": 0, "rates_rising": -1}
            score += regimes["rate_regime"].map(rate_map).fillna(0)

        # Classify composite
        conditions = [score >= 3, (score >= 0) & (score < 3), (score >= -2) & (score < 0), score < -2]
        choices = ["risk_on", "neutral", "risk_off", "crisis"]
        return pd.Series(np.select(conditions, choices, default="neutral"), index=regimes.index)

    def get_current_regime(self) -> Dict:
        """Get the current (most recent) regime classification."""
        macro = self.load()
        regimes = self.compute_regimes(macro)
        latest = regimes.iloc[-1].to_dict()
        latest["date"] = str(regimes.index[-1].date())

        # Add raw macro values
        macro_latest = macro.iloc[-1].to_dict()
        latest.update({f"raw_{k}": v for k, v in macro_latest.items()})

        return latest

    def get_factor_weights_for_regime(self, regime: str) -> Dict[str, float]:
        """
        Get recommended factor weights based on current regime.
        This implements the "mode switching" from the God-Mode spec.
        """
        regime_weights = {
            "risk_on": {
                "momentum": 0.30, "growth": 0.25, "quality": 0.10,
                "value": 0.05, "mean_reversion": 0.05, "volatility": 0.05,
                "earnings": 0.10, "sentiment": 0.10,
            },
            "neutral": {
                "momentum": 0.20, "growth": 0.15, "quality": 0.20,
                "value": 0.15, "mean_reversion": 0.10, "volatility": 0.05,
                "earnings": 0.10, "sentiment": 0.05,
            },
            "risk_off": {
                "momentum": 0.05, "growth": 0.05, "quality": 0.30,
                "value": 0.25, "mean_reversion": 0.15, "volatility": 0.10,
                "earnings": 0.05, "sentiment": 0.05,
            },
            "crisis": {
                "momentum": 0.00, "growth": 0.00, "quality": 0.35,
                "value": 0.30, "mean_reversion": 0.20, "volatility": 0.10,
                "earnings": 0.05, "sentiment": 0.00,
            },
        }
        return regime_weights.get(regime, regime_weights["neutral"])
