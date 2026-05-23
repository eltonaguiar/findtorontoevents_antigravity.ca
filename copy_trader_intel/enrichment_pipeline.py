#!/usr/bin/env python3
"""
Copy Trader Signal Enrichment Pipeline
=======================================
Attaches market context to each pick at generation time:
- Funding rates (Binance/OKX/Bybit - free, no auth)
- Open Interest changes (Binance - free, no auth)
- Fear & Greed Index (Alternative.me - free, no auth)
- Deribit DVOL + put/call ratio (Deribit - free, no auth)
- DEX flow signals (DexScreener/GeckoTerminal - free, no auth)
- Long/Short ratios (Binance/OKX - free, no auth)

All P0 signals are 100% free with zero auth required.
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "enrichment_cache"
CACHE_DIR.mkdir(exist_ok=True)

# TTL cache
_cache: Dict[str, tuple] = {}


def _cached_fetch(key: str, ttl_seconds: int, fetch_fn):
    """Fetch with TTL caching."""
    now = datetime.now(timezone.utc)
    if key in _cache:
        data, expires = _cache[key]
        if now < expires:
            return data
    try:
        result = fetch_fn()
        _cache[key] = (result, now + timedelta(seconds=ttl_seconds))
        return result
    except Exception:
        return _cache.get(key, (None, now))[0]


def _safe_get(url, params=None, headers=None, timeout=8):
    """Safe HTTP GET with error swallowing."""
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _safe_get_with_failover(urls: list, params=None, headers=None, timeout=8):
    """Try multiple URLs in order, return first successful JSON response."""
    for url in urls:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return None


# ======================================================================
# Signal 1: Aggregate Funding Rate (P0 - FREE)
# ======================================================================

def fetch_funding(symbol: str) -> dict:
    """Fetch funding rates from Binance, OKX, Bybit simultaneously."""
    binance_sym = symbol.replace("-", "").replace("/", "")
    # Build OKX instId: BTC-USDT-SWAP
    base = binance_sym.replace("USDT", "").replace("USD", "")
    okx_sym = f"{base}-USDT-SWAP"

    rates = {}

    # Binance
    data = _safe_get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={binance_sym}&limit=1")
    if data and isinstance(data, list) and data:
        try:
            rates['binance'] = float(data[0]['fundingRate'])
        except (KeyError, ValueError, IndexError):
            pass

    # Binance mirror fallback
    if 'binance' not in rates:
        data = _safe_get(f"https://fapi.binance.us/fapi/v1/fundingRate?symbol={binance_sym}&limit=1")
        if data and isinstance(data, list) and data:
            try:
                rates['binance'] = float(data[0]['fundingRate'])
            except (KeyError, ValueError, IndexError):
                pass

    # OKX
    data = _safe_get(f"https://www.okx.com/api/v5/public/funding-rate?instId={okx_sym}")
    if data and data.get('data'):
        try:
            rates['okx'] = float(data['data'][0]['fundingRate'])
        except (KeyError, ValueError, IndexError):
            pass

    # Bybit
    data = _safe_get(f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={binance_sym}&limit=1")
    if data and data.get('result', {}).get('list'):
        try:
            rates['bybit'] = float(data['result']['list'][0]['fundingRate'])
        except (KeyError, ValueError, IndexError):
            pass

    valid = [v for v in rates.values() if v is not None]
    avg = sum(valid) / len(valid) if valid else None

    signal = None
    direction = "NEUTRAL"
    if avg is not None:
        if avg > 0.0005:
            signal = "EXTREME_POSITIVE"
            direction = "BEARISH_CONTRARIAN"
        elif avg > 0.0002:
            signal = "POSITIVE"
            direction = "BEARISH_CONTRARIAN"
        elif avg < -0.0003:
            signal = "EXTREME_NEGATIVE"
            direction = "BULLISH_CONTRARIAN"
        elif avg < -0.0001:
            signal = "NEGATIVE"
            direction = "BULLISH_CONTRARIAN"
        else:
            signal = "NEUTRAL"

    return {
        **rates,
        "avg_funding_8h": round(avg, 6) if avg else None,
        "funding_annualized_pct": round(avg * 3 * 365 * 100, 1) if avg else None,
        "funding_signal": signal,
        "funding_signal_direction": direction,
    }


# ======================================================================
# Signal 2: Open Interest Change (P0 - FREE)
# ======================================================================

def fetch_oi_change(symbol: str) -> dict:
    """Fetch OI 24h change from Binance public API."""
    binance_sym = symbol.replace("-", "").replace("/", "")

    data = _safe_get(
        f"https://fapi.binance.com/futures/data/openInterestHist?symbol={binance_sym}&period=1h&limit=25"
    )
    if not data or not isinstance(data, list) or len(data) < 2:
        return {}

    try:
        current_oi = float(data[-1]['sumOpenInterestValue'])
        oi_24h_ago = float(data[0]['sumOpenInterestValue'])
        change_pct = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago > 0 else 0

        signal = "SURGING" if change_pct > 15 else \
                 "RISING" if change_pct > 5 else \
                 "DECLINING" if change_pct < -5 else \
                 "CRASHING" if change_pct < -15 else "STABLE"

        return {
            "total_oi_usd": round(current_oi),
            "change_24h_pct": round(change_pct, 1),
            "oi_signal": signal,
            "oi_direction_bias": "BEARISH" if change_pct > 15 else
                                 "BULLISH" if change_pct < -10 else "NEUTRAL",
        }
    except (KeyError, ValueError, IndexError):
        return {}


# ======================================================================
# Signal 3: Fear & Greed Index (P0 - FREE)
# ======================================================================

def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed Index from Alternative.me (free, no auth)."""
    data = _safe_get("https://api.alternative.me/fng/?limit=1&date_format=iso")
    if not data or not data.get('data'):
        return {}

    try:
        item = data['data'][0]
        val = int(item['value'])
        label = item.get('value_classification', '')

        signal = "CONTRARIAN_BULLISH" if val < 20 else \
                 "BULLISH_ZONE" if val < 35 else \
                 "CONTRARIAN_BEARISH" if val > 80 else \
                 "BEARISH_ZONE" if val > 65 else "NEUTRAL"

        return {
            "fear_greed_index": val,
            "fear_greed_label": label,
            "fear_greed_signal": signal,
        }
    except (KeyError, ValueError, IndexError):
        return {}


