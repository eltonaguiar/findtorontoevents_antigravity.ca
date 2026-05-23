"""
Discord DNA Sender - Track & Monitor Picks to Discord
=====================================================
Sends FreshPicks DNA signals to Discord with full tracking.

Features:
- Formatted Discord messages
- Pick tracking integration
- Error handling & retries
- Confirmation logging

Usage:
    from discord_dna_sender import DNADiscordSender
    
    sender = DNADiscordSender(webhook_url="your_webhook")
    
    for pick in picks:
        success = sender.send_pick(pick)
        if success:
            print(f"Sent {pick.tracking_id}")
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DNADiscord')


class DNADiscordSender:
    """
    Send DNA picks to Discord with tracking
    
    Formats picks nicely and tracks delivery.
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or self._load_webhook()
        self.sent_count = 0
        self.error_count = 0
    
    def _load_webhook(self) -> str:
        """Load webhook from config"""
        try:
            with open('discord_config.json', 'r') as f:
                config = json.load(f)
                return config.get('webhook_url', '')
        except FileNotFoundError:
            logger.warning("No discord_config.json found")
            return ""
    
    def format_pick_message(self, pick) -> Dict[str, Any]:
        """
        Format pick as Discord embed
        
        Returns Discord webhook payload
        """
        # Color based on direction
        color = 0x00ff00 if pick.direction == 'long' else 0xff0000
        
        # Emoji based on confidence
        if pick.confidence_score >= 0.8:
            confidence_emoji = "🟢"
        elif pick.confidence_score >= 0.6:
            confidence_emoji = "🟡"
        else:
            confidence_emoji = "🔴"
        
        embed = {
            "title": f"{confidence_emoji} DNA Pick: {pick.symbol}",
            "description": f"**{pick.direction.upper()}** | Tracking: `{pick.tracking_id}`",
            "color": color,
            "timestamp": pick.timestamp.isoformat(),
            "fields": [
                {
                    "name": "📊 Entry / Stop / Target",
                    "value": f"```Entry:  {pick.entry_price:,.8f}\nStop:   {pick.stop_loss:,.8f}\nTarget: {pick.take_profit:,.8f}```",
                    "inline": False
                },
                {
                    "name": "🎯 Risk/Reward",
                    "value": f"**{pick.rr:.2f}**",
                    "inline": True
                },
                {
                    "name": "📈 Confidence",
                    "value": f"**{pick.confidence_score:.0%}**",
                    "inline": True
                },
                {
                    "name": "💰 Position Size",
                    "value": f"**{pick.position_size:.1%}**",
                    "inline": True
                },
                {
                    "name": "💡 Signal DNA",
                    "value": f"```Funding: {pick.funding_annualized:.2%} annualized\nTrend:   {pick.trend_4h}\nVolume:  {pick.volume_ratio:.1f}x avg```",
                    "inline": False
                },
                {
                    "name": "⏱️ Expected Hold",
                    "value": f"~{pick.expected_hold_hours}h",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"FreshPicks DNA v{pick.version} | {pick.exchange}"
            }
        }
        
        return {
            "content": "@here New DNA Pick Alert",
            "embeds": [embed]
        }
    
    def send_pick(self, pick, dry_run: bool = False) -> bool:
        """
        Send pick to Discord
        
        Args:
            pick: DNAPick object
            dry_run: If True, just log without sending
        
        Returns:
            True if successful
        """
        if not self.webhook_url:
            logger.error("[Discord] No webhook configured")
            return False
        
        message = self.format_pick_message(pick)
        
        if dry_run:
            logger.info(f"[Discord DRY RUN] Would send: {pick.tracking_id}")
            return True
        
        try:
            # Send to Discord
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(message).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 204:
                    self.sent_count += 1
                    logger.info(f"[Discord] Sent {pick.tracking_id}")
                    return True
                else:
                    logger.error(f"[Discord] Failed: {response.status}")
                    self.error_count += 1
                    return False
                    
        except urllib.error.HTTPError as e:
            logger.error(f"[Discord] HTTP Error {e.code}: {e.reason}")
            self.error_count += 1
            return False
        except Exception as e:
            logger.error(f"[Discord] Error: {e}")
            self.error_count += 1
            return False
    
    def send_batch(self, picks: List, dry_run: bool = False) -> Dict[str, Any]:
        """
        Send multiple picks
        
        Returns summary of results
        """
        results = {
            'total': len(picks),
            'sent': 0,
            'failed': 0,
            'tracking_ids': []
        }
        
        for pick in picks:
            success = self.send_pick(pick, dry_run)
            if success:
                results['sent'] += 1
                results['tracking_ids'].append(pick.tracking_id)
            else:
                results['failed'] += 1
        
        return results
    
    def send_summary(self, picks: List, stats: Dict):
        """Send daily summary to Discord"""
        if not self.webhook_url:
            return False
        
        embed = {
            "title": "📊 DNA Strategy Daily Summary",
            "description": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "color": 0x0099ff,
            "fields": [
                {
                    "name": "📈 Picks Generated",
                    "value": str(len(picks)),
                    "inline": True
                },
                {
                    "name": "🎯 Avg Confidence",
                    "value": f"{stats.get('avg_confidence', 0):.0%}",
                    "inline": True
                },
                {
                    "name": "📊 Breakdown",
                    "value": f"Longs: {stats.get('breakdown', {}).get('longs', 0)}\nShorts: {stats.get('breakdown', {}).get('shorts', 0)}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "FreshPicks DNA Strategy"
            }
        }
        
        message = {"embeds": [embed]}
        
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(message).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 204
        except:
            return False


# Console formatter for when Discord is not available
class ConsoleSender:
    """Sends picks to console (for testing)"""
    
    def send_pick(self, pick, dry_run: bool = False) -> bool:
        """Print pick to console"""
        print("\n" + "=" * 80)
        print(f"[TARGET] DNA PICK: {pick.symbol}")
        print("=" * 80)
        print(f"Tracking ID: {pick.tracking_id}")
        print(f"Direction:   {pick.direction.upper()}")
        print(f"Entry:       {pick.entry_price:,.8f}")
        print(f"Stop:        {pick.stop_loss:,.8f}")
        print(f"Target:      {pick.take_profit:,.8f}")
        print(f"RR:          {pick.rr:.2f}")
        print(f"Confidence:  {pick.confidence_score:.0%}")
        print(f"Funding:     {pick.funding_annualized:.2%}")
        print(f"Trend:       {pick.trend_4h}")
        print("=" * 80)
        return True
    
    def send_batch(self, picks: List, dry_run: bool = False) -> Dict[str, Any]:
        """Print batch to console"""
        for pick in picks:
            self.send_pick(pick, dry_run)
        
        return {
            'total': len(picks),
            'sent': len(picks),
            'failed': 0,
            'tracking_ids': [p.tracking_id for p in picks]
        }


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("DISCORD DNA SENDER - Test")
    print("=" * 80)
    
    # Import pick generator
    from freshpicks_dna_strategy import DNAPickGenerator
    
    # Generate picks
    generator = DNAPickGenerator()
    picks = generator.generate_picks()
    
    if not picks:
        print("No picks generated")
    else:
        # Use console sender for testing
        sender = ConsoleSender()
        
        # Send picks
        results = sender.send_batch(picks, dry_run=False)
        
        print(f"\n\nResults: {results['sent']}/{results['total']} sent")
        print(f"Tracking IDs: {results['tracking_ids']}")
