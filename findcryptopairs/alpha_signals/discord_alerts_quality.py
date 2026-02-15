#!/usr/bin/env python3
"""
Discord Alert Bot with Quality Gates
"Are We Sure?" - Only sends Discord alerts when we have statistical evidence

SETUP:
1. Set DISCORD_WEBHOOK_URL environment variable
2. Import and use send_quality_alert() instead of raw webhook calls
3. All alerts pass through quality gates automatically
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from alert_system_v2_quality_gates import QualityGatedAlertSystem, ConfidenceTier


@dataclass
class DiscordAlertConfig:
    """Configuration for Discord alerts"""
    webhook_url: str = None
    min_adjusted_confidence: float = 60.0  # After quality gates
    
    # Role mentions by tier (optional)
    role_mentions: Dict[ConfidenceTier, str] = None
    
    # Channel filtering
    suppress_early_guess: bool = True
    suppress_emerging: bool = True
    suppress_validated: bool = False  # Allow but with warning
    suppress_proven: bool = False
    suppress_certain: bool = False
    suppress_institutional: bool = False
    
    def __post_init__(self):
        if self.webhook_url is None:
            self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
        if self.role_mentions is None:
            self.role_mentions = {
                ConfidenceTier.INSTITUTIONAL: "@everyone",  # Ping everyone for institutional
                ConfidenceTier.CERTAIN: "@here",            # Ping online for certain
                # Others don't ping
            }


class DiscordQualityAlertBot:
    """
    Discord bot that only sends alerts when we're "SURE"
    
    QUALITY PRINCIPLES:
    1. Suppress all "early guess" signals (<50 trades)
    2. Only validated strategies (50+ trades, 55%+ WR) get alerts
    3. Clear "how sure" indicators in every alert
    4. Position sizing recommendations based on validation level
    """
    
    def __init__(self, config: DiscordAlertConfig = None):
        self.config = config or DiscordAlertConfig()
        self.quality_system = QualityGatedAlertSystem()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Color coding by tier
        self.tier_colors = {
            ConfidenceTier.INSTITUTIONAL: 0xFFD700,    # Gold
            ConfidenceTier.CERTAIN: 0x00FF00,          # Green
            ConfidenceTier.PROVEN: 0x00AA00,           # Dark Green
            ConfidenceTier.VALIDATED: 0xFFA500,        # Orange
            ConfidenceTier.EMERGING: 0x808080,         # Gray
            ConfidenceTier.EARLY_GUESS: 0xFF0000,      # Red
        }
        
        # Stats tracking
        self.stats = {
            'sent': 0,
            'suppressed': 0,
            'by_tier': {tier: 0 for tier in ConfidenceTier}
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _build_discord_embed(self,
                            symbol: str,
                            signal_type: str,
                            entry: float,
                            stop: float,
                            target: float,
                            strategy_id: str,
                            base_confidence: float,
                            adjusted_confidence: float,
                            sureness_statement: str,
                            tier: ConfidenceTier,
                            metrics=None,
                            timeframe: str = "1h",
                            chart_url: str = None) -> Dict:
        """Build Discord embed with quality indicators"""
        
        # Calculate R:R
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        
        # Emoji for signal type
        signal_emoji = "🟢" if signal_type.lower() == "buy" else "🔴" if signal_type.lower() == "sell" else "⚪"
        
        # Tier emoji
        tier_emoji = {
            ConfidenceTier.INSTITUTIONAL: "🏆",
            ConfidenceTier.CERTAIN: "🎯",
            ConfidenceTier.PROVEN: "✅",
            ConfidenceTier.VALIDATED: "⚠️",
            ConfidenceTier.EMERGING: "🔍",
            ConfidenceTier.EARLY_GUESS: "❌"
        }.get(tier, "❓")
        
        # Position size recommendation
        if tier == ConfidenceTier.INSTITUTIONAL:
            position_guidance = "🏆 FULL SIZE (2-3% risk)"
            position_details = "Institutional-grade signal. Standard position sizing."
        elif tier == ConfidenceTier.CERTAIN:
            position_guidance = "✅ NORMAL SIZE (1.5-2% risk)"
            position_details = "High confidence. Standard position sizing."
        elif tier == ConfidenceTier.PROVEN:
            position_guidance = "⚠️ REDUCED SIZE (1-1.5% risk)"
            position_details = "Proven but watchful. Consider 75% target."
        elif tier == ConfidenceTier.VALIDATED:
            position_guidance = "🔍 TEST SIZE (0.5-1% risk)"
            position_details = "Still validating. Tighter stops. Scale 50% at first target."
        else:
            position_guidance = "❌ PAPER ONLY"
            position_details = "Insufficient data for live trading."
        
        # Build fields
        fields = [
            {
                "name": "📊 Confidence Assessment",
                "value": f"Base: {base_confidence:.0f}/100 → Adjusted: {adjusted_confidence:.0f}/100\n{tier_emoji} {tier.value.upper().replace('_', ' ')}",
                "inline": False
            },
            {
                "name": "💰 Trade Setup",
                "value": f"Entry: ${entry:,.8f}\nStop: ${stop:,.8f} ({((stop/entry)-1)*100:+.1f}%)\nTarget: ${target:,.8f} ({((target/entry)-1)*100:+.1f}%)\nR:R = 1:{rr:.1f}",
                "inline": True
            },
            {
                "name": "📈 Strategy Stats",
                "value": f"ID: {strategy_id}\nTrades: {metrics.total_trades if metrics else 'N/A'}\nWin Rate: {metrics.win_rate:.1% if metrics else 'N/A'}\nSharpe: {metrics.sharpe_ratio:.2f if metrics else 'N/A'}",
                "inline": True
            },
            {
                "name": "🛡️ Position Sizing",
                "value": f"{position_guidance}\n{position_details}",
                "inline": False
            },
            {
                "name": "🔍 How Sure Are We?",
                "value": sureness_statement[:1024],  # Discord field limit
                "inline": False
            }
        ]
        
        # Add warning for lower tiers
        if tier == ConfidenceTier.VALIDATED:
            fields.append({
                "name": "⚠️ CAUTION",
                "value": "This strategy meets minimum thresholds but is still building track record. Use smaller size.",
                "inline": False
            })
        
        embed = {
            "title": f"{signal_emoji} {symbol} {signal_type.upper()} SIGNAL",
            "description": f"Quality-gated alert from {strategy_id}",
            "color": self.tier_colors.get(tier, 0x808080),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": fields,
            "footer": {
                "text": f"Timeframe: {timeframe} | Quality Bot v2.0 | Suppressed: {self.stats['suppressed']} | Sent: {self.stats['sent']}"
            }
        }
        
        if chart_url:
            embed["image"] = {"url": chart_url}
        
        return embed
    
    async def send_alert(self,
                        symbol: str,
                        signal_type: str,
                        entry: float,
                        stop: float,
                        target: float,
                        strategy_id: str,
                        base_confidence: float,
                        timeframe: str = "1h",
                        chart_url: str = None,
                        extra_notes: str = None) -> Tuple[bool, str]:
        """
        Send Discord alert with quality gates
        
        Returns: (was_sent: bool, message: str)
        """
        
        # Check quality gates
        should_alert, adjusted_confidence, sureness_statement = \
            self.quality_system.evaluate_signal_quality(strategy_id, base_confidence)
        
        if not should_alert:
            self.stats['suppressed'] += 1
            
            # Log suppression
            print(f"🚫 SUPPRESSED Discord alert for {symbol}: {sureness_statement}")
            
            return False, f"SUPPRESSED: {sureness_statement}"
        
        # Check minimum adjusted confidence
        if adjusted_confidence < self.config.min_adjusted_confidence:
            self.stats['suppressed'] += 1
            msg = f"Adjusted confidence {adjusted_confidence:.0f} below minimum {self.config.min_adjusted_confidence:.0f}"
            print(f"🚫 SUPPRESSED: {msg}")
            return False, msg
        
        # Get metrics for embed
        metrics = self.quality_system.strategy_metrics.get(strategy_id)
        tier = metrics.confidence_tier if metrics else ConfidenceTier.EARLY_GUESS
        
        # Check tier-based suppression
        if tier == ConfidenceTier.EARLY_GUESS and self.config.suppress_early_guess:
            return False, "Early guess - suppressed by config"
        if tier == ConfidenceTier.EMERGING and self.config.suppress_emerging:
            return False, "Emerging - suppressed by config"
        
        # Build Discord payload
        embed = self._build_discord_embed(
            symbol=symbol,
            signal_type=signal_type,
            entry=entry,
            stop=stop,
            target=target,
            strategy_id=strategy_id,
            base_confidence=base_confidence,
            adjusted_confidence=adjusted_confidence,
            sureness_statement=sureness_statement,
            tier=tier,
            metrics=metrics,
            timeframe=timeframe,
            chart_url=chart_url
        )
        
        # Add role mention for high-tier alerts
        content = None
        if tier in self.config.role_mentions:
            content = self.config.role_mentions[tier]
        
        payload = {
            "embeds": [embed]
        }
        if content:
            payload["content"] = content
        
        # Send to Discord
        if not self.config.webhook_url:
            print("⚠️ No Discord webhook URL configured")
            return False, "No webhook URL"
        
        try:
            async with self.session.post(
                self.config.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 204:
                    self.stats['sent'] += 1
                    self.stats['by_tier'][tier] += 1
                    print(f"✅ Discord alert sent: {symbol} {signal_type} ({tier.value})")
                    return True, "Alert sent successfully"
                else:
                    error_text = await response.text()
                    print(f"❌ Discord API error: {response.status} - {error_text}")
                    return False, f"Discord API error: {response.status}"
        except Exception as e:
            print(f"❌ Error sending Discord alert: {e}")
            return False, str(e)
    
    async def send_stats_report(self):
        """Send stats report to Discord"""
        
        embed = {
            "title": "📊 Quality Alert Bot Stats",
            "color": 0x3498db,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": [
                {
                    "name": "📈 Alert Summary",
                    "value": f"Sent: {self.stats['sent']}\nSuppressed: {self.stats['suppressed']}\nQuality Rate: {self.stats['sent']/(self.stats['sent']+self.stats['suppressed'])*100:.1f}%",
                    "inline": True
                },
                {
                    "name": "🏆 By Tier",
                    "value": "\n".join([f"{tier.value}: {count}" for tier, count in self.stats['by_tier'].items() if count > 0]) or "No alerts yet",
                    "inline": True
                }
            ]
        }
        
        payload = {"embeds": [embed]}
        
        if self.config.webhook_url:
            async with self.session.post(
                self.config.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                return response.status == 204
        return False


# Synchronous wrapper for easier use
def send_quality_alert(symbol: str,
                       signal_type: str,
                       entry: float,
                       stop: float,
                       target: float,
                       strategy_id: str,
                       base_confidence: float,
                       timeframe: str = "1h",
                       chart_url: str = None,
                       webhook_url: str = None) -> Tuple[bool, str]:
    """
    Synchronous wrapper to send a quality-gated Discord alert
    
    Usage:
        sent, msg = send_quality_alert(
            symbol="BTCUSDT",
            signal_type="buy",
            entry=50000,
            stop=49000,
            target=52000,
            strategy_id="BTC_CME_GAP_V2",
            base_confidence=85
        )
    """
    
    config = DiscordAlertConfig(webhook_url=webhook_url)
    
    async def _send():
        async with DiscordQualityAlertBot(config) as bot:
            return await bot.send_alert(
                symbol=symbol,
                signal_type=signal_type,
                entry=entry,
                stop=stop,
                target=target,
                strategy_id=strategy_id,
                base_confidence=base_confidence,
                timeframe=timeframe,
                chart_url=chart_url
            )
    
    return asyncio.run(_send())


# Example usage
if __name__ == "__main__":
    
    print("🎯 Discord Quality Alert Bot - 'Are We Sure?' Edition")
    print("="*70)
    
    # Initialize bot with test configuration
    config = DiscordAlertConfig(
        webhook_url=os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/test'),
        min_adjusted_confidence=60
    )
    
    async def demo():
        async with DiscordQualityAlertBot(config) as bot:
            
            # Pre-populate some strategy metrics
            print("\n📊 Setting up strategy validation history...\n")
            
            # Institutional strategy
            for i in range(350):
                bot.quality_system.update_strategy_metrics(
                    "BTC_CME_GAP_V2", won=i<245, profit=100 if i<245 else -50
                )
            
            # Proven strategy
            for i in range(150):
                bot.quality_system.update_strategy_metrics(
                    "ETH_LONDON_BREAKOUT", won=i<90, profit=100 if i<90 else -50
                )
            
            # Validated strategy (borderline)
            for i in range(55):
                bot.quality_system.update_strategy_metrics(
                    "MEME_VOLUME_SPIKE", won=i<30, profit=100 if i<30 else -50
                )
            
            # New strategy (should be suppressed)
            for i in range(10):
                bot.quality_system.update_strategy_metrics(
                    "NEW_EXPERIMENTAL", won=i<6, profit=100 if i<6 else -50
                )
            
            # Broken strategy (consecutive losses)
            for i in range(100):
                bot.quality_system.update_strategy_metrics(
                    "BROKEN_STRAT", won=i<50, profit=100 if i<50 else -50
                )
            for i in range(5):
                bot.quality_system.update_strategy_metrics(
                    "BROKEN_STRAT", won=False, profit=-50
                )
            
            # Test alerts
            test_cases = [
                ("BTCUSDT", "buy", 50000, 49000, 52000, "BTC_CME_GAP_V2", 88, "Institutional"),
                ("ETHUSDT", "buy", 3000, 2950, 3150, "ETH_LONDON_BREAKOUT", 82, "Proven"),
                ("DOGEUSDT", "buy", 0.08, 0.077, 0.09, "MEME_VOLUME_SPIKE", 75, "Validated (borderline)"),
                ("SHIBUSDT", "buy", 0.00001, 0.0000095, 0.000012, "NEW_EXPERIMENTAL", 85, "NEW - Should be suppressed"),
                ("LINKUSDT", "sell", 15, 15.5, 14, "BROKEN_STRAT", 80, "Broken - Should be suppressed"),
            ]
            
            print("\n" + "="*70)
            print("🧪 TESTING DISCORD ALERTS:\n")
            
            for symbol, sig_type, entry, stop, target, strat_id, conf, desc in test_cases:
                print(f"\n{'='*70}")
                print(f"TEST: {desc}")
                print(f"{symbol} {sig_type.upper()} | Strategy: {strat_id} | Base Conf: {conf}")
                print("-"*70)
                
                sent, msg = await bot.send_alert(
                    symbol=symbol,
                    signal_type=sig_type,
                    entry=entry,
                    stop=stop,
                    target=target,
                    strategy_id=strat_id,
                    base_confidence=conf,
                    timeframe="1h"
                )
                
                if sent:
                    print(f"✅ SENT: {msg}")
                else:
                    print(f"🚫 SUPPRESSED: {msg}")
            
            # Print summary
            print("\n" + "="*70)
            print("📊 FINAL STATS:")
            print(f"   Alerts Sent: {bot.stats['sent']}")
            print(f"   Alerts Suppressed: {bot.stats['suppressed']}")
            print(f"   Quality Rate: {bot.stats['sent']/(bot.stats['sent']+bot.stats['suppressed'])*100:.1f}%")
            print("="*70)
    
    asyncio.run(demo())
