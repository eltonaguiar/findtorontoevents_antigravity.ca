#!/usr/bin/env python3
"""
Live Trading Pipeline for KIMI Rise of the Claw.

Runs every 15 minutes via GitHub Actions to:
1. Fetch real-time market prices
2. Generate trading signals from 10 algorithms
3. Execute paper trades (position updates)
4. Calculate performance metrics
5. Output live_competition.json for dashboard
6. Persist portfolio state for next run

Author: Claude Sonnet 4.5
Date: 2026-02-16
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import logging

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from tools.market_data_fetcher import MarketDataFetcher
from tools.portfolio_manager import PortfolioManager
from tools.live_strategies import LIVE_STRATEGIES
from tools.performance_calculator import PerformanceCalculator
from backtest_framework import Signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveTradingPipeline:
    """Main pipeline orchestrator."""

    def __init__(self):
        self.data_fetcher = MarketDataFetcher()
        self.portfolio_mgr = PortfolioManager()
        self.perf_calc = PerformanceCalculator()

        self.output_file = WORKSPACE / 'KIMI_RISEOFTHECLAW/data/live_competition.json'

    def run(self):
        """Execute full pipeline."""
        logger.info("=" * 60)
        logger.info("KIMI RISE OF THE CLAW - LIVE TRADING PIPELINE")
        logger.info(f"Run time: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        try:
            # Step 1: Fetch current market prices
            logger.info("\n[1/6] Fetching market prices...")
            prices = self._fetch_all_prices()
            logger.info(f"      Fetched {len(prices)} prices")

            # Step 2: Update existing positions
            logger.info("\n[2/6] Updating open positions...")
            self.portfolio_mgr.update_positions(prices)

            # Step 3: Check stop loss / take profit
            logger.info("\n[3/6] Checking risk limits...")
            exits = self.portfolio_mgr.check_stop_loss_take_profit()
            for algo_id, symbol, signal in exits:
                price = prices.get(symbol)
                if price:
                    self.portfolio_mgr.execute_trade(algo_id, signal, symbol, price, 'unknown')
                    logger.info(f"      Risk exit: {algo_id} {signal.name} {symbol}")

            # Step 4: Generate new signals
            logger.info("\n[4/6] Generating trading signals...")
            new_signals = self._generate_signals(prices)
            logger.info(f"      Generated {len(new_signals)} signals")

            # Step 5: Execute new trades
            logger.info("\n[5/6] Executing trades...")
            for algo_id, symbol, signal, price, asset_type in new_signals:
                self.portfolio_mgr.execute_trade(algo_id, signal, symbol, price, asset_type)

            # Step 6: Calculate metrics and write output
            logger.info("\n[6/6] Calculating metrics and writing output...")
            self._write_live_competition_json(prices)

            # Save portfolio state
            self.portfolio_mgr.save_state()

            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE COMPLETE")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"PIPELINE FAILED: {e}", exc_info=True)
            raise

    def _fetch_all_prices(self) -> dict:
        """Fetch prices for all symbols across all strategies."""
        symbols_to_fetch = []

        # Collect symbols from strategy universes
        for algo_id, strategy_config in LIVE_STRATEGIES.items():
            universe = strategy_config['universe']
            asset_type = strategy_config['asset_type']

            for symbol in universe:
                symbols_to_fetch.append((symbol, asset_type))

        # Add symbols from open positions
        open_symbols = self.portfolio_mgr.get_all_symbols()
        symbols_to_fetch.extend(open_symbols)

        # Remove duplicates
        symbols_to_fetch = list(set(symbols_to_fetch))

        # Batch fetch
        prices = self.data_fetcher.get_batch_prices(symbols_to_fetch)

        return prices

    def _generate_signals(self, prices: dict) -> list:
        """
        Run all 10 strategies to generate signals.

        Returns:
            List of (algorithm_id, symbol, signal, price, asset_type) tuples
        """
        signals = []

        for algo_id, strategy_config in LIVE_STRATEGIES.items():
            strategy_adapter = strategy_config['strategy']
            universe = strategy_config['universe']
            asset_type = strategy_config['asset_type']

            for symbol in universe:
                if symbol not in prices:
                    logger.debug(f"      {algo_id}: No price for {symbol}")
                    continue

                current_price = prices[symbol]

                try:
                    signal = strategy_adapter.generate_signal(symbol, asset_type, current_price)

                    if signal != Signal.HOLD:
                        signals.append((algo_id, symbol, signal, current_price, asset_type))
                        logger.info(f"      {algo_id}: {signal.name} {symbol} @ ${current_price:.2f}")

                except Exception as e:
                    logger.error(f"      Signal generation error for {algo_id}/{symbol}: {e}")

        return signals

    def _write_live_competition_json(self, prices: dict):
        """Generate live_competition.json matching dashboard schema."""

        algorithms_output = []
        all_active_picks = []

        for algo_id, algo_state in self.portfolio_mgr.algorithms.items():
            # Calculate current value
            current_value = self.portfolio_mgr.get_current_value(algo_id, prices)
            starting_value = algo_state['starting_value']

            # Update daily values
            self.perf_calc.update_daily_values(algo_state, current_value)

            # Calculate metrics
            total_return = self.perf_calc.calculate_total_return(starting_value, current_value)
            win_rate = self.perf_calc.calculate_win_rate(algo_state['closed_positions'])

            daily_values = [dv['value'] for dv in algo_state.get('daily_values', [])]
            sharpe = self.perf_calc.calculate_sharpe_ratio(daily_values)
            max_dd = self.perf_calc.calculate_max_drawdown(daily_values)

            # Map to dashboard category
            category = self._get_category(algo_id)

            # Build algorithm object
            algo_output = {
                'id': algo_id,
                'name': LIVE_STRATEGIES[algo_id]['name'],
                'category': category,
                'startingValue': starting_value,
                'currentValue': round(current_value, 2),
                'cash': round(algo_state['cash'], 2),
                'totalReturn': round(total_return, 2),
                'activePicks': [],  # Will populate below
                'closedPicks': algo_state['closed_positions'][-10:],  # Last 10
                'status': 'ACTIVE' if len(algo_state['positions']) > 0 else 'READY',
                'winRate': round(win_rate, 2) if win_rate > 0 else 0.0,
                'sharpeRatio': sharpe,
                'maxDrawdown': max_dd,
                'nextAction': self._get_next_action(algo_id)
            }

            # Add active picks
            for position in algo_state['positions']:
                pick_dict = position.to_dict()
                algo_output['activePicks'].append(pick_dict)
                all_active_picks.append(pick_dict)

            algorithms_output.append(algo_output)

        # Market status
        market_status = self.data_fetcher.get_market_status()

        # Sort active picks by P&L (best first)
        all_active_picks.sort(key=lambda p: p.get('plPercent', 0), reverse=True)

        # Final output
        output = {
            'competition': {
                'name': 'KIMI Rise of the Claw - LIVE',
                'type': 'Forward-Facing Paper Trading',
                'startDate': '2026-02-16',
                'startingCapital': 10000,
                'status': 'ACTIVE',
                'lastUpdated': datetime.now().isoformat() + 'Z',
                'updateFrequency': 'Every 15 minutes'
            },
            'algorithms': algorithms_output,
            'todaysPicks': all_active_picks[:20],  # Top 20 by P&L
            'marketStatus': market_status
        }

        # Write to file
        with open(self.output_file, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"      Wrote {self.output_file}")
        logger.info(f"      Total algorithms: {len(algorithms_output)}")
        logger.info(f"      Total active picks: {len(all_active_picks)}")

    def _get_category(self, algo_id: str) -> str:
        """Map algorithm ID to dashboard category."""
        mapping = {
            'etf-masters-live': 'stock',
            'crypto-winners-live': 'crypto',
            'meme-scanner-live': 'meme',
            'penny-tracker-live': 'penny',
            'forex-scanner-live': 'forex',
            'rsi-momentum-live': 'crypto',
            'alpha-hunter-live': 'crypto',
            'pump-watch-live': 'crypto',
            'blue-chip-live': 'stock',
            'technical-momentum-live': 'stock'
        }
        return mapping.get(algo_id, 'stock')

    def _get_next_action(self, algo_id: str) -> str:
        """Get human-readable next action for algorithm."""
        actions = {
            'etf-masters-live': 'Scan for quality ETFs',
            'crypto-winners-live': 'Monitor funding rates',
            'meme-scanner-live': 'High volatility scan',
            'penny-tracker-live': 'Breakout detection',
            'forex-scanner-live': 'Check major pairs',
            'rsi-momentum-live': 'RSI oversold scan',
            'alpha-hunter-live': 'Flash crash detection',
            'pump-watch-live': 'Volume spike monitor',
            'blue-chip-live': 'Low beta scan',
            'technical-momentum-live': 'Pairs correlation check'
        }
        return actions.get(algo_id, 'Scanning...')


def main():
    """Entry point."""
    try:
        pipeline = LiveTradingPipeline()
        pipeline.run()
    except Exception as e:
        logger.error(f"PIPELINE FAILED: {e}", exc_info=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
