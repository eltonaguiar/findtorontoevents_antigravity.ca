"""
Feature Family 9: Valuation

Value composites and sector-neutral value signals.
Classic value factors adapted for cross-sectional ranking.
"""
import numpy as np
import pandas as pd


def compute_valuation_features(
    close: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute valuation features.
    
    Features:
    - PE, PB, PS ratios and their ranks
    - Earnings yield, FCF yield ranks
    - Composite value score
    - Sector-neutral value (value vs sector peers)
    - Value momentum (improving valuation)
    - Deep value flags
    """
    features = {}
    tickers = fundamentals.index.tolist()

    # ── Raw Valuation Metrics ─────────────────────────────────────────────
    for col in ["pe_ratio", "pb_ratio", "ps_ratio", "earnings_yield", "fcf_yield"]:
        if col in fundamentals.columns:
            features[col] = fundamentals[col]

    # ── Valuation Ranks (lower P/E = higher value rank) ───────────────────
    if "pe_ratio" in fundamentals.columns:
        pe = fundamentals["pe_ratio"].clip(0, 200)
        features["pe_rank"] = (1 / pe.replace(0, np.nan)).rank(pct=True)  # Low PE = high rank

    if "pb_ratio" in fundamentals.columns:
        pb = fundamentals["pb_ratio"].clip(0, 50)
        features["pb_rank"] = (1 / pb.replace(0, np.nan)).rank(pct=True)

    if "ps_ratio" in fundamentals.columns:
        ps = fundamentals["ps_ratio"].clip(0, 50)
        features["ps_rank"] = (1 / ps.replace(0, np.nan)).rank(pct=True)

    for col in ["earnings_yield", "fcf_yield"]:
        if col in fundamentals.columns:
            features[f"{col}_rank"] = fundamentals[col].rank(pct=True)

    # ── Composite Value Score ─────────────────────────────────────────────
    value_composite = pd.Series(0.0, index=tickers)
    n = 0
    for col in ["pe_rank", "pb_rank", "ps_rank", "earnings_yield_rank", "fcf_yield_rank"]:
        if col in features:
            value_composite += features[col].fillna(0.5)
            n += 1
    if n > 0:
        features["value_composite"] = value_composite / n

    # ── Sector-Neutral Value ──────────────────────────────────────────────
    # Value relative to sector peers (avoids always picking "cheap" sectors)
    if "sector" in fundamentals.columns and "pe_ratio" in fundamentals.columns:
        sector_neutral = pd.Series(0.5, index=tickers)
        for sector in fundamentals["sector"].unique():
            if pd.isna(sector):
                continue
            mask = fundamentals["sector"] == sector
            if mask.sum() >= 3:
                sector_tickers = fundamentals[mask].index
                pe_sector = fundamentals.loc[sector_tickers, "pe_ratio"].clip(0, 200)
                sector_rank = (1 / pe_sector.replace(0, np.nan)).rank(pct=True)
                sector_neutral.update(sector_rank)
        features["sector_neutral_value"] = sector_neutral

    # ── EV/EBITDA proxy ───────────────────────────────────────────────────
    if "market_cap" in fundamentals.columns and "pe_ratio" in fundamentals.columns:
        # Rough proxy: use P/E as stand-in (proper EV/EBITDA needs enterprise value)
        features["ev_ebitda_proxy_rank"] = features.get("pe_rank", pd.Series(0.5, index=tickers))

    # ── Deep Value Flags ──────────────────────────────────────────────────
    if "pe_ratio" in fundamentals.columns:
        pe = fundamentals["pe_ratio"]
        features["deep_value"] = ((pe > 0) & (pe < 10)).astype(float)

    if "pb_ratio" in fundamentals.columns:
        pb = fundamentals["pb_ratio"]
        features["below_book"] = (pb < 1.0).astype(float)

    # ── Value + Quality (avoid value traps) ───────────────────────────────
    if "value_composite" in features and "roe" in fundamentals.columns:
        quality_rank = fundamentals["roe"].rank(pct=True).fillna(0.5)
        features["value_quality_combo"] = (features["value_composite"] + quality_rank) / 2

    # ── Dividend Yield Rank ───────────────────────────────────────────────
    if "dividend_yield" in fundamentals.columns:
        features["div_yield_rank"] = fundamentals["dividend_yield"].rank(pct=True)

    return pd.DataFrame(features)
