"""Build the prediction tracker from the closed ledger.

Source of truth: audit_dashboard/data/dashboard_data.json (picks.recent_closed).
A field that does not exist in the payload is written NOT MEASURED, never invented.

Run from the repo root: python3 <ws>/experiments/build_tracker.py <ws>
"""
import csv
import json
import os
import sys
from collections import Counter

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SRC = "audit_dashboard/data/dashboard_data.json"
d = json.load(open(SRC))
closed = (d.get("picks") or {}).get("recent_closed") or []


def g(p, *keys, default="NOT MEASURED"):
    for k in keys:
        v = p.get(k)
        if v not in (None, "", "None"):
            return v
    return default



def _horizon(p):
    """Hold length from the two timestamps the payload does carry.

    Preferred: explicit hold_days. Otherwise derive from entry->close, which is a measurement
    of the row itself. NOT MEASURED only when neither is available.
    """
    if p.get("hold_days") is not None:
        return "%sd" % p["hold_days"]
    t0 = p.get("timestamp") or p.get("entry_time")
    t1 = p.get("closed_at") or p.get("resolved_at")
    if t0 and t1:
        try:
            import datetime as _dt
            a = _dt.datetime.fromisoformat(str(t0).replace("Z", "+00:00"))
            b = _dt.datetime.fromisoformat(str(t1).replace("Z", "+00:00"))
            h = (b - a).total_seconds() / 3600.0
            return f"{h/24:.2f}d" if h >= 24 else f"{h:.2f}h"
        except ValueError:
            return "NOT MEASURED"
    return "NOT MEASURED"


rows = []
for p in closed:
    try:
        pnl = float(p.get("pnl_pct"))
    except (TypeError, ValueError):
        pnl = None
    rows.append({
        "timestamp": g(p, "closed_at", "resolved_at"),
        "asset": g(p, "symbol"),
        "asset_class": p.get("asset_class") or "NOT MEASURED",
        "regime": g(p, "regime_at_entry", "market_regime", "regime"),
        "direction": g(p, "direction", "signal_type"),
        "expected_return": g(p, "expected_return", "target_pct", "predicted_return"),
        "tp": g(p, "take_profit"),
        "sl": g(p, "stop_loss"),
        "horizon": _horizon(p),
        "confidence": g(p, "confidence", "score"),
        "actual_outcome": g(p, "pnl_pct"),
        "exit_reason": g(p, "exit_reason"),
        "hit_miss": ("hit" if (pnl is not None and pnl > 0) else
                     "miss" if (pnl is not None and pnl < 0) else "flat"),
        "trade_log_link": ("#pick-" + str(p["id"])) if p.get("id") else g(p, "id"),
        "strategy": g(p, "strategy"),
    })

os.makedirs(os.path.join(OUT, "tracker"), exist_ok=True)
csv_path = os.path.join(OUT, "tracker", "predictions_tracker.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

hit = sum(1 for r in rows if r["hit_miss"] == "hit")
miss = sum(1 for r in rows if r["hit_miss"] == "miss")
meas_exp = sum(1 for r in rows if r["expected_return"] != "NOT MEASURED")
meas_reg = sum(1 for r in rows if r["regime"] != "NOT MEASURED")

cols = list(rows[0].keys())
head = "".join(f'<th onclick="sortBy({i})">{c}</th>' for i, c in enumerate(cols))
body = "\n".join("<tr>" + "".join(f"<td>{r[c]}</td>" for c in cols) + "</tr>" for r in rows[:5000])
html = f"""<!doctype html><meta charset="utf-8"><title>Prediction tracker</title>
<style>
body{{font:13px system-ui;margin:16px;background:#0b1220;color:#e2e8f0}}
table{{border-collapse:collapse;width:100%}}
th,td{{padding:3px 6px;border-bottom:1px solid #1e293b;text-align:left;white-space:nowrap}}
th{{position:sticky;top:0;background:#111827;cursor:pointer;color:#94a3b8}}
tr:hover{{background:#111827}}.n{{color:#94a3b8}}
</style>
<h2>Prediction tracker</h2>
<p class="n">{len(rows)} rows · hit {hit} · miss {miss} · expected_return measured {meas_exp}/{len(rows)}
· regime measured {meas_reg}/{len(rows)}<br>
Source: {SRC} generated_at {d.get('generated_at')}. A cell reading NOT MEASURED means the payload
has no such field — it is not zero.</p>
<table id="t"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
<script>
var dir = {{}};
function sortBy(i) {{
  var t = document.getElementById('t'), tb = t.tBodies[0];
  var rows = Array.prototype.slice.call(tb.rows);
  dir[i] = !dir[i];
  rows.sort(function (a, b) {{
    var x = a.cells[i].innerText, y = b.cells[i].innerText;
    var nx = parseFloat(x), ny = parseFloat(y);
    var cmp = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
    return dir[i] ? cmp : -cmp;
  }});
  rows.forEach(function (r) {{ tb.appendChild(r); }});
}}
</script>"""
open(os.path.join(OUT, "tracker", "predictions_tracker.html"), "w").write(html)

print(f"tracker: {len(rows)} rows -> {csv_path}")
print(f"  hit {hit} | miss {miss} | flat {len(rows) - hit - miss}")
print(f"  expected_return present in {meas_exp} rows | regime present in {meas_reg} rows")
print("  classes:", dict(Counter(r["asset_class"] for r in rows).most_common(8)))
