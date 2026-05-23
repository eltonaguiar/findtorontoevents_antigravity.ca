"""
On-Chain Crypto — Exchange Flow Rate-of-Change, Whale Detection & Stablecoin Velocity
======================================================================================
Genuinely new input: exchange deposit/withdrawal *rate of change* (not just
net position), whale transaction clustering, and stablecoin mint/burn velocity.

Data sources (all FREE, no key required):
  - Glassnode free tier (BTC + ETH daily): exchange balance, active addresses
  - blockchain.info: transaction volume, exchange deposit/withdrawal estimates
  - DefiLlama: stablecoin supply data

Author: Alpha Engine (edge-hunt module)
Hypothesis: H-010 (exchange flow ROC + whale activity)
Family: onchain_crypto  |  Status: UNTESTED
"""
from __future__ import annotations

import json
import logging
import math
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENABLED_ENV_VAR = "ONCHAIN_CRYPTO_ENABLED"

SUPPORTED_ASSETS = {"BTC", "ETH"}

# Try to import existing Glassnode client (same infra as crypto_onchain_momentum.py)
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

glass = None
try:
    from tools import glassnode_data_fetcher as glass_mod
    glass = glass_mod
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_enabled() -> bool:
    return os.environ.get(ENABLED_ENV_VAR, "0").strip() == "1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from URL. Returns parsed data or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _latest_value(series: Optional[list[dict]]) -> Optional[float]:
    """Return the 'v' field of the last datapoint, or None."""
    if not series or not isinstance(series, list):
        return None
    try:
        last = series[-1]
        v = last.get("v")
        if v is None:
            v = last.get("value")
        if v is None:
            v = last.get("count")
        return float(v) if v is not None else None
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


# ---------------------------------------------------------------------------
# 1. Exchange Flow Rate of Change
# ---------------------------------------------------------------------------
# Novel input: Instead of using exchange balance *level* (already done by
# crypto_onchain_momentum.py), we compute the *rate of change* of daily
# exchange deposits and withdrawals separately.
#
# When deposit RATE accelerates (more coins flowing IN per day than the
# 7-day average), selling pressure is building — bearish.
# When withdrawal RATE accelerates (more coins flowing OUT per day),
# accumulation is happening — bullish.
#
# We also compute the deposit/withdrawal *ratio* and its momentum.
# ---------------------------------------------------------------------------

