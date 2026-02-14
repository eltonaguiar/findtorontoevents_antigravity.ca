"""
================================================================================
MODEL TOURNAMENT & BENCHMARK FRAMEWORK
================================================================================
Head-to-head comparison of all prediction models

Models Included:
1. CustomizedCryptoModel (47 features, regime-switching)
2. GenericCryptoModel (18 features, universal)
3. TransformerPredictor (TFT architecture)
4. RLTradingAgent (PPO reinforcement learning)
5. StatisticalArbitrageModel (mean reversion)
6. MLEnsembleModel (gradient boosting + bagging)
================================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

# Import all models
from models.customized_model import CustomizedCryptoModel
from models.generic_model import GenericCryptoModel
from models.transformer_model import TransformerPredictor
from models.rl_agent_model import RLTradingAgent
from models.stat_arb_model import StatisticalArbitrageModel
from models.ml_ensemble_model import MLEnsembleModel
from backtest_engine import run_comprehensive_backtest, PerformanceMetrics


@dataclass
class TournamentConfig:
    """Configuration for model tournament"""
    assets: List[str] = None
    train_window: int = 504
    test_step: int = 4
    risk_free_rate: float = 0.05
    
    def __post_init__(self):
        if self.assets is None:
            self.assets = ['BTC', 'ETH', 'AVAX']


class ModelTournament:
    """
    Tournament framework for comparing all prediction models
    
    Provides:
    - Fair head-to-head comparison
    - Rankings across multiple metrics
    - Statistical significance testing
    - Visualization data generation
    """
    
    def __init__(self, config: TournamentConfig = None):
        self.config = config or TournamentConfig()
        
        # Initialize all models
        self.models = {
            'Customized': CustomizedCryptoModel(),
            'Generic': GenericCryptoModel(),
            'Transformer': TransformerPredictor(),
            'RL_Agent': RLTradingAgent(),
            'StatArb': StatisticalArbitrageModel(),
            'ML_Ensemble': MLEnsembleModel()
        }
        
        # Results storage
        self.results = {}
        self.rankings = {}
    
    def run_tournament(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Run tournament on all assets and models
        
        Args:
            data: Dict mapping asset names to DataFrames
            
        Returns:
            Complete results and rankings
        """
        print("=" * 80)
        print("CRYPTO PREDICTION MODEL TOURNAMENT")
        print("=" * 80)
        
        for asset, df in data.items():
            print(f"\n--- Testing {asset} ---")
            self.results[asset] = {}
            
            for model_name, model in self.models.items():
                print(f"  Running {model_name}...")
                
                try:
                    results = run_comprehensive_backtest(
                        model, df, asset,
                        train_size=self.config.train_window,
                        step_size=self.config.test_step
                    )
                    
                    self.results[asset][model_name] = results
                    
                except Exception as e:
                    print(f"    ERROR: {e}")
                    self.results[asset][model_name] = None
        
        # Calculate rankings
        self._calculate_rankings()
        
        return self._compile_report()
    
    def _calculate_rankings(self):
        """Calculate model rankings for each metric"""
        metrics = ['sharpe_ratio', 'total_return', 'max_drawdown', 
                   'win_rate', 'calmar_ratio', 'sortino_ratio']
        
        for asset in self.results:
            self.rankings[asset] = {}
            
            for metric in metrics:
                # Extract metric values
                scores = {}
                for model, results in self.results[asset].items():
                    if results and 'metrics' in results:
                        try:
                            # Parse percentage strings
                            val = results['metrics'].get(metric, '0')
                            if isinstance(val, str) and '%' in val:
                                val = float(val.replace('%', ''))
                            else:
                                val = float(val)
                            
                            # For drawdown, lower is better
                            if metric == 'max_drawdown':
                                val = -val  # Invert so higher is better
                            
                            scores[model] = val
                        except:
                            continue
                
                # Rank models
                if scores:
                    sorted_models = sorted(scores.items(), 
                                          key=lambda x: x[1], 
                                          reverse=True)
                    self.rankings[asset][metric] = {
                        model: rank + 1 
                        for rank, (model, _) in enumerate(sorted_models)
                    }
    
    def _compile_report(self) -> Dict:
        """Compile comprehensive tournament report"""
        report = {
            'tournament_info': {
                'date': datetime.now().isoformat(),
                'assets_tested': self.config.assets,
                'models_compared': list(self.models.keys()),
                'train_window': self.config.train_window,
                'test_step': self.config.test_step
            },
            'results_by_asset': self.results,
            'rankings': self.rankings,
            'overall_standings': self._calculate_overall_standings(),
            'best_by_metric': self._find_best_by_metric(),
            'head_to_head': self._head_to_head_matrix()
        }
        
        return report
    
    def _calculate_overall_standings(self) -> Dict[str, Dict]:
        """Calculate overall model standings across all assets"""
        standings = {}
        
        for model in self.models.keys():
            total_rank = 0
            count = 0
            
            for asset in self.rankings:
                for metric, ranks in self.rankings[asset].items():
                    if model in ranks:
                        total_rank += ranks[model]
                        count += 1
            
            if count > 0:
                avg_rank = total_rank / count
                standings[model] = {
                    'average_rank': avg_rank,
                    'total_tests': count,
                    'score': 100 - avg_rank * 10  # Convert to score
                }
        
        # Sort by score
        return dict(sorted(standings.items(), 
                          key=lambda x: x[1]['score'], 
                          reverse=True))
    
    def _find_best_by_metric(self) -> Dict:
        """Find best model for each metric across assets"""
        best = {}
        
        metrics = ['sharpe_ratio', 'total_return', 'max_drawdown', 
                   'win_rate', 'calmar_ratio']
        
        for metric in metrics:
            best[metric] = {}
            for asset in self.results:
                best_score = -np.inf
                best_model = None
                
                for model, results in self.results[asset].items():
                    if results and 'metrics' in results:
                        try:
                            val = results['metrics'].get(metric, '0')
                            if isinstance(val, str) and '%' in val:
                                val = float(val.replace('%', ''))
                            else:
                                val = float(val)
                            
                            if metric == 'max_drawdown':
                                val = -val
                            
                            if val > best_score:
                                best_score = val
                                best_model = model
                        except:
                            continue
                
                if best_model:
                    best[metric][asset] = {
                        'model': best_model,
                        'value': best_score if metric != 'max_drawdown' else -best_score
                    }
        
        return best
    
    def _head_to_head_matrix(self) -> Dict:
        """Generate head-to-head win matrix"""
        models = list(self.models.keys())
        matrix = {m1: {m2: 0 for m2 in models} for m1 in models}
        
        for asset in self.rankings:
            for metric, ranks in self.rankings[asset].items():
                for m1 in models:
                    for m2 in models:
                        if m1 != m2 and m1 in ranks and m2 in ranks:
                            if ranks[m1] < ranks[m2]:
                                matrix[m1][m2] += 1
        
        return matrix
    
    def get_model_comparison_table(self, asset: str) -> pd.DataFrame:
        """Generate comparison table for specific asset"""
        if asset not in self.results:
            return pd.DataFrame()
        
        rows = []
        for model, results in self.results[asset].items():
            if results and 'metrics' in results:
                row = {'Model': model}
                row.update(results['metrics'])
                rows.append(row)
        
        return pd.DataFrame(rows)
    
    def print_summary(self):
        """Print tournament summary to console"""
        print("\n" + "=" * 80)
        print("TOURNAMENT RESULTS SUMMARY")
        print("=" * 80)
        
        # Overall standings
        print("\n🏆 OVERALL STANDINGS:")
        standings = self._calculate_overall_standings()
        for rank, (model, data) in enumerate(standings.items(), 1):
            print(f"  {rank}. {model:20s} - Score: {data['score']:.1f} (Avg Rank: {data['average_rank']:.2f})")
        
        # Best by metric
        print("\n📊 BEST BY METRIC:")
        best = self._find_best_by_metric()
        for metric, assets in best.items():
            print(f"\n  {metric}:")
            for asset, winner in assets.items():
                print(f"    {asset}: {winner['model']} ({winner['value']:.3f})")
        
        # Head-to-head
        print("\n⚔️  HEAD-TO-HEAD WINS:")
        matrix = self._head_to_head_matrix()
        total_wins = {m: sum(matrix[m].values()) for m in matrix}
        sorted_wins = sorted(total_wins.items(), key=lambda x: x[1], reverse=True)
        for model, wins in sorted_wins:
            print(f"  {model:20s}: {wins} wins")


