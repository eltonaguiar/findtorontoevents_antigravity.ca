#!/usr/bin/env python3
"""Standalone A/B analysis for leakage-purged ml_gatekeeper.

Per Grok PR #917 spec 2026-05-12. Companion to (not replacement for):
- tools/ml_gatekeeper_ab_decision.py (matches active picks ↔ closed_picks
  by tuple key)

This script uses a CLEANER signal: it reads `_ab_sleeve` field STAMPED
ONTO each pick by ml_gatekeeper.gatekeeper.score_active_picks_ab() at
emission time. Filters closed_picks.json to picks that were emitted
via the A/B router and have the sleeve tag. Computes WR/PF/cum_pnl per
arm + per asset_class + one-sided z-test.

Outputs:
  ml_gatekeeper/data/ab_summary.json   — machine-readable
  audit_dashboard/data/ab_panel.html   — drop-in HTML widget

Path conventions match this repo (closed_picks.json lives in
alpha_engine/data/, not ml_gatekeeper/data/). DB credentials are NOT
needed — this script is JSON-only.

Usage:
  python -m ml_gatekeeper.ab_analysis
  python ml_gatekeeper/ab_analysis.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Closed picks live in alpha_engine/data per repo convention; ml_gatekeeper
# only stores its own scored emissions. Fall back to ml_gatekeeper/data
# if the alpha_engine path is missing.
CLOSED_PICKS_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"
if not CLOSED_PICKS_PATH.exists():
    CLOSED_PICKS_PATH = ROOT / "ml_gatekeeper" / "data" / "closed_picks.json"

OUT_JSON = ROOT / "ml_gatekeeper" / "data" / "ab_summary.json"
OUT_HTML = ROOT / "audit_dashboard" / "data" / "ab_panel.html"
ROLLBACK_STATE = ROOT / "ml_gatekeeper" / "data" / "ab_rollback_state.json"
EMPTY_STREAK_THRESHOLD = 7


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erf (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def compute_metrics(pick_list: list) -> dict:
    if not pick_list:
        return {"wr": 0.0, "pf": 0.0, "cum_pnl": 0.0, "n": 0}
    # Accept pnl_pct (canonical in this repo) OR pnl (Grok spec)
    def _pnl(p):
        v = p.get("pnl_pct")
        if v is None:
            v = p.get("pnl", 0)
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0
    pnls = [_pnl(p) for p in pick_list]
    wins = sum(1 for v in pnls if v > 0)
    wr = wins / len(pnls)
    gross_profit = sum(v for v in pnls if v > 0)
    gross_loss = abs(sum(v for v in pnls if v < 0))
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )
    cum = sum(pnls)
    return {
        "wr": round(wr, 4),
        "pf": round(pf, 4) if math.isfinite(pf) else None,
        "cum_pnl": round(cum, 4),
        "n": len(pick_list),
    }


def main():
    if not CLOSED_PICKS_PATH.exists():
        print("ERROR: closed_picks.json not found at any known path",
              file=sys.stderr)
        sys.exit(1)
    with open(CLOSED_PICKS_PATH) as f:
        picks = json.load(f)
    if not isinstance(picks, list):
        print("ERROR: closed_picks.json is not a list", file=sys.stderr)
        sys.exit(1)

    # Filter to A/B-tagged emissions only (per Phase B stamping at
    # ml_gatekeeper/gatekeeper.py _stamp_sleeve())
    ab_picks = [p for p in picks if "_ab_sleeve" in p]
    if not ab_picks:
        print("INFO: no A/B-tagged picks yet; OLD/NEW models not in production",
              file=sys.stderr)

    arms = {"OLD": [], "NEW": []}
    asset_breakdown = {}
    for p in ab_picks:
        arm = p.get("_ab_sleeve")
        if arm not in arms:
            continue
        arms[arm].append(p)
        ac = (p.get("asset_class") or "UNKNOWN").upper()
        if ac not in asset_breakdown:
            asset_breakdown[ac] = {"OLD": [], "NEW": []}
        asset_breakdown[ac][arm].append(p)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": str(CLOSED_PICKS_PATH),
        "n_ab_tagged": len(ab_picks),
        "overall": {arm: compute_metrics(plist) for arm, plist in arms.items()},
        "asset_class": {
            ac: {arm: compute_metrics(plist) for arm, plist in d.items()}
            for ac, d in asset_breakdown.items()
        },
    }

    # One-sided z-test: H1 = NEW > OLD on WR
    old = summary["overall"]["OLD"]
    new = summary["overall"]["NEW"]
    recommendation = "INSUFFICIENT_DATA"
    if old["n"] > 30 and new["n"] > 30:
        p_old, p_new = old["wr"], new["wr"]
        n_old, n_new = old["n"], new["n"]
        p_pool = (p_old * n_old + p_new * n_new) / (n_old + n_new)
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_old + 1 / n_new))
        if se > 0:
            z = (p_new - p_old) / se
            p_value = 1.0 - _norm_cdf(z)
            wr_delta_pp = (p_new - p_old) * 100
            if p_value < 0.05 and wr_delta_pp >= 2.0:
                recommendation = "SWITCH_TO_NEW"
            elif p_value < 0.10 and wr_delta_pp >= 1.0:
                recommendation = "LEAN_NEW_CONTINUE_TESTING"
            elif p_value > 0.5 and wr_delta_pp < 0:
                recommendation = "OLD_AHEAD_INVESTIGATE_NEW"
            else:
                recommendation = "CONTINUE_TESTING"
            summary["z_test"] = {
                "z": round(z, 4),
                "p_value": round(p_value, 4),
                "wr_delta_pp": round(wr_delta_pp, 2),
                "significant_one_sided_p05": p_value < 0.05,
                "recommendation": recommendation,
            }
        else:
            recommendation = "ZERO_VARIANCE"
            summary["z_test"] = {
                "note": "zero variance — both arms identical",
                "recommendation": recommendation,
            }
    else:
        summary["z_test"] = {
            "note": f"insufficient samples (OLD n={old['n']}, NEW n={new['n']}; need >30 each)",
            "recommendation": recommendation,
        }
    summary["recommendation"] = recommendation

    # Phase-E rollback tracker: persist consecutive-empty-NEW streak
    # across cron cycles. Trigger rollback flag at 7-streak.
    summary["rollback_alert_this_cycle"] = (new["n"] == 0 and old["n"] > 0)

    state = {"consecutive_empty_new": 0, "last_updated": None, "rollback_triggered": False}
    if ROLLBACK_STATE.exists():
        try:
            prior = json.loads(ROLLBACK_STATE.read_text(encoding="utf-8"))
            if isinstance(prior, dict):
                state.update({k: prior.get(k, state[k]) for k in state})
        except (json.JSONDecodeError, OSError):
            pass
    if new["n"] == 0 and old["n"] > 0:
        state["consecutive_empty_new"] += 1
    else:
        state["consecutive_empty_new"] = 0
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state["rollback_triggered"] = state["consecutive_empty_new"] >= EMPTY_STREAK_THRESHOLD
    state["threshold"] = EMPTY_STREAK_THRESHOLD
    ROLLBACK_STATE.parent.mkdir(parents=True, exist_ok=True)
    ROLLBACK_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    summary["rollback_state"] = state

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # HTML widget
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    z = summary.get("z_test", {})
    pv = z.get("p_value", "—")
    html = f"""<div style="background:#111a33;border:1px solid #1f2a4a;border-radius:8px;padding:18px;margin:14px 0;color:#cbd5e1;font:13px system-ui,sans-serif">
