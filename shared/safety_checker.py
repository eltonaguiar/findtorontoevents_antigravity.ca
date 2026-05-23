#!/usr/bin/env python3
"""
Unified Rugpull / Honeypot Safety Checker
==========================================
Checks every pick against GoPlus Security API before it reaches the dashboard.
Whitelisted major coins skip API calls entirely (score=100).

GoPlus API: free, no auth, generous rate limits.
Scoring: start at 100, deduct for red flags. <30 = BLOCKED.

Usage:
    from shared.safety_checker import SafetyChecker
    safety = SafetyChecker()
    enriched = safety.enrich_picks(picks)
"""

import json
import time
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# ── Configuration ─────────────────────────────────────────────────────────

GOPLUS_BASE = "https://api.gopluslabs.com/api/v1/token_security"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

CACHE_TTL_HOURS = 24
RATE_LIMIT_DELAY = 0.5  # seconds between GoPlus calls
DEFAULT_BLOCK_THRESHOLD = 30

# GoPlus chain IDs
CHAIN_MAP = {
    "ethereum": "1", "eth": "1",
    "bsc": "56", "binance-smart-chain": "56",
    "solana": "solana",
    "polygon": "137", "polygon-pos": "137",
    "avalanche": "43114", "avax": "43114",
    "arbitrum": "42161", "arbitrum-one": "42161",
    "optimism": "10", "optimistic-ethereum": "10",
    "base": "8453",
    "fantom": "250",
    "cronos": "25",
}

# ── Whitelisted Symbols & CoinGecko IDs ──────────────────────────────────
# Major coins that are guaranteed safe — skip all API calls.

WHITELIST_SYMBOLS = {
    # Top crypto by market cap
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "LINK",
    "NEAR", "ATOM", "LTC", "DOGE", "SHIB", "MATIC", "POL", "TRX", "UNI",
    "AAVE", "MKR", "GRT", "FIL", "ETC", "BCH", "ALGO", "ICP", "APT",
    "SUI", "SEI", "TIA", "INJ", "RUNE", "STX", "OP", "ARB", "FTM",
    "CRO", "HBAR", "VET", "THETA", "XLM", "XMR", "EOS", "IOTA",
    "SAND", "MANA", "AXS", "FLOW", "NEO", "EGLD", "KAVA", "QNT",
    "RENDER", "FET", "TAO", "WLD", "JUP", "PYTH", "JTO", "W",
    # Stablecoins
    "USDT", "USDC", "DAI", "FRAX", "TUSD", "BUSD",
    # Wrapped tokens
    "WBTC", "WETH", "STETH",
    # Forex & equity symbols (always safe)
    "SPY", "QQQ", "GLD", "TLT", "IWM", "DIA", "VTI",
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF",
}

WHITELIST_COINGECKO_IDS = {
    "bitcoin", "ethereum", "tether", "usd-coin", "binancecoin",
    "ripple", "cardano", "solana", "dogecoin", "polkadot",
    "shiba-inu", "avalanche-2", "chainlink", "litecoin", "uniswap",
    "matic-network", "stellar", "cosmos", "monero", "ethereum-classic",
    "internet-computer", "filecoin", "aave", "the-graph", "maker",
    "near", "algorand", "tron", "wrapped-bitcoin", "dai",
    "frax", "lido-staked-ether", "aptos", "sui", "sei-network",
    "celestia", "injective-protocol", "thorchain", "stacks",
    "optimism", "arbitrum", "fantom", "render-token", "fetch-ai",
    "bittensor", "worldcoin-wld", "jupiter-exchange-solana",
}

# ── Scoring Deductions ───────────────────────────────────────────────────

DEDUCTIONS = {
    "is_honeypot":              -100,  # Instant block
    "is_open_source_0":          -30,  # Unverified/closed source
    "can_take_back_ownership":   -25,  # Owner can reclaim
    "hidden_owner":              -20,  # Obfuscated ownership
    "is_proxy":                  -15,  # Proxy contract (upgradeable)
    "selfdestruct":              -15,  # Self-destruct capability
    "external_call":             -10,  # External call risk
    "transfer_pausable":         -10,  # Can pause transfers
    "cannot_sell_all":           -50,  # Can't sell full balance
    "cannot_buy":                -50,  # Can't buy
    "buy_tax_high":              -10,  # per 5% above 5%
    "sell_tax_high":             -15,  # per 5% above 10%
    "low_holders_50":            -10,  # < 50 holders
    "low_holders_20":            -20,  # < 20 holders (additional)
}


