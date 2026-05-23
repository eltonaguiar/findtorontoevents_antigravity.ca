"""
regime_bridge.py — Regime Terminal Bridge
==========================================
Converts 7-state HMM regime data to formats consumed by:
  1. KIMI Rise of the Claw (STOCKS/competition/.regime_cache.json)
  2. Alpha Engine (per-symbol regime labels)
  3. Any future consumers

Run: python -m regime_terminal.regime_bridge
Called after live_regime.py in the GitHub Actions pipeline.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths
REGIME_STATE = Path(__file__).parent / "data" / "regime_state.json"
KIMI_CACHE = Path(__file__).parent.parent / "STOCKS" / "competition" / ".regime_cache.json"
ALPHA_REGIME = Path(__file__).parent.parent / "alpha_engine" / "data" / "hmm_regime.json"

# 7-state → 3-state mapping for KIMI
REGIME_TO_KIMI = {
    "Strong Bull": "bull",
    "Mild Bull": "bull",
    "Accumulation": "neutral",  # Accumulation could go either way
    "Chop/Neutral": "neutral",
    "Mild Bear": "bear",
    "Strong Bear": "bear",
    "Crash": "bear",
}

# 7-state → crypto regime mapping
REGIME_TO_CRYPTO = {
    "Strong Bull": "risk_on",
    "Mild Bull": "risk_on",
    "Accumulation": "neutral",
    "Chop/Neutral": "neutral",
    "Mild Bear": "neutral",
    "Strong Bear": "defensive",
    "Crash": "defensive",
}

# 7-state → Alpha Engine regime mapping
REGIME_TO_ALPHA = {
    "Strong Bull": "trending",
    "Mild Bull": "trending",
    "Accumulation": "transitional",
    "Chop/Neutral": "ranging",
    "Mild Bear": "trending",
    "Strong Bear": "trending",
    "Crash": "transitional",
}

# Leverage recommendations from HMM
REGIME_LEVERAGE = {
    "Strong Bull": 2.5,
    "Mild Bull": 1.5,
    "Accumulation": 1.0,
    "Chop/Neutral": 0.5,
    "Mild Bear": -1.0,
    "Strong Bear": -1.5,
    "Crash": -2.0,
}


def load_regime_state() -> dict:
    """Load the latest HMM regime state."""
    if not REGIME_STATE.exists():
        print(f"  [WARN] No regime state at {REGIME_STATE}")
        return {}
    with open(REGIME_STATE) as f:
        return json.load(f)


def compute_aggregate_regime(state: dict) -> tuple[str, str, float, float]:
    """
    Compute aggregate market regime from individual ticker regimes.
    Uses SPY as primary for stocks regime, BTC-USD for crypto.

    Returns: (market_regime, crypto_regime, hmm_confidence, vol_20d_proxy)
    """
    regimes = state.get("regimes", {})

    # Get SPY regime (primary market indicator)
    spy_result = None
    for cat in ("stocks", "indices"):
        if cat in regimes and "SPY" in regimes[cat]:
            spy_result = regimes[cat]["SPY"]
            break

    # Get BTC regime (primary crypto indicator)
    btc_result = None
    if "crypto" in regimes and "BTC-USD" in regimes["crypto"]:
        btc_result = regimes["crypto"]["BTC-USD"]

    # Market regime from SPY
    if spy_result:
        market_regime = REGIME_TO_KIMI.get(spy_result.get("regime", ""), "neutral")
        hmm_confidence = spy_result.get("confidence", 0.5)
        vol_20d = spy_result.get("volatility_30d", 0.01)
    else:
        # Fallback: aggregate from overview
        overview = state.get("market_overview", {})
        bull = overview.get("bull_count", 0)
        bear = overview.get("bear_count", 0)
        total = overview.get("total_scanned", 1)

        if bull > bear * 1.5:
            market_regime = "bull"
        elif bear > bull * 1.5:
            market_regime = "bear"
        else:
            market_regime = "neutral"
        hmm_confidence = max(bull, bear) / total if total > 0 else 0.5
        vol_20d = 0.015

    # Crypto regime from BTC
    if btc_result:
        crypto_regime = REGIME_TO_CRYPTO.get(btc_result.get("regime", ""), "neutral")
    else:
        overview = state.get("market_overview", {})
        bear = overview.get("bear_count", 0)
        total = overview.get("total_scanned", 1)
        if bear / total > 0.6:
            crypto_regime = "defensive"
        elif bear / total < 0.3:
            crypto_regime = "risk_on"
        else:
            crypto_regime = "neutral"

    return market_regime, crypto_regime, hmm_confidence, vol_20d


def compute_per_symbol_regimes(state: dict) -> dict:
    """
    Build per-symbol regime data for Alpha Engine.

    Returns: {symbol: {regime, alpha_regime, confidence, leverage, signal}}
    """
    regimes = state.get("regimes", {})
    per_symbol = {}

    for category, tickers in regimes.items():
        for ticker, result in tickers.items():
            raw_regime = result.get("regime", "Chop/Neutral")
            per_symbol[ticker] = {
                "regime": raw_regime,
                "kimi_regime": REGIME_TO_KIMI.get(raw_regime, "neutral"),
                "alpha_regime": REGIME_TO_ALPHA.get(raw_regime, "ranging"),
                "confidence": result.get("confidence", 0.5),
                "leverage": REGIME_LEVERAGE.get(raw_regime, 1.0),
                "signal": result.get("signal", "FLAT"),
                "confirmations": result.get("confirmations", 0),
                "rsi": result.get("rsi"),
                "category": category,
            }

    return per_symbol


def get_btc_eth_ratio(state: dict) -> float:
    """Extract BTC/ETH price ratio from regime state."""
    regimes = state.get("regimes", {})
    btc_price = 0
    eth_price = 0

    if "crypto" in regimes:
        btc_data = regimes["crypto"].get("BTC-USD", {})
        eth_data = regimes["crypto"].get("ETH-USD", {})
        btc_price = btc_data.get("price", 0)
        eth_price = eth_data.get("price", 0)

    if btc_price > 0 and eth_price > 0:
        return round(btc_price / eth_price, 4)
    return 1.0  # fallback


def write_kimi_cache(state: dict):
    """Write KIMI-compatible .regime_cache.json."""
    market_regime, crypto_regime, hmm_conf, vol_20d = compute_aggregate_regime(state)
    btc_eth_ratio = get_btc_eth_ratio(state)

    cache = {
        "regime": market_regime,
        "crypto_regime": crypto_regime,
        "hmm_confidence": round(hmm_conf, 4),
        "vol_20d": round(vol_20d, 6),
        "btc_eth_ratio": btc_eth_ratio,
        "source": "regime_terminal_hmm_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hmm_detail": {
            "n_regimes": state.get("config", {}).get("n_regimes", 7),
            "engine": state.get("engine", "GaussianHMM"),
            "market_overview": state.get("market_overview", {}),
        },
    }

    KIMI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(KIMI_CACHE, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"  → KIMI cache written: {KIMI_CACHE}")
    print(f"    regime={market_regime} crypto={crypto_regime} conf={hmm_conf:.2%} vol={vol_20d:.4f}")


def write_alpha_regime(state: dict):
    """Write Alpha Engine per-symbol regime data."""
    per_symbol = compute_per_symbol_regimes(state)
    market_regime, crypto_regime, hmm_conf, vol_20d = compute_aggregate_regime(state)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "regime_terminal_hmm_v1",
        "aggregate": {
            "market_regime": market_regime,
            "crypto_regime": crypto_regime,
            "hmm_confidence": round(hmm_conf, 4),
        },
        "per_symbol": per_symbol,
        "market_overview": state.get("market_overview", {}),
    }

    ALPHA_REGIME.parent.mkdir(parents=True, exist_ok=True)
    with open(ALPHA_REGIME, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  → Alpha regime written: {ALPHA_REGIME}")
    print(f"    {len(per_symbol)} symbols with HMM regime data")


def bridge():
    """Run the full regime bridge."""
    print("=" * 60)
    print("  REGIME BRIDGE — HMM → KIMI + Alpha Engine")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    state = load_regime_state()
    if not state:
        print("  No regime state available. Skipping bridge.")
        return

    print(f"\n  Source: regime_state.json ({state.get('generated_at', 'unknown')})")
    overview = state.get("market_overview", {})
    print(f"  Markets: {overview.get('total_scanned', 0)} | "
          f"Bull: {overview.get('bull_count', 0)} | "
          f"Bear: {overview.get('bear_count', 0)} | "
          f"Neutral: {overview.get('neutral_count', 0)}")

    print("\n  [1/2] Writing KIMI regime cache...")
    write_kimi_cache(state)

    print("\n  [2/2] Writing Alpha Engine regime data...")
    write_alpha_regime(state)

    print("\n  Bridge complete.")
    print("=" * 60)


if __name__ == "__main__":
    bridge()
