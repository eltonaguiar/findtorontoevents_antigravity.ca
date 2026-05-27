"""
Free Data Feeds for Battleground — no API keys required.

Sources:
  1. Binance Public API — 24h volume, open interest, funding rates, book ticker
  2. CoinGecko Public API — prices, global metrics, 30d history
  3. Alternative.me — Fear & Greed Index
  4. Blockchain.com — hash rate, difficulty, mempool
  5. FRED (Federal Reserve) — Treasury yields

All data is fetched with proper error handling and timeouts,
parsed into a standardized format, and saved to data/market_snapshot.json.
"""
import json
import os
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
SNAPSHOT_FILE = os.path.join(DATA_DIR, "market_snapshot.json")

TIMEOUT = 10  # seconds per request
USER_AGENT = "Battleground-DataFeed/1.0"

# Symbols we track
BINANCE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "NEARUSDT"]
COINGECKO_IDS = "bitcoin,ethereum,solana,ripple,binancecoin"


_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]


def _fetch_json(url, timeout=TIMEOUT):
    """Fetch JSON from a URL with error handling and endpoint failover."""
    # Build failover URL list if hitting known Binance endpoints
    urls_to_try = [url]
    if "fapi.binance.com" in url:
        for fbase in _FAPI_BASES:
            alt = url.replace("https://fapi.binance.com", fbase)
            if alt != url and alt not in urls_to_try:
                urls_to_try.append(alt)
    elif "api.binance.com" in url:
        for sbase in _SPOT_BASES:
            alt = url.replace("https://api.binance.com", sbase)
            if alt != url and alt not in urls_to_try:
                urls_to_try.append(alt)

    for try_url in urls_to_try:
        try:
            req = Request(try_url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code in (451, 403):
                continue  # geo-blocked, try next endpoint
            return {"error": str(e)}
        except (URLError, json.JSONDecodeError, Exception):
            continue
    return {"error": "all endpoints failed"}


def _safe_float(val, default=0.0):
    """Safely convert to float."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ==============================================================================
# 1. BINANCE PUBLIC API
# ==============================================================================

def fetch_binance_24hr():
    """Fetch 24h ticker data for tracked symbols."""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = _fetch_json(url)
    if isinstance(data, dict) and "error" in data:
        return {"source": "binance_24hr", "error": data["error"], "metrics": {}}

    metrics = {}
    if isinstance(data, list):
        for item in data:
            sym = item.get("symbol", "")
            if sym in BINANCE_SYMBOLS:
                metrics[sym] = {
                    "price": _safe_float(item.get("lastPrice")),
                    "price_change_pct": _safe_float(item.get("priceChangePercent")),
                    "volume_usd": _safe_float(item.get("quoteVolume")),
                    "high_24h": _safe_float(item.get("highPrice")),
                    "low_24h": _safe_float(item.get("lowPrice")),
                    "trade_count": int(item.get("count", 0)),
                }

    return {
        "source": "binance_24hr",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


def fetch_binance_open_interest():
    """Fetch open interest for perpetual futures."""
    metrics = {}
    for sym in BINANCE_SYMBOLS:
        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym}"
        data = _fetch_json(url)
        if isinstance(data, dict) and "openInterest" in data:
            metrics[sym] = {
                "open_interest": _safe_float(data.get("openInterest")),
                "symbol": data.get("symbol", sym),
            }

    return {
        "source": "binance_open_interest",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


def fetch_binance_funding_rates():
    """Fetch current funding rates for perpetual futures."""
    metrics = {}
    for sym in BINANCE_SYMBOLS:
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&limit=1"
        data = _fetch_json(url)
        if isinstance(data, list) and len(data) > 0:
            entry = data[0]
            metrics[sym] = {
                "funding_rate": _safe_float(entry.get("fundingRate")),
                "funding_time": entry.get("fundingTime", 0),
            }

    return {
        "source": "binance_funding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


def fetch_binance_book_ticker():
    """Fetch best bid/ask (spread) for tracked symbols."""
    url = "https://fapi.binance.com/fapi/v1/ticker/bookTicker"
    data = _fetch_json(url)
    metrics = {}

    if isinstance(data, list):
        for item in data:
            sym = item.get("symbol", "")
            if sym in BINANCE_SYMBOLS:
                bid = _safe_float(item.get("bidPrice"))
                ask = _safe_float(item.get("askPrice"))
                mid = (bid + ask) / 2 if (bid + ask) > 0 else 0
                spread_bps = ((ask - bid) / mid * 10000) if mid > 0 else 0
                metrics[sym] = {
                    "bid": bid,
                    "ask": ask,
                    "spread_bps": round(spread_bps, 2),
                }

    return {
        "source": "binance_book",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


# ==============================================================================
# 2. COINGECKO PUBLIC API
# ==============================================================================

def fetch_coingecko_prices():
    """Fetch current prices with 24h change and market cap."""
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={COINGECKO_IDS}"
        f"&vs_currencies=usd"
        f"&include_24hr_change=true"
        f"&include_market_cap=true"
        f"&include_24hr_vol=true"
    )
    data = _fetch_json(url)
    if isinstance(data, dict) and "error" in data:
        return {"source": "coingecko_prices", "error": data["error"], "metrics": {}}

    metrics = {}
    for coin_id, vals in data.items():
        if isinstance(vals, dict):
            metrics[coin_id] = {
                "price_usd": _safe_float(vals.get("usd")),
                "change_24h_pct": _safe_float(vals.get("usd_24h_change")),
                "market_cap_usd": _safe_float(vals.get("usd_market_cap")),
                "volume_24h_usd": _safe_float(vals.get("usd_24h_vol")),
            }

    return {
        "source": "coingecko_prices",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


def fetch_coingecko_global():
    """Fetch global market data — total market cap, BTC dominance."""
    url = "https://api.coingecko.com/api/v3/global"
    data = _fetch_json(url)

    metrics = {}
    if isinstance(data, dict) and "data" in data:
        d = data["data"]
        metrics = {
            "total_market_cap_usd": _safe_float(d.get("total_market_cap", {}).get("usd")),
            "total_volume_24h_usd": _safe_float(d.get("total_volume", {}).get("usd")),
            "btc_dominance_pct": _safe_float(d.get("market_cap_percentage", {}).get("btc")),
            "eth_dominance_pct": _safe_float(d.get("market_cap_percentage", {}).get("eth")),
            "active_cryptocurrencies": d.get("active_cryptocurrencies", 0),
            "market_cap_change_24h_pct": _safe_float(d.get("market_cap_change_percentage_24h_usd")),
        }

    return {
        "source": "coingecko_global",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


def fetch_coingecko_btc_30d():
    """Fetch 30-day BTC price history for volume trend analysis."""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30"
    data = _fetch_json(url)

    metrics = {}
    if isinstance(data, dict) and "prices" in data:
        prices = data["prices"]  # [[timestamp_ms, price], ...]
        volumes = data.get("total_volumes", [])

        if prices:
            recent_prices = [p[1] for p in prices[-7:]]
            all_prices = [p[1] for p in prices]
            metrics["current_price"] = all_prices[-1] if all_prices else 0
            metrics["price_7d_avg"] = sum(recent_prices) / len(recent_prices) if recent_prices else 0
            metrics["price_30d_avg"] = sum(all_prices) / len(all_prices) if all_prices else 0
            metrics["price_30d_high"] = max(all_prices) if all_prices else 0
            metrics["price_30d_low"] = min(all_prices) if all_prices else 0

        if volumes:
            recent_vols = [v[1] for v in volumes[-7:]]
            all_vols = [v[1] for v in volumes]
            metrics["volume_24h"] = all_vols[-1] if all_vols else 0
            metrics["volume_7d_avg"] = sum(recent_vols) / len(recent_vols) if recent_vols else 0
            metrics["volume_30d_avg"] = sum(all_vols) / len(all_vols) if all_vols else 0
            metrics["volume_ratio_vs_7d"] = (
                metrics["volume_24h"] / metrics["volume_7d_avg"]
                if metrics["volume_7d_avg"] > 0 else 0
            )

    return {
        "source": "coingecko_btc_30d",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


# ==============================================================================
# 3. ALTERNATIVE.ME — FEAR & GREED INDEX
# ==============================================================================

def fetch_fear_greed():
    """Fetch last 10 days of Crypto Fear & Greed Index."""
    url = "https://api.alternative.me/fng/?limit=10"
    data = _fetch_json(url)

    metrics = {}
    if isinstance(data, dict) and "data" in data:
        entries = data["data"]
        if entries:
            latest = entries[0]
            metrics["current_value"] = int(latest.get("value", 50))
            metrics["current_label"] = latest.get("value_classification", "Neutral")
            metrics["timestamp"] = latest.get("timestamp", "")

            # Compute 7-day trend
            values = [int(e.get("value", 50)) for e in entries[:7]]
            metrics["avg_7d"] = round(sum(values) / len(values), 1) if values else 50
            metrics["trend"] = "improving" if values[0] > values[-1] else "declining"
            metrics["history"] = [
                {"value": int(e.get("value", 50)), "label": e.get("value_classification", "")}
                for e in entries
            ]

    return {
        "source": "alternative_me_fng",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


# ==============================================================================
# 4. BLOCKCHAIN.COM
# ==============================================================================

def fetch_blockchain_stats():
    """Fetch Bitcoin network stats — hash rate, difficulty, mempool."""
    url = "https://api.blockchain.info/stats"
    data = _fetch_json(url)

    metrics = {}
    if isinstance(data, dict) and "error" not in data:
        metrics = {
            "hash_rate_ths": _safe_float(data.get("hash_rate", 0)) / 1e12,  # TH/s
            "difficulty": _safe_float(data.get("difficulty")),
            "mempool_bytes": _safe_float(data.get("mempool_size")),
            "mempool_tx_count": int(data.get("mempool_count", 0) or 0),
            "blocks_mined_24h": int(data.get("n_blocks_mined", 0) or 0),
            "btc_mined_24h": _safe_float(data.get("n_btc_mined", 0)) / 1e8,  # satoshi to BTC
            "total_fees_btc": _safe_float(data.get("total_fees_btc", 0)) / 1e8,
            "avg_block_size_kb": _safe_float(data.get("blocks_size", 0)) / 1024,
            "market_price_usd": _safe_float(data.get("market_price_usd")),
            "trade_volume_usd": _safe_float(data.get("trade_volume_usd")),
        }

    return {
        "source": "blockchain_info",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


# ==============================================================================
# 5. FRED (Federal Reserve Economic Data) — Public XML/JSON
# ==============================================================================

def fetch_fred_treasury():
    """
    Fetch US Treasury yield data from Treasury.gov XML API.
    No API key required.
    """
    metrics = {}

    # Treasury.gov RSS/XML feed for daily yield curve
    url = "https://data.treasury.gov/feed.svc/DailyTreasuryYieldCurveRateData?$top=1&$orderby=NEW_DATE%20desc&$format=json"
    try:
        data = _fetch_json(url, timeout=TIMEOUT)
        if isinstance(data, dict) and "d" in data:
            results = data["d"].get("results", data["d"] if isinstance(data["d"], list) else [])
            if not results and "value" in data:
                results = data["value"]
            if results and len(results) > 0:
                row = results[0]
                metrics = {
                    "date": row.get("NEW_DATE", ""),
                    "yield_1mo": _safe_float(row.get("BC_1MONTH")),
                    "yield_3mo": _safe_float(row.get("BC_3MONTH")),
                    "yield_6mo": _safe_float(row.get("BC_6MONTH")),
                    "yield_1yr": _safe_float(row.get("BC_1YEAR")),
                    "yield_2yr": _safe_float(row.get("BC_2YEAR")),
                    "yield_5yr": _safe_float(row.get("BC_5YEAR")),
                    "yield_10yr": _safe_float(row.get("BC_10YEAR")),
                    "yield_30yr": _safe_float(row.get("BC_30YEAR")),
                }
                y2 = metrics.get("yield_2yr", 0)
                y10 = metrics.get("yield_10yr", 0)
                if y2 > 0 and y10 > 0:
                    metrics["yield_curve_spread_2s10s"] = round(y10 - y2, 3)
                    metrics["yield_curve_inverted"] = y2 > y10
    except Exception:
        pass

    # Fallback: try FRED public page scraping for DGS10
    if not metrics or all(v == 0 for k, v in metrics.items() if k.startswith("yield_")):
        try:
            fred_url = "https://fred.stlouisfed.org/data/DGS10.txt"
            req = Request(fred_url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=TIMEOUT) as resp:
                text = resp.read().decode("utf-8")
                lines = text.strip().split("\n")
                # Find last non-empty data line
                for line in reversed(lines):
                    parts = line.strip().split()
                    if len(parts) == 2 and parts[1] != ".":
                        try:
                            metrics["date"] = parts[0]
                            metrics["yield_10yr"] = float(parts[1])
                            break
                        except ValueError:
                            continue
        except Exception as e:
            if not metrics:
                metrics = {"error": str(e)}

    return {
        "source": "us_treasury",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }


# ==============================================================================
# AGGREGATION
# ==============================================================================

def get_market_snapshot():
    """
    Fetch ALL data sources and return a unified market snapshot.
    Saves to data/market_snapshot.json.
    """
    print("  Fetching market data from free sources...")
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    fetchers = [
        ("binance_24hr", fetch_binance_24hr),
        ("binance_open_interest", fetch_binance_open_interest),
        ("binance_funding", fetch_binance_funding_rates),
        ("binance_book", fetch_binance_book_ticker),
        ("coingecko_prices", fetch_coingecko_prices),
        ("coingecko_global", fetch_coingecko_global),
        ("coingecko_btc_30d", fetch_coingecko_btc_30d),
        ("fear_greed", fetch_fear_greed),
        ("blockchain_info", fetch_blockchain_stats),
        ("us_treasury", fetch_fred_treasury),
    ]

    for name, fetcher in fetchers:
        try:
            print(f"    -> {name}...", end=" ", flush=True)
            result = fetcher()
            snapshot["sources"][name] = result
            has_error = "error" in result or "error" in result.get("metrics", {})
            print("OK" if not has_error else f"PARTIAL ({result.get('error', result['metrics'].get('error', ''))})")
        except Exception as e:
            snapshot["sources"][name] = {
                "source": name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": {},
                "error": str(e),
            }
            print(f"FAIL ({e})")

    # Save snapshot
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\n  Snapshot saved to {SNAPSHOT_FILE}")
    return snapshot


# ==============================================================================
# REGIME SIGNALS
# ==============================================================================

def generate_regime_signals(snapshot=None):
    """
    Analyze the market snapshot and produce actionable regime signals.

    Returns dict of signals, each with:
      - signal: "BUY" / "SELL" / "NEUTRAL" / "AVOID"
      - value: the underlying metric value
      - reason: human-readable explanation
    """
    if snapshot is None:
        if os.path.exists(SNAPSHOT_FILE):
            with open(SNAPSHOT_FILE, "r") as f:
                snapshot = json.load(f)
        else:
            return {"error": "No snapshot available. Run get_market_snapshot() first."}

    sources = snapshot.get("sources", {})
    signals = {}

    # 1. Fear & Greed Signal
    fng = sources.get("fear_greed", {}).get("metrics", {})
    fng_value = fng.get("current_value", 50)
    if fng_value < 25:
        signals["fear_greed_signal"] = {
            "signal": "BUY",
            "value": fng_value,
            "label": fng.get("current_label", ""),
            "reason": f"Extreme Fear ({fng_value}) — historically a buying opportunity",
        }
    elif fng_value > 75:
        signals["fear_greed_signal"] = {
            "signal": "SELL",
            "value": fng_value,
            "label": fng.get("current_label", ""),
            "reason": f"Extreme Greed ({fng_value}) — historically a selling signal",
        }
    else:
        signals["fear_greed_signal"] = {
            "signal": "NEUTRAL",
            "value": fng_value,
            "label": fng.get("current_label", ""),
            "reason": f"Neutral zone ({fng_value}) — no extreme sentiment",
        }

    # 2. Funding Rate Signal
    funding = sources.get("binance_funding", {}).get("metrics", {})
    btc_funding = funding.get("BTCUSDT", {}).get("funding_rate", 0)
    if btc_funding > 0.001:  # >0.1% = overleveraged longs
        signals["funding_signal"] = {
            "signal": "SELL",
            "value": round(btc_funding * 100, 4),
            "reason": f"High funding rate ({btc_funding*100:.4f}%) — longs paying shorts, potential squeeze down",
        }
    elif btc_funding < -0.001:  # <-0.1% = overleveraged shorts
        signals["funding_signal"] = {
            "signal": "BUY",
            "value": round(btc_funding * 100, 4),
            "reason": f"Negative funding ({btc_funding*100:.4f}%) — shorts paying longs, potential squeeze up",
        }
    else:
        signals["funding_signal"] = {
            "signal": "NEUTRAL",
            "value": round(btc_funding * 100, 4),
            "reason": f"Normal funding ({btc_funding*100:.4f}%) — balanced leverage",
        }

    # 3. Volume Signal (24h vs 7d average)
    btc_30d = sources.get("coingecko_btc_30d", {}).get("metrics", {})
    vol_ratio = btc_30d.get("volume_ratio_vs_7d", 0)
    if vol_ratio > 2.0:
        signals["volume_signal"] = {
            "signal": "ALERT",
            "value": round(vol_ratio, 2),
            "reason": f"Volume spike: {vol_ratio:.1f}x 7-day average — major move in progress",
        }
    elif vol_ratio > 1.5:
        signals["volume_signal"] = {
            "signal": "ELEVATED",
            "value": round(vol_ratio, 2),
            "reason": f"Elevated volume: {vol_ratio:.1f}x 7-day average — increased activity",
        }
    elif vol_ratio > 0:
        signals["volume_signal"] = {
            "signal": "NEUTRAL",
            "value": round(vol_ratio, 2),
            "reason": f"Normal volume: {vol_ratio:.1f}x 7-day average",
        }
    else:
        signals["volume_signal"] = {
            "signal": "NO_DATA",
            "value": 0,
            "reason": "Volume data unavailable",
        }

    # 4. BTC Dominance Signal
    global_data = sources.get("coingecko_global", {}).get("metrics", {})
    btc_dom = global_data.get("btc_dominance_pct", 0)
    mkt_change = global_data.get("market_cap_change_24h_pct", 0)
    if btc_dom > 55 and mkt_change > 0:
        signals["dominance_signal"] = {
            "signal": "RISK_OFF",
            "value": round(btc_dom, 2),
            "reason": f"BTC dominance high ({btc_dom:.1f}%) + market up — capital flowing to BTC safety",
        }
    elif btc_dom < 45:
        signals["dominance_signal"] = {
            "signal": "ALT_SEASON",
            "value": round(btc_dom, 2),
            "reason": f"BTC dominance low ({btc_dom:.1f}%) — alt-season conditions",
        }
    else:
        signals["dominance_signal"] = {
            "signal": "NEUTRAL",
            "value": round(btc_dom, 2),
            "reason": f"BTC dominance normal ({btc_dom:.1f}%)",
        }

    # 5. Spread Signal (liquidity proxy)
    book = sources.get("binance_book", {}).get("metrics", {})
    btc_spread = book.get("BTCUSDT", {}).get("spread_bps", 0)
    if btc_spread > 5.0:
        signals["spread_signal"] = {
            "signal": "AVOID",
            "value": round(btc_spread, 2),
            "reason": f"Wide spread ({btc_spread:.1f} bps) — low liquidity, avoid trading",
        }
    elif btc_spread > 2.0:
        signals["spread_signal"] = {
            "signal": "CAUTION",
            "value": round(btc_spread, 2),
            "reason": f"Moderate spread ({btc_spread:.1f} bps) — reduced liquidity",
        }
    else:
        signals["spread_signal"] = {
            "signal": "GOOD",
            "value": round(btc_spread, 2),
            "reason": f"Tight spread ({btc_spread:.1f} bps) — good liquidity",
        }

    # 6. Yield Curve Signal (bonus — macro)
    treasury = sources.get("us_treasury", {}).get("metrics", {})
    if "yield_curve_inverted" in treasury:
        inverted = treasury["yield_curve_inverted"]
        spread_2s10s = treasury.get("yield_curve_spread_2s10s", 0)
        signals["yield_curve_signal"] = {
            "signal": "RISK_OFF" if inverted else "NEUTRAL",
            "value": spread_2s10s,
            "reason": (
                f"Yield curve INVERTED (2s10s: {spread_2s10s:.3f}%) — recession risk"
                if inverted
                else f"Yield curve normal (2s10s: {spread_2s10s:.3f}%)"
            ),
        }

    return signals


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  BATTLEGROUND FREE DATA FEEDS — Market Snapshot")
    print("=" * 70)
    print()

    snapshot = get_market_snapshot()

    print()
    print("=" * 70)
    print("  REGIME SIGNALS")
    print("=" * 70)
    print()

    signals = generate_regime_signals(snapshot)

    for name, sig in sorted(signals.items()):
        arrow = {"BUY": "+", "SELL": "-", "NEUTRAL": "=", "ALERT": "!", "AVOID": "X"}.get(
            sig.get("signal", ""), "?"
        )
        print(f"  [{arrow}] {name}")
        print(f"      Signal: {sig.get('signal', 'N/A')} | Value: {sig.get('value', 'N/A')}")
        print(f"      {sig.get('reason', '')}")
        print()

    # Print key metrics summary
    print("=" * 70)
    print("  KEY METRICS SUMMARY")
    print("=" * 70)
    print()

    binance = snapshot.get("sources", {}).get("binance_24hr", {}).get("metrics", {})
    for sym in BINANCE_SYMBOLS:
        m = binance.get(sym, {})
        if m:
            chg = m.get("price_change_pct", 0)
            arrow = "+" if chg > 0 else ""
            print(f"  {sym:>10}: ${m.get('price', 0):>12,.2f}  ({arrow}{chg:.2f}%)  Vol: ${m.get('volume_usd', 0):>15,.0f}")

    fng = snapshot.get("sources", {}).get("fear_greed", {}).get("metrics", {})
    if fng:
        print(f"\n  Fear & Greed: {fng.get('current_value', '?')} ({fng.get('current_label', '?')})")

    blockchain = snapshot.get("sources", {}).get("blockchain_info", {}).get("metrics", {})
    if blockchain:
        print(f"  BTC Hash Rate: {blockchain.get('hash_rate_ths', 0):,.0f} TH/s")
        print(f"  Mempool: {blockchain.get('mempool_tx_count', 0):,} txs")

    print()
