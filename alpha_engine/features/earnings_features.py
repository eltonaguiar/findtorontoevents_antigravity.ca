"""
Feature Family 10: Earnings / Estimates

Surprise history, revision momentum, post-earnings drift.
"Earnings edge is huge" — the single biggest low-hanging fruit for alpha.
"""
import numpy as np
import pandas as pd
from typing import Dict


def compute_earnings_features(
    close: pd.DataFrame,
    earnings_data: Dict,
) -> pd.DataFrame:
    """
    Compute earnings-related features.
    
    Args:
        close: Adjusted close prices (date x ticker)
        earnings_data: Dict with keys:
            'beats': DataFrame from EarningsLoader.detect_consecutive_beats()
            'pead': DataFrame from EarningsLoader.compute_pead_signal()
            'revision': Series from EarningsLoader.compute_revision_momentum()
    
    Features (stacked or point-in-time broadcast):
    - Consecutive beats count
    - Is Safe Bet (3+ consecutive beats of 5%+)
    - Beat streak quality
    - Average earnings surprise
    - PEAD signal strength
    - Revision momentum
    - Earnings consistency score
    """
    tickers = close.columns.tolist()
    dates = close.index
    features = {}

    beats_df = earnings_data.get("beats", pd.DataFrame())
    pead_df = earnings_data.get("pead", pd.DataFrame())
    revision = earnings_data.get("revision", pd.Series(dtype=float))

    # ── Consecutive Beats ─────────────────────────────────────────────────
    if not beats_df.empty:
        for col in ["consecutive_beats", "avg_surprise", "is_safe_bet", "beat_streak_quality"]:
            if col in beats_df.columns:
                wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
                for ticker in tickers:
                    if ticker in beats_df.index:
                        val = beats_df.loc[ticker, col]
                        if col == "is_safe_bet":
                            val = float(val)
                        wide[ticker] = val
                features[col] = wide.stack()

    # ── PEAD (Post-Earnings Announcement Drift) ───────────────────────────
    if not pead_df.empty:
        # PEAD is already date x ticker
        aligned = pead_df.reindex(index=dates, columns=tickers).fillna(0)
        features["pead_signal"] = aligned.stack()

        # PEAD rank (cross-sectional)
        pead_rank = aligned.rank(axis=1, pct=True)
        features["pead_rank"] = pead_rank.stack()

    # ── Revision Momentum ─────────────────────────────────────────────────
    if not revision.empty:
        wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
        for ticker in tickers:
            if ticker in revision.index:
                wide[ticker] = revision[ticker]
        features["revision_momentum"] = wide.stack()

        # Revision rank
        rev_wide = wide.copy()
        rev_rank = pd.DataFrame(index=dates, columns=tickers, dtype=float)
        for ticker in tickers:
            if ticker in revision.index:
                rev_rank[ticker] = revision.rank(pct=True).get(ticker, 0.5)
        features["revision_rank"] = rev_rank.stack()

    # ── Earnings Consistency Score ────────────────────────────────────────
    # Combines beats + revision + PEAD into single score
    consistency = pd.DataFrame(0.0, index=dates, columns=tickers)
    n = 0

    if "beat_streak_quality" in features:
        # Unstack to wide, normalize to [0,1]
        beats_wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
        for ticker in tickers:
            if not beats_df.empty and ticker in beats_df.index:
                beats_wide[ticker] = min(beats_df.loc[ticker, "beat_streak_quality"] / 3.0, 1.0)
        consistency += beats_wide.fillna(0)
        n += 1

    if "revision_momentum" in features:
        rev_wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
        for ticker in tickers:
            if ticker in revision.index:
                rev_wide[ticker] = (revision[ticker] + 1) / 2  # Map [-1,1] to [0,1]
        consistency += rev_wide.fillna(0.5)
        n += 1

    if n > 0:
        consistency = consistency / n
        features["earnings_consistency"] = consistency.stack()

    # ── Earnings Event Flag ───────────────────────────────────────────────
    # Flag if stock recently reported (within PEAD window)
    if not pead_df.empty:
        recently_reported = (pead_df.abs() > 0).astype(float)
        aligned = recently_reported.reindex(index=dates, columns=tickers).fillna(0)
        features["recently_reported"] = aligned.stack()

    result = pd.DataFrame(features)
    if isinstance(result.index, pd.MultiIndex):
        result.index.names = ["date", "ticker"]
    return result
