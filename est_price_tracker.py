#!/usr/bin/env python3
"""
PRICE ACTION TRACKER - EST Timezone
Tracks all price action with EST timestamps for 2-hour challenge
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import requests

class ESTPriceTracker:
    """Tracks price action in EST timezone"""
    
    def __init__(self):
        self.est_tz = timezone(timedelta(hours=-5))  # EST is UTC-5
        self.price_history: List[Dict] = []
        self.signals: List[Dict] = []
        self.trades: List[Dict] = []
        
    def get_est_time(self) -> datetime:
        """Get current time in EST"""
        return datetime.now(self.est_tz)
    
    def format_est_timestamp(self, dt: datetime = None) -> str:
        """Format timestamp in EST"""
        if dt is None:
            dt = self.get_est_time()
        return dt.strftime('%Y-%m-%d %H:%M:%S EST')
    
    def fetch_crypto_price(self, symbol: str) -> Optional[Dict]:
        """Fetch current crypto price from Binance"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                est_time = self.get_est_time()
                
                price_data = {
                    'symbol': symbol,
                    'price': float(data['lastPrice']),
                    'open': float(data['openPrice']),
                    'high': float(data['highPrice']),
                    'low': float(data['lowPrice']),
                    'volume': float(data['volume']),
                    'quote_volume': float(data['quoteVolume']),
                    'price_change_pct': float(data['priceChangePercent']),
                    'weighted_avg_price': float(data['weightedAvgPrice']),
                    'timestamp_utc': datetime.utcnow().isoformat(),
                    'timestamp_est': self.format_est_timestamp(est_time),
                    'hour_est': est_time.hour,
                    'minute_est': est_time.minute,
                    'day_of_week': est_time.strftime('%A')
                }
                
                self.price_history.append(price_data)
                return price_data
                
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
        
        return None
    
    def log_signal(self, strategy: str, symbol: str, direction: str, 
                   entry_price: float, stop_loss: float, take_profit: float,
                   confidence: float, rationale: str) -> Dict:
        """Log a trading signal with EST timestamp"""
        est_time = self.get_est_time()
        
        signal = {
            'signal_id': len(self.signals),
            'strategy': strategy,
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': confidence,
            'rationale': rationale,
            'timestamp_est': self.format_est_timestamp(est_time),
            'hour_est': est_time.hour,
            'minute_est': est_time.minute,
            'status': 'ACTIVE'
        }
        
        self.signals.append(signal)
        
        print(f"\n🎯 SIGNAL LOGGED [{signal['timestamp_est']}]")
        print(f"   Strategy: {strategy}")
        print(f"   Symbol: {symbol} | Direction: {direction}")
        print(f"   Entry: ${entry_price:,.2f} | Stop: ${stop_loss:,.2f} | Target: ${take_profit:,.2f}")
        print(f"   Confidence: {confidence}%")
        
        return signal
    
    def log_trade_exit(self, signal_id: int, exit_price: float, 
                       exit_reason: str, pnl_pct: float) -> Dict:
        """Log trade exit with EST timestamp"""
        est_time = self.get_est_time()
        
        # Find the signal
        signal = None
        for s in self.signals:
            if s['signal_id'] == signal_id:
                signal = s
                break
        
        if not signal:
            return None
        
        trade = {
            'trade_id': len(self.trades),
            'signal_id': signal_id,
            'strategy': signal['strategy'],
            'symbol': signal['symbol'],
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'entry_time_est': signal['timestamp_est'],
            'exit_time_est': self.format_est_timestamp(est_time),
            'closed_at': datetime.now(timezone.utc).isoformat(),
            'duration_minutes': self.calculate_duration(
                signal['timestamp_est'],
                self.format_est_timestamp(est_time)
            )
        }
        
        self.trades.append(trade)
        signal['status'] = 'CLOSED'
        
        emoji = "✅" if pnl_pct > 0 else "❌"
        print(f"\n{emoji} TRADE CLOSED [{trade['exit_time_est']}]")
        print(f"   Strategy: {trade['strategy']}")
        print(f"   Symbol: {trade['symbol']} | P&L: {pnl_pct:+.2f}%")
        print(f"   Exit Reason: {exit_reason}")
        print(f"   Duration: {trade['duration_minutes']:.1f} minutes")
        
        return trade
    
    def calculate_duration(self, entry_time_str: str, exit_time_str: str) -> float:
        """Calculate trade duration in minutes"""
        try:
            fmt = '%Y-%m-%d %H:%M:%S EST'
            entry = datetime.strptime(entry_time_str, fmt)
            exit = datetime.strptime(exit_time_str, fmt)
            return (exit - entry).total_seconds() / 60
        except:
            return 0
    
    def get_session_type(self, hour_est: int) -> str:
        """Determine trading session based on EST hour"""
        if 9 <= hour_est < 11:
            return "PRE_MARKET"  # 9:00-11:00 AM
        elif 11 <= hour_est < 16:
            return "LUNCH"  # 11:00 AM - 4:00 PM
        elif 16 <= hour_est < 21:
            return "AFTERNOON"  # 4:00-9:00 PM
        else:
            return "OVERNIGHT"  # 9:00 PM - 9:00 AM
    
    def generate_est_report(self) -> str:
        """Generate report with all EST timestamps"""
        report = []
        report.append("# 📊 PRICE ACTION REPORT (EST)")
        report.append(f"\n**Generated:** {self.format_est_timestamp()}")
        report.append(f"\n## 🎯 Signals Generated ({len(self.signals)})")
        
        if self.signals:
            report.append("\n| Time (EST) | Strategy | Symbol | Direction | Entry | Status |")
            report.append("|------------|----------|--------|-----------|-------|--------|")
            for s in self.signals:
                report.append(f"| {s['timestamp_est']} | {s['strategy']} | {s['symbol']} | {s['direction']} | ${s['entry_price']:,.2f} | {s['status']} |")
        
        report.append(f"\n## 📈 Completed Trades ({len(self.trades)})")
        
        if self.trades:
            report.append("\n| Entry Time | Exit Time | Strategy | Symbol | P&L | Duration |")
            report.append("|------------|-----------|----------|--------|-----|----------|")
            for t in self.trades:
                emoji = "🟢" if t['pnl_pct'] > 0 else "🔴"
                report.append(f"| {t['entry_time_est']} | {t['exit_time_est']} | {t['strategy']} | {t['symbol']} | {emoji} {t['pnl_pct']:+.2f}% | {t['duration_minutes']:.0f}m |")
            
            # Summary stats
            total_pnl = sum(t['pnl_pct'] for t in self.trades)
            wins = sum(1 for t in self.trades if t['pnl_pct'] > 0)
            win_rate = wins / len(self.trades) if self.trades else 0
            
            report.append(f"\n### Summary")
            report.append(f"- **Total Trades:** {len(self.trades)}")
            report.append(f"- **Win Rate:** {win_rate:.1%}")
            report.append(f"- **Total P&L:** {total_pnl:+.2f}%")
        
        return "\n".join(report)
    
    def save_est_data(self, filename: str = "price_action_est.json"):
        """Save all data with EST timestamps"""
        data = {
            'generated_at_est': self.format_est_timestamp(),
            'signals': self.signals,
            'trades': self.trades,
            'price_history_count': len(self.price_history)
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 EST data saved to {filename}")

# Test the tracker
def main():
    tracker = ESTPriceTracker()
    
    print("🕐 EST PRICE ACTION TRACKER")
    print("=" * 60)
    print(f"Current EST Time: {tracker.format_est_timestamp()}")
    print()
    
    # Test fetching prices
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    print("📊 Fetching current prices...")
    for symbol in symbols:
        price_data = tracker.fetch_crypto_price(symbol)
        if price_data:
            print(f"{symbol}: ${price_data['price']:,.2f} ({price_data['price_change_pct']:+.2f}%)")
            print(f"   Time: {price_data['timestamp_est']}")
            print(f"   Session: {tracker.get_session_type(price_data['hour_est'])}")
    
    # Test logging signals
    print("\n🎯 Testing signal logging...")
    tracker.log_signal(
        strategy="News_Scalping",
        symbol="BTCUSDT",
        direction="LONG",
        entry_price=65000,
        stop_loss=63700,
        take_profit=67600,
        confidence=75,
        rationale="Volume surge + momentum"
    )
    
    # Test logging trade exit
    tracker.log_trade_exit(
        signal_id=0,
        exit_price=67600,
        exit_reason="TAKE_PROFIT",
        pnl_pct=4.0
    )
    
    # Generate report
    print("\n" + "=" * 60)
    print(tracker.generate_est_report())
    
    # Save data
    tracker.save_est_data()

if __name__ == "__main__":
    main()
