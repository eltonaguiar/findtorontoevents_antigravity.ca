"""
Quick audit: What system-level metrics do we already have in dashboard_payload.json?
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "audit_trail/data/dashboard_payload.json", "r", encoding="utf-8"))

systems = d.get("systems", [])
print(f"Total systems in payload: {len(systems)}")
print()

# Show all fields available per system
if systems:
    sample = systems[0]
    print("Fields per system:", list(sample.keys()))
    print()

# Full system data
for s in sorted(systems, key=lambda x: x.get("total_pnl", 0) or 0, reverse=True):
    print(f"{s.get('name', '?'):<30} WR={s.get('win_rate',0):>5.1f}%  trades={s.get('total_trades',0):>4}  "
          f"closed={s.get('closed_picks',0):>4}  active={s.get('active_picks',0):>4}  "
          f"pnl={s.get('total_pnl',0):>8.1f}%  PF={str(s.get('profit_factor','?')):>6}  "
          f"exp={str(s.get('expectancy','?')):>6}  "
          f"maxDD={s.get('max_drawdown','?')}")

# Also check what active picks look like per system
print()
print("=" * 60)
print("Active picks per system (for 'holdings' view)")
active = d["picks"]["active"]
from collections import Counter
sys_counts = Counter(p.get("source_system") for p in active)
for sys_name, count in sys_counts.most_common():
    print(f"  {sys_name}: {count} active picks")

# Check closed picks per system
print()
print("=" * 60)
print("Closed picks per system (for performance history)")
closed = d["picks"].get("closed", [])
sys_closed = Counter(p.get("source_system") for p in closed)
for sys_name, count in sys_closed.most_common()[:15]:
    print(f"  {sys_name}: {count} closed picks")
