"""CoinGecko ADV (24h USD volume) snapshot fetcher.

Fetches 24h trading volume for top-N CRYPTO coins via the free CoinGecko
/coins/markets endpoint and writes to alpha_engine/data/coingecko_adv_cache.json.

Used by alpha_engine.asset_class.is_liquid_crypto() for the CRYPTO ADV gate.

Usage:
    python tools/coingecko_adv_fetcher.py            # fetch top 500 coins
    python tools/coingecko_adv_fetcher.py --top 250  # fetch top 250 coins
    python tools/coingecko_adv_fetcher.py --dry-run  # print counts, no write

Schedule: wired into the hourly crypto scan (or run standalone).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CACHE_PATH = _ROOT / "alpha_engine" / "data" / "coingecko_adv_cache.json"
_COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

# Map CoinGecko coin IDs → USDT symbols (supplement for common coins missing
# direct symbol→USDT mapping)
_COINGECKO_ID_TO_SYMBOL: dict[str, str] = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "binancecoin": "BNBUSDT",
    "solana": "SOLUSDT",
    "ripple": "XRPUSDT",
    "cardano": "ADAUSDT",
    "dogecoin": "DOGEUSDT",
    "tron": "TRXUSDT",
    "avalanche-2": "AVAXUSDT",
    "chainlink": "LINKUSDT",
    "polkadot": "DOTUSDT",
    "matic-network": "MATICUSDT",
    "uniswap": "UNIUSDT",
    "shiba-inu": "SHIBUSDT",
    "litecoin": "LTCUSDT",
    "cosmos": "ATOMUSDT",
    "stellar": "XLMUSDT",
    "monero": "XMRUSDT",
    "ethereum-classic": "ETCUSDT",
    "aave": "AAVEUSDT",
    "the-sandbox": "SANDUSDT",
    "decentraland": "MANA" + "USDT",
    "axie-infinity": "AXSUSDT",
    "the-graph": "GRTUSDT",
    "filecoin": "FILUSDT",
    "sui": "SUIUSDT",
    "aptos": "APTUSDT",
    "arbitrum": "ARBUSDT",
    "optimism": "OPUSDT",
    "fetch-ai": "FETUSDT",
    "render-token": "RENDERUSDT",
    "injective-protocol": "INJUSDT",
    "near": "NEARUSDT",
    "internet-computer": "ICPUSDT",
    "hedera-hashgraph": "HBARUSDT",
    "pepe": "PEPEUSDT",
    "bonk": "BONKUSDT",
}


def fetch_adv_snapshot(top_n: int = 500) -> dict[str, float]:
    """Fetch top_n coins by market cap from CoinGecko and return symbol→24h_volume map."""
    try:
        import requests
    except ImportError:
        print("[coingecko_adv_fetcher] requests not installed — skip")
        return {}

    adv_map: dict[str, float] = {}
    per_page = min(250, top_n)
    pages = (top_n + per_page - 1) // per_page

    for page in range(1, pages + 1):
        try:
            resp = requests.get(
                _COINGECKO_URL,
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": per_page,
                    "page": page,
                    "sparkline": "false",
                },
                timeout=20,
                headers={"User-Agent": "findtorontoevents-adv-gate/1.0"},
            )
            resp.raise_for_status()
            coins = resp.json()
            for coin in coins:
                coin_id = str(coin.get("id", "")).lower()
                raw_sym = str(coin.get("symbol", "")).upper().strip()
                vol_usd = float(coin.get("total_volume") or 0)

                # Prefer explicit ID mapping, fall back to raw_symbol + USDT
                sym = _COINGECKO_ID_TO_SYMBOL.get(coin_id, raw_sym + "USDT")
                adv_map[sym] = vol_usd

                # Also store raw symbol without USDT suffix (for fallback lookups)
                if raw_sym and raw_sym not in adv_map:
                    adv_map[raw_sym] = vol_usd

            if len(coins) < per_page:
                break  # fewer results than requested — last page
            time.sleep(1.0)  # CoinGecko free-tier rate limit: ~30 req/min
        except Exception as e:
            print(f"[coingecko_adv_fetcher] Page {page} error: {e}")
            break

    return adv_map


def write_cache(adv_map: dict[str, float]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_fetched_at": time.time(),
        "_fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "_symbol_count": len(adv_map),
        "adv_by_symbol": adv_map,
    }
    _CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[coingecko_adv_fetcher] Wrote {len(adv_map)} symbols to {_CACHE_PATH}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--top", type=int, default=500, help="Top N coins by market cap (default 500)")
    p.add_argument("--dry-run", action="store_true", help="Print counts, do not write cache")
    args = p.parse_args()

    print(f"[coingecko_adv_fetcher] Fetching top {args.top} coins...")
    adv_map = fetch_adv_snapshot(top_n=args.top)
    print(f"[coingecko_adv_fetcher] Got {len(adv_map)} symbols")

    if args.dry_run:
        top5 = sorted(adv_map.items(), key=lambda x: x[1], reverse=True)[:5]
        print("Top 5 by volume:")
        for sym, vol in top5:
            print(f"  {sym}: ${vol:,.0f}")
        return

    write_cache(adv_map)


if __name__ == "__main__":
    main()
