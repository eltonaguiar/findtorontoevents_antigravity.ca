"""
Feature Family 13: Sentiment / Attention

News volume shock, social attention proxies, analyst tone.
The "Sentiment Velocity" signal: sudden changes in sentiment precede price moves.
"""
import numpy as np
import pandas as pd


def compute_sentiment_features(
    close: pd.DataFrame,
    volume: pd.DataFrame = None,
    sentiment_data: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Compute sentiment and attention features.
    
    Uses real sentiment data when available, falls back to
    price/volume-based proxies.
    
    Features (stacked):
    - Sentiment score (from news/social)
    - Sentiment velocity (rate of change)
    - Attention proxy (unusual volume + unusual returns)
    - Fear/greed proxy
    - Momentum-sentiment confirmation
    - Media attention score
    """
    features = {}
    returns = close.pct_change()

    # ── Real Sentiment Data (if available) ────────────────────────────────
    if sentiment_data is not None and not sentiment_data.empty:
        for col in sentiment_data.columns:
            if col in ["sentiment_score", "sentiment_velocity", "sentiment_count"]:
                # Broadcast point-in-time sentiment across dates
                wide = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
                for ticker in close.columns:
                    if ticker in sentiment_data.index:
                        wide[ticker] = sentiment_data.loc[ticker, col]
                features[col] = wide.stack()

    # ── Attention Proxy (from price/volume anomalies) ─────────────────────
    if volume is not None:
        vol_ratio = volume / volume.rolling(20).mean().replace(0, np.nan)
        abs_ret = returns.abs()
        abs_ret_ratio = abs_ret / abs_ret.rolling(20).mean().replace(0, np.nan)

        # Attention = unusual volume + unusual price moves
        attention = (vol_ratio * abs_ret_ratio).clip(0, 20)
        features["attention_proxy"] = attention.stack()

        # Attention rank (cross-sectional)
        features["attention_rank"] = attention.rank(axis=1, pct=True).stack()

        # Attention spike (>2 std devs above mean)
        att_mean = attention.rolling(63).mean()
        att_std = attention.rolling(63).std()
        att_spike = ((attention - att_mean) / att_std.replace(0, np.nan) > 2).astype(float)
        features["attention_spike"] = att_spike.stack()

    # ── Accumulation/Distribution Sentiment ───────────────────────────────
    if volume is not None:
        # Smart money proxy: large volume with small price change = accumulation
        # Dumb money proxy: large price change with normal volume = retail
        vol_ratio = volume / volume.rolling(20).mean().replace(0, np.nan)
        ret_abs = returns.abs()

        # Smart money: high volume, low return → accumulation
        smart_money = vol_ratio / (ret_abs * 100 + 1)
        features["smart_money_proxy"] = smart_money.rolling(5).mean().stack()

    # ── Momentum-Sentiment Confirmation ───────────────────────────────────
    # Price momentum confirmed by volume/attention = stronger signal
    if volume is not None:
        mom_21 = close.pct_change(21)
        vol_trend = volume.rolling(21).mean() / volume.rolling(63).mean().replace(0, np.nan)

        # Confirmed momentum: price up + volume up
        confirmed_bull = (mom_21 > 0).astype(float) * (vol_trend > 1.0).astype(float)
        confirmed_bear = (mom_21 < 0).astype(float) * (vol_trend > 1.0).astype(float)
        features["confirmed_momentum_bull"] = confirmed_bull.stack()
        features["confirmed_momentum_bear"] = confirmed_bear.stack()

    # ── Market-Wide Sentiment ─────────────────────────────────────────────
    # Cross-sectional: % of stocks above 50-day MA
    breadth = (close > close.rolling(50).mean()).mean(axis=1)
    breadth_wide = pd.DataFrame(
        breadth.values[:, np.newaxis] * np.ones(len(close.columns)),
        index=close.index, columns=close.columns,
    )
    features["market_breadth"] = breadth_wide.stack()

    # Breadth momentum
    breadth_mom = breadth - breadth.shift(21)
    bm_wide = pd.DataFrame(
        breadth_mom.values[:, np.newaxis] * np.ones(len(close.columns)),
        index=close.index, columns=close.columns,
    )
    features["breadth_momentum"] = bm_wide.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result
