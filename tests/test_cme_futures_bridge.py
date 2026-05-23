"""Tests for copy_trader_intel/cme_futures_bridge.py"""
import json
import os
import time
from pathlib import Path

import pytest

from copy_trader_intel import cme_futures_bridge as bridge


def _write(path: Path, content) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content)
    else:
        path.write_text(json.dumps(content))


def _read_dest(dest: Path) -> dict:
    return json.loads(dest.read_text())


@pytest.fixture
def paths(tmp_path):
    src = tmp_path / "src" / "futures_picks.json"
    dst = tmp_path / "dst" / "futures_copytrader_picks.json"
    return src, dst


def test_empty_list_input(paths):
    src, dst = paths
    _write(src, [])
    out = bridge.run(source_path=src, dest_path=dst)
    assert out == []
    payload = _read_dest(dst)
    assert payload["picks"] == []
    assert "generated_at" in payload


def test_list_shape_input(paths):
    src, dst = paths
    _write(src, [
        {"symbol": "ES", "signal_type": "BUY", "confidence": 0.7, "strategy": "tsmom"},
        {"symbol": "NQ", "direction": "SHORT", "confidence": 0.6},
    ])
    out = bridge.run(source_path=src, dest_path=dst)
    assert len(out) == 2
    syms = {p["symbol"] for p in out}
    assert syms == {"ES", "NQ"}
    # SHORT -> SELL normalization
    nq = next(p for p in out if p["symbol"] == "NQ")
    assert nq["signal_type"] == "SELL"
    assert nq["direction"] == "SHORT"


def test_dict_with_picks_shape(paths):
    src, dst = paths
    _write(src, {
        "agent": "futures",
        "timestamp": "2026-05-22T12:00:00",
        "picks": [{"symbol": "CL", "signal_type": "BUY", "confidence": 0.55}],
    })
    out = bridge.run(source_path=src, dest_path=dst)
    assert len(out) == 1
    assert out[0]["symbol"] == "CL"


def test_stale_source_emits_empty(paths, monkeypatch):
    src, dst = paths
    _write(src, [{"symbol": "ES", "signal_type": "BUY", "confidence": 0.7}])
    # Backdate mtime by 72h
    old = time.time() - 72 * 3600
    os.utime(src, (old, old))
    out = bridge.run(source_path=src, dest_path=dst)
    assert out == []
    payload = _read_dest(dst)
    assert payload["picks"] == []


def test_missing_source_no_crash(paths):
    src, dst = paths
    # src does NOT exist
    out = bridge.run(source_path=src, dest_path=dst)
    assert out == []
    payload = _read_dest(dst)
    assert payload["picks"] == []
    assert "generated_at" in payload


def test_malformed_json_no_crash(paths):
    src, dst = paths
    _write(src, "{not valid json,,,")
    out = bridge.run(source_path=src, dest_path=dst)
    assert out == []
    payload = _read_dest(dst)
    assert payload["picks"] == []


def test_pick_missing_asset_class_defaults_to_futures(paths):
    src, dst = paths
    _write(src, {"picks": [
        {"symbol": "ZN", "signal_type": "BUY", "confidence": 0.65},
    ]})
    out = bridge.run(source_path=src, dest_path=dst)
    assert len(out) == 1
    assert out[0]["asset_class"] == "FUTURES"
    assert out[0]["source_system"] == "futures_tsmom_elite"


def test_generated_at_present(paths):
    src, dst = paths
    _write(src, [])
    bridge.run(source_path=src, dest_path=dst)
    payload = _read_dest(dst)
    assert "generated_at" in payload
    assert payload["generated_at"]  # non-empty


def test_drops_picks_missing_required_fields(paths):
    src, dst = paths
    _write(src, [
        {"symbol": "ES", "signal_type": "BUY", "confidence": 0.7},   # good
        {"symbol": "", "signal_type": "BUY", "confidence": 0.7},      # no symbol
        {"symbol": "NQ", "signal_type": "WHATEVER", "confidence": 0.7},  # bad dir
        {"symbol": "CL", "signal_type": "BUY"},                       # no confidence
        "not-a-dict",                                                  # bad type
    ])
    out = bridge.run(source_path=src, dest_path=dst)
    assert len(out) == 1
    assert out[0]["symbol"] == "ES"


def test_atomic_write_no_partial_on_failure(paths, monkeypatch):
    src, dst = paths
    _write(src, [{"symbol": "ES", "signal_type": "BUY", "confidence": 0.7}])
    # First successful write
    bridge.run(source_path=src, dest_path=dst)
    first = dst.read_text()
    # Now simulate failure mid-write by monkeypatching os.replace
    def boom(*a, **k):
        raise OSError("simulated replace failure")
    monkeypatch.setattr(bridge.os, "replace", boom)
    with pytest.raises(OSError):
        bridge.run(source_path=src, dest_path=dst)
    # Original file untouched
    assert dst.read_text() == first
    # No leftover *.tmp files
    leftovers = [p for p in dst.parent.iterdir() if p.name.startswith(dst.name + ".")]
    assert leftovers == []
