"""
Feature Family 7: Fundamental Quality

Profitability, margins, ROIC, accruals, balance sheet strength.
"Boring but powerful" — these factors select for durable compounders.
"""
import numpy as np
import pandas as pd


def compute_fundamental_features(
    close: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute fundamental quality features.
    
    Converts point-in-time fundamentals to time-series features
    by broadcasting the latest fundamental values across dates.
    
    Features (stacked):
    - Profitability: ROE, ROIC, ROA
    - Margins: gross, operating, net
    - Earnings quality: accruals ratio
    - Balance sheet: debt/equity, current ratio
    - Capital efficiency: FCF yield, earnings yield
    - Quality composite score
    - Sector-neutral quality
    """
    features = {}

    # Broadcast fundamentals to time series (latest known value)
    dates = close.index
    tickers = close.columns

    # ── Raw Quality Metrics ───────────────────────────────────────────────
    quality_cols = [
        "roe", "roic", "roa", "gross_margin", "operating_margin", "net_margin",
        "accruals_ratio", "debt_to_equity", "current_ratio", "fcf_yield",
        "earnings_yield", "dividend_yield", "buyback_yield",
    ]

    for col in quality_cols:
        if col in fundamentals.columns:
            # Create wide DataFrame broadcasting fundamental value across time
            wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
            for ticker in tickers:
                if ticker in fundamentals.index:
                    wide[ticker] = fundamentals.loc[ticker, col]
            features[col] = wide.stack()

    # ── Cross-Sectional Quality Ranks ─────────────────────────────────────
    for col in ["roe", "roic", "gross_margin", "fcf_yield", "earnings_yield"]:
        if col in fundamentals.columns:
            values = fundamentals[col]
            rank = values.rank(pct=True)
            wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
            for ticker in tickers:
                if ticker in rank.index:
                    wide[ticker] = rank[ticker]
            features[f"{col}_rank"] = wide.stack()

    # ── Quality Composite Score ───────────────────────────────────────────
    # Combine: ROE + ROIC + Gross Margin + low accruals + low debt
    composite = pd.Series(0.0, index=tickers, dtype=float)
    n_factors = 0

    for col, higher_better in [
        ("roe", True), ("roic", True), ("gross_margin", True),
        ("operating_margin", True), ("fcf_yield", True),
        ("accruals_ratio", False), ("debt_to_equity", False),
    ]:
        if col in fundamentals.columns:
            vals = fundamentals[col].dropna()
            if len(vals) > 2:
                rank = vals.rank(pct=True, ascending=higher_better)
                composite = composite.add(rank, fill_value=0)
                n_factors += 1

    if n_factors > 0:
        composite = composite / n_factors

    wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    for ticker in tickers:
        if ticker in composite.index:
            wide[ticker] = composite[ticker]
    features["quality_composite"] = wide.stack()

    # ── Piotroski F-Score Proxy ───────────────────────────────────────────
    # Simplified: count positive signals
    fscore = pd.Series(0, index=tickers, dtype=int)
    if "roe" in fundamentals.columns:
        fscore += (fundamentals["roe"] > 0).astype(int).reindex(tickers, fill_value=0)
    if "roa" in fundamentals.columns:
        fscore += (fundamentals["roa"] > 0).astype(int).reindex(tickers, fill_value=0)
    if "operating_margin" in fundamentals.columns:
        fscore += (fundamentals["operating_margin"] > 0).astype(int).reindex(tickers, fill_value=0)
    if "fcf_yield" in fundamentals.columns:
        fscore += (fundamentals["fcf_yield"] > 0).astype(int).reindex(tickers, fill_value=0)
    if "current_ratio" in fundamentals.columns:
        fscore += (fundamentals["current_ratio"] > 1).astype(int).reindex(tickers, fill_value=0)
    if "debt_to_equity" in fundamentals.columns:
        fscore += (fundamentals["debt_to_equity"] < 100).astype(int).reindex(tickers, fill_value=0)

    wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    for ticker in tickers:
        if ticker in fscore.index:
            wide[ticker] = fscore[ticker]
    features["piotroski_proxy"] = wide.stack()

    # ── Balance Sheet Resilience ──────────────────────────────────────────
    # Important in tightening regimes
    resilience = pd.Series(0.0, index=tickers, dtype=float)
    if "current_ratio" in fundamentals.columns:
        resilience += fundamentals["current_ratio"].clip(0, 5).rank(pct=True).reindex(tickers, fill_value=0.5)
    if "debt_to_equity" in fundamentals.columns:
        resilience += (1 - fundamentals["debt_to_equity"].clip(0, 500).rank(pct=True)).reindex(tickers, fill_value=0.5)

    wide = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    for ticker in tickers:
        if ticker in resilience.index:
            wide[ticker] = resilience[ticker]
    features["balance_sheet_resilience"] = wide.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result
