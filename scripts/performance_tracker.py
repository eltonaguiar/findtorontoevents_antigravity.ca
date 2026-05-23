#!/usr/bin/env python3
"""
Performance Tracker — Tracks and updates signal performance over time.

For each signal in lm_signal_performance:
  - If signal_date is 7+ days ago and price_7d is still 0: fetch and update 7-day price
  - If signal_date is 30+ days ago and price_30d is still 0: fetch and update 30-day price
  - If signal_date is 90+ days ago and price_90d is still 0: fetch and update 90-day price

This script delegates most work to the PHP API (track_performance action).
As a fallback, it can also fetch current prices via Finnhub and compute returns.
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FINNHUB_API_KEY, TRACKED_TICKERS, API_BASE, ADMIN_KEY
from utils import call_api, post_to_api, safe_request

logger = logging.getLogger('performance_tracker')


def fetch_current_price(ticker):
    """
    Fetch current price for a ticker from Finnhub.
    Returns price as float, or None on failure.
    """
    if not FINNHUB_API_KEY:
        return None

    url = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}'
    resp = safe_request(url, retries=2, timeout=15)
    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            price = data.get('c', 0)  # 'c' = current price
            if price and price > 0:
                return float(price)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    return None


def track_via_api():
    """
    Try the PHP-side track_performance action.
    This is the preferred method — the PHP side handles DB queries and updates.
    """
    logger.info("Calling PHP track_performance action...")
    result = call_api('track_performance')

    if result.get('ok'):
        updated = result.get('updated', 0)
        pending = result.get('pending', 0)
        logger.info(f"PHP track_performance succeeded: {updated} signals updated, {pending} still pending")
        return result
    else:
        error = result.get('error', 'unknown')
        logger.info(f"PHP track_performance not available or failed: {error}")
        return None


def track_manually():
    """
    Fallback: Manually fetch signals needing price updates and update them.
    Uses the get_pending_signals + update_signal_price API pattern.
    """
    logger.info("Attempting manual performance tracking...")

    # Get signals that need updating
    result = call_api('pending_signals')
    if not result.get('ok'):
        # Try alternative action name
        result = call_api('signals_needing_update')

    if not result.get('ok') or not result.get('signals'):
        logger.info("No pending signals to update (or API action not available)")
        return {'updated': 0, 'skipped': 0}

    signals = result['signals']
    logger.info(f"Found {len(signals)} signals needing price updates")

    updated_count = 0
    skipped_count = 0
    now = datetime.utcnow()

    for signal in signals:
        ticker = signal.get('ticker', '')
        signal_date_str = signal.get('signal_date', '')
        entry_price = float(signal.get('entry_price', 0))
        signal_source = signal.get('signal_source', '')
        signal_id = signal.get('id', '')

        if not ticker or not signal_date_str or entry_price <= 0:
            skipped_count += 1
            continue

        try:
            signal_date = datetime.strptime(signal_date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            skipped_count += 1
            continue

        days_elapsed = (now - signal_date).days

        # Determine which price fields need updating
        needs_7d = days_elapsed >= 7 and float(signal.get('price_7d', 0)) == 0
        needs_30d = days_elapsed >= 30 and float(signal.get('price_30d', 0)) == 0
        needs_90d = days_elapsed >= 90 and float(signal.get('price_90d', 0)) == 0

        if not (needs_7d or needs_30d or needs_90d):
            continue

        # Fetch current price
        current_price = fetch_current_price(ticker)
        if current_price is None:
            logger.debug(f"Could not fetch price for {ticker}")
            skipped_count += 1
            continue

        # Calculate returns
        update_data = {
            'signal_id': signal_id,
            'ticker': ticker,
            'signal_source': signal_source,
            'signal_date': signal_date_str,
        }

        if needs_7d:
            return_7d = ((current_price - entry_price) / entry_price) * 100
            update_data['price_7d'] = current_price
            update_data['return_7d'] = round(return_7d, 2)

        if needs_30d:
            return_30d = ((current_price - entry_price) / entry_price) * 100
            update_data['price_30d'] = current_price
            update_data['return_30d'] = round(return_30d, 2)

        if needs_90d:
            return_90d = ((current_price - entry_price) / entry_price) * 100
            update_data['price_90d'] = current_price
            update_data['return_90d'] = round(return_90d, 2)

        # POST update
        api_result = post_to_api('update_signal_price', update_data)
        if api_result.get('ok'):
            updated_count += 1
            logger.debug(f"Updated {ticker} signal from {signal_date_str}: price={current_price}")
        else:
            skipped_count += 1

    return {'updated': updated_count, 'skipped': skipped_count}


def get_performance_summary():
    """
    Fetch performance summary per signal source from the API.
    """
    logger.info("Fetching performance summary...")

    result = call_api('performance_summary')
    if not result.get('ok'):
        # Try alternative action
        result = call_api('signal_performance')

    if result.get('ok'):
        summary = result.get('summary', result.get('sources', []))
        if isinstance(summary, list) and summary:
            logger.info("Performance by signal source:")
            logger.info(
                f"  {'Source':25s} | {'Signals':>8s} | {'Win Rate':>8s} | "
                f"{'Avg 7d':>8s} | {'Avg 30d':>8s}"
            )
            logger.info(f"  {'-'*25}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")
            for src in summary:
                logger.info(
                    f"  {src.get('signal_source', '?'):25s} | "
                    f"{src.get('total_signals', 0):8d} | "
                    f"{src.get('win_rate_7d', 0):7.1f}% | "
                    f"{src.get('avg_return_7d', 0):+7.2f}% | "
                    f"{src.get('avg_return_30d', 0):+7.2f}%"
                )
        elif isinstance(summary, dict):
            for source, data in summary.items():
                logger.info(f"  {source}: {json.dumps(data)[:200]}")
        else:
            logger.info(f"Performance result: {json.dumps(result)[:500]}")
    else:
        logger.info(f"Performance summary not available: {result.get('error', 'unknown')}")

    return result


def main():
    """Main entry point for performance tracking."""
    logger.info("=" * 60)
    logger.info("Performance Tracker — Starting")
    logger.info("=" * 60)

    # Step 1: Try PHP-side tracking first (preferred)
    api_result = track_via_api()

    # Step 2: If PHP action not available, try manual tracking
    if api_result is None:
        logger.info("Falling back to manual price tracking...")
        manual_result = track_manually()
        logger.info(
            f"Manual tracking: updated={manual_result['updated']}, "
            f"skipped={manual_result['skipped']}"
        )

    # Step 3: Get and log performance summary
    summary = get_performance_summary()

    # Summary
    logger.info("=" * 60)
    logger.info("PERFORMANCE TRACKER SUMMARY")
    if api_result and api_result.get('ok'):
        logger.info(f"  PHP tracking: {api_result.get('updated', 0)} signals updated")
    elif api_result is None:
        logger.info("  PHP tracking: not available (used manual fallback)")
    else:
        logger.info(f"  PHP tracking: failed ({api_result.get('error', 'unknown')})")

    if FINNHUB_API_KEY:
        logger.info("  Finnhub API: available for price lookups")
    else:
        logger.info("  Finnhub API: not configured (FINNHUB_API_KEY not set)")

    logger.info("=" * 60)

    return {
        'api_result': api_result,
        'summary': summary,
    }


if __name__ == '__main__':
    main()
