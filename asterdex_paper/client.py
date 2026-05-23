"""
AsterDEX API Client — Binance-compatible HMAC SHA256 authentication
===================================================================
Perpetual futures DEX API at https://fapi.asterdex.com
Supports: market data, order placement, account info, position management.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def _load_env():
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("ASTERDEX_API_KEY", "")
API_SECRET = os.environ.get("ASTERDEX_API_SECRET", "")
BASE_URL = os.environ.get("ASTERDEX_BASE_URL", "https://fapi.asterdex.com")
PAPER_MODE = os.environ.get("ASTERDEX_PAPER_MODE", "true").lower() == "true"


class AsterDEXClient:
    """Binance-compatible futures API client for AsterDEX."""

    def __init__(self, api_key: str = "", api_secret: str = "", base_url: str = ""):
        self.api_key = api_key or API_KEY
        self.api_secret = api_secret or API_SECRET
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        self.recv_window = 5000

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------
    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        query = urlencode(sorted(params.items()))
        sig = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = sig
        return params

    def _request(self, method: str, path: str, params: dict | None = None,
                 signed: bool = False) -> dict:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        if signed:
            params = self._sign(params)
        url = f"{self.base_url}{path}"
        try:
            # POST/DELETE use data= body; GET uses params= query string
            if method in ("POST", "DELETE"):
                resp = self.session.request(method, url, data=params, timeout=15)
            else:
                resp = self.session.request(method, url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # AsterDEX error convention: negative code = error
            if isinstance(data, dict) and data.get("code", 0) < 0:
                return {"error": data.get("msg", "Unknown"), "code": data["code"]}
            return data
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, "status_code", None)}

    # ------------------------------------------------------------------
    # Public Market Data
    # ------------------------------------------------------------------
    def ping(self) -> dict:
        return self._request("GET", "/fapi/v1/ping")

    def server_time(self) -> dict:
        return self._request("GET", "/fapi/v1/time")

    def exchange_info(self) -> dict:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_price(self, symbol: str) -> float | None:
        data = self._request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})
        if "price" in data:
            return float(data["price"])
        return None

    def get_all_prices(self) -> dict[str, float]:
        data = self._request("GET", "/fapi/v1/ticker/price")
        if isinstance(data, list):
            return {d["symbol"]: float(d["price"]) for d in data}
        return {}

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> list:
        return self._request("GET", "/fapi/v1/klines", {
            "symbol": symbol, "interval": interval, "limit": limit
        })

    def get_depth(self, symbol: str, limit: int = 20) -> dict:
        return self._request("GET", "/fapi/v1/depth", {
            "symbol": symbol, "limit": limit
        })

    def get_funding_rate(self, symbol: str) -> dict:
        return self._request("GET", "/fapi/v1/premiumIndex", {"symbol": symbol})

    def get_24hr_ticker(self, symbol: str) -> dict:
        return self._request("GET", "/fapi/v1/ticker/24hr", {"symbol": symbol})

    # ------------------------------------------------------------------
    # Account & Positions (signed)
    # ------------------------------------------------------------------
    def get_account(self) -> dict:
        return self._request("GET", "/fapi/v4/account", signed=True)

    def get_balance(self) -> dict:
        return self._request("GET", "/fapi/v2/balance", signed=True)

    def get_positions(self) -> dict:
        return self._request("GET", "/fapi/v2/positionRisk", signed=True)

    def get_open_orders(self, symbol: str = "") -> dict:
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params, signed=True)

    # ------------------------------------------------------------------
    # Order Placement (signed)
    # ------------------------------------------------------------------
    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: float, price: float | None = None,
                    stop_price: float | None = None,
                    time_in_force: str = "GTC",
                    reduce_only: bool = False) -> dict:
        params = {
            "symbol": symbol,
            "side": side,           # BUY or SELL
            "type": order_type,     # MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET
            "quantity": f"{quantity:.8f}".rstrip("0").rstrip("."),
        }
        if order_type == "LIMIT" and price is not None:
            params["price"] = f"{price:.8f}".rstrip("0").rstrip(".")
            params["timeInForce"] = time_in_force
        if stop_price is not None:
            params["stopPrice"] = f"{stop_price:.8f}".rstrip("0").rstrip(".")
        if reduce_only:
            params["reduceOnly"] = "true"
        return self._request("POST", "/fapi/v1/order", params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        return self._request("DELETE", "/fapi/v1/order", {
            "symbol": symbol, "orderId": order_id
        }, signed=True)

    def cancel_all_orders(self, symbol: str) -> dict:
        return self._request("DELETE", "/fapi/v1/allOpenOrders", {
            "symbol": symbol
        }, signed=True)

    def place_order_with_tp_sl(self, symbol: str, side: str, quantity: float,
                                take_profit: float, stop_loss: float) -> list[dict]:
        """Place market entry + TP + SL as batch orders (from RobotTraders pattern)."""
        import json as _json
        close_side = "SELL" if side == "BUY" else "BUY"
        orders = [
            {"symbol": symbol, "side": side, "type": "MARKET",
             "quantity": str(quantity)},
            {"symbol": symbol, "side": close_side, "type": "TAKE_PROFIT_MARKET",
             "stopPrice": str(take_profit), "closePosition": "true"},
            {"symbol": symbol, "side": close_side, "type": "STOP_MARKET",
             "stopPrice": str(stop_loss), "closePosition": "true"},
        ]
        params = {"batchOrders": _json.dumps(orders)}
        return self._request("POST", "/fapi/v1/batchOrders", params, signed=True)

    # ------------------------------------------------------------------
    # Leverage & Margin
    # ------------------------------------------------------------------
    def set_leverage(self, symbol: str, leverage: int) -> dict:
        return self._request("POST", "/fapi/v1/leverage", {
            "symbol": symbol, "leverage": leverage
        }, signed=True)

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> dict:
        return self._request("POST", "/fapi/v1/marginType", {
            "symbol": symbol, "marginType": margin_type
        }, signed=True)


# ---------------------------------------------------------------------------
# Symbol mapping: our strategy symbols → AsterDEX perpetual symbols
# ---------------------------------------------------------------------------
SYMBOL_MAP = {
    # Crypto majors
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT", "XRP-USD": "XRPUSDT", "ADA-USD": "ADAUSDT",
    "AVAX-USD": "AVAXUSDT", "LINK-USD": "LINKUSDT", "DOT-USD": "DOTUSDT",
    "NEAR-USD": "NEARUSDT",
    # Alts
    "SUI20947-USD": "SUIUSDT", "TIA-USD": "TIAUSDT", "INJ-USD": "INJUSDT",
    "ATOM-USD": "ATOMUSDT", "FIL-USD": "FILUSDT",
    # Memes
    "DOGE-USD": "DOGEUSDT", "SHIB-USD": "SHIBUSDT",
    "PEPE24478-USD": "1000PEPEUSDT", "WIF-USD": "WIFUSDT",
    "BONK-USD": "1000BONKUSDT", "FLOKI-USD": "1000FLOKIUSDT",
    # KIMI format (already USDT)
    "BTCUSDT": "BTCUSDT", "ETHUSDT": "ETHUSDT", "SOLUSDT": "SOLUSDT",
    "BNBUSDT": "BNBUSDT", "XRPUSDT": "XRPUSDT", "ADAUSDT": "ADAUSDT",
    "DOGEUSDT": "DOGEUSDT", "AVAXUSDT": "AVAXUSDT", "LINKUSDT": "LINKUSDT",
    "DOTUSDT": "DOTUSDT", "NEARUSDT": "NEARUSDT", "SUIUSDT": "SUIUSDT",
    "TIAUSDT": "TIAUSDT", "INJUSDT": "INJUSDT", "ATOMUSDT": "ATOMUSDT",
    "FILUSDT": "FILUSDT", "SHIBUSDT": "1000SHIBUSDT",
    "1000PEPEUSDT": "1000PEPEUSDT", "1000BONKUSDT": "1000BONKUSDT",
    "1000FLOKIUSDT": "1000FLOKIUSDT", "1000SHIBUSDT": "1000SHIBUSDT",
    "WIFUSDT": "WIFUSDT",
    "SPXUSDT": "SPXUSDT", "QQQUSDT": "QQQUSDT", "XAUUSDT": "XAUUSDT",
    # Tokenized stocks on AsterDEX (our RSI-2 proven edge)
    "SPY": "SPXUSDT", "QQQ": "QQQUSDT",   # RSI-2: 75.7% / 75.3% WR
    "AAPL": "AAPLUSDT", "TSLA": "TSLAUSDT", "NVDA": "NVDAUSDT",
    "AMZN": "AMZNUSDT", "META": "METAUSDT", "MSFT": "MSFTUSDT",
    "GOOGL": "GOOGUSDT", "INTC": "INTCUSDT",
    # Tokenized commodities on AsterDEX
    "GC=F": "XAUUSDT", "SI=F": "XAGUSDT",  # Gold, Silver
    "GLD": "XAUUSDT",                       # Gold ETF → Gold perp
}


def map_symbol(strategy_symbol: str) -> str | None:
    """Convert strategy symbol to AsterDEX perpetual symbol."""
    # Direct lookup
    if strategy_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[strategy_symbol]
    # Already ends with USDT
    if strategy_symbol.endswith("USDT"):
        return strategy_symbol
    # Try stripping -USD suffix
    base = strategy_symbol.replace("-USD", "").replace("=X", "")
    candidate = f"{base}USDT"
    return candidate
