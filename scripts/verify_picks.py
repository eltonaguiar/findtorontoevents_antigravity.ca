#!/usr/bin/env python3
"""
Pick Verifier — Resolves pending picks in pick-performance.json against real prices.

For each pending pick:
  1. Fetches current price via yfinance (free, no API key)
  2. Computes return since simulated entry
  3. Checks stop-loss and timeframe-based exit
  4. Marks as WIN / LOSS / STOPPED_OUT / EXPIRED
  5. Computes aggregate out-of-sample performance metrics (Sharpe, WR, etc.)

This is the missing link that enables measuring REAL out-of-sample performance
rather than just backtest results.

Usage:
  python verify_picks.py                    # Verify all pending picks
  python verify_picks.py --dry-run          # Preview without updating file
  python verify_picks.py --force            # Re-verify already resolved picks
"""
import os
import sys
import json
import math
import argparse
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('verify_picks')

PICKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'pick-performance.json')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Timeframe mapping (pick timeframe -> days to evaluate)
TIMEFRAME_DAYS = {
    '1d': 1,
    '3d': 3,
    '5d': 5,
    '1w': 7,
    '2w': 14,
    '1m': 30,
    '3m': 90,
}
DEFAULT_HOLD_DAYS = 5  # Default if timeframe not recognized


def fetch_price_yfinance(symbol):
    """Fetch current price for a symbol using yfinance (free, no API key)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except Exception as e:
        logger.debug("yfinance failed for %s: %s", symbol, e)
        return None


def fetch_price_at_date(symbol, target_date):
    """Fetch the closing price at or near a specific date."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        # Fetch a window around the target date
        start = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
        end = (target_date + timedelta(days=5)).strftime('%Y-%m-%d')
        hist = ticker.history(start=start, end=end)
        if hist.empty:
            return None
        # Find closest date <= target_date
        hist.index = hist.index.tz_localize(None)
        valid = hist[hist.index <= target_date]
        if not valid.empty:
            return float(valid['Close'].iloc[-1])
        return float(hist['Close'].iloc[0])
    except Exception as e:
        logger.debug("yfinance date lookup failed for %s: %s", symbol, e)
        return None


def resolve_pick(pick, now, force=False):
    """
    Resolve a single pick: determine if it's WIN, LOSS, STOPPED_OUT, or EXPIRED.

    Returns updated pick dict (or None if no changes needed).
    """
    status = pick.get('status', 'PENDING')
    if status != 'PENDING' and not force:
        return None  # Already resolved

    symbol = pick.get('symbol', '')
    if not symbol:
        return None

    entry_price = pick.get('simulatedEntryPrice', pick.get('price', 0))
    if entry_price <= 0:
        return None

    stop_loss = pick.get('stopLoss', 0)
    timeframe = pick.get('timeframe', '5d')
    picked_at_str = pick.get('pickedAt', '')

    # Parse pick date
    try:
        picked_at = datetime.fromisoformat(picked_at_str.replace('Z', '+00:00'))
        picked_at = picked_at.replace(tzinfo=None)
    except (ValueError, AttributeError):
        logger.warning("Cannot parse pickedAt for %s: %s", symbol, picked_at_str)
        return None

    # Determine evaluation window
    hold_days = TIMEFRAME_DAYS.get(timeframe, DEFAULT_HOLD_DAYS)
    expiry_date = picked_at + timedelta(days=hold_days)
    days_held = (now - picked_at).total_seconds() / 86400

    # Check if pick has expired (enough time has passed)
    if now < expiry_date:
        # Not yet expired — fetch current price and check stop-loss only
        current_price = fetch_price_yfinance(symbol)
        if current_price is None:
            return None

        return_pct = ((current_price - entry_price) / entry_price) * 100

        # Check stop-loss
        if stop_loss > 0 and current_price <= stop_loss:
            pick['status'] = 'STOPPED_OUT'
            pick['currentPrice'] = current_price
            pick['returnPercent'] = round(return_pct, 2)
            pick['daysHeld'] = round(days_held, 2)
            pick['resolvedAt'] = now.isoformat() + 'Z'
            pick['outcome'] = 'loss'
            return pick

        # Still pending — just update current price
        pick['currentPrice'] = current_price
        pick['returnPercent'] = round(return_pct, 2)
        pick['daysHeld'] = round(days_held, 2)
        return pick

    # Pick has expired — fetch exit price at expiry date
    exit_price = fetch_price_at_date(symbol, expiry_date)
    if exit_price is None:
        # Try current price as fallback
        exit_price = fetch_price_yfinance(symbol)
    if exit_price is None:
        return None

    return_pct = ((exit_price - entry_price) / entry_price) * 100

    # Check if stop was hit during hold period (simplified: check exit price)
    if stop_loss > 0 and exit_price <= stop_loss:
        pick['status'] = 'STOPPED_OUT'
        pick['outcome'] = 'loss'
    elif return_pct > 0:
        pick['status'] = 'WIN'
        pick['outcome'] = 'win'
    else:
        pick['status'] = 'LOSS'
        pick['outcome'] = 'loss'

    pick['exitPrice'] = exit_price
    pick['currentPrice'] = exit_price
    pick['returnPercent'] = round(return_pct, 2)
    pick['daysHeld'] = round(days_held, 2)
    pick['resolvedAt'] = now.isoformat() + 'Z'

    return pick


def calc_oos_sharpe(returns):
    """
    Calculate annualized Sharpe ratio from a list of per-pick returns (%).
    Assumes one pick per ~5 trading days on average.
    """
    if len(returns) < 2:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    std_ret = math.sqrt(variance)
    if std_ret == 0:
        return 0.0
    # Annualize: assume ~50 picks/year (252 trading days / ~5 day hold)
    trades_per_year = 50
    return (mean_ret / std_ret) * math.sqrt(trades_per_year)


