#!/usr/bin/env python3
"""
ALPHA ENGINE -- Prediction Verification
========================================
Reads prediction_verification_log.json, checks current prices for unverified
predictions past their verify_after window, and updates outcomes.

For each unverified candidate:
  - Fetches current price from Binance (with multi-mirror failover + CoinGecko)
  - Computes current_gain_pct = (current_price - entry_price) / entry_price * 100
  - Tags current_status: PUMPING (>3%), FLAT (-2% to +3%), DUMPING (<-2%)

Designed to run every 2 hours via GitHub Actions.

Usage:
  python verify_predictions.py
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
PREDICTIONS_FILE = DATA_DIR / "prediction_verification_log.json"

# ---------------------------------------------------------------------------
# Binance API failover chain (3+ mirrors as per project policy)
# ---------------------------------------------------------------------------
BINANCE_PRICE_URLS = [
    "https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}",
    "https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api2.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api3.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api.binance.us/api/v3/ticker/price?symbol={symbol}",
]

# Non-Binance fallbacks
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
KUCOIN_PRICE_URL = "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"
CRYPTOCOMPARE_PRICE_URL = "https://min-api.cryptocompare.com/data/price?fsym={base}&tsyms=USD"

HTTP_TIMEOUT = 10


def _ssl_ctx():
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


def _fetch_json(url: str, timeout: int = HTTP_TIMEOUT) -> dict | list | None:
    """Fetch JSON from URL using stdlib. Returns None on failure."""
    try:
        ctx = _ssl_ctx()
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaVerify/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# Symbol -> CoinGecko ID mapping for common symbols
_CG_ID_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "DOTUSDT": "polkadot", "AVAXUSDT": "avalanche-2",
    "LINKUSDT": "chainlink", "MATICUSDT": "matic-network", "SHIBUSDT": "shiba-inu",
    "LTCUSDT": "litecoin", "UNIUSDT": "uniswap", "ATOMUSDT": "cosmos",
    "NEARUSDT": "near", "APTUSDT": "aptos", "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism", "FILUSDT": "filecoin", "CHZUSDT": "chiliz",
}


def fetch_current_price(symbol: str) -> float | None:
    """Fetch current price using Binance mirror failover + CoinGecko + KuCoin + CryptoCompare.

    Returns price as float or None if all sources fail.
    """
    # 1. Try Binance mirrors
    for url_template in BINANCE_PRICE_URLS:
        url = url_template.format(symbol=symbol)
        data = _fetch_json(url)
        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                continue

    # 2. Try CoinGecko
    cg_id = _CG_ID_MAP.get(symbol)
    if cg_id:
        url = COINGECKO_PRICE_URL.format(cg_id=cg_id)
        data = _fetch_json(url)
        if data and cg_id in data and "usd" in data[cg_id]:
            try:
                return float(data[cg_id]["usd"])
            except (ValueError, TypeError):
                pass

    # 3. Try KuCoin (symbol format: BTC-USDT)
    base = symbol.replace("USDT", "")
    kucoin_sym = f"{base}-USDT"
    url = KUCOIN_PRICE_URL.format(kucoin_symbol=kucoin_sym)
    data = _fetch_json(url)
    if data and data.get("data") and data["data"].get("price"):
        try:
            return float(data["data"]["price"])
        except (ValueError, TypeError):
            pass

    # 4. Try CryptoCompare
    url = CRYPTOCOMPARE_PRICE_URL.format(base=base)
    data = _fetch_json(url)
    if data and "USD" in data:
        try:
            return float(data["USD"])
        except (ValueError, TypeError):
            pass

    return None


def classify_status(gain_pct: float) -> str:
    """Classify current status based on gain percentage."""
    if gain_pct > 3.0:
        return "PUMPING"
    elif gain_pct < -2.0:
        return "DUMPING"
    else:
        return "FLAT"


def classify_outcome(gain_pct: float) -> str | None:
    """Classify final outcome if clear signal exists.

    Returns:
      'CORRECT' if gain > 5% (pump prediction was right)
      'WRONG' if loss > 5% (price dumped instead)
      None if still inconclusive
    """
    if gain_pct >= 5.0:
        return "CORRECT"
    elif gain_pct <= -5.0:
        return "WRONG"
    return None


def parse_verify_after(verify_str: str) -> datetime | None:
    """Parse the verify_after_est string into a timezone-aware datetime."""
    # Format: "2026-03-26 06:55:44 AM EST"
    for fmt in (
        "%Y-%m-%d %I:%M:%S %p EST",
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            dt = datetime.strptime(verify_str.strip(), fmt)
            # Treat as UTC for simplicity (EST is UTC-5, but we want to check
            # after the window, so being slightly early is fine)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def verify_predictions() -> dict:
    """Main verification logic. Returns updated predictions dict."""
    if not PREDICTIONS_FILE.exists():
        print("[VERIFY] No prediction_verification_log.json found")
        return {"predictions": []}

    with open(PREDICTIONS_FILE, "r") as f:
        data = json.load(f)

    predictions = data.get("predictions", [])
    now = datetime.now(timezone.utc)
    total_checked = 0
    total_updated = 0
    total_skipped = 0

    for prediction_batch in predictions:
        candidates = prediction_batch.get("candidates", [])
        verify_after_str = prediction_batch.get("verify_after_est", "")
        verify_dt = parse_verify_after(verify_after_str)

        for candidate in candidates:
            # Skip already-verified candidates with a final outcome
            if candidate.get("outcome") in ("CORRECT", "WRONG"):
                continue

            symbol = candidate.get("symbol", "")
            entry_price = candidate.get("entry_price_at_prediction")

            if not symbol or not entry_price or entry_price <= 0:
                print(f"  [SKIP] {symbol}: missing entry_price")
                total_skipped += 1
                continue

            # Fetch current price
            current_price = fetch_current_price(symbol)
            if current_price is None:
                print(f"  [SKIP] {symbol}: could not fetch current price from any source")
                total_skipped += 1
                continue

            total_checked += 1

            # Compute gain
            gain_pct = (current_price - entry_price) / entry_price * 100.0
            status = classify_status(gain_pct)

            # Update candidate fields
            candidate["current_price"] = round(current_price, 6)
            candidate["current_gain_pct"] = round(gain_pct, 2)
            candidate["current_status"] = status
            candidate["outcome_checked_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            # If verification window has passed, try to set final outcome
            window_passed = verify_dt is not None and now >= verify_dt
            if window_passed:
                outcome = classify_outcome(gain_pct)
                if outcome:
                    candidate["outcome"] = outcome
                    total_updated += 1
                    print(f"  [{outcome}] {symbol}: {gain_pct:+.2f}% (entry={entry_price}, now={current_price})")
                else:
                    # Window passed but still inconclusive -> mark NEUTRAL
                    candidate["outcome"] = "NEUTRAL"
                    total_updated += 1
                    print(f"  [NEUTRAL] {symbol}: {gain_pct:+.2f}% (entry={entry_price}, now={current_price})")
            else:
                print(f"  [{status}] {symbol}: {gain_pct:+.2f}% (entry={entry_price}, now={current_price}) -- window not yet passed")

    # Compute summary stats
    all_candidates = []
    for p in predictions:
        all_candidates.extend(p.get("candidates", []))

    outcomes = [c.get("outcome") for c in all_candidates if c.get("outcome")]
    correct = sum(1 for o in outcomes if o == "CORRECT")
    wrong = sum(1 for o in outcomes if o == "WRONG")
    neutral = sum(1 for o in outcomes if o == "NEUTRAL")

    data["verification_summary"] = {
        "last_run_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_predictions": len(all_candidates),
        "verified": correct + wrong + neutral,
        "correct": correct,
        "wrong": wrong,
        "neutral": neutral,
        "pending": len(all_candidates) - (correct + wrong + neutral),
        "accuracy_pct": round(correct / max(correct + wrong, 1) * 100, 1),
    }

    print(f"\n[VERIFY] Checked {total_checked}, updated {total_updated}, skipped {total_skipped}")
    print(f"[VERIFY] Summary: {correct} correct, {wrong} wrong, {neutral} neutral, "
          f"{data['verification_summary']['pending']} pending")
    if correct + wrong > 0:
        print(f"[VERIFY] Accuracy: {data['verification_summary']['accuracy_pct']}%")

    return data


def main():
    data = verify_predictions()

    # Write updated predictions back
    PREDICTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PREDICTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n[VERIFY] Written to {PREDICTIONS_FILE}")


if __name__ == "__main__":
    main()
