#!/usr/bin/env python3
"""Aggregate ETF dual-momentum paper pilot forward stats for promotion gates."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "verified_strategies" / "paper_pilot" / "etf_dual_momentum_paper_log.jsonl"
STATE_PATH = ROOT / "verified_strategies" / "paper_pilot" / "etf_dual_momentum_state.json"
WF_PATH = ROOT / "verified_strategies" / "WALKFORWARD_REPORT.json"
OUT_PATH = ROOT / "reports" / "etf_forward_stats_latest.json"

FORWARD_N_TARGET = 100
SHADOW_N_TARGET = 30


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _closed_from_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    closed = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "CLOSE":
            closed.append(row)
    return closed


def _pf_wr(closed: list[dict]) -> tuple[float, float, int]:
    if not closed:
        return 0.0, 0.0, 0
    wins = sum(1 for r in closed if float(r.get("pnl_pct") or 0) > 0)
    gross_win = sum(float(r["pnl_pct"]) for r in closed if float(r.get("pnl_pct") or 0) > 0)
    gross_loss = abs(sum(float(r["pnl_pct"]) for r in closed if float(r.get("pnl_pct") or 0) < 0))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    return pf, wins / len(closed), len(closed)


def _gates(n: int, pf: float, wr: float, oos_pf: float) -> list[str]:
    gates = []
    if n < FORWARD_N_TARGET:
        gates.append(f"n<{FORWARD_N_TARGET}")
    if pf < 1.5:
        gates.append("pf<1.5")
    if wr < 0.5:
        gates.append("wr<50%")
    if oos_pf > 0 and pf < 0.85 * oos_pf:
        gates.append("pf<0.85*oos")
    return gates


def build_report() -> dict:
    closed = _closed_from_log()
    pf, wr, n = _pf_wr(closed)
    wf = _load_json(WF_PATH)
    lab = wf.get("dual_momentum_etf") or wf.get("etf_dual_momentum") or {}
    oos_pf = float(lab.get("pf") or 1.21)
    gates = _gates(n, pf, wr, oos_pf)
    state = _load_json(STATE_PATH)
    open_pos = state.get("open_position")

    shadow_gates = []
    if n < SHADOW_N_TARGET:
        shadow_gates.append(f"n<{SHADOW_N_TARGET}")
    shadow_ready = len(shadow_gates) == 0 and pf >= 1.2 and wr >= 0.4

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy_id": "etf_verified_dual_momentum",
        "lab_walkforward": {
            "verdict": lab.get("verdict", "PASS"),
            "oos_pf": oos_pf,
            "oos_n": lab.get("n", 32),
            "artifact": str(WF_PATH),
        },
        "paper_pilot_forward": {
            "source": "paper_pilot_virtual",
            "n_closed": n,
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "promotion_ready": len(gates) == 0 and n >= FORWARD_N_TARGET,
            "shadow_checkpoint_ready": shadow_ready,
            "gates": gates,
            "shadow_gates": shadow_gates,
            "open_position": open_pos,
            "signal": state.get("signal"),
            "symbol": state.get("symbol"),
        },
        "recommend_scanner_enable": False,
        "enable_flag": "ETF_VERIFIED_DUAL_MOMENTUM_ENABLED",
        "forward_n_target": FORWARD_N_TARGET,
        "shadow_n_target": SHADOW_N_TARGET,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    report = build_report()
    print(json.dumps(report, indent=2))
    if args.write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        pilot_copy = ROOT / "verified_strategies" / "paper_pilot" / "etf_forward_stats.json"
        pilot_copy.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
