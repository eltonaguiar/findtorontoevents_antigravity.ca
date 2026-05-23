"""
KIMI_FEB172026 - Autonomous Runner
Self-managing trading system that runs continuously without user intervention
- Auto-starts on system boot
- Scheduled scans every 5 minutes
- Self-validation and performance monitoring
- Auto-restart on failure
- Live dashboard updates
"""

import asyncio
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import threading
import subprocess
import os

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "autonomous.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("KIMI_AUTONOMOUS")

# Import our modules
try:
    from live_scanner import KIMILiveScanner
    from sqlite_store import SQLiteStore
    from elimination_engine import EliminationEngine
    from ml_signal_ranker import MLSignalRanker
    MODULES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    MODULES_AVAILABLE = False


class AutonomousTrader:
    """
    Self-managing trading system
    Runs 24/7 with minimal human intervention
    """
    
    VERSION = "11.0.0-AUTO"
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.scanner: Optional[KIMILiveScanner] = None
        self.store: Optional[SQLiteStore] = None
        self.elimination: Optional[EliminationEngine] = None
        self.ml_ranker: Optional[MLSignalRanker] = None
        
        self.is_running = False
        self.scan_count = 0
        self.error_count = 0
        self.last_scan_time = None
        self.performance_history = []
        
        # Config
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load or create configuration"""
        config_path = self.data_dir / "autonomous_config.json"
        
        default_config = {
            "scan_interval_minutes": 5,
            "market_hours_only": False,
            "crypto_24h": True,
            "min_confidence_threshold": 0.65,
            "max_signals_per_scan": 10,
            "auto_trade_mode": False,  # Paper trading only by default
            "position_size_usd": 1000,
            "max_positions": 5,
            "stop_loss_pct": 2.0,
            "take_profit_pct": 4.0,
            "time_exit_hours": 24,
            "performance_window_days": 7,
            "enable_ml_training": True,
            "ml_training_interval_hours": 24,
            "alert_webhook": None,
            "email_alerts": False,
            "created_at": datetime.now().isoformat()
        }
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                saved = json.load(f)
                default_config.update(saved)
        else:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
        
        return default_config
    
    def initialize(self) -> bool:
        """Initialize all components"""
        logger.info("=" * 80)
        logger.info(f"KIMI_FEB172026 Autonomous Trader v{self.VERSION}")
        logger.info("=" * 80)
        
        if not MODULES_AVAILABLE:
            logger.error("Required modules not available. Run setup.py first.")
            return False
        
        try:
            logger.info("Initializing components...")
            
            # Initialize database
            self.store = SQLiteStore(str(self.data_dir / "kimi_trading.db"))
            logger.info("✓ Database connected")
            
            # Initialize scanner
            self.scanner = KIMILiveScanner()
            logger.info("✓ Live scanner ready")
            
            # Initialize elimination engine
            self.elimination = EliminationEngine(str(self.data_dir))
            logger.info("✓ Elimination engine ready")
            
            # Initialize ML ranker
            self.ml_ranker = MLSignalRanker(str(self.data_dir))
            logger.info("✓ ML ranker ready")
            
            # Load performance history
            self._load_performance_history()
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _load_performance_history(self):
        """Load historical performance"""
        perf_path = self.data_dir / "performance_history.json"
        if perf_path.exists():
            with open(perf_path, 'r') as f:
                self.performance_history = json.load(f)
    
    def _save_performance_history(self):
        """Save performance history"""
        perf_path = self.data_dir / "performance_history.json"
        with open(perf_path, 'w') as f:
            json.dump(self.performance_history[-100:], f, indent=2)  # Keep last 100
    
    async def run_scan_cycle(self) -> Dict:
        """Execute one full scan cycle"""
        start_time = time.time()
        
        try:
            logger.info("Starting scan cycle...")
            
            # Run the scan
            results = await self.scanner.run_full_scan()
            
            # Get signals
            signals = self.scanner.get_latest_signals(
                limit=self.config["max_signals_per_scan"]
            )
            
            # Filter by confidence
            high_confidence = [
                s for s in signals 
                if s.get('win_probability', 0) >= self.config["min_confidence_threshold"]
            ]
            
            # Check for exits on existing positions
            await self._check_exits()
            
            # Create new picks for high-confidence signals
            if len(self.get_open_positions()) < self.config["max_positions"]:
                await self._create_positions(high_confidence)
            
            # Update performance metrics
            cycle_time = time.time() - start_time
            self._update_metrics(results, cycle_time)
            
            # Periodic ML training
            if self.config["enable_ml_training"]:
                await self._maybe_train_model()
            
            self.scan_count += 1
            self.last_scan_time = datetime.now()
            
            logger.info(f"Scan cycle complete in {cycle_time:.2f}s - "
                       f"{len(signals)} signals, {len(high_confidence)} high confidence")
            
            return {
                "success": True,
                "signals_found": len(signals),
                "high_confidence": len(high_confidence),
                "cycle_time": cycle_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Scan cycle failed: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    async def _check_exits(self):
        """Check existing positions for exit conditions"""
        open_positions = self.get_open_positions()
        
        for pos in open_positions:
            try:
                # Get current price (simulated - would be real API call)
                current_price = await self._get_current_price(pos['symbol'])
                
                if not current_price:
                    continue
                
                entry = pos.get('entry_price', 0)
                tp = pos.get('take_profit', 0)
                sl = pos.get('stop_loss', 0)
                entry_time = datetime.fromisoformat(pos.get('entry_date', datetime.now().isoformat()))
                
                pnl_pct = (current_price - entry) / entry * 100
                
                # Check exit conditions
                exit_triggered = False
                exit_reason = ""
                exit_price = current_price
                
                # Take profit
                if current_price >= tp:
                    exit_triggered = True
                    exit_reason = "TP_HIT"
                    exit_price = tp
                # Stop loss
                elif current_price <= sl:
                    exit_triggered = True
                    exit_reason = "SL_HIT"
                    exit_price = sl
                # Time exit
                elif (datetime.now() - entry_time).total_seconds() > (self.config["time_exit_hours"] * 3600):
                    exit_triggered = True
                    exit_reason = "TIME_EXIT"
                
                if exit_triggered:
                    pnl_pct = (exit_price - entry) / entry * 100
                    self._close_position(pos['id'], exit_price, exit_reason, pnl_pct)
                    logger.info(f"Closed {pos['symbol']}: {exit_reason} at ${exit_price:,.2f} ({pnl_pct:+.2f}%)")
                    
            except Exception as e:
                logger.error(f"Error checking exits for {pos.get('symbol')}: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price (simplified - would use real API)"""
        # This is a placeholder - in production would use Binance/Exchange API
        # For now, simulate small random movement
        import random
        
        # Try to get from last known price in database
        df = self.store.get_signals(symbol=symbol, limit=1)
        if not df.empty:
            base_price = df.iloc[0]['price']
            # Add small random movement (-0.5% to +0.5%)
            movement = random.uniform(-0.005, 0.005)
            return base_price * (1 + movement)
        
        return None
    
    async def _create_positions(self, signals: List[Dict]):
        """Create new positions from signals"""
        for signal in signals[:self.config["max_positions"] - len(self.get_open_positions())]:
            try:
                pick = {
                    "algorithm": signal.get('algorithm', 'unknown'),
                    "symbol": signal['symbol'],
                    "category": "crypto",
                    "tier": "TIER_1",
                    "entry_price": signal['entry'],
                    "status": "OPEN",
                    "reason": signal.get('reason', ''),
                    "regime": "bull",
                    "regime_confidence": 0.6,
                    "breadth_pct": 60.0,
                    "vol_20d": 0.025,
                    "rsi_at_entry": 50,
                    "volume_ratio": signal.get('metadata', {}).get('volume_ratio', 1.0),
                    "ml_win_prob": signal.get('win_probability', 0.5),
                    "features": {
                        "entry": signal['entry'],
                        "tp": signal.get('take_profit'),
                        "sl": signal.get('stop_loss'),
                        "win_prob": signal.get('win_probability')
                    }
                }
                
                pick_id = self.store.write_pick(pick)
                logger.info(f"Created position {pick_id} for {signal['symbol']} at ${signal['entry']:,.2f}")
                
            except Exception as e:
                logger.error(f"Error creating position for {signal.get('symbol')}: {e}")
    
    def _close_position(self, pick_id: str, exit_price: float, 
                       exit_reason: str, pnl_pct: float):
        """Close a position"""
        self.store.close_pick(pick_id, exit_price, exit_reason, pnl_pct)
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        if not self.store:
            return []
        
        df = self.store.get_open_picks()
        if df.empty:
            return []
        
        return df.to_dict('records')
    
    def _update_metrics(self, scan_results: Dict, cycle_time: float):
        """Update performance metrics"""
        # Get current summary
        perf = self.store.get_performance_summary(days=self.config["performance_window_days"])
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "scan_count": self.scan_count,
            "cycle_time": cycle_time,
            "signals_found": scan_results.get('signals_generated', 0),
            "high_confidence": scan_results.get('high_confidence_signals', 0),
            "win_rate": perf.get('win_rate', 0),
            "total_pnl": perf.get('total_pnl_pct', 0),
            "open_positions": len(self.get_open_positions())
        }
        
        self.performance_history.append(metric)
        self._save_performance_history()
        
        # Update status file for dashboard
        self._update_status_file(metric)
    
    def _update_status_file(self, metric: Dict):
        """Update status file for external monitoring"""
        status = {
            "system": "KIMI_FEB172026",
            "version": self.VERSION,
            "status": "running" if self.is_running else "stopped",
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "scan_count": self.scan_count,
            "error_count": self.error_count,
            "open_positions": metric.get('open_positions', 0),
            "current_metrics": metric,
            "config": self.config
        }
        
        status_path = self.data_dir / "system_status.json"
        with open(status_path, 'w') as f:
            json.dump(status, f, indent=2, default=str)
    
    async def _maybe_train_model(self):
        """Train ML model if enough data and time elapsed"""
        # Check if we should train
        last_training = self.data_dir / "last_ml_training.txt"
        
        if last_training.exists():
            with open(last_training, 'r') as f:
                last_time = datetime.fromisoformat(f.read().strip())
            
            hours_since = (datetime.now() - last_time).total_seconds() / 3600
            if hours_since < self.config["ml_training_interval_hours"]:
                return
        
        # Get training data
        df = self.store.get_closed_picks(min_picks=50)
        
        if len(df) < 50:
            logger.info(f"Not enough data for ML training (have {len(df)}, need 50)")
            return
        
        logger.info(f"Training ML model with {len(df)} samples...")
        
        try:
            # Prepare training data
            picks_data = df.to_dict('records')
            stats = self.ml_ranker.train_if_ready(picks_data)
            
            if stats.get('status') == 'trained':
                logger.info(f"✓ Model trained! Accuracy: {stats.get('accuracy', 0):.2%}")
                
                with open(last_training, 'w') as f:
                    f.write(datetime.now().isoformat())
            else:
                logger.info(f"Model training status: {stats.get('status')}")
                
        except Exception as e:
            logger.error(f"ML training failed: {e}")
    
    async def run_continuous(self):
        """Run continuously with scheduled scans"""
        self.is_running = True
        
        logger.info("Starting continuous operation...")
        logger.info(f"Scan interval: {self.config['scan_interval_minutes']} minutes")
        
        # Run initial scan immediately
        await self.run_scan_cycle()
        
        while self.is_running:
            try:
                # Wait for next scan interval
                await asyncio.sleep(self.config["scan_interval_minutes"] * 60)
                
                # Check if we should run (market hours, etc.)
                if self._should_run_scan():
                    await self.run_scan_cycle()
                else:
                    logger.info("Skipping scan (outside market hours)")
                    
            except asyncio.CancelledError:
                logger.info("Scan loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
                self.error_count += 1
                # Brief pause before retry
                await asyncio.sleep(10)
    
    def _should_run_scan(self) -> bool:
        """Check if scan should run based on configuration"""
        now = datetime.now()
        
        # If crypto 24h mode, always run
        if self.config.get("crypto_24h", True):
            return True
        
        # Otherwise check market hours (simplified)
        hour = now.hour
        day = now.weekday()
        
        # Skip weekends for stocks
        if day >= 5 and not self.config.get("crypto_24h"):
            return False
        
        # Market hours: 9:30 AM - 4:00 PM EST
        if self.config.get("market_hours_only", False):
            return 9 <= hour < 16
        
        return True
    
    def stop(self):
        """Stop the autonomous trader"""
        logger.info("Stopping autonomous trader...")
        self.is_running = False
        self._update_status_file({"status": "stopped"})
    
    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            "is_running": self.is_running,
            "scan_count": self.scan_count,
            "error_count": self.error_count,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "open_positions": len(self.get_open_positions()),
            "config": self.config
        }


