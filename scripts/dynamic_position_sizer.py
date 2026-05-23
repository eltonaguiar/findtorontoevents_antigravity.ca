#!/usr/bin/env python3
"""
Dynamic Position Sizer - Volatility-Based Risk Management
DEEPSEEK MOTHERLOAD Implementation
Purpose: Implement dynamic position sizing based on volatility and correlation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class DynamicPositionSizer:
    def __init__(self, target_volatility=0.10):
        self.target_volatility = target_volatility  # 10% annual volatility target
        self.min_position_size = 0.01  # 1% minimum
        self.max_position_size = 0.15  # 15% maximum
        
    def calculate_volatility(self, price_data, period=20):
        """Calculate volatility from price data"""
        
        if len(price_data) < period:
            return 0
        
        returns = []
        for i in range(1, len(price_data)):
            if price_data[i-1] > 0:
                ret = (price_data[i] - price_data[i-1]) / price_data[i-1]
                returns.append(ret)
        
        if len(returns) < 2:
            return 0
        
        # Annualize volatility
        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        
        return annual_vol
    
    def volatility_adjusted_size(self, asset_volatility, portfolio_volatility=None):
        """Calculate position size based on volatility"""
        
        if asset_volatility <= 0:
            return self.min_position_size
        
        # Inverse volatility weighting
        # Higher volatility = smaller position size
        size = self.target_volatility / asset_volatility
        
        # Apply bounds
        size = max(self.min_position_size, min(self.max_position_size, size))
        
        return size
    
    def kelly_position_size(self, win_rate, win_loss_ratio):
        """Calculate Kelly criterion position size"""
        
        if win_loss_ratio <= 0:
            return self.min_position_size
        
        # Full Kelly formula: f* = (bp - q) / b
        # Where b = win/loss ratio, p = win rate, q = loss rate
        p = win_rate / 100  # Convert from percentage
        q = 1 - p
        b = win_loss_ratio
        
        kelly_fraction = (b * p - q) / b
        
        # Use quarter-Kelly for safety
        quarter_kelly = kelly_fraction * 0.25
        
        # Apply bounds
        size = max(self.min_position_size, min(self.max_position_size, quarter_kelly))
        
        return size
    
    def correlation_adjusted_size(self, position_sizes, correlation_matrix):
        """Adjust position sizes based on correlation"""
        
        if not correlation_matrix or len(position_sizes) != len(correlation_matrix):
            return position_sizes
        
        # Calculate portfolio volatility contribution
        portfolio_variance = 0
        for i, size_i in enumerate(position_sizes):
            for j, size_j in enumerate(position_sizes):
                if i <= j:
                    corr = correlation_matrix[i][j] if i != j else 1.0
                    portfolio_variance += size_i * size_j * corr
        
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Adjust sizes if portfolio volatility exceeds target
        if portfolio_volatility > self.target_volatility:
            adjustment_factor = self.target_volatility / portfolio_volatility
            adjusted_sizes = [size * adjustment_factor for size in position_sizes]
            
            # Re-normalize to maintain relative sizes
            total_original = sum(position_sizes)
            total_adjusted = sum(adjusted_sizes)
            
            if total_adjusted > 0:
                normalized_sizes = [size * (total_original / total_adjusted) for size in adjusted_sizes]
                return normalized_sizes
        
        return position_sizes
    
    def generate_position_sizing_rules(self, trade_data):
        """Generate position sizing rules based on historical data"""
        
        rules = {}
        
        for asset, data in trade_data.items():
            # Calculate historical metrics
            win_rate = data.get('win_rate', 50)
            avg_win = data.get('avg_win_pct', 5) / 100
            avg_loss = data.get('avg_loss_pct', 3) / 100
            volatility = data.get('volatility', 0.20)
            
            # Win/loss ratio
            if avg_loss > 0:
                win_loss_ratio = avg_win / abs(avg_loss)
            else:
                win_loss_ratio = 1.0
            
            # Calculate different sizing methods
            vol_size = self.volatility_adjusted_size(volatility)
            kelly_size = self.kelly_position_size(win_rate, win_loss_ratio)
            
            # Combine methods (weighted average)
            final_size = (vol_size * 0.6 + kelly_size * 0.4)
            
            rules[asset] = {
                'volatility_based_size': vol_size,
                'kelly_based_size': kelly_size,
                'final_position_size': final_size,
                'volatility': volatility,
                'win_rate': win_rate,
                'win_loss_ratio': win_loss_ratio
            }
        
        return rules
    
    def create_sizing_table(self, rules):
        """Create position sizing table for implementation"""
        
        table = []
        
        for asset, rule in rules.items():
            table.append({
                'asset': asset,
                'volatility': f"{rule['volatility']:.1%}",
                'win_rate': f"{rule['win_rate']:.1f}%",
                'win_loss_ratio': f"{rule['win_loss_ratio']:.2f}",
                'vol_based_size': f"{rule['volatility_based_size']:.1%}",
                'kelly_size': f"{rule['kelly_based_size']:.1%}",
                'recommended_size': f"{rule['final_position_size']:.1%}"
            })
        
        return table

def load_trade_data(file_path):
    """Load trade data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Trade data file {file_path} not found")
        return {}

