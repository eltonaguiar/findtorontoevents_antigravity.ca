"""
CoinMetrics Community API -- On-chain fundamentals
==================================================
Free API, no key required. Rate limit: 10 req / 6 sec.
Endpoint: https://community-api.coinmetrics.io/v4

Features:
- MVRV ratio (Market Value / Realized Value) -- cycle top/bottom indicator
- NVT ratio (Network Value / Transaction Volume) -- overvaluation detector
- Active addresses (1d) -- network activity proxy
- Hash rate -- miner health (BTC only)
- Fee revenue -- network demand signal

MVRV > 3.5 historically called every BTC cycle top.
NVT spikes > 95 preceded 80% of corrections.
"""
import requests
import json
import os
from datetime import datetime, timezone, timedelta

_CACHE = {}

# Circuit breaker: after 3 consecutive failures (e.g. 403 Forbidden), skip all
# remaining CoinMetrics calls for this scan cycle to avoid 30+ wasted requests.
_COINMETRICS_FAIL_COUNT = 0
_COINMETRICS_DISABLED = False

def _cached_get(url, key, ttl=1800):
    global _COINMETRICS_FAIL_COUNT, _COINMETRICS_DISABLED
    if _COINMETRICS_DISABLED:
        return _CACHE.get(key, {}).get("data")
    now = datetime.now(timezone.utc).timestamp()
    if key in _CACHE and now - _CACHE[key]["ts"] < ttl:
        return _CACHE[key]["data"]
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _CACHE[key] = {"data": data, "ts": now}
        _COINMETRICS_FAIL_COUNT = 0  # Reset on success
        return data
    except Exception as e:
        _COINMETRICS_FAIL_COUNT += 1
        if _COINMETRICS_FAIL_COUNT >= 3:
            _COINMETRICS_DISABLED = True
            try:
                print(f"  [coinmetrics] CIRCUIT BREAKER: disabled after {_COINMETRICS_FAIL_COUNT} consecutive failures (last: {e})")
            except ValueError:
                pass
        else:
            try:
                print(f"  [coinmetrics] {key} failed ({_COINMETRICS_FAIL_COUNT}/3): {e}")
            except ValueError:
                pass
        return _CACHE.get(key, {}).get("data")

# Map our symbols to CoinMetrics asset IDs
SYMBOL_TO_CM = {
    "BTC": "btc", "ETH": "eth", "SOL": "sol", "XRP": "xrp",
    "BNB": "bnb", "ADA": "ada", "DOGE": "doge", "DOT": "dot",
    "AVAX": "avax", "LINK": "link", "NEAR": "near", "UNI": "uni",
    "AAVE": "aave", "ATOM": "atom", "LTC": "ltc", "ETC": "etc",
}

def fetch_onchain_metrics(symbol: str) -> dict:
    """Fetch on-chain metrics from CoinMetrics Community API."""
    sym = symbol.upper().replace("-USD", "").replace("USDT", "")
    cm_id = SYMBOL_TO_CM.get(sym)
    if not cm_id:
        return {}

    # Get latest metrics
    metrics = "CapMVRVCur,NVTAdj,SplyAct1d,HashRate,FeeTotNtv,TxCnt,AdrActCnt"
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    url = (f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
           f"?assets={cm_id}&metrics={metrics}&start_time={start}&end_time={end}"
           f"&frequency=1d&page_size=7")

    data = _cached_get(url, f"cm_{cm_id}")
    if not data or "data" not in data:
        return {}

    rows = data["data"]
    if not rows:
        return {}

    latest = rows[-1]
    result = {}

    # MVRV ratio
    mvrv = latest.get("CapMVRVCur")
    if mvrv is not None:
        result["mvrv"] = float(mvrv)
        # Signal: MVRV > 3.5 = cycle top warning, < 1.0 = undervalued
        if float(mvrv) > 3.5:
            result["mvrv_signal"] = "overvalued"
        elif float(mvrv) < 1.0:
            result["mvrv_signal"] = "undervalued"
        else:
            result["mvrv_signal"] = "neutral"

    # NVT ratio
    nvt = latest.get("NVTAdj")
    if nvt is not None:
        result["nvt"] = float(nvt)

    # Active addresses
    active = latest.get("AdrActCnt") or latest.get("SplyAct1d")
    if active is not None:
        result["active_addresses"] = float(active)
        # Compute growth vs 7d ago
        if len(rows) >= 7:
            old_active = rows[0].get("AdrActCnt") or rows[0].get("SplyAct1d")
            if old_active and float(old_active) > 0:
                result["active_addr_growth_7d"] = (float(active) - float(old_active)) / float(old_active)

    # Hash rate (BTC mainly)
    hr = latest.get("HashRate")
    if hr is not None:
        result["hash_rate"] = float(hr)

    # Transaction count
    txc = latest.get("TxCnt")
    if txc is not None:
        result["tx_count"] = float(txc)

    return result


def get_onchain_features(symbol: str) -> dict:
    """Get on-chain features formatted for ML feature vector."""
    metrics = fetch_onchain_metrics(symbol)
    return {
        "mvrv_ratio": metrics.get("mvrv", 0.0),
        "nvt_ratio": min(200, metrics.get("nvt", 0.0)),  # Cap at 200
        "active_addr_growth": metrics.get("active_addr_growth_7d", 0.0),
        "hash_rate": metrics.get("hash_rate", 0.0),
        "tx_count": metrics.get("tx_count", 0.0),
    }
