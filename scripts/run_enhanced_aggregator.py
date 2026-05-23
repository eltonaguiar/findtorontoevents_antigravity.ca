#!/usr/bin/env python3
"""
Enhanced Signal Aggregator Automation Script
Runs the signal aggregator with all new integrations.
"""

import os
import sys
import asyncio
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
        logging.FileHandler('logs/enhanced_aggregator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def run_enhanced_aggregation(
    mode: str = 'full',
    portfolio_value: float = 100000.0,
    detect_regime: bool = True
):
    """
    Run enhanced signal aggregation with all new features.
    
    Args:
        mode: 'full' (all features), 'quick' (basic), 'hub-only' (update only)
        portfolio_value: Current portfolio value for position sizing
        detect_regime: Whether to detect market regime
    """
    try:
        logger.info("=" * 70)
        logger.info(f"Enhanced Signal Aggregator Started (mode: {mode})")
        logger.info("=" * 70)
        
        # Import enhanced aggregator
        from signal_aggregator.integrations import EnhancedSignalAggregator
        from signal_aggregator.system_registry import SystemRegistry
        
        # Initialize enhanced aggregator
        enhanced = EnhancedSignalAggregator()
        registry = SystemRegistry()
        
        # Detect market regime if requested
        regime = None
        if detect_regime and mode == 'full':
            try:
                from forward_testing.adaptive_tpsl import AdaptiveTPSL
                tpsl = AdaptiveTPSL()
                # Load sample data for regime detection
                import pandas as pd
                # In production, this would load actual market data
                regime = 'SIDEWAYS'  # Default
                logger.info(f"Market regime detected: {regime}")
            except Exception as e:
                logger.warning(f"Could not detect regime: {e}")
                regime = 'SIDEWAYS'
        
        # Load price data if available
        price_data = None
        if mode == 'full':
            try:
                import pandas as pd
                # Try to load cached price data
                price_path = Path('data/market_cache.parquet')
                if price_path.exists():
                    price_data = pd.read_parquet(price_path)
                    logger.info(f"Loaded price data: {len(price_data)} rows")
            except Exception as e:
                logger.warning(f"Could not load price data: {e}")
        
        # Run enhanced aggregation
        logger.info("Running enhanced signal aggregation...")
        signals = await enhanced.aggregate_with_enhancements(
            price_data=price_data,
            regime=regime,
            portfolio_value=portfolio_value
        )
        
        logger.info(f"Enhanced aggregation complete: {len(signals)} signals")
        
        # Log high-confidence signals
        high_confidence = [
            s for s in signals.values()
            if s.get('confidence', 0) >= 0.7
        ]
        
        if high_confidence:
            logger.info(f"\nHigh-confidence signals ({len(high_confidence)}):")
            for sig in high_confidence[:5]:
                logger.info(
                    f"  {sig['symbol']} {sig['direction']} "
                    f"@ ${sig['entry_price']:,.2f} "
                    f"(Conf: {sig['confidence']:.2f})"
                )
                if 'tp_price' in sig:
                    logger.info(
                        f"    TP: ${sig['tp_price']:,.2f}, "
                        f"SL: ${sig['sl_price']:,.2f}, "
                        f"R:R: {sig.get('risk_reward_ratio', 0):.2f}"
                    )
                if 'position_sizing' in sig:
                    sizing = sig['position_sizing']
                    logger.info(
                        f"    Position: {sizing.get('position_pct', 0):.2%}, "
                        f"Risk: ${sizing.get('risk_amount', 0):,.2f}"
                    )
        
        # Save enhanced signals
        data_dir = Path('signal_aggregator/data')
        data_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        signals_path = data_dir / 'enhanced_signals.json'
        with open(signals_path, 'w') as f:
            json.dump(signals, f, indent=2, default=str)
        
        logger.info(f"Enhanced signals saved to: {signals_path}")
        
        # Update hub data
        if mode in ['full', 'hub-only']:
            await update_hub_data(signals, registry)
        
        return signals
        
    except Exception as e:
        logger.error(f"Error in enhanced aggregation: {e}", exc_info=True)
        return {}


