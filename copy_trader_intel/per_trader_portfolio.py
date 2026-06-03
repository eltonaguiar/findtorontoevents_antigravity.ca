#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): exit prices/WR here come from single
daily-snapshot marks (no intrabar OHLC path) and inherit upstream copy-trader resolution,
so WR/PF is inflated. Do not size up. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Per-Trader Portfolio Simulation
================================
Loads qualified traders and their active picks, then simulates a $500 portfolio
for each trader. Tracks open/closed trades, win rate, PnL, and max drawdown
using live Binance prices with a 3-endpoint failover chain.

Output: data/per_trader_portfolios.json
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

STARTING_CAPITAL = 500.0

# Binance API failover chain (CRITICAL: never use single endpoint)
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision",
    "https://api.binance.us",
    "https://api.binance.com",
]

# ---------- Price Fetching with Failover ----------

def get_binance_price(symbol):
    """Fetch current price from Binance with 3-endpoint failover chain."""
    for endpoint in BINANCE_ENDPOINTS:
        try:
            url = f"{endpoint}/api/v3/ticker/price?symbol={symbol}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return float(data.get("price", 0))
        except Exception:
            continue
    return None


def normalize_symbol_for_binance(symbol):
    """Convert pick symbol to Binance ticker format."""
    s = symbol.upper().replace("-", "").replace("/", "")
    # Already has USDT suffix
    if s.endswith("USDT"):
        return s
    # Add USDT if it looks like a crypto symbol
    if not s.endswith("USD"):
        return s + "USDT"
    # Convert xxxUSD -> xxxUSDT
    return s + "T"


def fetch_prices_batch(symbols):
    """Fetch prices for a list of symbols. Returns {symbol: price}."""
    prices = {}
    for sym in symbols:
        binance_sym = normalize_symbol_for_binance(sym)
        price = get_binance_price(binance_sym)
        if price and price > 0:
            prices[sym] = price
        time.sleep(0.1)  # rate limit
    return prices


# ---------- Portfolio State Management ----------

