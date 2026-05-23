"""Full portfolio reset — wipe all positions, start clean."""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

STATE_FILE = Path("audit_dashboard/data/claudes_test_state.json")
now = datetime.now(timezone(timedelta(hours=-5)))

# Load old state to count what we're wiping
with open(STATE_FILE) as f:
    old_state = json.load(f)

total_pos = sum(len(p.get("positions", [])) for p in old_state.values() if isinstance(p, dict))
total_closed = sum(len(p.get("closed_trades", p.get("closed", [])) or []) for p in old_state.values() if isinstance(p, dict))
print(f"Wiping: {total_pos} open positions, {total_closed} closed trades across {len(old_state)} portfolios")

# Portfolio definitions
PORTFOLIOS = [
    {"id": "score_leaders", "name": "Score Leaders", "desc": "Top picks by composite quality score", "cap": 10000, "max": 8, "pct": 0.10, "method": "score", "interval": 30},
    {"id": "proven_only", "name": "Proven Only", "desc": "Systems with WR >= 50% and 10+ closed trades", "cap": 10000, "max": 6, "pct": 0.15, "method": "proven", "interval": 30},
    {"id": "momentum_riders", "name": "Momentum Riders", "desc": "Chase 24h momentum", "cap": 10000, "max": 10, "pct": 0.10, "method": "momentum", "interval": 30},
    {"id": "contrarian", "name": "Contrarian", "desc": "Trade against the crowd", "cap": 10000, "max": 6, "pct": 0.15, "method": "contrarian", "interval": 30},
    {"id": "regime_aligned", "name": "Regime Aligned", "desc": "Trade with the macro regime", "cap": 10000, "max": 6, "pct": 0.15, "method": "regime", "interval": 30},
    {"id": "high_conviction", "name": "High Conviction", "desc": "High confidence picks with good R:R", "cap": 10000, "max": 5, "pct": 0.15, "method": "conviction", "interval": 30},
    {"id": "rr_kings", "name": "R:R Kings", "desc": "Best reward-to-risk ratio picks", "cap": 10000, "max": 5, "pct": 0.15, "method": "rr", "interval": 60},
    {"id": "consensus_plays", "name": "Consensus Plays", "desc": "Multi-system agreement picks", "cap": 10000, "max": 6, "pct": 0.12, "method": "consensus", "interval": 30},
    {"id": "fresh_signals", "name": "Fresh Signals", "desc": "Newest picks from all systems", "cap": 10000, "max": 8, "pct": 0.10, "method": "fresh", "interval": 30},
    {"id": "sector_rotation", "name": "Sector Rotation", "desc": "Diversified across sectors", "cap": 10000, "max": 8, "pct": 0.10, "method": "sector", "interval": 60},
    {"id": "anti_meme", "name": "Anti-Meme", "desc": "Excludes meme coins", "cap": 10000, "max": 8, "pct": 0.10, "method": "anti_meme", "interval": 30},
    {"id": "claude_best", "name": "Claude's Best", "desc": "Hybrid methodology", "cap": 10000, "max": 8, "pct": 0.10, "method": "claude_best", "interval": 30},
    {"id": "deep_drawdown_dca", "name": "Deep Drawdown DCA", "desc": "Deep value buy-the-blood", "cap": 10000, "max": 5, "pct": 0.15, "method": "deep_value", "interval": 120},
    {"id": "rsi_capitulation", "name": "RSI Capitulation Sniper", "desc": "RSI oversold bounce plays", "cap": 10000, "max": 5, "pct": 0.15, "method": "deep_value", "interval": 120},
    {"id": "fear_greed_contrarian", "name": "Fear & Greed Contrarian", "desc": "F&G index extremes", "cap": 10000, "max": 5, "pct": 0.15, "method": "deep_value", "interval": 120},
    {"id": "relative_strength_recovery", "name": "Relative Strength Recovery", "desc": "Relative laggard recovery", "cap": 10000, "max": 5, "pct": 0.20, "method": "deep_value", "interval": 120},
    {"id": "hoffman_elite", "name": "Hoffman Elite", "desc": "Hoffman + Connors RSI combo", "cap": 10000, "max": 5, "pct": 0.15, "method": "htf_hoffman", "interval": 120},
    {"id": "htf_trend_follow", "name": "HTF Trend Follow", "desc": "Higher timeframe trends", "cap": 10000, "max": 5, "pct": 0.15, "method": "htf_trend", "interval": 120},
    {"id": "htf_weekly_momentum", "name": "HTF Weekly Momentum", "desc": "EMA stack pullbacks", "cap": 10000, "max": 5, "pct": 0.15, "method": "htf_momentum", "interval": 120},
    {"id": "prop_conservative", "name": "Prop: Conservative", "desc": "Prop firm sim — conservative", "cap": 100000, "max": 8, "pct": 0.05, "method": "score", "interval": 30, "prop": True, "daily_loss": 4, "max_dd": 8, "target": 8},
    {"id": "prop_aggressive", "name": "Prop: Aggressive", "desc": "Prop firm sim — aggressive", "cap": 100000, "max": 10, "pct": 0.08, "method": "score", "interval": 30, "prop": True, "daily_loss": 6, "max_dd": 10, "target": 8},
    {"id": "prop_swing", "name": "Prop: Swing Trader", "desc": "Prop firm sim — swing", "cap": 200000, "max": 5, "pct": 0.10, "method": "rr", "interval": 60, "prop": True, "daily_loss": 3, "max_dd": 6, "target": 8},
    {"id": "stocks_best", "name": "Stocks: Best Picks", "desc": "Equity picks only", "cap": 10000, "max": 5, "pct": 0.15, "method": "score", "interval": 60},
    {"id": "stocks_short_term", "name": "Stocks: Short-Term Reversal", "desc": "Equity mean reversion", "cap": 10000, "max": 5, "pct": 0.15, "method": "fresh", "interval": 60},
    {"id": "forex_carry", "name": "Forex: Carry & Momentum", "desc": "Forex carry and momentum", "cap": 10000, "max": 4, "pct": 0.15, "method": "score", "interval": 60},
    {"id": "multi_asset_diversified", "name": "Multi-Asset: Diversified", "desc": "Mixed asset classes", "cap": 10000, "max": 6, "pct": 0.12, "method": "sector", "interval": 60},
]

