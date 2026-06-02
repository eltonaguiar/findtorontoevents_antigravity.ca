#!/usr/bin/env python3
"""
Daily EAGLE2 operator bundle — refresh local audit JSON + reports (no FTP, no dashboard HTML gen).

Usage:
  python3 tools/run_eagle_suite.py
  python3 tools/run_eagle_suite.py --skip-swarm
  python3 tools/run_eagle_suite.py --skip-pilots
  python3 tools/run_eagle_suite.py --write-admit etf_dual_momentum,CRYPTO:vwap_reversion
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "eagle_suite_latest.json"


def _run(cmd: list[str]) -> dict:
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": p.returncode,
        "stdout_tail": (p.stdout or "")[-800:],
        "stderr_tail": (p.stderr or "")[-400:],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-swarm", action="store_true")
    ap.add_argument("--skip-pilots", action="store_true", help="Skip verified paper pilots daily")
    ap.add_argument(
        "--write-admit",
        default="",
        help="Comma pairs strategy:CLASS e.g. etf_dual_momentum:ETF,vwap_reversion:CRYPTO",
    )
    args = ap.parse_args(argv)

    steps: list[dict] = []
    py = sys.executable

    for label, cmd in [
        ("money_ready", [py, "alpha_engine/money_ready_verdict.py", "--json"]),
        ("emitter_census", [py, "tools/emitter_census.py"]),
        ("pick_quality_pulse", [py, "tools/pick_quality_pulse.py"]),
        ("strategy_admissibility", [py, "tools/strategy_admissibility_report.py", "--write"]),
    ]:
        steps.append({"step": label, **_run(cmd)})

    if not args.skip_pilots:
        steps.append({"step": "verified_pilots_daily", **_run([py, "tools/run_verified_pilots_daily.py"])})

    if not args.skip_swarm:
        steps.append({"step": "best_picks_verify", **_run([py, "tools/verify_best_picks_swarm.py"])})
        steps.append(
            {
                "step": "eagle_swarm_synthesis",
                **_run([py, "tools/eagle_swarm_synthesis.py", "--models", "hybrid-model"]),
            }
        )

    for pair in [x.strip() for x in args.write_admit.split(",") if x.strip()]:
        if ":" in pair:
            strat, ac = pair.split(":", 1)
        else:
            strat, ac = pair, "CRYPTO"
        steps.append(
            {
                "step": f"strategy_admit_{strat}",
                **_run([py, "tools/strategy_admit.py", "--strategy", strat.strip(), "--asset-class", ac.strip(), "--write"]),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freeze_promotions": True,
        "money_ready_note": "0/9 classes READY — do not size CRYPTO/EQUITY/FOREX aggregate",
        "steps": steps,
        "ok": all(s.get("returncode") == 0 for s in steps),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ok={payload['ok']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())