# ======================================================================
# Signal 4: Deribit DVOL + Options (P0 - FREE, no auth)
# ======================================================================

def fetch_derivatives(symbol: str) -> dict:
    """Fetch DVOL and put/call ratio from Deribit (free, no auth)."""
    currency = None
    if "BTC" in symbol:
        currency = "BTC"
    elif "ETH" in symbol:
        currency = "ETH"
    else:
        return {}

    result = {}
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    day_ago_ms = now_ms - 86_400_000

    # DVOL
    dvol_data = _safe_get(
        "https://www.deribit.com/api/v2/public/get_volatility_index_data",
        params={
            "currency": currency,
            "start_timestamp": day_ago_ms,
            "end_timestamp": now_ms,
            "resolution": 3600,
        }
    )
    if dvol_data and dvol_data.get('result', {}).get('data'):
        try:
            candles = dvol_data['result']['data']
            current_dvol = candles[-1][4]  # close
            recent = candles[-min(7, len(candles)):]
            week_avg = sum(c[4] for c in recent) / len(recent)
            result['dvol'] = round(current_dvol, 1)
            result['dvol_7d_avg'] = round(week_avg, 1)
            result['dvol_elevation_pct'] = round((current_dvol - week_avg) / week_avg * 100, 1) if week_avg > 0 else 0
            result['dvol_signal'] = (
                "ELEVATED" if current_dvol > week_avg * 1.2 else
                "SUPPRESSED" if current_dvol < week_avg * 0.85 else "NORMAL"
            )
        except (KeyError, ValueError, IndexError):
            pass

    # Put/Call ratio
    opts_data = _safe_get(
        "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
        params={"currency": currency, "kind": "option"}
    )
    if opts_data and opts_data.get('result'):
        try:
            summaries = opts_data['result']
            put_oi = sum(s.get('open_interest', 0) for s in summaries
                        if s.get('instrument_name', '').endswith('P'))
            call_oi = sum(s.get('open_interest', 0) for s in summaries
                         if s.get('instrument_name', '').endswith('C'))
            if call_oi > 0:
                ratio = put_oi / call_oi
                result['put_call_oi_ratio'] = round(ratio, 3)
                result['options_bias'] = (
                    "BEARISH_HEDGE" if ratio > 1.15 else
                    "BULLISH_DEMAND" if ratio < 0.85 else "BALANCED"
                )
        except (KeyError, ValueError):
            pass

    return result


# ======================================================================
# Signal 5: Long/Short Ratio (P0 - FREE)
# ======================================================================

def fetch_long_short_ratio(symbol: str) -> dict:
    """Fetch top trader L/S ratio from Binance and OKX."""
    binance_sym = symbol.replace("-", "").replace("/", "")

    result = {}

    # Binance top trader L/S ratio
    data = _safe_get(
        f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={binance_sym}&period=1h&limit=1"
    )
    if data and isinstance(data, list) and data:
        try:
            ratio = float(data[0]['longShortRatio'])
            result['ls_ratio_binance'] = round(ratio, 3)
        except (KeyError, ValueError):
            pass

    # OKX L/S ratio
    base = binance_sym.replace("USDT", "").replace("USD", "")
    data = _safe_get(
        f"https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio-contract?ccy={base}&period=1H"
    )
    if data and data.get('data'):
        try:
            ratio = float(data['data'][0][1])  # [timestamp, ratio]
            result['ls_ratio_okx'] = round(ratio, 3)
        except (KeyError, ValueError, IndexError):
            pass

    # Derive crowd bias
    ratios = [v for k, v in result.items() if k.startswith('ls_ratio')]
    if ratios:
        avg = sum(ratios) / len(ratios)
        result['crowd_bias'] = (
            "OVERLONG" if avg > 1.3 else
            "OVERSHORT" if avg < 0.7 else "BALANCED"
        )

    return result


# ======================================================================
# Signal 6: DEX Flow (P1 - FREE, no auth)
# ======================================================================

def fetch_dex_flow(symbol: str) -> dict:
    """Fetch DEX buy/sell pressure from DexScreener (free, no auth)."""
    TOKEN_MAP = {
        "BTCUSDT": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",  # WBTC
        "ETHUSDT": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
        "SOLUSDT": "So11111111111111111111111111111111111111112",    # SOL (Solana native)
    }
    token = TOKEN_MAP.get(symbol)
    if not token:
        return {}

    data = _safe_get(f"https://api.dexscreener.com/latest/dex/tokens/{token}")
    if not data or not data.get('pairs'):
        return {}

    try:
        pairs = sorted(data['pairs'],
                       key=lambda p: p.get('liquidity', {}).get('usd', 0),
                       reverse=True)
        top = pairs[0]
        buys_1h = top.get('txns', {}).get('h1', {}).get('buys', 0)
        sells_1h = top.get('txns', {}).get('h1', {}).get('sells', 0)
        total = buys_1h + sells_1h
        ratio = buys_1h / total if total > 0 else 0.5

        signal = (
            "AGGRESSIVE_BUY" if ratio > 0.65 else
            "NET_BUY" if ratio > 0.55 else
            "AGGRESSIVE_SELL" if ratio < 0.35 else
            "NET_SELL" if ratio < 0.45 else "NEUTRAL"
        )

        return {
            "dex_txn_buy_ratio_1h": round(ratio, 3),
            "dex_volume_1h_usd": top.get('volume', {}).get('h1'),
            "dex_price_change_1h_pct": top.get('priceChange', {}).get('h1'),
            "dex_flow_signal": signal,
        }
    except (KeyError, ValueError, IndexError):
        return {}


# ======================================================================
# Signal 7: Binance Premium Index / Funding (P0 - FREE, failover chain)
# ======================================================================

