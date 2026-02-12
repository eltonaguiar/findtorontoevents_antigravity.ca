#!/usr/bin/env python3
"""
Stop Loss Analyzer - Investigate Stop-Loss Execution Failures
DEEPSEEK MOTHERLOAD Implementation
Purpose: Analyze why 3% stop becomes -12% avg loss and fix execution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class StopLossAnalyzer:
    def __init__(self):
        self.gap_threshold = 0.05  # 5% gap risk threshold
        self.after_hours_risk = True
        
    def analyze_stop_loss_failures(self, trades_data):
        """Analyze stop-loss execution failures"""
        
        failed_stops = []
        successful_stops = []
        
        for trade in trades_data:
            if 'stop_loss_pct' not in trade or 'actual_loss_pct' not in trade:
                continue
                
            stop_loss_pct = trade['stop_loss_pct']
            actual_loss_pct = trade['actual_loss_pct']
            
            # Check if stop loss failed
            if abs(actual_loss_pct) > abs(stop_loss_pct) * 1.1:  # 10% tolerance
                failure_data = {
                    'ticker': trade.get('ticker', 'Unknown'),
                    'entry_date': trade.get('entry_date', ''),
                    'stop_loss_pct': stop_loss_pct,
                    'actual_loss_pct': actual_loss_pct,
                    'failure_magnitude': abs(actual_loss_pct) - abs(stop_loss_pct),
                    'gap_risk': self.detect_gap_risk(trade),
                    'after_hours': self.check_after_hours(trade),
                    'volatility': trade.get('volatility', 0)
                }
                failed_stops.append(failure_data)
            else:
                successful_stops.append(trade)
        
        return {
            'failed_stops': failed_stops,
            'successful_stops': successful_stops,
            'failure_rate': len(failed_stops) / (len(failed_stops) + len(successful_stops)) if (len(failed_stops) + len(successful_stops)) > 0 else 0
        }
    
    def detect_gap_risk(self, trade):
        """Detect gap risk in trade data"""
        
        # Check for price gaps
        if 'open_price' in trade and 'prev_close' in trade:
            gap_pct = abs(trade['open_price'] - trade['prev_close']) / trade['prev_close']
            return gap_pct > self.gap_threshold
        
        return False
    
    def check_after_hours(self, trade):
        """Check if trade involves after-hours risk"""
        
        if 'entry_time' in trade:
            entry_time = pd.to_datetime(trade['entry_time'])
            # Check if trade entered near market close
            if entry_time.hour >= 15:  # After 3 PM
                return True
        
        return False
    
    def implement_gap_protection(self, trades_data):
        """Implement gap risk protection measures"""
        
        protected_trades = []
        
        for trade in trades_data:
            protected_trade = trade.copy()
            
            # Add gap protection measures
            if self.detect_gap_risk(trade):
                # Reduce position size for gap-prone trades
                protected_trade['position_size_pct'] = trade.get('position_size_pct', 10) * 0.5
                
                # Use wider stops for gap risk
                protected_trade['stop_loss_pct'] = trade.get('stop_loss_pct', 3) * 1.5
                
                # Add gap stop order type
                protected_trade['order_type'] = 'gap_stop'
            
            # After-hours protection
            if self.check_after_hours(trade):
                protected_trade['stop_type'] = 'market_on_open'
                protected_trade['max_slippage_pct'] = 2.0
            
            protected_trades.append(protected_trade)
        
        return protected_trades
    
    def generate_failure_report(self, analysis_results):
        """Generate detailed failure analysis report"""
        
        report = {
            'summary': {
                'total_trades': len(analysis_results['failed_stops']) + len(analysis_results['successful_stops']),
                'failed_stops': len(analysis_results['failed_stops']),
                'failure_rate': analysis_results['failure_rate'] * 100,
                'avg_failure_magnitude': np.mean([f['failure_magnitude'] for f in analysis_results['failed_stops']]) if analysis_results['failed_stops'] else 0
            },
            'root_causes': {
                'gap_risk_failures': len([f for f in analysis_results['failed_stops'] if f['gap_risk']]),
                'after_hours_failures': len([f for f in analysis_results['failed_stops'] if f['after_hours']]),
                'high_volatility_failures': len([f for f in analysis_results['failed_stops'] if f['volatility'] > 0.3])
            },
            'recommendations': [
                "Implement gap risk protection (reduce position size for gap-prone trades)",
                "Use market-on-open stops for after-hours entries",
                "Increase stop-loss distance for high-volatility assets",
                "Implement volatility-adjusted position sizing",
                "Add circuit breaker protection for extreme moves"
            ]
        }
        
        return report

def load_trade_data(file_path):
    """Load trade data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Trade data file {file_path} not found")
        return []

def main():
    """Main execution function"""
    
    # Load trade data
    trades_data = load_trade_data('data/trades_with_stops.json')
    
    if not trades_data:
        # Create sample data
        trades_data = [
            {
                'ticker': 'AAPL', 'entry_date': '2024-01-15', 'stop_loss_pct': 3.0, 'actual_loss_pct': -12.5,
                'open_price': 150, 'prev_close': 145, 'entry_time': '2024-01-15 15:45:00', 'volatility': 0.25
            },
            {
                'ticker': 'TSLA', 'entry_date': '2024-01-16', 'stop_loss_pct': 3.0, 'actual_loss_pct': -2.5,
                'open_price': 200, 'prev_close': 198, 'entry_time': '2024-01-16 10:30:00', 'volatility': 0.35
            },
            # Add more sample trades...
        ]
    
    # Initialize analyzer
    analyzer = StopLossAnalyzer()
    
    # Analyze stop-loss failures
    print("=== STOP-LOSS FAILURE ANALYSIS ===")
    analysis = analyzer.analyze_stop_loss_failures(trades_data)
    
    print(f"Total Trades: {len(analysis['failed_stops']) + len(analysis['successful_stops'])}")
    print(f"Failed Stops: {len(analysis['failed_stops'])}")
    print(f"Failure Rate: {analysis['failure_rate']:.1f}%")
    
    # Generate failure report
    report = analyzer.generate_failure_report(analysis)
    
    print("\n=== FAILURE REPORT ===")
    print(f"Average Failure Magnitude: {report['summary']['avg_failure_magnitude']:.2f}%")
    print(f"Gap Risk Failures: {report['root_causes']['gap_risk_failures']}")
    print(f"After-Hours Failures: {report['root_causes']['after_hours_failures']}")
    print(f"High Volatility Failures: {report['root_causes']['high_volatility_failures']}")
    
    print("\n=== RECOMMENDATIONS ===")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    # Implement gap protection
    print("\n=== GAP PROTECTION IMPLEMENTATION ===")
    protected_trades = analyzer.implement_gap_protection(trades_data)
    print(f"Protected trades generated: {len(protected_trades)}")

if __name__ == "__main__":
    main()