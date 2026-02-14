#!/usr/bin/env python3
"""
Dashboard Update Engine
Aggregates data from all systems and updates the unified monitoring dashboard
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

class DashboardUpdater:
    """Updates the unified monitoring dashboard with latest data"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.dashboard_dir = Path("monitoring/dashboard")
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)
        
    def load_alpha_signals(self) -> List[Dict]:
        """Load latest alpha signals"""
        signals_dir = self.data_dir / "signals"
        signals = []
        
        if not signals_dir.exists():
            return signals
        
        # Load signals from last 24 hours
        for file in signals_dir.glob("*.json"):
            try:
                with open(file) as f:
                    signal = json.load(f)
                    # Add metadata
                    signal['_source'] = 'alpha_signals'
                    signal['_file'] = file.name
                    signals.append(signal)
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        # Sort by confidence score
        signals.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
        return signals
    
    def load_gem_discoveries(self) -> List[Dict]:
        """Load latest gem discoveries"""
        gems_dir = self.data_dir / "gems"
        gems = []
        
        if not gems_dir.exists():
            return gems
        
        for file in gems_dir.glob("gem_*.json"):
            try:
                with open(file) as f:
                    gem = json.load(f)
                    gem['_source'] = 'goldmine_finder'
                    gem['_file'] = file.name
                    gems.append(gem)
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        # Sort by gem score
        gems.sort(key=lambda x: x.get('score', 0), reverse=True)
        return gems
    
    def load_predictions(self) -> List[Dict]:
        """Load prediction tracking status"""
        pred_file = self.data_dir / "predictions" / "current_status.json"
        
        if not pred_file.exists():
            return []
        
        try:
            with open(pred_file) as f:
                data = json.load(f)
                return data.get('predictions', [])
        except Exception as e:
            print(f"Error loading predictions: {e}")
            return []
    
    def load_strategy_performance(self) -> Dict:
        """Load strategy backtest results"""
        results_file = Path("strategy_backtest/results/final_rankings.json")
        
        if not results_file.exists():
            return {}
        
        try:
            with open(results_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading strategy results: {e}")
            return {}
    
    def aggregate_statistics(self) -> Dict:
        """Calculate aggregate statistics across all systems"""
        signals = self.load_alpha_signals()
        gems = self.load_gem_discoveries()
        predictions = self.load_predictions()
        
        # Alpha signals stats
        high_confidence_signals = [s for s in signals if s.get('confidence_score', 0) >= 80]
        s_plus_signals = [s for s in signals if s.get('confidence_score', 0) >= 96]
        
        # Gem stats
        high_potential_gems = [g for g in gems if g.get('score', 0) >= 80]
        
        # Prediction stats
        active_predictions = [p for p in predictions if p.get('status') == 'ACTIVE']
        won_predictions = [p for p in predictions if p.get('status') == 'WIN']
        
        win_rate = len(won_predictions) / (len(won_predictions) + len([p for p in predictions if p.get('status') == 'LOSS'])) * 100 if predictions else 0
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'alpha_signals': {
                'total_24h': len(signals),
                'high_confidence': len(high_confidence_signals),
                's_plus': len(s_plus_signals),
                'latest': signals[:3] if signals else []
            },
            'gem_discoveries': {
                'total_24h': len(gems),
                'high_potential': len(high_potential_gems),
                'latest': gems[:3] if gems else []
            },
            'predictions': {
                'active': len(active_predictions),
                'total_tracked': len(predictions),
                'win_rate': round(win_rate, 1),
                'wins': len(won_predictions)
            },
            'top_performers': {
                'alpha': signals[0] if signals else None,
                'gem': gems[0] if gems else None
            }
        }
    
    def generate_dashboard_data(self) -> Dict:
        """Generate comprehensive dashboard data"""
        stats = self.aggregate_statistics()
        
        dashboard_data = {
            'metadata': {
                'generated_at': stats['timestamp'],
                'version': '1.0',
                'systems': ['alpha_signals', 'goldmine_finder', 'predictions', 'strategy_backtest']
            },
            'overview': {
                'total_alpha_signals': stats['alpha_signals']['total_24h'],
                'total_gem_discoveries': stats['gem_discoveries']['total_24h'],
                'active_predictions': stats['predictions']['active'],
                'prediction_win_rate': stats['predictions']['win_rate'],
                'high_priority_alerts': stats['alpha_signals']['s_plus'] + stats['gem_discoveries']['high_potential']
            },
            'signals': self.load_alpha_signals()[:10],  # Top 10
            'gems': self.load_gem_discoveries()[:10],  # Top 10
            'predictions': self.load_predictions(),
            'statistics': stats
        }
        
        return dashboard_data
    
    def save_dashboard_data(self, data: Dict):
        """Save dashboard data for frontend consumption"""
        output_file = self.dashboard_dir / "data.json"
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Dashboard data saved to {output_file}")
    
    def generate_html_dashboard(self, data: Dict):
        """Generate static HTML dashboard"""
        # The HTML would be a copy of our dashboard with data injection
        # For now, we'll create a data loader that the HTML dashboard uses
        pass
    
    def update(self):
        """Main update routine"""
        print("🔄 Updating monitoring dashboard...")
        print("=" * 60)
        
        # Generate dashboard data
        data = self.generate_dashboard_data()
        
        # Save data
        self.save_dashboard_data(data)
        
        # Print summary
        print("\n📊 Dashboard Summary:")
        print(f"  Alpha Signals (24h): {data['overview']['total_alpha_signals']}")
        print(f"  Gem Discoveries (24h): {data['overview']['total_gem_discoveries']}")
        print(f"  Active Predictions: {data['overview']['active_predictions']}")
        print(f"  Prediction Win Rate: {data['overview']['prediction_win_rate']}%")
        print(f"  High Priority Alerts: {data['overview']['high_priority_alerts']}")
        
        print("\n✅ Dashboard update complete!")
        return data


def main():
    updater = DashboardUpdater()
    updater.update()


if __name__ == "__main__":
    main()
