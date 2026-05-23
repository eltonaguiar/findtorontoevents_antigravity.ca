#!/usr/bin/env python3
"""Build the dashboard HTML with current portfolio data injected."""
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

# Read portfolio
portfolio_file = DATA_DIR / "paper_portfolio.json"
with open(portfolio_file) as f:
    portfolio = json.load(f)

# Get current prices for open positions
import yfinance as yf
import pandas as pd

for pos in portfolio["positions"]:
    if pos["status"] == "OPEN":
        df = yf.download(pos["symbol"], period="5d", interval="1d", auto_adjust=True, progress=False)
        if not df.empty:
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            pos["current_price"] = float(close.iloc[-1])
        else:
            pos["current_price"] = pos["entry_price"]

# Read template
template_file = SCRIPT_DIR / "dashboard.html"
with open(template_file, encoding="utf-8") as f:
    html = f.read()

# Inject data
portfolio_json = json.dumps(portfolio, indent=2, default=str)
html = html.replace("PORTFOLIO_DATA_PLACEHOLDER", portfolio_json)

# Write built dashboard
output_file = SCRIPT_DIR / "dashboard_live.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dashboard built: {output_file}")
print(f"Positions: {len(portfolio['positions'])} open, {len(portfolio.get('closed_positions',[]))} closed")

# Also compute P&L summary
total_pnl = 0
for pos in portfolio["positions"]:
    cp = pos.get("current_price", pos["entry_price"])
    pnl = (cp - pos["entry_price"]) / pos["entry_price"] * 100
    dollar_pnl = pos["invested"] * pnl / 100
    total_pnl += dollar_pnl
    print(f"  {pos['symbol']:<12} Entry: ${pos['entry_price']:>10,.4f}  Current: ${cp:>10,.4f}  P&L: {pnl:+.2f}%  ${dollar_pnl:+.2f}")

print(f"\n  TOTAL P&L: ${total_pnl:+,.2f} on ${portfolio['starting_capital']:,}")
