import json

with open("data/alpha_research_v3.json") as f:
    data = json.load(f)

v = data["validations"]
v.sort(key=lambda x: (int(x["checks_passed"].split("/")[0]), x["total_pnl"]), reverse=True)

print(f"Total strategies tested: {len(v)}")
print()

header = f"{'RK':>3} {'TIER':<8} {'STRATEGY':<50} {'TR':>4} {'WR':>6} {'TOT PnL':>9} {'PF':>5} {'CHK':>5}  VERDICT"
print(header)
print("-" * len(header))

for i, s in enumerate(v):
    sign = "+" if s["total_pnl"] >= 0 else ""
    print(f"{i+1:>3} {s['tier']:<8} {s['name']:<50} {s['trades']:>4} {s['win_rate']:>5.1f}% {sign}{s['total_pnl']:>7.1f}% {s['profit_factor']:>5.2f} {s['checks_passed']:>5}  {s['verdict']}")

print()
pw = sum(1 for s in v if int(s["checks_passed"].split("/")[0]) >= 5)
st = sum(1 for s in v if int(s["checks_passed"].split("/")[0]) == 4)
pr = sum(1 for s in v if int(s["checks_passed"].split("/")[0]) == 3)
np_ = sum(1 for s in v if int(s["checks_passed"].split("/")[0]) < 3)
print(f"PROVEN WINNERS (5+/6): {pw}")
print(f"STRONG (4/6):          {st}")
print(f"PROMISING (3/6):       {pr}")
print(f"NOT PROVEN (<3):       {np_}")

# Print detail on winners and strong
for s in v:
    chk = int(s["checks_passed"].split("/")[0])
    if chk >= 4:
        print(f"\n  {'='*60}")
        print(f"  {s['verdict']} — {s['name']} [{s['tier']}]")
        print(f"  Trades: {s['trades']} | WR: {s['win_rate']}% | Total PnL: {s['total_pnl']:+.1f}% | PF: {s['profit_factor']:.2f}")
        for k, c in s["checks"].items():
            status = "PASS" if c["pass"] else "FAIL"
            print(f"    [{status}] {k}: {c['value']}")
