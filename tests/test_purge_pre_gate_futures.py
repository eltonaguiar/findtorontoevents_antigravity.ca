from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "purge_pre_gate_futures_closed",
    _REPO / "tools" / "purge_pre_gate_futures_closed.py",
)
assert _SPEC and _SPEC.loader
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules["purge_pre_gate_futures_closed"] = _mod
_SPEC.loader.exec_module(_mod)
should_purge_row = _mod.should_purge_row


def test_should_purge_score_band() -> None:
    assert should_purge_row(
        {"asset_class": "FUTURES", "score": 32}, also_scanner_lt55=False
    )
    assert not should_purge_row(
        {"asset_class": "FUTURES", "score": 40, "source_system": "x"},
        also_scanner_lt55=False,
    )


def test_should_purge_scanner_flag() -> None:
    assert should_purge_row(
        {
            "asset_class": "FUTURES",
            "score": 40,
            "strategy": "scanner_momo",
        },
        also_scanner_lt55=True,
    )
    assert not should_purge_row(
        {
            "asset_class": "FUTURES",
            "score": 40,
            "strategy": "scanner_momo",
        },
        also_scanner_lt55=False,
    )
