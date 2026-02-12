#!/usr/bin/env python3
"""
On-Chain Analytics — Crypto leading indicators from blockchain data.

Tracks metrics that lead price by hours to days:
  - BTC hash rate & mempool (network health)
  - DeFi TVL changes (money flowing in/out of DeFi)
  - Stablecoin supply (buying power indicator)
  - Exchange reserve estimates (selling pressure)

Free data sources (no API keys for basic metrics):
  - Blockchain.com API: https://blockchain.info/q/
  - DeFi Llama: https://api.llama.fi/
  - Stablecoins: https://stablecoins.llama.fi/

Pipeline:
  1. Fetch on-chain metrics from free APIs
  2. Compute signals (bullish/bearish/neutral)
  3. Post to world_class_intelligence.php for crypto signal modulation

Requires: pip install requests numpy
Runs via: python run_all.py --onchain
"""
import sys
import os
import json
import logging
import numpy as np
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, safe_request
from config import API_BASE, ADMIN_KEY

logger = logging.getLogger('onchain_analytics')


# ---------------------------------------------------------------------------
# Blockchain.com — BTC Network Metrics
# ---------------------------------------------------------------------------

def fetch_btc_network():
    """Fetch BTC network health metrics from Blockchain.com (free, no key)."""
    metrics = {}

    endpoints = {
        'hash_rate': 'https://blockchain.info/q/hashrate',
        'difficulty': 'https://blockchain.info/q/getdifficulty',
        'block_count': 'https://blockchain.info/q/getblockcount',
        'unconfirmed_tx': 'https://blockchain.info/q/unconfirmedcount',
        'market_price': 'https://blockchain.info/q/24hrprice',
        'total_btc': 'https://blockchain.info/q/totalbc',
    }

    for name, url in endpoints.items():
        resp = safe_request(url, timeout=10)
        if resp is not None:
            try:
                val = float(resp.text.strip())
                metrics[name] = val
            except (ValueError, TypeError):
                logger.warning("  Failed to parse %s: %s", name, resp.text[:50])

    if metrics:
        logger.info("  BTC Network: hash_rate=%.0f, unconfirmed=%d, price=$%.0f",
                     metrics.get('hash_rate', 0),
                     metrics.get('unconfirmed_tx', 0),
                     metrics.get('market_price', 0))

    return metrics


# ---------------------------------------------------------------------------
# DeFi Llama — TVL Data
# ---------------------------------------------------------------------------

def fetch_defi_tvl():
    """Fetch DeFi Total Value Locked from DeFi Llama (free, no key)."""
    resp = safe_request("https://api.llama.fi/v2/historicalChainTvl", timeout=15)
    if resp is None:
        return {}

    try:
        data = resp.json()
        if not data or len(data) < 8:
            return {}

        current_tvl = data[-1].get('tvl', 0)
        day_ago_tvl = data[-2].get('tvl', current_tvl) if len(data) > 1 else current_tvl
        week_ago_tvl = data[-8].get('tvl', current_tvl) if len(data) > 7 else current_tvl
        month_ago_tvl = data[-31].get('tvl', current_tvl) if len(data) > 30 else current_tvl

        tvl_1d_change = (current_tvl - day_ago_tvl) / max(day_ago_tvl, 1) * 100
        tvl_7d_change = (current_tvl - week_ago_tvl) / max(week_ago_tvl, 1) * 100
        tvl_30d_change = (current_tvl - month_ago_tvl) / max(month_ago_tvl, 1) * 100

        result = {
            'total_tvl': round(current_tvl, 0),
            'tvl_1d_change_pct': round(tvl_1d_change, 2),
            'tvl_7d_change_pct': round(tvl_7d_change, 2),
            'tvl_30d_change_pct': round(tvl_30d_change, 2),
        }

        logger.info("  DeFi TVL: $%.1fB | 1d: %+.1f%% | 7d: %+.1f%% | 30d: %+.1f%%",
                     current_tvl / 1e9, tvl_1d_change, tvl_7d_change, tvl_30d_change)

        return result

    except Exception as e:
        logger.warning("  DeFi TVL fetch failed: %s", e)
        return {}


