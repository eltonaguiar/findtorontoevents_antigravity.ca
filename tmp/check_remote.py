import subprocess, json

result = subprocess.run(
    ["git", "show", "origin/main:ALPHA_ENGINE/data/active_picks.json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
print(f"Remote active_picks.json: {len(data)} picks")
for p in data:
    sym = p["symbol"]
    entry = p["entry_price"]
    last = p.get("last_checked", "N/A")
    pnl = p.get("unrealized_pnl_pct", 0)
    print(f"  {sym:20s}  entry={entry}  pnl={pnl*100:+.2f}%  last_checked={last}")