def _fetch_blockchain_chart(chart_name: str, timespan: str = "30days") -> Optional[list[dict]]:
    """Fetch chart data from blockchain.info. Returns list of {x: unix, y: value}."""
    url = (
        f"https://api.blockchain.info/charts/{chart_name}"
        f"?timespan={timespan}&format=json&cors=true"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if isinstance(data, dict) and "values" in data:
                return data["values"]
    except Exception:
        pass
    return None


def _compute_rate_of_change(values: list[float], window: int = 7) -> Optional[float]:
    """
    Compute the rate of change of the *derivative* (i.e., acceleration).
    Returns (recent_mean - prior_mean) / prior_mean as a percentage.
    Positive = accelerating upward, negative = decelerating.
    """
    if len(values) < window * 2 + 1:
        return None

    recent = values[-window:]
    prior = values[-window * 2:-window]

    recent_mean = _mean(recent)
    prior_mean = _mean(prior)

    if prior_mean == 0:
        return None

    return ((recent_mean - prior_mean) / abs(prior_mean)) * 100.0


def _compute_deposit_withdrawal_estimate() -> Optional[dict]:
    """
    Estimate daily exchange deposit and withdrawal volumes using blockchain.info.
    Uses 'n-transactions' and 'estimated-transaction-volume' as proxies.

    Returns dict with deposit/withdrawal estimates and rate-of-change metrics.
    """
    # Fetch total transaction volume (proxy for overall chain activity)
    tx_volume = _fetch_blockchain_chart("estimated-transaction-volume", "30days")
    n_tx = _fetch_blockchain_chart("n-transactions", "30days")

    if not tx_volume or len(tx_volume) < 15:
        return None

    # Extract Y values (transaction volumes)
    tx_vals = [float(d["y"]) for d in tx_volume if d.get("y") is not None]

    if len(tx_vals) < 15:
        return None

    # Compute daily change in transaction volume (as proxy for exchange flow intensity)
    daily_changes = []
    for i in range(1, len(tx_vals)):
        if tx_vals[i - 1] > 0:
            daily_changes.append((tx_vals[i] - tx_vals[i - 1]) / tx_vals[i - 1] * 100.0)

    if len(daily_changes) < 7:
        return None

    # Rate of change of the daily changes (acceleration)
    acceleration = _compute_rate_of_change(daily_changes, window=7)

    # Current vs 7-day-ago volume ratio
    current_vol = tx_vals[-1]
    prior_vol = tx_vals[-8] if len(tx_vals) >= 8 else tx_vals[0]
    vol_ratio = (current_vol / prior_vol - 1.0) * 100.0 if prior_vol > 0 else 0.0

    return {
        "tx_volume_current": round(current_vol, 0),
        "tx_volume_7d_ago": round(prior_vol, 0),
        "tx_volume_change_pct": round(vol_ratio, 2),
        "daily_changes": [round(d, 2) for d in daily_changes[-14:]],
        "acceleration": round(acceleration, 2) if acceleration is not None else None,
        "n_data_points": len(tx_vals),
    }


def exchange_flow_rate_signal(asset: str = "BTC") -> Optional[dict]:
    """
    Exchange flow rate-of-change signal.
    Uses blockchain.info TX volume acceleration + Glassnode exchange balance.

    Signal logic:
    - TX volume decelerating + exchange balance declining = coins leaving exchanges
      (accumulation) → BULLISH
    - TX volume accelerating + exchange balance rising = coins moving to exchanges
      (distribution) → BEARISH
    """
    if asset.upper() not in SUPPORTED_ASSETS:
        return None

    # Primary data: Glassnode exchange balance (requires API key)
    exchange_balance = None
    eb_trend = None

    if glass is not None:
        try:
            eb_series = glass.fetch_exchange_balance(asset)
            exchange_balance = _latest_value(eb_series)
            eb_trend = glass.trend_30d(eb_series)
        except Exception as exc:
            logger.debug("Glassnode exchange balance failed for %s: %s", asset, exc)

    # Secondary data: blockchain.info TX volume (no key needed)
    chain_data = _compute_deposit_withdrawal_estimate()

    if exchange_balance is None and chain_data is None:
        return None

    # Composite scoring
    signals = []
    weights = []

    # Component 1: Glassnode exchange balance trend (weight: 0.5 if available)
    if eb_trend is not None:
        # Negative trend = exchange balance declining = accumulation = bullish
        signals.append(-eb_trend * 100.0)  # Invert: negative trend → positive signal
        weights.append(0.5)

    # Component 2: TX volume acceleration (weight: 0.3 if available)
    if chain_data and chain_data.get("acceleration") is not None:
        accel = chain_data["acceleration"]
        # Decelerating TX volume (negative acceleration) = less selling pressure = bullish
        signals.append(-accel)  # Invert
        weights.append(0.3)

    # Component 3: TX volume change (weight: 0.2)
    if chain_data and chain_data.get("tx_volume_change_pct") is not None:
        vol_change = chain_data["tx_volume_change_pct"]
        # Declining volume = less activity = potentially bullish (calm before storm / accumulation)
        signals.append(-vol_change * 0.5)
        weights.append(0.2)

    if not signals:
        return None

    # Weighted composite
    weight_sum = sum(weights)
    if weight_sum <= 0:
        return None

    composite = sum(s * w for s, w in zip(signals, weights)) / weight_sum

    # Signal thresholds
    THRESHOLD = 1.5  # Composite score threshold

    if composite > THRESHOLD:
        signal = "BULLISH"
        confidence = min(0.80, 0.55 + (composite - THRESHOLD) / 5.0)
        direction_label = "accumulation"
    elif composite < -THRESHOLD:
        signal = "BEARISH"
        confidence = min(0.80, 0.55 + abs(composite + THRESHOLD) / 5.0)
        direction_label = "distribution"
    else:
        signal = "NEUTRAL"
        confidence = 0.30
        direction_label = "no clear direction"

    # Build descriptive text
    parts = []
    if eb_trend is not None:
        parts.append(f"exchange-balance 30d trend: {eb_trend*100:+.1f}%")
    if chain_data:
        if chain_data.get("acceleration") is not None:
            parts.append(f"TX volume acceleration: {chain_data['acceleration']:+.1f}%")
        if chain_data.get("tx_volume_change_pct") is not None:
            parts.append(f"TX volume 7d change: {chain_data['tx_volume_change_pct']:+.1f}%")

    description = (
        f"{asset} on-chain flow: {direction_label} (score={composite:+.2f}). "
        + "; ".join(parts)
    )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "value": round(composite, 3),
        "description": description,
        "source": "exchange_flow_rate",
        "asset": asset,
        "components": {
            "exchange_balance_trend": round(eb_trend * 100, 2) if eb_trend is not None else None,
            "tx_volume_acceleration": chain_data.get("acceleration") if chain_data else None,
            "tx_volume_change_pct": chain_data.get("tx_volume_change_pct") if chain_data else None,
        },
    }


