"""
Earnings Data Loader

Tracks earnings surprises, revision momentum, and post-earnings drift (PEAD).
The "Earnings Beat Tracker" identifies stocks with consistent earnings beats.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class EarningsLoader:
    """
    Load earnings data and compute earnings-related signals.
    
    Key signals:
    - Earnings surprise (actual vs estimate)
    - Consecutive beats (3+ quarters of 5%+ beats = "Safe Bet")
    - Post-Earnings Announcement Drift (PEAD)
    - Revision momentum (estimate changes over time)
    """

    def __init__(self):
        from .. import config
        self.beat_threshold = config.EARNINGS_BEAT_THRESHOLD
        self.consecutive_beats_required = config.CONSECUTIVE_BEATS_REQUIRED
        self.pead_window = config.PEAD_DRIFT_WINDOW
        self._cache: Dict[str, pd.DataFrame] = {}

    def load_earnings_history(self, ticker: str) -> pd.DataFrame:
        """
        Load earnings history for a ticker.
        
        Returns DataFrame with columns:
        - date, eps_actual, eps_estimate, surprise_pct, beat
        """
        if ticker in self._cache:
            return self._cache[ticker]

        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)

            # Get earnings dates and history
            earnings = getattr(stock, "earnings_dates", None)
            if earnings is not None and not earnings.empty:
                df = self._parse_yfinance_earnings(earnings)
                self._cache[ticker] = df
                return df

            # Fallback: quarterly earnings from financials
            quarterly = getattr(stock, "quarterly_earnings", None)
            if quarterly is not None and not quarterly.empty:
                df = self._parse_quarterly_earnings(quarterly)
                self._cache[ticker] = df
                return df

        except Exception as e:
            logger.warning(f"Failed to load earnings for {ticker}: {e}")

        return pd.DataFrame(columns=["date", "eps_actual", "eps_estimate", "surprise_pct", "beat"])

    def _parse_yfinance_earnings(self, earnings: pd.DataFrame) -> pd.DataFrame:
        """Parse yfinance earnings_dates format."""
        result = pd.DataFrame()
        result["date"] = earnings.index

        if "Reported EPS" in earnings.columns:
            result["eps_actual"] = earnings["Reported EPS"].values
        elif "reportedEPS" in earnings.columns:
            result["eps_actual"] = earnings["reportedEPS"].values

        if "EPS Estimate" in earnings.columns:
            result["eps_estimate"] = earnings["EPS Estimate"].values
        elif "epsEstimate" in earnings.columns:
            result["eps_estimate"] = earnings["epsEstimate"].values

        if "Surprise(%)" in earnings.columns:
            result["surprise_pct"] = earnings["Surprise(%)"].values / 100.0
        elif "eps_actual" in result.columns and "eps_estimate" in result.columns:
            mask = result["eps_estimate"].abs() > 0.01
            result.loc[mask, "surprise_pct"] = (
                (result.loc[mask, "eps_actual"] - result.loc[mask, "eps_estimate"])
                / result.loc[mask, "eps_estimate"].abs()
            )

        result["beat"] = result.get("surprise_pct", pd.Series(dtype=float)) > self.beat_threshold
        result = result.dropna(subset=["eps_actual"]).sort_values("date")
        return result.reset_index(drop=True)

    def _parse_quarterly_earnings(self, quarterly: pd.DataFrame) -> pd.DataFrame:
        """Parse yfinance quarterly_earnings format."""
        result = pd.DataFrame()
        result["date"] = quarterly.index

        if "Earnings" in quarterly.columns:
            result["eps_actual"] = quarterly["Earnings"].values
        if "Revenue" in quarterly.columns:
            result["revenue"] = quarterly["Revenue"].values

        # No estimate available in this format
        result["eps_estimate"] = np.nan
        result["surprise_pct"] = np.nan
        result["beat"] = False

        return result.sort_values("date").reset_index(drop=True)

    def detect_consecutive_beats(self, tickers: List[str]) -> pd.DataFrame:
        """
        Identify tickers with consecutive earnings beats.
        
        The "Earnings Beat Tracker":
        - 3+ consecutive quarters of 5%+ EPS beats = "Safe Bet" candidate
        
        Returns DataFrame with:
        - ticker, consecutive_beats, avg_surprise, is_safe_bet, beat_streak_quality
        """
        results = []

        for ticker in tickers:
            earnings = self.load_earnings_history(ticker)
            if earnings.empty or "surprise_pct" not in earnings.columns:
                results.append({
                    "ticker": ticker, "consecutive_beats": 0,
                    "avg_surprise": 0.0, "is_safe_bet": False,
                    "beat_streak_quality": 0.0,
                })
                continue

            # Filter to actual reported earnings (not future estimates)
            reported = earnings.dropna(subset=["eps_actual"]).sort_values("date", ascending=False)

            if reported.empty:
                results.append({
                    "ticker": ticker, "consecutive_beats": 0,
                    "avg_surprise": 0.0, "is_safe_bet": False,
                    "beat_streak_quality": 0.0,
                })
                continue

            # Count consecutive beats from most recent
            consecutive = 0
            surprises = []
            for _, row in reported.iterrows():
                surprise = row.get("surprise_pct", 0)
                if pd.notna(surprise) and surprise > self.beat_threshold:
                    consecutive += 1
                    surprises.append(surprise)
                else:
                    break

            avg_surprise = np.mean(surprises) if surprises else 0.0
            is_safe_bet = consecutive >= self.consecutive_beats_required

            # Quality score: longer streak + bigger beats = better
            quality = min(consecutive / self.consecutive_beats_required, 2.0)
            if avg_surprise > 0.10:
                quality *= 1.3
            elif avg_surprise > 0.05:
                quality *= 1.1

            results.append({
                "ticker": ticker,
                "consecutive_beats": consecutive,
                "avg_surprise": avg_surprise,
                "is_safe_bet": is_safe_bet,
                "beat_streak_quality": min(quality, 3.0),
                "total_reported_quarters": len(reported),
            })

        return pd.DataFrame(results).set_index("ticker")

    def compute_pead_signal(
        self,
        tickers: List[str],
        close_prices: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute Post-Earnings Announcement Drift (PEAD) signal.
        
        PEAD: Stocks that beat earnings tend to continue drifting in the direction
        of the surprise for 6-8 weeks. This is one of the most robust anomalies
        in finance.
        
        Returns DataFrame indexed by date x ticker with PEAD signal strength.
        """
        pead_signals = pd.DataFrame(0.0, index=close_prices.index, columns=close_prices.columns)

        for ticker in tickers:
            if ticker not in close_prices.columns:
                continue

            earnings = self.load_earnings_history(ticker)
            if earnings.empty or "surprise_pct" not in earnings.columns:
                continue

            price_series = close_prices[ticker]

            for _, row in earnings.iterrows():
                earn_date = pd.to_datetime(row["date"])
                surprise = row.get("surprise_pct", 0)

                if pd.isna(surprise) or pd.isna(earn_date):
                    continue

                # Create PEAD window: signal active for pead_window days after earnings
                drift_start = earn_date
                drift_end = earn_date + timedelta(days=self.pead_window)

                mask = (pead_signals.index >= drift_start) & (pead_signals.index <= drift_end)

                if mask.any():
                    # Signal strength decays over the window
                    days_since = (pead_signals.index[mask] - drift_start).days
                    decay = 1.0 - (days_since / self.pead_window)
                    signal = surprise * decay
                    pead_signals.loc[mask, ticker] = signal.values

        return pead_signals

    def compute_revision_momentum(self, tickers: List[str]) -> pd.Series:
        """
        Compute earnings revision momentum.
        
        Looks at whether analyst estimates have been revised up or down.
        Positive revision momentum = analysts getting more bullish.
        
        Returns Series indexed by ticker with revision momentum score [-1, 1].
        """
        scores = {}

        for ticker in tickers:
            earnings = self.load_earnings_history(ticker)
            if earnings.empty or len(earnings) < 2:
                scores[ticker] = 0.0
                continue

            # Compare recent estimate trends
            if "eps_estimate" in earnings.columns:
                estimates = earnings["eps_estimate"].dropna()
                if len(estimates) >= 2:
                    # Revision = (latest estimate - previous estimate) / |previous estimate|
                    latest = estimates.iloc[-1]
                    previous = estimates.iloc[-2]
                    if abs(previous) > 0.01:
                        scores[ticker] = np.clip((latest - previous) / abs(previous), -1, 1)
                    else:
                        scores[ticker] = 0.0
                else:
                    scores[ticker] = 0.0
            else:
                # Use earnings growth as proxy
                if "eps_actual" in earnings.columns:
                    actuals = earnings["eps_actual"].dropna()
                    if len(actuals) >= 2:
                        growth = (actuals.iloc[-1] - actuals.iloc[-2]) / max(abs(actuals.iloc[-2]), 0.01)
                        scores[ticker] = np.clip(growth, -1, 1)
                    else:
                        scores[ticker] = 0.0
                else:
                    scores[ticker] = 0.0

        return pd.Series(scores, name="revision_momentum")

    def get_upcoming_earnings(self, tickers: List[str], days_ahead: int = 7) -> List[str]:
        """
        Get tickers with earnings within N days.
        
        Used for "do not trade" filter (avoid entering right before earnings
        unless explicitly an earnings strategy).
        """
        upcoming = []
        cutoff = datetime.now() + timedelta(days=days_ahead)

        for ticker in tickers:
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                cal = getattr(stock, "calendar", None)
                if cal is not None:
                    if isinstance(cal, dict) and "Earnings Date" in cal:
                        dates = cal["Earnings Date"]
                        if isinstance(dates, list) and dates:
                            next_date = pd.to_datetime(dates[0])
                            if next_date <= cutoff:
                                upcoming.append(ticker)
                    elif isinstance(cal, pd.DataFrame) and not cal.empty:
                        upcoming.append(ticker)
            except Exception:
                pass

        return upcoming
