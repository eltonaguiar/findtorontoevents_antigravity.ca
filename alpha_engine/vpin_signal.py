"""
ALPHA_ENGINE -- VPIN + OFI (Combined Microstructure Alpha)
==========================================================================
Detects informed trading activity in crypto markets using trade-level data
from Binance. Combines two complementary microstructure signals:

  VPIN (Volume-Synchronized Probability of Informed Trading):
    Measures the MAGNITUDE of informed flow -- how much toxic order flow exists.

  OFI (Order Flow Imbalance):
    Measures the DIRECTION of net buying/selling pressure.

Combined: VPIN tells us "smart money is moving", OFI tells us "which way".

Academic basis:
  - Easley, López de Prado & O'Hara (2012) "Flow Toxicity and Liquidity in a
    High-Frequency World" -- Review of Financial Studies 25(5).
  - Abad & Yague (2012) "From PIN to VPIN" -- Journal of Financial Markets.
  - Cont, Kukanov & Stoikov (2014) "The Price Impact of Order Book Events"
    -- Journal of Financial Econometrics 12(1). OFI predicts short-term returns.
  - 2026 journal: VPIN predicts BTC jumps with statistical significance.

Algorithm:
  1. Fetch 1000 recent aggTrades from Binance (free, no auth)
  2. Bucket trades into N volume bars (~50 trades per bucket)
  3. For each bucket, classify buy/sell volume using Binance's m flag
  4. VPIN = mean(|buy_vol - sell_vol|) / mean(total_vol) over last W buckets
  5. OFI = (total_buy - total_sell) / (total_buy + total_sell) over last W buckets
  6. Signal fires when VPIN > 0.55 (informed flow) AND |OFI| > 0.20 (directional)
  7. Direction from OFI sign: positive = LONG, negative = SHORT
  8. Confidence = VPIN * |OFI| (ranges 0-1, typically 0.11-0.70)

Data source (FREE, no auth):
  Binance aggTrades: GET /api/v3/aggTrades?symbol=X&limit=1000
  Each trade: {"p": price, "q": qty, "m": true/false}
    m=true  → buyer is maker (seller aggressed) → SELL volume
    m=false → seller is maker (buyer aggressed) → BUY volume
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np

try:
    from config import CRYPTO_SYMBOLS, fetch_binance_json
except ImportError:
    CRYPTO_SYMBOLS = {}
    fetch_binance_json = None  # type: ignore


# -- Configuration ----------------------------------------------------------

VPIN_BUCKET_SIZE = 50       # Trades per volume bucket
VPIN_WINDOW = 10            # Number of buckets to average over
VPIN_HIGH_THRESHOLD = 0.55  # VPIN > 0.55 = informed flow detected
VPIN_EXTREME_THRESHOLD = 0.70  # VPIN > 0.70 = very high informed flow

# OFI (Order Flow Imbalance) -- Cont, Kukanov & Stoikov (2014)
OFI_DIRECTIONAL_THRESHOLD = 0.20  # |OFI| > 0.20 = meaningful directional pressure
OFI_STRONG_THRESHOLD = 0.40       # |OFI| > 0.40 = strong directional conviction


# -- Symbol mapping ---------------------------------------------------------

_VPIN_SYMBOLS: dict[str, str] = {
    "BTC-USD":  "BTCUSDT",
    "ETH-USD":  "ETHUSDT",
    "SOL-USD":  "SOLUSDT",
    "BNB-USD":  "BNBUSDT",
    "XRP-USD":  "XRPUSDT",
    "ADA-USD":  "ADAUSDT",
    "AVAX-USD": "AVAXUSDT",
    "LINK-USD": "LINKUSDT",
    "DOGE-USD": "DOGEUSDT",
    "DOT-USD":  "DOTUSDT",
}


# -- Helpers -----------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_agg_trades(binance_symbol: str, limit: int = 1000) -> Optional[list]:
    """Fetch recent aggregate trades from Binance (with failover)."""
    if fetch_binance_json is not None:
        data = fetch_binance_json(f"/api/v3/aggTrades?symbol={binance_symbol}&limit={limit}")
        if data and isinstance(data, list) and len(data) > 0:
            return data
        return None
    # Fallback if config not available
    url = f"https://api.binance.com/api/v3/aggTrades?symbol={binance_symbol}&limit={limit}"
    data = _fetch_json(url, timeout=10)
    if data and isinstance(data, list) and len(data) > 0:
        return data
    return None


# -- VPIN Computation --------------------------------------------------------

def compute_vpin(trades: list,
                 bucket_size: int = VPIN_BUCKET_SIZE,
                 window: int = VPIN_WINDOW) -> Optional[dict]:
    """
    Compute VPIN and OFI from a list of Binance aggTrades.

    Returns a dict with:
      - vpin: float in [0, 1] -- probability of informed trading
      - ofi: float in [-1, +1] -- order flow imbalance (positive = net buying)
      - ofi_abs: float in [0, 1] -- absolute OFI strength
      - vpin_ofi_confidence: float in [0, 1] -- combined confidence (vpin * |ofi|)
      - signal: "HIGH" | "EXTREME" | "NORMAL"
      - buy_pct: percentage of buy volume (0-100)
      - n_buckets: number of volume buckets used
      - n_trades: total trades analyzed
    """
    if not trades or len(trades) < bucket_size * 3:
        return None

    # Classify each trade as buy or sell using Binance's maker flag
    # m=true  → buyer is maker → seller aggressed → SELL
    # m=false → seller is maker → buyer aggressed → BUY
    buy_volumes = []
    sell_volumes = []
    bucket_buy = 0.0
    bucket_sell = 0.0
    bucket_count = 0

    for trade in trades:
        qty = float(trade["q"])
        is_sell = trade["m"]  # True = buyer is maker → sell aggression

        if is_sell:
            bucket_sell += qty
        else:
            bucket_buy += qty

        bucket_count += 1
        if bucket_count >= bucket_size:
            buy_volumes.append(bucket_buy)
            sell_volumes.append(bucket_sell)
            bucket_buy = 0.0
            bucket_sell = 0.0
            bucket_count = 0

    if len(buy_volumes) < window:
        return None

    # Take the last `window` buckets
    buy_arr = np.array(buy_volumes[-window:])
    sell_arr = np.array(sell_volumes[-window:])
    total_arr = buy_arr + sell_arr

    # VPIN = mean(|buy_vol - sell_vol|) / mean(total_vol)
    imbalance = np.abs(buy_arr - sell_arr)
    vpin = float(np.mean(imbalance) / np.mean(total_arr)) if np.mean(total_arr) > 0 else 0.0

    # Clamp to [0, 1]
    vpin = max(0.0, min(1.0, vpin))

    # Total buy/sell over the window
    total_buy = float(np.sum(buy_arr))
    total_sell = float(np.sum(sell_arr))
    total_all = float(np.sum(total_arr))
    buy_pct = (total_buy / total_all * 100) if total_all > 0 else 50.0

    # OFI = (buy_vol - sell_vol) / (buy_vol + sell_vol) -- Cont et al. (2014)
    # Ranges from -1 (pure selling) to +1 (pure buying)
    ofi = float((total_buy - total_sell) / total_all) if total_all > 0 else 0.0
    ofi = max(-1.0, min(1.0, ofi))
    ofi_abs = abs(ofi)

    # Combined confidence: VPIN (magnitude of informed flow) * |OFI| (directional strength)
    # This is high only when BOTH informed flow AND directional pressure are present
    vpin_ofi_confidence = round(vpin * ofi_abs, 4)

    # Signal classification
    if vpin >= VPIN_EXTREME_THRESHOLD:
        signal = "EXTREME"
    elif vpin >= VPIN_HIGH_THRESHOLD:
        signal = "HIGH"
    else:
        signal = "NORMAL"

    return {
        "vpin": round(vpin, 4),
        "ofi": round(ofi, 4),
        "ofi_abs": round(ofi_abs, 4),
        "vpin_ofi_confidence": vpin_ofi_confidence,
        "signal": signal,
        "buy_pct": round(buy_pct, 1),
        "n_buckets": len(buy_volumes),
        "n_trades": len(trades),
    }


def get_vpin_score(symbol: str) -> Optional[dict]:
    """
    Compute VPIN for a single symbol.

    Args:
        symbol: yfinance symbol (e.g., "BTC-USD") or Binance symbol (e.g., "BTCUSDT")

    Returns:
        Dict with vpin, signal, buy_pct, etc. or None on failure.
    """
    # Normalize symbol to Binance format
    binance_sym = _VPIN_SYMBOLS.get(symbol, symbol)
    if "-USD" in binance_sym:
        binance_sym = binance_sym.replace("-USD", "USDT")

    trades = _fetch_agg_trades(binance_sym, limit=1000)
    if trades is None or len(trades) < VPIN_BUCKET_SIZE * 3:
        return None

    result = compute_vpin(trades)
    if result:
        result["symbol"] = symbol
        result["binance_symbol"] = binance_sym
        result["timestamp"] = datetime.now(timezone.utc).isoformat()

    return result


def get_vpin_scores_batch(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch VPIN scores for multiple symbols.
    Returns dict of {symbol: vpin_result_dict}. Missing symbols are omitted.
    """
    results = {}
    for sym in symbols:
        score = get_vpin_score(sym)
        if score is not None:
            results[sym] = score
    return results


