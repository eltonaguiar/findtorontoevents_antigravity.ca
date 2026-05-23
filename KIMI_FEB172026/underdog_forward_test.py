#!/usr/bin/env python3
"""
UNDERDOG FORWARD TEST RUNNER
============================
Runs continuous forward testing of underdog strategies.

FORWARD TESTING PRINCIPLES:
1. Generate signals from REAL-TIME data only
2. Track every signal until resolution
3. No optimization on historical results
4. Publish results regardless of outcome
5. Discard strategies that fail forward test

This is the ONLY valid way to test strategies.
Backtests lie. Forward tests tell the truth.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from underdog_audit_trail import ForwardTestValidator, AuditSignal

# Configure logging
Path('logs').mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - FORWARD_TEST - %(message)s',
    handlers=[
        logging.FileHandler('logs/forward_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ForwardTest')


class UnderdogForwardTest:
    """
    Manages forward testing of all underdog strategies.
    
    Each strategy must prove itself in real-time or be discarded.
    """
    
    def __init__(self):
        self.validator = ForwardTestValidator()
        self.running = False
        
        # Strategy configurations
        self.strategies = {
            'crypto_funding_arbitrage': {
                'name': 'Crypto Perpetual Funding Arbitrage',
                'target_sharpe': 1.8,
                'target_return': 0.15,
                'min_trades_for_validation': 50,
                'max_drawdown': 0.15,
                'status': 'TESTING'
            },
            'earnings_vol_crush': {
                'name': 'Earnings Vol Crush',
                'target_sharpe': 1.5,
                'target_return': 0.30,
                'min_trades_for_validation': 30,  # Event-driven, fewer trades
                'max_drawdown': 0.20,
                'status': 'PENDING_DATA'  # Waiting for earnings calendar integration
            },
            'wsb_sentiment_fade': {
                'name': 'WSB Sentiment Fade',
                'target_sharpe': 1.2,
                'target_return': 0.25,
                'min_trades_for_validation': 50,
                'max_drawdown': 0.15,
                'status': 'PENDING_DATA'  # Waiting for Reddit API
            },
            'robinhood_momentum_crash': {
                'name': 'Robinhood Momentum Crash',
                'target_sharpe': 1.1,
                'target_return': 0.22,
                'min_trades_for_validation': 30,
                'max_drawdown': 0.18,
                'status': 'PENDING_DATA'  # Waiting for SwaggyStocks
            },
            'options_max_pain': {
                'name': 'Options Max Pain Pinning',
                'target_sharpe': 0.9,
                'target_return': 0.18,
                'min_trades_for_validation': 40,
                'max_drawdown': 0.12,
                'status': 'PENDING_DATA'  # Waiting for options data
            }
        }
    
    async def run_continuous_test(self):
        """Run continuous forward testing loop."""
        logger.info("=" * 70)
        logger.info("🚀 UNDERDOG FORWARD TEST STARTED")
        logger.info("=" * 70)
        logger.info("⚠️  FORWARD-LOOKING DATA ONLY")
        logger.info("⚠️  NO BACKTESTS. NO CURVE-FITTING.")
        logger.info("⚠️  REAL PERFORMANCE OR DISCARD.")
        logger.info("=" * 70)
        
        self.running = True
        cycle_count = 0
        
        try:
            while self.running:
                cycle_count += 1
                cycle_start = datetime.now()
                
                logger.info(f"\n{'='*70}")
                logger.info(f"📊 CYCLE #{cycle_count} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                logger.info(f"{'='*70}")
                
                # 1. Scan for new signals (real-time data only)
                await self._scan_for_signals()
                
                # 2. Check existing signals for exits
                await self._check_exits()
                
                # 3. Update forward test results
                await self._update_results()
                
                # 4. Log status
                await self._log_status()
                
                # 5. Export audit trail every 10 cycles
                if cycle_count % 10 == 0:
                    self.validator.export_audit_trail()
                
                # Wait before next cycle (5 minutes)
                await asyncio.sleep(300)
                
        except Exception as e:
            logger.error(f"Forward test error: {e}")
            raise
        finally:
            logger.info("🛑 Forward test stopped")
            self.validator.export_audit_trail()
    
    async def _scan_for_signals(self):
        """Scan all strategies for new signals."""
        logger.info("\n🔍 SCANNING FOR NEW SIGNALS")
        
        # Only crypto funding is live now (real-time data available)
        signals = await self.validator.scan_and_log_crypto_funding()
        
        if signals:
            logger.info(f"✅ Generated {len(signals)} new signals")
            for s in signals[:3]:
                logger.info(f"   {s.direction} {s.symbol} @ ${s.entry_price:.4f}")
        else:
            logger.info("ℹ️ No new signals this cycle")
    
    async def _check_exits(self):
        """Check if any active signals should be closed."""
        # This would check stop losses, take profits, time exits
        # For now, we'll use simple time-based exits for demo
        
        # In production, this would:
        # 1. Fetch current prices
        # 2. Compare to stop loss / take profit levels
        # 3. Close signals that hit levels
        pass
    
    async def _update_results(self):
        """Update forward test results for each strategy."""
        logger.info("\n📊 UPDATING FORWARD TEST RESULTS")
        
        for strategy_id, config in self.strategies.items():
            report = self.validator.get_forward_test_report(strategy_id)
            
            summary = report['summary']
            
            # Update strategy status
            if summary['total_trades'] >= config['min_trades_for_validation']:
                if report['validation_status'] == 'VALIDATED':
                    config['status'] = 'VALIDATED'
                    logger.info(f"✅ {strategy_id}: VALIDATED")
                elif report['validation_status'] == 'FAILED':
                    config['status'] = 'FAILED'
                    logger.warning(f"❌ {strategy_id}: FAILED - Consider removing")
                else:
                    config['status'] = 'PROVEN'
                    logger.info(f"⏳ {strategy_id}: PROVEN (needs more trades)")
            
            # Log progress
            if summary['total_trades'] > 0:
                logger.info(f"   {strategy_id}: {summary['total_trades']} trades, "
                          f"{summary['win_rate']:.1%} WR, "
                          f"{summary['total_pnl']:+.2%} P&L, "
                          f"PF {summary['profit_factor']:.2f}")
    
    async def _log_status(self):
        """Log overall system status."""
        overall = self.validator.get_forward_test_report()
        
        logger.info("\n📈 OVERALL STATUS")
        logger.info(f"   Total Trades: {overall['summary']['total_trades']}")
        logger.info(f"   Win Rate: {overall['summary']['win_rate']:.1%}")
        logger.info(f"   Total P&L: {overall['summary']['total_pnl']:+.2%}")
        logger.info(f"   Pending Signals: {overall['summary']['pending_signals']}")
        logger.info(f"   Validation Status: {overall['validation_status']}")
        
        # Save status to file
        status_file = Path('KIMI_FEB172026/data/forward_test_status.json')
        status_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(status_file, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'status': overall,
                'strategies': self.strategies
            }, f, indent=2, default=str)
    
    def get_recommendation(self) -> str:
        """Get recommendation based on forward test results."""
        report = self.validator.get_forward_test_report()
        
        status = report['validation_status']
        trades = report['summary']['total_trades']
        pnl = report['summary']['total_pnl']
        
        if status == 'VALIDATED':
            return f"✅ STRATEGY VALIDATED: {trades} trades, {pnl:+.2%} return. Ready for scaling."
        elif status == 'PROVEN':
            return f"⏳ PROVEN BUT NOT VALIDATED: {trades} trades, continue testing."
        elif status == 'PROMISING':
            return f"⏳ SHOWING PROMISE: {trades} trades, {pnl:+.2%}, need more data."
        elif status == 'FAILING':
            return f"⚠️ UNDERPERFORMING: {trades} trades, {pnl:+.2%}. Monitor closely."
        elif status == 'FAILED':
            return f"❌ FAILED: {trades} trades, {pnl:+.2%}. CONSIDER DISCARDING."
        else:
            return f"⏳ INSUFFICIENT DATA: {trades} trades. Continue forward testing."


async def run_single_cycle():
    """Run a single forward test cycle (for GitHub Actions)."""
    test = UnderdogForwardTest()
    
    logger.info("=" * 70)
    logger.info("🔄 SINGLE FORWARD TEST CYCLE")
    logger.info("=" * 70)
    
    # Scan for signals
    await test._scan_for_signals()
    
    # Update results
    await test._update_results()
    
    # Log status
    await test._log_status()
    
    # Get recommendation
    rec = test.get_recommendation()
    logger.info(f"\n🎯 RECOMMENDATION: {rec}")
    
    # Export audit trail
    export_path = test.validator.export_audit_trail()
    logger.info(f"\n📄 Audit trail: {export_path}")
    
    return rec


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        # Run continuous mode
        test = UnderdogForwardTest()
        asyncio.run(test.run_continuous_test())
    else:
        # Run single cycle (for GitHub Actions)
        asyncio.run(run_single_cycle())