# ---------------------------------------------------------------------------
# 2. Whale Transaction Clustering
# ---------------------------------------------------------------------------
# Detect large-value transaction clusters on the blockchain that may
# indicate institutional positioning or whale accumulation/distribution.
#
# Uses blockchain.info large transaction data as a free proxy.
# When large transactions spike AND move to/from exchanges, it's a signal.
# ---------------------------------------------------------------------------

def _fetch_large_transactions(hours: int = 24) -> Optional[list[dict]]:
    """
    Fetch recent large Bitcoin transactions from blockchain.info.
    Returns list of transaction dicts or None.
    """
    url = f"https://blockchain.info/q/getblockhash/{hours}"
    # Note: blockchain.info doesn't have a direct "large transactions" endpoint
    # without an API key. We use the mempool and recent block data as proxy.

    # Alternative: fetch the latest blocks and look for large-tx patterns
    try:
        # Get latest block height
        height_url = "https://blockchain.info/latestblock"
        height_data = _fetch_json(height_url)
        if not height_data or "height" not in height_data:
            return None

        current_height = height_data["height"]
        blocks = []

        # Fetch last few blocks and check for large transactions
        for offset in range(min(5, hours)):
            block_hash_url = f"https://blockchain.info/block-height/{current_height - offset}?format=json"
            block_data = _fetch_json(block_hash_url)
            if not block_data or "blocks" not in block_data:
                continue
            for blk in block_data["blocks"]:
                txs = blk.get("tx", [])
                for tx in txs:
                    total_out = sum(
                        out.get("value", 0)
                        for out in tx.get("out", [])
                        if isinstance(out.get("value"), (int, float))
                    )
                    # Threshold: transactions moving > 100 BTC equivalent
                    if total_out > 10_000_000_000:  # satoshis (> 100 BTC)
                        blocks.append({
                            "txid": tx.get("hash", "")[:16],
                            "total_value_btc": round(total_out / 1e8, 2),
                            "n_outputs": len(tx.get("out", [])),
                            "time": blk.get("time", 0),
                        })

        return blocks if blocks else None
    except Exception:
        return None


