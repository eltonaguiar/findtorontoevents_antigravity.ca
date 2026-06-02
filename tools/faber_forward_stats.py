#!/usr/bin/env python3
"""Faber TAA paper pilot forward stats (ETF probation graduation track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "verified_strategies" / "paper_pilot" / "faber_taa_paper_log.jsonl"
POSITIONS_PATH = ROOT / "verified_strategies" / "paper_pilot" / "faber_taa_positions.json"
OUT_PATH = ROOT / "reports" / "faber_forward_stats_latest.json"
FORWARD_N_TARGET = 100


def _load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
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
        if row.get("event") == "CLOSE" or row.get("status") == "CLOSED":
            closed.append(row)
    return closed


def build_report() -> dict:
    closed = _closed_from_log()
    n = len(closed)
    wins = sum(1 for r in closed if float(r.get("pnl_pct") or 0) > 0)
    gw = sum(float(r["pnl_pct"]) for r in closed if float(r.get("pnl_pct") or 0) > 0)
    gl = abs(sum(float(r["pnl_pct"]) for r in closed if float(r.get("pnl_pct") or 0) < 0))
    pf = (gw / gl) if gl > 0 else (0.0 if n == 0 else 999.0)
    wr = (wins / n) if n else 0.0
    gates = []
    if n < FORWARD_N_TARGET:
        gates.append(f"n={n}<{FORWARD_N_TARGET}")
    if pf < 1.5:
        gates.append(f"PF={pf:.2f}<1.5")
    if wr < 0.5:
        gates.append(f"WR={wr:.1%}<50%")

    positions = _load_json(POSITIONS_PATH)
    open_syms = []
    open_count = 0
    portfolio_value = None
    if isinstance(positions, dict):
        opens = positions.get("open") or positions.get("positions") or []
        if isinstance(opens, list):
            open_count = len(opens)
            open_syms = [p.get("symbol") for p in opens if isinstance(p, dict) and p.get("symbol")]
        portfolio_value = positions.get("portfolio_value")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": "faber_taa_paper_pilot",
        "n_closed": n,
        "wr": round(wr, 4),
        "pf": round(min(pf, 999.0), 4),
        "open_count": open_count,
        "portfolio_value": portfolio_value,
        "promotion_ready": len(gates) == 0 and n >= FORWARD_N_TARGET,
        "gates": gates,
        "open_symbols": open_syms[:10],
        "note": "0 ETF strategy closes in trading_picks — forward pilot only until resolver closes etf_faber_tactical rows.",
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
        print(f"Wrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
