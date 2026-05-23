#!/usr/bin/env python3
"""
Risk-Adjusted Performance Analysis
Ranks strategies by true risk-adjusted returns
"""

import json
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Strategy:
    id: str
    name: str
    category: str
    engine: str
    return_pct: float
    sharpe: float = 0.0
    win_rate: float = 50.0
    max_drawdown: float = -20.0
    volatility: float = 15.0
    downside_deviation: float = 10.0
    avg_win: float = 5.0
    avg_loss: float = -3.0
    trades_per_month: float = 20.0
    status: str = "ACTIVE"
    
    # Risk-adjusted metrics (calculated)
    sortino: float = 0.0
    calmar: float = 0.0
    omega: float = 0.0
    tail_ratio: float = 0.0
    common_sense_ratio: float = 0.0
    adjusted_return: float = 0.0
    
    # Stress test results
    stress_2008: float = 0.0
    stress_covid: float = 0.0
    stress_2022: float = 0.0
    stress_flash: float = 0.0
    stress_gap: float = 0.0
    
    # Real-world adjustments
    costs_adjusted_return: float = 0.0
    tax_adjusted_return: float = 0.0

class RiskAdjustedAnalyzer:
    """Calculate advanced risk metrics and stress tests"""
    
    # Real-world cost assumptions
    TRANSACTION_COST_PCT = 0.05  # 0.05% per trade (commission + spread)
    SLIPPAGE_PCT = 0.03  # 0.03% slippage per trade
    BORROW_COST_ANNUAL = 0.02  # 2% annual for short positions
    MARGIN_REQUIREMENT = 0.25  # 25% margin requirement
    SHORT_TERM_TAX_RATE = 0.37  # 37% short-term capital gains
    LONG_TERM_TAX_RATE = 0.20  # 20% long-term capital gains
    
    def __init__(self):
        self.strategies: List[Strategy] = []
        
    def load_strategies(self):
        """Load strategies from data files"""
        # Load from complete_strategies.json
        try:
            with open('/root/.openclaw/workspace/KIMI_RISEOFTHECLAW/data/complete_strategies.json', 'r') as f:
                data = json.load(f)
                
            # Crypto Signals
            for s in data['engines']['crypto_signals']['strategies']:
                self.strategies.append(Strategy(
                    id=s['id'],
                    name=s['name'],
                    category='Crypto Signals',
                    engine='Crypto Signals',
                    return_pct=s.get('return', 0),
                    sharpe=s.get('sharpe', 0),
                    status=s.get('status', 'ACTIVE'),
                    volatility=25.0 if 'BTC' in s['name'] or 'ETH' in s['name'] else 20.0,
                    max_drawdown=-15.0 if s.get('sharpe', 0) > 0.5 else -25.0,
                    trades_per_month=30
                ))
                
            # Alpha Engine
            for s in data['engines']['alpha_engine']['strategies']:
                holding = s.get('holding', '5 days')
                days = self._parse_holding_period(holding)
                self.strategies.append(Strategy(
                    id=s.get('id', s['name'].replace(' ', '_')),
                    name=s['name'],
                    category='Alpha Engine',
                    engine='Alpha Engine',
                    return_pct=s.get('return', 0),
                    status=s.get('status', 'ACTIVE'),
                    volatility=18.0,
                    max_drawdown=-12.0,
                    trades_per_month=20 if days < 7 else 8
                ))
                
            # Live Monitor
            for s in data['engines']['live_monitor']['strategies']:
                self.strategies.append(Strategy(
                    id=s.get('id', s['name'].replace(' ', '_')),
                    name=s['name'],
                    category='Live Monitor',
                    engine='Live Monitor',
                    return_pct=s.get('return', 0),
                    status=s.get('status', 'ACTIVE'),
                    volatility=22.0,
                    max_drawdown=-18.0,
                    trades_per_month=40
                ))
                
            # Backtest Arena
            for s in data['engines']['backtest_arena']['strategies']:
                self.strategies.append(Strategy(
                    id=s['id'],
                    name=s['name'],
                    category='Backtest Arena',
                    engine='Backtest Arena',
                    return_pct=s.get('return', 0),
                    status=s.get('status', 'ACTIVE'),
                    volatility=16.0,
                    max_drawdown=-14.0,
                    trades_per_month=15
                ))
                
            # Algo Battle
            for s in data['engines']['algo_battle']['strategies']:
                self.strategies.append(Strategy(
                    id=s['id'],
                    name=s['name'],
                    category='Algo Battle',
                    engine='Algo Battle',
                    return_pct=s.get('return', 0),
                    win_rate=s.get('winRate', 55.0),
                    status=s.get('status', 'ACTIVE'),
                    volatility=20.0,
                    max_drawdown=-15.0,
                    trades_per_month=25
                ))
                
            # Specialized
            for s in data['engines']['specialized']['strategies']:
                self.strategies.append(Strategy(
                    id=s['id'],
                    name=s['name'],
                    category='Specialized',
                    engine='Specialized',
                    return_pct=s.get('return', 0),
                    status=s.get('status', 'ACTIVE'),
                    volatility=35.0 if 'Meme' in s['name'] or 'Pump' in s['name'] else 25.0,
                    max_drawdown=-25.0 if 'Meme' in s['name'] or 'Pump' in s['name'] else -18.0,
                    trades_per_month=50 if 'Meme' in s['name'] else 30
                ))
                
        except Exception as e:
            print(f"Error loading strategies: {e}")
            
    def _parse_holding_period(self, holding: str) -> int:
        """Parse holding period string to days"""
        if 'day' in holding.lower():
            try:
                return int(''.join(filter(str.isdigit, holding.split()[0])))
            except:
                return 5
        elif 'intraday' in holding.lower():
            return 1
        return 5
        
    def calculate_sortino_ratio(self, strategy: Strategy) -> float:
        """
        Sortino Ratio = (Return - Risk Free Rate) / Downside Deviation
        Measures return per unit of downside risk
        """
        risk_free_rate = 2.0  # 2% risk-free rate
        downside_dev = abs(strategy.downside_deviation) if strategy.downside_deviation != 0 else 5.0
        
        # Estimate downside deviation from max drawdown if not available
        if downside_dev < 1:
            downside_dev = abs(strategy.max_drawdown) * 0.6
            
        sortino = (strategy.return_pct - risk_free_rate) / downside_dev
        return round(sortino, 3)
        
    def calculate_calmar_ratio(self, strategy: Strategy) -> float:
        """
        Calmar Ratio = Annual Return / Maximum Drawdown
        Measures return per unit of maximum drawdown
        """
        max_dd = abs(strategy.max_drawdown) if strategy.max_drawdown != 0 else 15.0
        calmar = strategy.return_pct / max_dd
        return round(calmar, 3)
        
    def calculate_omega_ratio(self, strategy: Strategy) -> float:
        """
        Omega Ratio = Sum of gains above threshold / Sum of losses below threshold
        Uses threshold = 0 (risk-free rate adjusted)
        """
        # Estimate from win rate and avg win/loss
        win_rate = strategy.win_rate / 100
        avg_win = strategy.avg_win
        avg_loss = abs(strategy.avg_loss)
        
        # Expected gains above threshold
        gains = win_rate * avg_win
        # Expected losses below threshold  
        losses = (1 - win_rate) * avg_loss
        
        if losses == 0:
            return 2.0
            
        omega = gains / losses
        return round(omega, 3)
        
    def calculate_tail_ratio(self, strategy: Strategy) -> float:
        """
        Tail Ratio = 95th percentile gain / 95th percentile loss
        Measures upside potential vs downside risk
        """
        # Estimate from volatility
        vol = strategy.volatility
        
        # 95th percentile approx 1.645 * vol
        upside = 1.645 * vol * (strategy.win_rate / 50)  # Adjust for win rate
        downside = 1.645 * vol * ((100 - strategy.win_rate) / 50)
        
        if downside == 0:
            return 1.5
            
        tail = upside / downside
        return round(tail, 3)
        
    def calculate_common_sense_ratio(self, strategy: Strategy) -> float:
        """
        Common Sense Ratio = (Win Rate * Avg Win) / (Loss Rate * Avg Loss)
        Simple but effective risk-adjusted metric
        """
        win_rate = strategy.win_rate / 100
        loss_rate = 1 - win_rate
        avg_win = strategy.avg_win
        avg_loss = abs(strategy.avg_loss)
        
        numerator = win_rate * avg_win
        denominator = loss_rate * avg_loss
        
        if denominator == 0:
            return 2.0
            
        csr = numerator / denominator
        return round(csr, 3)
        
    def apply_transaction_costs(self, strategy: Strategy) -> float:
        """Adjust returns for transaction costs"""
        trades_per_year = strategy.trades_per_month * 12
        cost_per_trade = self.TRANSACTION_COST_PCT + self.SLIPPAGE_PCT
        total_cost = trades_per_year * cost_per_trade
        
        return strategy.return_pct - total_cost
        
    def apply_tax_adjustment(self, strategy: Strategy, holding_days: int = 5) -> float:
        """Adjust returns for tax implications"""
        tax_rate = self.LONG_TERM_TAX_RATE if holding_days > 365 else self.SHORT_TERM_TAX_RATE
        after_tax_return = strategy.return_pct * (1 - tax_rate)
        return after_tax_return
        
    def stress_test_2008(self, strategy: Strategy) -> float:
        """
        Stress test: 2008-style financial crisis
        - Market down ~50%
        - Correlations → 1.0
        - Liquidity dries up
        """
        base_return = strategy.return_pct
        
        # Different strategies perform differently in 2008
        if 'Momentum' in strategy.name or 'Trend' in strategy.name:
            # Trend following can do well
            return base_return * 0.7
        elif 'Mean Reversion' in strategy.name or 'Reversal' in strategy.name:
            # Mean reversion gets crushed
            return base_return * 0.2
        elif 'Breakout' in strategy.name:
            # Breakouts fail in choppy markets
            return base_return * 0.4
        elif 'Arbitrage' in strategy.name or 'StatArb' in strategy.name:
            # Correlations break
            return base_return * 0.3
        elif 'Options' in strategy.name:
            # Volatility spike helps option sellers initially
            return base_return * 0.5
        else:
            return base_return * 0.5
            
    def stress_test_covid(self, strategy: Strategy) -> float:
        """
        Stress test: 2020 COVID crash
        - Sudden 35% drop in weeks
        - V-shaped recovery
        - High volatility
        """
        base_return = strategy.return_pct
        
        if 'Momentum' in strategy.name:
            return base_return * 0.6
        elif 'Mean Reversion' in strategy.name:
            return base_return * 0.8  # V-recovery helps
        elif 'Breakout' in strategy.name:
            return base_return * 0.5
        elif 'Scalp' in strategy.name or '0DTE' in strategy.name:
            # High vol helps scalpers
            return base_return * 0.9
        else:
            return base_return * 0.65
            
    def stress_test_2022(self, strategy: Strategy) -> float:
        """
        Stress test: 2022 bear market
        - Sustained downtrend
        - Inflation/rate hikes
        - Tech selloff
        """
        base_return = strategy.return_pct
        
        if 'Short' in strategy.name or 'Inverse' in strategy.name:
            return base_return * 1.3  # Short strategies do well
        elif 'Long' in strategy.name or 'Buy' in strategy.name:
            return base_return * 0.4
        elif 'Crypto' in strategy.category:
            return base_return * 0.3  # Crypto crushed in 2022
        else:
            return base_return * 0.6
            
    def stress_test_flash_crash(self, strategy: Strategy) -> float:
        """
        Stress test: Flash crash scenario
        - 10% drop in minutes
        - Liquidity evaporates
        - Stop losses fail
        """
        base_return = strategy.return_pct
        
        if 'HFT' in strategy.name or 'High Frequency' in strategy.name:
            return base_return * 0.1  # HFT gets destroyed
        elif 'Scalp' in strategy.name:
            return base_return * 0.3
        elif 'Options' in strategy.name:
            return base_return * 0.4
        else:
            return base_return * 0.7
            
    def stress_test_gap_risk(self, strategy: Strategy) -> float:
        """
        Stress test: Gap risk
        - Overnight gaps against positions
        - Stop losses not honored
        """
        base_return = strategy.return_pct
        
        if 'Overnight' in strategy.name or 'Swing' in strategy.name:
            return base_return * 0.6
        elif 'Day' in strategy.name or 'Intraday' in strategy.name or '0DTE' in strategy.name:
            return base_return * 0.95  # No overnight risk
        else:
            return base_return * 0.75
            
    def calculate_comprehensive_score(self, strategy: Strategy) -> float:
        """
        Calculate comprehensive risk-adjusted score
        Weights:
        - Sharpe: 20%
        - Sortino: 20%
        - Calmar: 20%
        - Omega: 10%
        - Tail Ratio: 10%
        - Common Sense Ratio: 10%
        - Stress Test Average: 10%
        """
        # Normalize metrics to 0-100 scale
        sharpe_score = min(max(strategy.sharpe * 25, 0), 100)  # Sharpe 4 = 100
        sortino_score = min(max(strategy.sortino * 20, 0), 100)  # Sortino 5 = 100
        calmar_score = min(max(strategy.calmar * 33, 0), 100)  # Calmar 3 = 100
        omega_score = min(max((strategy.omega - 0.5) * 50, 0), 100)  # Omega 2.5 = 100
        tail_score = min(max(strategy.tail_ratio * 40, 0), 100)  # Tail 2.5 = 100
        csr_score = min(max(strategy.common_sense_ratio * 25, 0), 100)  # CSR 4 = 100
        
        # Stress test average
        stress_avg = (strategy.stress_2008 + strategy.stress_covid + 
                     strategy.stress_2022 + strategy.stress_flash + strategy.stress_gap) / 5
        stress_score = min(max(stress_avg * 0.5, 0), 100)  # Normalize
        
        # Weighted composite
        composite = (
            sharpe_score * 0.20 +
            sortino_score * 0.20 +
            calmar_score * 0.20 +
            omega_score * 0.10 +
            tail_score * 0.10 +
            csr_score * 0.10 +
            stress_score * 0.10
        )
        
        return round(composite, 2)
        
    def analyze_all(self):
        """Run complete risk-adjusted analysis on all strategies"""
        self.load_strategies()
        
        results = []
        for strategy in self.strategies:
            # Skip eliminated strategies
            if strategy.status == 'ELIMINATE':
                continue
                
            # Calculate risk metrics
            strategy.sortino = self.calculate_sortino_ratio(strategy)
            strategy.calmar = self.calculate_calmar_ratio(strategy)
            strategy.omega = self.calculate_omega_ratio(strategy)
            strategy.tail_ratio = self.calculate_tail_ratio(strategy)
            strategy.common_sense_ratio = self.calculate_common_sense_ratio(strategy)
            
            # Apply real-world adjustments
            strategy.costs_adjusted_return = self.apply_transaction_costs(strategy)
            strategy.tax_adjusted_return = self.apply_tax_adjustment(strategy)
            
            # Stress tests
            strategy.stress_2008 = self.stress_test_2008(strategy)
            strategy.stress_covid = self.stress_test_covid(strategy)
            strategy.stress_2022 = self.stress_test_2022(strategy)
            strategy.stress_flash = self.stress_test_flash_crash(strategy)
            strategy.stress_gap = self.stress_test_gap_risk(strategy)
            
            # Calculate comprehensive score
            strategy.adjusted_return = self.calculate_comprehensive_score(strategy)
            
            results.append(strategy)
            
        return results
        
    def generate_report(self, strategies: List[Strategy]) -> str:
        """Generate comprehensive risk-adjusted ranking report"""
        
        # Sort by adjusted return
        ranked = sorted(strategies, key=lambda x: x.adjusted_return, reverse=True)
        
        report = []
        report.append("=" * 100)
        report.append("RISK-ADJUSTED PERFORMANCE ANALYSIS REPORT")
        report.append("=" * 100)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Strategies Analyzed: {len(strategies)}")
        report.append("")
        
        # Top 30 by risk-adjusted returns
        report.append("=" * 100)
        report.append("TOP 30 STRATEGIES - RISK-ADJUSTED RANKINGS")
        report.append("=" * 100)
        report.append("")
        report.append(f"{'Rank':<5} {'Strategy':<35} {'Engine':<18} {'Sharpe':<8} {'Sortino':<8} {'Calmar':<8} {'Omega':<7} {'CSR':<6} {'Adj.Score':<10} {'Status':<10}")
        report.append("-" * 100)
        
        for i, s in enumerate(ranked[:30], 1):
            report.append(f"{i:<5} {s.name[:34]:<35} {s.engine[:17]:<18} {s.sharpe:<8.2f} {s.sortino:<8.2f} {s.calmar:<8.2f} {s.omega:<7.2f} {s.common_sense_ratio:<6.2f} {s.adjusted_return:<10.1f} {s.status:<10}")
            
        report.append("")
        report.append("=" * 100)
        report.append("DETAILED TOP 10 ANALYSIS")
        report.append("=" * 100)
        report.append("")
        
        for i, s in enumerate(ranked[:10], 1):
            report.append(f"\n{'='*80}")
            report.append(f"#{i} - {s.name}")
            report.append(f"{'='*80}")
            report.append(f"  Engine:          {s.engine}")
            report.append(f"  Category:        {s.category}")
            report.append(f"  Raw Return:      {s.return_pct:.1f}%")
            report.append(f"  After Costs:     {s.costs_adjusted_return:.1f}%")
            report.append(f"  After Tax:       {s.tax_adjusted_return:.1f}%")
            report.append("")
            report.append("  RISK METRICS:")
            report.append(f"    Sharpe Ratio:        {s.sharpe:.3f}")
            report.append(f"    Sortino Ratio:       {s.sortino:.3f}")
            report.append(f"    Calmar Ratio:        {s.calmar:.3f}")
            report.append(f"    Omega Ratio:         {s.omega:.3f}")
            report.append(f"    Tail Ratio:          {s.tail_ratio:.3f}")
            report.append(f"    Common Sense Ratio:  {s.common_sense_ratio:.3f}")
            report.append("")
            report.append("  STRESS TEST RESULTS:")
            report.append(f"    2008 Crash:          {s.stress_2008:.1f}%")
            report.append(f"    COVID Crash:         {s.stress_covid:.1f}%")
            report.append(f"    2022 Bear Market:    {s.stress_2022:.1f}%")
            report.append(f"    Flash Crash:         {s.stress_flash:.1f}%")
            report.append(f"    Gap Risk:            {s.stress_gap:.1f}%")
            report.append(f"    Average Stress:      {np.mean([s.stress_2008, s.stress_covid, s.stress_2022, s.stress_flash, s.stress_gap]):.1f}%")
            report.append("")
            report.append(f"  COMPOSITE RISK-ADJUSTED SCORE: {s.adjusted_return:.1f}")
            
        # Category rankings
        report.append("")
        report.append("=" * 100)
        report.append("CATEGORY PERFORMANCE SUMMARY")
        report.append("=" * 100)
        report.append("")
        
        categories = {}
        for s in strategies:
            if s.category not in categories:
                categories[s.category] = []
            categories[s.category].append(s)
            
        for cat, strats in sorted(categories.items(), key=lambda x: np.mean([s.adjusted_return for s in x[1]]), reverse=True):
            avg_score = np.mean([s.adjusted_return for s in strats])
            avg_sharpe = np.mean([s.sharpe for s in strats])
            avg_calmar = np.mean([s.calmar for s in strats])
            report.append(f"{cat:<25} | Avg Score: {avg_score:>6.1f} | Avg Sharpe: {avg_sharpe:>5.2f} | Avg Calmar: {avg_calmar:>5.2f} | Count: {len(strats)}")
            
        # Most robust to tail events
        report.append("")
        report.append("=" * 100)
        report.append("MOST ROBUST TO TAIL EVENTS (Top 10)")
        report.append("=" * 100)
        report.append("")
        
        robust_ranked = sorted(strategies, key=lambda x: min(x.stress_2008, x.stress_covid, x.stress_2022, x.stress_flash, x.stress_gap), reverse=True)
        report.append(f"{'Rank':<5} {'Strategy':<40} {'Min Stress':<12} {'Avg Stress':<12}")
        report.append("-" * 70)
        
        for i, s in enumerate(robust_ranked[:10], 1):
            min_stress = min(s.stress_2008, s.stress_covid, s.stress_2022, s.stress_flash, s.stress_gap)
            avg_stress = np.mean([s.stress_2008, s.stress_covid, s.stress_2022, s.stress_flash, s.stress_gap])
            report.append(f"{i:<5} {s.name[:39]:<40} {min_stress:>10.1f}% {avg_stress:>10.1f}%")
            
        # Best drawdown recovery (Calmar)
        report.append("")
        report.append("=" * 100)
        report.append("BEST DRAWDOWN RECOVERY (Top 10 by Calmar Ratio)")
        report.append("=" * 100)
        report.append("")
        
        calmar_ranked = sorted(strategies, key=lambda x: x.calmar, reverse=True)
        report.append(f"{'Rank':<5} {'Strategy':<40} {'Calmar':<10} {'Return':<10} {'Max DD':<10}")
        report.append("-" * 75)
        
        for i, s in enumerate(calmar_ranked[:10], 1):
            report.append(f"{i:<5} {s.name[:39]:<40} {s.calmar:>8.2f} {s.return_pct:>8.1f}% {s.max_drawdown:>8.1f}%")
            
        # Most consistent (Sortino)
        report.append("")
        report.append("=" * 100)
        report.append("MOST CONSISTENT PERFORMERS (Top 10 by Sortino Ratio)")
        report.append("=" * 100)
        report.append("")
        
        sortino_ranked = sorted(strategies, key=lambda x: x.sortino, reverse=True)
        report.append(f"{'Rank':<5} {'Strategy':<40} {'Sortino':<10} {'Return':<10} {'Downside':<10}")
        report.append("-" * 75)
        
        for i, s in enumerate(sortino_ranked[:10], 1):
            report.append(f"{i:<5} {s.name[:39]:<40} {s.sortino:>8.2f} {s.return_pct:>8.1f}% {s.downside_deviation:>8.1f}%")
            
        return "\n".join(report)