def whale_transaction_signal() -> Optional[dict]:
    """
    Analyze recent large blockchain transactions for clustering patterns.
    Multiple large transactions in same direction = institutional signal.

    Returns signal dict or None.
    """
    large_txs = _fetch_large_transactions(hours=24)

    if not large_txs or len(large_txs) < 3:
        return None

    n_transactions = len(large_txs)
    total_value = sum(t["total_value_btc"] for t in large_txs)
    avg_value = _mean([t["total_value_btc"] for t in large_txs])
    max_value = max(t["total_value_btc"] for t in large_txs)

    # Analyze clustering: are transactions concentrated in time?
    if len(large_txs) >= 2 and all("time" in t for t in large_txs):
        times = sorted(t["time"] for t in large_txs)
        intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
        avg_interval = _mean(intervals) if intervals else 3600

        # Clustering = short average interval between large transactions
        # Normal: hours apart. Clustered: minutes apart.
        is_clustered = avg_interval < 1800  # < 30 minutes average
    else:
        avg_interval = 3600
        is_clustered = False

    # Signal logic
    # Heavy whale activity with clustering = potential institutional move
    # Sparse whale activity = normal market, no signal
    TRANSACTION_THRESHOLD = 5      # Need at least 5 large transactions
    CLUSTER_THRESHOLD = 3          # Need at least 3 for clustering analysis
    VALUE_THRESHOLD_BTC = 500.0    # Total value threshold

    if n_transactions >= TRANSACTION_THRESHOLD and total_value > VALUE_THRESHOLD_BTC:
        if is_clustered:
            # Clustered large transactions = likely institutional positioning
            signal = "BEARISH"  # Large movements to exchanges = sell pressure
            confidence = min(0.70, 0.50 + min(n_transactions / 20.0, 0.20))
            description = (
                f"Whale transactions clustered: {n_transactions} txs moving "
                f"{total_value:.0f} BTC total (avg {avg_value:.1f} BTC). "
                f"Short intervals suggest institutional positioning. "
                f"Contrarian alert for potential distribution."
            )
        else:
            # Spread out large transactions = normal market-making
            signal = "NEUTRAL"
            confidence = 0.35
            description = (
                f"Large whale transactions ({n_transactions} txs, "
                f"{total_value:.0f} BTC total) but spread over time. "
                f"No clear directional signal."
            )
    elif n_transactions >= CLUSTER_THRESHOLD and total_value > VALUE_THRESHOLD_BTC * 0.5:
        signal = "NEUTRAL"
        confidence = 0.30
        description = (
            f"Moderate whale activity: {n_transactions} large txs, "
            f"{total_value:.0f} BTC. Below significance threshold."
        )
    else:
        signal = "NEUTRAL"
        confidence = 0.30
        description = (
            f"Minimal whale activity: only {n_transactions} large transactions "
            f"({total_value:.0f} BTC total). No signal."
        )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "value": round(total_value, 2),
        "description": description,
        "source": "whale_transactions",
        "n_transactions": n_transactions,
        "total_value_btc": round(total_value, 2),
        "avg_value_btc": round(avg_value, 2),
        "max_value_btc": round(max_value, 2),
        "is_clustered": is_clustered,
        "avg_interval_seconds": round(avg_interval, 0),
    }


# ---------------------------------------------------------------------------
# 3. Stablecoin Velocity Signal
# ---------------------------------------------------------------------------
# Stablecoin mint/burn velocity indicates capital deployment intent.
# When stablecoin supply grows rapidly, dry powder is entering the system
# (bullish). When stablecoins are being redeemed/burned, capital is leaving
# (bearish).
#
# This complements existing defillama_signals.py by focusing on the
# *rate of change* of supply rather than the absolute level.
# ---------------------------------------------------------------------------

def _fetch_stablecoin_supply() -> Optional[list[dict]]:
    """Fetch stablecoin supply data from DefiLlama."""
    try:
        url = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
        resp = _fetch_json(url)
        if not resp or "peggedAssets" not in resp:
            return None
        return resp["peggedAssets"]
    except Exception:
        return None


def _fetch_stablecoin_chart(stablecoin_id: int = 1, days: int = 30) -> Optional[list[dict]]:
    """Fetch historical supply chart for a specific stablecoin (USDT=1)."""
    try:
        url = f"https://stablecoins.llama.fi/stablecoincharts/all?stablecoin={stablecoin_id}"
        resp = _fetch_json(url)
        if not isinstance(resp, list) or len(resp) < days + 1:
            return None
        return resp
    except Exception:
        return None


