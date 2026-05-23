"""
ALPHA_ENGINE -- Regime Sentinel: 4-State On-Chain Cycle Classifier
==================================================================
Transforms the generic 5-state regime into a proper crypto cycle
state machine based on on-chain fundamentals:

  ACCUMULATION -- MVRV<1.0, F&G<25, funding negative  → LONG bias, 2% risk
  MARKUP       -- MVRV 1.0-4.0, F&G 25-60, mild funding → LONG, 1.5% risk
  DISTRIBUTION -- MVRV 4.0-7.0, F&G 60-80, high funding → reduce size, tighten
  MARKDOWN     -- MVRV>7.0 or fast decline, F&G>80      → SHORT bias or CASH

Data sources (all free, no new API keys):
  - MVRV proxy: price / 200d SMA ratio (already in onchain_strategies)
  - Fear & Greed: alternative.me (already in cryptopanic_feargreed)
  - Funding rate: Binance public fapi (already in enhanced_data_feeds)

Reference: Google AG review recommendation -- "lowest effort, highest impact".
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# -- Data fetchers (lightweight, reuse existing patterns) -------------

_BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RegimeSentinel/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8")
            if "json" in ct or raw.strip().startswith(("{", "[")):
                return json.loads(raw)
            return None
    except Exception:
        return None


def fetch_mvrv_proxy(btc_prices: Optional[list[float]] = None) -> float:
    """
    MVRV Z-Score proxy: BTC price / 200d SMA.
    If btc_prices (list of recent 210+ daily closes) provided, compute directly.
    Otherwise fetch from CoinGecko market_chart (free, no key).
    Returns ratio (e.g. 1.35 means 35% above 200d SMA).
    """
    if btc_prices and len(btc_prices) >= 200:
        sma_200 = sum(btc_prices[-200:]) / 200
        return btc_prices[-1] / sma_200 if sma_200 > 0 else 1.0

    # Fallback: fetch from CoinGecko (210 days of daily BTC prices)
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=210&interval=daily"
    data = _fetch_json(url)
    if data and "prices" in data and len(data["prices"]) >= 200:
        prices = [p[1] for p in data["prices"]]
        sma_200 = sum(prices[-200:]) / 200
        return prices[-1] / sma_200 if sma_200 > 0 else 1.0
    return 1.0  # neutral fallback


def fetch_fear_greed() -> int:
    """Fetch current Fear & Greed index (0-100). Returns 50 on failure."""
    data = _fetch_json("https://api.alternative.me/fng/?limit=1")
    if data and isinstance(data, dict) and data.get("data"):
        try:
            return int(data["data"][0]["value"])
        except (KeyError, ValueError, IndexError):
            pass
    return 50


def fetch_funding_rate() -> float:
    """Fetch BTC perpetual funding rate from Binance. Returns 0.0 on failure."""
    for base in _BINANCE_FAPI_BASES:
        data = _fetch_json(f"{base}/fapi/v1/premiumIndex?symbol=BTCUSDT")
        if data and isinstance(data, dict):
            try:
                return float(data.get("lastFundingRate", 0))
            except (TypeError, ValueError):
                pass
    return 0.0


# -- 4-State Classifier ----------------------------------------------

REGIMES = ("ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN")

# Maps sentinel regime -> canonical meta-router regime
SENTINEL_TO_CANONICAL = {
    "ACCUMULATION": "CRASH",          # Extreme fear = CRASH in old system (contrarian buy)
    "MARKUP":       "TRENDING_UP",
    "DISTRIBUTION": "TRENDING_DOWN",  # Start reducing = early bearish
    "MARKDOWN":     "TRENDING_DOWN",
}

# Risk multipliers per regime (applied to position sizing)
RISK_MULTIPLIERS = {
    "ACCUMULATION": 1.3,   # Be aggressive at capitulation
    "MARKUP":       1.0,   # Normal risk
    "DISTRIBUTION": 0.6,   # Reduce size
    "MARKDOWN":     0.3,   # Minimal exposure
}

ACTION_BIAS = {
    "ACCUMULATION": "LONG",
    "MARKUP":       "LONG",
    "DISTRIBUTION": "REDUCE",
    "MARKDOWN":     "SHORT_OR_CASH",
}


def classify_regime(
    mvrv: Optional[float] = None,
    fng: Optional[int] = None,
    funding: Optional[float] = None,
) -> dict:
    """
    Classify crypto market cycle into 4 states.

    Args:
        mvrv: price/200d SMA ratio (None = fetch live)
        fng: Fear & Greed index 0-100 (None = fetch live)
        funding: BTC perpetual funding rate (None = fetch live)

    Returns:
        {
            "regime": "ACCUMULATION"|"MARKUP"|"DISTRIBUTION"|"MARKDOWN",
            "confidence": 0.0-1.0,
            "risk_multiplier": float,
            "action_bias": str,
            "inputs": {"mvrv": ..., "fng": ..., "funding": ...},
            "reasoning": str,
            "timestamp": str,
        }
    """
    # Fetch any missing inputs
    if mvrv is None:
        mvrv = fetch_mvrv_proxy()
    if fng is None:
        fng = fetch_fear_greed()
    if funding is None:
        funding = fetch_funding_rate()

    # Score each axis (0-3 maps to ACCUMULATION..MARKDOWN)
    # MVRV scoring
    if mvrv < 1.0:
        mvrv_score = 0  # ACCUMULATION zone
    elif mvrv < 4.0:
        mvrv_score = 1  # MARKUP zone
    elif mvrv < 7.0:
        mvrv_score = 2  # DISTRIBUTION zone
    else:
        mvrv_score = 3  # MARKDOWN zone

    # F&G scoring (inverted: low F&G = accumulation)
    if fng < 25:
        fng_score = 0
    elif fng < 60:
        fng_score = 1
    elif fng < 80:
        fng_score = 2
    else:
        fng_score = 3

    # Funding rate scoring
    # Negative funding = shorts paying = accumulation signal
    # High positive = overleveraged longs = distribution/markdown
    if funding < -0.0001:
        fund_score = 0
    elif funding < 0.0003:
        fund_score = 1
    elif funding < 0.0008:
        fund_score = 2
    else:
        fund_score = 3

    # Weighted average: MVRV is most reliable (50%), F&G (30%), funding (20%)
    weighted = mvrv_score * 0.50 + fng_score * 0.30 + fund_score * 0.20

    # Map continuous score to discrete regime
    if weighted < 0.75:
        regime = "ACCUMULATION"
    elif weighted < 1.75:
        regime = "MARKUP"
    elif weighted < 2.5:
        regime = "DISTRIBUTION"
    else:
        regime = "MARKDOWN"

    # Confidence: how much the three axes agree
    scores = [mvrv_score, fng_score, fund_score]
    spread = max(scores) - min(scores)
    if spread == 0:
        confidence = 0.95  # Perfect agreement
    elif spread == 1:
        confidence = 0.75  # Adjacent disagreement
    elif spread == 2:
        confidence = 0.55  # Moderate disagreement
    else:
        confidence = 0.35  # Full disagreement

    # Build reasoning string
    mvrv_labels = ["<1.0 (undervalued)", "1.0-4.0 (fair)", "4.0-7.0 (overvalued)", ">7.0 (extreme)"]
    fng_labels = ["<25 (Extreme Fear)", "25-60 (Neutral)", "60-80 (Greed)", ">80 (Extreme Greed)"]
    fund_labels = ["negative (shorts pay)", "neutral", "positive (longs pay)", "extreme (overleveraged)"]

    reasoning = (
        f"MVRV={mvrv:.2f} {mvrv_labels[mvrv_score]}, "
        f"F&G={fng} {fng_labels[fng_score]}, "
        f"Funding={funding:.4%} {fund_labels[fund_score]} "
        f"-> weighted={weighted:.2f}"
    )

    return {
        "regime": regime,
        "confidence": round(confidence, 2),
        "risk_multiplier": RISK_MULTIPLIERS[regime],
        "action_bias": ACTION_BIAS[regime],
        "canonical_regime": SENTINEL_TO_CANONICAL[regime],
        "inputs": {
            "mvrv": round(mvrv, 3),
            "fng": fng,
            "funding_rate": round(funding, 6),
        },
        "scores": {
            "mvrv_score": mvrv_score,
            "fng_score": fng_score,
            "funding_score": fund_score,
            "weighted": round(weighted, 2),
        },
        "reasoning": reasoning,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# -- Public API (for scanner.py integration) -------------------------

def get_regime_sentinel(btc_prices: Optional[list[float]] = None) -> dict:
    """
    Top-level entry point. Fetches all data and classifies.
    Pass btc_prices if you already have them (avoids extra API call).
    """
    mvrv = fetch_mvrv_proxy(btc_prices)
    fng = fetch_fear_greed()
    funding = fetch_funding_rate()
    return classify_regime(mvrv, fng, funding)


# -- CLI --------------------------------------------------------------

if __name__ == "__main__":
    import sys
    result = get_regime_sentinel()
    print("=" * 60)
    print("  REGIME SENTINEL -- 4-State On-Chain Cycle Classifier")
    print("=" * 60)
    print(f"  Regime:          {result['regime']}")
    print(f"  Confidence:      {result['confidence']:.0%}")
    print(f"  Risk Multiplier: {result['risk_multiplier']}x")
    print(f"  Action Bias:     {result['action_bias']}")
    print(f"  Canonical:       {result['canonical_regime']}")
    print(f"  Reasoning:       {result['reasoning']}")
    inp = result["inputs"]
    print(f"\n  Inputs:")
    print(f"    MVRV proxy:    {inp['mvrv']:.3f}")
    print(f"    Fear & Greed:  {inp['fng']}")
    print(f"    Funding Rate:  {inp['funding_rate']:.4%}")
    print("=" * 60)
