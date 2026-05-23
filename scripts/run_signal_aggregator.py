#!/usr/bin/env python3
"""
Signal Aggregator Automation Script
Run periodically to poll systems, generate consensus signals, and update dashboard.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/signal_aggregator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_aggregator():
    """Run the signal aggregator and update dashboard."""
    try:
        logger.info("Starting signal aggregator run...")
        
        # Import aggregator
        from signal_aggregator.aggregator import SignalAggregator
        
        # Initialize and run
        aggregator = SignalAggregator()
        consensus_signals = aggregator.run_aggregation()
        
        # Generate dashboard data
        dashboard_data = aggregator.generate_dashboard_data()
        
        # Save dashboard data
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        data_dir = project_root / 'signal_aggregator' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        
        dashboard_path = data_dir / 'dashboard_data.json'
        import json
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        logger.info(f"Signal aggregation completed. {len(consensus_signals)} consensus signals generated.")
        logger.info(f"Dashboard data saved to: {dashboard_path}")
        
        # Update system registry metrics
        from signal_aggregator.system_registry import SystemRegistry
        registry = SystemRegistry()
        
        # Try to calculate portfolio diversification with default weights
        try:
            # Create default weights based on reliability scores
            system_weights = {}
            for name, data in registry.registry.items():
                weight = data.get("reliability_score", 0.5)
                system_weights[name] = weight
            
            diversification = registry.calculate_portfolio_diversification(system_weights)
            logger.info(f"Portfolio diversification: {diversification}")
        except Exception as e:
            logger.warning(f"Could not calculate portfolio diversification: {e}")
        
        # Export to CSV for analysis
        csv_path = registry.export_to_csv()
        logger.info(f"System registry exported to: {csv_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error running signal aggregator: {e}", exc_info=True)
        return False

def update_hub_data():
    """Copy dashboard data to hub directory for web display."""
    try:
        import shutil
        import json
        
        # Source and destination paths
        src_path = Path('signal_aggregator/data/dashboard_data.json')
        dest_path = Path('hub/data/dashboard_data.json')
        
        # Ensure hub data directory exists
        dest_path.parent.mkdir(exist_ok=True)
        
        # Copy the file
        shutil.copy2(src_path, dest_path)
        
        # Also create a simplified version for quick loading
        with open(src_path, 'r') as f:
            data = json.load(f)
        
        simplified = {
            "last_update": data.get("last_update"),
            "active_systems": data.get("active_systems"),
            "total_consensus_signals": data.get("total_consensus_signals"),
            "top_signals": data.get("top_signals", [])[:3],
            "performance_metrics": data.get("performance_metrics", {})
        }
        
        simplified_path = Path('hub/data/simplified_dashboard.json')
        with open(simplified_path, 'w') as f:
            json.dump(simplified, f, indent=2)
        
        logger.info(f"Hub data updated: {dest_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating hub data: {e}")
        return False

def send_notifications():
    """Send notifications for high-confidence signals."""
    try:
        # Load consensus signals
        consensus_path = Path('signal_aggregator/data/consensus_signals.json')
        if consensus_path.exists():
            import json
            with open(consensus_path, 'r') as f:
                data = json.load(f)
            
            high_confidence_signals = [
                sig for sig in data.get('signals', [])
                if sig.get('confidence', 0) >= 0.75
            ]
            
            if high_confidence_signals:
                logger.info(f"Found {len(high_confidence_signals)} high-confidence signals")
                
                # Log them for now (can extend to Discord/email later)
                for sig in high_confidence_signals[:5]:  # Limit to top 5
                    logger.info(
                        f"High-confidence signal: {sig.get('symbol')} "
                        f"{sig.get('direction')} @ {sig.get('entry_price')} "
                        f"(Confidence: {sig.get('confidence'):.2f})"
                    )
                
                return len(high_confidence_signals)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='Signal Aggregator Automation')
    parser.add_argument('--mode', choices=['full', 'quick', 'hub-only'], 
                       default='full', help='Run mode')
    parser.add_argument('--notify', action='store_true', 
                       help='Send notifications for high-confidence signals')
    
    args = parser.parse_args()
    
    logger.info(f"Signal aggregator automation started (mode: {args.mode})")
    
    success = True
    
    if args.mode in ['full', 'quick']:
        # Run aggregator
        if not run_aggregator():
            success = False
    
    if args.mode in ['full', 'hub-only']:
        # Update hub data
        if not update_hub_data():
            success = False
    
    if args.notify:
        # Send notifications
        signal_count = send_notifications()
        logger.info(f"Notifications sent for {signal_count} signals")
    
    # Health check
    try:
        # Verify dashboard data exists and is recent
        dashboard_path = Path('signal_aggregator/data/dashboard_data.json')
        if dashboard_path.exists():
            import json
            from datetime import datetime, timezone
            with open(dashboard_path, 'r') as f:
                data = json.load(f)
            
            last_update = data.get('last_update')
            if last_update:
                # Parse ISO format timestamp
                update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                age = (now - update_time).total_seconds()
                
                if age > 3600:  # 1 hour
                    logger.warning(f"Dashboard data is {age/3600:.1f} hours old")
                else:
                    logger.info(f"Dashboard data is {age/60:.0f} minutes old")
    except Exception as e:
        logger.warning(f"Health check warning: {e}")
    
    if success:
        logger.info("Signal aggregator automation completed successfully")
        return 0
    else:
        logger.error("Signal aggregator automation completed with errors")
        return 1

if __name__ == '__main__':
    sys.exit(main())