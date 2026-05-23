"""
Enhanced Data Feeds — Professional Crypto Intelligence
=====================================================
Free public API data feeds used by crypto hedge funds:
- On-chain metrics (Etherscan, Blockchain.info)
- Mining stats (hashrate, difficulty, miner revenue)
- Token holder analytics (holder count, concentration)
- Glassnode free-tier metrics
- Google Trends sentiment
- Fear & Greed Index (already have, but integrate)
- ETF flow proxy (via public data)
- Funding rates across exchanges
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger("EnhancedDataFeeds")

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "market_intel"


@dataclass
class MarketIntelligence:
    """Aggregated market intelligence snapshot."""
    timestamp: str
    fear_greed_index: int = 50
    fear_greed_label: str = "Neutral"
    btc_hashrate_th: float = 0.0
    btc_difficulty: float = 0.0
    btc_miner_revenue_usd: float = 0.0
    eth_gas_price_gwei: float = 0.0
    eth_total_supply: float = 0.0
    google_trends_bitcoin: int = 0  # 0-100 search interest
    google_trends_ethereum: int = 0
    google_trends_crypto: int = 0
    btc_exchange_netflow: float = 0.0  # negative = outflow (bullish)
    btc_active_addresses_24h: int = 0
    eth_active_addresses_24h: int = 0
    stablecoin_market_cap_b: float = 0.0
    btc_realized_price: float = 0.0
    btc_mvrv_ratio: float = 0.0
    funding_rate_btc: float = 0.0
    funding_rate_eth: float = 0.0
    open_interest_btc_b: float = 0.0
    long_short_ratio_btc: float = 0.0
    # Token holder data
    holder_data: Dict[str, Dict] = field(default_factory=dict)
    # Supply data
    supply_data: Dict[str, Dict] = field(default_factory=dict)
    # Signals derived from the data
    signals: List[Dict] = field(default_factory=list)


class EnhancedDataFeeds:
    """Fetch and aggregate professional-grade market intelligence."""

    def __init__(self, etherscan_key: str = None, glassnode_key: str = None):
        self.etherscan_key = etherscan_key or os.environ.get("ETHERSCAN_API_KEY", "")
        self.glassnode_key = glassnode_key or os.environ.get("GLASSNODE_API_KEY", "")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self._cache_ttl = 300  # 5 min cache

    def _cached_get(self, url: str, params: dict = None, ttl: int = None) -> Optional[Any]:
        """HTTP GET with caching and rate limiting."""
        import requests
        cache_key = f"{url}_{json.dumps(params or {}, sort_keys=True)}"
        now = time.time()
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if now - ts < (ttl or self._cache_ttl):
                return data
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            # Some blockchain.info endpoints return plain text numbers
            content_type = resp.headers.get("content-type", "")
            if "json" in content_type or resp.text.strip().startswith(("{", "[")):
                data = resp.json()
            else:
                # Try to parse as a number (blockchain.info /q/ endpoints)
                text = resp.text.strip()
                try:
                    data = float(text) if "." in text else int(text)
                except ValueError:
                    data = text
            self._cache[cache_key] = (data, now)
            return data
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    # === FEAR & GREED ===
    def fetch_fear_greed(self) -> tuple:
        """Fetch Fear & Greed index. Returns (value, label)."""
        data = self._cached_get("https://api.alternative.me/fng/?limit=1")
        if data and isinstance(data, dict) and data.get("data"):
            val = int(data["data"][0]["value"])
            label = data["data"][0]["value_classification"]
            return val, label
        return 50, "Neutral"

    # === BITCOIN MINING STATS ===
    def fetch_btc_mining(self) -> Dict:
        """Fetch BTC hashrate, difficulty, miner revenue from blockchain.info."""
        result = {"hashrate_th": 0.0, "difficulty": 0.0, "miner_revenue_usd": 0.0}

        # Hashrate (GH/s from blockchain.info, convert to TH/s)
        data = self._cached_get("https://blockchain.info/q/hashrate")
        if data is not None:
            try:
                result["hashrate_th"] = float(data) / 1e3  # GH/s -> TH/s
            except (TypeError, ValueError):
                pass

        # Difficulty
        data = self._cached_get("https://blockchain.info/q/getdifficulty")
        if data is not None:
            try:
                result["difficulty"] = float(data)
            except (TypeError, ValueError):
                pass

        # Miner revenue (from blockchain.info charts API)
        data = self._cached_get(
            "https://api.blockchain.info/charts/miners-revenue",
            {"timespan": "1days", "format": "json"}
        )
        if data and isinstance(data, dict) and "values" in data and data["values"]:
            result["miner_revenue_usd"] = data["values"][-1].get("y", 0)

        return result

    # === ETHEREUM ON-CHAIN (Etherscan) ===
    def fetch_eth_onchain(self) -> Dict:
        """Fetch ETH gas price, supply from Etherscan free API."""
        result = {"gas_price_gwei": 0.0, "total_supply": 0.0, "eth2_staked": 0.0}

        if self.etherscan_key:
            # Gas price
            data = self._cached_get(
                "https://api.etherscan.io/api",
                {"module": "gastracker", "action": "gasoracle", "apikey": self.etherscan_key}
            )
            if data and isinstance(data, dict) and data.get("result") and isinstance(data["result"], dict):
                try:
                    result["gas_price_gwei"] = float(data["result"].get("SafeGasPrice", 0))
                except (TypeError, ValueError):
                    pass

            # ETH supply
            data = self._cached_get(
                "https://api.etherscan.io/api",
                {"module": "stats", "action": "ethsupply", "apikey": self.etherscan_key}
            )
            if data and isinstance(data, dict) and data.get("result"):
                try:
                    result["total_supply"] = float(data["result"]) / 1e18
                except (TypeError, ValueError):
                    pass
        else:
            logger.info("No ETHERSCAN_API_KEY, skipping Etherscan feeds")

        return result

    # === TOKEN HOLDER DATA ===
    def fetch_token_holders(self, symbols: List[str] = None) -> Dict:
        """Fetch holder counts and supply info from CoinGecko free API."""
        if symbols is None:
            symbols = ["bitcoin", "ethereum", "solana", "dogecoin", "cardano"]

        result = {}
        for coin_id in symbols:
            data = self._cached_get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                {"localization": "false", "tickers": "false", "community_data": "true",
                 "developer_data": "false"}
            )
            if data and isinstance(data, dict):
                market = data.get("market_data", {})
                community = data.get("community_data", {})
                total_supply = market.get("total_supply") or 0
                circulating_supply = market.get("circulating_supply") or 0
                result[coin_id] = {
                    "circulating_supply": circulating_supply,
                    "total_supply": total_supply,
                    "max_supply": market.get("max_supply"),  # None = unlimited
                    "supply_ratio": (circulating_supply / total_supply) if total_supply else 0,
                    "is_capped": market.get("max_supply") is not None,
                    "reddit_subscribers": community.get("reddit_subscribers", 0),
                    "twitter_followers": community.get("twitter_followers", 0),
                    "telegram_members": community.get("telegram_channel_user_count", 0),
                }
                # Rate limit for CoinGecko free tier
                time.sleep(1.5)

        return result

    # === GOOGLE TRENDS ===
    def fetch_google_trends(self) -> Dict:
        """Fetch Google Trends data for crypto keywords.
        Uses pytrends library if available, otherwise returns zeros."""
        result = {"bitcoin": 0, "ethereum": 0, "crypto": 0, "solana": 0}
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
            kw_list = ["bitcoin", "ethereum", "crypto", "solana"]
            pytrends.build_payload(kw_list, cat=0, timeframe='now 7-d')
            df = pytrends.interest_over_time()
            if not df.empty:
                for kw in kw_list:
                    if kw in df.columns:
                        result[kw] = int(df[kw].iloc[-1])
        except ImportError:
            logger.info("pytrends not installed — Google Trends data unavailable (pip install pytrends)")
        except Exception as e:
            logger.warning(f"Google Trends fetch failed: {e}")
        return result

    # === Binance futures failover bases ===
    _FAPI_BASES = [
        "https://fapi.binance.com",
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
    ]

    def _cached_get_fapi(self, path: str, params: dict = None, ttl: int = None) -> Optional[Any]:
        """Fetch from Binance futures API with endpoint failover."""
        for base in self._FAPI_BASES:
            data = self._cached_get(f"{base}{path}", params, ttl)
            if data is not None:
                return data
        return None

    # === FUNDING RATES ===
    def fetch_funding_rates(self) -> Dict:
        """Fetch perpetual funding rates from Binance (with failover)."""
        result = {}
        symbols = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "AVAXUSDT"}
        data = self._cached_get_fapi("/fapi/v1/premiumIndex")
        if data and isinstance(data, list):
            for item in data:
                sym = item.get("symbol", "")
                if sym in symbols:
                    result[sym] = {
                        "funding_rate": float(item.get("lastFundingRate", 0)),
                        "mark_price": float(item.get("markPrice", 0)),
                        "index_price": float(item.get("indexPrice", 0)),
                        "basis": float(item.get("markPrice", 0)) - float(item.get("indexPrice", 0)),
                    }
        return result

    # === OPEN INTEREST ===
    def fetch_open_interest(self) -> Dict:
        """Fetch open interest from Binance futures (with failover)."""
        result = {}
        for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            data = self._cached_get_fapi(
                "/fapi/v1/openInterest",
                {"symbol": sym}
            )
            if data and isinstance(data, dict):
                result[sym] = {
                    "open_interest": float(data.get("openInterest", 0)),
                    "symbol": sym,
                }
        return result

    # === LONG/SHORT RATIO ===
    def fetch_long_short_ratio(self) -> Dict:
        """Fetch top trader long/short ratio from Binance (with failover)."""
        result = {}
        for sym in ["BTCUSDT", "ETHUSDT"]:
            data = self._cached_get_fapi(
                "/futures/data/topLongShortPositionRatio",
                {"symbol": sym, "period": "1h", "limit": 1}
            )
            if data and isinstance(data, list) and len(data) > 0:
                result[sym] = {
                    "long_account": float(data[0].get("longAccount", 0.5)),
                    "short_account": float(data[0].get("shortAccount", 0.5)),
                    "long_short_ratio": float(data[0].get("longShortRatio", 1.0)),
                }
        return result

    # === BTC EXCHANGE FLOWS (blockchain.info proxy) ===
    def fetch_exchange_flows(self) -> Dict:
        """Estimate exchange netflow from blockchain.info mempool + n_tx."""
        result = {"btc_unconfirmed_tx": 0, "btc_n_tx_24h": 0}
        data = self._cached_get("https://blockchain.info/q/unconfirmedcount")
        if data is not None:
            try:
                result["btc_unconfirmed_tx"] = int(data)
            except (TypeError, ValueError):
                pass

        data = self._cached_get(
            "https://api.blockchain.info/charts/n-transactions",
            {"timespan": "1days", "format": "json"}
        )
        if data and isinstance(data, dict) and "values" in data and data["values"]:
            result["btc_n_tx_24h"] = int(data["values"][-1].get("y", 0))

        return result

    # === STABLECOIN SUPPLY (CoinGecko) ===
    def fetch_stablecoin_mcap(self) -> float:
        """Fetch total stablecoin market cap as buying power indicator."""
        total = 0.0
        for coin_id in ["tether", "usd-coin", "dai", "first-digital-usd"]:
            data = self._cached_get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                {"localization": "false", "tickers": "false", "community_data": "false"}
            )
            if data and isinstance(data, dict):
                mcap = data.get("market_data", {}).get("market_cap", {}).get("usd", 0)
                total += mcap
            time.sleep(1.5)
        return total / 1e9  # Return in billions

    # === GLASSNODE FREE TIER ===
    def fetch_glassnode_free(self) -> Dict:
        """Fetch available Glassnode free-tier metrics."""
        result = {}
        if not self.glassnode_key:
            logger.info("No GLASSNODE_API_KEY, skipping Glassnode feeds")
            return result

        endpoints = {
            "active_addresses": "/v1/metrics/addresses/active_count",
            "new_addresses": "/v1/metrics/addresses/new_non_zero_count",
            "transaction_count": "/v1/metrics/transactions/count",
        }

        for metric_name, endpoint in endpoints.items():
            data = self._cached_get(
                f"https://api.glassnode.com{endpoint}",
                {"a": "BTC", "api_key": self.glassnode_key, "i": "24h"}
            )
            if data and isinstance(data, list) and len(data) > 0:
                result[metric_name] = data[-1].get("v", 0)

        return result

    # === AGGREGATE ALL ===
    def fetch_all(self, include_holders: bool = False) -> MarketIntelligence:
        """Fetch all data feeds and return aggregated MarketIntelligence."""
        logger.info("Fetching enhanced market intelligence...")

        intel = MarketIntelligence(timestamp=datetime.now(timezone.utc).isoformat())

        # Fear & Greed
        intel.fear_greed_index, intel.fear_greed_label = self.fetch_fear_greed()

        # Mining
        mining = self.fetch_btc_mining()
        intel.btc_hashrate_th = mining["hashrate_th"]
        intel.btc_difficulty = mining["difficulty"]
        intel.btc_miner_revenue_usd = mining["miner_revenue_usd"]

        # ETH on-chain
        eth = self.fetch_eth_onchain()
        intel.eth_gas_price_gwei = eth["gas_price_gwei"]
        intel.eth_total_supply = eth["total_supply"]

        # Funding rates
        funding = self.fetch_funding_rates()
        if "BTCUSDT" in funding:
            intel.funding_rate_btc = funding["BTCUSDT"]["funding_rate"]
        if "ETHUSDT" in funding:
            intel.funding_rate_eth = funding["ETHUSDT"]["funding_rate"]

        # Open interest
        oi = self.fetch_open_interest()
        if "BTCUSDT" in oi:
            intel.open_interest_btc_b = oi["BTCUSDT"]["open_interest"]

        # Long/short ratio
        ls = self.fetch_long_short_ratio()
        if "BTCUSDT" in ls:
            intel.long_short_ratio_btc = ls["BTCUSDT"]["long_short_ratio"]

        # Exchange flows
        flows = self.fetch_exchange_flows()
        intel.btc_active_addresses_24h = flows.get("btc_n_tx_24h", 0)

        # Google Trends
        trends = self.fetch_google_trends()
        intel.google_trends_bitcoin = trends.get("bitcoin", 0)
        intel.google_trends_ethereum = trends.get("ethereum", 0)
        intel.google_trends_crypto = trends.get("crypto", 0)

        # Glassnode
        glass = self.fetch_glassnode_free()
        if glass.get("active_addresses"):
            intel.btc_active_addresses_24h = glass["active_addresses"]

        # Token holders (slower, optional)
        if include_holders:
            intel.holder_data = self.fetch_token_holders()
            for coin, hdata in intel.holder_data.items():
                intel.supply_data[coin] = {
                    "circulating": hdata["circulating_supply"],
                    "total": hdata["total_supply"],
                    "max": hdata["max_supply"],
                    "is_capped": hdata["is_capped"],
                    "supply_ratio": hdata["supply_ratio"],
                }

        # Derive signals from aggregated data
        intel.signals = self._derive_signals(intel, funding, ls)

        # Save to cache
        self._save_snapshot(intel)

        logger.info(f"Market intelligence ready: F&G={intel.fear_greed_index}, "
                     f"BTC funding={intel.funding_rate_btc:.4%}, "
                     f"Trends BTC={intel.google_trends_bitcoin}")
        return intel

    def _derive_signals(self, intel: MarketIntelligence, funding: Dict, ls: Dict) -> List[Dict]:
        """Derive actionable signals from aggregated data."""
        signals = []

        # 1. Extreme Fear = contrarian buy signal
        if intel.fear_greed_index <= 20:
            signals.append({
                "signal": "FEAR_EXTREME_BUY",
                "strength": min(1.0, (25 - intel.fear_greed_index) / 25),
                "description": f"F&G at {intel.fear_greed_index} (Extreme Fear) — contrarian buy zone",
                "direction": "LONG",
                "confidence": 0.65,
            })
        elif intel.fear_greed_index >= 80:
            signals.append({
                "signal": "GREED_EXTREME_SELL",
                "strength": min(1.0, (intel.fear_greed_index - 75) / 25),
                "description": f"F&G at {intel.fear_greed_index} (Extreme Greed) — distribution zone",
                "direction": "SHORT",
                "confidence": 0.60,
            })

        # 2. Funding rate carry signals
        for sym, fdata in funding.items():
            rate = fdata["funding_rate"]
            if rate > 0.0005:  # > 0.05% = overleveraged longs
                signals.append({
                    "signal": "FUNDING_OVERLEVERAGED_LONGS",
                    "symbol": sym,
                    "strength": min(1.0, rate / 0.001),
                    "description": f"{sym} funding {rate:.4%} — longs paying premium, squeeze risk",
                    "direction": "SHORT",
                    "confidence": 0.60,
                })
            elif rate < -0.0003:  # < -0.03% = overleveraged shorts
                signals.append({
                    "signal": "FUNDING_OVERLEVERAGED_SHORTS",
                    "symbol": sym,
                    "strength": min(1.0, abs(rate) / 0.001),
                    "description": f"{sym} funding {rate:.4%} — shorts paying, squeeze up risk",
                    "direction": "LONG",
                    "confidence": 0.60,
                })

        # 3. Long/short ratio extremes
        for sym, lsdata in ls.items():
            ratio = lsdata["long_short_ratio"]
            if ratio > 2.0:  # Too many longs
                signals.append({
                    "signal": "CROWD_OVERLEVERAGED_LONG",
                    "symbol": sym,
                    "strength": min(1.0, (ratio - 1.5) / 2),
                    "description": f"{sym} L/S ratio {ratio:.2f} — crowded long, contrarian short",
                    "direction": "SHORT",
                    "confidence": 0.55,
                })
            elif ratio < 0.5:  # Too many shorts
                signals.append({
                    "signal": "CROWD_OVERLEVERAGED_SHORT",
                    "symbol": sym,
                    "strength": min(1.0, (1.0 - ratio) / 0.8),
                    "description": f"{sym} L/S ratio {ratio:.2f} — crowded short, contrarian long",
                    "direction": "LONG",
                    "confidence": 0.55,
                })

        # 4. Google Trends momentum
        if intel.google_trends_bitcoin > 80:
            signals.append({
                "signal": "RETAIL_FOMO",
                "strength": (intel.google_trends_bitcoin - 70) / 30,
                "description": f"BTC Google Trends at {intel.google_trends_bitcoin} — retail FOMO, distribution risk",
                "direction": "SHORT",
                "confidence": 0.50,
            })

        return signals

    def _save_snapshot(self, intel: MarketIntelligence):
        """Save intelligence snapshot to disk."""
        outfile = CACHE_DIR / "latest_intel.json"
        with open(outfile, "w") as f:
            json.dump(asdict(intel), f, indent=2, default=str)
        logger.info(f"Saved snapshot to {outfile}")


# === CLI ===
def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Enhanced Market Data Feeds")
    parser.add_argument("--holders", action="store_true", help="Include token holder data (slower)")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    feeds = EnhancedDataFeeds()
    intel = feeds.fetch_all(include_holders=args.holders)

    if args.json:
        print(json.dumps(asdict(intel), indent=2, default=str))
    else:
        print(f"\n{'='*60}")
        print(f"  ENHANCED MARKET INTELLIGENCE")
        print(f"{'='*60}")
        print(f"  Timestamp:       {intel.timestamp}")
        print(f"  Fear & Greed:    {intel.fear_greed_index} ({intel.fear_greed_label})")
        print(f"  BTC Hashrate:    {intel.btc_hashrate_th:.1f} TH/s")
        print(f"  BTC Difficulty:  {intel.btc_difficulty:.2e}")
        print(f"  ETH Gas:         {intel.eth_gas_price_gwei:.1f} gwei")
        print(f"  BTC Funding:     {intel.funding_rate_btc:.4%}")
        print(f"  ETH Funding:     {intel.funding_rate_eth:.4%}")
        print(f"  BTC OI:          {intel.open_interest_btc_b:,.0f}")
        print(f"  BTC L/S Ratio:   {intel.long_short_ratio_btc:.2f}")
        print(f"  Google Trends:   BTC={intel.google_trends_bitcoin} ETH={intel.google_trends_ethereum}")
        print(f"  BTC Addresses:   {intel.btc_active_addresses_24h:,}")
        if intel.holder_data:
            print(f"\n  Token Holder Data:")
            for coin, hdata in intel.holder_data.items():
                cap = "CAPPED" if hdata["is_capped"] else "UNLIMITED"
                print(f"    {coin}: supply_ratio={hdata['supply_ratio']:.1%} ({cap})")
        print(f"\n  Signals Generated: {len(intel.signals)}")
        for s in intel.signals:
            print(f"    {s['direction']:5s} {s['signal']:30s} conf={s['confidence']:.0%} | {s['description']}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