def fetch_binance_premium_index(symbol: str) -> dict:
    """
    Fetch funding rate from Binance premiumIndex endpoint with 3+ failover.
    Per project API Failover Rule: never use single Binance API.
    """
    binance_sym = symbol.replace("-", "").replace("/", "")
    urls = [
        f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={binance_sym}",
        f"https://fapi1.binance.com/fapi/v1/premiumIndex?symbol={binance_sym}",
        f"https://fapi2.binance.com/fapi/v1/premiumIndex?symbol={binance_sym}",
        f"https://fapi3.binance.com/fapi/v1/premiumIndex?symbol={binance_sym}",
    ]
    data = _safe_get_with_failover(urls)
    if not data:
        return {}

    try:
        result = {
            "mark_price": float(data.get("markPrice", 0)),
            "index_price": float(data.get("indexPrice", 0)),
            "last_funding_rate": float(data.get("lastFundingRate", 0)),
            "next_funding_time": data.get("nextFundingTime"),
            "interest_rate": float(data.get("interestRate", 0)),
        }
        return result
    except (KeyError, ValueError, TypeError):
        return {}


# ======================================================================
# Signal 8: 24h Volume & Price Change (P0 - FREE, failover chain)
# ======================================================================

def fetch_binance_ticker_24h(symbol: str) -> dict:
    """
    Fetch 24h volume and price change from Binance with 3+ failover.
    Per project API Failover Rule: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare.
    """
    binance_sym = symbol.replace("-", "").replace("/", "")

    # Failover chain: 3 Binance mirrors
    urls = [
        f"https://api1.binance.com/api/v3/ticker/24hr?symbol={binance_sym}",
        f"https://api2.binance.com/api/v3/ticker/24hr?symbol={binance_sym}",
        f"https://api3.binance.com/api/v3/ticker/24hr?symbol={binance_sym}",
        f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_sym}",
    ]
    data = _safe_get_with_failover(urls)

    # CoinGecko fallback
    if not data:
        cg_id_map = {
            "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
            "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
            "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
            "MATICUSDT": "matic-network", "LINKUSDT": "chainlink",
        }
        cg_id = cg_id_map.get(binance_sym)
        if cg_id:
            cg_data = _safe_get(f"https://api.coingecko.com/api/v3/coins/{cg_id}")
            if cg_data and cg_data.get("market_data"):
                md = cg_data["market_data"]
                return {
                    "volume_24h_usd": md.get("total_volume", {}).get("usd"),
                    "price_change_24h_pct": md.get("price_change_percentage_24h"),
                    "volume_24h_change_pct": None,  # CoinGecko doesn't provide this directly
                    "current_price": md.get("current_price", {}).get("usd"),
                    "source": "coingecko_fallback",
                }

    # KuCoin fallback
    if not data:
        kucoin_sym = f"{binance_sym[:len(binance_sym)-4]}-USDT"
        kc_data = _safe_get(f"https://api.kucoin.com/api/v1/market/stats?symbol={kucoin_sym}")
        if kc_data and kc_data.get("data"):
            kd = kc_data["data"]
            try:
                return {
                    "volume_24h_usd": float(kd.get("volValue", 0)),
                    "price_change_24h_pct": float(kd.get("changeRate", 0)) * 100,
                    "volume_24h_change_pct": None,
                    "current_price": float(kd.get("last", 0)),
                    "source": "kucoin_fallback",
                }
            except (ValueError, TypeError):
                pass

    if not data:
        return {}

    try:
        volume_24h = float(data.get("quoteVolume", 0))
        price_change_pct = float(data.get("priceChangePercent", 0))
        # Volume change: compare current volume to previous 24h (not available directly,
        # but we can use the volume to assess activity level)
        return {
            "volume_24h_usd": round(volume_24h, 2),
            "price_change_24h_pct": round(price_change_pct, 2),
            "volume_24h_change_pct": None,  # Not directly available from single 24h endpoint
            "high_24h": float(data.get("highPrice", 0)),
            "low_24h": float(data.get("lowPrice", 0)),
            "current_price": float(data.get("lastPrice", 0)),
            "weighted_avg_price": float(data.get("weightedAvgPrice", 0)),
            "trades_count_24h": int(data.get("count", 0)),
            "source": "binance",
        }
    except (KeyError, ValueError, TypeError):
        return {}


# ======================================================================
# Signal 9: RSI from Last 50 1h Candles (P0 - FREE, failover chain)
# ======================================================================