class SafetyChecker:
    """Unified token safety checker using GoPlus Security API."""

    def __init__(self, cache_dir=None, block_threshold=DEFAULT_BLOCK_THRESHOLD):
        self.block_threshold = block_threshold
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "safety_cache.json"
        self.cache = self._load_cache()
        self._last_call_time = 0

    # ── Public API ────────────────────────────────────────────────────────

    def check_token(self, symbol, contract_address=None, chain=None, coin_id=None):
        """Check a single token's safety. Returns dict with safety_score, safety_flags, is_safe."""
        clean_sym = self._clean_symbol(symbol)

        # 1. Whitelist check
        if clean_sym in WHITELIST_SYMBOLS:
            return self._safe_result(100, source="whitelist")
        if coin_id and coin_id.lower() in WHITELIST_COINGECKO_IDS:
            return self._safe_result(100, source="whitelist")

        # 2. Non-crypto symbols are always safe
        if self._is_non_crypto(symbol):
            return self._safe_result(100, source="non_crypto")

        # 3. Check cache
        cache_key = self._cache_key(clean_sym, contract_address)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # 4. Need contract address for GoPlus
        if not contract_address and coin_id:
            contract_address, chain = self._resolve_contract_via_coingecko(coin_id)

        if not contract_address:
            # Can't verify without contract — permissive default
            result = self._safe_result(-1, flags=["no_contract_address"],
                                       source="unknown")
            self._set_cached(cache_key, result)
            return result

        # 5. Detect chain if not provided
        if not chain:
            chain = self._detect_chain(symbol) or "1"  # default to Ethereum

        chain_id = CHAIN_MAP.get(str(chain).lower(), str(chain))

        # 6. GoPlus API check
        result = self._goplus_check(chain_id, contract_address)
        self._set_cached(cache_key, result)
        return result

    def enrich_picks(self, picks):
        """Add safety_score, safety_flags, is_safe to each pick. Mark unsafe picks."""
        if not requests:
            print("  [SAFETY] requests library not available, skipping safety checks")
            return picks

        checked = 0
        blocked = 0
        whitelisted = 0

        for pick in picks:
            symbol = pick.get("symbol", "")
            contract = pick.get("extra", {}).get("token_address") if isinstance(pick.get("extra"), dict) else None
            chain = pick.get("extra", {}).get("chain") if isinstance(pick.get("extra"), dict) else None
            coin_id = pick.get("coin_id", "")

            result = self.check_token(symbol, contract_address=contract,
                                      chain=chain, coin_id=coin_id)

            pick["safety_score"] = result["safety_score"]
            pick["safety_flags"] = result["safety_flags"]
            pick["is_safe"] = result["is_safe"]
            pick["safety_source"] = result["source"]

            if result.get("details"):
                pick["safety_details"] = result["details"]

            if result["source"] == "whitelist":
                whitelisted += 1
            else:
                checked += 1

            if not result["is_safe"]:
                blocked += 1
                pick["status"] = "BLOCKED_UNSAFE"
                print(f"  [SAFETY] BLOCKED: {symbol} — score={result['safety_score']}, "
                      f"flags={result['safety_flags']}")

        self._save_cache()
        print(f"  [SAFETY] {whitelisted} whitelisted, {checked} checked, {blocked} blocked")
        return picks

    # ── GoPlus Integration ────────────────────────────────────────────────

    def _goplus_check(self, chain_id, address):
        """Call GoPlus Security API and compute safety score."""
        if not requests:
            return self._safe_result(-1, flags=["no_requests_lib"], source="error")

        # Rate limit
        elapsed = time.time() - self._last_call_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)

        url = f"{GOPLUS_BASE}/{chain_id}?contract_addresses={address}"
        try:
            self._last_call_time = time.time()
            r = requests.get(url, timeout=10)

            if r.status_code != 200:
                return self._safe_result(-1, flags=["goplus_api_error"],
                                         source="error")

            data = r.json()
            if not data or "result" not in data:
                return self._safe_result(-1, flags=["goplus_empty_response"],
                                         source="error")

            # GoPlus returns results keyed by lowercase address
            token_info = data["result"].get(address.lower(), {})
            if not token_info:
                token_info = data["result"].get(address, {})
            if not token_info:
                # Try first key if only one result
                keys = list(data["result"].keys())
                token_info = data["result"][keys[0]] if keys else {}

            if not token_info:
                return self._safe_result(-1, flags=["goplus_no_data"],
                                         source="goplus")

            return self._compute_score(token_info)

        except Exception as e:
            return self._safe_result(-1, flags=[f"goplus_error:{str(e)[:50]}"],
                                     source="error")

    def _compute_score(self, info):
        """Convert GoPlus response into a 0-100 safety score."""
        score = 100
        flags = []
        details = {}

        # Honeypot — instant kill
        if info.get("is_honeypot") == "1":
            score = 0
            flags.append("HONEYPOT")

        # Open source check
        if info.get("is_open_source") == "0":
            score += DEDUCTIONS["is_open_source_0"]
            flags.append("CLOSED_SOURCE")

        # Ownership flags
        if info.get("can_take_back_ownership") == "1":
            score += DEDUCTIONS["can_take_back_ownership"]
            flags.append("CAN_RECLAIM_OWNERSHIP")

        if info.get("hidden_owner") == "1":
            score += DEDUCTIONS["hidden_owner"]
            flags.append("HIDDEN_OWNER")

        if info.get("owner_change_balance") == "1":
            score -= 15
            flags.append("OWNER_CAN_CHANGE_BALANCE")

        # Proxy / upgradeable
        if info.get("is_proxy") == "1":
            score += DEDUCTIONS["is_proxy"]
            flags.append("PROXY_CONTRACT")

        # Self-destruct
        if info.get("selfdestruct") == "1":
            score += DEDUCTIONS["selfdestruct"]
            flags.append("SELF_DESTRUCT")

        # External call
        if info.get("external_call") == "1":
            score += DEDUCTIONS["external_call"]
            flags.append("EXTERNAL_CALL")

        # Transfer restrictions
        if info.get("transfer_pausable") == "1":
            score += DEDUCTIONS["transfer_pausable"]
            flags.append("TRANSFER_PAUSABLE")

        if info.get("cannot_sell_all") == "1":
            score += DEDUCTIONS["cannot_sell_all"]
            flags.append("CANNOT_SELL_ALL")

        if info.get("cannot_buy") == "1":
            score += DEDUCTIONS["cannot_buy"]
            flags.append("CANNOT_BUY")

        # Tax analysis
        buy_tax = float(info.get("buy_tax", 0) or 0)
        sell_tax = float(info.get("sell_tax", 0) or 0)
        details["buy_tax"] = round(buy_tax * 100, 1)
        details["sell_tax"] = round(sell_tax * 100, 1)

        if buy_tax > 0.05:
            penalty = int((buy_tax - 0.05) / 0.05) * abs(DEDUCTIONS["buy_tax_high"])
            score -= penalty
            flags.append(f"BUY_TAX_{details['buy_tax']:.0f}%")

        if sell_tax > 0.10:
            penalty = int((sell_tax - 0.10) / 0.05) * abs(DEDUCTIONS["sell_tax_high"])
            score -= penalty
            flags.append(f"SELL_TAX_{details['sell_tax']:.0f}%")

        # Holder count
        holder_count = int(info.get("holder_count", 0) or 0)
        details["holder_count"] = holder_count

        if holder_count > 0:
            if holder_count < 20:
                score += DEDUCTIONS["low_holders_50"]
                score += DEDUCTIONS["low_holders_20"]
                flags.append(f"ONLY_{holder_count}_HOLDERS")
            elif holder_count < 50:
                score += DEDUCTIONS["low_holders_50"]
                flags.append(f"LOW_HOLDERS_{holder_count}")

        # LP info
        details["lp_holder_count"] = int(info.get("lp_holder_count", 0) or 0)
        details["is_in_dex"] = info.get("is_in_dex") == "1"
        details["ownership_renounced"] = info.get("owner_address") in ("", "0x0000000000000000000000000000000000000000", None)
        details["token_name"] = info.get("token_name", "")
        details["token_symbol"] = info.get("token_symbol", "")
        details["total_supply"] = info.get("total_supply", "")

        # Clamp
        score = max(0, min(100, score))
        is_safe = score >= self.block_threshold

        return {
            "safety_score": score,
            "safety_flags": flags,
            "is_safe": is_safe,
            "honeypot": "HONEYPOT" in flags,
            "source": "goplus",
            "details": details,
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _clean_symbol(self, symbol):
        """Normalize symbol to base ticker: 'BTCUSDT' → 'BTC', 'DEX:PEPE' → 'PEPE'."""
        s = str(symbol).upper().strip()

        # Remove prefixes like DEX:, ETH:, BSC:
        if ":" in s:
            s = s.split(":", 1)[1]

        # Remove common suffixes
        for suffix in ("USDT", "USDC", "BUSD", "-USD", "-USDT",
                        "/USD", "/USDT", "USD", "BTC", "ETH", "=X"):
            if s.endswith(suffix) and len(s) > len(suffix):
                s = s[:-len(suffix)]
                break

        return s

    def _is_non_crypto(self, symbol):
        """Check if symbol is forex/equity (always safe)."""
        s = str(symbol).upper()
        # Forex pairs
        if "=X" in s or any(s.startswith(p) for p in ("EUR", "GBP", "JPY", "AUD", "CAD", "CHF")):
            if len(s) <= 8:
                return True
        # Known equity ETFs
        equity = {"SPY", "QQQ", "GLD", "TLT", "IWM", "DIA", "VTI", "VOO"}
        if self._clean_symbol(symbol) in equity:
            return True
        return False

    def _detect_chain(self, symbol):
        """Infer chain from symbol prefix."""
        s = str(symbol).upper()
        if s.startswith("DEX:") or s.startswith("ETH:"):
            return "1"
        if s.startswith("BSC:"):
            return "56"
        if s.startswith("SOL:"):
            return "solana"
        if s.startswith("ARB:"):
            return "42161"
        if s.startswith("BASE:"):
            return "8453"
        if s.startswith("OP:"):
            return "10"
        if s.startswith("AVAX:"):
            return "43114"
        # Default: most Binance pairs are on Ethereum/BSC
        return None

    def _resolve_contract_via_coingecko(self, coin_id):
        """Look up contract address from CoinGecko. Returns (address, chain) or (None, None)."""
        if not requests:
            return None, None

        try:
            url = f"{COINGECKO_BASE}/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=false&developer_data=false"
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return None, None

            data = r.json()
            platforms = data.get("platforms", {})

            # Prefer Ethereum, then BSC, then any
            for chain_name in ["ethereum", "binance-smart-chain", "polygon-pos",
                                "arbitrum-one", "optimistic-ethereum", "base", "avalanche"]:
                addr = platforms.get(chain_name, "")
                if addr and len(addr) > 10:
                    chain_id = CHAIN_MAP.get(chain_name, "1")
                    return addr, chain_id

            # Take first available
            for chain_name, addr in platforms.items():
                if addr and len(str(addr)) > 10 and chain_name != "":
                    chain_id = CHAIN_MAP.get(chain_name, "1")
                    return addr, chain_id

        except Exception:
            pass

        return None, None

    def _safe_result(self, score, flags=None, source="whitelist"):
        """Build a safe result dict."""
        return {
            "safety_score": score,
            "safety_flags": flags or [],
            "is_safe": True,
            "honeypot": False,
            "source": source,
            "details": {},
        }

    # ── Cache ─────────────────────────────────────────────────────────────

    def _cache_key(self, symbol, contract_address=None):
        if contract_address:
            return f"{symbol}_{contract_address[:20]}".lower()
        return symbol.lower()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception:
            pass

    def _get_cached(self, key):
        if key not in self.cache:
            return None
        entry = self.cache[key]
        checked_at = entry.get("checked_at", "")
        try:
            ts = datetime.fromisoformat(checked_at)
            if datetime.now(timezone.utc) - ts < timedelta(hours=CACHE_TTL_HOURS):
                return entry.get("result")
        except (ValueError, TypeError):
            pass
        return None

    def _set_cached(self, key, result):
        self.cache[key] = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
        }


# ── Standalone test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Safety Checker — GoPlus Integration Test")
    print("=" * 60)

    checker = SafetyChecker()

    # Test whitelisted coins
    print("\n  Whitelisted coins:")
    for sym in ["BTC", "ETHUSDT", "SOL-USD", "DEX:UNI"]:
        r = checker.check_token(sym)
        print(f"    {sym:>15}: score={r['safety_score']}, safe={r['is_safe']}, source={r['source']}")

    # Test with contract address (PEPE on Ethereum)
    print("\n  Contract check (PEPE):")
    r = checker.check_token("PEPE",
                            contract_address="0x6982508145454Ce325dDbE47a25d4ec3d2311933",
                            chain="1")
    print(f"    PEPE: score={r['safety_score']}, flags={r['safety_flags']}, source={r['source']}")

    print("\n  Done.")
