"""
Test Portfolio Tracker — Runs hourly to validate Battleground strategies in real-time.
Tracks 4 portfolio approaches and determines which is most optimal.

Portfolios:
  A: Keltner-Only (BTC+ETH+SOL) — conservative
  B: Keltner+RSI Confluence — balanced
  C: Full Battleground (all 9 strategies) — aggressive
  D: Best Per-Trade (DD Recovery BTC + Keltner BTC) — cherry pick
  E: HRP-Weighted — risk parity allocation
  F: Walk-Forward Survivors Only — OOS-validated strategies, BTC-heavy

Each portfolio starts with $1000 and simulates Quarter-Kelly sizing.
"""
import json
import os
from datetime import datetime, timezone
from collections import defaultdict

try:
    from battleground.hrp_allocation import compute_hrp_weights
except ImportError:
    try:
        from hrp_allocation import compute_hrp_weights
    except ImportError:
        compute_hrp_weights = None

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "test_portfolios.json")

# Strategy groupings for each portfolio
PORTFOLIOS = {
    "A_keltner_only": {
        "name": "Portfolio A: Keltner-Only",
        "strategies": [
            "crypto_keltner_compression_expansion_v1",
            "keltner_compression_expansion_eth_v1",
            "keltner_compression_expansion_sol_v1",
        ],
        "description": "Only statistically proven Keltner strategies (p<0.05)",
    },
    "B_keltner_rsi": {
        "name": "Portfolio B: Keltner + RSI",
        "strategies": [
            "crypto_keltner_compression_expansion_v1",
            "keltner_compression_expansion_eth_v1",
            "keltner_compression_expansion_sol_v1",
            "keltner_compression_expansion_xrp_v1",
            "multi_period_rsi_confluence_eth",
            "multi_period_rsi_confluence_xrp",
        ],
        "description": "Keltner + RSI Confluence for balanced LONG/SHORT",
    },
    "C_full_battleground": {
        "name": "Portfolio C: Full Battleground",
        "strategies": [
            "crypto_keltner_compression_expansion_v1",
            "keltner_compression_expansion_eth_v1",
            "keltner_compression_expansion_sol_v1",
            "keltner_compression_expansion_xrp_v1",
            "drawdown_recovery_rsi",
            "drawdown_recovery_rsi_eth",
            "multi_period_rsi_confluence_eth",
            "multi_period_rsi_confluence_xrp",
            "crypto_drawdown_convexity_recovery_v1",
        ],
        "description": "All 9 profitable Battleground strategies",
    },
    "D_best_per_trade": {
        "name": "Portfolio D: Best Per-Trade",
        "strategies": [
            "drawdown_recovery_rsi",
            "crypto_keltner_compression_expansion_v1",
        ],
        "description": "DD Recovery BTC (best R:R) + Keltner BTC (best WR)",
    },
    "E_hrp_weighted": {
        "name": "Portfolio E: HRP-Weighted",
        "strategies": [
            "crypto_keltner_compression_expansion_v1",
            "keltner_compression_expansion_eth_v1",
            "keltner_compression_expansion_sol_v1",
            "keltner_compression_expansion_xrp_v1",
            "drawdown_recovery_rsi",
            "drawdown_recovery_rsi_eth",
            "multi_period_rsi_confluence_eth",
            "multi_period_rsi_confluence_xrp",
            "crypto_drawdown_convexity_recovery_v1",
        ],
        "description": "Hierarchical Risk Parity allocation — auto-reduces correlated exposure",
    },
    "F_walkforward_survivors": {
        "name": "Portfolio F: Walk-Forward Survivors Only",
        "strategies": [
            "crypto_keltner_compression_expansion_v1",  # BTC 75% WR OOS, p=0.002
            "keltner_compression_expansion_sol_v1",      # SOL 62.1% WR OOS
            "multi_period_rsi_confluence_eth",            # ETH 64.3% WR OOS
            "multi_period_rsi_confluence_xrp",            # XRP 83.3% WR OOS (n=6)
        ],
        "weights": {
            "crypto_keltner_compression_expansion_v1": 0.35,  # strongest stat sig
            "keltner_compression_expansion_sol_v1": 0.20,
            "multi_period_rsi_confluence_eth": 0.25,
            "multi_period_rsi_confluence_xrp": 0.20,
        },
        "description": "Only strategies that passed walk-forward OOS validation (BTC-heavy, p<0.05)",
    },
}