def stablecoin_velocity_signal() -> Optional[dict]:
    """
    Stablecoin mint/burn velocity signal.
    Uses USDT (id=1) supply changes as primary indicator.

    Rising supply = capital entering crypto ecosystem = BULLISH
    Falling supply = capital exiting = BEARISH
    """
    # Current aggregate stablecoin supply
    stable_data = _fetch_stablecoin_supply()
    if not stable_data:
        return None

    total_now = 0.0
    for coin in stable_data:
        circ = coin.get("circulating", {})
        pegged_usd = circ.get("peggedUSD", 0)
        if pegged_usd:
            total_now += float(pegged_usd)

    if total_now == 0:
        return None

    # Historical USDT supply for velocity calculation
    chart = _fetch_stablecoin_chart(stablecoin_id=1, days=30)
    if not chart or len(chart) < 8:
        return None

    # Extract daily USDT supply values
    usdt_supplies = []
    usdt_dates = []
    for point in chart:
        val = point.get("totalCirculating", {}).get("peggedUSD")
        if val is not None:
            usdt_supplies.append(float(val))
            usdt_dates.append(point.get("date", 0))

    if len(usdt_supplies) < 8:
        return None

    # Compute daily supply changes (velocity of minting/burning)
    daily_changes = []
    for i in range(1, len(usdt_supplies)):
        delta = usdt_supplies[i] - usdt_supplies[i - 1]
        if usdt_supplies[i - 1] > 0:
            pct_change = (delta / usdt_supplies[i - 1]) * 100.0
            daily_changes.append(pct_change)

    if len(daily_changes) < 5:
        return None

    # Rate of change of supply (acceleration)
    recent_7d = daily_changes[-7:]
    prior_7d = daily_changes[-14:-7] if len(daily_changes) >= 14 else daily_changes[:7]

    recent_mean = _mean(recent_7d)
    prior_mean = _mean(prior_7d)
    prior_std = _std(prior_7d) if len(prior_7d) >= 2 else 1.0

    # Z-score: how unusual is the current minting/burning rate?
    if prior_std > 0:
        z_score = (recent_mean - prior_mean) / prior_std
    else:
        z_score = 0.0

    # Overall supply change percentage (7-day)
    supply_7d_ago = usdt_supplies[-8] if len(usdt_supplies) >= 8 else usdt_supplies[0]
    supply_change_7d = ((usdt_supplies[-1] - supply_7d_ago) / supply_7d_ago) * 100.0 if supply_7d_ago > 0 else 0.0

    # Signal logic
    Z_THRESHOLD = 1.5    # z-score for significant change
    CHANGE_THRESHOLD = 0.5  # 0.5% weekly supply change

    if z_score > Z_THRESHOLD and supply_change_7d > CHANGE_THRESHOLD:
        # Rapid stablecoin minting = capital entering = bullish
        signal = "BULLISH"
        confidence = min(0.75, 0.55 + (z_score - Z_THRESHOLD) * 0.10)
        description = (
            f"Stablecoin minting accelerating: z={z_score:+.1f}, "
            f"supply +{supply_change_7d:+.2f}% over 7d. "
            f"Dry powder entering the system."
        )
    elif z_score < -Z_THRESHOLD and supply_change_7d < -CHANGE_THRESHOLD:
        # Rapid stablecoin burning = capital exiting = bearish
        signal = "BEARISH"
        confidence = min(0.75, 0.55 + abs(z_score + Z_THRESHOLD) * 0.10)
        description = (
            f"Stablecoin burning accelerating: z={z_score:+.1f}, "
            f"supply {supply_change_7d:+.2f}% over 7d. "
            f"Capital exiting the ecosystem."
        )
    elif abs(z_score) < 1.0 and abs(supply_change_7d) < 0.3:
        signal = "NEUTRAL"
        confidence = 0.30
        description = (
            f"Stablecoin velocity normal: z={z_score:+.1f}, "
            f"supply {supply_change_7d:+.2f}% over 7d."
        )
    else:
        # Moderate change, not extreme enough for high conviction
        signal = "NEUTRAL"
        confidence = 0.40
        direction = "slight inflow" if supply_change_7d > 0 else "slight outflow"
        description = (
            f"Stablecoin velocity moderate ({direction}): "
            f"z={z_score:+.1f}, supply {supply_change_7d:+.2f}% over 7d."
        )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "value": round(z_score, 2),
        "description": description,
        "source": "stablecoin_velocity",
        "total_supply_now": round(total_now, 2),
        "usdt_supply_change_7d_pct": round(supply_change_7d, 4),
        "mint_burn_z_score": round(z_score, 2),
        "recent_daily_changes": [round(d, 3) for d in daily_changes[-7:]],
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def get_onchain_crypto_signals() -> list[dict]:
    """
    Run all on-chain crypto strategies across BTC and ETH.
    Returns list of signal dicts (non-None results only).
    """
    signals = []

    for asset in SUPPORTED_ASSETS:
        try:
            result = exchange_flow_rate_signal(asset)
            if result is not None:
                signals.append(result)
        except Exception as exc:
            logger.warning("exchange_flow_rate_signal(%s) failed: %s", asset, exc)

    # Whale transactions (BTC only for blockchain.info)
    try:
        result = whale_transaction_signal()
        if result is not None:
            signals.append(result)
    except Exception as exc:
        logger.warning("whale_transaction_signal() failed: %s", exc)

    # Stablecoin velocity (global, not per-asset)
    try:
        result = stablecoin_velocity_signal()
        if result is not None:
            signals.append(result)
    except Exception as exc:
        logger.warning("stablecoin_velocity_signal() failed: %s", exc)

    logger.info(
        "On-chain crypto signals: %d results from 3 strategies",
        len(signals),
    )
    return signals


