import json

v1 = json.load(open("data/live_2hr_challenge.json"))
v3 = json.load(open("data/challenge_v3.json"))

print("=== V1 CHALLENGE (Original) ===")
print(f"Start: {v1.get('start_time', '?')}")
print(f"Total: {len(v1['picks'])} picks")
for p in v1["picks"]:
    entry = p.get("verified_entry_price", p["entry_price"])
    ts = p.get("challenge_entry_time", p.get("timestamp", "?"))
    print(f"  {p['signal_type']:>4s} {p['symbol']:>16s} @ {entry:.8g}")
    print(f"       TP={p['take_profit']:.8g}  SL={p['stop_loss']:.8g}  R:R={p['risk_reward']:.1f}x")
    print(f"       Strategy: {p['strategy']}  Category: {p.get('category','?')}")
    print(f"       Reason: {p.get('reason', '?')}")
    print(f"       Timestamp: {ts}")
    print()

print("\n=== V3 CHALLENGE (Institutional) ===")
print(f"Start: {v3.get('start_time_est', '?')}")
print(f"Total: {len(v3['picks'])} picks")
for p in v3["picks"]:
    print(f"  {p['signal_type']:>4s} {p['symbol']:>12s} @ {p['entry_price']:.8g}")
    print(f"       TP={p['take_profit']:.8g}  SL={p['stop_loss']:.8g}  R:R={p['risk_reward']:.1f}x")
    print(f"       Strategy: {p['strategy']}  TF: {p['timeframe']}  Category: {p['category']}")
    print(f"       Reason: {p.get('reason', '?')}")
    print(f"       Position: ${p.get('position_size', 0):,.0f}  MaxLoss: ${p.get('max_loss', 0):.0f}")
    print(f"       Entry EST: {p.get('entry_time_est', '?')}")
    print()