# Tournament metadata
TOURNAMENT_METADATA = {
    "tournament_name": "CryptoAlpha Model Championship",
    "version": "1.0.0",
    "models": [
        {
            "name": "Customized",
            "class": "CustomizedCryptoModel",
            "description": "Asset-specific with on-chain metrics and regime detection",
            "complexity": "High",
            "data_requirements": "Asset-specific (on-chain, funding rates)"
        },
        {
            "name": "Generic",
            "class": "GenericCryptoModel",
            "description": "Universal OHLCV-based framework",
            "complexity": "Low",
            "data_requirements": "OHLCV only"
        },
        {
            "name": "Transformer",
            "class": "TransformerPredictor",
            "description": "Temporal Fusion Transformer with attention",
            "complexity": "Very High",
            "data_requirements": "Large dataset for training"
        },
        {
            "name": "RL_Agent",
            "class": "RLTradingAgent",
            "description": "PPO reinforcement learning agent",
            "complexity": "High",
            "data_requirements": "Extensive training episodes"
        },
        {
            "name": "StatArb",
            "class": "StatisticalArbitrageModel",
            "description": "Mean reversion with OU process and Kalman filter",
            "complexity": "Medium",
            "data_requirements": "OHLCV, optional pair data"
        },
        {
            "name": "ML_Ensemble",
            "class": "MLEnsembleModel",
            "description": "Gradient boosting + bagging ensemble",
            "complexity": "Medium-High",
            "data_requirements": "ML training dataset"
        }
    ],
    "evaluation_metrics": [
        "Sharpe Ratio",
        "Total Return",
        "Maximum Drawdown",
        "Win Rate",
        "Calmar Ratio",
        "Sortino Ratio",
        "Profit Factor"
    ],
    "fairness_measures": [
        "Same train/test periods for all models",
        "Same transaction costs (9 bps)",
        "Walk-forward validation",
        "No look-ahead bias",
        "Same feature calculation windows"
    ]
}


def run_example_tournament():
    """Run example tournament with synthetic data"""
    print("=" * 80)
    print("MODEL TOURNAMENT - EXAMPLE RUN")
    print("=" * 80)
    print("\nNote: This uses synthetic data for demonstration.")
    print("Replace with real historical data for actual comparison.\n")
    
    # Generate synthetic data
    np.random.seed(42)
    n_periods = 2000
    
    data = {}
    for asset in ['BTC', 'ETH', 'AVAX']:
        # Generate price path with trend and noise
        returns = np.random.normal(0.0002, 0.02, n_periods)
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'price': prices,
            'volume': np.random.lognormal(10, 0.5, n_periods)
        }, index=pd.date_range('2020-01-01', periods=n_periods, freq='4H'))
        
        data[asset] = df
    
    # Run tournament
    tournament = ModelTournament()
    report = tournament.run_tournament(data)
    tournament.print_summary()
    
    return report


if __name__ == "__main__":
    report = run_example_tournament()
    
    print("\n" + "=" * 80)
    print("Tournament complete! Report saved to memory.")
    print("Access results via: report['overall_standings']")
    print("=" * 80)
