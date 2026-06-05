#!/usr/bin/env python3
"""VRP harvest paper pilot (2026-06-05).

State file + log writer for the volatility risk premium harvest strategy
(verified_strategies/vol_risk_premium_harvest.py). Writes:
  - verified_strategies/paper_pilot/vrp_harvest_state.json
  - verified_strategies/paper_pilot/vrp_harvest_paper_log.jsonl

At each invocation, computes the forward 21-day VRP harvest based on
current SPY/VIX and appends a row. Shadow-only by default.
Set VRP_PILOT_LIVE=1 to enable live sizing (operator-gated).
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Dict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import data_fetcher  # noqa: E402
import vol_risk_premium_harvest as vrp_mod  # noqa: E402

PILOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(PILOT_DIR, "vrp_harvest_state.json")
LOG_PATH = os.path.join(PILOT_DIR, "vrp_harvest_paper_log.jsonl")
LIVE = os.environ.get("VRP_PILOT_LIVE", "0") == "1"


def _read_jsonl(path: str):
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _write_jsonl(path: str, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def run_one_shot() -> Dict:
    spy_df, _ = data_fetcher.fetch_ohlcv("SPY", period_days=1260)
    vix_df, _ = data_fetcher.fetch_ohlcv("^VIX", period_days=1260)
    if spy_df is None or vix_df is None:
        raise RuntimeError("could not fetch SPY or VIX")
    if isinstance(vix_df, pd.DataFrame):
        vix_s = vix_df["close"] if "close" in vix_df.columns else vix_df.iloc[:, 0]
    else:
        vix_s = vix_df
    if isinstance(vix_s, pd.DataFrame):
        vix_s = vix_s.squeeze("columns")
    idx = pd.to_datetime(vix_s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    vix_s = pd.Series(vix_s.values, index=idx)
    vix_s = vix_s[~vix_s.index.duplicated(keep="last")].sort_index()

    anchor = spy_df["close"].index[-1]
    prior_vix = vix_s.loc[:anchor]
    if prior_vix.empty:
        raise RuntimeError("no VIX prior to anchor")
    v_t = float(prior_vix.iloc[-1])
    tail = v_t > vrp_mod.VIX_TAIL_THRESHOLD

    pnl, meta = vrp_mod.vrp_harvest_one_period(
        spy_df["close"], vix_s, anchor, tail_invert=tail)

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "anchor": str(anchor),
        "vix_at_anchor": round(v_t, 2),
        "regime": "tail_inverted" if tail else "normal_short",
        "iv_squared": meta.get("iv"),
        "expected_rv": meta.get("rv"),
        "expected_vrp_harvest": meta.get("vrp_harvest"),
        "expected_pnl": round(pnl, 6) if not math.isnan(pnl) else None,
        "size_pct": 0.10 if LIVE else 0.0,
        "live": LIVE,
        "note": "paper-only" if not LIVE else "live-sizing (operator-approved)",
    }


def update_state(decision: Dict):
    rows = _read_jsonl(LOG_PATH)
    rows.append(decision)
    _write_jsonl(LOG_PATH, rows)
    state = {
        "last_decision": decision,
        "n_runs": len(rows),
        "live": LIVE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_strategy": "verified_strategies/vol_risk_premium_harvest.py",
    }
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, default=str)

    # Wire the forward stats into a dashboard-readable JSON (EXEC PLAN 01)
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dashboard_dir = os.path.join(project_root, "audit_dashboard", "data")
        os.makedirs(dashboard_dir, exist_ok=True)
        dashboard_path = os.path.join(dashboard_dir, "vrp_forward_stats.json")
        
        now_str = pd.Timestamp.now(tz="UTC").isoformat()
        n_resolved = sum(1 for r in rows if r.get("expected_pnl") is not None and r.get("ts", "") < now_str)
        
        forward_stats = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "strategy": "vrp_harvest_v1",
            "n_runs": state["n_runs"],
            "n_resolved": n_resolved,
            "live": LIVE,
            "shadow_size_pct": 0.10,
            "regime_breakdown": {
                "normal_short": sum(1 for r in rows if r.get("regime") == "normal_short"),
                "tail_inverted": sum(1 for r in rows if r.get("regime") == "tail_inverted"),
            },
            "vix_at_last_decision": state["last_decision"].get("vix_at_anchor"),
            "next_21d_pnl_forecast": state["last_decision"].get("expected_pnl"),
            "acceptance_criteria": {
                "target_pf": 6.4,            # 0.7 × 9.14 backtest PF
                "target_md": -0.08,           # 2.4× backtest MDD ceiling
                "min_n_resolved": 30,         # for rigorous harness walk-forward to enable
                "min_attr_t": 1.5,            # lower than lab 7.88 (n<30)
            },
        }
        with open(dashboard_path, "w") as f:
            json.dump(forward_stats, f, indent=2, default=str)
        print(f"Wrote dashboard stats to {dashboard_path}")
    except Exception as e:
        print(f"Error writing vrp dashboard stats: {e}", file=sys.stderr)

    return state


def run():
    decision = run_one_shot()
    state = update_state(decision)
    print(json.dumps(state, indent=2, default=str))
    return state


if __name__ == "__main__":
    run()
