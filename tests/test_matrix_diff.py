"""Tests for tools/matrix_diff.py"""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "matrix_diff", _ROOT / "tools" / "matrix_diff.py"
)
assert _spec and _spec.loader
_md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_md)
run_diff = _md.run_diff


def test_run_diff_flags_wr_drop():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        prev = p / "prev.csv"
        curr = p / "curr.csv"
        prev.write_text(
            "system,symbol,trades,wins,wr_pct,avg_pnl_pct\n"
            "s1,AA,10,8,80.0,1\n",
            encoding="utf-8",
        )
        curr.write_text(
            "system,symbol,trades,wins,wr_pct,avg_pnl_pct\n"
            "s1,AA,12,7,58.0,0.5\n",
            encoding="utf-8",
        )
        lines = run_diff(prev, curr, threshold_pp=15.0)
        assert len(lines) == 1
        assert "s1" in lines[0] and "AA" in lines[0]


def test_run_diff_no_flag_below_threshold():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        prev = p / "prev.csv"
        curr = p / "curr.csv"
        prev.write_text(
            "system,symbol,trades,wins,wr_pct\ns1,AA,10,6,60.0\n", encoding="utf-8"
        )
        curr.write_text(
            "system,symbol,trades,wins,wr_pct\ns1,AA,11,6,55.0\n", encoding="utf-8"
        )
        lines = run_diff(prev, curr, threshold_pp=15.0)
        assert lines == []
