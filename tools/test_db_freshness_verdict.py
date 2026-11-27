#!/usr/bin/env python3
"""Tests for tools/db_freshness_verdict.py.

Run: python3 tools/test_db_freshness_verdict.py
Exit 0 = all pass.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERDICT = os.path.join(HERE, "db_freshness_verdict.py")
sys.path.insert(0, HERE)

from db_freshness_verdict import classify  # noqa: E402

failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}: got {got!r} want {want!r}")
        print(f"FAIL {name}: got {got!r} want {want!r}")
    else:
        print(f"ok   {name}")


# ── pure classify() cases ────────────────────────────────────────────────
check("green -> no fail",
      classify({"overall": "GREEN", "checks": [{"check": "a", "status": "GREEN"}]})["should_fail"],
      False)

check("yellow -> no fail",
      classify({"overall": "YELLOW", "checks": [{"check": "a", "status": "YELLOW"}]})["should_fail"],
      False)

# genuine staleness: RED with data fields, no `error` key
check("data-red -> fail",
      classify({"overall": "RED", "checks": [
          {"check": "live_picks", "status": "RED", "minutes_stale": 5000,
           "last_pick_at": "2026-11-20T00:00:00Z"}]})["should_fail"],
      True)

# connectivity failure: RED with `error` key
check("env-red only -> no fail",
      classify({"overall": "RED", "checks": [
          {"check": "live_picks", "status": "RED", "error": "connect failed"}]})["should_fail"],
      False)

# mixed: one real finding among connectivity failures -> must fail
mixed = classify({"overall": "RED", "checks": [
    {"check": "live_picks", "status": "RED", "error": "connect failed"},
    {"check": "backtests", "status": "RED", "minutes_stale": 9, "last_trade_at": "x"},
]})
check("mixed -> fail", mixed["should_fail"], True)
check("mixed -> 1 data red", len(mixed["data_reds"]), 1)
check("mixed -> 1 env red", len(mixed["env_reds"]), 1)

# RED with no detail at all -> do not fail (cannot attribute)
check("bare red -> no fail",
      classify({"overall": "RED", "checks": []})["should_fail"], False)

# empty checks but GREEN -> pass
check("empty green -> no fail",
      classify({"overall": "GREEN", "checks": []})["should_fail"], False)

# unknown overall treated as RED; no detail -> no fail
check("unknown overall -> no fail",
      classify({"overall": "PURPLE", "checks": []})["should_fail"], False)


# ── end-to-end exit codes ────────────────────────────────────────────────
def run_with(report, strict=False):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(report, f)
        p = f.name
    try:
        cmd = [sys.executable, VERDICT, p] + (["--strict"] if strict else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr
    finally:
        os.unlink(p)


rc, out = run_with({"overall": "GREEN", "checks": [{"check": "a", "status": "GREEN"}]})
check("e2e green exit", rc, 0)

rc, out = run_with({"overall": "YELLOW", "checks": [{"check": "a", "status": "YELLOW"}]})
check("e2e yellow exit", rc, 0)
check("e2e yellow warns", "::warning::" in out, True)

rc, out = run_with({"overall": "RED", "checks": [
    {"check": "live_picks", "status": "RED", "minutes_stale": 400,
     "last_pick_at": "2026-11-19T00:00:00Z"}]})
check("e2e data-red exit", rc, 1)
check("e2e data-red errors", "::error::" in out, True)
check("e2e data-red names check", "live_picks" in out, True)

rc, out = run_with({"overall": "RED", "checks": [
    {"check": "live_picks", "status": "RED", "error": "RuntimeError: connect failed"}]})
check("e2e env-red exit", rc, 0)
check("e2e env-red warns", "::warning::" in out, True)

# missing report
cmd = [sys.executable, VERDICT, "/tmp/definitely_not_here_xyz.json"]
r = subprocess.run(cmd, capture_output=True, text=True)
check("e2e missing report default exit", r.returncode, 0)
r2 = subprocess.run(cmd + ["--strict"], capture_output=True, text=True)
check("e2e missing report strict exit", r2.returncode, 2)

print()
if failures:
    print(f"{len(failures)} FAILURE(S)")
    sys.exit(1)
print("all verdict tests passed")