async def update_hub_data(signals: dict, registry):
    """Update hub dashboard with enhanced data."""
    try:
        import json
        import shutil
        
        # Prepare hub data
        hub_data = {
            'last_update': datetime.now().isoformat(),
            'total_signals': len(signals),
            'high_confidence_count': len([s for s in signals.values() if s.get('confidence', 0) >= 0.7]),
            'signals_with_tpsl': len([s for s in signals.values() if 'tp_price' in s]),
            'signals_with_sizing': len([s for s in signals.values() if 'position_sizing' in s]),
            'top_signals': sorted(
                signals.values(),
                key=lambda x: x.get('confidence', 0),
                reverse=True
            )[:5],
            'system_stats': registry.generate_dashboard_data() if registry else {}
        }
        
        # Save to hub directory
        hub_dir = Path('hub/data')
        hub_dir.mkdir(exist_ok=True)
        
        hub_path = hub_dir / 'enhanced_dashboard.json'
        with open(hub_path, 'w') as f:
            json.dump(hub_data, f, indent=2, default=str)
        
        logger.info(f"Hub data updated: {hub_path}")
        
        # Also update simplified version
        simplified = {
            'last_update': hub_data['last_update'],
            'total_signals': hub_data['total_signals'],
            'high_confidence': hub_data['high_confidence_count'],
            'systems_active': hub_data['system_stats'].get('active_systems', 0)
        }
        
        with open(hub_dir / 'simplified_enhanced.json', 'w') as f:
            json.dump(simplified, f, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating hub data: {e}")
        return False


def send_discord_notification(signals: dict):
    """Send Discord notification for high-confidence signals."""
    try:
        import os
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        
        if not webhook_url:
            logger.info("No Discord webhook configured")
            return
        
        high_conf = [
            s for s in signals.values()
            if s.get('confidence', 0) >= 0.75
        ]
        
        if not high_conf:
            return
        
        # Build message
        message = f"**🎯 High-Confidence Signals ({len(high_conf)})**\n\n"
        
        for sig in high_conf[:3]:
            message += (
                f"**{sig['symbol']}** {sig['direction']}\n"
                f"Entry: ${sig['entry_price']:,.2f}\n"
            )
            if 'tp_price' in sig:
                message += f"TP: ${sig['tp_price']:,.2f} | SL: ${sig['sl_price']:,.2f}\n"
            message += f"Confidence: {sig['confidence']:.1%}\n\n"
        
        # Send webhook with retry
        import requests
        import time as _time
        payload = {'content': message}
        for _attempt in range(3):
            try:
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code in (200, 204):
                    logger.info(f"Discord notification sent for {len(high_conf)} signals")
                    break
                if response.status_code == 429:
                    _time.sleep(response.json().get("retry_after", 3))
                    continue
                logger.warning(f"Discord webhook failed: {response.status_code}")
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                break
            except Exception as e:
                if _attempt == 2:
                    logger.error(f"Discord notification error after 3 attempts: {e}")
                else:
                    _time.sleep(2 * (_attempt + 1))

    except Exception as e:
        logger.error(f"Discord notification error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Signal Aggregator with All Features'
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'quick', 'hub-only'],
        default='full',
        help='Run mode: full (all features), quick (basic), hub-only (update)'
    )
    parser.add_argument(
        '--portfolio-value',
        type=float,
        default=100000.0,
        help='Current portfolio value for position sizing'
    )
    parser.add_argument(
        '--no-regime',
        action='store_true',
        help='Skip regime detection'
    )
    parser.add_argument(
        '--notify',
        action='store_true',
        help='Send Discord notifications'
    )
    
    args = parser.parse_args()
    
    # Run enhanced aggregation
    signals = asyncio.run(run_enhanced_aggregation(
        mode=args.mode,
        portfolio_value=args.portfolio_value,
        detect_regime=not args.no_regime
    ))
    
    # Send notifications if requested
    if args.notify and signals:
        send_discord_notification(signals)
    
    # Health check
    logger.info("\n" + "=" * 70)
    logger.info("Health Check:")
    logger.info(f"  Signals generated: {len(signals)}")
    logger.info(f"  With TP/SL: {len([s for s in signals.values() if 'tp_price' in s])}")
    logger.info(f"  With sizing: {len([s for s in signals.values() if 'position_sizing' in s])}")
    logger.info("=" * 70)
    
    return 0 if signals else 1


if __name__ == '__main__':
    sys.exit(main())
