"""5-layer API failover for all data sources.

Layer 1: SHARED alpha_engine.crypto_data_failover module (Binance fapi/api/api1/api2/api3
         -> CoinGecko -> KuCoin -> CryptoCompare with circuit breakers)
Layer 2: Binance Global (api.binance.com) -- legacy direct call (only if shared module unavailable)
Layer 3: Binance US (api.binance.us)
Layer 4: CryptoCompare (min-api.cryptocompare.com)
Layer 5: CoinGecko (api.coingecko.com)
Layer 6: Local cache (data/price_cache.json)
"""
import json
import logging
import numpy as np
import pandas as pd
import requests
from pathlib import Path

# Wire in the shared multi-source failover (project rule: never single Binance)
try:
    from alpha_engine.failover_imports import (
        fetch_klines as _shared_fetch_klines,
        fetch_funding_rate as _shared_fetch_funding_rate,
        HAS_SHARED_FAILOVER as _HAS_SHARED_FAILOVER,
    )
except ImportError:
    _HAS_SHARED_FAILOVER = False
    _shared_fetch_klines = None  # type: ignore[assignment]
    _shared_fetch_funding_rate = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent / "data" / "price_cache.json"

# CoinGecko ID mapping for fallback
COINGECKO_IDS = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink", "LTCUSDT": "litecoin", "BCHUSDT": "bitcoin-cash",
    "TRXUSDT": "tron", "SHIBUSDT": "shiba-inu", "INJUSDT": "injective-protocol",
    "SUIUSDT": "sui", "ARBUSDT": "arbitrum", "OPUSDT": "optimism",
    "AAVEUSDT": "aave", "ETCUSDT": "ethereum-classic",
}