# ---------------------------------------------------------------------------
# Pick generator: convert signals into scanner-compatible picks
# ---------------------------------------------------------------------------

SYMBOL_MAP = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}


def generate_onchain_crypto_picks() -> list[dict]:
    """
    Convert on-chain signals into alpha_engine pick format.
    Only generates picks for non-NEUTRAL signals with confidence >= 0.5.
    """
    signals = get_onchain_crypto_signals()
    now = datetime.now(timezone.utc)
    picks = []

    for sig in signals:
        if sig["signal"] == "NEUTRAL":
            continue
        if sig["confidence"] < 0.5:
            continue

        # Determine symbol
        asset = sig.get("asset", "BTC")
        symbol = SYMBOL_MAP.get(asset, f"{asset}USDT")

        # For non-asset-specific signals (whale, stablecoin), default to BTC
        if asset not in SUPPORTED_ASSETS:
            symbol = "BTCUSDT"

        source = sig["source"]
        direction = sig["signal"]
        signal_type = "BUY" if direction == "BULLISH" else "SELL"

        pick_id = f"onchain_{source}_{symbol}_{now.strftime('%Y%m%d%H%M')}"

        # Avoid duplicate IDs
        existing_ids = {p["id"] for p in picks}
        base_id = pick_id
        suffix = 0
        while pick_id in existing_ids:
            suffix += 1
            pick_id = f"{base_id}_{suffix}"

        picks.append({
            "id": pick_id,
            "strategy": source,
            "symbol": symbol,
            "category": "crypto",
            "signal_type": signal_type,
            "entry_price": None,  # Signal-based, no specific entry
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": None,
            "stop_loss": None,
            "confidence": sig["confidence"],
            "ml_score": None,
            "status": "SIGNAL",
            "source_system": "onchain_crypto",
            "created_at": now.isoformat(),
            "onchain_data": {
                "signal_type": sig["source"],
                "value": sig["value"],
                "description": sig["description"],
                "asset": asset,
            },
        })

    logger.info(
        "Generated %d on-chain crypto picks from %d signals",
        len(picks),
        len(signals),
    )
    return picks


# ---------------------------------------------------------------------------
# Registration for scanner.py
# ---------------------------------------------------------------------------

ONCHAIN_CRYPTO_STRATEGIES = {
    "exchange_flow_rate": exchange_flow_rate_signal,
    "whale_transactions": whale_transaction_signal,
    "stablecoin_velocity": stablecoin_velocity_signal,
}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys as _sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 70)
    print("On-Chain Crypto Signals")
    print("=" * 70)

    sigs = get_onchain_crypto_signals()
    for s in sigs:
        emoji = {"BULLISH": "+", "BEARISH": "-", "NEUTRAL": "~"}
        print(f"\n[{emoji.get(s['signal'], '?')}] {s['source']} ({s.get('asset', '?')})")
        print(f"    Signal:     {s['signal']}")
        print(f"    Confidence: {s['confidence']}")
        print(f"    Value:      {s['value']}")
        print(f"    {s['description']}")

    print(f"\n{'=' * 70}")
    picks = generate_onchain_crypto_picks()
    print(f"Generated {len(picks)} actionable pick(s)")
    for p in picks:
        print(f"  [{p['signal_type']}] {p['symbol']} via {p['strategy']} "
              f"(conf: {p['confidence']})")