<h3 style="color:#22c55e;margin:0 0 10px;font-size:15px">&#x1F52C; ML Gatekeeper A/B Results</h3>
<div style="color:#94a3b8;font-size:11px;margin-bottom:10px">NEW (leakage-purged) vs OLD (with leakage) &middot; updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
<table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="color:#94a3b8;border-bottom:1px solid #1f2a4a"><th style="text-align:left;padding:6px">Metric</th><th style="text-align:right;padding:6px">OLD</th><th style="text-align:right;padding:6px">NEW</th><th style="text-align:right;padding:6px">&Delta;</th></tr>
<tr><td style="padding:6px">Win Rate</td><td style="text-align:right;padding:6px">{old['wr']*100:.1f}%</td><td style="text-align:right;padding:6px">{new['wr']*100:.1f}%</td><td style="text-align:right;padding:6px">{(new['wr']-old['wr'])*100:+.1f}pp</td></tr>
<tr><td style="padding:6px">Profit Factor</td><td style="text-align:right;padding:6px">{old['pf'] if old['pf'] is not None else '&infin;'}</td><td style="text-align:right;padding:6px">{new['pf'] if new['pf'] is not None else '&infin;'}</td><td style="text-align:right;padding:6px">{(new['pf']-old['pf']) if (new['pf'] is not None and old['pf'] is not None) else '&mdash;'}</td></tr>
<tr><td style="padding:6px">Cum PnL</td><td style="text-align:right;padding:6px">{old['cum_pnl']}</td><td style="text-align:right;padding:6px">{new['cum_pnl']}</td><td style="text-align:right;padding:6px">{new['cum_pnl']-old['cum_pnl']:+.0f}</td></tr>
<tr><td style="padding:6px">Samples</td><td style="text-align:right;padding:6px">{old['n']}</td><td style="text-align:right;padding:6px">{new['n']}</td><td style="text-align:right;padding:6px">&mdash;</td></tr>
</table>
<div style="margin-top:10px;font-size:11px;color:#a78bfa">one-sided z-test p-value: <strong>{pv}</strong> &middot; recommendation: <strong>{recommendation}</strong> &middot; rollback streak: {state['consecutive_empty_new']}/{EMPTY_STREAK_THRESHOLD}{' &#x26A0; TRIGGERED' if state['rollback_triggered'] else ''}</div>
</div>"""
    OUT_HTML.write_text(html, encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"\nOK A/B summary → {OUT_JSON}", file=sys.stderr)
    print(f"OK HTML widget → {OUT_HTML}", file=sys.stderr)


if __name__ == "__main__":
    main()
