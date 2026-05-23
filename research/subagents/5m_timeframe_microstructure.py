#!/usr/bin/env python3
"""
Subagent: 5m Timeframe Strategy Development
Mission: Develop microstructure strategies that can generate edge on 5m timeframe
Research findings: Currently zero models passed on 5m — this is the single biggest gap
"""

import json
from datetime import datetime
from pathlib import Path

class MicrostructureStrategyResearcher:
    def __init__(self):
        self.research_dir = Path('ml_crypto_predictor/enhanced_models/results')
        self.output_dir = Path('research/subagent_reports')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_5m_failure(self):
        """Understand why 5m failed and design microstructure solutions"""
        report = {
            'subagent': '5m_timeframe_microstructure',
            'timestamp': datetime.now().isoformat(),
            'problem_statement': 'Zero tradeable models on 5m timeframe — all 40 pairs failed edge threshold',
            'root_causes': [
                'Microstructure noise dominates signal at sub-15m frequencies',
                'Bid-ask spread and slippage are larger relative to price moves',
                'Order book imbalance changes faster than ML can react with 1m candles',
                'Current feature set (RSI, MACD, etc.) too lagging for scalping regimes'
            ],
            'research_directions': self._design_microstructure_approaches(),
            'feature_engineering': self._propose_5m_specific_features(),
            'validation_framework': self._define_5m_validation(),
            'implementation_plan': self._create_implementation_roadmap(),
            'success_metrics': {
                'target_sharpe': '>0.8 (conservative for 5m)',
                'min_trades': '50+ per pair to overcome noise',
                'max_drawdown': '<15% (higher tolerance for scalping)',
                'win_rate': '>52% after costs'
            }
        }
        return report

    def _design_microstructure_approaches(self):
        """Research-backed microstructure strategies for 5m"""
        return [
            {
                'name': 'Order Flow Imbalance',
                'description': 'Use trade-based flow: buy_volume vs sell_volume, trade count imbalance, large trade detection',
                'rationale': 'Research shows order flow predicts 5-15m price moves better than price-based indicators',
                'features': [
                    'volume_imbalance_ratio (buy vol / total)',
                    'large_trade_detection (threshold: >5x avg trade size)',
                    'trade_count_delta (change in trade frequency)',
                    'bid_ask_spread_dynamic (rolling mean of spread %)' # Note: may need API access
                ],
                'implementation': 'Requires Binance trade stream API (not just klines) — upgrade data pipeline'
            },
            {
                'name': 'Liquidity Grab Detection',
                'description': 'Identify rapid price movements through support/resistance that sweep stops',
                'rationale': 'ICT/SMC literature: liquidity sweeps create short-term reversal opportunities',
                'features': [
                    'price_velocity (price change / volume)',
                    'wick_to_body_ratio (long wicks indicate rejection)',
                    'previous_high_low_breaks_velocity',
                    'volume_spike_detection (detect stop hunts)'
                ],
                'implementation': 'Can be implemented with existing OHLCV + volume'
            },
            {
                'name': 'Micro-Order-Book Signals',
                'description': 'Simulate order book pressure using kline patterns and volume profile',
                'rationale': 'Without direct order book API, we infer from price action and volatility',
                'features': [
                    'bid_ask_imbalance_proxy (close location relative to range)',
                    'volatility_adjusted_range (ATR normalized)',
                    'rolling_volume_profile (volume at price buckets)',
                    'micro_gap_fill_tendency (do gaps fill within 3 bars?)'
                ],
                'implementation': 'Pure OHLCV — no external data needed'
            },
            {
                'name': 'Cross-Pair Arbitrage Signals',
                'description': 'Identify relative value moves between correlated pairs on 5m',
                'rationale': 'Statistical arbitrage on 5m: mean reversion between BTC and top alts',
                'features': [
                    'returns_spread (e.g., NEAR - BTC normalized)',
                    'zscore_5m (rolling 20-bar z-score of spread)',
                    'correlation_change (5m vs 1h correlation delta)',
                    'pair_beta_dynamic (rolling beta to BTC)'
                ],
                'implementation': 'Requires multi-pair synchronized data'
            }
        ]

    def _propose_5m_specific_features(self):
        """Feature engineering specific to 5m edge"""
        return {
            'technical_features': [
                ' Quintessence Scalp RSI (3, 5, 7) — ultra-short RSI',
                'Volume-weighted MACD (signal tuned to 5m cycles)',
                'HLC/3 deviation from VWAP (5m VWAP)',
                'Micro-trend detection: EMA(3) vs EMA(7) crossover',
                '5m realized volatility (rolling std of returns)'
            ],
            'derived_features': [
                'signal_to_noise_ratio (price move / ATR)',
                'liquidity_adjusted_returns (return / volume)',
                'microstructure_efficiency (close proximity to VWAP)',
                'momentum_decay (how fast 5m momentum reverses)',
                'hourly_session_effect (first/last 5m of hour)'
            ],
            'targets': [
                '5m forward return (next 2-3 bars)',
                'deltaprice_change_3_bars (3 * 5m = 15min outlook)',
                'risk_adjusted_target (return ATR)'
            ]
        }

    def _define_5m_validation(self):
        """Stricter validation for 5m due to noise"""
        return {
            'walk_forward_5m_specific': {
                'purge_gap': '10 bars (50 minutes) — larger due to autocorrelation',
                'fold_count': '8 folds (more folds for robustness)',
                'training_window': '5000 bars ≈ 17 days of 5m data',
                'testing_window': '1000 bars ≈ 3.5 days'
            },
            'noise_filters': [
                'Minimum trades: 50 per model (reduce luck impact)',
                'Monte Carlo: 20,000 permutations (more than standard 10k)',
                'Deflated Sharpe: use 1.5x standard error multiplier',
                'Require positive skew (avoid negative tail risk models)'
            ],
            'economic_traces': [
                'Commission + slippage = 0.15% total per trade (higher for 5m)',
                'Max position duration: 4 hours (no overnight)',
                'Daily loss limit: 3% of capital per model'
            ]
        }

    def _create_implementation_roadmap(self):
        return [
            'Week 1: Build trade stream data pipeline (Binance WebSocket)',
            'Week 2: Implement order flow imbalance features',
            'Week 3: Train 5m models with microstructural features only',
            'Week 4: Validate with 8-fold walk-forward + Monte Carlo 20k',
            'Week 5: Paper trade top 5 models for 7 days (forward test)',
            'Week 6: Analyze results; if Sharpe >0.8 and WR >52%, deploy to live'
        ]

    def save_report(self):
        report = self.analyze_5m_failure()
        filename = self.output_dir / '5m_microstructure_research.json'
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f'✅ 5m research report saved: {filename}')
        return filename

if __name__ == '__main__':
    researcher = MicrostructureStrategyResearcher()
    researcher.save_report()
