#!/usr/bin/env python3
"""
Consensus Engine — Orchestrates the Smart Money consensus calculation.

This script triggers three PHP-side actions in sequence:
  1. calculate_consensus — Combines all data sources (analyst ratings, insider sentiment,
     13F holdings, news sentiment, WSB sentiment, technical signals) into an overall score.
  2. generate_challenger — Creates "Challenger Bot" signals based on consensus scores
     to compete against existing trading algorithms.
  3. update_showdown — Updates the Challenger vs existing algos leaderboard.

Each action is a simple HTTP GET that triggers server-side processing.
"""
import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import call_api

logger = logging.getLogger('consensus_engine')


def run_consensus():
    """
    Trigger consensus score calculation.
    Combines: analyst ratings, insider sentiment, 13F holdings, news sentiment,
    WSB sentiment, technical signals into overall_score per ticker.
    """
    logger.info("Triggering consensus calculation...")
    result = call_api('calculate_consensus')

    if result.get('ok'):
        scores = result.get('scores', result.get('consensus', []))
        logger.info(f"Consensus calculated successfully for {len(scores) if isinstance(scores, list) else 'N/A'} tickers")

        # Log top scores if available
        if isinstance(scores, list) and scores:
            # Sort by overall_score descending
            sorted_scores = sorted(scores, key=lambda x: x.get('overall_score', 0), reverse=True)
            logger.info("Top consensus scores:")
            logger.info(f"  {'Ticker':6s} | {'Overall':>8s} | {'Smart$':>7s} | {'Insider':>7s} | {'Analyst':>7s} | {'Social':>7s} | {'Direction':10s}")
            logger.info(f"  {'-'*6}-+-{'-'*8}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*10}")
            for s in sorted_scores[:10]:
                logger.info(
                    f"  {s.get('ticker', '?'):6s} | "
                    f"{s.get('overall_score', 0):8d} | "
                    f"{s.get('smart_money_score', 0):7d} | "
                    f"{s.get('insider_score', 0):7d} | "
                    f"{s.get('analyst_score', 0):7d} | "
                    f"{s.get('social_score', 0):7d} | "
                    f"{s.get('signal_direction', '?'):10s}"
                )
        elif isinstance(scores, dict):
            # API returned dict format
            logger.info(f"Consensus result: {json.dumps(scores, indent=2)[:500]}")
        else:
            logger.info(f"Raw result: {json.dumps(result)[:500]}")
    else:
        error = result.get('error', 'unknown')
        logger.warning(f"Consensus calculation returned error: {error}")
        # Not fatal — the action might not be implemented yet

    return result


def run_challenger():
    """
    Trigger Challenger Bot signal generation.
    Creates trading signals based on consensus scores to compete against existing algos.
    """
    logger.info("Triggering Challenger Bot signal generation...")
    result = call_api('generate_challenger')

    if result.get('ok'):
        signals = result.get('signals', result.get('generated', []))
        count = len(signals) if isinstance(signals, list) else result.get('count', 'N/A')
        logger.info(f"Challenger Bot generated {count} signals")

        if isinstance(signals, list):
            for sig in signals[:5]:
                logger.info(
                    f"  Challenger signal: {sig.get('ticker', '?')} "
                    f"{sig.get('direction', '?')} "
                    f"(confidence={sig.get('confidence', '?')}, "
                    f"score={sig.get('score', '?')})"
                )
        else:
            logger.info(f"Raw result: {json.dumps(result)[:500]}")
    else:
        error = result.get('error', 'unknown')
        logger.warning(f"Challenger generation returned error: {error}")

    return result


def run_showdown():
    """
    Trigger showdown standings update.
    Compares Challenger Bot performance against all existing algorithms.
    """
    logger.info("Triggering showdown standings update...")
    result = call_api('update_showdown')

    if result.get('ok'):
        showdown = result.get('showdown', result.get('standings', {}))
        logger.info("Showdown standings updated successfully")

        if isinstance(showdown, dict):
            challenger = showdown.get('challenger', {})
            best_algo = showdown.get('best_algo', {})

            if challenger:
                logger.info(
                    f"  Challenger Bot: "
                    f"trades={challenger.get('trades', 0)}, "
                    f"win_rate={challenger.get('win_rate', 0):.1f}%, "
                    f"PnL=${challenger.get('pnl', 0):,.2f}, "
                    f"Sharpe={challenger.get('sharpe', 0):.3f}"
                )
            if best_algo:
                logger.info(
                    f"  Best Algo ({best_algo.get('name', '?')}): "
                    f"trades={best_algo.get('trades', 0)}, "
                    f"win_rate={best_algo.get('win_rate', 0):.1f}%, "
                    f"PnL=${best_algo.get('pnl', 0):,.2f}, "
                    f"Sharpe={best_algo.get('sharpe', 0):.3f}"
                )
            rank = showdown.get('challenger_rank', 0)
            total = showdown.get('total_algos', 0)
            if rank and total:
                logger.info(f"  Challenger ranks #{rank} out of {total} algorithms")
        elif isinstance(showdown, list):
            logger.info(f"Showdown standings: {len(showdown)} entries")
            for entry in showdown[:3]:
                logger.info(f"  {json.dumps(entry)[:200]}")
        else:
            logger.info(f"Raw result: {json.dumps(result)[:500]}")
    else:
        error = result.get('error', 'unknown')
        logger.warning(f"Showdown update returned error: {error}")

    return result


def main():
    """Main entry point for consensus engine."""
    logger.info("=" * 60)
    logger.info("Consensus Engine — Starting")
    logger.info("=" * 60)

    results = {}

    # Step 1: Calculate consensus scores
    results['consensus'] = run_consensus()

    # Step 2: Generate Challenger Bot signals
    results['challenger'] = run_challenger()

    # Step 3: Update showdown standings
    results['showdown'] = run_showdown()

    # Summary
    logger.info("=" * 60)
    logger.info("CONSENSUS ENGINE SUMMARY")
    for step, result in results.items():
        status = "OK" if result.get('ok') else f"ISSUE ({result.get('error', 'unknown')})"
        logger.info(f"  {step}: {status}")
    logger.info("=" * 60)

    return results


if __name__ == '__main__':
    main()
