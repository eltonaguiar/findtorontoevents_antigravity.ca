"""
ALPHA_ENGINE -- Beta-Adjusted Residual Momentum
=================================================
Academic: Liu & Tsyvinski (2021), "Risks and Returns of Cryptocurrency",
Review of Financial Studies.

Strategy: beta_adjusted_residual_momentum
  - For each altcoin, compute rolling 30-day beta vs BTC (OLS regression)
  - Residual return (alpha) = altcoin_30d_return - beta * btc_30d_return
  - Rank all coins by residual alpha
  - LONG top 3 coins with highest positive residual alpha
  - Optionally SHORT bottom 3 (worst underperformers)
  - TP: +8%, SL: -4% (2:1 R:R)
  - Confidence: 0.60-0.85 based on magnitude of residual alpha

Data: Binance spot API with 3+ mirror failover chain.
Rebalance: weekly (7d timeframe).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Binance API mirrors (3+ failover per project rules)
# ---------------------------------------------------------------------------
BINANCE_SPOT_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# In GitHub Actions, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_SPOT_MIRRORS = _preferred + [
        u for u in BINANCE_SPOT_MIRRORS if u not in _preferred
    ]

# Non-Binance fallbacks
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# CoinGecko ID map for fallback pricing
_CG_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink", "DOTUSDT": "polkadot",
    "ATOMUSDT": "cosmos", "NEARUSDT": "near", "MATICUSDT": "matic-network",
    "DOGEUSDT": "dogecoin", "SHIBUSDT": "shiba-inu", "LTCUSDT": "litecoin",
    "UNIUSDT": "uniswap", "AAVEUSDT": "aave", "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism", "SUIUSDT": "sui",
}

# ---------------------------------------------------------------------------
# Top-20 altcoin universe (by typical volume, excluding BTC itself)
# ---------------------------------------------------------------------------
ALT_UNIVERSE = [
    "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "LINKUSDT", "DOTUSDT", "ATOMUSDT", "NEARUSDT",
    "MATICUSDT", "DOGEUSDT", "SHIBUSDT", "LTCUSDT", "UNIUSDT",
    "AAVEUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "FILUSDT",
]

# Strategy parameters
LOOKBACK_DAYS = 30
TP_PCT = 0.08       # +8%
SL_PCT = 0.04       # -4%
TOP_N = 3            # Long top 3
BOTTOM_N = 3         # Short bottom 3
RATE_LIMIT_SEC = 0.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from a single URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_binance_klines(symbol: str, interval: str = "1d",
                          limit: int = 35) -> Optional[list]:
    """Fetch klines from Binance with mirror failover, then CoinGecko/CryptoCompare."""
    # Try all Binance mirrors
    for base in BINANCE_SPOT_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            return data

    # Fallback: CoinGecko (daily OHLC)
    cg_id = _CG_IDS.get(symbol)
    if cg_id:
        url = f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            # CoinGecko OHLC format: [timestamp, open, high, low, close]
            # Convert to Binance-like: [ts, o, h, l, c, vol, ...]
            return [[d[0], d[1], d[2], d[3], d[4], 0] for d in data]

    # Fallback: CryptoCompare
    fsym = symbol.replace("USDT", "")
    url = f"{CRYPTOCOMPARE_BASE}/v2/histoday?fsym={fsym}&tsym=USD&limit={limit}"
    data = _fetch_json(url)
    if data and isinstance(data, dict):
        hist = data.get("Data", {}).get("Data", [])
        if hist:
            return [
                [d["time"] * 1000, d["open"], d["high"], d["low"], d["close"], d["volumeto"]]
                for d in hist
            ]

    return None


def _extract_close_series(klines: list) -> np.ndarray:
    """Extract closing prices from klines data."""
    closes = []
    for k in klines:
        try:
            closes.append(float(k[4]))
        except (IndexError, ValueError, TypeError):
            continue
    return np.array(closes)


def _compute_returns(prices: np.ndarray) -> np.ndarray:
    """Compute daily log returns from price series."""
    if len(prices) < 2:
        return np.array([])
    return np.diff(np.log(prices))


def _compute_beta(alt_returns: np.ndarray, btc_returns: np.ndarray) -> float:
    """
    OLS beta = cov(alt, btc) / var(btc).
    Simple, no scipy needed.
    """
    if len(alt_returns) < 10 or len(btc_returns) < 10:
        return 1.0  # default beta
    # Align lengths
    n = min(len(alt_returns), len(btc_returns))
    alt_r = alt_returns[-n:]
    btc_r = btc_returns[-n:]

    cov_matrix = np.cov(alt_r, btc_r)
    var_btc = cov_matrix[1, 1]
    if var_btc < 1e-15:
        return 1.0
    beta = cov_matrix[0, 1] / var_btc
    return float(beta)


def _compute_residual_alpha(alt_returns: np.ndarray, btc_returns: np.ndarray,
                            beta: float) -> float:
    """
    Residual alpha = cumulative(alt_return) - beta * cumulative(btc_return)
    over the lookback window.
    """
    n = min(len(alt_returns), len(btc_returns))
    alt_cum = float(np.sum(alt_returns[-n:]))
    btc_cum = float(np.sum(btc_returns[-n:]))
    return alt_cum - beta * btc_cum


# ---------------------------------------------------------------------------
# Main strategy function
# ---------------------------------------------------------------------------
def beta_adjusted_residual_momentum(data: dict = None) -> list[dict]:
    """
    Beta-Adjusted Residual Momentum strategy.

    Fetches its own data from Binance (with failover).
    Optionally accepts pre-loaded `data` dict but fetches fresh daily klines
    regardless since we need exactly 30d daily candles for beta calculation.

    Returns list of pick dicts matching Alpha Engine format.
    """
    signals: list[dict] = []

    # --- Step 1: Fetch BTC daily klines ---
    btc_klines = _fetch_binance_klines("BTCUSDT", "1d", LOOKBACK_DAYS + 5)
    if not btc_klines or len(btc_klines) < LOOKBACK_DAYS:
        print("  [residual_momentum] Could not fetch BTC klines, skipping")
        return signals

    btc_prices = _extract_close_series(btc_klines)
    btc_returns = _compute_returns(btc_prices)
    if len(btc_returns) < LOOKBACK_DAYS - 1:
        print("  [residual_momentum] Insufficient BTC return data, skipping")
        return signals

    btc_30d_return = float(np.sum(btc_returns[-LOOKBACK_DAYS:]))

    # --- Step 2: Fetch altcoin data and compute residuals ---
    residuals: dict[str, dict] = {}  # symbol -> {beta, residual_alpha, price, ...}

    for symbol in ALT_UNIVERSE:
        time.sleep(RATE_LIMIT_SEC)

        klines = _fetch_binance_klines(symbol, "1d", LOOKBACK_DAYS + 5)
        if not klines or len(klines) < LOOKBACK_DAYS:
            continue

        alt_prices = _extract_close_series(klines)
        alt_returns = _compute_returns(alt_prices)
        if len(alt_returns) < LOOKBACK_DAYS - 1:
            continue

        # Compute beta and residual
        beta = _compute_beta(alt_returns[-LOOKBACK_DAYS:], btc_returns[-LOOKBACK_DAYS:])
        residual_alpha = _compute_residual_alpha(
            alt_returns[-LOOKBACK_DAYS:], btc_returns[-LOOKBACK_DAYS:], beta
        )

        current_price = float(alt_prices[-1])
        alt_30d_return = float(np.sum(alt_returns[-LOOKBACK_DAYS:]))

        residuals[symbol] = {
            "beta": beta,
            "residual_alpha": residual_alpha,
            "price": current_price,
            "alt_30d_return": alt_30d_return,
            "btc_30d_return": btc_30d_return,
        }

    if len(residuals) < 6:
        print(f"  [residual_momentum] Only {len(residuals)} alts fetched, need >= 6")
        return signals

    # --- Step 3: Rank by residual alpha ---
    sorted_by_alpha = sorted(
        residuals.items(), key=lambda x: x[1]["residual_alpha"], reverse=True
    )

    # Compute alpha stats for confidence scaling
    all_alphas = [v["residual_alpha"] for v in residuals.values()]
    alpha_std = float(np.std(all_alphas)) if len(all_alphas) > 1 else 0.01
    alpha_mean = float(np.mean(all_alphas))

    # --- Step 4: LONG top N with positive residual alpha ---
    long_candidates = [(s, d) for s, d in sorted_by_alpha[:TOP_N]
                       if d["residual_alpha"] > 0]

    for symbol, info in long_candidates:
        price = info["price"]
        tp = _smart_round(price * (1 + TP_PCT))
        sl = _smart_round(price * (1 - SL_PCT))
        entry = _smart_round(price)

        # Confidence: scale 0.60-0.85 by z-score of residual alpha
        z_score = (info["residual_alpha"] - alpha_mean) / max(alpha_std, 0.001)
        conf = min(0.85, max(0.60, 0.60 + z_score * 0.05))

        rank = [s for s, _ in sorted_by_alpha].index(symbol)

        signals.append({
            "strategy": "beta_adjusted_residual_momentum",
            "symbol": symbol,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "tp": tp,
            "sl": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(TP_PCT / SL_PCT, 2),
            "reason": (
                f"Residual Momentum: alpha={info['residual_alpha']*100:.2f}% "
                f"(rank {rank+1}/{len(sorted_by_alpha)}), "
                f"beta={info['beta']:.2f}, "
                f"30d raw={info['alt_30d_return']*100:.1f}%, "
                f"BTC 30d={info['btc_30d_return']*100:.1f}%"
            ),
            "timeframe": "7d",
            "extra": {
                "residual_alpha_pct": round(info["residual_alpha"] * 100, 3),
                "beta_vs_btc": round(info["beta"], 4),
                "alt_30d_return_pct": round(info["alt_30d_return"] * 100, 2),
                "btc_30d_return_pct": round(info["btc_30d_return"] * 100, 2),
                "z_score": round(z_score, 3),
                "rank": rank + 1,
                "universe_size": len(sorted_by_alpha),
                "lookback_days": LOOKBACK_DAYS,
                "rebalance": "weekly",
                "source": "Liu & Tsyvinski (2021) Review of Financial Studies",
            },
            "timestamp": _now_iso(),
        })

    # --- Step 5: SHORT bottom N with negative residual alpha ---
    short_candidates = [(s, d) for s, d in sorted_by_alpha[-BOTTOM_N:]
                        if d["residual_alpha"] < 0]

    for symbol, info in short_candidates:
        price = info["price"]
        # For shorts: TP is below entry, SL is above entry
        tp = _smart_round(price * (1 - TP_PCT))
        sl = _smart_round(price * (1 + SL_PCT))
        entry = _smart_round(price)

        z_score = (info["residual_alpha"] - alpha_mean) / max(alpha_std, 0.001)
        conf = min(0.85, max(0.60, 0.60 + abs(z_score) * 0.05))

        rank = [s for s, _ in sorted_by_alpha].index(symbol)

        signals.append({
            "strategy": "beta_adjusted_residual_momentum",
            "symbol": symbol,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "tp": tp,
            "sl": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(TP_PCT / SL_PCT, 2),
            "reason": (
                f"Residual Momentum SHORT: alpha={info['residual_alpha']*100:.2f}% "
                f"(rank {rank+1}/{len(sorted_by_alpha)}), "
                f"beta={info['beta']:.2f}, "
                f"30d raw={info['alt_30d_return']*100:.1f}%, "
                f"BTC 30d={info['btc_30d_return']*100:.1f}%"
            ),
            "timeframe": "7d",
            "extra": {
                "residual_alpha_pct": round(info["residual_alpha"] * 100, 3),
                "beta_vs_btc": round(info["beta"], 4),
                "alt_30d_return_pct": round(info["alt_30d_return"] * 100, 2),
                "btc_30d_return_pct": round(info["btc_30d_return"] * 100, 2),
                "z_score": round(z_score, 3),
                "rank": rank + 1,
                "universe_size": len(sorted_by_alpha),
                "lookback_days": LOOKBACK_DAYS,
                "rebalance": "weekly",
                "source": "Liu & Tsyvinski (2021) Review of Financial Studies",
            },
            "timestamp": _now_iso(),
        })

    return signals


# Allow standalone execution for testing
if __name__ == "__main__":
    print("Beta-Adjusted Residual Momentum Scanner")
    print("=" * 50)
    picks = beta_adjusted_residual_momentum()
    print(f"\nTotal signals: {len(picks)}")
    for p in picks:
        print(f"  {p['direction']:5s} {p['symbol']:12s} "
              f"alpha={p['extra']['residual_alpha_pct']:+.2f}% "
              f"beta={p['extra']['beta_vs_btc']:.2f} "
              f"conf={p['confidence']:.2f}")
