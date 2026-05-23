"""
Skyrocket Detector — Live Detection Entry Point
=================================================
Scans all configured symbols for skyrocket signals using the trained model.
Uses the shared multi_source_fetcher for API failover (OKX -> CoinGecko ->
Kraken -> CryptoCompare -> Binance -> yfinance).

Dynamic Universe Expansion (Gap #5):
  Core 30 symbols are always scanned.  Up to 50 additional symbols are
  pulled from alpha_engine/data/dynamic_universe.json, CoinGecko trending,
  and Binance 24h top gainers -- capped at 80 total.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

# Add project root to path for shared imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from skyrocket_detector import config
from skyrocket_detector.feature_engine import compute_features_for_live, FEATURE_NAMES
from skyrocket_detector.model import SkyrocketModel

# Data directory for alerts
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_MODEL_PATH = os.path.join(_DATA_DIR, "skyrocket_model.joblib")
_ALERTS_PATH = os.path.join(_DATA_DIR, "alerts.json")

# ---------------------------------------------------------------------------
# Dynamic Universe Expansion
# ---------------------------------------------------------------------------
MAX_TOTAL_SYMBOLS = 80
MAX_DYNAMIC_SYMBOLS = 50  # additional symbols beyond the core list

_DYNAMIC_UNIVERSE_PATH = os.path.join(
    _PROJECT_ROOT, "alpha_engine", "data", "dynamic_universe.json"
)


def _load_dynamic_universe_file(exclude):
    """Read hot symbols from the alpha_engine dynamic universe JSON.

    Args:
        exclude: set of symbols to skip (the core set)

    Returns:
        list of symbol strings sorted by hotness / priority
    """
    try:
        with open(_DYNAMIC_UNIVERSE_PATH, "r") as fh:
            data = json.load(fh)

        # Use the rankings list (sorted by hotness_score) for priority order
        rankings = data.get("rankings", [])
        symbols = []
        for entry in rankings:
            sym = entry.get("symbol", "")
            vol = entry.get("volume_usd", 0)
            if sym and sym.endswith("USDT") and sym not in exclude and vol >= 5_000_000:
                symbols.append(sym)

        # Also pick up dynamic_symbols not already in rankings
        seen = set(symbols)
        for sym in data.get("dynamic_symbols", []):
            if sym and sym.endswith("USDT") and sym not in exclude and sym not in seen:
                symbols.append(sym)
                seen.add(sym)

        print("[detector]   dynamic_universe.json: %d candidates" % len(symbols))
        return symbols
    except FileNotFoundError:
        print("[detector]   dynamic_universe.json not found, skipping")
        return []
    except Exception as exc:
        print("[detector]   dynamic_universe.json error: %s" % exc)
        return []


def _fetch_coingecko_trending(exclude, already_added):
    """Fetch CoinGecko trending coins (free, no API key needed).

    Args:
        exclude: set of core symbols to skip
        already_added: set of dynamic symbols already collected

    Returns:
        list of Binance-format symbol strings
    """
    url = "https://api.coingecko.com/api/v3/search/trending"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SkyrocketDetector/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        symbols = []
        for coin_wrapper in data.get("coins", []):
            item = coin_wrapper.get("item", {})
            ticker = item.get("symbol", "").upper()
            if not ticker:
                continue
            binance_sym = ticker + "USDT"
            if binance_sym not in exclude and binance_sym not in already_added:
                symbols.append(binance_sym)

        print("[detector]   CoinGecko trending: %d candidates" % len(symbols))
        return symbols
    except Exception as exc:
        print("[detector]   CoinGecko trending failed: %s" % exc)
        return []


def _fetch_binance_gainers(exclude, already_added):
    """Fetch Binance 24h top gainers with >10%% gain and >$5M volume.

    Args:
        exclude: set of core symbols to skip
        already_added: set of dynamic symbols already collected

    Returns:
        list of Binance-format symbol strings sorted by volume desc
    """
    endpoints = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://data-api.binance.vision",
    ]

    for base in endpoints:
        try:
            url = base + "/api/v3/ticker/24hr"
            req = urllib.request.Request(url, headers={"User-Agent": "SkyrocketDetector/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                tickers = json.loads(resp.read())

            candidates = []
            for t in tickers:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue
                if sym in exclude or sym in already_added:
                    continue

                try:
                    change_pct = float(t.get("priceChangePercent", 0))
                    quote_vol = float(t.get("quoteVolume", 0))
                except (ValueError, TypeError):
                    continue

                # Filter: >10% gain AND >$5M USDT volume
                if change_pct >= 10.0 and quote_vol >= 5_000_000:
                    candidates.append((sym, change_pct, quote_vol))

            # Sort by volume descending (highest volume = most liquid)
            candidates.sort(key=lambda x: x[2], reverse=True)
            symbols = [c[0] for c in candidates]

            print("[detector]   Binance 24h gainers (>10%%, >$5M vol): %d candidates" % len(symbols))
            return symbols
        except Exception:
            continue

    print("[detector]   Binance 24h gainers: all endpoints failed")
    return []


def _expand_universe(core_symbols):
    """Expand the core symbol list with dynamic symbols from multiple sources.

    Priority order:
      1. alpha_engine/data/dynamic_universe.json  (already curated)
      2. CoinGecko trending coins  (free, no key)
      3. Binance 24h top gainers   (>10%% gain, >$5M volume)

    Always keeps core_symbols intact and caps total at MAX_TOTAL_SYMBOLS.

    Args:
        core_symbols: list of core symbol strings (e.g. config.SYMBOLS)

    Returns:
        list of symbol strings = core + dynamic (deduplicated, capped)
    """
    core_set = set(core_symbols)
    dynamic = []  # ordered list, first = highest priority

    print("[detector] Expanding universe from dynamic sources...")

    # --- Source 1: alpha_engine dynamic_universe.json ---
    dynamic.extend(_load_dynamic_universe_file(core_set))

    # --- Source 2: CoinGecko trending ---
    dynamic.extend(_fetch_coingecko_trending(core_set, set(dynamic)))

    # --- Source 3: Binance 24h gainers ---
    dynamic.extend(_fetch_binance_gainers(core_set, set(dynamic)))

    # Deduplicate (preserving order) and cap
    seen = set(core_set)
    unique_dynamic = []
    for sym in dynamic:
        if sym not in seen:
            seen.add(sym)
            unique_dynamic.append(sym)
        if len(unique_dynamic) >= MAX_DYNAMIC_SYMBOLS:
            break

    expanded = list(core_symbols) + unique_dynamic
    expanded = expanded[:MAX_TOTAL_SYMBOLS]

    n_added = len(expanded) - len(core_symbols)
    print("[detector] Universe expanded: %d core + %d dynamic = %d total" % (
        len(core_symbols), n_added, len(expanded)))
    return expanded


def _fetch_ohlcv(symbol, limit=300):
    """
    Fetch OHLCV data using the shared multi-source fetcher with full failover.

    Args:
        symbol: Binance-format symbol (e.g., "BTCUSDT")
        limit: Number of 1h bars to fetch

    Returns:
        DataFrame with columns [timestamp, open, high, low, close, volume]
        or None if all sources fail.
    """
    try:
        from shared.multi_source_fetcher import fetch_klines
        klines = fetch_klines(symbol, interval="1h", limit=limit)
    except ImportError:
        # Fallback: direct Binance API call if shared module unavailable
        print("[detector] WARNING: shared.multi_source_fetcher not available, using direct API")
        klines = _fetch_binance_direct(symbol, limit)

    if not klines or len(klines) < 30:
        return None

    df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def _fetch_binance_direct(symbol, limit=300):
    """Fallback: fetch from Binance REST API directly."""
    endpoints = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://data-api.binance.vision",
    ]

    for base in endpoints:
        try:
            url = "%s/api/v3/klines?symbol=%s&interval=1h&limit=%d" % (base, symbol, limit)
            req = urllib.request.Request(url, headers={"User-Agent": "SkyrocketDetector/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            if data and isinstance(data, list):
                result = []
                for k in data:
                    result.append([
                        int(k[0]), float(k[1]), float(k[2]),
                        float(k[3]), float(k[4]), float(k[5]),
                    ])
                return result
        except Exception:
            continue
    return []


def scan_symbol(symbol, model):
    """
    Scan a single symbol for skyrocket probability.

    Args:
        symbol: Binance-format symbol
        model: Trained SkyrocketModel instance

    Returns:
        SkyrocketAlert dict if signal is strong enough, else None.
    """
    df = _fetch_ohlcv(symbol, limit=300)
    if df is None:
        print("  [%s] No data available, skipping" % symbol)
        return None

    features = compute_features_for_live(df)
    if features is None:
        print("  [%s] Feature computation failed, skipping" % symbol)
        return None

    # Build feature vector in correct order
    X = pd.DataFrame([features])[FEATURE_NAMES]
    prob = float(model.predict_proba(X)[0])

    # Check thresholds: probability AND volume acceleration
    vol_accel = features.get("vol_accel_6h", 0)
    passes_prob = prob >= config.MIN_CONFIDENCE
    passes_vol = vol_accel >= 1.5

    current_price = float(df["close"].iloc[-1])

    if passes_prob and passes_vol:
        alert = {
            "symbol": symbol,
            "probability": round(prob, 4),
            "current_price": current_price,
            "tp_price": round(current_price * (1 + config.TP_PCT), 8),
            "sl_price": round(current_price * (1 - config.SL_PCT), 8),
            "tp_pct": config.TP_PCT,
            "sl_pct": config.SL_PCT,
            "features": {k: round(v, 4) for k, v in features.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print("  [%s] SKYROCKET ALERT: prob=%.3f vol_accel=%.2f" % (symbol, prob, vol_accel))
        return alert
    else:
        if prob >= 0.5:
            print("  [%s] Near-miss: prob=%.3f vol_accel=%.2f" % (symbol, prob, vol_accel))
        return None


def scan_all_symbols(symbols=None):
    """
    Scan all configured symbols for skyrocket signals.

    Args:
        symbols: Override symbol list (default: dynamically expanded from config.SYMBOLS)

    Returns:
        List of SkyrocketAlert dicts for symbols that triggered.
    """
    if symbols is None:
        symbols = _expand_universe(config.SYMBOLS)

    print("[detector] Scanning %d symbols for skyrocket signals..." % len(symbols))
    print("[detector] Thresholds: prob >= %.2f, vol_accel >= 1.5" % config.MIN_CONFIDENCE)

    # Load model -- auto-train if it doesn't exist
    model = SkyrocketModel()
    if not os.path.exists(_MODEL_PATH):
        print("[detector] No trained model found at %s" % _MODEL_PATH)
        print("[detector] Attempting auto-training from Binance historical data...")
        try:
            from skyrocket_detector.train import train_if_needed
            trained = train_if_needed()
            if not trained:
                print("[detector] Training failed -- cannot scan without a model")
                return []
        except Exception as e:
            print("[detector] Training failed: %s" % e)
            return []

    try:
        model.load(_MODEL_PATH)
    except Exception as e:
        print("[detector] ERROR loading model: %s" % e)
        return []

    alerts = []
    errors = 0

    for i, symbol in enumerate(symbols):
        try:
            alert = scan_symbol(symbol, model)
            if alert is not None:
                alerts.append(alert)
        except Exception as e:
            print("  [%s] ERROR: %s" % (symbol, e))
            errors += 1

        # Rate limiting: small delay between API calls
        if i < len(symbols) - 1:
            time.sleep(0.5)

    print("\n[detector] Scan complete: %d alerts from %d symbols (%d errors)" % (
        len(alerts), len(symbols), errors))

    # Save alerts
    _save_alerts(alerts)

    return alerts


def _save_alerts(alerts):
    """Save alerts to JSON file."""
    os.makedirs(_DATA_DIR, exist_ok=True)

    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "n_alerts": len(alerts),
        "alerts": alerts,
    }

    try:
        with open(_ALERTS_PATH, "w") as f:
            json.dump(output, f, indent=2)
        print("[detector] Alerts saved to %s" % _ALERTS_PATH)
    except Exception as e:
        print("[detector] WARNING: Failed to save alerts: %s" % e)


def main():
    """CLI entry point: scan all symbols and print results as JSON."""
    print("=" * 60)
    print("  SKYROCKET DETECTOR -- Live Scan")
    print("  Time: %s" % datetime.now(timezone.utc).isoformat())
    print("  Core symbols: %d" % len(config.SYMBOLS))
    print("  Max universe: %d (core + dynamic)" % MAX_TOTAL_SYMBOLS)
    print("  Min confidence: %.2f" % config.MIN_CONFIDENCE)
    print("=" * 60)

    alerts = scan_all_symbols()

    if alerts:
        print("\n" + "=" * 60)
        print("  ALERTS SUMMARY")
        print("=" * 60)
        for a in sorted(alerts, key=lambda x: x["probability"], reverse=True):
            print(
                "  %-12s prob=%.3f price=%.4f TP=%.4f SL=%.4f" % (
                    a["symbol"], a["probability"],
                    a["current_price"],
                    a["tp_price"], a["sl_price"])
            )
    else:
        print("\n[detector] No skyrocket signals detected in this scan.")

    # Output as JSON for pipeline consumption
    print("\n--- JSON OUTPUT ---")
    print(json.dumps({"alerts": alerts}, indent=2))


if __name__ == "__main__":
    main()
