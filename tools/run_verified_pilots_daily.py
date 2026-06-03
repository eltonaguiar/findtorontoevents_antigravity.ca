#!/usr/bin/env python3
"""Daily verified paper pilots — ETF DM + forward stats + dashboard refresh."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "verified_pilots_daily_latest.json"


def _run(cmd: list[str]) -> dict:
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": p.returncode,
        "stdout_tail": (p.stdout or "")[-600:],
        "stderr_tail": (p.stderr or "")[-300:],
    }


def main() -> int:
    py = sys.executable
    steps = [
        _run([py, "verified_strategies/paper_pilot/etf_dual_momentum_pilot.py", "--one-shot"]),
        # 2026-06-02 EAGLE-3 second candidate (PR #462). Live lab stats:
        # n=65, WR 75.4%, PF ~3.06. Already in CRYPTO_PROVEN_STRATEGIES.
        # Flips SHADOW -> READY_REVIEW when PF>=1.5 + WR>=0.55 + n>=30 +
        # PF drift <=30% from lab.
        _run([py, "verified_strategies/paper_pilot/macd_rsi_m048_pilot.py", "--one-shot"]),
        # PR #482 bootstrap forward-test (virtual book; no production enable)
        _run([py, "verified_strategies/paper_pilot/b_flip_price_roc_forward_pilot.py"]),
        _run([py, "verified_strategies/paper_pilot/inverse_ml_btc_forward_pilot.py"]),
        _run([py, "tools/etf_forward_stats.py", "--write"]),
        _run([py, "tools/crypto_wf_forward_stats.py", "--write"]),
        _run([py, "tools/faber_forward_stats.py", "--write"]),
        _run([py, "tools/bootstrap_forward_stats.py", "--write"]),
        _run([py, "tools/pilot_forward_dashboard.py"]),
        _run([py, "tools/strategy_admit.py", "--strategy", "etf_dual_momentum", "--asset-class", "ETF", "--write"]),
    ]
    if os.environ.get("VERIFIED_PILOT_WALKFORWARD", "").strip() in ("1", "true", "yes"):
        wf = ROOT / "verified_strategies" / "walkforward_suite.py"
        if wf.exists():
            steps.append(_run([py, str(wf), "--only", "pilot"]))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": all(s["returncode"] == 0 for s in steps),
        "steps": steps,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ok={payload['ok']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
