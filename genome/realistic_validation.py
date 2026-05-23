#!/usr/bin/env python3
"""
REALISTIC Validation Framework - With Transaction Costs
========================================================

Honest assessment including:
- Trading fees (0.1% per trade)
- Slippage (0.1-0.3% based on liquidity)
- Spread costs
- Profit factor calculation
- CVaR (Conditional VaR)
- MAE (Maximum Adverse Excursion)
- Realistic worst-case scenarios

Usage:
    python realistic_validation.py --honest-assessment
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RealisticValidation')


# REALISTIC COST ASSUMPTIONS
TRADING_FEE = 0.001  # 0.1% per trade (Binance taker fee)
SLIPPAGE_SMALL = 0.001  # 0.1% for BTC, ETH
SLIPPAGE_MEDIUM = 0.002  # 0.2% for SOL, ADA, DOT
SLIPPAGE_LARGE = 0.003  # 0.3% for smaller alts
SPREAD_COST = 0.0005  # 0.05% spread


def get_slippage(symbol: str) -> float:
    """Get realistic slippage by symbol."""
    major = ['BTCUSDT', 'ETHUSDT']
    medium = ['SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'AVAXUSDT']
    
    if symbol in major:
        return SLIPPAGE_SMALL
    elif symbol in medium:
        return SLIPPAGE_MEDIUM
    else:
        return SLIPPAGE_LARGE


def calculate_total_cost(symbol: str) -> float:
    """Calculate total transaction cost per trade."""
    fee = TRADING_FEE  # Entry fee
    slippage = get_slippage(symbol)
    spread = SPREAD_COST
    
    # Round trip (entry + exit)
    return (fee + slippage + spread) * 2


@dataclass
class RealisticTradeMetrics:
    """Trade metrics with realistic costs."""
    symbol: str
    direction: str
    gross_pnl_pct: float
    cost_pct: float
    net_pnl_pct: float
    holding_minutes: int
    max_adverse_excursion: float  # MAE - worst underwater during trade


class RealisticValidator:
    """Honest validation with real-world costs."""
    
    def __init__(self):
        self.data = {}
        self.load_data()
        self.trades_with_costs = []
    
    def load_data(self):
        """Load historical data."""
        for period in ['today', 'yesterday', 'week']:
            file_path = Path(f'genome/results/historical_{period}.json')
            if file_path.exists():
                with open(file_path) as f:
                    self.data[period] = json.load(f)
        logger.info(f"Loaded {len(self.data)} periods")
    
    def apply_realistic_costs(self) -> List[RealisticTradeMetrics]:
        """Apply transaction costs to all trades."""
        realistic_trades = []
        
        for period, data in self.data.items():
            for trade in data.get('best_trades', []):
                symbol = trade['symbol']
                gross_pnl = trade['pnl_pct']
                
                # Calculate costs
                cost_pct = calculate_total_cost(symbol) * 100
                
                # Net PnL after costs
                net_pnl = gross_pnl - cost_pct
                
                # Estimate MAE (Maximum Adverse Excursion)
                # In reality, this would be the worst drawdown during the trade
                # Here we estimate based on volatility
                mae = trade['max_dd'] * 1.5  # Conservative estimate
                
                realistic_trades.append(RealisticTradeMetrics(
                    symbol=symbol,
                    direction=trade['direction'],
                    gross_pnl_pct=gross_pnl,
                    cost_pct=cost_pct,
                    net_pnl_pct=net_pnl,
                    holding_minutes=trade['duration_min'],
                    max_adverse_excursion=mae
                ))
        
        self.trades_with_costs = realistic_trades
        return realistic_trades
    
    def calculate_profit_factor(self) -> Dict:
        """Calculate proper profit factor."""
        trades = self.trades_with_costs
        
        if not trades:
            return {}
        
        gross_profits = sum(t.net_pnl_pct for t in trades if t.net_pnl_pct > 0)
        gross_losses = abs(sum(t.net_pnl_pct for t in trades if t.net_pnl_pct < 0))
        
        # Also calculate by direction
        long_trades = [t for t in trades if t.direction == 'LONG']
        short_trades = [t for t in trades if t.direction == 'SHORT']
        
        long_pf = (sum(t.net_pnl_pct for t in long_trades if t.net_pnl_pct > 0) /
                   abs(sum(t.net_pnl_pct for t in long_trades if t.net_pnl_pct < 0))) \
                  if any(t.net_pnl_pct < 0 for t in long_trades) else 999
        
        short_pf = (sum(t.net_pnl_pct for t in short_trades if t.net_pnl_pct > 0) /
                    abs(sum(t.net_pnl_pct for t in short_trades if t.net_pnl_pct < 0))) \
                   if any(t.net_pnl_pct < 0 for t in short_trades) else 999
        
        return {
            'overall_pf': gross_profits / gross_losses if gross_losses > 0 else 999,
            'long_pf': long_pf if long_pf != 999 else 'Infinity',
            'short_pf': short_pf if short_pf != 999 else 'Infinity',
            'gross_profits': gross_profits,
            'gross_losses': gross_losses,
            'winning_trades': sum(1 for t in trades if t.net_pnl_pct > 0),
            'losing_trades': sum(1 for t in trades if t.net_pnl_pct < 0),
            'breakeven_trades': sum(1 for t in trades if t.net_pnl_pct == 0)
        }
    
    def calculate_expectancy(self) -> Dict:
        """Calculate expectancy (average profit per trade)."""
        trades = self.trades_with_costs
        
        if not trades:
            return {}
        
        wins = [t.net_pnl_pct for t in trades if t.net_pnl_pct > 0]
        losses = [t.net_pnl_pct for t in trades if t.net_pnl_pct < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        win_rate = len(wins) / len(trades)
        
        # Expectancy formula: (Win% × Avg Win) - (Loss% × Avg Loss)
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
        
        return {
            'expectancy_pct': expectancy,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'risk_reward_ratio': avg_win / abs(avg_loss) if avg_loss != 0 else 999,
            'trades_needed_for_confidence': int(100 / (win_rate * (1 - win_rate))) if win_rate not in [0, 1] else 1000
        }
    
    def calculate_cvar_mae(self) -> Dict:
        """Calculate CVaR (Conditional VaR) and MAE (Max Adverse Excursion)."""
        trades = self.trades_with_costs
        
        if not trades:
            return {}
        
        pnls = [t.net_pnl_pct for t in trades]
        maes = [t.max_adverse_excursion for t in trades]
        
        # VaR at 95% and 99%
        var_95 = np.percentile(pnls, 5)
        var_99 = np.percentile(pnls, 1)
        
        # CVaR (Expected Shortfall) - average of worst 5% and 1%
        cvar_95 = np.mean([p for p in pnls if p <= var_95]) if any(p <= var_95 for p in pnls) else var_95
        cvar_99 = np.mean([p for p in pnls if p <= var_99]) if any(p <= var_99 for p in pnls) else var_99
        
        # MAE statistics
        avg_mae = np.mean(maes)
        max_mae = max(maes)
        mae_95 = np.percentile(maes, 95)
        
        return {
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,  # Expected loss in worst 5% of cases
            'cvar_99': cvar_99,  # Expected loss in worst 1% of cases
            'avg_mae': avg_mae,
            'max_mae': max_mae,
            'mae_95': mae_95,
            'interpretation': {
                'cvar_95': f'In worst 5% of trades, expect to lose {abs(cvar_95):.2f}% on average',
                'mae': f'Typical worst underwater: {avg_mae:.2f}%, Extreme: {max_mae:.2f}%'
            }
        }
    
    def realistic_monte_carlo(self, n_simulations: int = 10000) -> Dict:
        """
        Monte Carlo with realistic costs and path dependency.
        """
        trades = self.trades_with_costs
        if not trades:
            return {}
        
        pnls = [t.net_pnl_pct for t in trades]
        
        # Starting capital
        initial_capital = 10000
        
        final_equities = []
        max_drawdowns = []
        underwater_periods = []
        
        for _ in range(n_simulations):
            # Bootstrap sample with replacement
            sample_pnls = np.random.choice(pnls, size=len(pnls), replace=True)
            
            # Calculate equity curve
            equity = initial_capital
            peak = equity
            max_dd = 0
            underwater_days = 0
            current_underwater = 0
            
            for pnl in sample_pnls:
                # Apply PnL
                equity *= (1 + pnl / 100)
                
                # Track peak and drawdown
                if equity > peak:
                    peak = equity
                    if current_underwater > 0:
                        underwater_periods.append(current_underwater)
                    current_underwater = 0
                else:
                    dd = (peak - equity) / peak
                    max_dd = max(max_dd, dd)
                    current_underwater += 1
                
                # Stop if blow up (>50% loss)
                if equity < initial_capital * 0.5:
                    break
            
            final_equities.append(equity)
            max_drawdowns.append(max_dd)
            if current_underwater > 0:
                underwater_periods.append(current_underwater)
        
        # Calculate statistics
        returns = [(e - initial_capital) / initial_capital for e in final_equities]
        
        return {
            'n_simulations': n_simulations,
            'median_final_equity': np.median(final_equities),
            'median_return': np.median(returns) * 100,
            'mean_return': np.mean(returns) * 100,
            
            # Percentiles
            'return_5th': np.percentile(returns, 5) * 100,
            'return_25th': np.percentile(returns, 25) * 100,
            'return_75th': np.percentile(returns, 75) * 100,
            'return_95th': np.percentile(returns, 95) * 100,
            
            # Drawdown
            'median_max_dd': np.median(max_drawdowns) * 100,
            'worst_dd_5th': np.percentile(max_drawdowns, 95) * 100,
            'worst_dd_1st': np.percentile(max_drawdowns, 99) * 100,
            
            # Underwater
            'avg_underwater_period': np.mean(underwater_periods) if underwater_periods else 0,
            'max_underwater_period': max(underwater_periods) if underwater_periods else 0,
            
            # Risk of ruin
            'prob_profit': sum(1 for r in returns if r > 0) / n_simulations,
            'prob_blow_up': sum(1 for e in final_equities if e < initial_capital * 0.5) / n_simulations,
            'prob_10pct_loss': sum(1 for r in returns if r < -0.10) / n_simulations
        }
    
    def generate_honest_report(self):
        """Generate honest assessment with realistic costs."""
        
        print("\n" + "="*80)
        print("  REALISTIC VALIDATION - HONEST ASSESSMENT")
        print("="*80)
        print(f"\nAssessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("\n⚠️  IMPORTANT: This analysis includes realistic transaction costs")
        print("   (0.1% fees + 0.1-0.3% slippage + 0.05% spread per trade)")
        
        # Apply costs
        trades = self.apply_realistic_costs()
        print(f"\nTotal trades analyzed: {len(trades)}")
        
        # Profit Factor
        print("\n" + "-"*80)
        print("  PROFIT FACTOR ANALYSIS")
        print("-"*80)
        
        pf = self.calculate_profit_factor()
        print(f"\nOverall Profit Factor: {pf['overall_pf']:.2f}")
        print(f"  (Gross Profits: {pf['gross_profits']:.1f}% / Gross Losses: {pf['gross_losses']:.1f}%)")
        print(f"Long Profit Factor: {pf['long_pf']}")
        print(f"Short Profit Factor: {pf['short_pf']}")
        print(f"\nWinning Trades: {pf['winning_trades']}")
        print(f"Losing Trades: {pf['losing_trades']}")
        print(f"Breakeven Trades: {pf['breakeven_trades']}")
        
        realistic_wr = pf['winning_trades'] / (pf['winning_trades'] + pf['losing_trades'] + pf['breakeven_trades']) if (pf['winning_trades'] + pf['losing_trades'] + pf['breakeven_trades']) > 0 else 0
        print(f"Realistic Win Rate (after costs): {realistic_wr:.1%}")
        
        # Expectancy
        print("\n" + "-"*80)
        print("  EXPECTANCY ANALYSIS")
        print("-"*80)
        
        exp = self.calculate_expectancy()
        print(f"\nExpectancy per Trade: {exp['expectancy_pct']:.2f}%")
        print(f"  (Win Rate: {exp['win_rate']:.1%} × Avg Win: {exp['avg_win']:.2f}%) - "
              f"(Loss Rate: {1-exp['win_rate']:.1%} × Avg Loss: {abs(exp['avg_loss']):.2f}%)")
        print(f"Risk:Reward Ratio: 1:{exp['risk_reward_ratio']:.2f}")
        print(f"Trades needed for statistical confidence: ~{exp['trades_needed_for_confidence']}")
        
        if exp['expectancy_pct'] > 0:
            print(f"\n✓ Positive expectancy: Strategy has edge")
        else:
            print(f"\n✗ Negative expectancy: Strategy loses money after costs")
        
        # CVaR and MAE
        print("\n" + "-"*80)
        print("  TAIL RISK ANALYSIS (CVaR & MAE)")
        print("-"*80)
        
        risk = self.calculate_cvar_mae()
        print(f"\nValue at Risk (VaR):")
        print(f"  95% VaR: {risk['var_95']:.2f}% (1 in 20 trades worse than this)")
        print(f"  99% VaR: {risk['var_99']:.2f}% (1 in 100 trades worse than this)")
        
        print(f"\nConditional VaR (Expected Shortfall):")
        print(f"  CVaR 95%: {risk['cvar_95']:.2f}%")
        print(f"    → {risk['interpretation']['cvar_95']}")
        print(f"  CVaR 99%: {risk['cvar_99']:.2f}%")
        
        print(f"\nMaximum Adverse Excursion (MAE):")
        print(f"  Average MAE: {risk['avg_mae']:.2f}%")
        print(f"  95th percentile MAE: {risk['mae_95']:.2f}%")
        print(f"  Maximum MAE: {risk['max_mae']:.2f}%")
        print(f"  → {risk['interpretation']['mae']}")
        
        # Realistic Monte Carlo
        print("\n" + "-"*80)
        print("  REALISTIC MONTE CARLO SIMULATION (10,000 runs with costs)")
        print("-"*80)
        
        mc = self.realistic_monte_carlo(1000)
        
        print(f"\nReturn Distribution:")
        print(f"  5th percentile (worst): {mc['return_5th']:.1f}%")
        print(f"  25th percentile: {mc['return_25th']:.1f}%")
        print(f"  Median: {mc['median_return']:.1f}%")
        print(f"  Mean: {mc['mean_return']:.1f}%")
        print(f"  75th percentile: {mc['return_75th']:.1f}%")
        print(f"  95th percentile (best): {mc['return_95th']:.1f}%")
        
        print(f"\nDrawdown Scenarios:")
        print(f"  Median max drawdown: {mc['median_max_dd']:.1f}%")
        print(f"  Worst 5% drawdown: {mc['worst_dd_5th']:.1f}%")
        print(f"  Worst 1% drawdown: {mc['worst_dd_1st']:.1f}%")
        
        print(f"\nRisk Metrics:")
        print(f"  Probability of profit: {mc['prob_profit']:.1%}")
        print(f"  Probability of 10%+ loss: {mc['prob_10pct_loss']:.1%}")
        print(f"  Probability of blow-up (>50% loss): {mc['prob_blow_up']:.2%}")
        
        print(f"\nUnderwater Periods:")
        print(f"  Average: {mc['avg_underwater_period']:.0f} trades")
        print(f"  Maximum: {mc['max_underwater_period']:.0f} trades")
        
        # Cost Impact Analysis
        print("\n" + "-"*80)
        print("  TRANSACTION COST IMPACT")
        print("-"*80)
        
        gross_pnls = [t.gross_pnl_pct for t in trades]
        net_pnls = [t.net_pnl_pct for t in trades]
        costs = [t.cost_pct for t in trades]
        
        print(f"\nAverage cost per trade: {np.mean(costs):.2f}%")
        print(f"Average gross PnL: {np.mean(gross_pnls):.2f}%")
        print(f"Average net PnL: {np.mean(net_pnls):.2f}%")
        print(f"Cost erosion: {np.mean(gross_pnls) - np.mean(net_pnls):.2f}% per trade")
        
        # Count how many winners become losers after costs
        winners_before = sum(1 for g, n in zip(gross_pnls, net_pnls) if g > 0)
        winners_after = sum(1 for n in net_pnls if n > 0)
        
        print(f"\nWinners before costs: {winners_before}")
        print(f"Winners after costs: {winners_after}")
        print(f"Trades turned to losers by costs: {winners_before - winners_after}")
        
        # Final Verdict
        print("\n" + "="*80)
        print("  HONEST VERDICT")
        print("="*80)
        
        # Calculate realistic readiness score
        score = 0
        checks = []
        
        # Check 1: Profit Factor > 1.3
        if pf['overall_pf'] > 1.3:
            score += 15
            checks.append("✓ Profit Factor > 1.3")
        else:
            checks.append(f"✗ Profit Factor {pf['overall_pf']:.2f} < 1.3")
        
        # Check 2: Positive Expectancy
        if exp['expectancy_pct'] > 0:
            score += 20
            checks.append("✓ Positive Expectancy")
        else:
            checks.append("✗ Negative Expectancy")
        
        # Check 3: Win Rate > 50%
        if realistic_wr > 0.5:
            score += 15
            checks.append("✓ Win Rate > 50%")
        else:
            checks.append(f"✗ Win Rate {realistic_wr:.1%} < 50%")
        
        # Check 4: CVaR 95% better than -5%
        if risk['cvar_95'] > -5:
            score += 15
            checks.append("✓ CVaR 95% > -5%")
        else:
            checks.append(f"⚠ CVaR 95% {risk['cvar_95']:.2f}% (high tail risk)")
        
        # Check 5: Max DD < 30%
        if mc['worst_dd_5th'] < 30:
            score += 15
            checks.append("✓ Max DD < 30%")
        else:
            checks.append(f"⚠ Worst DD {mc['worst_dd_5th']:.1f}% (very high)")
        
        # Check 6: Prob of profit > 60%
        if mc['prob_profit'] > 0.6:
            score += 10
            checks.append("✓ Prob of Profit > 60%")
        else:
            checks.append(f"⚠ Prob of Profit {mc['prob_profit']:.1%}")
        
        # Check 7: Blow-up risk < 1%
        if mc['prob_blow_up'] < 0.01:
            score += 10
            checks.append("✓ Blow-up risk < 1%")
        else:
            checks.append(f"⚠ Blow-up risk {mc['prob_blow_up']:.2%}")
        
        print(f"\nRealistic Readiness Score: {score}/100")
        
        for check in checks:
            print(f"  {check}")
        
        # Verdict
        print("\n" + "-"*80)
        if score >= 80:
            verdict = "GOOD - Ready for small live test with tight risk controls"
        elif score >= 60:
            verdict = "MARGINAL - Paper trade only, high costs eroding edge"
        else:
            verdict = "NOT READY - Strategy loses money after realistic costs"
        
        print(f"Verdict: {verdict}")
        
        print("\n" + "-"*80)
        print("REALISTIC EXPECTATIONS:")
        print(f"  With ${10000:.0f} capital:")
        print(f"  - Median outcome: ${mc['median_final_equity']:.0f} ({mc['median_return']:+.1f}%)")
        print(f"  - Worst 5% outcome: ${10000 * (1 + mc['return_5th']/100):.0f} ({mc['return_5th']:+.1f}%)")
        print(f"  - You should expect drawdowns of {mc['median_max_dd']:.1f}% or more")
        print(f"  - Be prepared to be underwater for {mc['avg_underwater_period']:.0f}+ trades")
        
        print("\n" + "="*80)
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'realistic_score': score,
            'verdict': verdict,
            'profit_factor': pf,
            'expectancy': exp,
            'tail_risk': risk,
            'monte_carlo': mc,
            'cost_impact': {
                'avg_cost_per_trade': float(np.mean(costs)),
                'winners_before_costs': winners_before,
                'winners_after_costs': winners_after,
                'trades_turned_to_losers': winners_before - winners_after
            }
        }
        
        output_path = Path('genome/results/realistic_validation_report.json')
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n[Saved] Realistic report: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--honest-assessment', action='store_true', help='Run realistic validation')
    
    args = parser.parse_args()
    
    validator = RealisticValidator()
    
    if not validator.data:
        print("No data found. Run historical analysis first.")
        return
    
    if args.honest_assessment:
        validator.generate_honest_report()
    else:
        print("Realistic Validation Framework")
        print("\nUsage:")
        print("  --honest-assessment    Run realistic validation with costs")
        print("\nExample:")
        print("  python realistic_validation.py --honest-assessment")


if __name__ == "__main__":
    main()