INITIAL_CAPITAL = 1000.0
POSITION_SIZE_PCT = 0.05  # 5% of capital per trade (Quarter-Kelly)
MAX_POSITIONS = 5


def load_portfolios():
    """Load existing portfolio state or initialize fresh."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    
    # Initialize fresh portfolios
    state = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
        "portfolios": {},
    }
    for pid, config in PORTFOLIOS.items():
        state["portfolios"][pid] = {
            "name": config["name"],
            "description": config["description"],
            "strategies": config["strategies"],
            "capital": INITIAL_CAPITAL,
            "peak_capital": INITIAL_CAPITAL,
            "trades_taken": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "active_positions": [],
            "closed_trades": [],
            "daily_pnl": [],
            "hourly_snapshots": [],
        }
    return state


def ensure_new_portfolios(state):
    """Add any newly defined portfolios that don't exist in saved state."""
    for pid, config in PORTFOLIOS.items():
        if pid not in state["portfolios"]:
            state["portfolios"][pid] = {
                "name": config["name"],
                "description": config["description"],
                "strategies": config["strategies"],
                "capital": INITIAL_CAPITAL,
                "peak_capital": INITIAL_CAPITAL,
                "trades_taken": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "active_positions": [],
                "closed_trades": [],
                "daily_pnl": [],
                "hourly_snapshots": [],
            }
    return state


def load_battleground_data():
    """Load current active and closed picks from Battleground."""
    active_file = os.path.join(BASE, "data", "active_picks.json")
    closed_file = os.path.join(BASE, "data", "closed_picks.json")
    
    active = []
    closed = []
    
    if os.path.exists(active_file):
        with open(active_file, "r") as f:
            active = json.load(f)
    
    if os.path.exists(closed_file):
        with open(closed_file, "r") as f:
            closed = json.load(f)
    
    return active, closed


