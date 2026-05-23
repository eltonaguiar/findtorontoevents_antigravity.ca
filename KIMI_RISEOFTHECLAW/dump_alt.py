import json

with open("data/alternative_data_results.json") as f:
    data = json.load(f)

print("ALTERNATIVE DATA ENGINE RESULTS")
print("=" * 110)
for r in data["results"]:
    if r["trades"] >= 3:
        sign = "+" if r.get("total_pnl", 0) >= 0 else ""
        name = r["name"]
        print(f"  {name:<50} {r['trades']:>4}t  WR:{r.get('win_rate',0):>5.1f}%  "
              f"PnL:{sign}{r.get('total_pnl',0):>7.1f}%  Sharpe:{r.get('sharpe',0):>6.2f}  "
              f"p={r.get('p_value',1):.4f}  {r['verdict']}")
