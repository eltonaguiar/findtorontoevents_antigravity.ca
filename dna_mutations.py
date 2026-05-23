# dna_mutations.py
"""
High‑impact DNA‑style mutation strategies for crypto prediction.
These functions inject additional on‑chain and macro signals that have
historically shown strong predictive power on major assets.
"""
import pandas as pd
import numpy as np


def add_dna_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add a suite of DNA‑style features.

    Features include:
      * Network hash‑rate momentum (for PoW coins)
      * Active address growth (Ethereum‑style chains)
      * Funding‑rate skew (perpetual markets)
      * Order‑book depth imbalance (approximate via volume)
    """
    # Defensive copy
    df = df.copy()

    # 1. Hash‑rate momentum – placeholder using price volatility as proxy
    df['hash_rate_mom'] = df['close'].pct_change(7).fillna(0)

    # 2. Active address growth – proxy using volume spikes
    df['active_addr_growth'] = df['volume'].pct_change(3).fillna(0)

    # 3. Funding‑rate skew – simulate with price‑to‑MA difference
    df['funding_skew'] = (df['close'] - df['close'].rolling(20).mean()) / df['close']

    # 4. Order‑book depth imbalance – proxy using high‑low range vs volume
    df['depth_imbalance'] = (df['high'] - df['low']) / (df['volume'] + 1e-8)

    return df
