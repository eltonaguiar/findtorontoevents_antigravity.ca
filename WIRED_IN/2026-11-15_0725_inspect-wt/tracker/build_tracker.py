"""
Multi-Horizon Prediction Tracker Generator (Phase 5b).

Reconciles pre-registered quant proof strategies (E1, M1, MA1, MA2, S1, C1, B1, CM1, FX1)
across horizons (<=1d, 1d-3mo, >3mo) with live/closed picks from findtorontoevents.ca/audit.
Outputs tracker/predictions_tracker.csv and Tufte-styled tracker/predictions_tracker.html.
"""

from __future__ import annotations

import csv
import gzip
import html
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# REPO_ROOT preamble per AGENTS.md
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TRACKER_DIR = Path(__file__).resolve().parent
BASE_DIR = TRACKER_DIR.parent
EXP_DIR = BASE_DIR / "experiments"


def map_horizon(tf: str | None) -> str:
    s = (tf or "").upper()
    if any(k in s for k in ("SCALP", "INTRADAY", "1H", "4H", "15M")):
        return "<=1d"
    if any(k in s for k in ("MONTHLY", "POSITION", "90D", "180D", "365D", "LONG")):
        return ">3mo"
    return "1d-3mo"


def build() -> int:
    cfg = json.loads((EXP_DIR / "experiment_configs.json").read_text(encoding="utf-8"))
    res_path = EXP_DIR / "experiment_results.json"
    results = json.loads(res_path.read_text(encoding="utf-8")) if res_path.exists() else {"trials": {}}
    trials = results.get("trials", {})

    snap_path = REPO_ROOT / cfg["datasets"]["live_picks_snapshot"]
    with gzip.open(snap_path, "rb") as f:
        snap = json.loads(f.read().decode("utf-8"))

    rows: list[dict[str, Any]] = []

    # 1. Pre-registered Quant Proof Forward Watchlist (9 trials mapped to explicit horizons)
    horizon_overrides = {
        "E1": ">3mo",
        "M1": ">3mo",
        "MA2": ">3mo",
        "B1": ">3mo",
        "CM1": ">3mo",
        "MA1": "1d-3mo",
        "S1": "1d-3mo",
        "C1": "<=1d",
        "FX1": "<=1d",
    }
    pre_reg_windows = {
        "E1": "90-365d monthly rebalance",
        "M1": ">=30d monthly NAV hold",
        "MA1": "30-90d Variant-C review",
        "MA2": "90-365d risk-parity combo",
        "S1": "1-14d swing cohort",
        "C1": "1h trend <=72h hold",
        "B1": "30-180d duration switch",
        "CM1": "30-180d trend rotation",
        "FX1": "Intraday-swing FX (QUARANTINED)",
    }

    generated_at = results.get("generated_at_utc") or snap.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for tcfg in cfg["trials"]:
        tid = tcfg["id"]
        tr = trials.get(tid, {})
        m = tr.get("metrics", {})
        verdict = tr.get("verdict", "PENDING")
        status = "SHADOW_WATCH" if verdict != "REJECT" else "QUARANTINED_NO_TRADE"
        if verdict == "PROVEN":
            status = "FORWARD_PAPER_READY"

        rows.append({
            "tracker_id": f"PREREG_{tid}",
            "origin": "PRE_REGISTERED_PROOF",
            "horizon_bucket": horizon_overrides.get(tid, "1d-3mo"),
            "symbol": tcfg.get("asset_class"),
            "asset_class": tcfg.get("asset_class"),
            "strategy_id": tcfg.get("name"),
            "direction": "SYSTEMATIC_LONG_OR_CASH",
            "timeframe_label": pre_reg_windows.get(tid, tcfg.get("timeframe")),
            "issued_at_utc": generated_at[:19],
            "entry_price": "NAV_OR_CLOSE",
            "take_profit": f"Benchmark={tcfg.get('benchmark')}",
            "stop_loss": "VolTarget_OR_ATR_Stop",
            "status": status,
            "gross_net_pnl_pct": m.get("cagr_net_pct", ""),
            "proof_verdict": verdict,
            "audit_flags": f"Gates={tr.get('gates_passed_of_10', 0)}/10; DSR646={tr.get('dsr_n646', '')}; CostSafety={tr.get('cost_margin_of_safety_x', '')}x",
        })

    # 2. Live /audit Active Picks (all 20)
    for r in snap.get("picks", {}).get("active", []):
        tf = r.get("trade_timeframe") or "SWING"
        flags = []
        if str(r.get("asset_class", "")).upper() == "FOREX" and str(r.get("symbol", "")).upper().endswith("USDT"):
            flags.append("SYNTHETIC_CRYPTO_IN_FX")
        if str(r.get("asset_class", "")).upper() in ("SPORTS", "FUTURES"):
            flags.append(f"NON_CORE_AC_{r.get('asset_class')}")
        if float(r.get("age_hours") or 0) > 168:
            flags.append(f"STALE_AGE_{int(float(r.get('age_hours')))}H")
        rows.append({
            "tracker_id": str(r.get("id", ""))[:64],
            "origin": "AUDIT_ACTIVE",
            "horizon_bucket": map_horizon(tf),
            "symbol": r.get("symbol", ""),
            "asset_class": r.get("asset_class", ""),
            "strategy_id": r.get("strategy", ""),
            "direction": r.get("direction", ""),
            "timeframe_label": tf,
            "issued_at_utc": str(r.get("timestamp") or "")[:19],
            "entry_price": r.get("entry_price", ""),
            "take_profit": r.get("take_profit", ""),
            "stop_loss": r.get("stop_loss", ""),
            "status": r.get("status", "OPEN"),
            "gross_net_pnl_pct": round(float(r.get("pnl_pct") or 0.0), 3),
            "proof_verdict": "LIVE_MONITORED",
            "audit_flags": ";".join(flags) if flags else "OK",
        })

    # 3. Most Recent Closed /audit Picks (latest 40 for closed reconciliation)
    closed_sorted = sorted(
        snap.get("picks", {}).get("recent_closed", []),
        key=lambda x: str(x.get("closed_at") or x.get("timestamp") or ""),
        reverse=True,
    )[:40]
    for r in closed_sorted:
        tf = r.get("trade_timeframe") or "INTRADAY"
        pnl = float(r.get("pnl_pct") or 0.0)
        flags = []
        if pnl == 0.0:
            flags.append("ZERO_PNL_EXPIRED_ARTIFACT")
        if str(r.get("asset_class", "")).upper() == "FOREX" and str(r.get("symbol", "")).upper().endswith("USDT"):
            flags.append("SYNTHETIC_CRYPTO_IN_FX")
        if not flags:
            flags.append(str(r.get("exit_reason") or "CLOSED"))
        rows.append({
            "tracker_id": str(r.get("id", ""))[:64],
            "origin": "AUDIT_RECENT_CLOSED",
            "horizon_bucket": map_horizon(tf),
            "symbol": r.get("symbol", ""),
            "asset_class": r.get("asset_class", ""),
            "strategy_id": r.get("strategy", ""),
            "direction": r.get("direction", ""),
            "timeframe_label": tf,
            "issued_at_utc": str(r.get("closed_at") or r.get("timestamp") or "")[:19],
            "entry_price": r.get("entry_price", ""),
            "take_profit": r.get("take_profit", ""),
            "stop_loss": r.get("stop_loss", ""),
            "status": r.get("status", ""),
            "gross_net_pnl_pct": round(pnl, 3),
            "proof_verdict": "CLOSED_AUDIT_SAMPLE",
            "audit_flags": ";".join(flags),
        })

    # Write CSV
    fieldnames = [
        "tracker_id", "origin", "horizon_bucket", "symbol", "asset_class",
        "strategy_id", "direction", "timeframe_label", "issued_at_utc",
        "entry_price", "take_profit", "stop_loss", "status",
        "gross_net_pnl_pct", "proof_verdict", "audit_flags",
    ]
    csv_path = TRACKER_DIR / "predictions_tracker.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    horizon_counts = Counter(r["horizon_bucket"] for r in rows)
    origin_counts = Counter(r["origin"] for r in rows)

    # Render clean Edward Tufte tabular HTML (strictly offline, high-contrast paper aesthetic)
    trs_html = []
    for r in rows:
        verdict = str(r["proof_verdict"])
        badge_cls = "badge-muted"
        if verdict == "PROVEN":
            badge_cls = "badge-pass"
        elif "PROMISING" in verdict:
            badge_cls = "badge-warn"
        elif verdict == "REJECT":
            badge_cls = "badge-fail"

        pnl_val = r["gross_net_pnl_pct"]
        pnl_str = f"{pnl_val:+.2f}%" if isinstance(pnl_val, (int, float)) else html.escape(str(pnl_val))
        pnl_cls = "num-pos" if isinstance(pnl_val, (int, float)) and pnl_val > 0 else ("num-neg" if isinstance(pnl_val, (int, float)) and pnl_val < 0 else "")

        trs_html.append(
            f"<tr data-horizon='{html.escape(r['horizon_bucket'])}' data-origin='{html.escape(r['origin'])}'>"
            f"<td><code>{html.escape(r['tracker_id'])}</code></td>"
            f"<td>{html.escape(r['origin'])}</td>"
            f"<td><strong>{html.escape(r['horizon_bucket'])}</strong></td>"
            f"<td>{html.escape(str(r['symbol']))}</td>"
            f"<td>{html.escape(str(r['asset_class']))}</td>"
            f"<td>{html.escape(str(r['strategy_id']))}</td>"
            f"<td>{html.escape(str(r['timeframe_label']))}</td>"
            f"<td>{html.escape(str(r['status']))}</td>"
            f"<td class='num {pnl_cls}'>{pnl_str}</td>"
            f"<td><span class='badge {badge_cls}'>{html.escape(verdict)}</span></td>"
            f"<td><small>{html.escape(str(r['audit_flags']))}</small></td>"
            f"</tr>"
        )

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Quant Audit — Multi-Horizon Prediction Tracker</title>
<style>
  :root {{
    --bg: #faf9f5;
    --ink: #1a1a1a;
    --muted: #555555;
    --rule: #d6d3c9;
    --pass: #1b5e20;
    --warn: #8a5300;
    --fail: #8b1a1a;
  }}
  body {{
    font-family: "Georgia", "Times New Roman", serif;
    background: var(--bg);
    color: var(--ink);
    margin: 0 auto;
    max-width: 1280px;
    padding: 28px 24px 64px;
    line-height: 1.45;
  }}
  header {{ border-bottom: 2px solid var(--ink); padding-bottom: 12px; margin-bottom: 20px; }}
  h1 {{ font-size: 1.75rem; font-weight: normal; margin: 0 0 6px; letter-spacing: -0.01em; }}
  .subtitle {{ font-family: system-ui, -apple-system, sans-serif; font-size: 0.9rem; color: var(--muted); }}
  .stats-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
    margin: 18px 0 22px;
    font-family: system-ui, -apple-system, sans-serif;
  }}
  .stat-card {{ border-top: 1px solid var(--ink); padding-top: 8px; }}
  .stat-label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
  .stat-val {{ font-size: 1.35rem; font-weight: 600; margin-top: 2px; }}
  .controls {{
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
    font-family: system-ui, -apple-system, sans-serif; font-size: 0.85rem;
    padding: 10px 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);
    margin-bottom: 16px;
  }}
  select {{
    font-family: inherit; font-size: 0.85rem; padding: 4px 8px;
    background: #fff; border: 1px solid #aaa; color: var(--ink);
  }}
  table {{
    width: 100%; border-collapse: collapse;
    font-family: system-ui, -apple-system, sans-serif; font-size: 0.82rem;
  }}
  th {{
    text-align: left; font-weight: 600; border-bottom: 2px solid var(--ink);
    padding: 8px 8px; white-space: nowrap; font-size: 0.76rem;
    text-transform: uppercase; letter-spacing: 0.04em;
  }}
  td {{ border-bottom: 1px solid var(--rule); padding: 7px 8px; vertical-align: top; }}
  tr:hover td {{ background: #f2f0e8; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .num-pos {{ color: var(--pass); font-weight: 600; }}
  .num-neg {{ color: var(--fail); font-weight: 600; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.78rem; }}
  .badge {{
    display: inline-block; padding: 2px 6px; border: 1px solid currentColor;
    font-size: 0.72rem; font-weight: 600; white-space: nowrap;
  }}
  .badge-pass {{ color: var(--pass); background: #eef6ee; }}
  .badge-warn {{ color: var(--warn); background: #fdf5e6; }}
  .badge-fail {{ color: var(--fail); background: #fbeaec; }}
  .badge-muted {{ color: var(--muted); background: #f0efe9; }}
</style>
</head>
<body>
<header>
  <h1>Multi-Horizon Prediction Tracker &amp; /audit Reconciliation</h1>
  <div class="subtitle">Run ID: <code>2026-11-15_0725_inspect-wt</code> &middot; Snapshot UTC: <code>{html.escape(str(snap.get('generated_at', generated_at)))}</code> &middot; Source: <code>findtorontoevents.ca/audit</code> + 10-Step Proof Suite</div>
</header>

<section class="stats-row">
  <div class="stat-card"><div class="stat-label">Tracked Rows</div><div class="stat-val" id="visible-count">{len(rows)}</div></div>
  <div class="stat-card"><div class="stat-label">Short (&lt;=1d)</div><div class="stat-val">{horizon_counts['<=1d']}</div></div>
  <div class="stat-card"><div class="stat-label">Swing (1d-3mo)</div><div class="stat-val">{horizon_counts['1d-3mo']}</div></div>
  <div class="stat-card"><div class="stat-label">Macro (&gt;3mo)</div><div class="stat-val">{horizon_counts['>3mo']}</div></div>
  <div class="stat-card"><div class="stat-label">Pre-Reg / Active / Closed</div><div class="stat-val">{origin_counts['PRE_REGISTERED_PROOF']} / {origin_counts['AUDIT_ACTIVE']} / {origin_counts['AUDIT_RECENT_CLOSED']}</div></div>
</section>

<div class="controls">
  <label>Horizon:
    <select id="f-horizon">
      <option value="ALL">All Horizons</option>
      <option value="<=1d">&lt;= 1 Day (Intraday / Scalp)</option>
      <option value="1d-3mo">1 Day - 3 Months (Swing / Re-rank)</option>
      <option value=">3mo">&gt; 3 Months (Monthly / Structural)</option>
    </select>
  </label>
  <label>Origin:
    <select id="f-origin">
      <option value="ALL">All Origins</option>
      <option value="PRE_REGISTERED_PROOF">Pre-Registered Proof Suite</option>
      <option value="AUDIT_ACTIVE">Live /audit Active Picks</option>
      <option value="AUDIT_RECENT_CLOSED">Recent /audit Closed Picks</option>
    </select>
  </label>
</div>

<table>
  <thead>
    <tr>
      <th>Tracker ID</th><th>Origin</th><th>Horizon</th><th>Symbol / Class</th>
      <th>Asset Class</th><th>Strategy</th><th>Window</th><th>Status</th>
      <th class="num">Return / CAGR</th><th>Verdict / State</th><th>Audit &amp; Gate Notes</th>
    </tr>
  </thead>
  <tbody id="tracker-body">
    {''.join(trs_html)}
  </tbody>
</table>

<script>
(function() {{
  const hSel = document.getElementById('f-horizon');
  const oSel = document.getElementById('f-origin');
  const rows = Array.from(document.querySelectorAll('#tracker-body tr'));
  const cntEl = document.getElementById('visible-count');
  function apply() {{
    const hv = hSel.value, ov = oSel.value;
    let vis = 0;
    for (const tr of rows) {{
      const show = (hv === 'ALL' || tr.dataset.horizon === hv) && (ov === 'ALL' || tr.dataset.origin === ov);
      tr.style.display = show ? '' : 'none';
      if (show) vis++;
    }}
    cntEl.textContent = String(vis);
  }}
  hSel.addEventListener('change', apply);
  oSel.addEventListener('change', apply);
}})();
</script>
</body>
</html>
"""
    html_path = TRACKER_DIR / "predictions_tracker.html"
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {csv_path} ({len(rows)} rows) and {html_path} ({html_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

