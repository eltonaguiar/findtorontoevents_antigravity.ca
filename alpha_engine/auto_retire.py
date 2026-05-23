#!/usr/bin/env python3
"""Auto-Retirement of bleeding strategies.

Per xiao mi mimo deep-review 2026-05-12: strategies hoard for months
before quarantine (kimi_signal_tracking -954% / claude_gainer_st -355%).
Hard rules quarantine before further bleed.

Rules:
- PF < 0.5 after >=50 resolved trades -> AUTO-QUARANTINE
- WR < 35% after >=50 resolved trades -> AUTO-QUARANTINE
- Max drawdown > 20% from peak -> AUTO-QUARANTINE
- |BT_WR - FWD_WR| > 15pp with >=20 fwd trades -> AUTO-QUARANTINE (overfit)

DEFAULT DRY-RUN. Set AUTO_RETIRE_APPLY=1 to actually write the manifest.

Source: docs/feedback from xiao mi mimo (Cerebras) consultation 2026-05-12.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DASHBOARD_DATA = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
QUARANTINE_FILE = REPO / "alpha_engine" / "quarantine_manifest.json"

# Thresholds (tunable via env)
MIN_TRADES_FOR_EVAL = int(os.environ.get("AUTO_RETIRE_MIN_TRADES", "50"))
PF_FLOOR = float(os.environ.get("AUTO_RETIRE_PF_FLOOR", "0.5"))
WR_FLOOR = float(os.environ.get("AUTO_RETIRE_WR_FLOOR", "0.35"))
MAX_DRAWDOWN_PCT = float(os.environ.get("AUTO_RETIRE_MAX_DD", "-20.0"))
FWD_BT_DIVERGENCE_PP = float(os.environ.get("AUTO_RETIRE_DIVERGENCE", "0.15"))
APPLY_MODE = os.environ.get("AUTO_RETIRE_APPLY", "0") == "1"


def load_strategy_performance() -> dict[str, dict[str, Any]]:
    """Load per-strategy metrics from dashboard_data.json::systems (top-level)."""
    if not DASHBOARD_DATA.exists():
        return {}
    try:
        data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
    except Exception:
        return {}
    # Schema: top-level "systems" is the canonical list; also try performance.systems/strategies.
    systems = data.get("systems")
    if not systems:
        perf = data.get("performance", {})
        systems = perf.get("systems") or perf.get("strategies") or {}
    # systems may be list or dict
    if isinstance(systems, list):
        out = {}
        for row in systems:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or row.get("strategy") or row.get("source_system")
            if name:
                out[name] = row
        return out
    if isinstance(systems, dict):
        return systems
    return {}


def load_quarantine_manifest() -> dict:
    if QUARANTINE_FILE.exists():
        try:
            return json.loads(QUARANTINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quarantined_strategies": [],
    }


def save_quarantine_manifest(manifest: dict) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    QUARANTINE_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def evaluate_strategy(name: str, stats: dict) -> str | None:
    """Return reason string if strategy should be quarantined, else None."""
    n = int(stats.get("n_resolved") or stats.get("resolved_picks") or stats.get("total_trades") or 0)
    if n < MIN_TRADES_FOR_EVAL:
        return None
    pf = float(stats.get("profit_factor") or stats.get("pf") or 0)
    wr_raw = stats.get("win_rate") or stats.get("wr") or 0
    wr = float(wr_raw) / 100.0 if float(wr_raw) > 1 else float(wr_raw)
    max_dd = float(stats.get("max_drawdown_pct") or stats.get("max_drawdown") or stats.get("mdd_pct") or 0)
    fwd_wr_raw = stats.get("forward_win_rate") or stats.get("fwd_wr")
    bt_wr_raw = stats.get("backtest_win_rate") or stats.get("bt_wr")
    fwd_n = int(stats.get("forward_trades") or stats.get("fwd_trades") or 0)

    if pf > 0 and pf < PF_FLOOR:
        return f"PF {pf:.2f} < {PF_FLOOR} after {n} trades"
    if wr > 0 and wr < WR_FLOOR:
        return f"WR {wr:.1%} < {WR_FLOOR:.0%} after {n} trades"
    # dashboard_data.json stores max_drawdown as POSITIVE magnitude; the prior
    # `max_dd < MAX_DRAWDOWN_PCT` (where MAX_DRAWDOWN_PCT=-20) never fired
    # because no entry is negative. Compare absolute magnitudes instead.
    if abs(max_dd) > abs(MAX_DRAWDOWN_PCT):
        return f"Max DD {abs(max_dd):.1f}% > {abs(MAX_DRAWDOWN_PCT)}%"
    if fwd_wr_raw is not None and bt_wr_raw is not None and fwd_n >= 20:
        fwd_wr = float(fwd_wr_raw) / 100.0 if float(fwd_wr_raw) > 1 else float(fwd_wr_raw)
        bt_wr = float(bt_wr_raw) / 100.0 if float(bt_wr_raw) > 1 else float(bt_wr_raw)
        if abs(bt_wr - fwd_wr) > FWD_BT_DIVERGENCE_PP:
            return f"BT WR {bt_wr:.1%} vs FWD WR {fwd_wr:.1%} divergence >{FWD_BT_DIVERGENCE_PP:.0%}"
    return None


def check_auto_retire() -> list[str]:
    perf = load_strategy_performance()
    manifest = load_quarantine_manifest()
    already = {
        s.get("name", "") for s in manifest.get("quarantined_strategies", [])
        if isinstance(s, dict)
    }
    actions: list[str] = []
    for name, stats in perf.items():
        if name in already:
            continue
        if not isinstance(stats, dict):
            continue
        reason = evaluate_strategy(name, stats)
        if reason:
            # CLAUDE.md Goal #1: FOREX requires mutate-before-kill protocol
            # per docs/MUTATION_THREE_AXIS_PROTOCOL.md; do NOT silently quarantine
            # multi-class strategies that touch FOREX without investigation gate.
            asset_classes = stats.get("asset_classes") or []
            if isinstance(asset_classes, str):
                asset_classes = [asset_classes]
            touches_forex = any(
                str(ac).upper() == "FOREX" for ac in asset_classes
            )
            if touches_forex:
                actions.append(
                    f"SKIP {name}: {reason} -- TOUCHES FOREX; "
                    f"run docs/MUTATION_THREE_AXIS_PROTOCOL.md first"
                )
                continue
            entry = {
                "name": name,
                "reason": f"AUTO-RETIRE: {reason}",
                "since": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "verified_blocked_at_exec": False,
                "ref": "alpha_engine/auto_retire.py",
            }
            actions.append(f"QUARANTINE {name}: {reason}")
            if APPLY_MODE:
                manifest["quarantined_strategies"].append(entry)
    if actions and APPLY_MODE:
        save_quarantine_manifest(manifest)
    return actions


def main() -> int:
    actions = check_auto_retire()
    print(f"AUTO_RETIRE_APPLY={'1' if APPLY_MODE else '0 (DRY-RUN)'}")
    print(f"Strategies evaluated: {len(load_strategy_performance())}")
    if actions:
        print(f"Quarantine candidates ({len(actions)}):")
        for a in actions:
            print(f"  - {a}")
    else:
        print("OK: no strategies need quarantine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