class DataFetcher:
    """Fetches OHLCV, funding rates, and sentiment with multi-source failover."""

    def __init__(self, timeout=10):
        self.timeout = timeout
        self._cache = self._load_cache()
        self.audit = []

    # ================================================================
    # OHLCV — 5-layer failover
    # ================================================================

    def fetch_ohlcv(self, symbol, interval="1h", limit=2000):
        """Fetch OHLCV candles with multi-source failover.

        Layer 0 is the shared alpha_engine.crypto_data_failover module which
        already implements Binance-mirrors -> CoinGecko -> KuCoin ->
        CryptoCompare with persistent circuit breakers. The legacy direct
        sources remain as a defensive backstop.
        """
        sources = []
        if _HAS_SHARED_FAILOVER:
            sources.append(("shared_failover", self._ohlcv_shared))
        sources.extend([
            ("binance", self._ohlcv_binance),
            ("binance_vision", self._ohlcv_binance_vision),
            ("binance_us", self._ohlcv_binance_us),
            ("cryptocompare", self._ohlcv_cryptocompare),
            ("coingecko", self._ohlcv_coingecko),
            ("cache", self._ohlcv_cache),
        ])
        for name, fn in sources:
            try:
                df = fn(symbol, interval, limit)
                if df is not None and len(df) > 50:
                    self.audit.append({
                        "source": name, "symbol": symbol,
                        "status": "OK", "rows": len(df),
                    })
                    self._update_cache(symbol, df)
                    return df
            except Exception as e:
                self.audit.append({
                    "source": name, "symbol": symbol,
                    "status": "FAIL", "error": str(e)[:120],
                })
                logger.warning(f"OHLCV {name} failed for {symbol}: {e}")
        logger.error(f"ALL OHLCV sources failed for {symbol}")
        return None

    def _ohlcv_shared(self, symbol, interval, limit):
        """Use the shared multi-source failover module (Binance -> CG -> KuCoin -> CC)."""
        if not _HAS_SHARED_FAILOVER:
            return None
        raw = _shared_fetch_klines(symbol, interval, limit)
        if not raw:
            return None
        # Pad rows to 12 cols (Binance shape) so _parse_binance_klines accepts them
        padded = []
        for row in raw:
            r = list(row)
            while len(r) < 12:
                r.append("0")
            padded.append(r)
        return self._parse_binance_klines(padded)

    def _ohlcv_binance(self, symbol, interval, limit):
        url = (f"https://api.binance.com/api/v3/klines"
               f"?symbol={symbol}&interval={interval}&limit={limit}")
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        return self._parse_binance_klines(r.json())

    def _ohlcv_binance_vision(self, symbol, interval, limit):
        url = (f"https://data-api.binance.vision/api/v3/klines"
               f"?symbol={symbol}&interval={interval}&limit={limit}")
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        return self._parse_binance_klines(r.json())

    def _ohlcv_binance_us(self, symbol, interval, limit):
        url = (f"https://api.binance.us/api/v3/klines"
               f"?symbol={symbol}&interval={interval}&limit={limit}")
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        return self._parse_binance_klines(r.json())

    def _ohlcv_cryptocompare(self, symbol, interval, limit):
        fsym = symbol.replace("USDT", "")
        url = (f"https://min-api.cryptocompare.com/data/v2/histohour"
               f"?fsym={fsym}&tsym=USDT&limit={min(limit, 2000)}")
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("Response") != "Success":
            return None
        rows = data["Data"]["Data"]
        df = pd.DataFrame(rows)
        df["ts"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("ts", inplace=True)
        df = df.rename(columns={"volumefrom": "vol"})
        return df[["open", "high", "low", "close", "vol"]].astype(float)

    def _ohlcv_coingecko(self, symbol, interval, limit):
        coin_id = COINGECKO_IDS.get(symbol)
        if not coin_id:
            return None
        url = (f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
               f"?vs_currency=usd&days=90")
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or len(data) < 10:
            return None
        df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        df["vol"] = 0.0  # CoinGecko OHLC doesn't include volume
        return df.astype(float)

    def _ohlcv_cache(self, symbol, interval, limit):
        if symbol in self._cache:
            df = pd.DataFrame(self._cache[symbol])
            df["ts"] = pd.to_datetime(df["ts"])
            df.set_index("ts", inplace=True)
            return df.tail(limit)
        return None

    @staticmethod
    def _parse_binance_klines(raw):
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=[
            "ts", "open", "high", "low", "close", "vol",
            "close_time", "quote_vol", "trades",
            "taker_base", "taker_quote", "ignore",
        ])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        return df[["open", "high", "low", "close", "vol"]].astype(float)

    # ================================================================
    # Funding Rate — 2-layer failover
    # ================================================================

    def fetch_funding(self, symbol):
        """Fetch latest funding rate. Returns float (PERCENTAGE, e.g. 0.01 = 0.01%).

        Failover chain (per project rule -- never single Binance):
          1. shared crypto_data_failover (Binance fapi mirrors -> Bybit -> OKX -> Coinglass)
          2. legacy direct Binance fapi (back-compat only)
          3. neutral 0.0
        """
        # 1. Shared multi-source failover (decimal -> percentage)
        if _HAS_SHARED_FAILOVER:
            try:
                rate_decimal = _shared_fetch_funding_rate(symbol)
                if rate_decimal is not None:
                    rate = float(rate_decimal) * 100
                    self.audit.append({
                        "source": "shared_failover", "symbol": symbol,
                        "type": "funding", "status": "OK", "value": rate,
                    })
                    return rate
            except Exception as e:
                self.audit.append({
                    "source": "shared_failover", "symbol": symbol,
                    "type": "funding", "status": "FAIL", "error": str(e)[:80],
                })

        # 2. Legacy direct Binance fapi (kept for back-compat; usually geo-blocked on GHA)
        try:
            url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if data:
                rate = float(data[0]["fundingRate"]) * 100
                self.audit.append({
                    "source": "binance_fapi", "symbol": symbol,
                    "type": "funding", "status": "OK", "value": rate,
                })
                return rate
        except Exception as e:
            self.audit.append({
                "source": "binance_fapi", "symbol": symbol,
                "type": "funding", "status": "FAIL", "error": str(e)[:80],
            })
        return 0.0

    # ================================================================
    # Sentiment — 2-layer failover each
    # ================================================================

    def fetch_fear_greed(self):
        """Fear & Greed Index (0-100). Failover: alternative.me → 50 (neutral)."""
        try:
            r = requests.get(
                "https://api.alternative.me/fng/?limit=1&format=json",
                timeout=self.timeout,
            )
            r.raise_for_status()
            val = int(r.json()["data"][0]["value"])
            self.audit.append({"source": "alternative.me", "type": "fng", "status": "OK", "value": val})
            return val
        except Exception as e:
            self.audit.append({"source": "alternative.me", "type": "fng", "status": "FAIL", "error": str(e)[:80]})
            return 50

    def fetch_btc_dominance(self):
        """BTC market cap dominance (%). Failover: CoinGecko → 0.0."""
        try:
            r = requests.get("https://api.coingecko.com/api/v3/global", timeout=self.timeout)
            r.raise_for_status()
            val = float(r.json()["data"]["market_cap_percentage"]["btc"])
            self.audit.append({"source": "coingecko", "type": "btc_dom", "status": "OK", "value": round(val, 2)})
            return val
        except Exception as e:
            self.audit.append({"source": "coingecko", "type": "btc_dom", "status": "FAIL", "error": str(e)[:80]})
            return 0.0

    # ================================================================
    # Current prices — for performance tracking
    # ================================================================

    def fetch_current_prices(self, symbols):
        """Fetch current prices for multiple symbols. Returns {symbol: price}."""
        prices = {}
        # Layer 1: Binance batch ticker
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=self.timeout)
            r.raise_for_status()
            for item in r.json():
                if item["symbol"] in symbols:
                    prices[item["symbol"]] = float(item["price"])
            if len(prices) == len(symbols):
                return prices
        except Exception:
            pass
        # Layer 2: Binance Vision (unrestricted public data API)
        try:
            r = requests.get("https://data-api.binance.vision/api/v3/ticker/price", timeout=self.timeout)
            r.raise_for_status()
            for item in r.json():
                if item["symbol"] in symbols and item["symbol"] not in prices:
                    prices[item["symbol"]] = float(item["price"])
            if len(prices) == len(symbols):
                return prices
        except Exception:
            pass
        # Layer 3: Binance US batch
        try:
            r = requests.get("https://api.binance.us/api/v3/ticker/price", timeout=self.timeout)
            r.raise_for_status()
            for item in r.json():
                if item["symbol"] in symbols and item["symbol"] not in prices:
                    prices[item["symbol"]] = float(item["price"])
        except Exception:
            pass
        # Layer 4: CoinLore individual
        for sym in symbols:
            if sym in prices:
                continue
            try:
                fsym = sym.replace("USDT", "").lower()
                r = requests.get(f"https://api.coinlore.net/api/ticker/?id={fsym}", timeout=5)
                data = r.json()
                if data:
                    prices[sym] = float(data[0]["price_usd"])
            except Exception:
                pass
        return prices

    # ================================================================
    # Cache management
    # ================================================================

    def _load_cache(self):
        try:
            if CACHE_FILE.exists():
                return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
        return {}

    def _update_cache(self, symbol, df):
        tail = df.tail(200).reset_index()
        tail["ts"] = tail["ts"].astype(str)
        self._cache[symbol] = tail.to_dict(orient="records")

    def save_cache(self):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(self._cache, default=str))
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
