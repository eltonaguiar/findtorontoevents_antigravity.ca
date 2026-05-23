"""
Mempool.space API -- BTC mempool congestion & fee pressure
=========================================================
Free API, no key required. Well-documented.
Endpoint: https://mempool.space/api

Features:
- Recommended fee rates (sat/vB) -- network demand signal
- Mempool size (vMB) -- congestion indicator
- Pending TX count -- activity signal

Mempool congestion spikes precede BTC volatility.
Fee surges correlate with panic/demand.
"""
import requests
from datetime import datetime, timezone

_CACHE = {}

def _cached_get(url, key, ttl=300):
    now = datetime.now(timezone.utc).timestamp()
    if key in _CACHE and now - _CACHE[key]["ts"] < ttl:
        return _CACHE[key]["data"]
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _CACHE[key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        print(f"  [mempool] {key} failed: {e}")
        return _CACHE.get(key, {}).get("data")


def fetch_mempool_stats() -> dict:
    """Fetch BTC mempool statistics."""
    result = {}

    # Fee estimates
    fees = _cached_get("https://mempool.space/api/v1/fees/recommended", "mempool_fees")
    if fees:
        result["fee_fastest"] = fees.get("fastestFee", 0)
        result["fee_half_hour"] = fees.get("halfHourFee", 0)
        result["fee_hour"] = fees.get("hourFee", 0)
        result["fee_economy"] = fees.get("economyFee", 0)
        # Fee urgency ratio: high = congested
        if result["fee_economy"] > 0:
            result["fee_urgency_ratio"] = result["fee_fastest"] / result["fee_economy"]
        else:
            result["fee_urgency_ratio"] = 1.0

    # Mempool stats
    mempool = _cached_get("https://mempool.space/api/mempool", "mempool_stats")
    if mempool:
        result["mempool_count"] = mempool.get("count", 0)
        result["mempool_vsize"] = mempool.get("vsize", 0)  # in vBytes
        result["mempool_total_fee"] = mempool.get("total_fee", 0)  # in satoshis
        # Convert vsize to MB
        result["mempool_mb"] = result["mempool_vsize"] / 1_000_000

    # Hashrate (1 month)
    hashrate = _cached_get("https://mempool.space/api/v1/mining/hashrate/1m", "mempool_hashrate")
    if hashrate and "currentHashrate" in hashrate:
        result["btc_hashrate_current"] = hashrate["currentHashrate"]
        result["btc_hashrate_avg"] = hashrate.get("currentDifficulty", 0)

    return result


def get_mempool_features() -> dict:
    """Get mempool features formatted for ML feature vector."""
    stats = fetch_mempool_stats()
    return {
        "mempool_fee_fastest": stats.get("fee_fastest", 0),
        "mempool_fee_ratio": stats.get("fee_urgency_ratio", 1.0),
        "mempool_mb": stats.get("mempool_mb", 0.0),
        "mempool_tx_count": stats.get("mempool_count", 0),
    }