def compute_summary(picks):
    """Compute aggregate performance metrics from resolved picks."""
    resolved = [p for p in picks if p.get('status') not in ('PENDING', None)]
    wins = [p for p in resolved if p.get('outcome') == 'win']
    losses = [p for p in resolved if p.get('outcome') == 'loss']
    pending = [p for p in picks if p.get('status') == 'PENDING']

    returns = [p.get('returnPercent', 0) for p in resolved]

    total = len(resolved)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total * 100) if total > 0 else 0
    avg_return = (sum(returns) / total) if total > 0 else 0
    sharpe = calc_oos_sharpe(returns)

    avg_win = sum(p.get('returnPercent', 0) for p in wins) / win_count if win_count else 0
    avg_loss = sum(p.get('returnPercent', 0) for p in losses) / loss_count if loss_count else 0

    # Per-algorithm breakdown
    by_algo = {}
    for p in picks:
        algo = p.get('algorithm', 'Unknown')
        if algo not in by_algo:
            by_algo[algo] = {'picks': 0, 'verified': 0, 'wins': 0, 'losses': 0,
                             'returns': [], 'winRate': 0, 'avgReturn': 0}
        by_algo[algo]['picks'] += 1
        if p.get('status') not in ('PENDING', None):
            by_algo[algo]['verified'] += 1
            by_algo[algo]['returns'].append(p.get('returnPercent', 0))
            if p.get('outcome') == 'win':
                by_algo[algo]['wins'] += 1
            elif p.get('outcome') == 'loss':
                by_algo[algo]['losses'] += 1

    for algo, data in by_algo.items():
        v = data['verified']
        data['winRate'] = round(data['wins'] / v * 100, 1) if v > 0 else 0
        data['avgReturn'] = round(sum(data['returns']) / v, 2) if v > 0 else 0
        data['sharpe'] = round(calc_oos_sharpe(data['returns']), 3) if len(data['returns']) >= 2 else 0
        del data['returns']  # Don't serialize

    return {
        'lastVerified': datetime.utcnow().isoformat() + 'Z',
        'totalPicks': len(picks),
        'verified': total,
        'pending': len(pending),
        'wins': win_count,
        'losses': loss_count,
        'winRate': round(win_rate, 1),
        'avgReturn': round(avg_return, 2),
        'avgWin': round(avg_win, 2),
        'avgLoss': round(avg_loss, 2),
        'sharpe_oos': round(sharpe, 3),
        'byAlgorithm': by_algo,
    }


def main():
    parser = argparse.ArgumentParser(description='Pick Verifier — Resolve pending picks')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--force', action='store_true', help='Re-verify resolved picks')
    args = parser.parse_args()

    logger.info("=== Pick Verifier ===")

    # Load picks
    if not os.path.exists(PICKS_FILE):
        logger.error("Picks file not found: %s", PICKS_FILE)
        return

    with open(PICKS_FILE, 'r') as f:
        data = json.load(f)

    picks = data.get('allPicks', [])
    logger.info("Loaded %d picks (%d pending)",
                len(picks), sum(1 for p in picks if p.get('status') == 'PENDING'))

    # Resolve picks
    now = datetime.utcnow()
    resolved_count = 0
    updated_count = 0

    for i, pick in enumerate(picks):
        result = resolve_pick(pick, now, force=args.force)
        if result is not None:
            picks[i] = result
            updated_count += 1
            if result.get('status') != 'PENDING':
                resolved_count += 1
                logger.info("  %s (%s): %s -> %s (%.2f%%)",
                            result['symbol'], result.get('algorithm', '?'),
                            'PENDING', result['status'],
                            result.get('returnPercent', 0))

    # Compute summary
    summary = compute_summary(picks)
    logger.info("\n=== Out-of-Sample Performance ===")
    logger.info("  Total: %d | Verified: %d | Pending: %d",
                summary['totalPicks'], summary['verified'], summary['pending'])
    logger.info("  Wins: %d | Losses: %d | Win Rate: %.1f%%",
                summary['wins'], summary['losses'], summary['winRate'])
    logger.info("  Avg Return: %.2f%% | Avg Win: %.2f%% | Avg Loss: %.2f%%",
                summary['avgReturn'], summary['avgWin'], summary['avgLoss'])
    logger.info("  OOS Sharpe (annualized): %.3f", summary['sharpe_oos'])

    # Per-algorithm
    logger.info("\n  By Algorithm:")
    for algo, stats in summary['byAlgorithm'].items():
        logger.info("    %s: %d/%d verified, WR=%.1f%%, avg=%.2f%%, sharpe=%.3f",
                     algo, stats['verified'], stats['picks'],
                     stats['winRate'], stats['avgReturn'], stats.get('sharpe', 0))

    if args.dry_run:
        logger.info("\n  [DRY RUN — no files updated]")
        return

    # Save updated picks
    data['allPicks'] = picks
    # Update summary fields
    for key in ('lastVerified', 'totalPicks', 'verified', 'pending', 'wins',
                'losses', 'winRate', 'avgReturn', 'byAlgorithm'):
        data[key] = summary[key]
    data['sharpe_oos'] = summary['sharpe_oos']

    with open(PICKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info("\nUpdated: %s", PICKS_FILE)

    # Also save a clean OOS report
    report_path = os.path.join(OUTPUT_DIR, 'oos_performance.json')
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info("Saved OOS report: %s", report_path)


if __name__ == '__main__':
    main()