def fetch_chain_tvls():
    """Fetch TVL per chain to detect rotation."""
    resp = safe_request("https://api.llama.fi/v2/chains", timeout=15)
    if resp is None:
        return []

    try:
        chains = resp.json()
        top_chains = []
        for chain in sorted(chains, key=lambda x: x.get('tvl', 0), reverse=True)[:10]:
            top_chains.append({
                'name': chain.get('name', ''),
                'tvl': round(chain.get('tvl', 0), 0),
                'tokenSymbol': chain.get('tokenSymbol', ''),
            })

        if top_chains:
            logger.info("  Top chains: %s",
                         ', '.join(f"{c['name']}=${c['tvl']/1e9:.1f}B" for c in top_chains[:5]))

        return top_chains

    except Exception as e:
        logger.warning("  Chain TVL fetch failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Stablecoin Supply — Buying Power Indicator
# ---------------------------------------------------------------------------

def fetch_stablecoin_supply():
    """
    Fetch stablecoin market cap from DeFi Llama.
    Rising stablecoin supply = more buying power waiting on sidelines.
    """
    resp = safe_request("https://stablecoins.llama.fi/stablecoins?includePrices=true", timeout=15)
    if resp is None:
        return {}

    try:
        data = resp.json()
        assets = data.get('peggedAssets', [])

        total_mcap = 0
        top_stables = []

        for asset in assets:
            circ = asset.get('circulating', {})
            mcap = circ.get('peggedUSD', 0) if isinstance(circ, dict) else 0
            if mcap > 0:
                total_mcap += mcap
                if mcap > 1e9:  # Only track >$1B stablecoins
                    top_stables.append({
                        'name': asset.get('name', ''),
                        'symbol': asset.get('symbol', ''),
                        'mcap': round(mcap, 0),
                    })

        top_stables.sort(key=lambda x: x['mcap'], reverse=True)

        result = {
            'total_stablecoin_mcap': round(total_mcap, 0),
            'top_stablecoins': top_stables[:5],
        }

        logger.info("  Stablecoin supply: $%.1fB total", total_mcap / 1e9)
        for s in top_stables[:3]:
            logger.info("    %s (%s): $%.1fB", s['name'], s['symbol'], s['mcap'] / 1e9)

        return result

    except Exception as e:
        logger.warning("  Stablecoin fetch failed: %s", e)
        return {}


# ---------------------------------------------------------------------------
# DeFi Protocol Yields — Smart Money Flow
# ---------------------------------------------------------------------------

def fetch_top_yields():
    """Fetch top DeFi yields to detect where smart money is flowing."""
    resp = safe_request("https://yields.llama.fi/pools", timeout=15)
    if resp is None:
        return []

    try:
        data = resp.json()
        pools = data.get('data', [])

        # Filter: TVL > $10M, APY > 5%, stablecoin or major token
        quality_pools = []
        for pool in pools:
            tvl = pool.get('tvlUsd', 0)
            apy = pool.get('apy', 0)
            if tvl > 10_000_000 and apy and 5 < apy < 100:
                quality_pools.append({
                    'pool': pool.get('pool', ''),
                    'chain': pool.get('chain', ''),
                    'project': pool.get('project', ''),
                    'symbol': pool.get('symbol', ''),
                    'tvl': round(tvl, 0),
                    'apy': round(apy, 2),
                })

        quality_pools.sort(key=lambda x: x['tvl'], reverse=True)

        if quality_pools:
            logger.info("  Top DeFi yields (TVL>$10M):")
            for p in quality_pools[:5]:
                logger.info("    %s on %s: %.1f%% APY ($%.0fM TVL)",
                             p['symbol'], p['chain'], p['apy'], p['tvl'] / 1e6)

        return quality_pools[:20]

    except Exception as e:
        logger.warning("  Yield fetch failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Signal Generation
# ---------------------------------------------------------------------------

def generate_onchain_signals(btc_network, defi_tvl, stablecoin, chain_tvls):
    """
    Generate trading signals from on-chain data.

    Signals:
    1. TVL_RISING + STABLECOIN_RISING → Bullish (money flowing in)
    2. TVL_FALLING + STABLECOIN_FALLING → Bearish (money flowing out)
    3. HIGH_MEMPOOL → Network congestion, possible volatility
    4. HASH_RATE_DROP → Miner capitulation, possible bottom
    """
    signals = []

    # DeFi TVL signals
    tvl_7d = defi_tvl.get('tvl_7d_change_pct', 0)
    if tvl_7d > 5:
        signals.append({
            'signal_type': 'TVL_SURGING',
            'direction': 'BULLISH',
            'strength': min(80, 50 + int(tvl_7d * 2)),
            'description': f"DeFi TVL up {tvl_7d:.1f}% in 7 days — money flowing into crypto",
        })
    elif tvl_7d < -5:
        signals.append({
            'signal_type': 'TVL_DROPPING',
            'direction': 'BEARISH',
            'strength': min(80, 50 + int(abs(tvl_7d) * 2)),
            'description': f"DeFi TVL down {abs(tvl_7d):.1f}% in 7 days — money leaving crypto",
        })

    # Mempool congestion
    unconfirmed = btc_network.get('unconfirmed_tx', 0)
    if unconfirmed > 200000:
        signals.append({
            'signal_type': 'HIGH_MEMPOOL',
            'direction': 'VOLATILE',
            'strength': 60,
            'description': f"BTC mempool congested ({unconfirmed:,} unconfirmed) — expect volatility",
        })

    return signals


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    """Run on-chain analytics pipeline."""
    logger.info("=" * 60)
    logger.info("ON-CHAIN ANALYTICS — Starting")
    logger.info("=" * 60)

    # Fetch all data sources
    logger.info("")
    logger.info("--- BTC Network Metrics ---")
    btc_network = fetch_btc_network()

    logger.info("")
    logger.info("--- DeFi TVL ---")
    defi_tvl = fetch_defi_tvl()

    logger.info("")
    logger.info("--- Chain TVLs ---")
    chain_tvls = fetch_chain_tvls()

    logger.info("")
    logger.info("--- Stablecoin Supply ---")
    stablecoin = fetch_stablecoin_supply()

    logger.info("")
    logger.info("--- Top DeFi Yields ---")
    top_yields = fetch_top_yields()

    # Generate signals
    signals = generate_onchain_signals(btc_network, defi_tvl, stablecoin, chain_tvls)

    # Post to API
    payload = {
        'source': 'onchain_analytics',
        'btc_network': btc_network,
        'defi_tvl': defi_tvl,
        'stablecoin_supply': stablecoin,
        'chain_tvls': chain_tvls,
        'top_yields': top_yields[:10],
        'signals': signals,
        'computed_at': datetime.utcnow().isoformat(),
    }

    api_result = post_to_api('ingest_regime', payload)
    if api_result.get('ok'):
        logger.info("On-chain data posted to API")
    else:
        logger.warning("API post error: %s", api_result.get('error', 'unknown'))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("ON-CHAIN ANALYTICS SUMMARY")
    logger.info("  BTC price: $%s", f"{btc_network.get('market_price', 0):,.0f}")
    logger.info("  DeFi TVL: $%.1fB (7d: %+.1f%%)",
                 defi_tvl.get('total_tvl', 0) / 1e9,
                 defi_tvl.get('tvl_7d_change_pct', 0))
    logger.info("  Stablecoin supply: $%.1fB",
                 stablecoin.get('total_stablecoin_mcap', 0) / 1e9)
    logger.info("  Signals: %d", len(signals))
    for sig in signals:
        logger.info("    [%s] %s (strength=%d)", sig['direction'], sig['signal_type'], sig['strength'])
    logger.info("=" * 60)

    return payload


if __name__ == '__main__':
    main()
