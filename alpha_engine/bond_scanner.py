#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Bond Signal Scanner
=====================================
Runs bond ETF strategies using FRED macro data + yfinance OHLCV,
emits picks to active_picks_bond.json for merge into the main pipeline.

Strategies:
  1. Yield Momentum — SMA20/50 + RSI on Treasury yield proxies
  2. Duration Rotation — TLT regime-based allocation across duration buckets
  3. Mean Reversion — Bollinger Band + volume on bond ETFs

Data sources:
  - FRED (via bond_data_fred.py): DGS2, DGS10, DGS30, T10Y2Y, credit spreads
  - yfinance: Bond ETF OHLCV (TLT, IEF, SHY, LQD, HYG, etc.)

Run via cron:
  python -m alpha_engine.bond_scanner              # Generate signals only
  python -m alpha_engine.bond_scanner --merge      # Generate + merge into active_picks.json

Designed for Phase 2 of FOREX_COMMODITIES_BONDS.MD remediation plan.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    DATA_DIR,
    BOND_SYMBOLS,
    CATEGORY_RISK,
    MAX_PICKS_PER_STRATEGY,
    STRATEGY_WEIGHT_OVERRIDES,
    DEFAULT_ALLOCATION,
)

# Import bond strategies
try:
    from alpha_engine.bond_strategies import (
        bond_yield_momentum,
        bond_duration_rotation,
        bond_tlt_ief_v3,
        bond_mean_reversion,
        bond_yield_curve_slope,
        bond_connors_rsi2,
        bond_credit_spread_mean_reversion,
        bond_ust_tsmom,
    )
except ImportError:
    from bond_strategies import (
        bond_yield_momentum,
        bond_duration_rotation,
        bond_tlt_ief_v3,
        bond_mean_reversion,
        bond_yield_curve_slope,
        bond_connors_rsi2,
        bond_credit_spread_mean_reversion,
        bond_ust_tsmom,
    )

# Import FRED data fetcher
try:
    from alpha_engine.bond_data_fred import fetch_bond_bundle
except ImportError:
    try:
        from bond_data_fred import fetch_bond_bundle
    except ImportError:
        fetch_bond_bundle = None

# Optional: yfinance for OHLCV data
try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = DATA_DIR / "scanner_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# dashboard_generator.py reads from DATA_DIR/active_picks_bond.json (line 3944).
# Primary write goes there so picks appear in /audit without a separate merge step.
BOND_PICKS_PATH = DATA_DIR / "active_picks_bond.json"
_BOND_PICKS_SCANNER_PATH = OUTPUT_DIR / "active_picks_bond.json"  # secondary audit copy

STRATEGIES = [
    ("bond_yield_momentum", bond_yield_momentum),
    ("bond_duration_rotation", bond_duration_rotation),
    ("bond_tlt_ief_v3", bond_tlt_ief_v3),
    ("bond_mean_reversion", bond_mean_reversion),
    # 2026-05-14: Added yield-curve slope strategy (swarm P1 consensus)
    # Uses FRED T10Y2Y (2s10s spread): inverted→BUY TLT, steep→SELL TLT + BUY IEF
    # Academic basis: Fama-Bliss 1987, Estrella-Mishkin 1996
    ("bond_yield_curve_slope", bond_yield_curve_slope),
    # 2026-05-15: Wire-Up Rule compliance — these were imported but not registered
    ("bond_connors_rsi2", bond_connors_rsi2),
    ("bond_credit_spread_mean_reversion", bond_credit_spread_mean_reversion),
    # 2026-05-18: B-003/B-004 — UST TSMOM via FRED DGS10 + T10YIE inflation context
    ("bond_ust_tsmom", bond_ust_tsmom),
]

