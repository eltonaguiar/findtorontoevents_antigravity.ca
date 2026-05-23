"""
failover_imports.py — Centralized import point for crypto_data_failover
========================================================================
Single place to import and re-export the shared multi-source failover
functions.  All callers (funding_rate_scanner, winner_reverse_engineer,
data_fetcher) import from this module instead of duplicating the
dual try/except ImportError pattern.

Eliminates the maintenance hazard where 3+ files each had identical
fallback blocks that had to be updated in lockstep.
"""
from __future__ import annotations

try:
    from alpha_engine.crypto_data_failover import (
        fetch_tickers_24h,
        fetch_klines,
        fetch_funding_rate,
        fetch_funding_entry,
    )
    HAS_SHARED_FAILOVER = True
except ImportError:
    try:
        from crypto_data_failover import (  # type: ignore[no-redef]
            fetch_tickers_24h,
            fetch_klines,
            fetch_funding_rate,
            fetch_funding_entry,
        )
        HAS_SHARED_FAILOVER = True
    except ImportError:
        HAS_SHARED_FAILOVER = False
        fetch_tickers_24h = None  # type: ignore[assignment]
        fetch_klines = None  # type: ignore[assignment]
        fetch_funding_rate = None  # type: ignore[assignment]
        fetch_funding_entry = None  # type: ignore[assignment]
