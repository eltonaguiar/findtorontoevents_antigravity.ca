#!/usr/bin/env python3
import json
state = json.load(open('audit_dashboard/data/claudes_test_state.json'))
for pid in ['deep_drawdown_dca', 'rsi_capitulation', 'fear_greed_contrarian', 'relative_strength_recovery']:
    port = state.get(pid, {})
    name = port.get("name", pid)
    equity = port.get("equity", 0)
    positions = port.get("positions", [])
    print(f"\n=== {name} ===")
    print(f"  Equity: ${equity:,.2f} | Positions: {len(positions)}")
    for pos in positions:
        sym = pos["symbol"]
        d = pos["direction"]
        entry = pos["entry_price"]
        tp = pos["take_profit"]
        sl = pos["stop_loss"]
        strat = pos["strategy"]
        print(f"  {sym:12s} {d:5s} entry=${entry:,.4f} TP=${tp:,.4f} SL=${sl:,.4f} strat={strat}")