# Last-run data-fetch diagnostics. Populated by run_bond_scanner() so the CLI
# entry point can distinguish a real-empty market (exit 0 + ::warning::) from a
# data-provider outage (exit 1 + ::error::). Without this the scanner exited
# GitHub Actions GREEN on a total yfinance failure — "fail-open masking",
# infra_fragility_audit_2026_05_18.md §B.
LAST_RUN_DIAGNOSTICS: dict = {
    "symbols_requested": 0,
    "symbols_loaded": 0,
    "raw_signals": 0,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def fetch_bond_data(
    symbols: dict[str, dict],
    period: str = "2y",
    chunk_size: int = 12,
    retries: int = 3,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for bond ETF symbols via yfinance.

    Returns dict of symbol -> DataFrame with columns: Open, High, Low, Close, Volume.

    A single-batch yf.download is fragile on GitHub Actions runners — Yahoo
    rate-limits the shared runner IPs and the whole batch returns empty,
    aborting the scan. Download in small chunks, each with retry + backoff,
    and keep whatever partial data succeeds. (Mirrors etf_scanner.fetch_etf_data.)
    """
    data: dict[str, pd.DataFrame] = {}
    tickers = list(symbols.keys())

    def _download_chunk(chunk: list[str]):
        """Download one chunk with retry + linear backoff. None on total failure."""
        if not _HAS_YFINANCE:
            return None  # no yfinance in this env -> fall through to failover
        for attempt in range(1, retries + 1):
            try:
                raw = yf.download(
                    chunk, period=period, group_by="ticker",
                    progress=False, threads=False,
                )
                if raw is not None and not raw.empty:
                    return raw
            except Exception as e:  # noqa: BLE001 — any fetch error is retryable
                logger.warning(
                    "yfinance bond chunk %s attempt %d/%d failed: %s",
                    chunk, attempt, retries, e,
                )
            if attempt < retries:
                time.sleep(2 * attempt)
        return None

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        raw = _download_chunk(chunk)
        if raw is None:
            logger.warning("Bond chunk %s — no data after %d retries", chunk, retries)
            continue

        for symbol in chunk:
            try:
                if len(chunk) == 1:
                    df = raw
                else:
                    df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None

                if df is None or df.empty or len(df) < 60:
                    logger.warning(
                        "Bond %s: insufficient data (%d bars)",
                        symbol, len(df) if df is not None else 0,
                    )
                    continue

                df = df.dropna(subset=["Close"])
                if len(df) < 60:
                    continue

                data[symbol] = df
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Bond {symbol}: data error — {e}")
                continue

    # Failover: yfinance is blocked from GitHub Actions runner IPs, so in CI
    # the chunks above yield nothing. Fill any missing symbol from Tiingo /
    # Polygon (no-op when no key is configured).
    missing = [s for s in tickers if s not in data]
    if missing:
        try:
            from ohlcv_failover import (  # type: ignore
                fetch_ohlcv_failover, failover_available, POLYGON_RATE_SLEEP,
            )
        except ImportError:
            from alpha_engine.ohlcv_failover import (  # type: ignore
                fetch_ohlcv_failover, failover_available, POLYGON_RATE_SLEEP,
            )
        if failover_available():
            logger.info("Bond: %d symbols missing from yfinance — trying failover",
                        len(missing))
            for idx, symbol in enumerate(missing):
                provider = "none"
                try:
                    df, provider = fetch_ohlcv_failover(symbol)
                    if df is not None and len(df) >= 60:
                        data[symbol] = df
                except Exception as e:  # noqa: BLE001
                    logger.warning("Bond %s: failover error — %s", symbol, e)
                # Pace requests: Polygon free tier needs ~13s; Tiingo does not.
                if idx < len(missing) - 1:
                    time.sleep(POLYGON_RATE_SLEEP if provider == "polygon" else 0.4)

    logger.info(f"Bond data fetched: {len(data)}/{len(symbols)} symbols")
    return data


def _fred_rows_to_series(rows: list) -> pd.Series:
    """Convert FRED list[{"date": "YYYY-MM-DD", "value": float}] to pd.Series indexed by date."""
    if not rows:
        return pd.Series(dtype=float)
    dates = pd.to_datetime([r["date"] for r in rows])
    vals = [r["value"] for r in rows]
    return pd.Series(vals, index=dates, dtype=float).sort_index()


def _convert_fred_bundle(bundle: dict) -> dict:
    """Convert fetch_bond_bundle() output (list[dict] per series) to pd.Series per series."""
    return {sid: _fred_rows_to_series(rows) for sid, rows in bundle.items()}


def run_bond_scanner(merge: bool = False) -> list[dict]:
    """Run all bond strategies and return signals.

    Args:
        merge: If True, also merge results into active_picks.json

    Returns:
        List of signal dicts
    """
    logger.info("Bond Scanner starting — %d strategies, %d symbols",
                len(STRATEGIES), len(BOND_SYMBOLS))

    # Fetch OHLCV data
    data = fetch_bond_data(BOND_SYMBOLS)
    LAST_RUN_DIAGNOSTICS["symbols_requested"] = len(BOND_SYMBOLS)
    LAST_RUN_DIAGNOSTICS["symbols_loaded"] = len(data)
    LAST_RUN_DIAGNOSTICS["raw_signals"] = 0
    if not data:
        logger.warning("No bond ETF data available — aborting scan")
        return []

    # Fetch FRED macro data (optional enrichment).
    # fetch_bond_bundle returns dict[str, list[dict]]; convert to dict[str, pd.Series]
    # so that bond_yield_curve_slope (and other FRED-aware strategies) can use real data
    # instead of the price-proxy fallback (B-003 wire-up).
    fred_data = None
    if fetch_bond_bundle:
        try:
            raw_bundle = fetch_bond_bundle(lookback_days=365)
            fred_data = _convert_fred_bundle(raw_bundle)
            populated = sum(1 for s in fred_data.values() if not s.empty)
            logger.info("FRED data fetched: %d/%d series populated", populated, len(fred_data))
        except Exception as e:
            logger.warning(f"FRED data fetch failed (non-fatal): {e}")

    all_signals = []

    for strategy_name, strategy_fn in STRATEGIES:
        try:
            # Bond strategies accept data dict; some also use fred_data
            import inspect
            sig = inspect.signature(strategy_fn)
            if "fred_data" in sig.parameters and fred_data:
                signals = strategy_fn(data, fred_data=fred_data)
            else:
                signals = strategy_fn(data)

            if not signals:
                logger.info(f"Bond strategy {strategy_name}: 0 signals")
                continue

            # Tag and limit
            for s in signals[:MAX_PICKS_PER_STRATEGY]:
                s["asset_class"] = "BOND"
                s["strategy"] = strategy_name
                s["source_system"] = "bond_scanner"
                s["timestamp"] = _now_iso()
                s["allocation"] = DEFAULT_ALLOCATION * STRATEGY_WEIGHT_OVERRIDES.get(strategy_name, 1.0)
                all_signals.append(s)

            logger.info(f"Bond strategy {strategy_name}: {len(signals)} signals, {min(len(signals), MAX_PICKS_PER_STRATEGY)} kept")

        except Exception as e:
            logger.error(f"Bond strategy {strategy_name} failed: {e}", exc_info=True)
            continue

    # Sanitize
    all_signals = _sanitize_for_json(all_signals)
    LAST_RUN_DIAGNOSTICS["raw_signals"] = len(all_signals)

    # Save to JSON
    _save_bond_picks(all_signals)

    # Optionally merge into main active_picks
    if merge and all_signals:
        _merge_into_active_picks(all_signals)

    logger.info("Bond Scanner complete: %d total signals", len(all_signals))
    return all_signals


def _save_bond_picks(signals: list[dict]) -> None:
    """Save bond picks to dedicated JSON file."""
    output = {
        "generated_at": _now_iso(),
        "source": "bond_scanner",
        "count": len(signals),
        "picks": signals,
    }
    BOND_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOND_PICKS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Saved {len(signals)} bond picks to {BOND_PICKS_PATH}")
    try:
        _BOND_PICKS_SCANNER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_BOND_PICKS_SCANNER_PATH, "w", encoding="utf-8") as _sf:
            json.dump(output, _sf, indent=2, default=str)
    except Exception as _e:
        logger.debug("Secondary scanner_output write failed (non-fatal): %s", _e)


def _merge_into_active_picks(signals: list[dict]) -> None:
    """Merge bond signals into the main active_picks.json.

    Reads existing picks, removes old bond scanner picks (same strategy+symbol),
    appends new ones, writes back.
    """
    active_picks_path = DATA_DIR / "active_picks.json"

    # Load existing
    existing = []
    if active_picks_path.exists():
        try:
            with open(active_picks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing = data
                elif isinstance(data, dict) and "picks" in data:
                    existing = data["picks"]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load existing active_picks.json: {e}")

    # Remove old bond scanner picks (same strategy + symbol)
    new_keys = {(s.get("strategy"), s.get("symbol")) for s in signals}
    existing = [
        p for p in existing
        if not (p.get("source_system") == "bond_scanner" and
                (p.get("strategy"), p.get("symbol")) in new_keys)
    ]

    # Append new
    existing.extend(signals)

    # Write back
    try:
        with open(active_picks_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, default=str)
        logger.info(f"Merged {len(signals)} bond picks into {active_picks_path} (total: {len(existing)})")
    except OSError as e:
        logger.error(f"Failed to write active_picks.json: {e}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Bond Signal Scanner")
    parser.add_argument("--merge", action="store_true",
                        help="Merge signals into active_picks.json")
    args = parser.parse_args()

    signals = run_bond_scanner(merge=args.merge)
    print(f"Bond Scanner: {len(signals)} signals generated")
    for s in signals:
        print(f"  {s.get('strategy')}: {s.get('signal_type')} {s.get('symbol')} "
              f"@ {s.get('entry_price')} (conf={s.get('confidence')})")

    # ── fail-open guard ────────────────────────────────────────────────────
    # Distinguish a data-provider outage from a genuinely empty market so the
    # GitHub Actions status UI stops lying. Mirrors the ratio logic in the
    # *-agent.yml inline scanners. infra_fragility_audit_2026_05_18.md §B.
    _requested = max(1, LAST_RUN_DIAGNOSTICS["symbols_requested"])
    _loaded = LAST_RUN_DIAGNOSTICS["symbols_loaded"]
    _ratio = _loaded / _requested
    if _ratio < 0.5:
        print(f"::error::DATA FETCH FAILURE — only {_loaded}/{_requested} bond "
              f"symbols loaded (yfinance empty/delisted, failover exhausted); "
              f"refusing to exit green on missing data")
        sys.exit(1)
    if len(signals) == 0:
        print(f"::warning::Bond scanner produced 0 signals on healthy data "
              f"({_loaded}/{_requested} symbols loaded) — real-empty market, "
              f"not a data failure")