def update_portfolios():
    """Main update loop — run this hourly."""
    state = load_portfolios()
    state = ensure_new_portfolios(state)
    active_picks, closed_picks = load_battleground_data()
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    # Build lookup of closed picks by key
    closed_lookup = {}
    for p in closed_picks:
        key = f"{p.get('symbol','')}_{p.get('strategy','')}_{p.get('direction','')}"
        closed_lookup[key] = p
    
    # Build set of currently active pick keys
    active_keys = set()
    for p in active_picks:
        key = f"{p.get('symbol','')}_{p.get('strategy','')}_{p.get('direction','')}"
        active_keys.add(key)
    
    for pid, portfolio in state["portfolios"].items():
        config = PORTFOLIOS.get(pid, {})
        allowed_strategies = set(config.get("strategies", []))
        
        # 1. Check for closed positions
        still_active = []
        for pos in portfolio["active_positions"]:
            trade_key = f"{pos['symbol']}_{pos['strategy']}_{pos['direction']}"
            
            if trade_key not in active_keys:
                # Position was closed
                closed_match = closed_lookup.get(trade_key)
                pnl_pct = 0.0
                exit_reason = "UNKNOWN"
                
                if closed_match:
                    pnl_pct = float(closed_match.get("pnl_pct", 0) or 0)
                    exit_reason = closed_match.get("exit_reason", "UNKNOWN")

                # Determine position size — HRP for E, walk-forward weights for F, flat for others
                if pid == "E_hrp_weighted" and compute_hrp_weights is not None:
                    hrp_weights = compute_hrp_weights(
                        config.get("strategies", []),
                        total_risk_budget=POSITION_SIZE_PCT * len(config.get("strategies", []))
                    )
                    pos_size_pct = hrp_weights.get(pos["strategy"], POSITION_SIZE_PCT)
                    # Cap at 3x equal-weight
                    pos_size_pct = min(pos_size_pct, POSITION_SIZE_PCT * 3)
                elif pid == "F_walkforward_survivors" and "weights" in config:
                    wf_weights = config["weights"]
                    pos_size_pct = POSITION_SIZE_PCT * (wf_weights.get(pos["strategy"], 0.25) / 0.25)
                    pos_size_pct = min(pos_size_pct, POSITION_SIZE_PCT * 3)
                else:
                    pos_size_pct = POSITION_SIZE_PCT

                # Update portfolio capital
                trade_pnl = portfolio["capital"] * pos_size_pct * (pnl_pct / 100)
                portfolio["capital"] += trade_pnl
                portfolio["total_pnl_pct"] += pnl_pct
                portfolio["trades_taken"] += 1
                
                if pnl_pct > 0:
                    portfolio["wins"] += 1
                else:
                    portfolio["losses"] += 1
                
                # Track peak and drawdown
                if portfolio["capital"] > portfolio["peak_capital"]:
                    portfolio["peak_capital"] = portfolio["capital"]
                dd = (portfolio["peak_capital"] - portfolio["capital"]) / portfolio["peak_capital"] * 100
                if dd > portfolio["max_drawdown_pct"]:
                    portfolio["max_drawdown_pct"] = round(dd, 4)
                
                portfolio["closed_trades"].append({
                    "symbol": pos["symbol"],
                    "strategy": pos["strategy"],
                    "direction": pos["direction"],
                    "pnl_pct": round(pnl_pct, 4),
                    "exit_reason": exit_reason,
                    "opened_at": pos.get("opened_at", ""),
                    "closed_at": now_str,
                    "capital_after": round(portfolio["capital"], 2),
                })
            else:
                still_active.append(pos)
        
        portfolio["active_positions"] = still_active
        
        # 2. Add new positions from active picks
        current_tracking = {
            f"{pos['symbol']}_{pos['strategy']}_{pos['direction']}"
            for pos in portfolio["active_positions"]
        }
        
        for pick in active_picks:
            strat = pick.get("strategy", "")
            if strat not in allowed_strategies:
                continue
            
            pick_key = f"{pick.get('symbol','')}_{strat}_{pick.get('direction','')}"
            if pick_key in current_tracking:
                continue
            
            if len(portfolio["active_positions"]) >= MAX_POSITIONS:
                continue
            
            # Correlation check: max 2 positions per symbol
            sym = pick.get("symbol", "")
            sym_count = sum(1 for p in portfolio["active_positions"] if p["symbol"] == sym)
            if sym_count >= 2:
                continue
            
            portfolio["active_positions"].append({
                "symbol": sym,
                "strategy": strat,
                "direction": pick.get("direction", ""),
                "entry_price": pick.get("entry_price", 0),
                "take_profit": pick.get("take_profit", 0),
                "stop_loss": pick.get("stop_loss", 0),
                "confidence": pick.get("confidence", 0),
                "opened_at": now_str,
            })
            current_tracking.add(pick_key)
        
        # 3. Hourly snapshot
        portfolio["hourly_snapshots"].append({
            "time": now_str,
            "capital": round(portfolio["capital"], 2),
            "active_count": len(portfolio["active_positions"]),
            "trades_total": portfolio["trades_taken"],
        })
        
        # Keep last 168 snapshots (1 week of hourly)
        if len(portfolio["hourly_snapshots"]) > 168:
            portfolio["hourly_snapshots"] = portfolio["hourly_snapshots"][-168:]
        
        # Keep last 200 closed trades
        if len(portfolio["closed_trades"]) > 200:
            portfolio["closed_trades"] = portfolio["closed_trades"][-200:]
        
        # Round capital
        portfolio["capital"] = round(portfolio["capital"], 2)
    
    state["last_updated"] = now_str
    
    # Save state
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"  TEST PORTFOLIO UPDATE — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*80}\n")
    
    for pid, portfolio in sorted(state["portfolios"].items()):
        n = portfolio["trades_taken"]
        wr = portfolio["wins"] / n * 100 if n > 0 else 0
        roi = (portfolio["capital"] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        active_n = len(portfolio["active_positions"])
        
        emoji = "+" if roi > 0 else ""
        
        print(f"  {portfolio['name']}")
        print(f"    Capital: ${portfolio['capital']:.2f} ({emoji}{roi:.2f}% ROI)")
        print(f"    Trades: {n} ({portfolio['wins']}W/{portfolio['losses']}L, {wr:.1f}% WR)")
        print(f"    Max DD: {portfolio['max_drawdown_pct']:.2f}%")
        print(f"    Active: {active_n} positions | Strategies: {len(portfolio['strategies'])}")
        print()
    
    # Determine leader
    leaders = sorted(state["portfolios"].items(), key=lambda x: x[1]["capital"], reverse=True)
    best_pid, best = leaders[0]
    best_roi = (best["capital"] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print(f"  LEADER: {best['name']} (${best['capital']:.2f}, {best_roi:+.2f}% ROI)")
    print(f"{'='*80}\n")
    
    return state


if __name__ == "__main__":
    update_portfolios()
