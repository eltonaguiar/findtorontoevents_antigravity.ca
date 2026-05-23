import json
import os

# Load the integrity report data
with open('audit_dashboard/data/integrity_report.json', 'r', encoding='utf-8') as f:
    integrity_data = json.load(f)

# Define non-crypto portfolio names (excluding crypto-specific ones)
non_crypto_portfolios = {
    'stocks_best', 'stocks_short_term', 'forex_carry',
    'multi_asset_diversified', 'prop_aggressive', 'prop_conservative',
    'prop_swing', 'proven_only', 'relative_strength_recovery',
    'rr_kings', 'rsi_capitulation', 'score_leaders', 'sector_rotation'
}

# Filter portfolios
filtered_portfolios = [p for p in integrity_data['portfolios'] if p['portfolio'] in non_crypto_portfolios]

# Helper to calculate unrealized P&L (assuming initial capital of $10,000)
def calculate_unrealized_pnl(equity):
    initial_capital = 10000.0
    return equity - initial_capital

# Generate markdown content
markdown_content = """# Non-Crypto Asset Performance History Review (2026-03-11)

## Executive Summary
This document provides a detailed review of the forward-facing performance of all non-crypto portfolios as of **March 11, 2026**. The data is extracted from the latest integrity report (`integrity_report.json`) and includes key metrics such as equity, P&L percentage, open positions, closed trades, and unrealized profit/loss.

## Performance Overview Table
"""

# Table header
markdown_content += """| Portfolio | Equity (USD) | P&L % | Open Positions | Closed Trades | Wins | Losses | Unrealized P&L (USD) | Realized P&L (USD) | Sharpe | Sortino |
|-----------|--------------|-------|----------------|---------------|------|--------|----------------------|--------------------|--------|---------|
"""

# Table rows
for portfolio in filtered_portfolios:
    equity = portfolio['equity']
    pnl_pct = portfolio['pnl_pct'] * 100
    open_positions = portfolio['open_positions']
    closed_trades = portfolio['closed_trades']
    wins = portfolio['wins']
    losses = portfolio['losses']
    unrealized_pnl = calculate_unrealized_pnl(equity)
    realized_pnl = 0.0  # Not recorded in current snapshot
    sharpe = 0.0  # Not calculated in current report
    sortino = 0.0  # Not calculated in current report
    
    # Handle large equity values for prop portfolios
    equity_str = f"{equity:,.2f}"
    unrealized_pnl_str = f"{unrealized_pnl:,.2f}"
    
    markdown_content += (
        f"| {portfolio['portfolio']} | {equity_str} | {pnl_pct:+.2f}% | {open_positions} | {closed_trades} | {wins} | {losses} | {unrealized_pnl_str} | {realized_pnl:,.2f} | {sharpe:.2f} | {sortino:.2f} |\n"
    )

# Add methodology section
markdown_content += """
## Methodology
- **Equity Calculation**: All equity values are based on an assumed initial capital of **$10,000** for standard portfolios. Proprietary (prop) portfolios have larger initial capital bases.
- **Unrealized P&L**: Represents the profit/loss on currently open positions