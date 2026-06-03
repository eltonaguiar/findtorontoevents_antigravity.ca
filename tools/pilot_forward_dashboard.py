#!/usr/bin/env python3
"""Unified verified pilot forward dashboard — all sleeves in one report."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "pilot_forward_dashboard.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(path: Path) -> dict:
    if not path.exists():
        return {"error": "missing"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"error": str(exc)}


def main() -> int:
    # Refresh sub-reports (best-effort)
    for script in (
        "tools/etf_forward_stats.py",
        "tools/crypto_wf_forward_stats.py",
        "tools/faber_forward_stats.py",
        "tools/bootstrap_forward_stats.py",
    ):
        args = [sys.executable, str(ROOT / script)]
        if script.endswith("bootstrap_forward_stats.py"):
            args.append("--write")
        subprocess.call(args, cwd=str(ROOT))

    etf = _load(ROOT / "reports/etf_forward_stats_latest.json")
    crypto = _load(ROOT / "reports/crypto_wf_forward_stats_latest.json")
    faber = _load(ROOT / "reports/faber_forward_stats_latest.json")
    bootstrap = _load(ROOT / "reports/bootstrap_forward_stats_latest.json")

    any_ready = any(
        x.get("paper_pilot_forward", {}).get("promotion_ready")
        or x.get("promotion_ready")
        for x in (etf, crypto, faber)
        if isinstance(x, dict)
    ) or bool(bootstrap.get("any_promotion_ready"))

    dashboard = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "forward_n_target": 100,
        "any_promotion_ready": any_ready,
        "sleeves": {
            "etf_dual_momentum": {
                "lab_wf": etf.get("lab_walkforward"),
                "forward": etf.get("paper_pilot_forward"),
                "recommend_enable": etf.get("recommend_scanner_enable"),
                "flag": etf.get("enable_flag"),
            },
            "crypto_wf_hyro": {
                "lab_wf": crypto.get("lab_walkforward"),
                "forward": crypto.get("paper_pilot_forward"),
                "recommend_vwap": crypto.get("recommend_vwap_enable"),
                "recommend_bollinger": crypto.get("recommend_bollinger_enable"),
                "flags": crypto.get("enable_flags"),
            },
            "faber_taa": faber,
            "bootstrap_b_flip": bootstrap.get("sleeves", {}).get("b_flip_price_roc"),
            "bootstrap_inverse_ml_btc": bootstrap.get("sleeves", {}).get("inverse_ml_btc_15m"),
        },
        "bootstrap_forward": bootstrap,
        "money_ready_blockers": [
            "All sleeves require forward virtual n>=100, PF>=1.5, WR>=50%",
            "Lab walk-forward PASS required for crypto/ETF scanner flags",
            "DSR/PBO shadow tier — no real-money sizing until forward track validates",
        ],
    }
    OUT.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    audit_data = ROOT / "audit_dashboard" / "data"
    audit_data.mkdir(parents=True, exist_ok=True)
    edge_path = audit_data / "verified_edge_status.json"
    try:
        from alpha_engine.verified_promotion_gate import build_edge_status

        edge_path.write_text(json.dumps(build_edge_status(), indent=2), encoding="utf-8")
        (audit_data / "pilot_forward_dashboard.json").write_text(
            json.dumps(dashboard, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        print(f"  [verified_edge_status] skip: {exc}", file=sys.stderr)
    print(json.dumps(dashboard, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
