"""
================================================================================
REGIME DETECTION SYSTEM - DEMONSTRATION SCRIPT
================================================================================

This script demonstrates the complete usage of the regime detection system
with real market data.

Usage:
    python regime_demo.py

Output:
    - Console output with regime analysis
    - regime_visualization.png with charts
    - regime_history.json with full history
================================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import sys

# Import the regime detector
from regime_detector import (
    RegimeDetector, 
    RegimeThresholds, 
    AssetClass, 
    AssetClassConfig,
    TradeDirection, 
    MarketRegime, 
    get_default_thresholds_for_risk_profile,
    create_regime_detector_from_data
)


def load_market_data():
    """Load VIX and DXY market data."""
    print("Loading market data...")
    
    vix_df = pd.read_csv('/mnt/okcomputer/output/vix_data.csv')
    dxy_df = pd.read_csv('/mnt/okcomputer/output/dxy_data.csv')
    
    vix_df['Date'] = pd.to_datetime(vix_df['Date'])
    dxy_df['Date'] = pd.to_datetime(dxy_df['Date'])
    
    vix_df.set_index('Date', inplace=True)
    dxy_df.set_index('Date', inplace=True)
    
    vix = vix_df['Close']
    dxy = dxy_df['Close']
    
    # Align data
    common_dates = vix.index.intersection(dxy.index)
    vix_aligned = vix.loc[common_dates]
    dxy_aligned = dxy.loc[common_dates]
    
    print(f"  Loaded {len(common_dates)} observations")
    print(f"  Date range: {common_dates.min()} to {common_dates.max()}")
    
    return vix_aligned, dxy_aligned, common_dates


def create_and_train_detector(vix, dxy, dates):
    """Create and train the regime detector."""
    print("\nInitializing regime detector...")
    
    detector = RegimeDetector(
        thresholds=get_default_thresholds_for_risk_profile('moderate'),
        verbose=False
    )
    
    # Feed historical data
    for timestamp in dates:
        detector.update_market_data(
            timestamp=timestamp,
            vix=vix.loc[timestamp],
            dxy=dxy.loc[timestamp]
        )
    
    print(f"  Trained on {len(detector.regime_history)} observations")
    print(f"  Current regime: {detector.current_state.regime.name}")
    print(f"  Current VIX: {detector.current_state.vix_level:.2f}")
    print(f"  Current DXY: {detector.current_state.dxy_level:.2f}")
    
    return detector


def demonstrate_trade_filtering(detector):
    """Demonstrate trade filtering capabilities."""
    print("\n" + "=" * 80)
    print("TRADE FILTER DEMONSTRATION")
    print("=" * 80)
    
    print(f"\nCurrent Market State:")
    print(f"  Regime: {detector.current_state.regime.name}")
    print(f"  VIX: {detector.current_state.vix_level:.2f}")
    print(f"  DXY: {detector.current_state.dxy_level:.2f}")
    print(f"  Days in regime: {detector.current_state.regime_days}")
    
    test_scenarios = [
        ('ES (E-mini S&P)', AssetClass.EQUITY_INDEX, TradeDirection.LONG),
        ('ES (E-mini S&P)', AssetClass.EQUITY_INDEX, TradeDirection.SHORT),
        ('NQ (E-mini Nasdaq)', AssetClass.EQUITY_INDEX, TradeDirection.LONG),
        ('CL (Crude Oil)', AssetClass.COMMODITY, TradeDirection.LONG),
        ('CL (Crude Oil)', AssetClass.COMMODITY, TradeDirection.SHORT),
        ('GC (Gold)', AssetClass.COMMODITY, TradeDirection.LONG),
        ('EUR/USD', AssetClass.CURRENCY, TradeDirection.LONG),
        ('EUR/USD', AssetClass.CURRENCY, TradeDirection.SHORT),
        ('TLT (Bonds)', AssetClass.BOND, TradeDirection.LONG),
        ('VIX Futures', AssetClass.VOLATILITY, TradeDirection.LONG),
        ('VIX Futures', AssetClass.VOLATILITY, TradeDirection.SHORT),
    ]
    
    print("\n" + "-" * 100)
    print(f"{'Asset':<20} {'Direction':<8} {'Decision':<10} {'Risk Adj':<10} {'Reason'}")
    print("-" * 100)
    
    for symbol, asset_class, direction in test_scenarios:
        decision = detector.allow_trade(
            asset_class=asset_class,
            direction=direction,
            symbol=symbol
        )
        
        status = "✅ ALLOW" if decision.allow_trade else "❌ BLOCK"
        risk = f"{decision.risk_adjustment:.1%}"
        
        print(f"{symbol:<20} {direction.name:<8} {status:<10} {risk:<10} {decision.reason}")
        
        if decision.warning_flags:
            print(f"     ⚠️  Warnings: {', '.join(decision.warning_flags)}")
    
    print("-" * 100)


def demonstrate_historical_filtering(detector, vix, dxy, dates):
    """Demonstrate filtering across different historical regimes."""
    print("\n" + "=" * 80)
    print("HISTORICAL REGIME FILTERING EXAMPLES")
    print("=" * 80)
    
    # Extract regime history
    regime_data = []
    for state in detector.regime_history:
        regime_data.append({
            'timestamp': state.timestamp,
            'regime': state.regime.name,
            'vix': state.vix_level,
            'dxy': state.dxy_level
        })
    
    regime_df = pd.DataFrame(regime_data)
    regime_df.set_index('timestamp', inplace=True)
    
    # Find examples of each regime
    examples = {}
    for regime in ['BULL', 'BEAR', 'CHOP', 'CRISIS']:
        mask = regime_df['regime'] == regime
        if mask.any():
            examples[regime] = regime_df[mask].iloc[len(regime_df[mask])//2]
    
    test_cases = [
        ('BULL', 'ES Long', AssetClass.EQUITY_INDEX, TradeDirection.LONG),
        ('BULL', 'ES Short', AssetClass.EQUITY_INDEX, TradeDirection.SHORT),
        ('BULL', 'CL Long', AssetClass.COMMODITY, TradeDirection.LONG),
        ('BEAR', 'ES Long', AssetClass.EQUITY_INDEX, TradeDirection.LONG),
        ('BEAR', 'ES Short', AssetClass.EQUITY_INDEX, TradeDirection.SHORT),
        ('BEAR', 'CL Long', AssetClass.COMMODITY, TradeDirection.LONG),
        ('CHOP', 'ES Long', AssetClass.EQUITY_INDEX, TradeDirection.LONG),
        ('CHOP', 'CL Long', AssetClass.COMMODITY, TradeDirection.LONG),
        ('CRISIS', 'ES Long', AssetClass.EQUITY_INDEX, TradeDirection.LONG),
        ('CRISIS', 'VIX Long', AssetClass.VOLATILITY, TradeDirection.LONG),
    ]
    
    print("\nRegime-Based Filter Matrix:")
    print("-" * 100)
    print(f"{'Test Point':<15} {'Scenario':<15} {'VIX':<8} {'Regime':<10} {'Decision':<10} {'Reason'}")
    print("-" * 100)
    
    for regime_name, scenario, asset, direction in test_cases:
        if regime_name in examples:
            example = examples[regime_name]
            
            temp_detector = RegimeDetector(verbose=False)
            temp_detector.update_market_data(
                timestamp=example.name,
                vix=example['vix'],
                dxy=example['dxy']
            )
            
            decision = temp_detector.allow_trade(
                asset_class=asset,
                direction=direction
            )
            
            status = "✅ ALLOW" if decision.allow_trade else "❌ BLOCK"
            print(f"{regime_name:<15} {scenario:<15} {example['vix']:<8.1f} {regime_name:<10} {status:<10} {decision.reason}")
    
    print("-" * 100)


def print_regime_summary(detector):
    """Print comprehensive regime summary."""
    print("\n" + "=" * 80)
    print("REGIME SUMMARY STATISTICS")
    print("=" * 80)
    
    summary = detector.get_regime_summary(lookback_days=500)
    
    print(f"\nLookback Period: {summary['lookback_days']} days")
    print(f"Total Observations: {summary['total_observations']}")
    
    print("\nRegime Distribution:")
    for regime, count in summary['regime_distribution'].items():
        pct = count / summary['total_observations'] * 100
        print(f"  {regime}: {count} observations ({pct:.1f}%)")
    
    print("\nVIX Statistics:")
    vix_stats = summary['vix_statistics']
    print(f"  Mean: {vix_stats['mean']:.2f}")
    print(f"  Std: {vix_stats['std']:.2f}")
    print(f"  Min: {vix_stats['min']:.2f}")
    print(f"  Max: {vix_stats['max']:.2f}")
    
    print("\nDXY Statistics:")
    dxy_stats = summary['dxy_statistics']
    print(f"  Mean: {dxy_stats['mean']:.2f}")
    print(f"  Std: {dxy_stats['std']:.2f}")
    print(f"  Min: {dxy_stats['min']:.2f}")
    print(f"  Max: {dxy_stats['max']:.2f}")
    
    print("\nFilter Statistics:")
    filter_stats = summary['filter_statistics']
    print(f"  Total Checks: {filter_stats['total_checks']}")
    print(f"  Trades Allowed: {filter_stats['trades_allowed']}")
    print(f"  Trades Blocked: {filter_stats['trades_blocked']}")
    if filter_stats['total_checks'] > 0:
        allow_rate = filter_stats['trades_allowed'] / filter_stats['total_checks'] * 100
        print(f"  Allow Rate: {allow_rate:.1f}%")
    print(f"  Regime Transitions: {filter_stats['regime_transitions']}")


def create_visualization(detector, output_path):
    """Create regime visualization."""
    print("\nCreating visualization...")
    
    regime_data = []
    for state in detector.regime_history:
        regime_data.append({
            'timestamp': state.timestamp,
            'regime': state.regime.name,
            'vix': state.vix_level,
            'dxy': state.dxy_level,
            'regime_days': state.regime_days
        })
    
    regime_df = pd.DataFrame(regime_data)
    regime_df.set_index('timestamp', inplace=True)
    
    regime_colors = {
        'BULL': 'green',
        'BEAR': 'red',
        'CHOP': 'orange',
        'CRISIS': 'purple',
        'TRANSITION': 'blue',
        'UNKNOWN': 'gray'
    }
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Plot 1: VIX with regime coloring
    ax1 = axes[0]
    for regime in regime_df['regime'].unique():
        mask = regime_df['regime'] == regime
        ax1.scatter(regime_df.index[mask], regime_df['vix'][mask], 
                    c=regime_colors.get(regime, 'gray'), label=regime, s=10, alpha=0.7)
    
    ax1.axhline(y=20, color='green', linestyle='--', alpha=0.5, label='BULL/CHOP (20)')
    ax1.axhline(y=25, color='orange', linestyle='--', alpha=0.5, label='CHOP/BEAR (25)')
    ax1.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='BEAR/CRISIS (30)')
    
    ax1.set_ylabel('VIX Level')
    ax1.set_title('VIX-Based Regime Classification', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: DXY
    ax2 = axes[1]
    ax2.plot(regime_df.index, regime_df['dxy'], color='blue', linewidth=1)
    ax2.axhline(y=105, color='red', linestyle='--', alpha=0.5, label='Strong USD (105)')
    ax2.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='Weak USD (100)')
    ax2.set_ylabel('DXY Level')
    ax2.set_title('DXY (Dollar Strength Index)', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Regime distribution over time
    ax3 = axes[2]
    
    window_size = 30
    regime_counts = pd.DataFrame(index=regime_df.index)
    for regime in ['BULL', 'CHOP', 'BEAR', 'CRISIS']:
        regime_counts[regime] = (regime_df['regime'] == regime).astype(int).rolling(window_size, min_periods=1).sum()
    
    regime_pct = regime_counts.div(regime_counts.sum(axis=1), axis=0) * 100
    
    ax3.stackplot(regime_pct.index, 
                  regime_pct['BULL'], 
                  regime_pct['CHOP'], 
                  regime_pct['BEAR'], 
                  regime_pct['CRISIS'],
                  labels=['BULL', 'CHOP', 'BEAR', 'CRISIS'],
                  colors=['green', 'orange', 'red', 'purple'],
                  alpha=0.7)
    
    ax3.set_ylabel('Regime % (30-day rolling)')
    ax3.set_xlabel('Date')
    ax3.set_title('Regime Distribution Over Time', fontsize=14, fontweight='bold')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  Saved to {output_path}")


def export_regime_history(detector, output_path):
    """Export regime history to JSON."""
    print("\nExporting regime history...")
    detector.export_regime_history(output_path)
    print(f"  Saved to {output_path}")


def main():
    """Main demonstration function."""
    print("=" * 80)
    print("REGIME DETECTION SYSTEM - DEMONSTRATION")
    print("=" * 80)
    
    # Load data
    vix, dxy, dates = load_market_data()
    
    # Create and train detector
    detector = create_and_train_detector(vix, dxy, dates)
    
    # Demonstrate trade filtering
    demonstrate_trade_filtering(detector)
    
    # Demonstrate historical filtering
    demonstrate_historical_filtering(detector, vix, dxy, dates)
    
    # Print summary
    print_regime_summary(detector)
    
    # Create visualization
    create_visualization(detector, '/mnt/okcomputer/output/regime_visualization.png')
    
    # Export history
    export_regime_history(detector, '/mnt/okcomputer/output/regime_history.json')
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nOutput files:")
    print("  - regime_visualization.png")
    print("  - regime_history.json")
    print("\nFor more information, see REGIME_DETECTION_GUIDE.md")


if __name__ == "__main__":
    main()