new_state = {}
for pdef in PORTFOLIOS:
    new_state[pdef["id"]] = {
        "id": pdef["id"],
        "name": pdef["name"],
        "description": pdef["desc"],
        "methodology": pdef["method"],
        "initial_capital": pdef["cap"],
        "equity": pdef["cap"],
        "high_water_mark": pdef["cap"],
        "cash": pdef["cap"],
        "max_positions": pdef["max"],
        "position_pct": pdef["pct"],
        "positions": [],
        "closed_trades": [],
        "equity_history": [{"time": now.isoformat(), "equity": pdef["cap"]}],
        "total_commission": 0.0,
        "total_slippage": 0.0,
        "wins": 0,
        "losses": 0,
        "max_drawdown_pct": 0.0,
        "daily_pnl": 0.0,
        "daily_pnl_reset_date": now.strftime("%Y-%m-%d"),
        "created_at": now.isoformat(),
        "last_updated": "",
        "update_interval_min": pdef.get("interval", 30),
        "prop_firm": pdef.get("prop", False),
        "daily_loss_limit_pct": pdef.get("daily_loss", 0),
        "max_drawdown_limit_pct": pdef.get("max_dd", 0),
        "profit_target_pct": pdef.get("target", 0),
        "resets": 0,
        "reset_history": [],
        "status": "ACTIVE",
    }

with open(STATE_FILE, "w") as f:
    json.dump(new_state, f, indent=2)

print(f"\nNew state: {len(new_state)} portfolios, all clean")
for pid, pdata in new_state.items():
    cap = pdata["initial_capital"]
    print(f"  {pdata['name']:35s} ${cap:>10,}  max_pos={pdata['max_positions']}  method={pdata['methodology']}")

total = sum(p["initial_capital"] for p in new_state.values())
print(f"\nTotal capital: ${total:,}")
print("RESET COMPLETE.")
