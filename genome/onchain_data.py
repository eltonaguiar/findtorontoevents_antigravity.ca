"""
Real On-Chain Data Fetcher for DNA Mutation Engine
===================================================

Replaces proxy features (e.g. close.pct_change(7) pretending to be hash rate)
with real API data from Binance, Alternative.me, and CoinGecko.

Provides mutation bias signals based on on-chain conditions:
- Fear & Greed extremes → directional bias
- Funding rate extremes → crowding signal
- Stablecoin Supply Ratio → buying power
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Safe defaults when APIs fail — never crash
DEFAULTS = {
    "funding_rate": 0.0,
    "fear_greed": 50,
    "ssr": 10.0,
    "btc_dominance": 50.0,
}

CACHE_PATH = Path(__file__).parent / "data" / "onchain_cache.json"


class OnchainDataFetcher:
    """Fetches real on-chain data with caching and graceful fallbacks."""

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self._memory_cache: Dict[str, dict] = {}
        self._load_disk_cache()

    # ------------------------------------------------------------------ #
    #  Public fetch methods
    # ------------------------------------------------------------------ #

    def fetch_funding_rate(self, symbol: str = "BTCUSDT") -> float:
        """Binance Futures funding rate (latest)."""
        cache_key = f"funding_rate_{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        _fapi_bases = [
            "https://fapi.binance.com", "https://fapi1.binance.com",
            "https://fapi2.binance.com",
        ]
        value = DEFAULTS["funding_rate"]
        for _base in _fapi_bases:
            try:
                resp = requests.get(
                    f"{_base}/fapi/v1/fundingRate",
                    params={"symbol": symbol, "limit": 1},
                    timeout=10,
                )
                if resp.status_code in (451, 403):
                    continue
                resp.raise_for_status()
                data = resp.json()
                value = float(data[0]["fundingRate"]) if data else DEFAULTS["funding_rate"]
                break  # success
            except Exception as exc:
                logger.warning("Funding rate API failed (%s): %s", _base, exc)
                continue

        self._set_cached(cache_key, value)
        return value

    def fetch_fear_greed(self) -> int:
        """Alternative.me Fear & Greed Index (0-100)."""
        cache_key = "fear_greed"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            resp = requests.get(
                "https://api.alternative.me/fng/",
                params={"limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            value = int(data["data"][0]["value"])
        except Exception as exc:
            logger.warning("Fear & Greed API failed: %s", exc)
            value = DEFAULTS["fear_greed"]

        self._set_cached(cache_key, value)
        return value

    def fetch_ssr(self) -> float:
        """Stablecoin Supply Ratio (BTC market cap / stablecoin estimate)."""
        cache_key = "ssr"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/global",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            total_cap = data["total_market_cap"].get("usd", 0)
            btc_dom = data.get("market_cap_percentage", {}).get("btc", 50.0)
            btc_cap = total_cap * (btc_dom / 100.0)
            # Estimate stablecoin market cap from top stablecoins share
            # CoinGecko global doesn't give stablecoin cap directly;
            # approximate as total_cap minus top-coin caps isn't reliable,
            # so use a rough 8-12% of total market cap heuristic.
            # Better: use the "market_cap_percentage" for known stablecoins.
            usdt_pct = data.get("market_cap_percentage", {}).get("usdt", 4.0)
            usdc_pct = data.get("market_cap_percentage", {}).get("usdc", 1.5)
            stablecoin_cap = total_cap * ((usdt_pct + usdc_pct) / 100.0)
            value = round(btc_cap / stablecoin_cap, 2) if stablecoin_cap > 0 else DEFAULTS["ssr"]
        except Exception as exc:
            logger.warning("SSR API failed: %s", exc)
            value = DEFAULTS["ssr"]

        self._set_cached(cache_key, value)
        return value

    def fetch_btc_dominance(self) -> float:
        """BTC dominance percentage from CoinGecko."""
        cache_key = "btc_dominance"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/global",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            value = round(float(data["market_cap_percentage"].get("btc", DEFAULTS["btc_dominance"])), 2)
        except Exception as exc:
            logger.warning("BTC dominance API failed: %s", exc)
            value = DEFAULTS["btc_dominance"]

        self._set_cached(cache_key, value)
        return value

    # ------------------------------------------------------------------ #
    #  Aggregation
    # ------------------------------------------------------------------ #

    def get_all_genes(self, symbol: str = "BTCUSDT") -> dict:
        """Fetch all on-chain genes as a flat dict."""
        return {
            "funding_rate": self.fetch_funding_rate(symbol),
            "fear_greed": self.fetch_fear_greed(),
            "ssr": self.fetch_ssr(),
            "btc_dominance": self.fetch_btc_dominance(),
        }

    @staticmethod
    def get_mutation_bias(genes: dict) -> dict:
        """Derive mutation bias from on-chain genes.

        Returns a dict of bias hints that the mutation engine can use
        to steer offspring towards favourable parameter ranges.
        """
        bias: Dict[str, object] = {}
        fg = genes.get("fear_greed", 50)
        fr = genes.get("funding_rate", 0.0)
        ssr = genes.get("ssr", 10.0)

        # Fear / Greed extremes
        if fg < 20:
            bias["entry_direction"] = "long"
            bias["tp_mult_range"] = (2.0, 5.0)
        elif fg > 80:
            bias["entry_direction"] = "short"

        # Funding rate crowding
        if fr > 0.0003:
            bias["entry_direction"] = "short"
        elif fr < -0.0003:
            bias["entry_direction"] = "long"

        # Stablecoin buying power
        if ssr < 8:
            bias["position_size_range"] = (0.05, 0.15)

        return bias

    # ------------------------------------------------------------------ #
    #  Cache helpers
    # ------------------------------------------------------------------ #

    def _get_cached(self, key: str) -> Optional[object]:
        entry = self._memory_cache.get(key)
        if entry and (time.time() - entry["ts"]) < self.cache_ttl:
            return entry["value"]
        return None

    def _set_cached(self, key: str, value: object) -> None:
        self._memory_cache[key] = {"value": value, "ts": time.time()}
        self._save_disk_cache()

    def _load_disk_cache(self) -> None:
        try:
            if CACHE_PATH.exists():
                with open(CACHE_PATH, "r") as f:
                    self._memory_cache = json.load(f)
        except Exception:
            self._memory_cache = {}

    def _save_disk_cache(self) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, "w") as f:
                json.dump(self._memory_cache, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save disk cache: %s", exc)
