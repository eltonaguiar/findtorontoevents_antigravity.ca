#!/usr/bin/env python3
"""
ALPHA_ENGINE -- ETF Signal Scanner
====================================
Runs ETF rotation and trend-following strategies, emits picks to
active_picks_etf.json for merge into the main active_picks pipeline.

Strategies:
  1. Dual Momentum (Antonacci 2014) — absolute + relative 12m momentum
  2. Sector Momentum (Faber 2007) — 10-month SMA filter + 3m sector rotation
  3. Risk-On/Off — regime-based allocation (TLT/SPY inverse correlation)
  4. Trend Following (Kirby & Ostdiek 2012) — SMA crossover on ETF baskets

Run via cron:
  python -m alpha_engine.etf_scanner              # Generate signals only
  python -m alpha_engine.etf_scanner --merge      # Generate + merge into active_picks.json

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
    ETF_SYMBOLS,
    CATEGORY_RISK,
    MAX_PICKS_PER_STRATEGY,
    STRATEGY_WEIGHT_OVERRIDES,
    DEFAULT_ALLOCATION,
)

# Import ETF strategies.
# The risk-on/off strategy is defined as `etf_risk_parity_rotation` in
# etf_strategies.py (its docstring: "SPY/TLT risk-on/off regime rotation"),
# but the scanner + quality_gates.py register it under the name
# `etf_risk_on_off`. Alias on import so the registered name is preserved
# and the long-standing ImportError (scanner failed every run) is fixed.
try:
    from alpha_engine.etf_strategies import (
        etf_dual_momentum,
        etf_sector_momentum,
        etf_risk_parity_rotation as etf_risk_on_off,
        etf_trend_following,
        etf_faber_tactical,
        etf_rsi2_pullback,
        etf_sector_dual_momentum,
        etf_cross_sectional_momentum,
    )
except ImportError:
    from etf_strategies import (
        etf_dual_momentum,
        etf_sector_momentum,
        etf_risk_parity_rotation as etf_risk_on_off,
        etf_trend_following,
        etf_faber_tactical,
        etf_rsi2_pullback,
        etf_sector_dual_momentum,
        etf_cross_sectional_momentum,
    )

# Optional: yfinance for data fetching
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
ETF_PICKS_PATH = OUTPUT_DIR / "active_picks_etf.json"

STRATEGIES = [
    ("etf_dual_momentum", etf_dual_momentum),
    ("etf_sector_momentum", etf_sector_momentum),
    ("etf_risk_on_off", etf_risk_on_off),
    ("etf_trend_following", etf_trend_following),
    ("etf_faber_tactical", etf_faber_tactical),
    ("etf_rsi2_pullback", etf_rsi2_pullback),
    # E-002 (2026-05-18): Antonacci dual momentum — absolute + relative vs SPY
    # Academic basis: Antonacci (2014) — 75%+ winning months, Sharpe ~0.95
    ("etf_sector_dual_momentum", etf_sector_dual_momentum),
    # H-003 (2026-05-18): Cross-sectional 12-1 momentum on 20-ETF universe
    # Academic basis: Jegadeesh & Titman (1993) — momentum; skip-last-month reversal fix.
    # Top 3 positive-momentum ETFs ranked by 12m-1m return. Gate: ETF_CS_MOM_ENABLED.
    ("etf_cross_sectional_momentum", etf_cross_sectional_momentum),
]

# Last-run data-fetch diagnostics. Populated by run_etf_scanner() so the CLI
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


def fetch_etf_data(
    symbols: dict[str, dict],
    period: str = "2y",
    chunk_size: int = 12,
    retries: int = 3,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for ETF symbols via yfinance.

    Returns dict of symbol -> DataFrame with columns: Open, High, Low, Close, Volume.

    A single 84-ticker batch download is fragile on GitHub Actions runners —
    Yahoo rate-limits the shared runner IPs and the whole batch comes back
    empty (observed: scanner emitted 0 signals in CI while fetching 84/84
    locally). Download in small chunks, each with retry + backoff, and keep
    whatever partial data succeeds rather than aborting the entire scan.
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
                    "yfinance chunk %s attempt %d/%d failed: %s",
                    chunk, attempt, retries, e,
                )
            if attempt < retries:
                time.sleep(2 * attempt)
        return None

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        raw = _download_chunk(chunk)
        if raw is None:
            logger.warning("ETF chunk %s — no data after %d retries", chunk, retries)
            continue

        for symbol in chunk:
            try:
                if len(chunk) == 1:
                    df = raw
                else:
                    df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None

                if df is None or df.empty or len(df) < 60:
                    logger.warning(
                        "ETF %s: insufficient data (%d bars)",
                        symbol, len(df) if df is not None else 0,
                    )
                    continue

                # Drop NaN rows
                df = df.dropna(subset=["Close"])
                if len(df) < 60:
                    continue

                data[symbol] = df
            except Exception as e:  # noqa: BLE001
                logger.warning(f"ETF {symbol}: data error — {e}")
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
            logger.info("ETF: %d symbols missing from yfinance — trying failover",
                        len(missing))
            for idx, symbol in enumerate(missing):
                provider = "none"
                try:
                    df, provider = fetch_ohlcv_failover(symbol)
                    if df is not None and len(df) >= 60:
                        data[symbol] = df
                except Exception as e:  # noqa: BLE001
                    logger.warning("ETF %s: failover error — %s", symbol, e)
                # Pace requests: Polygon free tier needs ~13s; Tiingo does not.
                if idx < len(missing) - 1:
                    time.sleep(POLYGON_RATE_SLEEP if provider == "polygon" else 0.4)

    logger.info(f"ETF data fetched: {len(data)}/{len(symbols)} symbols")
    return data


def run_etf_scanner(merge: bool = False) -> list[dict]:
    """Run all ETF strategies and return signals.

    Args:
        merge: If True, also merge results into active_picks.json

    Returns:
        List of signal dicts
    """
    logger.info("ETF Scanner starting — %d strategies, %d symbols",
                len(STRATEGIES), len(ETF_SYMBOLS))

    # Fetch data
    data = fetch_etf_data(ETF_SYMBOLS)
    LAST_RUN_DIAGNOSTICS["symbols_requested"] = len(ETF_SYMBOLS)
    LAST_RUN_DIAGNOSTICS["symbols_loaded"] = len(data)
    LAST_RUN_DIAGNOSTICS["raw_signals"] = 0
    if not data:
        logger.warning("No ETF data available — aborting scan")
        return []

    all_signals = []

    for strategy_name, strategy_fn in STRATEGIES:
        try:
            signals = strategy_fn(data)
            if not signals:
                logger.info(f"ETF strategy {strategy_name}: 0 signals")
                continue

            # Tag and limit
            for sig in signals[:MAX_PICKS_PER_STRATEGY]:
                sig["asset_class"] = "ETF"
                sig["strategy"] = strategy_name
                sig["source_system"] = "etf_scanner"
                sig["timestamp"] = _now_iso()
                sig["allocation"] = DEFAULT_ALLOCATION * STRATEGY_WEIGHT_OVERRIDES.get(strategy_name, 1.0)
                all_signals.append(sig)

            logger.info(f"ETF strategy {strategy_name}: {len(signals)} signals, {min(len(signals), MAX_PICKS_PER_STRATEGY)} kept")

        except Exception as e:
            logger.error(f"ETF strategy {strategy_name} failed: {e}", exc_info=True)
            continue

    # Sanitize
    all_signals = _sanitize_for_json(all_signals)
    LAST_RUN_DIAGNOSTICS["raw_signals"] = len(all_signals)

    # Save to JSON
    _save_etf_picks(all_signals)

    # Optionally merge into main active_picks
    if merge and all_signals:
        _merge_into_active_picks(all_signals)

    logger.info("ETF Scanner complete: %d total signals", len(all_signals))
    return all_signals


def _save_etf_picks(signals: list[dict]) -> None:
    """Save ETF picks to dedicated JSON file."""
    output = {
        "generated_at": _now_iso(),
        "source": "etf_scanner",
        "count": len(signals),
        "picks": signals,
    }
    ETF_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ETF_PICKS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Saved {len(signals)} ETF picks to {ETF_PICKS_PATH}")


def _merge_into_active_picks(signals: list[dict]) -> None:
    """Merge ETF signals into the main active_picks.json.

    Reads existing picks, removes old ETF scanner picks (same strategy+symbol),
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

    # Remove old ETF scanner picks (same strategy + symbol)
    new_keys = {(s.get("strategy"), s.get("symbol")) for s in signals}
    existing = [
        p for p in existing
        if not (p.get("source_system") == "etf_scanner" and
                (p.get("strategy"), p.get("symbol")) in new_keys)
    ]

    # Normalise fields required by the outcome_resolver before appending:
    #   id — resolver skips picks with empty id in the DB update loop
    #   direction — resolver needs LONG/SHORT (not signal_type BUY/SELL) for TP/SL scan
    #   status — resolver's is_unresolved() only acts on recognised statuses
    import hashlib as _hashlib
    for s in signals:
        if not s.get("id"):
            raw = f"{s.get('symbol')}-{s.get('strategy')}-{s.get('signal_type','')}-{s.get('timestamp','')}"
            s["id"] = "etf-" + _hashlib.md5(raw.encode()).hexdigest()[:12]
        if not s.get("direction"):
            sig = str(s.get("signal_type", "")).upper()
            s["direction"] = "LONG" if sig in ("BUY", "LONG") else "SHORT"
        if not s.get("status"):
            s["status"] = "OPEN"

    # Append new
    existing.extend(signals)

    # Write back
    try:
        with open(active_picks_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, default=str)
        logger.info(f"Merged {len(signals)} ETF picks into {active_picks_path} (total: {len(existing)})")
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

    parser = argparse.ArgumentParser(description="ETF Signal Scanner")
    parser.add_argument("--merge", action="store_true",
                        help="Merge signals into active_picks.json")
    args = parser.parse_args()

    signals = run_etf_scanner(merge=args.merge)
    print(f"ETF Scanner: {len(signals)} signals generated")
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
        print(f"::error::DATA FETCH FAILURE — only {_loaded}/{_requested} ETF "
              f"symbols loaded (yfinance empty/delisted, failover exhausted); "
              f"refusing to exit green on missing data")
        sys.exit(1)
    if len(signals) == 0:
        print(f"::warning::ETF scanner produced 0 signals on healthy data "
              f"({_loaded}/{_requested} symbols loaded) — real-empty market, "
              f"not a data failure")
