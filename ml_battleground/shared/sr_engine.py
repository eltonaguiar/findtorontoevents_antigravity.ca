"""
Support/Resistance detection engine for ML Battleground.
Combines Williams fractal pivots, volume profile (POC/VAH/VAL),
multi-touch clustering, and round-number magnetism.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
import itertools

try:
    from statsmodels.tsa.stattools import coint
except ImportError:
    coint = None  # pairs trading features unavailable without statsmodels


@dataclass
class SRLevel:
    price: float
    strength: float       # composite score (higher = stronger)
    touches: int
    level_type: str       # "support" | "resistance"
    source: str           # "fractal" | "volume_profile" | "round_number"
    recency: float        # 0-1, higher = more recent


def find_cointegrated_pairs(price_data: dict, p_threshold: float = 0.05, min_periods: int = 100) -> list[dict]:
    """
    Find statistically cointegrated pairs using Engle-Granger test.
    Returns list of dicts with pair info sorted by p-value.
    """
    if coint is None:
        return []  # statsmodels not installed
    pairs = []
    symbols = list(price_data.keys())

    for sym1, sym2 in itertools.combinations(symbols, 2):
        if sym1 not in price_data or sym2 not in price_data:
            continue

        df1, df2 = price_data[sym1], price_data[sym2]
        if len(df1) < min_periods or len(df2) < min_periods:
            continue

        prices1 = df1['Close'].values[-min_periods:]
        prices2 = df2['Close'].values[-min_periods:]

        try:
            score, p_value, hedge_ratio = coint(prices1, prices2)
            correlation = np.corrcoef(prices1, prices2)[0, 1]

            if p_value < p_threshold and abs(correlation) > 0.6:  # Require decent correlation too
                pairs.append({
                    'pair': (sym1, sym2),
                    'p_value': p_value,
                    'hedge_ratio': float(hedge_ratio),
                    'correlation': correlation,
                    'spread_volatility': calculate_spread_volatility(prices1, prices2, hedge_ratio)
                })
        except Exception as e:
            continue

    return sorted(pairs, key=lambda x: x['p_value'])


def calculate_spread_volatility(prices1: np.ndarray, prices2: np.ndarray, hedge_ratio: float) -> float:
    """Calculate annualized volatility of the spread"""
    spread = prices1 - hedge_ratio * prices2
    returns = np.diff(spread) / spread[:-1]
    return np.std(returns) * np.sqrt(365)


def pairs_trading_signal(df1: pd.DataFrame, df2: pd.DataFrame, hedge_ratio: float,
                        lookback: int = 60, z_threshold: float = 2.0) -> dict:
    """
    Generate z-score based pairs trading signals.
    Returns signal dict with z-score, direction, and confidence.
    """
    spread = df1['Close'] - hedge_ratio * df2['Close']
    spread_mean = spread.rolling(lookback).mean()
    spread_std = spread.rolling(lookback).std()

    if len(spread_std.dropna()) < lookback:
        return {'signal': 'HOLD', 'z_score': 0.0, 'confidence': 0.0}

    z_score = (spread.iloc[-1] - spread_mean.iloc[-1]) / spread_std.iloc[-1]

    if abs(z_score) >= z_threshold:
        signal = 'LONG_SPREAD' if z_score < 0 else 'SHORT_SPREAD'  # Buy cheap, sell expensive
        confidence = min(abs(z_score) / 3.0, 1.0)
    else:
        signal = 'HOLD'
        confidence = 0.0

    return {
        'signal': signal,
        'z_score': z_score,
        'confidence': confidence,
        'spread': spread.iloc[-1],
        'mean': spread_mean.iloc[-1],
        'std': spread_std.iloc[-1]
    }


def detect_sr_levels(
    df: pd.DataFrame,
    current_price: Optional[float] = None,
    fractal_window: int = 5,
    cluster_tolerance: float = 0.003,
    min_touches: int = 2,
    n_volume_bins: int = 50,
    volume_lookback: int = 100,
    max_levels: int = 10,
) -> list[SRLevel]:
    """
    Detect support and resistance levels from OHLCV data.

    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
        current_price: Current price (defaults to last close)
        fractal_window: Window for Williams fractal detection
        cluster_tolerance: Clustering tolerance as fraction of price
        min_touches: Minimum touches for a level to qualify
        n_volume_bins: Number of bins for volume profile
        volume_lookback: Bars to look back for volume profile
        max_levels: Maximum S/R levels to return

    Returns:
        List of SRLevel sorted by strength (strongest first)
    """
    if current_price is None:
        current_price = float(df["Close"].iloc[-1])

    levels = []

    # 1. Fractal pivots + clustering
    fractal_levels = _fractal_sr(df, fractal_window, cluster_tolerance, min_touches)
    levels.extend(fractal_levels)

    # 2. Volume profile
    vp_levels = _volume_profile_sr(df, n_volume_bins, volume_lookback)
    levels.extend(vp_levels)

    # 3. Round numbers
    round_levels = _round_number_sr(current_price)
    levels.extend(round_levels)

    # Label as support/resistance relative to current price
    for level in levels:
        if level.price < current_price:
            level.level_type = "support"
        else:
            level.level_type = "resistance"

    # Merge nearby levels from different sources
    levels = _merge_nearby(levels, tolerance=cluster_tolerance)

    # Sort by strength descending
    levels.sort(key=lambda x: x.strength, reverse=True)

    return levels[:max_levels]


def detect_sr_levels(
    df: pd.DataFrame,
    current_price: Optional[float] = None,
    fractal_window: int = 5,
    cluster_tolerance: float = 0.003,
    min_touches: int = 2,
    n_volume_bins: int = 50,
    volume_lookback: int = 100,
    max_levels: int = 10,
) -> list[SRLevel]:
    """
    Detect support and resistance levels from OHLCV data.

    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
        current_price: Current price (defaults to last close)
        fractal_window: Window for Williams fractal detection
        cluster_tolerance: Clustering tolerance as fraction of price
        min_touches: Minimum touches for a level to qualify
        n_volume_bins: Number of bins for volume profile
        volume_lookback: Bars to look back for volume profile
        max_levels: Maximum S/R levels to return

    Returns:
        List of SRLevel sorted by strength (strongest first)
    """
    if current_price is None:
        current_price = float(df["Close"].iloc[-1])

    levels = []

    # 1. Fractal pivots + clustering
    fractal_levels = _fractal_sr(df, fractal_window, cluster_tolerance, min_touches)
    levels.extend(fractal_levels)

    # 2. Volume profile
    vp_levels = _volume_profile_sr(df, n_volume_bins, volume_lookback)
    levels.extend(vp_levels)

    # 3. Round numbers
    round_levels = _round_number_sr(current_price)
    levels.extend(round_levels)

    # Label as support/resistance relative to current price
    for level in levels:
        if level.price < current_price:
            level.level_type = "support"
        else:
            level.level_type = "resistance"

    # Merge nearby levels from different sources
    levels = _merge_nearby(levels, tolerance=cluster_tolerance)

    # Sort by strength descending
    levels.sort(key=lambda x: x.strength, reverse=True)

    return levels[:max_levels]


def nearest_support(levels: list[SRLevel], price: float) -> Optional[SRLevel]:
    """Find strongest support level below price."""
    supports = [l for l in levels if l.level_type == "support" and l.price < price]
    if not supports:
        return None
    return max(supports, key=lambda x: x.strength)


def nearest_resistance(levels: list[SRLevel], price: float) -> Optional[SRLevel]:
    """Find strongest resistance level above price."""
    resistances = [l for l in levels if l.level_type == "resistance" and l.price > price]
    if not resistances:
        return None
    return max(resistances, key=lambda x: x.strength)


def sr_based_tp_sl(
    entry_price: float,
    levels: list[SRLevel],
    atr_value: float,
    signal_type: str = "BUY",
    min_rr: float = 2.0,
    tp_atr_fallback: float = 3.0,
    sl_atr_fallback: float = 1.5,
) -> tuple[float, float, str]:
    """
    Set TP/SL using S/R levels with ATR fallback.
    Enforces minimum 2:1 reward-to-risk and 1.5% minimum SL distance.

    Returns:
        (take_profit, stop_loss, method) where method is "sr" or "atr"
    """
    # Minimum SL distance: 1.5x ATR to avoid noise-triggered stops
    # Enforce 2.5% minimum distance from entry (crypto 4h candles move 1-3% routinely)
    # Old value 1.5% caused 90% of trades to hit SL on normal noise
    min_sl_dist = max(1.5 * atr_value, entry_price * 0.025)

    if signal_type == "BUY":
        resistance = nearest_resistance(levels, entry_price)
        support = nearest_support(levels, entry_price)

        tp = resistance.price if resistance else entry_price + tp_atr_fallback * atr_value
        sl = support.price * 0.998 if support else entry_price - sl_atr_fallback * atr_value

        # Enforce minimum SL distance (1x ATR)
        if entry_price - sl < min_sl_dist:
            sl = entry_price - min_sl_dist

        # Ensure minimum R:R
        risk = entry_price - sl
        reward = tp - entry_price
        if risk > 0 and reward / risk < min_rr:
            tp = entry_price + min_rr * risk

        method = "sr" if (resistance or support) else "atr"
    else:  # SELL
        support = nearest_support(levels, entry_price)
        resistance = nearest_resistance(levels, entry_price)

        tp = support.price if support else entry_price - tp_atr_fallback * atr_value
        sl = resistance.price * 1.002 if resistance else entry_price + sl_atr_fallback * atr_value

        # Enforce minimum SL distance (1x ATR)
        if sl - entry_price < min_sl_dist:
            sl = entry_price + min_sl_dist

        # Cap maximum SL at 4% from entry — S/R can place resistance 10%+ away
        # which is insane for crypto shorts. 4% is generous for 4h timeframe.
        max_sl_dist = entry_price * 0.04
        if sl - entry_price > max_sl_dist:
            sl = entry_price + max_sl_dist

        risk = sl - entry_price
        reward = entry_price - tp
        if risk > 0 and reward / risk < min_rr:
            tp = entry_price - min_rr * risk

        method = "sr" if (support or resistance) else "atr"

    return tp, sl, method


def _fractal_sr(
    df: pd.DataFrame,
    window: int = 5,
    tolerance: float = 0.003,
    min_touches: int = 2,
) -> list[SRLevel]:
    """Williams fractal pivots -> clustered S/R levels."""
    high = df["High"].values
    low = df["Low"].values
    n = len(df)
    half = window // 2
    pivots = []

    for i in range(half, n - half):
        is_high = True
        is_low = True
        for j in range(i - half, i + half + 1):
            if j == i:
                continue
            if high[j] >= high[i]:
                is_high = False
            if low[j] <= low[i]:
                is_low = False
        if is_high:
            pivots.append((i, float(high[i]), "high"))
        if is_low:
            pivots.append((i, float(low[i]), "low"))

    # Cluster pivots
    if not pivots:
        return []

    pivots.sort(key=lambda x: x[1])
    clusters = []
    used = set()

    for idx, (i, price, ptype) in enumerate(pivots):
        if idx in used:
            continue
        cluster = [(i, price, ptype)]
        used.add(idx)
        for jdx, (j, price2, ptype2) in enumerate(pivots):
            if jdx in used:
                continue
            if abs(price2 - price) / price <= tolerance:
                cluster.append((j, price2, ptype2))
                used.add(jdx)

        if len(cluster) >= min_touches:
            avg_price = np.mean([p for _, p, _ in cluster])
            max_idx = max(c[0] for c in cluster)
            recency = max_idx / n if n > 0 else 0.5
            strength = len(cluster) * (1.0 + 0.5 * recency)

            levels_out = SRLevel(
                price=round(avg_price, 8),
                strength=strength,
                touches=len(cluster),
                level_type="support",  # will be relabeled
                source="fractal",
                recency=recency,
            )
            clusters.append(levels_out)

    return clusters


def _volume_profile_sr(
    df: pd.DataFrame,
    n_bins: int = 50,
    lookback: int = 100,
) -> list[SRLevel]:
    """Volume profile -> POC, VAH, VAL as S/R levels."""
    data = df.tail(lookback)
    if len(data) < 20:
        return []

    price_min = float(data["Low"].min())
    price_max = float(data["High"].max())
    if price_max <= price_min:
        return []

    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    profile = np.zeros(n_bins)

    for _, row in data.iterrows():
        bar_low = float(row["Low"])
        bar_high = float(row["High"])
        bar_vol = float(row["Volume"])
        if bar_high <= bar_low or bar_vol <= 0:
            continue
        for k in range(n_bins):
            overlap = max(0, min(bar_high, bin_edges[k + 1]) - max(bar_low, bin_edges[k]))
            bar_range = bar_high - bar_low
            if bar_range > 0:
                profile[k] += bar_vol * (overlap / bar_range)

    if profile.sum() == 0:
        return []

    # POC
    poc_idx = int(np.argmax(profile))
    poc_price = float(bin_centers[poc_idx])

    # Value Area (70% of volume)
    total_vol = profile.sum()
    target = 0.70 * total_vol
    accumulated = profile[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx

    while accumulated < target and (lo_idx > 0 or hi_idx < n_bins - 1):
        expand_lo = profile[lo_idx - 1] if lo_idx > 0 else 0
        expand_hi = profile[hi_idx + 1] if hi_idx < n_bins - 1 else 0
        if expand_lo >= expand_hi and lo_idx > 0:
            lo_idx -= 1
            accumulated += profile[lo_idx]
        elif hi_idx < n_bins - 1:
            hi_idx += 1
            accumulated += profile[hi_idx]
        else:
            break

    val = float(bin_centers[lo_idx])
    vah = float(bin_centers[hi_idx])

    levels = [
        SRLevel(price=round(poc_price, 8), strength=5.0, touches=0,
                level_type="support", source="volume_profile", recency=0.9),
        SRLevel(price=round(val, 8), strength=3.5, touches=0,
                level_type="support", source="volume_profile", recency=0.9),
        SRLevel(price=round(vah, 8), strength=3.5, touches=0,
                level_type="resistance", source="volume_profile", recency=0.9),
    ]
    return levels


def _round_number_sr(price: float) -> list[SRLevel]:
    """Psychological round-number levels near current price."""
    if price <= 0:
        return []

    magnitude = 10 ** int(np.log10(price))
    step = magnitude / 10 if price < magnitude * 5 else magnitude / 5
    if step < 0.01:
        step = 0.01

    levels = []
    base = round(price / step) * step
    for offset in [-3, -2, -1, 0, 1, 2, 3]:
        level_price = base + offset * step
        if level_price > 0 and abs(level_price - price) / price < 0.10:
            distance = abs(level_price - price) / price
            strength = max(0.5, 2.0 - distance * 20)
            levels.append(SRLevel(
                price=round(level_price, 8),
                strength=strength,
                touches=0,
                level_type="support",
                source="round_number",
                recency=1.0,
            ))
    return levels


def _merge_nearby(levels: list[SRLevel], tolerance: float = 0.003) -> list[SRLevel]:
    """Merge S/R levels from different sources that are very close."""
    if not levels:
        return []

    levels.sort(key=lambda x: x.price)
    merged = [levels[0]]

    for level in levels[1:]:
        prev = merged[-1]
        if abs(level.price - prev.price) / prev.price <= tolerance:
            # Merge: keep higher strength, sum touches, combine sources
            if level.strength > prev.strength:
                merged[-1] = SRLevel(
                    price=(prev.price + level.price) / 2,
                    strength=prev.strength + level.strength,
                    touches=prev.touches + level.touches,
                    level_type=prev.level_type,
                    source=f"{prev.source}+{level.source}",
                    recency=max(prev.recency, level.recency),
                )
            else:
                merged[-1] = SRLevel(
                    price=(prev.price + level.price) / 2,
                    strength=prev.strength + level.strength,
                    touches=prev.touches + level.touches,
                    level_type=prev.level_type,
                    source=f"{prev.source}+{level.source}",
                    recency=max(prev.recency, level.recency),
                )
        else:
            merged.append(level)

    return merged
