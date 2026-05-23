"""
KIMI_FEB172026 - Integrated Trading System
Complete system combining signal generation, validation, and optimization
Runs everything together for maximum performance
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import logging

# Import all our modules
from autonomous_runner import AutonomousTrader
from live_validator import LiveValidator
from signal_tracker import SignalTracker
from performance_validator import PerformanceValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIMI_INTEGRATED")


class IntegratedTradingSystem:
    """
    Master integration of all KIMI_FEB172026 components
    - Signal generation
    - Outcome validation
    - Performance tracking
    - Parameter optimization
    - Self-monitoring
    """
    
    VERSION = "11.0.0-INTEGRATED"
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all components
        logger.info("Initializing Integrated Trading System...")
        
        self.autonomous = AutonomousTrader()
        self.validator = LiveValidator()
        self.tracker = SignalTracker(str(self.data_dir))
        self.perf_validator = PerformanceValidator(str(self.data_dir))
        
        self.is_running = False
        self.system_stats = {
            "signals_generated": 0,
            "signals_validated": 0,
            "optimizations_applied": 0,
            "performance_checks": 0
        }
        
        logger.info("All components initialized")
    
    def initialize(self) -> bool:
        """Initialize all subsystems"""
        try:
            # Initialize autonomous trader
            if not self.autonomous.initialize():
                logger.error("Failed to initialize autonomous trader")
                return False
            
            logger.info("✓ Autonomous trader ready")
            logger.info("✓ Signal tracker ready")
            logger.info("✓ Live validator ready")
            logger.info("✓ Performance validator ready")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    async def full_cycle(self):
        """
        Run one complete cycle:
        1. Generate signals
        2. Track outcomes
        3. Validate performance
        4. Optimize parameters
        """
        logger.info("=" * 80)
        logger.info("Running full system cycle")
        logger.info("=" * 80)
        
        # 1. Generate signals
        logger.info("[1/4] Generating signals...")
        scan_result = await self.autonomous.run_scan_cycle()
        
        if scan_result.get("success"):
            self.system_stats["signals_generated"] += scan_result.get("signals_generated", 0)
            logger.info(f"✓ Generated {scan_result.get('signals_generated', 0)} signals")
        
        # 2. Check outcomes and track
        logger.info("[2/4] Validating signal outcomes...")
        await self.validator.run_validation_cycle()
        self.system_stats["signals_validated"] += len(self.tracker.completed_signals)
        logger.info(f"✓ Validated {len(self.tracker.completed_signals)} completed signals")
        
        # 3. Performance validation
        logger.info("[3/4] Checking performance metrics...")
        perf_summary = self.autonomous.get_performance_summary()
        self.system_stats["performance_checks"] += 1
        
        # Check if we need alerts
        if perf_summary.get("win_rate", 0) < 0.55:
            logger.warning("⚠️ Win rate below 55% - consider increasing confidence threshold")
        
        if perf_summary.get("total_pnl_pct", 0) < -5:
            logger.warning("⚠️ Negative P&L - review strategy effectiveness")
        
        logger.info(f"✓ Performance: WR={perf_summary.get('win_rate', 0):.1%}, "
                   f"PnL={perf_summary.get('total_pnl_pct', 0):+.2f}%")
        
        # 4. Optimization (if needed)
        logger.info("[4/4] Checking optimization needs...")
        
        if (self.validator.last_optimization is None or
            (datetime.now() - self.validator.last_optimization).total_seconds() > 24 * 3600):
            
            opt_result = await self.validator.run_optimization()
            changes = len(opt_result.get('optimizations', []))
            self.system_stats["optimizations_applied"] += changes
            
            if changes > 0:
                logger.info(f"✓ Applied {changes} parameter optimizations")
            else:
                logger.info("✓ No optimizations needed")
        else:
            logger.info("✓ Optimization not due yet")
        
        # Save system state
        self._save_system_state()
        
        logger.info("=" * 80)
        logger.info("Cycle complete")
        logger.info("=" * 80)
    
    def _save_system_state(self):
        """Save current system state"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "version": self.VERSION,
            "is_running": self.is_running,
            "stats": self.system_stats,
            "active_signals": len(self.tracker.active_signals),
            "completed_signals": len(self.tracker.completed_signals),
            "validations_run": self.validator.validation_count
        }
        
        state_file = self.data_dir / "integrated_system_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    async def run_continuous(self):
        """Run integrated system continuously"""
        self.is_running = True
        
        logger.info("=" * 80)
        logger.info(f"KIMI_FEB172026 Integrated System v{self.VERSION}")
        logger.info("=" * 80)
        logger.info("Components:")
        logger.info("  - Autonomous signal generation (every 5 min)")
        logger.info("  - Live outcome validation (every 4 hours)")
        logger.info("  - Performance monitoring (continuous)")
        logger.info("  - Parameter optimization (every 24 hours)")
        logger.info("=" * 80)
        logger.info("System is running. Press Ctrl+C to stop.")
        logger.info("=" * 80)
        
        # Run initial cycle immediately
        await self.full_cycle()
        
        cycle_count = 0
        
        while self.is_running:
            try:
                # Wait 5 minutes between cycles
                await asyncio.sleep(300)
                
                cycle_count += 1
                
                # Run full cycle
                await self.full_cycle()
                
                # Every 12 cycles (1 hour), generate report
                if cycle_count % 12 == 0:
                    report = self.validator.generate_report()
                    report_file = self.data_dir / f"hourly_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                    with open(report_file, 'w') as f:
                        f.write(report)
                    logger.info(f"Hourly report saved: {report_file}")
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in continuous loop: {e}")
                await asyncio.sleep(60)  # 1 min retry
        
        self.stop()
    
    def stop(self):
        """Stop the integrated system"""
        logger.info("Stopping integrated system...")
        self.is_running = False
        self.autonomous.stop()
        self._save_system_state()
        logger.info("System stopped")
    
    def get_status(self) -> dict:
        """Get current system status"""
        return {
            "version": self.VERSION,
            "is_running": self.is_running,
            "stats": self.system_stats,
            "autonomous_status": self.autonomous.get_status(),
            "validation_count": self.validator.validation_count,
            "active_signals": len(self.tracker.active_signals),
            "completed_signals": len(self.tracker.completed_signals)
        }


# =============================================================================
# Entry Point
# =============================================================================
async def main():
    """Run integrated system"""
    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║     KIMI_FEB172026 - Integrated Trading System                      ║
    ║     Signal Generation + Validation + Optimization                    ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    system = IntegratedTradingSystem()
    
    if not system.initialize():
        print("[ERROR] Failed to initialize system")
        return 1
    
    print("\n[System Ready]")
    print("Starting integrated trading system...")
    print("Press Ctrl+C to stop\n")
    
    try:
        await system.run_continuous()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        system.stop()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
