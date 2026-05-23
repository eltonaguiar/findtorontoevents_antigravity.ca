"""Export enhanced ML predictions in cross-aggregator format.

Reads live_picks_1h.json (raw model probabilities) and converts to
the standard active_picks.json format with direction, entry, TP/SL.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results"
OUTPUT_DIR = SCRIPT_DIR / "live_picks"
INPUT_FILE = RESULTS_DIR / "live_picks_1h.json"
OUTPUT_FILE = OUTPUT_DIR / "active_picks.json"

# Confidence thresholds: only emit picks with strong conviction
MIN_LONG_CONFIDENCE = 0.65   # 65%+ probability of increase → LONG
MAX_SHORT_CONFIDENCE = 0.35  # 35%- probability of increase → SHORT
# Only use the best variant per pair (highest confidence)
BEST_VARIANT_ONLY = True


def fetch_binance_prices() -> dict[str, float]:
    """Fetch current prices for all crypto pairs from Binance, with OKX fallback."""
    # Try Binance first
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=10)
        resp.raise_for_status()
        return {t["symbol"]: float(t["price"]) for t in resp.json()}
    except Exception as e:
        print(f"  Binance price fetch failed ({e}), trying OKX...")

    # OKX fallback
    try:
        resp = requests.get(
            "https://www.okx.com/api/v5/market/tickers",
            params={"instType": "SPOT"},
            timeout=15,
        )
        if resp.ok:
            tickers = resp.json().get("data", [])
            prices = {}
            for t in tickers:
                inst = t.get("instId", "")
                last = t.get("last", "")
                if inst.endswith("-USDT") and last:
                    # Convert OKX format (BTC-USDT) to Binance format (BTCUSDT)
                    symbol = inst.replace("-", "")
                    prices[symbol] = float(last)
            print(f"  OKX fallback: {len(prices)} prices fetched")
            return prices
    except Exception as e2:
        print(f"  OKX price fetch also failed: {e2}")

    # CoinGecko last resort - fetch top 250 coins
    try:
        all_prices = {}
        for page in range(1, 3):
            resp = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={"vs_currency": "usd", "order": "market_cap_desc",
                        "per_page": 250, "page": page},
                timeout=15,
            )
            if resp.ok:
                for coin in resp.json():
                    sym = coin.get("symbol", "").upper()
                    price = coin.get("current_price")
                    if sym and price:
                        all_prices[f"{sym}USDT"] = float(price)
        if all_prices:
            print(f"  CoinGecko fallback: {len(all_prices)} prices fetched")
            return all_prices
    except Exception as e3:
        print(f"  CoinGecko price fetch also failed: {e3}")

    return {}


def export_picks() -> int:
    """Convert enhanced ML predictions to aggregator format."""
    if not INPUT_FILE.exists():
        print("No live_picks_1h.json found")
        return 0

    with open(INPUT_FILE) as f:
        data = json.load(f)

    raw_picks = data.get("picks", [])
    if not raw_picks:
        print("No picks in live_picks_1h.json")
        return 0

    # Fetch current prices for entry/TP/SL calculation
    prices = fetch_binance_prices()

    # Group by pair, keep best variant per pair
    best_by_pair: dict[str, dict] = {}
    for pick in raw_picks:
        pair = pick.get("pair", "")
        conf = pick.get("confidence", 0.5)

        # Determine direction from probability
        if conf >= MIN_LONG_CONFIDENCE:
            direction = "LONG"
            strength = conf
        elif conf <= MAX_SHORT_CONFIDENCE:
            direction = "SHORT"
            strength = 1.0 - conf
        else:
            continue  # Skip neutral zone

        key = f"{pair}_{direction}"
        if BEST_VARIANT_ONLY:
            existing = best_by_pair.get(key)
            if existing and existing["_strength"] >= strength:
                continue

        best_by_pair[key] = {
            "pair": pair,
            "direction": direction,
            "confidence": round(strength, 4),
            "variant": pick.get("variant", "unknown"),
            "timeframe": pick.get("timeframe", "1h"),
            "_strength": strength,
            "timestamp": pick.get("timestamp", ""),
        }

    # Convert to aggregator format with entry/TP/SL
    active_picks = []
    for pick in best_by_pair.values():
        pair = pick["pair"]
        current_price = prices.get(pair)
        if not current_price:
            continue

        direction = pick["direction"]
        confidence = pick["confidence"]

        # ATR-approximate TP/SL: 3% TP, 2% SL for crypto
        if direction == "LONG":
            tp = round(current_price * 1.03, 8)
            sl = round(current_price * 0.98, 8)
        else:
            tp = round(current_price * 0.97, 8)
            sl = round(current_price * 1.02, 8)

        active_picks.append({
            "symbol": pair,
            "direction": direction,
            "confidence": confidence,
            "entry_price": current_price,
            "take_profit": tp,
            "stop_loss": sl,
            "strategy": f"enhanced_ml_{pick['variant']}",
            "timeframe": pick["timeframe"],
            "signal_type": direction,
            "timestamp": pick["timestamp"],
            "source": "enhanced_ml_crypto",
        })

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "enhanced_ml_crypto",
        "picks": active_picks,
        "total": len(active_picks),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(active_picks, f, indent=2, default=str)

    print(f"Enhanced ML: {len(active_picks)} picks exported to {OUTPUT_FILE}")
    for p in active_picks:
        print(f"  {p['symbol']:12s} {p['direction']:5s} conf={p['confidence']:.2f} "
              f"entry={p['entry_price']:.4f} tp={p['take_profit']:.4f} sl={p['stop_loss']:.4f}")

    return len(active_picks)


if __name__ == "__main__":
    count = export_picks()
    sys.exit(0 if count >= 0 else 1)
