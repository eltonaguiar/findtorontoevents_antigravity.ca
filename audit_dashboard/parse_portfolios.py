#!/usr/bin/env python3
import json
import os

def main():
    dashboard_file = os.path.join(os.path.dirname(__file__), "data", "claudes_test_dashboard.json")
    
    try:
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print('=== Portfolio Performance Comparison ===')
        print('Generated:', data['generated_at'])
        print('Market Regime:', data['regime'])
        print('')
        
        # Extract and print portfolio details
        for portfolio in data['portfolios']:
            portfolio_id = portfolio['id']
            name = portfolio['name']
            methodology = portfolio['methodology']
            status = portfolio['status']
            
            # Get key metrics
            stats = portfolio['stats']
            pnl_pct = stats['pnl_pct']
            pnl_usd = stats['pnl_usd']
            win_rate = stats['win_rate']
            total_trades = stats['total_trades']
            sharpe = stats['sharpe']
            max_drawdown = stats['max_drawdown_pct']
            profit_factor = stats['profit_factor']
            open_positions = stats['open_positions']
            
            print(f'Portfolio: {name} ({portfolio_id})')
            print(f'  Methodology: {methodology}')
            print(f'  Status: {status}')
            print(f'  PnL: {pnl_pct:.2f}% (${pnl_usd:.2f})')
            print(f'  Win Rate: {win_rate:.1f}% ({total_trades} trades)')
            print(f'  Sharpe Ratio: {sharpe:.2f}')
            print(f'  Max Drawdown: {max_drawdown:.2f}%')
            print(f'  Profit Factor: {profit_factor:.2f}')
            print(f'  Open Positions: {open_positions}')
            print('-' * 60)
            
    except Exception as e:
        print(f"Error reading or parsing dashboard file: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
