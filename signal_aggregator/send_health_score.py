#!/usr/bin/env python3
"""
Send Master-Picks Health Score to Discord

This script sends the current health score of master-picks to the 
#master-picks Discord channel.

Usage:
    python send_health_score.py

Environment Variables:
    DISCORD_MASTER_PICKS: Webhook URL for #master-picks channel
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Send health score to Discord."""
    # Check for webhook
    webhook_url = os.getenv('DISCORD_MASTER_PICKS')
    if not webhook_url:
        logger.warning("DISCORD_MASTER_PICKS not set; skipping health score send")
        return 0
    
    # Import and send
    try:
        from signal_aggregator.picks_router import PicksRouter
        
        router = PicksRouter()
        success = router.send_master_picks_health_score()
        
        if success:
            logger.info("Health score sent successfully")
            return 0
        else:
            logger.warning("Health score send returned false; treating as non-fatal")
            return 0
            
    except Exception as e:
        logger.warning(f"Health score send error (non-fatal): {e}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
