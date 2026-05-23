import json

d = json.load(open("data/live_challenge_results.json"))

with open("data/challenge_dump.txt", "w") as f:
    f.write(f"Cycle: {d['cycles_completed']} | Time: {d['current_time_est']}\n")
    f.write(f"Status: {d['status']}\n\n")

    for n, v in d["algorithms"].items():
        f.write(f"ALGO: {n}\n")
        f.write(f"  predictions={v['predictions']} wins={v['wins']} losses={v['losses']} open={v['open']}\n")
        f.write(f"  realized={v['realized_pnl']} unrealized={v['unrealized_pnl']} total={v['total_pnl']}\n\n")

    f.write("---ALL PREDICTIONS---\n")
    for i, p in enumerate(d["all_predictions"]):
        f.write(f"\n#{i+1}\n")
        f.write(f"  algo: {p['algo']}\n")
        f.write(f"  direction: {p['direction']}\n")
        f.write(f"  symbol: {p['symbol']}\n")
        f.write(f"  entry_price: {p['entry_price']}\n")
        f.write(f"  tp_price: {p['tp_price']}\n")
        f.write(f"  sl_price: {p['sl_price']}\n")
        f.write(f"  tp_pct: {p['tp_pct']}%\n")
        f.write(f"  sl_pct: {p['sl_pct']}%\n")
        f.write(f"  confidence: {p['confidence']}%\n")
        f.write(f"  reason: {p['reason']}\n")
        f.write(f"  entry_time_est: {p.get('entry_time_est', '?')}\n")
        f.write(f"  outcome: {p['outcome']}\n")
        f.write(f"  unrealized_pnl: {p.get('unrealized_pnl', 0)}\n")
        f.write(f"  current_price: {p.get('current_price', '?')}\n")

print("Dumped to data/challenge_dump.txt")