# ---------------------------------------------------------------------------
# Strategy: VPIN + OFI Combined Microstructure Alpha
# ---------------------------------------------------------------------------
# Combined signal requires BOTH conditions:
#   1. VPIN > 0.55 -- informed traders are active (flow toxicity)
#   2. |OFI| > 0.20 -- clear directional pressure (not just noise)
#
# Direction comes from OFI sign:
#   OFI > +0.20 → net buying pressure → LONG
#   OFI < -0.20 → net selling pressure → SHORT
#
# Confidence = VPIN * |OFI|, capturing both toxicity magnitude and
# directional conviction. This eliminates the old buy_pct > 60% / < 40%
# heuristic with a proper normalized metric from Cont et al. (2014).
# ---------------------------------------------------------------------------

def vpin_informed_flow(data: dict, context: dict | None = None) -> list[dict]:
    """
    VPIN + OFI Combined Microstructure Alpha.
    Generates LONG/SHORT signals when informed trading is detected (VPIN)
    AND order flow has clear directional bias (OFI).
    """
    import pandas as pd
    signals = []

    for symbol, binance_sym in _VPIN_SYMBOLS.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 20:
                continue

            close = df["Close"]
            price = float(close.iloc[-1])

            vpin_data = get_vpin_score(symbol)
            if vpin_data is None:
                continue

            vpin_val = vpin_data["vpin"]
            ofi = vpin_data["ofi"]
            ofi_abs = vpin_data["ofi_abs"]
            buy_pct = vpin_data["buy_pct"]

            # Gate 1: VPIN must indicate informed flow
            if vpin_val < VPIN_HIGH_THRESHOLD:
                continue

            # Gate 2: OFI must show meaningful directional pressure
            if ofi_abs < OFI_DIRECTIONAL_THRESHOLD:
                continue

            # Direction from OFI sign (replaces old buy_pct heuristic)
            if ofi > 0:
                # Net buying pressure → LONG
                direction = "BUY"
                dir_label = "LONG"
                tp_mult = 1.02
                sl_mult = 0.985
            else:
                # Net selling pressure → SHORT
                direction = "SELL"
                dir_label = "SHORT"
                tp_mult = 0.98
                sl_mult = 1.015

            # Confidence = VPIN * |OFI| (both must be high for strong signal)
            # Scale to usable range: raw product is 0.11-0.70, map to 0.50-0.88
            raw_conf = vpin_val * ofi_abs
            conf = min(0.88, 0.50 + raw_conf * 0.55)

            # Boost for strong OFI (>0.40) or extreme VPIN (>0.70)
            if ofi_abs >= OFI_STRONG_THRESHOLD:
                conf = min(0.90, conf + 0.04)
            if vpin_val >= VPIN_EXTREME_THRESHOLD:
                conf = min(0.90, conf + 0.04)

            entry = round(price, 2) if price > 1 else round(price, 6)
            tp = round(price * tp_mult, 2) if price > 1 else round(price * tp_mult, 6)
            sl = round(price * sl_mult, 2) if price > 1 else round(price * sl_mult, 6)
            rr = abs(tp - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 1.5

            cat_info = CRYPTO_SYMBOLS.get(symbol, {})
            cat = cat_info.get("cat", "crypto")

            signals.append({
                "strategy": "vpin_informed_flow",
                "symbol": symbol,
                "category": cat,
                "signal_type": direction,
                "direction": dir_label,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"VPIN {vpin_val:.3f} ({vpin_data['signal']}) + "
                    f"OFI {ofi:+.3f} → informed {dir_label}. "
                    f"Combined confidence {raw_conf:.3f}. "
                    f"Analyzed {vpin_data['n_trades']} trades in "
                    f"{vpin_data['n_buckets']} volume buckets"
                ),
                "timeframe": "5m-4h",  # Microstructure: scalp to intraday
                "rsi_at_entry": 50,  # Placeholder -- microstructure signal, not momentum
                "volume_ratio": 1.0,
                "extra": {
                    "vpin": vpin_val,
                    "ofi": ofi,
                    "ofi_abs": ofi_abs,
                    "vpin_ofi_confidence": vpin_data["vpin_ofi_confidence"],
                    "vpin_signal": vpin_data["signal"],
                    "buy_pct": buy_pct,
                    "n_trades": vpin_data["n_trades"],
                    "n_buckets": vpin_data["n_buckets"],
                    "source": "Binance aggTrades (free API, 1000 trades)",
                    "reference": (
                        "Easley, López de Prado & O'Hara (2012), RFS 25(5) [VPIN]; "
                        "Cont, Kukanov & Stoikov (2014), JFEC 12(1) [OFI]"
                    ),
                },
                "research_basis": (
                    "VPIN: Easley et al. (2012); "
                    "OFI: Cont, Kukanov & Stoikov (2014)"
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vpin": vpin_val,       # For ML ranker feature injection
                "ofi": ofi,             # For ML ranker feature injection
                "ofi_abs": ofi_abs,     # For ML ranker feature injection
            })

        except Exception:
            continue

    return signals


# -- Strategy registry -------------------------------------------------------

VPIN_STRATEGIES: dict[str, callable] = {
    "vpin_informed_flow": vpin_informed_flow,
}


# -- Self-test ---------------------------------------------------------------
if __name__ == "__main__":
    print("VPIN + OFI Microstructure Module -- Self-Test")
    print("=" * 60)
    for sym in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        result = get_vpin_score(sym)
        if result:
            ofi_dir = "BUY" if result["ofi"] > 0 else "SELL"
            fires = (result["vpin"] >= VPIN_HIGH_THRESHOLD
                     and result["ofi_abs"] >= OFI_DIRECTIONAL_THRESHOLD)
            print(f"  {sym}: VPIN={result['vpin']:.4f} ({result['signal']}) "
                  f"OFI={result['ofi']:+.4f} ({ofi_dir}) "
                  f"conf={result['vpin_ofi_confidence']:.4f} "
                  f"{'** SIGNAL **' if fires else '(no signal)'} "
                  f"trades={result['n_trades']} buckets={result['n_buckets']}")
        else:
            print(f"  {sym}: [UNAVAILABLE]")