def main():
    analyzer = RiskAdjustedAnalyzer()
    strategies = analyzer.analyze_all()
    report = analyzer.generate_report(strategies)
    
    # Save report
    with open('/root/.openclaw/workspace/RISK_ADJUSTED_RANKINGS.txt', 'w') as f:
        f.write(report)
        
    # Save JSON data
    output = []
    for s in sorted(strategies, key=lambda x: x.adjusted_return, reverse=True)[:30]:
        output.append({
            'rank': len(output) + 1,
            'id': s.id,
            'name': s.name,
            'engine': s.engine,
            'category': s.category,
            'raw_return': s.return_pct,
            'costs_adjusted': s.costs_adjusted_return,
            'tax_adjusted': s.tax_adjusted_return,
            'sharpe': s.sharpe,
            'sortino': s.sortino,
            'calmar': s.calmar,
            'omega': s.omega,
            'tail_ratio': s.tail_ratio,
            'common_sense_ratio': s.common_sense_ratio,
            'composite_score': s.adjusted_return,
            'stress_2008': s.stress_2008,
            'stress_covid': s.stress_covid,
            'stress_2022': s.stress_2022,
            'stress_flash': s.stress_flash,
            'stress_gap': s.stress_gap,
            'status': s.status
        })
        
    with open('/root/.openclaw/workspace/risk_adjusted_rankings.json', 'w') as f:
        json.dump(output, f, indent=2)
        
    print(report)
    print(f"\n\nReport saved to: /root/.openclaw/workspace/RISK_ADJUSTED_RANKINGS.txt")
    print(f"JSON data saved to: /root/.openclaw/workspace/risk_adjusted_rankings.json")


if __name__ == "__main__":
    main()
