#!/usr/bin/env python3
"""
Regime-Switching Composite Allocator
=====================================
Dynamically allocates strategy weights based on BTC volatility regime.

Backtest evidence:
  Battleground:  PF 3.14 in ranging,  PF 1.20 in high-vol
  Alpha Engine:  PF 0.41 in ranging,  PF 2.01 in high-vol
  LuxAlgo:       Limited data, held constant across regimes

By switching weights per regime, theoretical composite PF rises from ~1.5 to ~2.5.

Regime classification:
  - Ranging:         BTC 14-day annualized vol < 60%
  - High Volatility: BTC 14-day annualized vol >= 60%
  - Transition:      Within 48h of a regime threshold crossing

API failover: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare
State persistence: alpha_engine/data/regime_allocator_state.json
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

_log = logging.getLogger("alpha_engine.regime_allocator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BTC_VOL_THRESHOLD = 0.60  # 60% annualized
TRANSITION_WINDOW_SECONDS = 48 * 3600  # 48 hours
VOL_WINDOW_DAYS = 14

STATE_DIR = Path(__file__).resolve().parent / "data"
STATE_FILE = STATE_DIR / "regime_allocator_state.json"

# ---------------------------------------------------------------------------
# Allocation tables
# ---------------------------------------------------------------------------
ALLOCATIONS = {
    "ranging": {
        "battleground": 1.5,   # PF 3.14 -- dominant
        "alpha_engine": 0.0,   # PF 0.41 -- destructive, disabled
        "luxalgo": 0.3,        # limited, needs more validation
    },
    "high_volatility": {
        "battleground": 0.7,   # PF 1.20 -- decent but not dominant
        "alpha_engine": 1.2,   # PF 2.01 -- dominant
        "luxalgo": 0.3,        # limited
    },
    "transition": {
        "battleground": 1.0,
        "alpha_engine": 0.5,
        "luxalgo": 0.3,
    },
}

# ---------------------------------------------------------------------------
# BTC price fetching (multi-source failover)
# ---------------------------------------------------------------------------
_BINANCE_KLINE_URLS = [
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
    "https://api2.binance.com/api/v3/klines",
    "https://api3.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
]

_COINGECKO_BTC_CHART = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
_KUCOIN_KLINES = "https://api.kucoin.com/api/v1/market/candles"
_CRYPTOCOMPARE_HISTODAY = "https://min-api.cryptocompare.com/data/v2/histoday"


def _url_fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from URL using stdlib only."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RegimeAllocator/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        _log.debug("Fetch failed for %s: %s", url, exc)
        return None


def _fetch_btc_daily_closes(days: int = 20) -> Optional[list[float]]:
    """Fetch BTC daily close prices with 3+ source failover.

    Returns list of daily closes (oldest first) or None on total failure.
    Chain: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare
    """
    # --- Binance mirrors ---
    for base_url in _BINANCE_KLINE_URLS:
        url = f"{base_url}?symbol=BTCUSDT&interval=1d&limit={days}"
        data = _url_fetch_json(url)
        if isinstance(data, list) and len(data) >= days:
            try:
                return [float(candle[4]) for candle in data]
            except (IndexError, ValueError, TypeError):
                continue

    # --- CoinGecko ---
    url = f"{_COINGECKO_BTC_CHART}?vs_currency=usd&days={days}&interval=daily"
    data = _url_fetch_json(url)
    if isinstance(data, dict):
        prices = data.get("prices", [])
        if len(prices) >= days:
            try:
                return [p[1] for p in prices[-days:]]
            except (IndexError, TypeError):
                pass

    # --- KuCoin ---
    try:
        end_at = int(time.time())
        start_at = end_at - days * 86400
        url = f"{_KUCOIN_KLINES}?type=1day&symbol=BTC-USDT&startAt={start_at}&endAt={end_at}"
        data = _url_fetch_json(url)
        if isinstance(data, dict):
            candles = data.get("data", [])
            if isinstance(candles, list) and len(candles) >= days:
                # KuCoin returns newest first; index 2 = close
                closes = [float(c[2]) for c in candles]
                closes.reverse()
                return closes[-days:]
    except Exception:
        pass

    # --- CryptoCompare ---
    url = f"{_CRYPTOCOMPARE_HISTODAY}?fsym=BTC&tsym=USD&limit={days}"
    data = _url_fetch_json(url)
    if isinstance(data, dict):
        try:
            hist = data.get("Data", {}).get("Data", [])
            if len(hist) >= days:
                return [float(d["close"]) for d in hist[-days:]]
        except (KeyError, TypeError, ValueError):
            pass

    _log.warning("All BTC price sources failed -- cannot determine regime")
    return None


# ---------------------------------------------------------------------------
# Volatility computation
# ---------------------------------------------------------------------------
def _compute_annualized_vol(closes: list[float], window: int = VOL_WINDOW_DAYS) -> float:
    """Compute annualized volatility from daily closes using log returns."""
    if len(closes) < window + 1:
        raise ValueError(f"Need at least {window + 1} closes, got {len(closes)}")

    recent = closes[-(window + 1):]
    log_returns = [math.log(recent[i] / recent[i - 1]) for i in range(1, len(recent))]
    mean_r = sum(log_returns) / len(log_returns)
    variance = sum((r - mean_r) ** 2 for r in log_returns) / (len(log_returns) - 1)
    daily_vol = math.sqrt(variance)
    return daily_vol * math.sqrt(365)


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------
def _load_state() -> dict:
    """Load persisted allocator state."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning("Failed to load state: %s", exc)
    return {}


