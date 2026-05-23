#!/usr/bin/env python3
import json
import os

def main():
    dashboard_file = os.path.join(os.path.dirname(__file__), "data", "claudes_test_dashboard.json")
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract portfolios by methodology
    score_portfolios = []
    confidence_portfolios = []
    proven_portfolios = []
    other_portfolios = []
    
    for portfolio in data['portfolios']:
        methodology = portfolio['methodology']
        if methodology == 'score':
            score_portfolios.append(portfolio)
        elif methodology == 'conviction':
            confidence_portfolios.append(portfolio)
        elif methodology == 'proven':
            proven_portfolios.append(portfolio)
        else:
            other_portfolios.append(portfolio)
    
    # Calculate aggregate metrics
    def calculate_aggregates(portfolios, label):
        if not portfolios:
            return None
        
        total_pnl = 0
        total_trades = 0
        total_wins = 0
        total_profit = 0
        total_loss = 0
        total_equity = 0
        
        for p in portfolios:
            stats = p['stats']
            total_pnl += stats['pnl_usd']
            total_trades += stats['total_trades']
            total_equity += p['equity']
            
            # Calculate wins/losses from closed trades
            closed = p.get('recent_closed', [])
            for trade in closed:
                net_pnl = trade['net_pnl_usd']
                if net_pnl > 0:
                    total_wins += 1
                    total_profit += net_pnl
                elif net_pnl < 0:
                    total_loss += abs(net_pnl)
        
        avg_pnl = total_pnl / len(portfolios)
        win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'count': len(portfolios),
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_equity': total_equity
        }
    
    score_agg = calculate_aggregates(score_portfolios, 'score')
    confidence_agg = calculate_aggregates(confidence_portfolios, 'conviction')
    proven_agg = calculate_aggregates(proven_portfolios, 'proven')
    
    print('=== Methodology Performance Comparison ===')
    print('Generated:', data['generated_at'])
    print('Market Regime:', data['regime'])
    print('')
    
    # Display results
    print(f"{'Metric':30s} {'Score':15s} {'Confidence':15s} {'Proven':15s}")
    print('-' * 80)
    
    # Portfolio Count
    print(f"{'Number of Portfolios':30s} {score_agg['count']:>15} {confidence_agg['count']:>15} {proven_agg['count']:>15}")
    
    # Total PnL
    print(f"{'Total PnL ($)':30s} {score_agg['total_pnl']:>14.2f} {confidence_agg['total_pnl']:>14.2f} {proven_agg['total_pnl']:>14.2f}")
    
    # Average PnL per Portfolio
    print(f"{'Avg PnL per Portfolio ($)':30s} {score_agg['avg_pnl']:>14.2f} {confidence_agg['avg_pnl']:>14.2f} {proven_agg['avg_pnl']:>14.2f}")
    
    # Total Trades
    print(f"{'Total Trades':30s} {score_agg['total_trades']:>15} {confidence_agg['total_trades']:>15} {proven_agg['total_trades']:>15}")
    
    # Win Rate
    print(f"{'Win Rate (%)':30s} {score_agg['win_rate']:>14.1f} {confidence_agg['win_rate']:>14.1f} {proven_agg['win_rate']:>14.1f}")
    
    # Profit Factor
    print(f"{'Profit Factor':30s} {score_agg['profit_factor']:>14.2f} {confidence_agg['profit_factor']:>14.2f} {proven_agg['profit_factor']:>14.2f}")
    
    print('')
    print('=== Detailed Portfolio Breakdown ===')
    print('')
    
    # Score-based portfolios
    print('Score-based Portfolios:')
    for p in score_portfolios:
        print(f"  {p['name']:30s} {p['stats']['pnl_pct']:>8.2f}%  ${p['stats']['pnl_usd']:>9.2f}  {p['stats']['total_trades']:>3} trades")
    
    print('')
    
    # Confidence-based portfolios
    print('Confidence-based Portfolios:')
    for p in confidence_portfolios:
        print(f"  {p['name']:30s} {p['stats']['pnl_pct']:>8.2f}%  ${p['stats']['pnl_usd']:>9.2f}  {p['stats']['total_trades']:>3} trades")
    
    print('')
    
    # Proven-only portfolios
    print('Proven-only Portfolios:')
    for p in proven_portfolios:
        print(f"  {p['name']:30s} {p['stats']['pnl_pct']:>8.2f}%  ${p['stats']['pnl_usd']:>9.2f}  {p['stats']['total_trades']:>3} trades")
    
    print('')
    print('=== Portfolio Performance Rankings ===')
    print('')
    
    # Rank all portfolios by PnL
    all_portfolios = score_portfolios + confidence_portfolios + proven_portfolios
    all_portfolios.sort(key=lambda x: x['stats']['pnl_pct'], reverse=True)
    
    print('Top Performers:')
    for i, p in enumerate(all_portfolios[:5], 1):
        print(f"{i:2d}. {p['name']:30s} {p['methodology']:10s} {p['stats']['pnl_pct']:>8.2f}%  ${p['stats']['pnl_usd']:>9.2f}")
    
    print('')
    
    print('Bottom Performers:')
    for i, p in enumerate(all_portfolios[-5:], 1):
        print(f"{i:2d}. {p['name']:30s} {p['methodology']:10s} {p['stats']['pnl_pct']:>8.2f}%  ${p['stats']['pnl_usd']:>9.2f}")

if __name__ == "__main__":
    main()
