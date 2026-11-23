"""Smoke test for P0-1 parity assertion tool."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_assert_surface_parity_help_and_basic(tmp_path):
    """Tool must accept --help and run on identical ledgers + fresh status."""
    l1 = tmp_path / "a.json"
    l2 = tmp_path / "b.json"
    st = tmp_path / "status.json"
    l1.write_text('{"schema":"x"}')
    l2.write_text('{"schema":"x"}')
    st.write_text('{"stale": false}')

    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/assert_surface_parity.py"),
         "--ledger", str(l1), "--ledger", str(l2), "--status", str(st)],
        cwd=ROOT, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_audit2_js_ledger_served_from_disclosure(tmp_path):
    """P2-9: --audit2-js must verify LEDGER_SERVED_FROM disclosure is present."""
    l1 = tmp_path / "a.json"
    l2 = tmp_path / "b.json"
    st = tmp_path / "status.json"
    l1.write_text('{"schema":"x"}')
    l2.write_text('{"schema":"x"}')
    st.write_text('{"stale": false}')

    # real audit2.js carries the disclosure -> passes
    real_js = ROOT / "audit_dashboard/audit2.js"
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/assert_surface_parity.py"),
         "--ledger", str(l1), "--ledger", str(l2), "--status", str(st),
         "--audit2-js", str(real_js)],
        cwd=ROOT, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    assert real_js.read_text().count("LEDGER_SERVED_FROM") >= 1

    # a js without the disclosure -> FAIL
    bare_js = tmp_path / "bare.js"
    bare_js.write_text('"use strict";\nvar PODS = [];\n')
    r2 = subprocess.run(
        [sys.executable, str(ROOT / "tools/assert_surface_parity.py"),
         "--ledger", str(l1), "--ledger", str(l2), "--status", str(st),
         "--audit2-js", str(bare_js)],
        cwd=ROOT, capture_output=True, text=True
    )
    assert r2.returncode == 1, r2.stdout
    assert "LEDGER_SERVED_FROM" in r2.stderr