def _save_state(state: dict) -> None:
    """Persist allocator state."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        # Atomic-ish rename (best effort on Windows)
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        tmp.rename(STATE_FILE)
    except OSError as exc:
        _log.warning("Failed to save state: %s", exc)


# ---------------------------------------------------------------------------
# Core regime detection
# ---------------------------------------------------------------------------
def _classify_regime(btc_vol: float, state: dict) -> tuple[str, dict]:
    """Classify current regime and handle transition detection.

    Returns (regime_name, updated_state).
    """
    now = time.time()
    raw_regime = "high_volatility" if btc_vol >= BTC_VOL_THRESHOLD else "ranging"

    prev_raw = state.get("raw_regime")
    last_transition = state.get("last_transition_ts", 0.0)

    # Detect regime change
    if prev_raw is not None and raw_regime != prev_raw:
        last_transition = now
        _log.info(
            "Regime transition detected: %s -> %s (vol=%.1f%%)",
            prev_raw, raw_regime, btc_vol * 100,
        )

    # If within 48h of a transition, use transition weights
    in_transition = (now - last_transition) < TRANSITION_WINDOW_SECONDS and last_transition > 0
    effective_regime = "transition" if in_transition else raw_regime

    updated_state = {
        "raw_regime": raw_regime,
        "effective_regime": effective_regime,
        "btc_vol": btc_vol,
        "last_transition_ts": last_transition,
        "last_update_ts": now,
    }
    return effective_regime, updated_state


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_current_allocations() -> dict[str, float]:
    """Returns {strategy_name: weight_multiplier} for the current BTC regime.

    Uses cached state if available and fresh (< 1 hour).
    Falls back to transition weights if BTC data unavailable.
    """
    # Check if cached state is fresh enough (< 1 hour)
    state = _load_state()
    now = time.time()
    last_update = state.get("last_update_ts", 0.0)

    if (now - last_update) < 3600 and "effective_regime" in state:
        regime = state["effective_regime"]
        return dict(ALLOCATIONS.get(regime, ALLOCATIONS["transition"]))

    # Fetch fresh data
    closes = _fetch_btc_daily_closes(days=VOL_WINDOW_DAYS + 5)
    if closes is None:
        _log.warning("Cannot fetch BTC prices -- using transition weights as safe default")
        return dict(ALLOCATIONS["transition"])

    btc_vol = _compute_annualized_vol(closes, VOL_WINDOW_DAYS)
    regime, new_state = _classify_regime(btc_vol, state)
    _save_state(new_state)

    _log.info(
        "Regime: %s | BTC vol: %.1f%% | Weights: %s",
        regime, btc_vol * 100, ALLOCATIONS[regime],
    )
    return dict(ALLOCATIONS[regime])


def get_regime_info() -> dict:
    """Returns full regime information including current weights.

    {
        "regime": str,           # "ranging" | "high_volatility" | "transition"
        "raw_regime": str,       # underlying regime without transition buffer
        "btc_vol": float,        # 14-day annualized vol (0.0-N)
        "btc_vol_pct": str,      # human-readable percentage
        "threshold": float,      # 0.60
        "last_transition": float, # unix timestamp of last regime change
        "last_update": float,    # unix timestamp of last computation
        "weights": dict,         # {strategy: multiplier}
    }
    """
    # Force a fresh computation
    closes = _fetch_btc_daily_closes(days=VOL_WINDOW_DAYS + 5)
    state = _load_state()

    if closes is None:
        # Return whatever we have cached, or defaults
        return {
            "regime": state.get("effective_regime", "unknown"),
            "raw_regime": state.get("raw_regime", "unknown"),
            "btc_vol": state.get("btc_vol", 0.0),
            "btc_vol_pct": f"{state.get('btc_vol', 0.0) * 100:.1f}%",
            "threshold": BTC_VOL_THRESHOLD,
            "last_transition": state.get("last_transition_ts", 0.0),
            "last_update": state.get("last_update_ts", 0.0),
            "weights": dict(ALLOCATIONS.get(state.get("effective_regime", "transition"), ALLOCATIONS["transition"])),
            "error": "Could not fetch fresh BTC data",
        }

    btc_vol = _compute_annualized_vol(closes, VOL_WINDOW_DAYS)
    regime, new_state = _classify_regime(btc_vol, state)
    _save_state(new_state)

    return {
        "regime": regime,
        "raw_regime": new_state["raw_regime"],
        "btc_vol": btc_vol,
        "btc_vol_pct": f"{btc_vol * 100:.1f}%",
        "threshold": BTC_VOL_THRESHOLD,
        "last_transition": new_state["last_transition_ts"],
        "last_update": new_state["last_update_ts"],
        "weights": dict(ALLOCATIONS[regime]),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    info = get_regime_info()
    print()
    print("=" * 60)
    print("  REGIME-SWITCHING COMPOSITE ALLOCATOR")
    print("=" * 60)
    print(f"  Regime:          {info['regime']}")
    print(f"  Raw regime:      {info['raw_regime']}")
    print(f"  BTC 14d vol:     {info['btc_vol_pct']}")
    print(f"  Threshold:       {info['threshold'] * 100:.0f}%")
    print()
    print("  Strategy Weights:")
    for strat, weight in info["weights"].items():
        status = "DISABLED" if weight == 0.0 else f"{weight:.1f}x"
        print(f"    {strat:20s} {status}")
    print("=" * 60)
    print()
