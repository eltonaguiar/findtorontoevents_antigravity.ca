#!/usr/bin/env python3
"""
Subagent: BTCUSDT Edge Investigation & Enhancement
Mission: Investigate why the most liquid crypto pair has zero tradeable models and develop BTC-specific strategies
Research findings: BTCUSDT appears in pairs_without_edge despite being the most liquid
"""

import json
from datetime import datetime
from pathlib import Path

class BTCEdgeResearcher:
    def __init__(self):
        self.research_dir = Path('ml_crypto_predictor/enhanced_models/results')
        self.output_dir = Path('research/subagent_reports')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def investigate_btc_failure(self):
        """Deep dive into why BTCUSDT has no edge across all timeframes"""
        report = {
            'subagent': 'btcusdt_edge_investigation',
            'timestamp': datetime.now().isoformat(),
            'problem_statement': 'BTCUSDT — the most liquid, most traded crypto pair — has ZERO tradeable models across all 5 timeframes',
            'hypotheses': self._generate_failure_hypotheses(),
            'data_analysis': self._analyze_btc_characteristics(),
            'strategy_enhancements': self._design_btc_specific_strategies(),
            'implementation_roadmap': self._create_btc_roadmap(),
            'validation_plan': self._define_btc_validation()
        }
        return report

    def _generate_failure_hypotheses(self):
        """Why does BTC fail to produce edge?"""
        return [
            {
                'hypothesis': 'BTC is too efficient — EMH holds better for top-liquidity assets',
                'evidence': 'High liquidity means information disseminates instantly; any alpha is arbitraged away within seconds',
                'implication': 'Need strategies that exploit microstructure or cross-asset relative value, not pure price momentum'
            },
            {
                'hypothesis': 'BTC dominance creates correlation saturation',
                'evidence': 'BTC moves with macro factors (Fed policy, ETF flows) that are exogenous to technical patterns',
                'implication': 'Incorporate macro features (SPX, DXY, BTC dominance index, ETF net flows)'
            },
            {
                'hypothesis': 'Lower volatility regime in recent BTC reduces mean-reversion opportunities',
                'evidence': 'BTC volatility has decreased post-ETF approval; strategies need adaptation',
                'implication': 'Volatility‑adjusted position sizing and strategy selection based on regime'
            },
            {
                'hypothesis': 'Current strategies are too generic — BTC requires custom feature engineering',
                'evidence': 'Same feature set works for altcoins but not BTC; BTC is a different beast',
                'implication': 'Design BTC-exclusive features: on-chain metrics, dominance ratio, ETF flows proxy'
            }
        ]

    def _analyze_btc_characteristics(self):
        """What makes BTC unique"""
        return {
            'liquidity_profile': {
                'spread': '0.01% typical (tighter than alts)',
                'impact': 'Large orders have minimal slippage',
                'implication': 'Edge must come from information, not liquidity provision'
            },
            'volatility_regime': {
                'daily_vol_2024': '~3% (down from 5-6% in 2021-2022)',
                'intraday_patterns': 'Lower volatility during Asian session; highest during US overlap',
                'implication': 'ATR-based stops need dynamic calibration'
            },
            'correlation_environment': {
                'correlation_to_SPX': '0.6-0.8 (macro‑driven)',
                'correlation_to_DXY': '-0.5 to -0.7',
                'correlation_to_alts': '0.7-0.9 (but varies)',
                'implication': ' BTC moves on macro news, not crypto‑specific TA'
            },
            'on_chain_factors': {
                ' NUPL (Net Unrealized Profit/Loss)': 'Contrarian indicator — extreme greed = reversal',
                'MVRV Ratio': 'Market Value to Realized Value — identifies bubbles',
                'Exchange Netflow': 'Outflows = accumulation (bullish), inflows = distribution',
                'implied': 'These can be integrated as regime features'
            }
        }

    def _design_btc_specific_strategies(self):
        """Custom strategies for BTC"""
        return [
            {
                'name': 'Macro‑Regime BTC Strategy',
                'core_idea': 'Fade extreme macro correlations when BTC deviates from SPX/DXY regimes',
                'features': [
                    'SPX 5‑day returns normalized',
                    'DXY 5‑day returns normalized',
                    'BTC/SPX ratio z‑score (20‑day)',
                    'BTC dominance 5‑day change',
                    'Fear & Greed Index (proxy via social sentiment)'
                ],
                'model_type': 'Ensemble: Random Forest + Gradient Boosting',
                'target': 'next 4‑8 hour return (regime‑dependent)',
                'validation': 'Walk‑forward with macro regime holdout (e.g., Fed meeting weeks)'
            },
            {
                'name': 'On‑Chain Regime‑Aware BTC Strategy',
                'core_idea': 'Use on‑chain metrics to detect overbought/oversold and trade mean‑reversion',
                'features': [
                    'NUPL (7‑day EMA)',
                    'MVRV Z‑score (30‑day)',
                    'Exchange Netflow 24h delta',
                    'BTC 30‑day realized volatility',
                    'Funding rates (perpetual futures) as sentiment gauge'
                ],
                'model_type': 'LightGBM with monotonic constraints',
                'target': 'next 12‑24 hour return (longer horizon for on‑chain)',
                'notes': 'Low turnover (6‑12 trades/month); high conviction'
            },
            {
                'name': 'BTC‑Alt Correlation Arbitrage',
                'core_idea': 'When BTC stagnates but alts pump (or vice versa), trade the most correlated pairs',
                'features': [
                    'BTC 24h return (benchmark)',
                    'Top 5 alts 24h returns',
                    'Alt‑BTC beta (rolling 24h)',
                    'Correlation matrix rank (which alt diverges most)',
                   DXY and SPX correlations to BTC'
                ],
                'model_type': 'Pair‑specific dynamic selector (same as existing but BTC‑filtered)',
                'target': 'next 6‑12 hour relative return vs BTC',
                'notes': 'Only trades when BTC volatility < threshold (avoid regime shifts)'
            },
            {
                'name': 'Liquidity‑Cycle BTC Strategy',
                'core_idea': 'Exploit intraday liquidity patterns unique to BTC (Asian vs US session)',
                'features': [
                    'hour_of_day_utc (one‑hot)',
                    'spread_dynamic (rolling 1‑hour median)',
                    'volume_profile_deviation (current volume vs daily average)',
                    'order_book_imbalance_proxy (close‑location in range)',
                    'funding_rate (for perpetuals)'
                ],
                'model_type': 'Neural network with temporal convolutions',
                'target': 'next 2‑4 hour return (session‑specific)',
                'notes': 'Higher turnover; requires 5m or 15m data; strict risk caps'
            }
        ]

    def _create_btc_roadmap(self):
        return [
            'Week 1: Integrate macro data feeds (FRED API for SPX/DXY, CryptoQuant for on‑chain)',
            'Week 2: Engineer BTC‑specific features + regime labels',
            'Week 3: Train 4 candidate BTC models on 2 years of hourly data',
            'Week 4: Walk‑forward validation with regime‑aware splits',
            'Week 5: Forward test (paper trading) — 14‑day incubation',
            'Week 6: If any model passes (Sharpe >1.0, WR >55%), integrate into live pipeline'
        ]

    def _define_btc_validation(self):
        return {
            'benchmarks': [
                'Buy‑and‑hold BTC Sharpe (typically 0.8‑1.2)',
                'Existing v4.1 altcoin average Sharpe (1.34)',
                'Simpleton v0.07 BTC model (if exists)'
            ],
            'must_pass_filters': [
                'Monte Carlo p < 0.05',
                'Deflated Sharpe Ratio positive',
                'Max drawdown < 20%',
                'Minimum trades: 30 (longer hold, fewer trades)'
            ],
            'economic_costs': '0.1% Binance taker fee + 0.05% slippage assumption'
        }

    def save_report(self):
        report = self.investigate_btc_failure()
        filename = self.output_dir / 'btcusdt_edge_investigation.json'
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f'✅ BTC edge report saved: {filename}')
        return filename

if __name__ == '__main__':
    researcher = BTCEdgeResearcher()
    researcher.save_report()
