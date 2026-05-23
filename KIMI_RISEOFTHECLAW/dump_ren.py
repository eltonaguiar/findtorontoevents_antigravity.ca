import json

with open("data/renaissance_killer_v1.json") as f:
    data = json.load(f)

v = data["ensemble_results"]
v.sort(key=lambda x: (int(x["checks_passed"].split("/")[0]), x["total_pnl"]), reverse=True)

print(f"Total ensemble strategies: {len(v)}")
print()

header = f"{'RK':>3} {'ASSET':<35} {'TR':>5} {'WR':>6} {'PnL':>9} {'SHP':>5} {'PF':>5} {'CAL':>5} {'KEL':>6} {'CHK':>5}  VERDICT"
print(header)
print("-" * 115)

for i, s in enumerate(v, 1):
    sign = "+" if s["total_pnl"] >= 0 else ""
    print(f"{i:>3} {s['name']:<35} {s['trades']:>5} {s['win_rate']:>5.1f}% {sign}{s['total_pnl']:>7.1f}% "
          f"{s['sharpe']:>5.2f} {s['profit_factor']:>5.2f} {s['calmar']:>5.2f} {s['kelly_fraction']:>5.4f} "
          f"{s['checks_passed']:>5}  {s['verdict']}")

# Count tiers
tiers = {}
for s in v:
    tiers[s['verdict']] = tiers.get(s['verdict'], 0) + 1

print()
for t, c in sorted(tiers.items()):
    print(f"  {t}: {c}")

# Detail best ones
print()
for s in v:
    chk = int(s['checks_passed'].split('/')[0])
    if chk >= 5:
        print(f"\n  === {s['verdict']} === {s['name']}")
        print(f"  Trades: {s['trades']} | WR: {s['win_rate']}% | PnL: {s['total_pnl']:+.1f}% | Sharpe: {s['sharpe']}")
        print(f"  PF: {s['profit_factor']} | Calmar: {s['calmar']} | Expectancy: {s['expectancy']} | Kelly: {s['kelly_fraction']*100:.1f}%")
        print(f"  WF Consistency: {s.get('walk_forward_consistency', 'N/A')}% ({s.get('profitable_windows', 'N/A')})")
        for k, c in s['checks'].items():
            status = "PASS" if c['pass'] else "FAIL"
            print(f"    [{status}] {k}: {c['value']}")
