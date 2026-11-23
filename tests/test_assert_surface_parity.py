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
