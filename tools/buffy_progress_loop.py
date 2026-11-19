#!/usr/bin/env python3
"""Idempotent 10-minute progress checkpoint for the 2026-11-19 work threads.

Runs only cheap, re-runnable checks and appends one JSON line per run to
reports/progress_loop/<date>.jsonl. It NEVER edits tracked source, never writes
to the DB, and self-disables after MAX_RUNS so a forgotten cron cannot grind
forever.

Checkpoints:
  taa      - report whether reports/taa_settle_2026-11-19.json exists + its verdict
  divergence - recount money_ready_verdict vs audit3_ledger per class, flag any
               ratio > 1.5x
  sim      - run the crypto sim's own tests if present on this checkout
  ledger   - count open items in reports/TODO_LEDGER_2026-11-19.json

Usage:  python3 tools/buffy_progress_loop.py [--once]
Exit 0 always (a cron must not spam mail on a known-missing artifact).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "reports" / "progress_loop"
STATE = ROOT / "reports" / "progress_loop_state.json"
MAX_RUNS = 400


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:  # noqa: BLE001 - a checkpoint must never raise
        return 1, f"{type(exc).__name__}: {exc}"


def check_taa() -> dict:
    p = ROOT / "reports" / "taa_settle_2026-11-19.json"
    if not p.exists():
        return {"state": "missing"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"state": "unreadable", "err": str(exc)}
    return {"state": "present", "verdict": d.get("verdict"),
            "best_sharpe_lag1": d.get("best_sharpe_lag1"),
            "cells": len(d.get("cells") or [])}


def check_divergence() -> dict:
    vp = ROOT / "audit_dashboard" / "data" / "money_ready_verdict.json"
    ap = ROOT / "audit_dashboard" / "data" / "audit3_ledger.json"
    if not (vp.exists() and ap.exists()):
        return {"state": "missing"}
    try:
        v = json.loads(vp.read_text(encoding="utf-8"))
        a = json.loads(ap.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"state": "unreadable", "err": str(exc)}
    vclasses = v.get("classes") or {}
    acells = a.get("cells") or a.get("ledger") or []
    agg: dict[str, list[float]] = {}
    for c in acells:
        if not isinstance(c, dict):
            continue
        k = c.get("asset_class") or c.get("class")
        pf = c.get("pf")
        if k and isinstance(pf, (int, float)):
            agg.setdefault(k, []).append(float(pf))
    out: dict[str, float] = {}
    for k, pfs in agg.items():
        vc = vclasses.get(k) or {}
        vpf = vc.get("policy_clean_pf") or vc.get("pf")
        apf = sum(pfs) / len(pfs) if pfs else None
        if isinstance(vpf, (int, float)) and apf:
            try:
                out[k] = round(float(vpf) / float(apf), 3)
            except ZeroDivisionError:
                continue
    return {"state": "computed", "ratio_verdict_over_audit3": out,
            "max_ratio": max(out.values()) if out else None,
            "n_classes": len(out)}


def check_sim() -> dict:
    t = ROOT / "tests" / "test_crypto_intraday_sim.py"
    if not t.exists():
        return {"state": "tests-not-on-this-checkout"}
    rc, out = _run([sys.executable, "-m", "pytest", str(t), "-q"], timeout=240)
    tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1:] or [""]
    return {"state": "ran", "rc": rc, "summary": tail[0][:200]}


def check_ledger() -> dict:
    p = ROOT / "reports" / "TODO_LEDGER_2026-11-19.json"
    if not p.exists():
        return {"state": "missing"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"state": "unreadable", "err": str(exc)}
    items = d.get("items") or []
    return {"state": "ok", "open": sum(1 for i in items if i.get("status") != "done"),
            "total": len(items)}


def main() -> int:
    st = {"runs": 0}
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    runs = int(st.get("runs") or 0)
    if runs >= MAX_RUNS:
        return 0

    row = {"ts": _now(), "run": runs + 1,
           "taa": check_taa(), "divergence": check_divergence(),
           "sim": check_sim(), "ledger": check_ledger()}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with (OUT_DIR / f"{day}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"runs": runs + 1, "last": row["ts"]}, indent=2),
                     encoding="utf-8")
    print(json.dumps(row, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
