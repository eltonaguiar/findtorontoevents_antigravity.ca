#!/usr/bin/env python3
"""
Portfolio Manager for KIMI Rise of the Claw.

NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Tracks positions, executes paper trades, manages risk limits, persists state.

Features:
- Position tracking with entry prices and dates
- Risk management (stop loss, take profit, max positions)
- Portfolio valuation and P&L calculation
- State persistence across 15-minute runs

Author: Claude Sonnet 4.5
Date: 2026-02-16
"""

import logging
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path to import backtest_framework
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from backtest_framework import Signal

logger = logging.getLogger(__name__)


@dataclass
class LivePosition:
    """Represents an open position in live trading."""

    symbol: str
    algorithm_id: str
    entry_price: float
    entry_date: str  # ISO format
    quantity: float
    stop_loss: float
    take_profit: float
    current_price: float = 0.0
    category: str = 'stock'

    @property
    def pl_percent(self) -> float:
        """P&L percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    @property
    def pl_value(self) -> float:
        """P&L in dollars."""
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def days_held(self) -> int:
        """Days since entry."""
        try:
            entry = datetime.fromisoformat(self.entry_date.replace('Z', '+00:00'))
            now = datetime.now()
            return (now - entry).days
        except:
            return 0

    def to_dict(self) -> dict:
        """Convert to dashboard pick schema."""
        return {
            'symbol': self.symbol,
            'algorithm': self._algorithm_id_to_name(self.algorithm_id),
            'algorithmId': self.algorithm_id,
            'category': self.category,
            'entryPrice': round(self.entry_price, 2),
            'currentPrice': round(self.current_price, 2),
            'plPercent': round(self.pl_percent, 2),
            'plValue': round(self.pl_value, 2),
            'daysHeld': self.days_held,
            'signal': 'buy',
            'entryDate': self.entry_date,
            'targetPrice': round(self.take_profit, 2),
            'stopLoss': round(self.stop_loss, 2)
        }

    def _algorithm_id_to_name(self, algo_id: str) -> str:
        """Convert algorithm ID to display name."""
        mapping = {
            'etf-masters-live': 'ETF Masters',
            'crypto-winners-live': 'Crypto Winners Scanner',
            'meme-scanner-live': 'Meme Coin Scanner',
            'penny-tracker-live': 'Penny Stock Tracker',
            'forex-scanner-live': 'Forex Scanner',
            'rsi-momentum-live': 'RSI Momentum 5',
            'alpha-hunter-live': 'Alpha Hunter',
            'pump-watch-live': 'Pump Watch',
            'blue-chip-live': 'Blue Chip Growth',
            'technical-momentum-live': 'Technical Momentum'
        }
        return mapping.get(algo_id, algo_id)


class PortfolioManager:
    """Manages live portfolio state across 10 algorithms."""

    def __init__(self, state_file: str = None):
        """
        Initialize portfolio manager.

        Args:
            state_file: Path to portfolio state JSON (default: KIMI_RISEOFTHECLAW/data/portfolio_state.json)
        """
        if state_file is None:
            state_file = WORKSPACE / 'KIMI_RISEOFTHECLAW/data/portfolio_state.json'

        self.state_file = Path(state_file)
        self.algorithms = {}  # algorithm_id -> {cash, positions, closed_positions, daily_values}

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self.load_state()

    def load_state(self):
        """Load portfolio state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self._deserialize_state(data)
                logger.info(f"Loaded portfolio state from {self.state_file}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}, initializing fresh")
                self._initialize_algorithms()
        else:
            logger.info("No existing state found, initializing fresh portfolio")
            self._initialize_algorithms()

    def save_state(self):
        """Persist portfolio state to disk."""
        try:
            serialized = self._serialize_state()

            with open(self.state_file, 'w') as f:
                json.dump(serialized, f, indent=2)

            logger.info(f"Portfolio state saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _initialize_algorithms(self):
        """Create fresh portfolio for 10 algorithms."""
        algorithm_ids = [
            'etf-masters-live', 'crypto-winners-live', 'meme-scanner-live',
            'penny-tracker-live', 'forex-scanner-live', 'rsi-momentum-live',
            'alpha-hunter-live', 'pump-watch-live', 'blue-chip-live',
            'technical-momentum-live'
        ]

        for algo_id in algorithm_ids:
            self.algorithms[algo_id] = {
                'cash': 10000.0,
                'starting_value': 10000.0,
                'positions': [],
                'closed_positions': [],
                'daily_values': []
            }

        logger.info(f"Initialized {len(algorithm_ids)} algorithms with $10,000 each")

    def execute_trade(
        self,
        algorithm_id: str,
        signal: Signal,
        symbol: str,
        current_price: float,
        asset_type: str
    ) -> Optional[LivePosition]:
        """
        Execute a paper trade.

        Args:
            algorithm_id: Algorithm executing the trade
            signal: BUY or SELL signal
            symbol: Ticker symbol
            current_price: Current market price
            asset_type: Asset category

        Returns:
            LivePosition if trade opened, None otherwise
        """
        if algorithm_id not in self.algorithms:
            logger.error(f"Unknown algorithm: {algorithm_id}")
            return None

        algo_state = self.algorithms[algorithm_id]

        if signal == Signal.BUY:
            return self._execute_buy(algo_state, algorithm_id, symbol, current_price, asset_type)
        elif signal == Signal.SELL:
            return self._execute_sell(algo_state, algorithm_id, symbol, current_price)

        return None

    def _execute_buy(
        self,
        algo_state: dict,
        algorithm_id: str,
        symbol: str,
        current_price: float,
        asset_type: str
    ) -> Optional[LivePosition]:
        """Execute a buy order."""
        # Check limits
        open_positions = len(algo_state['positions'])
        if open_positions >= 5:  # Max 5 positions per algorithm
            logger.info(f"{algorithm_id}: Max positions reached (5), skipping BUY {symbol}")
            return None

        # Position sizing: 20% of cash per trade
        position_size_dollars = algo_state['cash'] * 0.20
        if position_size_dollars < 10:  # Minimum $10 position
            logger.warning(f"{algorithm_id}: Insufficient cash (${algo_state['cash']:.2f})")
            return None

        quantity = position_size_dollars / current_price

        # Calculate stop loss and take profit
        stop_loss = current_price * 0.95  # -5% stop
        take_profit = current_price * 1.10  # +10% target

        # Create position
        position = LivePosition(
            symbol=symbol,
            algorithm_id=algorithm_id,
            entry_price=current_price,
            entry_date=datetime.now().isoformat(),
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_price=current_price,
            category=asset_type
        )

        # Update cash
        algo_state['cash'] -= position_size_dollars
        algo_state['positions'].append(position)

        logger.info(f"{algorithm_id}: OPENED {symbol} @ ${current_price:.2f} (qty: {quantity:.4f}, value: ${position_size_dollars:.2f})")
        return position

    def _execute_sell(
        self,
        algo_state: dict,
        algorithm_id: str,
        symbol: str,
        current_price: float
    ) -> None:
        """Execute a sell order (close position)."""
        # Find and close position
        for i, pos in enumerate(algo_state['positions']):
            if pos.symbol == symbol:
                # Update current price before closing
                pos.current_price = current_price

                # Realize P&L
                exit_value = pos.quantity * current_price
                algo_state['cash'] += exit_value

                # Record closed position
                closed_pos = {
                    'symbol': symbol,
                    'entry_price': pos.entry_price,
                    'exit_price': current_price,
                    'pl_percent': pos.pl_percent,
                    'pl_value': pos.pl_value,
                    'entry_date': pos.entry_date,
                    'exit_date': datetime.now().isoformat(),
                    'days_held': pos.days_held
                }
                algo_state['closed_positions'].append(closed_pos)

                # Remove from open positions
                algo_state['positions'].pop(i)

                logger.info(f"{algorithm_id}: CLOSED {symbol} @ ${current_price:.2f} (P&L: {pos.pl_percent:.2f}%, ${pos.pl_value:.2f})")
                return

        logger.warning(f"{algorithm_id}: No open position for {symbol} to sell")

    def update_positions(self, prices: Dict[str, float]):
        """
        Update all open positions with current prices.

        Args:
            prices: Dict mapping symbol to current price
        """
        updated_count = 0

        for algo_id, algo_state in self.algorithms.items():
            for position in algo_state['positions']:
                if position.symbol in prices:
                    position.current_price = prices[position.symbol]
                    updated_count += 1

        logger.debug(f"Updated {updated_count} positions with current prices")

    def check_stop_loss_take_profit(self) -> List[Tuple[str, str, Signal]]:
        """
        Check all positions for stop loss or take profit hits.

        Returns:
            List of (algorithm_id, symbol, Signal.SELL) tuples
        """
        exits = []

        for algo_id, algo_state in self.algorithms.items():
            for position in algo_state['positions']:
                # Stop loss hit
                if position.current_price <= position.stop_loss:
                    exits.append((algo_id, position.symbol, Signal.SELL))
                    logger.warning(f"{algo_id}: STOP LOSS hit on {position.symbol} (${position.current_price:.2f} <= ${position.stop_loss:.2f})")

                # Take profit hit
                elif position.current_price >= position.take_profit:
                    exits.append((algo_id, position.symbol, Signal.SELL))
                    logger.info(f"{algo_id}: TAKE PROFIT hit on {position.symbol} (${position.current_price:.2f} >= ${position.take_profit:.2f})")

        return exits

    def get_current_value(self, algorithm_id: str, prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value (cash + positions).

        Args:
            algorithm_id: Algorithm to value
            prices: Current market prices

        Returns:
            Total portfolio value in dollars
        """
        if algorithm_id not in self.algorithms:
            return 0.0

        algo_state = self.algorithms[algorithm_id]
        cash = algo_state['cash']

        position_value = sum(
            pos.quantity * prices.get(pos.symbol, pos.current_price)
            for pos in algo_state['positions']
        )

        return cash + position_value

    def get_all_symbols(self) -> List[Tuple[str, str]]:
        """
        Get list of all symbols with open positions.

        Returns:
            List of (symbol, asset_type) tuples
        """
        symbols = set()

        for algo_state in self.algorithms.values():
            for position in algo_state['positions']:
                symbols.add((position.symbol, position.category))

        return list(symbols)

    def _serialize_state(self) -> dict:
        """Serialize portfolio state to JSON-compatible dict."""
        state_data = {'algorithms': {}}

        for algo_id, algo_state in self.algorithms.items():
            state_data['algorithms'][algo_id] = {
                'cash': algo_state['cash'],
                'starting_value': algo_state['starting_value'],
                'positions': [asdict(pos) for pos in algo_state['positions']],
                'closed_positions': algo_state['closed_positions'],
                'daily_values': algo_state['daily_values']
            }

        return state_data

    def _deserialize_state(self, data: dict):
        """Load portfolio state from JSON dict."""
        self.algorithms = {}

        for algo_id, algo_data in data.get('algorithms', {}).items():
            # Convert position dicts to LivePosition objects
            positions = [
                LivePosition(**pos_data)
                for pos_data in algo_data.get('positions', [])
            ]

            self.algorithms[algo_id] = {
                'cash': algo_data.get('cash', 10000.0),
                'starting_value': algo_data.get('starting_value', 10000.0),
                'positions': positions,
                'closed_positions': algo_data.get('closed_positions', []),
                'daily_values': algo_data.get('daily_values', [])
            }


if __name__ == '__main__':
    # Test the portfolio manager
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("Testing Portfolio Manager")
    print("=" * 60)

    # Create manager with test file
    pm = PortfolioManager(state_file='test_portfolio_state.json')

    print(f"\n[Initial State]")
    print(f"  Algorithms: {len(pm.algorithms)}")
    for algo_id, state in list(pm.algorithms.items())[:2]:
        print(f"  {algo_id}: ${state['cash']:.2f} cash, {len(state['positions'])} positions")

    # Test BUY
    print(f"\n[Execute BUY]")
    pos = pm.execute_trade('etf-masters-live', Signal.BUY, 'SPY', 500.0, 'stock')
    if pos:
        print(f"  Opened: {pos.symbol} @ ${pos.entry_price:.2f}")
        print(f"  Stop: ${pos.stop_loss:.2f}, Target: ${pos.take_profit:.2f}")

    # Update prices
    print(f"\n[Update Prices]")
    prices = {'SPY': 510.0, 'QQQ': 400.0}
    pm.update_positions(prices)
    print(f"  Updated positions with new prices")

    # Check current value
    print(f"\n[Portfolio Value]")
    value = pm.get_current_value('etf-masters-live', prices)
    print(f"  Total value: ${value:.2f}")

    # Check stop loss/take profit
    print(f"\n[Risk Check]")
    exits = pm.check_stop_loss_take_profit()
    if exits:
        for algo_id, symbol, signal in exits:
            print(f"  {algo_id}: EXIT {symbol}")
    else:
        print(f"  No exits triggered")

    # Test SELL
    print(f"\n[Execute SELL]")
    pm.execute_trade('etf-masters-live', Signal.SELL, 'SPY', 510.0, 'stock')

    # Save state
    print(f"\n[Save State]")
    pm.save_state()
    print(f"  State saved to {pm.state_file}")

    # Test reload
    print(f"\n[Reload State]")
    pm2 = PortfolioManager(state_file='test_portfolio_state.json')
    print(f"  Reloaded {len(pm2.algorithms)} algorithms")
    print(f"  etf-masters-live: ${pm2.algorithms['etf-masters-live']['cash']:.2f} cash")
    print(f"  Closed positions: {len(pm2.algorithms['etf-masters-live']['closed_positions'])}")

    print("\n" + "=" * 60)
    print("Test complete!")

    # Cleanup test file
    import os
    if os.path.exists('test_portfolio_state.json'):
        os.remove('test_portfolio_state.json')
        print("Test file cleaned up")
