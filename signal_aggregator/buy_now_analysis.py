#!/usr/bin/env python3
"""
Buy Now Analysis - Comprehensive Signal Evaluation & Backtesting

Analyzes what would be sent to #master-picks and #freshpicks,
backtests performance with $100 per pick, and determines
which strategies/systems are worth following.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.insert(0, '.')
from signal_aggregator.price_fetcher import get_current_price

# Constants
INVESTMENT_PER_PICK = 100.0  # $100 per pick
MASTER_THRESHOLD = 0.80      # 80%+ confidence for master-picks
FRESH_THRESHOLD = 0.60       # 60-79% confidence for freshpicks

@dataclass
class PickPerformance:
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    entry_time: str
    system: str
    confidence: float
    pnl_percent: float
    pnl_dollar: float  # Based on $100 investment
    status: str  # 'win', 'loss', 'open'

class BuyNowAnalyzer:
    def __init__(self):
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'master_picks': [],
            'freshpicks': [],
            'rejected': [],
            'performance_by_system': {},
            'performance_by_strategy': {},
            'recommendations': []
        }
    
    def load_all_historical_picks(self) -> List[Dict]:
        """Load picks from all system closed_picks files"""
        all_picks = []
        
        system_files = {
            'mercury2': 'mercury2/data/closed_picks.json',
            'alpha_engine': 'alpha_engine/data/closed_picks.json',
            'dna_genome': 'genome/active_picks.json',  # Has closed picks too
            'claws_of_doom': 'ml_battleground/system_f_clawsofdoom/data/closed_picks.json',
        }
        
        for system, filepath in system_files.items():
            path = Path(filepath)
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    
                    picks = data if isinstance(data, list) else data.get('picks', data.get('closed_picks', []))
                    
                    for pick in picks:
                        pick['system_source'] = system
                        # Normalize fields
                        if 'realized_pnl_pct' in pick or 'pnl' in pick or 'unrealized_pnl_pct' in pick:
                            all_picks.append(pick)
                            
                except Exception as e:
                    print(f"Error loading {system}: {e}")
        
        return all_picks
    
    def calculate_performance(self, picks: List[Dict]) -> Dict:
        """Calculate performance metrics for a set of picks"""
        if not picks:
            return {'error': 'No picks to analyze'}

        # dict.get(key, default) returns the default only when the key is absent;
        # explicit None values fall through and break numeric comparisons.
        def _pnl(p):
            for k in ('realized_pnl_pct', 'pnl', 'unrealized_pnl_pct'):
                v = p.get(k)
                if v is not None:
                    return v
            return 0

        total_picks = len(picks)
        winners = [p for p in picks if _pnl(p) > 0]
        losers = [p for p in picks if _pnl(p) <= 0]

        # Calculate returns
        returns = [_pnl(p) for p in picks]
        total_return_pct = sum(returns)

        # Dollar returns (assuming $100 per pick)
        dollar_returns = [(r/100) * INVESTMENT_PER_PICK for r in returns]
        total_profit_loss = sum(dollar_returns)

        # Win rate
        win_rate = len(winners) / total_picks * 100 if total_picks > 0 else 0

        # Profit factor
        gross_profit = sum(_pnl(p) for p in winners)
        gross_loss = abs(sum(_pnl(p) for p in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average return per pick
        avg_return = total_return_pct / total_picks if total_picks > 0 else 0
        avg_dollar_return = total_profit_loss / total_picks if total_picks > 0 else 0
        
        # Max drawdown (simplified)
        cumulative = 0
        max_dd = 0
        peak = 0
        for r in returns:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_picks': total_picks,
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': round(win_rate, 1),
            'total_return_pct': round(total_return_pct, 2),
            'total_profit_loss': round(total_profit_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_return_per_pick': round(avg_return, 2),
            'avg_dollar_return': round(avg_dollar_return, 2),
            'max_drawdown_pct': round(max_dd, 2),
            'roi_percent': round((total_profit_loss / (total_picks * INVESTMENT_PER_PICK)) * 100, 2)
        }
    
    def analyze_by_system(self, picks: List[Dict]) -> Dict:
        """Group picks by system and calculate performance"""
        by_system = {}
        
        for pick in picks:
            system = pick.get('system_source', pick.get('system', 'unknown'))
            if system not in by_system:
                by_system[system] = []
            by_system[system].append(pick)
        
        results = {}
        for system, system_picks in by_system.items():
            results[system] = self.calculate_performance(system_picks)
            results[system]['pick_count'] = len(system_picks)
        
        # Sort by ROI
        return dict(sorted(results.items(), key=lambda x: x[1].get('roi_percent', 0), reverse=True))
    
    def generate_buy_recommendations(self, current_picks: List[Dict]) -> List[Dict]:
        """Generate buy/hold/skip recommendations for current picks"""
        recommendations = []
        
        for pick in current_picks:
            symbol = pick.get('symbol', 'UNKNOWN')
            entry = pick.get('entry_price', 0)
            current = get_current_price(symbol)
            
            if not current or not entry:
                continue
            
            # Calculate current position
            direction = pick.get('direction', 'LONG')
            if direction == 'LONG':
                current_pnl = ((current - entry) / entry) * 100
            else:
                current_pnl = ((entry - current) / entry) * 100
            
            # Generate recommendation
            recommendation = {
                'symbol': symbol,
                'direction': direction,
                'entry': entry,
                'current': current,
                'current_pnl': round(current_pnl, 2),
                'system': pick.get('system', 'unknown'),
                'confidence': pick.get('confidence', 0)
            }
            
            # Decision logic
            if current_pnl > 5:
                recommendation['action'] = 'HOLD / TAKE PROFITS'
                recommendation['reason'] = f'Already up {current_pnl:.1f}%, consider taking profits'
            elif current_pnl < -3:
                recommendation['action'] = 'SKIP / WAIT'
                recommendation['reason'] = f'Down {abs(current_pnl):.1f}% from entry, wait for better entry'
            else:
                recommendation['action'] = 'BUY NOW'
                recommendation['reason'] = f'Within 3% of entry, good time to enter'
            
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x['confidence'], reverse=True)
    
    def run_analysis(self):
        """Run complete buy-now analysis"""
        print("=" * 80)
        print("BUY NOW ANALYSIS - Signal Performance & Backtesting")
        print("=" * 80)
        
        # Load historical picks
        print("\n[LOADING] Loading historical picks from all systems...")
        all_picks = self.load_all_historical_picks()
        print(f"   Loaded {len(all_picks)} historical picks")
        
        # Overall performance
        print("\n" + "=" * 80)
        print("OVERALL PERFORMANCE ($100 per pick)")
        print("=" * 80)
        overall = self.calculate_performance(all_picks)
        for key, value in overall.items():
            if isinstance(value, float):
                print(f"   {key}: {value}")
        
        # Performance by system
        print("\n" + "=" * 80)
        print("PERFORMANCE BY SYSTEM (Ranked by ROI)")
        print("=" * 80)
        by_system = self.analyze_by_system(all_picks)
        
        print(f"\n{'System':<25} {'Picks':<8} {'Win Rate':<10} {'ROI %':<10} {'Profit Factor':<15} {'Verdict'}")
        print("-" * 90)
        
        for system, stats in by_system.items():
            picks = stats.get('pick_count', 0)
            wr = stats.get('win_rate', 0)
            roi = stats.get('roi_percent', 0)
            pf = stats.get('profit_factor', 0)
            
            # Verdict
            if roi > 10 and pf > 1.5:
                verdict = "[YES] FOLLOW"
            elif roi > 0 and pf > 1.0:
                verdict = "[WARN]  CAUTION"
            else:
                verdict = "[NO] AVOID"
            
            print(f"{system:<25} {picks:<8} {wr:<10.1f} {roi:<10.1f} {pf:<15.2f} {verdict}")
        
        # Current actionable picks
        print("\n" + "=" * 80)
        print("CURRENT BUY RECOMMENDATIONS")
        print("=" * 80)
        
        # Get current picks from genome and other systems
        current_picks = []
        
        # Load genome active picks
        genome_file = Path('genome/active_picks.json')
        if genome_file.exists():
            with open(genome_file) as f:
                data = json.load(f)
            for pick in data.get('picks', []):
                pick['system'] = 'dna_genome'
                current_picks.append(pick)
        
        # Load mercury2 active picks
        mercury_file = Path('mercury2/data/active_picks.json')
        if mercury_file.exists():
            with open(mercury_file) as f:
                picks = json.load(f)
            for pick in picks:
                pick['system'] = 'mercury2'
                current_picks.append(pick)
        
        recommendations = self.generate_buy_recommendations(current_picks)
        
        if recommendations:
            print(f"\n{'Symbol':<12} {'Dir':<6} {'Entry':<12} {'Current':<12} {'P/L':<10} {'Action':<20}")
            print("-" * 100)
            for rec in recommendations[:10]:
                action = rec['action']
                if 'BUY' in action:
                    action_icon = "[BUY]"
                elif 'HOLD' in action:
                    action_icon = "[HOLD]"
                else:
                    action_icon = "[SKIP]"
                
                print(f"{rec['symbol']:<12} {rec['direction']:<6} ${rec['entry']:<11.2f} ${rec['current']:<11.2f} {rec['current_pnl']:<9.1f}% {action_icon} {action}")
                print(f"     -> {rec['reason']}")
        else:
            print("   No current actionable picks found")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        
        # Best system
        best_system = list(by_system.keys())[0] if by_system else None
        if best_system:
            best_stats = by_system[best_system]
            print(f"\n[BEST] Best Performing System: {best_system}")
            print(f"   ROI: {best_stats.get('roi_percent', 0):.1f}% | Win Rate: {best_stats.get('win_rate', 0):.1f}% | Profit Factor: {best_stats.get('profit_factor', 0):.2f}")
        
        # Worth it verdict
        total_roi = overall.get('roi_percent', 0)
        print(f"\n[MONEY] Overall Strategy Verdict:")
        if total_roi > 20:
            print(f"   [YES] EXCELLENT - Following these signals with $100/pick would have made ${overall.get('total_profit_loss', 0):.2f} ({total_roi:.1f}% ROI)")
        elif total_roi > 5:
            print(f"   [YES] PROFITABLE - Following these signals with $100/pick would have made ${overall.get('total_profit_loss', 0):.2f} ({total_roi:.1f}% ROI)")
        elif total_roi > -5:
            print(f"   [WARN]  BREAK EVEN - Following these signals would have resulted in ${overall.get('total_profit_loss', 0):.2f} ({total_roi:.1f}% ROI)")
        else:
            print(f"   [NO] LOSING - Following these signals would have LOST ${abs(overall.get('total_profit_loss', 0)):.2f} ({total_roi:.1f}% ROI)")
        
        print("\n" + "=" * 80)

if __name__ == '__main__':
    analyzer = BuyNowAnalyzer()
    analyzer.run_analysis()