def main():
    """Main execution function"""
    
    # Load trade data
    trade_data = load_trade_data('data/trade_performance.json')
    
    if not trade_data:
        # Create sample data
        trade_data = {
            'AAPL': {'win_rate': 65.3, 'avg_win_pct': 4.3, 'avg_loss_pct': 2.1, 'volatility': 0.18},
            'TSLA': {'win_rate': 55.2, 'avg_win_pct': 8.5, 'avg_loss_pct': 4.2, 'volatility': 0.35},
            'SPY': {'win_rate': 58.7, 'avg_win_pct': 3.2, 'avg_loss_pct': 2.8, 'volatility': 0.15},
            'BTC': {'win_rate': 62.1, 'avg_win_pct': 12.5, 'avg_loss_pct': 6.8, 'volatility': 0.65}
        }
    
    # Initialize position sizer
    sizer = DynamicPositionSizer()
    
    # Generate position sizing rules
    print("=== DYNAMIC POSITION SIZING ===")
    rules = sizer.generate_position_sizing_rules(trade_data)
    
    # Create sizing table
    table = sizer.create_sizing_table(rules)
    
    print("\nPosition Sizing Recommendations:")
    print("-" * 80)
    print(f"{'Asset':<10} {'Vol':<8} {'Win Rate':<10} {'W/L Ratio':<10} {'Vol Size':<10} {'Kelly Size':<10} {'Final Size':<10}")
    print("-" * 80)
    
    for row in table:
        print(f"{row['asset']:<10} {row['volatility']:<8} {row['win_rate']:<10} {row['win_loss_ratio']:<10} {row['vol_based_size']:<10} {row['kelly_size']:<10} {row['recommended_size']:<10}")
    
    # Test correlation adjustment
    print("\n=== CORRELATION ADJUSTMENT TEST ===")
    
    # Sample correlation matrix
    correlation_matrix = [
        [1.0, 0.6, 0.8, 0.2],  # AAPL correlations
        [0.6, 1.0, 0.7, 0.3],  # TSLA correlations
        [0.8, 0.7, 1.0, 0.1],  # SPY correlations
        [0.2, 0.3, 0.1, 1.0]   # BTC correlations
    ]
    
    original_sizes = [rules[asset]['final_position_size'] for asset in rules.keys()]
    adjusted_sizes = sizer.correlation_adjusted_size(original_sizes, correlation_matrix)
    
    print("Original sizes:", [f"{s:.1%}" for s in original_sizes])
    print("Adjusted sizes:", [f"{s:.1%}" for s in adjusted_sizes])
    
    # Generate implementation code
    print("\n=== IMPLEMENTATION CODE ===")
    
    php_code = """
// Dynamic Position Sizing Implementation
function calculate_position_size($ticker, $volatility, $win_rate, $avg_win_pct, $avg_loss_pct) {
    $target_volatility = 0.10; // 10% annual target
    $min_size = 0.01; // 1% minimum
    $max_size = 0.15; // 15% maximum
    
    // Volatility-based sizing
    $vol_size = $target_volatility / max(0.01, $volatility);
    $vol_size = max($min_size, min($max_size, $vol_size));
    
    // Kelly criterion (quarter-Kelly for safety)
    $p = $win_rate / 100;
    $q = 1 - $p;
    $b = ($avg_loss_pct > 0) ? ($avg_win_pct / $avg_loss_pct) : 1.0;
    $kelly_fraction = ($b * $p - $q) / $b;
    $kelly_size = $kelly_fraction * 0.25;
    $kelly_size = max($min_size, min($max_size, $kelly_size));
    
    // Combined approach
    $final_size = ($vol_size * 0.6 + $kelly_size * 0.4);
    
    return round($final_size * 100, 1); // Return as percentage
}
"""
    
    print(php_code)

if __name__ == "__main__":
    main()