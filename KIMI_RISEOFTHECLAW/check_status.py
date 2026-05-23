import json

d = json.load(open("data/live_challenge_results.json"))
print(f"Cycle: {d['cycles_completed']} | Time: {d['current_time_est']}")
print(f"Status: {d['status']}")
print()

print("=" * 70)
print(f"{'ALGORITHM':20s} {'Picks':>5s} {'W':>3s} {'L':>3s} {'Open':>4s} {'Realized':>10s} {'Unrealized':>10s} {'Total':>10s}")
print("=" * 70)
for n, v in d["algorithms"].items():
    print(f"{n:20s} {v['predictions']:5d} {v['wins']:3d} {v['losses']:3d} {v['open']:4d} "
          f"{v['realized_pnl']:+10.2f}% {v['unrealized_pnl']:+10.2f}% {v['total_pnl']:+10.2f}%")

print()
print("=" * 70)
print(f"{'Algo':15s} {'Dir':5s} {'Symbol':12s} {'Entry':>12s} {'Unrealized':>10s} {'Status'}")
print("=" * 70)
for p in d["all_predictions"]:
    unr = p.get("unrealized_pnl", 0) or 0
    icon = "+" if unr > 0 else "" if unr == 0 else ""
    print(f"{p['algo'][:15]:15s} {p['direction']:5s} {p['symbol']:12s} "
          f"${p['entry_price']:>11.4f} {unr:+10.3f}% {p['outcome']}")

# Summary
total_unr = sum(p.get("unrealized_pnl", 0) or 0 for p in d["all_predictions"] if p["outcome"] == "OPEN")
total_real = sum(float(p.get("pnl_pct", 0) or 0) or 0 for p in d["all_predictions"] if p["outcome"] != "OPEN")
print(f"\nTotal Unrealized: {total_unr:+.3f}%  |  Total Realized: {total_real:+.3f}%")