# =============================================================================
# Windows Service / Background Runner
# =============================================================================
class BackgroundRunner:
    """Run trader in background as a service-like process"""
    
    def __init__(self):
        self.trader = AutonomousTrader()
        self.loop = None
        self.task = None
    
    def start(self):
        """Start background execution"""
        if not self.trader.initialize():
            logger.error("Failed to initialize trader")
            return False
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.trader.run_continuous())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.stop()
        except Exception as e:
            logger.error(f"Background runner error: {e}")
            return False
        
        return True
    
    def stop(self):
        """Stop background execution"""
        if self.trader:
            self.trader.stop()
        
        if self.loop:
            self.loop.stop()


# =============================================================================
# Entry Points
# =============================================================================
def run_once():
    """Run a single scan cycle (for cron jobs)"""
    trader = AutonomousTrader()
    
    if not trader.initialize():
        sys.exit(1)
    
    result = asyncio.run(trader.run_scan_cycle())
    
    if result.get("success"):
        print(f"Scan complete: {result['signals_found']} signals found")
        sys.exit(0)
    else:
        print(f"Scan failed: {result.get('error')}")
        sys.exit(1)


def run_continuous():
    """Run continuous mode"""
    runner = BackgroundRunner()
    
    try:
        runner.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        runner.stop()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="KIMI_FEB172026 Autonomous Trader")
    parser.add_argument("--once", action="store_true", help="Run single scan and exit")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--config", type=str, help="Path to config file")
    
    args = parser.parse_args()
    
    if args.status:
        trader = AutonomousTrader()
        status = trader.get_status()
        print(json.dumps(status, indent=2, default=str))
        return
    
    if args.once:
        run_once()
    else:
        run_continuous()


if __name__ == "__main__":
    main()
