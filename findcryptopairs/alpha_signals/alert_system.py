#!/usr/bin/env python3
"""
Alpha Signal Alert System
Real-time notifications for 80+ confidence signals
"""

import json
import time
from datetime import datetime, timezone
from typing import List, Dict
from alpha_engine import AlphaEngine, AlphaSignal

class AlertSystem:
    """
    Monitors markets and sends alerts for high-certainty signals
    Simulates what paid Discord groups do
    """
    
    def __init__(self):
        self.engine = AlphaEngine()
        self.alerted_signals = set()  # Prevent duplicate alerts
        self.audit_log = []
        
    def format_alert(self, signal: AlphaSignal) -> str:
        """Format signal as professional alert message"""
        
        emoji = "🟢" if signal.signal_type == 'buy' else "🔴"
        grade = signal.get_grade()
        
        alert = f"""
{'='*60}
🎯 ALPHA SIGNAL ALERT - {grade}
{'='*60}

{emoji} {signal.symbol} {signal.signal_type.upper()} SIGNAL

📊 Signal Grade: {grade}
💯 Confidence: {signal.confidence_score}/100
⏰ Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}

💰 TRADE DETAILS:
   Entry: ${signal.entry_price:,.8f}
   Stop:  ${signal.stop_loss:,.8f} ({((signal.stop_loss/signal.entry_price)-1)*100:.1f}%)
   Target: ${signal.take_profit:,.8f} ({((signal.take_profit/signal.entry_price)-1)*100:.1f}%)
   R:R Ratio: 1:{signal.risk_reward:.1f}
   Hold Time: {signal.time_to_hold}

🔍 FACTOR BREAKDOWN:
"""
        
        # Add factor details
        factors = signal.factors
        if 'htf_trend' in factors:
            alert += f"   📈 HTF Trend: {factors['htf_trend']['score']}/15\n"
        if 'smart_money' in factors:
            alert += f"   🎯 Smart Money: {factors['smart_money']['score']}/40\n"
        if 'onchain' in factors:
            alert += f"   🐋 On-Chain: {factors['onchain']['score']}/20\n"
        if 'volume_profile' in factors:
            alert += f"   📊 Volume: {factors['volume_profile']['score']}/15\n"
        if 'kill_zone' in factors:
            alert += f"   ⏰ Kill Zone: {factors['kill_zone']['score']}/10\n"
        
        alert += f"""
📝 SETUP NOTES:
"""
        
        # Add specific setup notes
        reasons = []
        if 'smart_money' in factors and factors['smart_money'].get('reasons'):
            reasons.extend(factors['smart_money']['reasons'][:2])
        if 'onchain' in factors and factors['onchain'].get('indicators'):
            reasons.extend(factors['onchain']['indicators'][:2])
            
        for reason in reasons:
            alert += f"   • {reason}\n"
        
        alert += f"""
⚠️  RISK MANAGEMENT:
   • Risk max 2% account on S+ signals
   • Risk max 1.5% on S/A+ signals
   • Set alerts at entry, -3%, +5%, +10%
   
🔗 Full analysis: audit_log/{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M')}.json

{'='*60}
        """
        
        return alert
    
    def send_alert(self, signal: AlphaSignal, channels: List[str] = None):
        """
        Send alert through multiple channels
        In production: Discord webhook, Telegram, email, SMS
        """
        alert_text = self.format_alert(signal)
        
        # Print to console (would be Discord/Telegram in production)
        print(alert_text)
        
        # Log to file
        self.log_alert(signal, alert_text)
        
        # Track that we alerted this signal
        signal_id = f"{signal.symbol}_{signal.timestamp.timestamp()}"
        self.alerted_signals.add(signal_id)
        
        # Save to audit
        self.audit_alert(signal)
        
    def log_alert(self, signal: AlphaSignal, alert_text: str):
        """Log alert to file"""
        timestamp = signal.timestamp.strftime('%Y%m%d')
        filename = f"alerts/alpha_alerts_{timestamp}.log"
        
        try:
            with open(filename, 'a') as f:
                f.write(alert_text)
                f.write("\n\n")
        except Exception as e:
            print(f"Error logging alert: {e}")
    
    def audit_alert(self, signal: AlphaSignal):
        """Save complete audit trail for signal"""
        audit_entry = {
            'timestamp': signal.timestamp.isoformat(),
            'symbol': signal.symbol,
            'signal_type': signal.signal_type,
            'confidence': signal.confidence_score,
            'grade': signal.get_grade(),
            'entry': signal.entry_price,
            'stop': signal.stop_loss,
            'target': signal.take_profit,
            'risk_reward': signal.risk_reward,
            'factors': signal.factors,
            'alerted': True
        }
        
        self.audit_log.append(audit_entry)
        
        # Save to file
        filename = f"audit/{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w') as f:
                json.dump(audit_entry, f, indent=2)
        except Exception as e:
            print(f"Error saving audit: {e}")
    
    def should_alert(self, signal: AlphaSignal) -> bool:
        """Check if we should alert this signal"""
        # Only alert 80+ confidence
        if signal.confidence_score < 80:
            return False
        
        # Check if already alerted
        signal_id = f"{signal.symbol}_{signal.timestamp.timestamp()}"
        if signal_id in self.alerted_signals:
            return False
        
        return True
    
    def monitor_continuous(self, pairs_data: Dict, interval_seconds: int = 300):
        """
        Continuously monitor all pairs for signals
        Run this as background process
        """
        print(f"🎯 Alpha Alert System Started")
        print(f"   Monitoring {len(pairs_data)} pairs")
        print(f"   Check interval: {interval_seconds}s")
        print(f"   Min confidence: 80\n")
        
        while True:
            try:
                print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Scanning...")
                
                # Scan for signals
                signals = self.engine.scan_all_pairs(pairs_data)
                
                # Alert high certainty signals
                for signal in signals:
                    if self.should_alert(signal):
                        print(f"\n🚨 HIGH CERTAINTY SIGNAL DETECTED!")
                        self.send_alert(signal)
                
                if not signals:
                    print("   No high certainty signals found.")
                
                print(f"   Waiting {interval_seconds}s...\n")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\n⚠️  Monitoring stopped by user")
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(interval_seconds)
    
    def generate_daily_report(self) -> str:
        """Generate daily performance report"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Count signals
        today_signals = [s for s in self.audit_log 
                        if s['timestamp'].startswith(today)]
        
        buy_signals = [s for s in today_signals if s['signal_type'] == 'buy']
        sell_signals = [s for s in today_signals if s['signal_type'] == 'sell']
        
        s_plus = [s for s in today_signals if s['confidence'] >= 96]
        s_grade = [s for s in today_signals if 90 <= s['confidence'] < 96]
        a_plus = [s for s in today_signals if 85 <= s['confidence'] < 90]
        
        report = f"""
{'='*60}
📊 DAILY ALPHA SIGNAL REPORT - {today}
{'='*60}

