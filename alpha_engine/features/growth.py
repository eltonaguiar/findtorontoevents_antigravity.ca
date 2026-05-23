"""
Feature Family 8: Growth

Revenue/earnings growth consistency, operating leverage, guidance signals.
Separates "compounding machines" from one-time blips.
"""
import numpy as np
import pandas as pd


def compute_growth_features(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """
    Compute growth-related features from fundamental data.
    
    Features:
    - Revenue growth rate
    - Earnings growth rate
    - Growth consistency (low variance in growth)
    - Operating leverage proxy
    - Growth-profitability combo (GARP)
    - Growth rank (cross-sectional)
    - Growth stability score
    """
    features = {}
    tickers = fundamentals.index.tolist()

    # ── Raw Growth Rates ──────────────────────────────────────────────────
    for col in ["revenue_growth", "earnings_growth"]:
        if col in fundamentals.columns:
            features[col] = fundamentals[col]

    # ── Growth Ranks ──────────────────────────────────────────────────────
    for col in ["revenue_growth", "earnings_growth"]:
        if col in fundamentals.columns:
            features[f"{col}_rank"] = fundamentals[col].rank(pct=True)

    # ── GARP Score (Growth at Reasonable Price) ───────────────────────────
    # PEG ratio proxy: lower = better growth per unit of valuation
    if "earnings_growth" in fundamentals.columns and "pe_ratio" in fundamentals.columns:
        eg = fundamentals["earnings_growth"].clip(0.01, None)
        pe = fundamentals["pe_ratio"].clip(1, None)
        peg = pe / (eg * 100)  # Convert growth to % for PEG
        features["peg_ratio"] = peg
        features["peg_rank"] = (1 / peg.replace(0, np.nan)).rank(pct=True)  # Lower PEG = higher rank

    # ── Growth + Quality Combo ────────────────────────────────────────────
    # High growth + high margins = best compounders
    if "earnings_growth" in fundamentals.columns and "operating_margin" in fundamentals.columns:
        growth_rank = fundamentals["earnings_growth"].rank(pct=True)
        margin_rank = fundamentals["operating_margin"].rank(pct=True)
        features["growth_quality_combo"] = (growth_rank + margin_rank) / 2

    # ── Growth Stability ──────────────────────────────────────────────────
    # Consistent growers are more reliable than spiky ones
    # We use a heuristic based on available data
    if "revenue_growth" in fundamentals.columns and "earnings_growth" in fundamentals.columns:
        # Both positive = stable growing
        both_positive = (
            (fundamentals["revenue_growth"] > 0).astype(float) +
            (fundamentals["earnings_growth"] > 0).astype(float)
        ) / 2
        features["growth_stability"] = both_positive

    # ── Operating Leverage Proxy ──────────────────────────────────────────
    # op_margin_change / revenue_change would be ideal
    # Proxy: operating margin level (high = more leverage benefit from revenue growth)
    if "operating_margin" in fundamentals.columns and "revenue_growth" in fundamentals.columns:
        features["operating_leverage_proxy"] = (
            fundamentals["operating_margin"].rank(pct=True) *
            fundamentals["revenue_growth"].clip(0, None).rank(pct=True)
        )

    # ── Dividend + Buyback Growth (total shareholder yield proxy) ─────────
    total_yield = pd.Series(0.0, index=tickers)
    if "dividend_yield" in fundamentals.columns:
        total_yield += fundamentals["dividend_yield"].fillna(0)
    if "buyback_yield" in fundamentals.columns:
        total_yield += fundamentals["buyback_yield"].fillna(0)
    features["total_shareholder_yield"] = total_yield
    features["total_yield_rank"] = total_yield.rank(pct=True)

    # ── Growth Composite ──────────────────────────────────────────────────
    composite = pd.Series(0.0, index=tickers)
    n = 0
    for col in ["revenue_growth", "earnings_growth"]:
        if col in fundamentals.columns:
            composite += fundamentals[col].rank(pct=True).fillna(0.5)
            n += 1
    if "growth_quality_combo" in features:
        composite += features["growth_quality_combo"].fillna(0.5)
        n += 1
    if n > 0:
        features["growth_composite"] = composite / n

    return pd.DataFrame(features)
