"""
Feature Family 14: Flow

ETF flow proxies, institutional ownership changes, short interest proxies.
"Follow the smart money" signals.
"""
import numpy as np
import pandas as pd


def compute_flow_features(
    close: pd.DataFrame,
    volume: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute flow and institutional positioning features.
    
    Without premium data feeds, we compute proxies from public data.
    
    Features (stacked):
    - Institutional accumulation proxy (price-volume pattern)
    - ETF flow proxy (sector ETF vs constituents)
    - Short interest proxy (from return patterns)
    - Block trade detection proxy
    - Money flow index (MFI)
    - Relative flow strength
    """
    features = {}
    returns = close.pct_change()
    dollar_volume = close * volume

    # ── Institutional Accumulation Proxy ──────────────────────────────────
    # Institutions buy gradually: volume up but price stable or slightly up
    # vs retail: price spikes with volume
    for w in [10, 20]:
        vol_trend = volume.rolling(w).mean() / volume.rolling(w * 3).mean().replace(0, np.nan)
        price_trend = close.pct_change(w).abs()

        # High volume growth + low price volatility = accumulation
        accumulation = vol_trend / (price_trend * 10 + 1)
        features[f"accumulation_proxy_{w}d"] = accumulation.stack()

    # ── Money Flow (Chaikin-style proxy) ──────────────────────────────────
    # Without intraday data, use close-to-close direction * volume
    mf_raw = returns.apply(np.sign) * dollar_volume
    for w in [10, 20]:
        mf_ratio = mf_raw.rolling(w).sum() / dollar_volume.rolling(w).sum().replace(0, np.nan)
        features[f"money_flow_{w}d"] = mf_ratio.stack()

    # ── Block Trade Proxy ─────────────────────────────────────────────────
    # Large single-day volume spikes with small price moves = block trades
    vol_zscore = (volume - volume.rolling(50).mean()) / volume.rolling(50).std().replace(0, np.nan)
    ret_zscore = returns.abs() / returns.abs().rolling(50).mean().replace(0, np.nan)

    # High volume z-score but low return z-score = block-like
    block_proxy = vol_zscore / (ret_zscore + 1)
    features["block_trade_proxy"] = block_proxy.stack()

    # ── Short Interest Proxy ──────────────────────────────────────────────
    # Stocks with high negative momentum + high volume = potential short covering
    # Stocks with steady decline on low volume = shorts building position
    ret_21 = close.pct_change(21)
    vol_ratio = volume / volume.rolling(50).mean().replace(0, np.nan)

    # Short covering candidate: negative 21d return + volume spike
    short_cover_proxy = (-ret_21).clip(0, None) * vol_ratio
    features["short_cover_proxy"] = short_cover_proxy.stack()

    # Short building proxy: steady decline on normal/low volume
    short_build_proxy = (-ret_21).clip(0, None) * (1 / vol_ratio.clip(0.1, None))
    features["short_build_proxy"] = short_build_proxy.stack()

    # ── ETF Flow Proxy ────────────────────────────────────────────────────
    # When sector ETF volume spikes, constituent stocks follow
    # Use average dollar volume change across universe as market flow proxy
    universe_flow = dollar_volume.mean(axis=1)
    universe_flow_norm = universe_flow / universe_flow.rolling(50).mean()

    # Individual stock flow vs market flow
    stock_flow = dollar_volume.div(dollar_volume.rolling(50).mean().replace(0, np.nan))
    relative_flow = stock_flow.sub(universe_flow_norm, axis=0)
    features["relative_flow"] = relative_flow.stack()

    # ── Flow Momentum ─────────────────────────────────────────────────────
    # Change in dollar volume trend
    dv_ma5 = dollar_volume.rolling(5).mean()
    dv_ma20 = dollar_volume.rolling(20).mean()
    flow_momentum = dv_ma5 / dv_ma20.replace(0, np.nan) - 1
    features["flow_momentum"] = flow_momentum.stack()

    # ── Cumulative Flow Score ─────────────────────────────────────────────
    # Sum of signed dollar volume over window (like OBV but dollar-weighted)
    for w in [10, 20]:
        signed_flow = returns.apply(np.sign) * dollar_volume
        cum_flow = signed_flow.rolling(w).sum()
        cum_flow_norm = cum_flow / dollar_volume.rolling(w).sum().replace(0, np.nan)
        features[f"cum_flow_{w}d"] = cum_flow_norm.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result
