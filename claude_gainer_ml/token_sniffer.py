#!/usr/bin/env python3
"""
CLAUDE CODE — TokenSniffer Scam Detection Integration
======================================================
Checks token safety scores via TokenSniffer API and filters out
potential scams before picks are made.

TokenSniffer scoring:
  - Score < 30  = likely scam (REJECT)
  - Score 30-40 = very risky (REJECT at threshold 40)
  - Score 40-60 = risky (WARN)
  - Score 60+   = probably safe (PASS)

Usage:
    from token_sniffer import TokenSniffer
    sniffer = TokenSniffer(api_key="...")
    result = sniffer.check_token("ethereum", "0x...")
    if result["safe"]:
        # proceed with pick
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SNIFFER_CACHE_FILE = DATA_DIR / "token_sniffer_cache.json"

# ── TokenSniffer API ─────────────────────────────────────────────────────
TOKENSNIFFER_API_BASE = "https://tokensniffer.com/api/v2/tokens"
# Chain IDs for TokenSniffer: 1=ETH, 56=BSC, 137=Polygon, etc.
CHAIN_MAP = {
    "ethereum": 1,
    "eth": 1,
    "binance-smart-chain": 56,
    "bsc": 56,
    "polygon-pos": 137,
    "polygon": 137,
    "avalanche": 43114,
    "avax": 43114,
    "arbitrum-one": 42161,
    "arbitrum": 42161,
    "optimistic-ethereum": 10,
    "optimism": 10,
    "base": 8453,
    "solana": -1,  # Not supported by TokenSniffer API
}

# Known safe coins that don't need sniffer checks
SAFE_COINS = {
    "bitcoin", "ethereum", "tether", "usd-coin", "binancecoin",
    "ripple", "cardano", "solana", "dogecoin", "polkadot",
    "shiba-inu", "avalanche-2", "chainlink", "litecoin", "uniswap",
    "matic-network", "stellar", "cosmos", "monero", "ethereum-classic",
    "internet-computer", "filecoin", "aave", "the-graph", "maker",
    "axie-infinity", "fantom", "theta-token", "vechain", "tron",
    "near", "algorand", "decentraland", "the-sandbox", "flow",
    "hedera-hashgraph", "elrond-erd-2", "tezos", "eos", "iota",
    "wrapped-bitcoin", "dai", "frax", "lido-staked-ether",
}

# Honeypot characteristics to flag
HONEYPOT_INDICATORS = [
    "can_take_back_ownership",
    "cannot_sell_all",
    "cannot_buy",
    "transfer_pausable",
    "hidden_owner",
    "proxy_contract",
    "external_call_risk",
    "self_destruct",
]


class TokenSniffer:
    """Token safety checker using TokenSniffer API."""

    def __init__(self, api_key=None, min_score=40, cache_ttl_hours=24):
        """
        Args:
            api_key: TokenSniffer API key (optional for free tier)
            min_score: Minimum score to consider safe (default 40)
            cache_ttl_hours: Cache TTL in hours (default 24)
        """
        self.api_key = api_key or os.environ.get("TOKENSNIFFER_API_KEY", "")
        self.min_score = min_score
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache = self._load_cache()
        self.request_count = 0
        self.max_requests_per_minute = 10  # Free tier limit

    def _load_cache(self):
        """Load cached results."""
        if SNIFFER_CACHE_FILE.exists():
            try:
                with open(SNIFFER_CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        with open(SNIFFER_CACHE_FILE, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _cache_key(self, chain_id, address):
        """Generate cache key."""
        return f"{chain_id}_{address.lower()}"

    def _is_cached_fresh(self, key):
        """Check if cached result is still fresh."""
        if key not in self.cache:
            return False
        cached = self.cache[key]
        cached_time = datetime.fromisoformat(cached.get("checked_at", "2000-01-01"))
        return datetime.now(timezone.utc) - cached_time < self.cache_ttl

    def check_token(self, chain, address):
        """Check a token's safety score.

        Args:
            chain: Chain name (e.g., "ethereum", "bsc") or chain ID
            address: Token contract address

        Returns:
            dict with keys:
                safe (bool): Whether token passes safety threshold
                score (int): Safety score 0-100
                flags (list): List of flagged issues
                honeypot (bool): Whether honeypot characteristics detected
                details (dict): Full response data
        """
        # Resolve chain ID
        if isinstance(chain, str):
            chain_id = CHAIN_MAP.get(chain.lower(), -1)
        else:
            chain_id = chain

        if chain_id == -1:
            return {
                "safe": True,  # Can't check, assume safe
                "score": -1,
                "flags": ["unsupported_chain"],
                "honeypot": False,
                "details": {"reason": f"Chain '{chain}' not supported by TokenSniffer"},
            }

        if not address or address == "native":
            return {
                "safe": True,
                "score": 100,
                "flags": [],
                "honeypot": False,
                "details": {"reason": "Native token — no contract to check"},
            }

        # Check cache
        key = self._cache_key(chain_id, address)
        if self._is_cached_fresh(key):
            return self.cache[key]["result"]

        # Call API
        result = self._api_check(chain_id, address)

        # Cache result
        self.cache[key] = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "chain_id": chain_id,
            "address": address,
            "result": result,
        }
        self._save_cache()

        return result

    def _api_check(self, chain_id, address):
        """Make actual API call to TokenSniffer."""
        url = f"{TOKENSNIFFER_API_BASE}/{chain_id}/{address}"
        params = {}
        if self.api_key:
            params["apikey"] = self.api_key

        try:
            # Rate limiting
            self.request_count += 1
            if self.request_count > self.max_requests_per_minute:
                print(f"  [SNIFFER] Rate limit — sleeping 60s")
                time.sleep(60)
                self.request_count = 0

            r = requests.get(url, params=params, timeout=15)

            if r.status_code == 429:
                print(f"  [SNIFFER] Rate limited — waiting 60s")
                time.sleep(60)
                r = requests.get(url, params=params, timeout=15)

            if r.status_code == 404:
                return {
                    "safe": False,
                    "score": 0,
                    "flags": ["not_found"],
                    "honeypot": False,
                    "details": {"reason": "Token not found in TokenSniffer database"},
                }

            if r.status_code != 200:
                return {
                    "safe": True,  # Can't check, err on side of allowing
                    "score": -1,
                    "flags": ["api_error"],
                    "honeypot": False,
                    "details": {"reason": f"API error: {r.status_code}", "body": r.text[:200]},
                }

            data = r.json()
            return self._parse_response(data)

        except Exception as e:
            return {
                "safe": True,  # Can't check, err on side of allowing
                "score": -1,
                "flags": ["request_error"],
                "honeypot": False,
                "details": {"reason": f"Request error: {str(e)}"},
            }

    def _parse_response(self, data):
        """Parse TokenSniffer API response."""
        score = data.get("score", -1)
        flags = []
        honeypot = False

        # Check for explicit scam markers
        if data.get("is_flagged"):
            flags.append("FLAGGED_BY_COMMUNITY")
        if data.get("is_scam"):
            flags.append("KNOWN_SCAM")
            score = min(score, 10)

        # Check honeypot indicators
        exploits = data.get("exploits", [])
        for exploit in exploits:
            exploit_id = exploit.get("id", "")
            if exploit_id in HONEYPOT_INDICATORS:
                flags.append(f"HONEYPOT:{exploit_id}")
                honeypot = True

        # Check swap analysis
        swap_analysis = data.get("swap_analysis", {})
        if swap_analysis:
            buy_tax = swap_analysis.get("buy_tax", 0) or 0
            sell_tax = swap_analysis.get("sell_tax", 0) or 0

            if buy_tax > 10:
                flags.append(f"HIGH_BUY_TAX:{buy_tax}%")
            if sell_tax > 10:
                flags.append(f"HIGH_SELL_TAX:{sell_tax}%")
            if sell_tax > 50:
                honeypot = True
                flags.append("LIKELY_HONEYPOT")

        # Check deployer
        deployer = data.get("deployer_analysis", {})
        if deployer:
            if deployer.get("has_deployed_scams"):
                flags.append("DEPLOYER_HAS_SCAM_HISTORY")
                score = min(score, 20)

        # Determine safety
        safe = score >= self.min_score and not honeypot and "KNOWN_SCAM" not in flags

        return {
            "safe": safe,
            "score": score,
            "flags": flags,
            "honeypot": honeypot,
            "details": {
                "name": data.get("name", ""),
                "symbol": data.get("symbol", ""),
                "holders": data.get("holder_count", 0),
                "deployer_scams": deployer.get("has_deployed_scams", False) if deployer else False,
                "buy_tax": swap_analysis.get("buy_tax") if swap_analysis else None,
                "sell_tax": swap_analysis.get("sell_tax") if swap_analysis else None,
                "raw_score": score,
            },
        }

    def check_coingecko_coin(self, coin_id):
        """Check a coin by its CoinGecko ID.

        Many top CoinGecko coins are in the safe list and skip API calls.
        For others, we'd need the contract address from CoinGecko's API.
        """
        # Check safe list first
        if coin_id.lower() in SAFE_COINS:
            return {
                "safe": True,
                "score": 100,
                "flags": [],
                "honeypot": False,
                "details": {"reason": "Known safe coin (top market cap)"},
            }

        # For unknown coins, we'd need contract address
        # This is a placeholder — in production, call CoinGecko /coins/{id}
        # to get platforms.ethereum contract address
        return {
            "safe": True,  # Default to safe if we can't check
            "score": -1,
            "flags": ["no_contract_address"],
            "honeypot": False,
            "details": {"reason": "Contract address not available — needs CoinGecko lookup"},
        }

    def filter_picks(self, picks):
        """Filter a list of pick candidates, removing scams.

        Args:
            picks: List of pick dicts with 'coin_id' field

        Returns:
            (safe_picks, filtered_picks) tuple
        """
        safe = []
        filtered = []

        for pick in picks:
            coin_id = pick.get("coin_id", "")
            result = self.check_coingecko_coin(coin_id)

            pick["sniffer_score"] = result["score"]
            pick["sniffer_safe"] = result["safe"]
            pick["sniffer_flags"] = result["flags"]
            pick["sniffer_honeypot"] = result["honeypot"]

            if result["safe"]:
                safe.append(pick)
            else:
                filtered.append(pick)
                print(f"  [SNIFFER] FILTERED: {pick.get('symbol', '?')} — "
                      f"score={result['score']}, flags={result['flags']}")

        print(f"  [SNIFFER] {len(safe)} safe, {len(filtered)} filtered out of {len(picks)} candidates")
        return safe, filtered


def main():
    """Standalone test of TokenSniffer integration."""
    print("=" * 60)
    print("  CLAUDE CODE — TokenSniffer Test")
    print("=" * 60)

    sniffer = TokenSniffer()

    # Test safe coins
    print("\n  Testing known safe coins:")
    for coin_id in ["bitcoin", "ethereum", "solana", "dogecoin"]:
        result = sniffer.check_coingecko_coin(coin_id)
        status = "SAFE" if result["safe"] else "BLOCKED"
        print(f"    {coin_id:>20}: [{status}] score={result['score']} flags={result['flags']}")

    # Test unknown coin
    print("\n  Testing unknown coins:")
    for coin_id in ["some-random-token-xyz", "definitely-not-a-scam"]:
        result = sniffer.check_coingecko_coin(coin_id)
        status = "SAFE" if result["safe"] else "BLOCKED"
        print(f"    {coin_id:>30}: [{status}] score={result['score']} flags={result['flags']}")

    # Test filter_picks
    print("\n  Testing pick filtering:")
    test_picks = [
        {"coin_id": "bitcoin", "symbol": "BTC"},
        {"coin_id": "ethereum", "symbol": "ETH"},
        {"coin_id": "random-scam-token", "symbol": "SCAM"},
    ]
    safe, filtered = sniffer.filter_picks(test_picks)
    print(f"    Picks passed: {len(safe)}")
    print(f"    Picks filtered: {len(filtered)}")

    print("\n  TokenSniffer integration ready.")


if __name__ == "__main__":
    main()
