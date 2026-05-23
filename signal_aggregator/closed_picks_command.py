#!/usr/bin/env python3
"""
Closed Picks Command Handler

Sends closed master-picks summary to Discord when triggered.
Can be used as a Discord command (!closed) or run manually.

Usage:
    python closed_picks_command.py [days]
    
Arguments:
    days: Number of days to look back (default: 30)

Environment Variables:
    DISCORD_MASTER_PICKS: Webhook URL for #master-picks channel
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Send closed picks summary to Discord."""
    # Parse args
    days = 30
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid days argument: {sys.argv[1]}")
            sys.exit(1)
    
    # Check for webhook
    webhook_url = os.getenv('DISCORD_MASTER_PICKS')
    if not webhook_url:
        logger.error("DISCORD_MASTER_PICKS environment variable not set")
        sys.exit(1)
    
    # Import and send
    try:
        from signal_aggregator.picks_router import PicksRouter
        
        router = PicksRouter()
        success = router.send_closed_picks_summary(days=days)
        
        if success:
            logger.info(f"Closed picks summary sent successfully ({days}d)")
            sys.exit(0)
        else:
            logger.error("Failed to send closed picks summary")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
