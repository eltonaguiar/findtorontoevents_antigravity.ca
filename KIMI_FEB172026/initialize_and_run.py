"""
KIMI_FEB172026 - Initialize and Run
First-time setup and signal generation
This script starts the system and generates the first batch of signals
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KIMI_INIT")


def initialize_system():
    """Initialize all components and database"""
    logger.info("=" * 80)
    logger.info("KIMI_FEB172026 - System Initialization")
    logger.info("=" * 80)
    
    # Import and initialize
    from sqlite_store import SQLiteStore
    from signal_tracker import SignalTracker
    from parameter_optimizer import ParameterOptimizer
    
    # Initialize database
    store = SQLiteStore()
    logger.info("✓ Database initialized")
    
    # Initialize tracker
    tracker = SignalTracker()
    logger.info(f"✓ Signal tracker ready (active: {len(tracker.active_signals)}, completed: {len(tracker.completed_signals)})")
    
    # Initialize optimizer
    optimizer = ParameterOptimizer()
    logger.info(f"✓ Parameter optimizer ready ({len(optimizer.optimized_params)} optimized sets)")
    
    return store, tracker, optimizer


async def generate_first_signals():
    """Generate the first batch of signals"""
    logger.info("\n" + "=" * 80)
    logger.info("Generating First Signals")
    logger.info("=" * 80)
    
    from live_scanner import KIMILiveScanner
    
    scanner = KIMILiveScanner()
    
    if not scanner.initialize():
        logger.error("Failed to initialize scanner")
        return None
    
    logger.info("Running first scan...")
    results = await scanner.run_full_scan()
    
    logger.info(f"\nResults:")
    logger.info(f"  Algorithms checked: {results.get('algorithms_checked', 0)}")
    logger.info(f"  Signals generated: {results.get('signals_generated', 0)}")
    logger.info(f"  High confidence: {results.get('high_confidence_signals', 0)}")
    logger.info(f"  Picks created: {results.get('picks_created', 0)}")
    
    return results


def display_signals():
    """Display current signals"""
    from signal_tracker import SignalTracker
    
    tracker = SignalTracker()
    
    logger.info("\n" + "=" * 80)
    logger.info("Current Signal Status")
    logger.info("=" * 80)
    
    # Active signals
    if tracker.active_signals:
        logger.info(f"\nActive Signals: {len(tracker.active_signals)}")
        for sig_id, signal in list(tracker.active_signals.items())[:5]:
            logger.info(f"  {signal.symbol} {signal.direction}")
            logger.info(f"    Entry: ${signal.entry_price:,.2f}")
            logger.info(f"    TP: ${signal.take_profit:,.2f} | SL: ${signal.stop_loss:,.2f}")
            logger.info(f"    Confidence: {signal.confidence:.1%}")
    else:
        logger.info("\nNo active signals yet")
    
    # Completed signals
    if tracker.completed_signals:
        recent = tracker.completed_signals[-5:]
        logger.info(f"\nRecent Completed Signals:")
        for signal in reversed(recent):
            status_icon = "✓" if signal.pnl_pct > 0 else "✗"
            logger.info(f"  {status_icon} {signal.symbol} {signal.exit_reason} "
                       f"PnL: {signal.pnl_pct:+.2f}%")
    else:
        logger.info("\nNo completed signals yet (validation runs every 4 hours)")


def create_initial_status():
    """Create initial system status file"""
    status = {
        "system": "KIMI_FEB172026",
        "version": "11.0.0-INTEGRATED",
        "status": "initialized",
        "initialized_at": datetime.now().isoformat(),
        "first_run": True,
        "message": "System initialized. First scan completed. Validation begins in 4 hours."
    }
    
    status_path = Path(__file__).parent / "data" / "system_status.json"
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2)
    
    logger.info(f"✓ Status file created: {status_path}")


async def main():
    """Main initialization and first run"""
    print("""
    +======================================================================+
    |                                                                      |
    |     KIMI_FEB172026 - First Run Initialization                       |
    |                                                                      |
    +======================================================================+
    """)
    
    # Initialize
    try:
        store, tracker, optimizer = initialize_system()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return 1
    
    # Generate first signals
    try:
        results = await generate_first_signals()
        if not results:
            logger.error("Signal generation failed")
            return 1
    except Exception as e:
        logger.error(f"Signal generation error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Create status file
    create_initial_status()
    
    # Display current state
    display_signals()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Initialization Complete")
    logger.info("=" * 80)
    logger.info("\nSystem is now running!")
    logger.info("Next validation cycle: 4 hours")
    logger.info("Next optimization: 24 hours")
    logger.info("\nTo monitor progress:")
    logger.info("  - Check: KIMI_FEB172026/data/system_status.json")
    logger.info("  - Check: KIMI_FEB172026/data/signal_tracking.json")
    logger.info("  - Dashboard: python monitor_dashboard.py")
    logger.info("\nGitHub Actions will now run automatically every 5 minutes")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