📈 SUMMARY:
   Total Signals: {len(today_signals)}
   Buy Signals: {len(buy_signals)}
   Sell Signals: {len(sell_signals)}
   
🎯 BY GRADE:
   S+ (96-100): {len(s_plus)}
   S (90-95): {len(s_grade)}
   A+ (85-89): {len(a_plus)}
   A (80-84): {len(today_signals) - len(s_plus) - len(s_grade) - len(a_plus)}

🔔 ALERTS SENT: {len([s for s in today_signals if s.get('alerted')])}

📁 AUDIT TRAIL: audit/ directory
{'='*60}
        """
        
        return report


# Example/demo
if __name__ == "__main__":
    import numpy as np
    
    alerts = AlertSystem()
    
    # Create sample signal
    sample_signal = AlphaSignal(
        symbol="PENGU",
        current_price=0.00665,
        signal_type="buy",
        confidence_score=94,
        entry_price=0.00665,
        stop_loss=0.00635,
        take_profit=0.00785,
        risk_reward=4.0,
        time_to_hold="12-24 hours",
        factors={
            'htf_trend': {'score': 14, 'trend': 'bullish'},
            'smart_money': {'score': 35, 'reasons': ['Liquidity sweep', 'Order Block']},
            'onchain': {'score': 18, 'indicators': ['Whale accumulation']},
            'volume_profile': {'score': 13},
            'kill_zone': {'score': 10}
        },
        timestamp=datetime.now(timezone.utc)
    )
    
    # Send alert
    if alerts.should_alert(sample_signal):
        alerts.send_alert(sample_signal)
    
    # Show daily report
    print(alerts.generate_daily_report())
