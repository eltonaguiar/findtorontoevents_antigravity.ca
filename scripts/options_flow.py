#!/usr/bin/env python3
"""
Options Flow & Gamma Exposure (GEX) Analyzer — The best free leading indicator.

Options flow is the single best leading indicator for stock prices:
  - When someone buys $10M in NVDA calls, the dealer buys shares to hedge → price up
  - Gamma Exposure (GEX) predicts support/resistance better than technicals
  - Put/Call ratio extremes predict reversals
  - Unusual options activity signals institutional positioning

Data source: Yahoo Finance options chains (free, no API key)

Pipeline:
  1. Fetch options chains for tracked tickers via yfinance
  2. Compute GEX (Gamma Exposure) per ticker
  3. Compute put/call ratios and unusual activity
  4. Identify key gamma levels (support/resistance)
  5. Post to world_class_intelligence.php for signal modulation

Requires: pip install yfinance numpy pandas requests
Runs via: python run_all.py --options
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, post_to_bridge, safe_request
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS

logger = logging.getLogger('options_flow')

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    logger.warning("yfinance not installed: pip install yfinance")


# ---------------------------------------------------------------------------
# Gamma Exposure (GEX) Computation
# ---------------------------------------------------------------------------

def compute_gex(ticker):
    """
    Calculate Gamma Exposure (GEX) from options chain.

    GEX = sum(Gamma × OpenInterest × 100 × SpotPrice²) for all strikes
    - Calls contribute positive gamma (dealers long gamma → dampen moves)
    - Puts contribute negative gamma (dealers short gamma → amplify moves)

    Positive total GEX → market is "pinned" (support)
    Negative total GEX → market is "volatile" (amplified moves)

    Returns dict with GEX metrics or None on failure.
    """
    if not YF_AVAILABLE:
        return None

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            logger.warning("  No options data for %s", ticker)
            return None

        # Use next 4 expiry dates (near-term most impactful)
        near_exps = expirations[:4]

        # Get spot price
        hist = stock.history(period='1d')
        if hist.empty:
            return None
        spot = float(hist['Close'].iloc[-1])

        if spot <= 0:
            return None

        total_call_gex = 0.0
        total_put_gex = 0.0
        total_call_oi = 0
        total_put_oi = 0
        total_call_volume = 0
        total_put_volume = 0
        strike_gex = {}  # GEX per strike for finding key levels
        unusual_activity = []

        for exp in near_exps:
            try:
                chain = stock.option_chain(exp)
            except Exception:
                continue

            calls = chain.calls
            puts = chain.puts

            # Call GEX (positive — dealers are long gamma on calls they sold)
            if not calls.empty and 'gamma' in calls.columns:
                valid_calls = calls.dropna(subset=['gamma', 'openInterest'])
                for _, row in valid_calls.iterrows():
                    gamma = float(row.get('gamma', 0))
                    oi = int(row.get('openInterest', 0))
                    vol = int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0
                    strike = float(row.get('strike', 0))

                    gex = gamma * oi * 100 * spot * spot
                    total_call_gex += gex
                    total_call_oi += oi
                    total_call_volume += vol

                    # Track per-strike GEX
                    strike_key = round(strike, 2)
                    strike_gex[strike_key] = strike_gex.get(strike_key, 0) + gex

                    # Unusual activity: volume > 5x open interest
                    if oi > 100 and vol > oi * 5:
                        unusual_activity.append({
                            'type': 'CALL',
                            'strike': strike,
                            'expiry': exp,
                            'volume': vol,
                            'oi': oi,
                            'vol_oi_ratio': round(vol / max(oi, 1), 1)
                        })

            # Put GEX (negative — dealers are short gamma on puts they sold)
            if not puts.empty and 'gamma' in puts.columns:
                valid_puts = puts.dropna(subset=['gamma', 'openInterest'])
                for _, row in valid_puts.iterrows():
                    gamma = float(row.get('gamma', 0))
                    oi = int(row.get('openInterest', 0))
                    vol = int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0
                    strike = float(row.get('strike', 0))

                    gex = -gamma * oi * 100 * spot * spot  # Negative for puts
                    total_put_gex += gex
                    total_put_oi += oi
                    total_put_volume += vol

                    strike_key = round(strike, 2)
                    strike_gex[strike_key] = strike_gex.get(strike_key, 0) + gex

                    if oi > 100 and vol > oi * 5:
                        unusual_activity.append({
                            'type': 'PUT',
                            'strike': strike,
                            'expiry': exp,
                            'volume': vol,
                            'oi': oi,
                            'vol_oi_ratio': round(vol / max(oi, 1), 1)
                        })

        # Total GEX
        net_gex = total_call_gex + total_put_gex

        # Put/Call ratios
        pc_oi_ratio = total_put_oi / max(total_call_oi, 1)
        pc_vol_ratio = total_put_volume / max(total_call_volume, 1)

        # Find key gamma levels (highest absolute GEX strikes)
        sorted_strikes = sorted(strike_gex.items(), key=lambda x: abs(x[1]), reverse=True)
        key_levels = []
        for strike, gex_val in sorted_strikes[:5]:
            level_type = 'SUPPORT' if gex_val > 0 else 'RESISTANCE'
            key_levels.append({
                'strike': strike,
                'gex': round(gex_val, 0),
                'type': level_type,
                'distance_pct': round((strike - spot) / spot * 100, 2)
            })

        # GEX signal interpretation
        if net_gex > 0:
            gex_signal = 'POSITIVE_GAMMA'
            gex_interpretation = 'Dealers long gamma — market dampened, expect mean reversion'
        else:
            gex_signal = 'NEGATIVE_GAMMA'
            gex_interpretation = 'Dealers short gamma — market amplified, expect larger moves'

        # P/C ratio signal
        if pc_oi_ratio > 1.5:
            pcr_signal = 'EXTREME_PUTS'
            pcr_interpretation = 'Heavy put buying — contrarian bullish signal'
        elif pc_oi_ratio < 0.5:
            pcr_signal = 'EXTREME_CALLS'
            pcr_interpretation = 'Heavy call buying — contrarian bearish signal'
        else:
            pcr_signal = 'NEUTRAL'
            pcr_interpretation = 'Normal put/call ratio'

        return {
            'ticker': ticker,
            'spot_price': round(spot, 2),
            'net_gex': round(net_gex, 0),
            'call_gex': round(total_call_gex, 0),
            'put_gex': round(total_put_gex, 0),
            'gex_signal': gex_signal,
            'gex_interpretation': gex_interpretation,
            'pc_oi_ratio': round(pc_oi_ratio, 3),
            'pc_vol_ratio': round(pc_vol_ratio, 3),
            'pcr_signal': pcr_signal,
            'pcr_interpretation': pcr_interpretation,
            'total_call_oi': total_call_oi,
            'total_put_oi': total_put_oi,
            'total_call_volume': total_call_volume,
            'total_put_volume': total_put_volume,
            'key_gamma_levels': key_levels,
            'unusual_activity': unusual_activity[:10],
            'expirations_analyzed': len(near_exps),
            'computed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.warning("  GEX computation failed for %s: %s", ticker, e)
        return None


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    """Run options flow analysis for all tracked tickers."""
    logger.info("=" * 60)
    logger.info("OPTIONS FLOW & GEX ANALYZER — Starting")
    logger.info("=" * 60)

    if not YF_AVAILABLE:
        logger.error("yfinance not installed. Run: pip install yfinance")
        return []

    all_results = []

    for ticker in TRACKED_TICKERS:
        logger.info("  Analyzing %s options...", ticker)
        result = compute_gex(ticker)

        if result is None:
            logger.info("    No options data available")
            continue

        all_results.append(result)

        # Log summary
        gex_emoji = '+' if result['net_gex'] > 0 else '-'
        logger.info("    [%s] GEX=%s | P/C=%.2f (%s) | %d unusual | %d key levels",
                     gex_emoji,
                     f"{result['net_gex']:,.0f}",
                     result['pc_oi_ratio'],
                     result['pcr_signal'],
                     len(result['unusual_activity']),
                     len(result['key_gamma_levels']))

        # Log unusual activity
        for ua in result['unusual_activity'][:3]:
            logger.info("      UNUSUAL: %s $%.0f %s — vol=%d, OI=%d (%.1fx)",
                         ua['type'], ua['strike'], ua['expiry'],
                         ua['volume'], ua['oi'], ua['vol_oi_ratio'])

    # Post to API
    if all_results:
        api_result = post_to_api('ingest_regime', {
            'source': 'options_flow',
            'options_data': all_results,
            'computed_at': datetime.utcnow().isoformat(),
            'tickers_analyzed': len(all_results)
        })

        if api_result.get('ok'):
            logger.info("Options flow data posted to API")
        else:
            logger.warning("API post error: %s", api_result.get('error', 'unknown'))

    # Post to bridge dashboard
    if all_results:
        post_to_bridge('options_flow', {'options_data': all_results},
                       "%d tickers analyzed" % len(all_results))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("OPTIONS FLOW SUMMARY")
    logger.info("  Tickers analyzed: %d", len(all_results))

    pos_gamma = [r for r in all_results if r['gex_signal'] == 'POSITIVE_GAMMA']
    neg_gamma = [r for r in all_results if r['gex_signal'] == 'NEGATIVE_GAMMA']
    extreme_puts = [r for r in all_results if r['pcr_signal'] == 'EXTREME_PUTS']
    extreme_calls = [r for r in all_results if r['pcr_signal'] == 'EXTREME_CALLS']

    if pos_gamma:
        logger.info("  POSITIVE GAMMA (dampened): %s",
                     ', '.join(r['ticker'] for r in pos_gamma))
    if neg_gamma:
        logger.info("  NEGATIVE GAMMA (amplified): %s",
                     ', '.join(r['ticker'] for r in neg_gamma))
    if extreme_puts:
        logger.info("  EXTREME PUTS (contrarian bullish): %s",
                     ', '.join(r['ticker'] for r in extreme_puts))
    if extreme_calls:
        logger.info("  EXTREME CALLS (contrarian bearish): %s",
                     ', '.join(r['ticker'] for r in extreme_calls))

    total_unusual = sum(len(r['unusual_activity']) for r in all_results)
    logger.info("  Total unusual activity alerts: %d", total_unusual)
    logger.info("=" * 60)

    return all_results


if __name__ == '__main__':
    main()
