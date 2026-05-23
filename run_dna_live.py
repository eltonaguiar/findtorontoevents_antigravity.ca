"""
Run DNA Live - Main Execution Script
====================================
Main script to run FreshPicks DNA strategy live.

This script:
1. Generates picks
2. Sends to Discord
3. Tracks performance
4. Logs everything

Usage:
    # Run once
    python run_dna_live.py
    
    # Run continuously (every 4 hours)
    python run_dna_live.py --loop --interval 14400
    
    # Dry run (don't actually send to Discord)
    python run_dna_live.py --dry-run

Environment Variables:
    DISCORD_WEBHOOK_URL - Discord webhook for sending picks
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dna_live.log')
    ]
)
logger = logging.getLogger('DNALive')

# Import our modules
try:
    from freshpicks_dna_strategy import DNAPickGenerator
    from discord_dna_sender import DNADiscordSender, ConsoleSender
    from dna_live_tracker import DNALiveTracker
    from consistency_tracker import ConsistencyTracker
    from wtf_dashboard import WTFDashboard
    from portfolio_circuit_breaker import PortfolioCircuitBreaker
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)


class DNALiveRunner:
    """
    Main runner for DNA live strategy
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        
        # Initialize components
        self.generator = DNAPickGenerator()
        self.tracker = DNALiveTracker()
        self.consistency = ConsistencyTracker()
        self.wtf = WTFDashboard()
        self.circuit_breaker = PortfolioCircuitBreaker()
        
        # Discord sender
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url and not dry_run:
            self.sender = DNADiscordSender(webhook_url)
            logger.info("Using Discord sender")
        else:
            self.sender = ConsoleSender()
            if dry_run:
                logger.info("DRY RUN MODE - Using console sender")
            else:
                logger.warning("No Discord webhook - using console sender")
    
    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one full cycle: generate -> send -> track
        
        Returns results summary
        """
        logger.info("=" * 80)
        logger.info("DNA LIVE CYCLE STARTING")
        logger.info("=" * 80)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'picks_generated': 0,
            'picks_sent': 0,
            'errors': []
        }
        
        try:
            # Step 1: Check circuit breaker
            can_trade, reason = self.circuit_breaker.can_trade()
            if not can_trade:
                logger.error(f"CIRCUIT BREAKER ACTIVE: {reason}")
                results['circuit_breaker'] = reason
                return results
            
            # Step 2: Generate picks
            logger.info("Generating picks...")
            picks = self.generator.generate_picks()
            results['picks_generated'] = len(picks)
            
            if not picks:
                logger.info("No picks generated this cycle")
                return results
            
            # Step 3: Send to Discord
            logger.info(f"Sending {len(picks)} picks...")
            send_results = self.sender.send_batch(picks, dry_run=self.dry_run)
            results['picks_sent'] = send_results['sent']
            
            # Step 4: Add to tracker
            for pick in picks:
                self.tracker.add_pick(pick)
                
                # Log to consistency tracker
                self.consistency.add_trade(
                    strategy_id='freshpicks_dna',
                    pnl_percent=0,  # Will update later
                    timestamp=pick.timestamp
                )
            
            # Step 5: Log to WTF dashboard
            self.wtf.update_pipeline_stats('signals_received', len(picks))
            self.wtf.update_pipeline_stats('final_approved', send_results['sent'])
            
            logger.info(f"Cycle complete: {send_results['sent']}/{len(picks)} picks sent")
            
        except Exception as e:
            logger.exception("Error in cycle")
            results['errors'].append(str(e))
        
        return results
    
    def update_prices(self, prices: Dict[str, float]):
        """Update pick prices"""
        self.tracker.update_all_prices(prices)
    
    def get_status(self) -> Dict[str, Any]:
        """Get full system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'circuit_breaker': self.circuit_breaker.get_status(),
            'active_picks': self.tracker.get_active_summary(),
            'consistency': self.consistency.get_consistency_report('freshpicks_dna'),
            'generator_stats': self.generator.get_stats()
        }
    
    def run_continuous(self, interval_seconds: int = 14400):
        """
        Run continuously with sleep intervals
        
        Default: every 4 hours (14400 seconds)
        """
        logger.info(f"Starting continuous mode (interval: {interval_seconds}s)")
        
        try:
            while True:
                # Run cycle
                results = self.run_cycle()
                
                # Log results
                logger.info(f"Cycle results: {json.dumps(results, default=str)}")
                
                # Sleep
                logger.info(f"Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.exception("Error in continuous mode")
            raise


def main():
    parser = argparse.ArgumentParser(description='Run FreshPicks DNA Live')
    parser.add_argument('--loop', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=14400, help='Interval in seconds (default: 4h)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no Discord)')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    
    args = parser.parse_args()
    
    # Create runner
    runner = DNALiveRunner(dry_run=args.dry_run)
    
    if args.status:
        # Show status
        status = runner.get_status()
        print(json.dumps(status, indent=2, default=str))
        return
    
    if args.loop:
        # Continuous mode
        runner.run_continuous(args.interval)
    else:
        # Single run
        results = runner.run_cycle()
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(json.dumps(results, indent=2, default=str))
        
        # Show active picks
        active = runner.tracker.get_active_summary()
        if 'picks' in active:
            print("\n" + "=" * 80)
            print("ACTIVE PICKS")
            print("=" * 80)
            for pick in active['picks']:
                print(f"  {pick['id']}: {pick['symbol']} {pick['direction']} {pick['pnl']:+.2f}%")


if __name__ == "__main__":
    main()