def compute_rsi(closes: list, period: int = 14) -> float:
    """Compute RSI from a list of close prices."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    # Initial averages (SMA for first N periods)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # EMA-style smoothing for remaining periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def fetch_rsi(symbol: str, period: int = 14) -> dict:
    """
    Fetch last 50 1h candles from Binance (with failover) and compute RSI.
    Per project API Failover Rule: 3+ Binance mirrors.
    """
    binance_sym = symbol.replace("-", "").replace("/", "")

    # Failover chain: Binance futures klines -> spot klines -> KuCoin
    urls = [
        f"https://fapi.binance.com/fapi/v1/klines?symbol={binance_sym}&interval=1h&limit=50",
        f"https://fapi1.binance.com/fapi/v1/klines?symbol={binance_sym}&interval=1h&limit=50",
        f"https://api1.binance.com/api/v3/klines?symbol={binance_sym}&interval=1h&limit=50",
        f"https://api2.binance.com/api/v3/klines?symbol={binance_sym}&interval=1h&limit=50",
    ]
    data = _safe_get_with_failover(urls)

    # KuCoin fallback
    if not data:
        kucoin_sym = f"{binance_sym[:len(binance_sym)-4]}-USDT"
        kc_data = _safe_get(
            f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={kucoin_sym}"
        )
        if kc_data and kc_data.get("data"):
            try:
                # KuCoin returns newest first; close is at index 2
                candles = sorted(kc_data["data"], key=lambda c: int(c[0]))
                closes = [float(c[2]) for c in candles[-50:]]
                rsi = compute_rsi(closes, period)
                if rsi is not None:
                    return {
                        "rsi_14_1h": rsi,
                        "rsi_signal": _rsi_signal(rsi),
                        "source": "kucoin_fallback",
                    }
            except (ValueError, TypeError, IndexError):
                pass

    # CryptoCompare fallback
    if not data:
        base = binance_sym.replace("USDT", "").replace("USD", "")
        cc_data = _safe_get(
            f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={base}&tsym=USD&limit=50"
        )
        if cc_data and cc_data.get("Data", {}).get("Data"):
            try:
                closes = [float(c["close"]) for c in cc_data["Data"]["Data"]]
                rsi = compute_rsi(closes, period)
                if rsi is not None:
                    return {
                        "rsi_14_1h": rsi,
                        "rsi_signal": _rsi_signal(rsi),
                        "source": "cryptocompare_fallback",
                    }
            except (ValueError, TypeError, IndexError):
                pass

    if not data or not isinstance(data, list):
        return {}

    try:
        # Binance klines: [openTime, open, high, low, close, volume, ...]
        closes = [float(c[4]) for c in data]
        rsi = compute_rsi(closes, period)
        if rsi is None:
            return {}
        return {
            "rsi_14_1h": rsi,
            "rsi_signal": _rsi_signal(rsi),
            "source": "binance",
        }
    except (KeyError, ValueError, TypeError, IndexError):
        return {}


def _rsi_signal(rsi: float) -> str:
    """Classify RSI into signal categories."""
    if rsi >= 80:
        return "EXTREME_OVERBOUGHT"
    elif rsi >= 70:
        return "OVERBOUGHT"
    elif rsi <= 20:
        return "EXTREME_OVERSOLD"
    elif rsi <= 30:
        return "OVERSOLD"
    elif 45 <= rsi <= 55:
        return "NEUTRAL"
    elif rsi > 55:
        return "BULLISH_MOMENTUM"
    else:
        return "BEARISH_MOMENTUM"


# ======================================================================
# Signal 10: BTC Mempool Network Demand (P0 - FREE, no auth)
# ======================================================================

def fetch_mempool_btc() -> dict:
    """
    Fetch Bitcoin mempool fee rates + backlog from mempool.space (free, no auth).
    Fee rate spikes historically precede BTC price rallies by 3-14 days,
    reflecting genuine on-chain demand rather than speculative paper trading.
    """
    result = {}

    # Recommended fee rates (sat/vB)
    fees = _safe_get("https://mempool.space/api/v1/fees/recommended", timeout=8)
    if fees:
        try:
            fastest = int(fees.get("fastestFee", 0))
            economy = int(fees.get("economyFee", 0))
            result["btc_fee_fastest_sat_vb"] = fastest
            result["btc_fee_economy_sat_vb"] = economy
            result["btc_network_congestion"] = (
                "EXTREME" if fastest >= 100 else
                "HIGH"    if fastest >= 40  else
                "NORMAL"  if fastest >= 15  else
                "LOW"
            )
            result["btc_demand_signal"] = (
                "BULLISH_DEMAND" if fastest >= 40 else
                "RISING_DEMAND"  if fastest >= 15 else
                "LOW_DEMAND"
            )
        except (KeyError, ValueError, TypeError):
            pass

    # Mempool backlog size
    mempool_data = _safe_get("https://mempool.space/api/mempool", timeout=8)
    if mempool_data:
        try:
            vsize_mb = round(int(mempool_data.get("vsize", 0)) / 1_000_000, 2)
            result["btc_mempool_tx_count"] = int(mempool_data.get("count", 0))
            result["btc_mempool_vsize_mb"] = vsize_mb
            result["btc_mempool_backlog"] = (
                "EXTREME" if vsize_mb > 100 else
                "HIGH"    if vsize_mb > 50  else
                "NORMAL"  if vsize_mb > 5   else
                "EMPTY"
            )
        except (KeyError, ValueError, TypeError):
            pass

    return result


# ======================================================================
# Signal 11: 0x DEX Liquidity Depth (P1 - FREE, no auth)
# ======================================================================

_0X_TOKEN_MAP = {
    "BTCUSDT":  {"sell": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "amt": "100000000"},
    "ETHUSDT":  {"sell": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", "amt": "10000000000000000000"},
    "LINKUSDT": {"sell": "0x514910771AF9Ca656af840dff83E8264EcF986CA", "amt": "1000000000000000000000"},
    "BNBUSDT":  {"sell": "0xB8c77482e45F1F44dE1745F52C74426C631bDD52", "amt": "10000000000000000000"},
}
_0X_USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def fetch_0x_liquidity(symbol: str) -> dict:
    """
    Test DEX liquidity depth via 0x swap API (free, no auth).
    High price impact = liquidity thinning = smart money exiting.
    Covers Uniswap, Curve, Balancer, and 30+ Ethereum DEX sources.
    """
    token_info = _0X_TOKEN_MAP.get(symbol)
    if not token_info:
        return {}

    # Try v1 API then permit2 v2
    data = (
        _safe_get(
            "https://api.0x.org/swap/v1/price",
            params={"sellToken": token_info["sell"], "buyToken": _0X_USDC, "sellAmount": token_info["amt"]},
            headers={"0x-api-version": "1"},
            timeout=10,
        ) or
        _safe_get(
            "https://api.0x.org/swap/permit2/price",
            params={"chainId": "1", "sellToken": token_info["sell"], "buyToken": _0X_USDC, "sellAmount": token_info["amt"]},
            timeout=10,
        )
    )
    if not data:
        return {}

    try:
        price_impact = float(data.get("estimatedPriceImpact") or data.get("priceImpact") or 0)
        return {
            "dex_price_impact_pct": round(price_impact, 4),
            "dex_source_count": len(data.get("sources", [])),
            "dex_liquidity_grade": (
                "DEEP"      if price_impact < 0.1 else
                "NORMAL"    if price_impact < 0.5 else
                "THIN"      if price_impact < 1.5 else
                "VERY_THIN"
            ),
            "dex_liquidity_signal": (
                "HEALTHY_LIQUIDITY"  if price_impact < 0.1 else
                "NORMAL_LIQUIDITY"   if price_impact < 0.5 else
                "THINNING_LIQUIDITY" if price_impact < 1.5 else
                "ILLIQUID_WARNING"
            ),
        }
    except (KeyError, ValueError, TypeError):
        return {}


# ======================================================================
# Signal 12: 1inch DEX/CEX Price Spread (P1 - FREE, no auth)
# ======================================================================

_1INCH_TOKEN_MAP = {
    "BTCUSDT":  {"src": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "decimals": 8,  "amount": "100000000"},
    "ETHUSDT":  {"src": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", "decimals": 18, "amount": "1000000000000000000"},
    "LINKUSDT": {"src": "0x514910771AF9Ca656af840dff83E8264EcF986CA", "decimals": 18, "amount": "100000000000000000000"},
}
_1INCH_USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def fetch_1inch_spread(symbol: str) -> dict:
    """
    Compare 1inch aggregated DEX price vs Binance CEX spot price.
    DEX > CEX (+spread) = DEX buyers more aggressive = bullish pressure building on CEX.
    DEX < CEX (-spread) = CEX running ahead of DEX = potential pullback signal.
    Uses v5.2 endpoint with v5.0 fallback (both no-auth).
    """
    token_info = _1INCH_TOKEN_MAP.get(symbol)
    if not token_info:
        return {}

    params_v52 = {"src": token_info["src"], "dst": _1INCH_USDC, "amount": token_info["amount"]}
    params_v50 = {"fromTokenAddress": token_info["src"], "toTokenAddress": _1INCH_USDC, "amount": token_info["amount"]}
    quote = (
        _safe_get("https://api.1inch.io/v5.2/1/quote", params=params_v52, timeout=10) or
        _safe_get("https://api.1inch.io/v5.0/1/quote", params=params_v50, timeout=10)
    )
    if not quote:
        return {}

    try:
        # Handle v5.2 (dstAmount) and v5.0 (toTokenAmount) response formats
        raw_out = quote.get("dstAmount") or quote.get("toTokenAmount") or quote.get("toAmount")
        if not raw_out:
            return {}
        usdc_out = float(raw_out) / 1e6  # USDC has 6 decimals
        amount_float = float(token_info["amount"]) / (10 ** token_info["decimals"])
        dex_price = usdc_out / amount_float

        # Get Binance CEX spot price for comparison
        binance_sym = symbol.replace("-", "").replace("/", "")
        cex_data = _safe_get(f"https://api.binance.com/api/v3/ticker/price?symbol={binance_sym}", timeout=5)
        if not cex_data:
            return {"dex_1inch_price": round(dex_price, 4)}
        cex_price = float(cex_data.get("price", 0))
        if not cex_price:
            return {"dex_1inch_price": round(dex_price, 4)}

        spread_pct = (dex_price - cex_price) / cex_price * 100
        return {
            "dex_1inch_price": round(dex_price, 4),
            "cex_binance_price": round(cex_price, 4),
            "defi_cex_spread_pct": round(spread_pct, 4),
            "defi_cex_signal": (
                "DEX_PREMIUM_BULLISH"  if spread_pct > 0.3  else
                "DEX_DISCOUNT_BEARISH" if spread_pct < -0.3 else
                "PRICE_ALIGNED"
            ),
        }
    except (KeyError, ValueError, TypeError):
        return {}


# ======================================================================
# Signal 13: Messari On-Chain Fundamentals (P0 - FREE, no auth)
# ======================================================================

_MESSARI_SLUG_MAP = {
    "BTCUSDT":  "bitcoin",       "ETHUSDT":  "ethereum",      "SOLUSDT":  "solana",
    "BNBUSDT":  "binance-coin",  "XRPUSDT":  "xrp",           "DOGEUSDT": "dogecoin",
    "ADAUSDT":  "cardano",       "AVAXUSDT": "avalanche",      "LINKUSDT": "chainlink",
    "DOTUSDT":  "polkadot",      "MATICUSDT":"polygon",        "ARBUSDT":  "arbitrum",
    "OPUSDT":   "optimism",      "INJUSDT":  "injective",      "SUIUSDT":  "sui",
    "APTUSDT":  "aptos",         "NEARUSDT": "near-protocol",
}


def fetch_messari_fundamentals(symbol: str) -> dict:
    """
    Fetch on-chain fundamental metrics from Messari (free, no auth required).
    Key alpha signals not available from pure price feeds:
      - active_addresses_24h: adoption momentum, leads price on alts by weeks
      - txn_volume_usd_24h: real economic throughput (NVT ratio proxy)
      - nvt_ratio: market_cap / txn_volume — historically >100 = overvalued
      - real_volume_24h_usd: wash-trading-adjusted volume
      - annual_inflation_pct: supply dilution pressure (critical for alts)
    """
    slug = _MESSARI_SLUG_MAP.get(symbol)
    if not slug:
        return {}

    data = _safe_get(
        f"https://data.messari.io/api/v1/assets/{slug}/metrics",
        timeout=12,
    )
    if not data or not data.get("data"):
        return {}

    try:
        metrics = data["data"]
        result = {}

        ocd = metrics.get("on_chain_data") or {}
        if ocd.get("active_addresses"):
            result["active_addresses_24h"] = int(ocd["active_addresses"])
        if ocd.get("txn_volume_last_24_hours"):
            result["txn_volume_usd_24h"] = round(float(ocd["txn_volume_last_24_hours"]), 0)
        if ocd.get("transactions_last_24_hours"):
            result["txn_count_24h"] = int(ocd["transactions_last_24_hours"])

        # Real vs reported volume (wash-trading indicator)
        md = metrics.get("market_data") or {}
        real_vol = md.get("real_volume_last_24_hours")
        rpt_vol = md.get("volume_last_24_hours")
        if real_vol:
            result["real_volume_24h_usd"] = round(float(real_vol), 0)
        if real_vol and rpt_vol and float(rpt_vol) > 0:
            result["real_vol_ratio"] = round(float(real_vol) / float(rpt_vol), 3)

        # NVT ratio: price disconnected from on-chain utility when high
        mcap = (metrics.get("marketcap") or {}).get("current_marketcap_usd")
        txn_vol = ocd.get("txn_volume_last_24_hours")
        if mcap and txn_vol and float(txn_vol) > 0:
            nvt = float(mcap) / float(txn_vol)
            result["nvt_ratio"] = round(nvt, 1)
            result["nvt_signal"] = (
                "OVERVALUED"  if nvt > 100 else
                "ELEVATED"    if nvt > 60  else
                "FAIR"        if nvt > 20  else
                "UNDERVALUED"
            )

        # Supply inflation pressure (dilutive for long alts)
        supply = metrics.get("supply") or {}
        if supply.get("annual_inflation_percent") is not None:
            result["annual_inflation_pct"] = round(float(supply["annual_inflation_percent"]), 3)

        return result
    except (KeyError, ValueError, TypeError):
        return {}


# ======================================================================
# Signal 14: Coinpaprika Supplemental Metrics (P1 - FREE, no auth, CORS OK)
# ======================================================================

_COINPAPRIKA_ID_MAP = {
    "BTCUSDT":  "btc-bitcoin",        "ETHUSDT":  "eth-ethereum",
    "SOLUSDT":  "sol-solana",          "BNBUSDT":  "bnb-binance-coin",
    "XRPUSDT":  "xrp-xrp",            "DOGEUSDT": "doge-dogecoin",
    "ADAUSDT":  "ada-cardano",         "AVAXUSDT": "avax-avalanche-2",
    "LINKUSDT": "link-chainlink",      "DOTUSDT":  "dot-polkadot",
    "MATICUSDT":"matic-polygon",       "SUIUSDT":  "sui-sui",
    "ARBUSDT":  "arb-arbitrum",        "OPUSDT":   "op-optimism",
    "INJUSDT":  "inj-injective-protocol", "NEARUSDT": "near-near-protocol",
    "APTUSDT":  "apt-aptos",
}


def fetch_coinpaprika_metrics(symbol: str) -> dict:
    """
    Fetch supplemental multi-timeframe metrics from Coinpaprika (free, no auth).
    Unique signals vs CoinGecko: 7d/30d/1y % change, ATH distance, market cap rank.
    Weekly momentum alignment/opposition is used in confidence calibration.
    """
    coin_id = _COINPAPRIKA_ID_MAP.get(symbol)
    if not coin_id:
        return {}

    data = _safe_get(f"https://api.coinpaprika.com/v1/tickers/{coin_id}", timeout=8)
    if not data:
        return {}

    try:
        quotes = data.get("quotes", {}).get("USD", {})
        result = {}

        for key, field in [
            ("price_change_7d_pct",  "percent_change_7d"),
            ("price_change_30d_pct", "percent_change_30d"),
            ("price_change_1y_pct",  "percent_change_1y"),
        ]:
            val = quotes.get(field)
            if val is not None:
                result[key] = round(float(val), 2)

        if data.get("rank"):
            result["market_cap_rank"] = int(data["rank"])

        ath = quotes.get("ath_price")
        cur = quotes.get("price")
        if ath and cur and float(ath) > 0:
            ath_dist = ((float(cur) - float(ath)) / float(ath)) * 100
            result["ath_distance_pct"] = round(ath_dist, 1)
            result["ath_zone"] = (
                "NEAR_ATH"      if ath_dist > -10 else
                "RECOVERY"      if ath_dist > -40 else
                "MID_RANGE"     if ath_dist > -70 else
                "DEEP_DISCOUNT"
            )

        pct_7d = result.get("price_change_7d_pct")
        if pct_7d is not None:
            result["weekly_momentum"] = (
                "STRONG_UPTREND"   if pct_7d > 15  else
                "UPTREND"          if pct_7d > 5   else
                "STRONG_DOWNTREND" if pct_7d < -15 else
                "DOWNTREND"        if pct_7d < -5  else
                "SIDEWAYS"
            )

        return result
    except (KeyError, ValueError, TypeError):
        return {}


# ======================================================================
# Confidence Adjustment Engine
# ======================================================================

def adjust_confidence(pick: dict) -> dict:
    """
    Adjust pick confidence based on enrichment signals.
    Rules:
      - Funding rate > 0.03% (0.0003) and LONG: reduce 0.05 (crowded trade)
      - RSI > 70 and LONG: reduce 0.05 (overbought)
      - RSI < 30 and LONG: increase 0.05 (oversold bounce)
      - Volume 24h increase > 100%: increase 0.03 (volume confirmation)
    """
    enrichment = pick.get("enrichment", {})
    if not enrichment:
        return pick

    original_confidence = pick.get("confidence", 0.5)
    adjustment = 0.0
    reasons = []

    direction = pick.get("direction", pick.get("signal_type", "LONG")).upper()
    is_long = direction in ("LONG", "BUY")

    # --- Funding rate check ---
    funding = enrichment.get("funding", {})
    avg_funding = funding.get("avg_funding_8h")
    premium = enrichment.get("premium_index", {})
    last_funding = premium.get("last_funding_rate")

    # Use premium index funding if available, otherwise use avg from multi-exchange
    effective_funding = last_funding if last_funding is not None else avg_funding

    if effective_funding is not None:
        if effective_funding > 0.0003 and is_long:
            adjustment -= 0.05
            reasons.append(f"funding={effective_funding:.4%} crowded long, -0.05")
        elif effective_funding > 0.0003 and not is_long:
            adjustment += 0.03
            reasons.append(f"funding={effective_funding:.4%} crowded long favors short, +0.03")
        elif effective_funding < -0.0003 and not is_long:
            adjustment -= 0.05
            reasons.append(f"funding={effective_funding:.4%} crowded short, -0.05")
        elif effective_funding < -0.0003 and is_long:
            adjustment += 0.03
            reasons.append(f"funding={effective_funding:.4%} crowded short favors long, +0.03")

    # --- RSI check ---
    rsi_data = enrichment.get("rsi", {})
    rsi = rsi_data.get("rsi_14_1h")
    if rsi is not None:
        if rsi > 70 and is_long:
            adjustment -= 0.05
            reasons.append(f"RSI={rsi:.1f} overbought for long, -0.05")
        elif rsi < 30 and is_long:
            adjustment += 0.05
            reasons.append(f"RSI={rsi:.1f} oversold bounce for long, +0.05")
        elif rsi > 70 and not is_long:
            adjustment += 0.05
            reasons.append(f"RSI={rsi:.1f} overbought favors short, +0.05")
        elif rsi < 30 and not is_long:
            adjustment -= 0.05
            reasons.append(f"RSI={rsi:.1f} oversold against short, -0.05")

    # --- Volume confirmation check ---
    ticker = enrichment.get("ticker_24h", {})
    vol_change = ticker.get("volume_24h_change_pct")
    # If we have volume_24h_usd but not change%, use trades count as proxy
    trades_count = ticker.get("trades_count_24h", 0)
    if vol_change is not None and vol_change > 100:
        adjustment += 0.03
        reasons.append(f"volume 24h change={vol_change:.0f}% >100%, +0.03")
    elif trades_count and trades_count > 500000:
        # High trade count as volume confirmation proxy
        adjustment += 0.02
        reasons.append(f"high trade activity ({trades_count:,} trades), +0.02")

    # --- Fear & Greed alignment ---
    sentiment = enrichment.get("sentiment", {})
    fg = sentiment.get("fear_greed_index")
    if fg is not None:
        if fg < 25 and is_long:
            adjustment += 0.03
            reasons.append(f"F&G={fg} extreme fear favors long, +0.03")
        elif fg > 75 and not is_long:
            adjustment += 0.03
            reasons.append(f"F&G={fg} extreme greed favors short, +0.03")
        elif fg < 25 and not is_long:
            adjustment -= 0.03
            reasons.append(f"F&G={fg} extreme fear against short, -0.03")
        elif fg > 75 and is_long:
            adjustment -= 0.03
            reasons.append(f"F&G={fg} extreme greed against long, -0.03")

    # --- Messari NVT check (on-chain fundamental valuation) ---
    on_chain = enrichment.get("on_chain", {})
    nvt = on_chain.get("nvt_ratio")
    if nvt is not None and nvt > 100 and is_long:
        adjustment -= 0.03
        reasons.append(f"NVT={nvt:.0f} overvalued vs on-chain activity, -0.03")

    # --- Coinpaprika weekly momentum alignment ---
    supplemental = enrichment.get("supplemental", {})
    pct_7d = supplemental.get("price_change_7d_pct")
    if pct_7d is not None:
        if pct_7d > 10 and is_long:
            adjustment += 0.02
            reasons.append(f"7d momentum={pct_7d:.1f}% confirms long, +0.02")
        elif pct_7d < -10 and not is_long:
            adjustment += 0.02
            reasons.append(f"7d momentum={pct_7d:.1f}% confirms short, +0.02")
        elif pct_7d > 10 and not is_long:
            adjustment -= 0.03
            reasons.append(f"7d momentum={pct_7d:.1f}% against short, -0.03")
        elif pct_7d < -10 and is_long:
            adjustment -= 0.03
            reasons.append(f"7d momentum={pct_7d:.1f}% against long, -0.03")

    # --- BTC mempool demand boost ---
    mempool = enrichment.get("mempool", {})
    btc_demand = mempool.get("btc_demand_signal")
    if btc_demand == "BULLISH_DEMAND" and is_long and "BTC" in pick.get("symbol", ""):
        adjustment += 0.02
        reasons.append(f"BTC mempool demand={btc_demand}, +0.02")

    # Apply adjustment
    new_confidence = round(max(0.0, min(0.95, original_confidence + adjustment)), 3)
    pick["confidence"] = new_confidence
    # FIX: ml_score must come from real ML model, not confidence adjustments
    # pick["ml_score"] = new_confidence  # REMOVED: was fake ML

    # Record adjustment metadata
    enrichment["confidence_adjustment"] = {
        "original_confidence": original_confidence,
        "adjustment": round(adjustment, 3),
        "adjusted_confidence": new_confidence,
        "reasons": reasons,
    }

    return pick


# ======================================================================
# Main Enrichment Engine
# ======================================================================

def enrich_pick(pick: dict) -> dict:
    """Enrich a single pick with all market context signals."""
    symbol = pick.get('symbol', 'BTCUSDT')

    # Fetch all signals (with caching)
    funding = _cached_fetch(f"funding_{symbol}", 300, lambda: fetch_funding(symbol))
    oi = _cached_fetch(f"oi_{symbol}", 300, lambda: fetch_oi_change(symbol))
    fear_greed = _cached_fetch("fear_greed", 3600, fetch_fear_greed)
    derivatives = _cached_fetch(f"deriv_{symbol}", 60, lambda: fetch_derivatives(symbol))
    ls_ratio = _cached_fetch(f"ls_{symbol}", 300, lambda: fetch_long_short_ratio(symbol))
    dex = _cached_fetch(f"dex_{symbol}", 120, lambda: fetch_dex_flow(symbol))
    premium = _cached_fetch(f"premium_{symbol}", 300, lambda: fetch_binance_premium_index(symbol))
    ticker_24h = _cached_fetch(f"ticker24h_{symbol}", 300, lambda: fetch_binance_ticker_24h(symbol))
    rsi = _cached_fetch(f"rsi_{symbol}", 300, lambda: fetch_rsi(symbol))
    # New supplemental signals (all free, no auth)
    mempool     = _cached_fetch("mempool_btc", 180,  fetch_mempool_btc)           if "BTC" in symbol else {}
    dex_0x      = _cached_fetch(f"0x_{symbol}",  300,  lambda: fetch_0x_liquidity(symbol))
    dex_1inch   = _cached_fetch(f"1inch_{symbol}", 300, lambda: fetch_1inch_spread(symbol))
    on_chain    = _cached_fetch(f"messari_{symbol}", 3600, lambda: fetch_messari_fundamentals(symbol))
    supplemental = _cached_fetch(f"paprika_{symbol}", 3600, lambda: fetch_coinpaprika_metrics(symbol))

    enrichment = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "funding": funding or {},
        "open_interest": oi or {},
        "derivatives": derivatives or {},
        "sentiment": fear_greed or {},
        "market_structure": ls_ratio or {},
        "dex_flow": dex or {},
        "premium_index": premium or {},
        "ticker_24h": ticker_24h or {},
        "rsi": rsi or {},
        # New signals
        "mempool": mempool or {},
        "dex_0x": dex_0x or {},
        "dex_1inch": dex_1inch or {},
        "on_chain": on_chain or {},
        "supplemental": supplemental or {},
    }

    # Build context summary — count bearish vs bullish signals
    bearish_signals = []
    bullish_signals = []

    fund_dir = (funding or {}).get('funding_signal_direction', '')
    if 'BEARISH' in fund_dir:
        bearish_signals.append("EXTREME_FUNDING")
    elif 'BULLISH' in fund_dir:
        bullish_signals.append("NEGATIVE_FUNDING")

    oi_sig = (oi or {}).get('oi_signal', '')
    if oi_sig == 'SURGING':
        bearish_signals.append("SURGING_OI")
    elif oi_sig in ('DECLINING', 'CRASHING'):
        bullish_signals.append("DECLINING_OI")

    fg = (fear_greed or {}).get('fear_greed_index', 50)
    if fg > 75:
        bearish_signals.append("EXTREME_GREED")
    elif fg < 25:
        bullish_signals.append("EXTREME_FEAR")

    crowd = (ls_ratio or {}).get('crowd_bias', '')
    if crowd == 'OVERLONG':
        bearish_signals.append("CROWD_OVERLONG")
    elif crowd == 'OVERSHORT':
        bullish_signals.append("CROWD_OVERSHORT")

    dvol_sig = (derivatives or {}).get('dvol_signal', '')
    if dvol_sig == 'ELEVATED':
        # IV spikes can be either direction — note it
        bearish_signals.append("ELEVATED_IV")

    dex_sig = (dex or {}).get('dex_flow_signal', '')
    if 'AGGRESSIVE_BUY' in dex_sig:
        bearish_signals.append("DEX_BUY_FRENZY")  # contrarian
    elif 'AGGRESSIVE_SELL' in dex_sig:
        bullish_signals.append("DEX_PANIC_SELL")  # contrarian

    # Messari NVT signal (on-chain valuation)
    nvt_sig = (enrichment.get("on_chain") or {}).get('nvt_signal', '')
    if nvt_sig == 'OVERVALUED':
        bearish_signals.append("NVT_OVERVALUED")
    elif nvt_sig == 'UNDERVALUED':
        bullish_signals.append("NVT_UNDERVALUED")

    # Coinpaprika weekly momentum
    weekly_mom = (enrichment.get("supplemental") or {}).get('weekly_momentum', '')
    if weekly_mom == 'STRONG_UPTREND':
        bullish_signals.append("7D_STRONG_UPTREND")
    elif weekly_mom == 'STRONG_DOWNTREND':
        bearish_signals.append("7D_STRONG_DOWNTREND")

    # BTC mempool demand
    btc_demand = (enrichment.get("mempool") or {}).get('btc_demand_signal', '')
    if btc_demand == 'BULLISH_DEMAND':
        bullish_signals.append("BTC_NETWORK_DEMAND")

    # 0x liquidity warning
    liq_sig = (enrichment.get("dex_0x") or {}).get('dex_liquidity_signal', '')
    if liq_sig == 'ILLIQUID_WARNING':
        bearish_signals.append("DEX_ILLIQUID")

    # Determine overall context
    direction = pick.get('direction', 'LONG')
    bearish_count = len(bearish_signals)
    bullish_count = len(bullish_signals)

    if direction in ('SHORT', 'SELL'):
        alignment = bearish_count
        contrary = bullish_count
        aligned_sigs = bearish_signals
    else:
        alignment = bullish_count
        contrary = bearish_count
        aligned_sigs = bullish_signals

    context_parts = bearish_signals + bullish_signals
    if alignment >= 3:
        grade = "STRONG_ALIGNMENT"
    elif alignment >= 2:
        grade = "MODERATE_ALIGNMENT"
    elif contrary >= 3:
        grade = "STRONG_CONTRARY"
    else:
        grade = "NEUTRAL_CONDITIONS"

    enrichment['context_summary'] = (
        f"{' + '.join(context_parts) if context_parts else 'NEUTRAL'} "
        f"= {grade} ({alignment}/{alignment+contrary} signals aligned with {direction})"
    )
    enrichment['alignment_score'] = alignment
    enrichment['contrary_score'] = contrary
    enrichment['context_grade'] = grade

    pick['enrichment'] = enrichment

    # Apply confidence adjustments based on enrichment data
    pick = adjust_confidence(pick)

    return pick


def enrich_picks(picks: list) -> list:
    """Enrich all picks with market context. Uses threading for speed."""
    if not picks:
        return picks

    print(f"  [ENRICHMENT] Enriching {len(picks)} picks with market context...")

    # Get unique symbols to minimize API calls
    symbols = set(p.get('symbol', '') for p in picks)
    print(f"  [ENRICHMENT] {len(symbols)} unique symbols: {', '.join(sorted(symbols)[:10])}")

    # Enrich picks (cache means duplicate symbols are fast)
    enriched = []
    aligned = 0
    for pick in picks:
        try:
            enriched_pick = enrich_pick(pick)
            enriched.append(enriched_pick)
            if enriched_pick.get('enrichment', {}).get('context_grade', '').startswith('STRONG_ALIGN'):
                aligned += 1
        except Exception as e:
            pick['enrichment'] = {"error": str(e)}
            enriched.append(pick)

    print(f"  [ENRICHMENT] Done. {aligned}/{len(enriched)} picks have strong market alignment.")

    # Log fear & greed for visibility
    fg = _cache.get('fear_greed', (None, None))[0]
    if fg:
        print(f"  [ENRICHMENT] Fear & Greed: {fg.get('fear_greed_index', '?')} ({fg.get('fear_greed_label', '?')})")

    return enriched


def run_enrichment(picks: list) -> list:
    """Sync entry point for use in existing code."""
    return enrich_picks(picks)


if __name__ == "__main__":
    # Test with a sample pick
    test_pick = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "entry_price": 70000,
        "strategy": "test",
    }
    result = enrich_pick(test_pick)
    print(json.dumps(result.get('enrichment', {}), indent=2, default=str))
