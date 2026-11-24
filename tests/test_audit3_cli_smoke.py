"""Guards for the classes of breakage that took the ledger down on 2026-11-19.

Between 23:45 and 00:09 the scheduled ledger failed three times, all from a
partially-merged port rather than from trading logic:

* a duplicated ``--history`` flag made argparse raise at parser build time;
* ``main()`` passed ``require_alpha=`` to a ``build_report`` that did not accept it;
* ``ALPHA_PASSTHROUGH_KEYS`` was referenced but never defined.

None of these are behaviour bugs, so behavioural tests missed them. These smoke
checks exercise the real entry points instead.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha_engine import audit3_tribunal as T  # noqa: E402


def test_cli_parser_builds_without_duplicate_flags():
    """`--help` builds the parser; a repeated option string raises here."""
    r = subprocess.run([sys.executable, "-m", "alpha_engine.audit3_tribunal",
                        "--help"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    for flag in ("--picks", "--out", "--history", "--forward-ledger",
                 "--alpha", "--confirmatory", "--prev-ledger", "--max-churn"):
        assert flag in r.stdout, flag


def test_build_report_accepts_require_alpha():
    """main() passes this keyword in the scheduled build; it must exist."""
    rows = [{"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
             "pnl_pct": 1.0, "symbol": "BTCUSDT", "source_system": "x"}]
    rep = T.build_report(rows, "x.json", None, require_alpha=True)
    assert rep["schema"] == "audit3.v1"


def test_require_alpha_caps_proven_when_alpha_is_absent():
    """G8: no alpha ⇒ nothing can be PROVEN_T2 in a require-alpha build."""
    rows = []
    for i in range(140):
        rows.append({"asset_class": "CRYPTO", "strategy": "s1",
                     "direction": "LONG", "pnl_pct": 4.0,
                     "symbol": f"S{i % 5}", "source_system":
                     "src_a" if i % 2 else "src_b"})
    for r in rows[:5]:
        r["pnl_pct"] = -0.6
    manifest = {"path": "m.json", "available": True,
                "pods": [{"id": "POD-A", "status": "pre_registered",
                          "strategies": ["s1"], "asset_classes": ["CRYPTO"],
                          "directions": ["LONG"]}]}
    gated = T.build_report(rows, "x.json", None, confirmatory=manifest,
                           require_alpha=True)
    assert all(c["verdict"] != "PROVEN_T2" for c in gated["cells"])


def test_alpha_passthrough_constant_is_defined():
    assert isinstance(T.ALPHA_PASSTHROUGH_KEYS, tuple)
    assert "covered" in T.ALPHA_PASSTHROUGH_KEYS