def load_previous_state():
    """Load the previous portfolio state for detecting closed positions."""
    state_path = DATA_DIR / "per_trader_portfolios.json"
    if state_path.exists():
        try:
            with open(state_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def get_trader_strategy_name(trader):
    """Build the strategy name that matches active_picks format."""
    label = trader.get("label", "")
    return f"copy_hl_{label}"


# ---------- Core Simulation ----------

def simulate_portfolios():
    """Run per-trader portfolio simulation."""
    print("=" * 70)
    print("  PER-TRADER PORTFOLIO SIMULATION")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Starting capital per trader: ${STARTING_CAPITAL:.0f}")
    print("=" * 70)

    # Load qualified traders
    qt_path = DATA_DIR / "qualified_traders.json"
    if not qt_path.exists():
        print("  [ERROR] No qualified_traders.json found")
        return

    with open(qt_path) as f:
        qt_data = json.load(f)
    traders = qt_data.get("traders", [])
    print(f"  Qualified traders: {len(traders)}")

    # Load active picks
    picks_path = DATA_DIR / "active_picks.json"
    if not picks_path.exists():
        print("  [ERROR] No active_picks.json found")
        return

    with open(picks_path) as f:
        all_picks = json.load(f)
    if isinstance(all_picks, dict):
        all_picks = all_picks.get("picks", [])
    print(f"  Total active picks: {len(all_picks)}")

    # Group picks by trader strategy name
    picks_by_trader = defaultdict(list)
    for pick in all_picks:
        strategy = pick.get("strategy", "")
        if strategy.startswith("copy_hl_"):
            picks_by_trader[strategy].append(pick)

    # Load previous state for tracking closed trades
    prev_state = load_previous_state()
    prev_portfolios = {}
    if prev_state and "portfolios" in prev_state:
        for p in prev_state["portfolios"]:
            prev_portfolios[p["trader_address"]] = p

    # Collect all unique symbols we need prices for
    all_symbols = set()
    for picks in picks_by_trader.values():
        for pick in picks:
            sym = pick.get("symbol", "")
            if sym:
                all_symbols.add(sym)

    # Also add symbols from previous open trades
    for prev_p in prev_portfolios.values():
        for t in prev_p.get("open_trades", []):
            sym = t.get("symbol", "")
            if sym:
                all_symbols.add(sym)

    print(f"  Fetching prices for {len(all_symbols)} symbols...")
    live_prices = fetch_prices_batch(all_symbols)
    print(f"  Got prices for {len(live_prices)} symbols")

    # Build portfolio for each trader
    portfolios = []

    for trader in traders:
        addr = trader["address"]
        label = trader.get("label", addr[:10])
        strategy_name = get_trader_strategy_name(trader)
        trader_picks = picks_by_trader.get(strategy_name, [])

        # Get previous portfolio state
        prev_p = prev_portfolios.get(addr, {})
        prev_open_ids = {t["pick_id"] for t in prev_p.get("open_trades", [])}
        prev_closed = prev_p.get("closed_trades", [])
        prev_capital = prev_p.get("current_capital", STARTING_CAPITAL)

        # Current open pick IDs
        current_open_ids = {p.get("id", "") for p in trader_picks if p.get("status") == "OPEN"}

        # Detect closed trades: picks that were open before but are gone now
        newly_closed = []
        for prev_trade in prev_p.get("open_trades", []):
            pid = prev_trade.get("pick_id", "")
            if pid and pid not in current_open_ids:
                # This position disappeared -- it was closed
                sym = prev_trade.get("symbol", "")
                entry_px = prev_trade.get("entry_price", 0)
                direction = prev_trade.get("direction", "LONG")
                alloc = prev_trade.get("allocation", 0)
                exit_px = live_prices.get(sym, entry_px)

                if entry_px > 0:
                    if direction == "LONG":
                        pnl_pct = (exit_px - entry_px) / entry_px * 100
                    else:
                        pnl_pct = (entry_px - exit_px) / entry_px * 100
                    pnl_dollar = alloc * (pnl_pct / 100)
                else:
                    pnl_pct = 0
                    pnl_dollar = 0

                newly_closed.append({
                    "pick_id": pid,
                    "symbol": sym,
                    "direction": direction,
                    "entry_price": entry_px,
                    "exit_price": round(exit_px, 6),
                    "allocation": round(alloc, 2),
                    "pnl_pct": round(pnl_pct, 4),
                    "pnl_dollar": round(pnl_dollar, 2),
                    "is_win": pnl_pct > 0,
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                })

        # Merge with historical closed trades
        all_closed = prev_closed + newly_closed

        # Build open trade snapshots
        open_trades = []
        for pick in trader_picks:
            if pick.get("status") != "OPEN":
                continue
            sym = pick.get("symbol", "")
            entry_px = pick.get("entry_price", 0)
            direction = pick.get("direction", "LONG")
            alloc = pick.get("allocation", 0)
            current_px = live_prices.get(sym)

            unrealized_pnl_pct = 0
            unrealized_pnl_dollar = 0
            if current_px and entry_px > 0:
                if direction == "LONG":
                    unrealized_pnl_pct = (current_px - entry_px) / entry_px * 100
                else:
                    unrealized_pnl_pct = (entry_px - current_px) / entry_px * 100
                unrealized_pnl_dollar = alloc * (unrealized_pnl_pct / 100)

            open_trades.append({
                "pick_id": pick.get("id", ""),
                "symbol": sym,
                "direction": direction,
                "entry_price": entry_px,
                "current_price": current_px or entry_px,
                "allocation": round(alloc, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
                "unrealized_pnl_dollar": round(unrealized_pnl_dollar, 2),
                "entry_date": pick.get("entry_date", ""),
                "take_profit": pick.get("take_profit"),
                "stop_loss": pick.get("stop_loss"),
            })

        # Calculate portfolio stats
        realized_pnl = sum(t["pnl_dollar"] for t in all_closed)
        unrealized_pnl = sum(t["unrealized_pnl_dollar"] for t in open_trades)
        current_capital = STARTING_CAPITAL + realized_pnl
        total_equity = current_capital + unrealized_pnl

        # Win rate from closed trades
        wins = sum(1 for t in all_closed if t.get("is_win"))
        total_closed = len(all_closed)
        win_rate = wins / total_closed if total_closed > 0 else 0

        # Max drawdown calculation
        # Track equity curve through closed trades
        equity_curve = [STARTING_CAPITAL]
        running = STARTING_CAPITAL
        for t in all_closed:
            running += t.get("pnl_dollar", 0)
            equity_curve.append(running)

        peak = STARTING_CAPITAL
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Profit factor
        gross_profit = sum(t["pnl_dollar"] for t in all_closed if t.get("pnl_dollar", 0) > 0)
        gross_loss = abs(sum(t["pnl_dollar"] for t in all_closed if t.get("pnl_dollar", 0) < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99

        portfolio = {
            "trader_address": addr,
            "trader_label": label,
            "strategy_name": strategy_name,
            "starting_capital": STARTING_CAPITAL,
            "current_capital": round(current_capital, 2),
            "total_equity": round(total_equity, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl_pct": round((total_equity - STARTING_CAPITAL) / STARTING_CAPITAL * 100, 2),
            "open_trade_count": len(open_trades),
            "closed_trade_count": total_closed,
            "win_rate": round(win_rate, 4),
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_dd, 2),
            "open_trades": open_trades,
            "closed_trades": all_closed[-50:],  # Keep last 50 closed trades
            "trader_edge_score": trader.get("edge_score", 0),
            "trader_account_value": trader.get("account_value", 0),
            "trader_total_pnl": trader.get("total_realized_pnl", 0),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        portfolios.append(portfolio)

        # Print summary
        status_tag = "[OK]" if total_equity >= STARTING_CAPITAL else "[WARN]"
        print(f"\n  {status_tag} {label:25s} | Capital: ${total_equity:>10.2f} | "
              f"Open: {len(open_trades):2d} | Closed: {total_closed:3d} | "
              f"WR: {win_rate*100:5.1f}% | PnL: ${realized_pnl:>8.2f}")

    # Sort by total equity descending
    portfolios.sort(key=lambda p: p["total_equity"], reverse=True)

    # Save output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "starting_capital_per_trader": STARTING_CAPITAL,
        "total_traders": len(portfolios),
        "summary": {
            "total_capital_deployed": round(STARTING_CAPITAL * len(portfolios), 2),
            "total_equity": round(sum(p["total_equity"] for p in portfolios), 2),
            "total_realized_pnl": round(sum(p["realized_pnl"] for p in portfolios), 2),
            "total_unrealized_pnl": round(sum(p["unrealized_pnl"] for p in portfolios), 2),
            "avg_win_rate": round(
                sum(p["win_rate"] for p in portfolios if p["closed_trade_count"] > 0) /
                max(sum(1 for p in portfolios if p["closed_trade_count"] > 0), 1), 4
            ),
            "best_trader": portfolios[0]["trader_label"] if portfolios else "",
            "worst_trader": portfolios[-1]["trader_label"] if portfolios else "",
        },
        "portfolios": portfolios,
    }

    out_path = DATA_DIR / "per_trader_portfolios.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"  PORTFOLIO SUMMARY")
    print(f"  Total capital: ${output['summary']['total_capital_deployed']:.0f}")
    print(f"  Total equity:  ${output['summary']['total_equity']:.2f}")
    print(f"  Realized PnL:  ${output['summary']['total_realized_pnl']:.2f}")
    print(f"  Unrealized:    ${output['summary']['total_unrealized_pnl']:.2f}")
    print(f"  Saved to {out_path}")
    print(f"{'='*70}\n")

    return output


if __name__ == "__main__":
    simulate_portfolios()
