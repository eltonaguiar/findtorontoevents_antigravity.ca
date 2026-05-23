"""Tests for Action Item A9 -- emitter/resolver idempotency.

Proves the deterministic dedup_key guard:
  (a) a fresh closed-pick row is written through,
  (b) an identical signal re-emitted with a fresh id is blocked once,
  (c) EMITTER_DEDUP=0 disables the guard,
  plus key determinism + distinct-signal safety.

See alpha_engine/emitter_dedup.py + reports/pf_registry_2026-05-17.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.emitter_dedup import (  # noqa: E402
    compute_dedup_key,
    dedup_closed_picks,
    ensure_dedup_key,
)


def _base():
    return {
        "asset_class": "CRYPTO",
        "strategy": "dna_winner",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_time": "2026-05-17T00:00:00Z",
        "entry_price": 64000.01,
        "id": "id-A",
    }


def test_fresh_row_writes(monkeypatch):
    monkeypatch.setenv("EMITTER_DEDUP", "1")
    out, blocked = dedup_closed_picks([_base()], label="test")
    assert len(out) == 1
    assert blocked == 0
    assert out[0].get("dedup_key")  # key was stamped


def test_reemission_blocked_once(monkeypatch):
    """Re-emission gets a FRESH id + float jitter; id-dedup would miss it,
    dedup_key must still collapse it."""
    monkeypatch.setenv("EMITTER_DEDUP", "1")
    reemit = _base()
    reemit["id"] = "id-B"               # fresh id (re-emission)
    reemit["entry_price"] = 64000.0103  # float jitter, same rounded price
    out, blocked = dedup_closed_picks([_base(), reemit], label="test")
    assert len(out) == 1
    assert blocked == 1


def test_distinct_signal_not_blocked(monkeypatch):
    monkeypatch.setenv("EMITTER_DEDUP", "1")
    other = _base()
    other["symbol"] = "ETHUSDT"
    out, blocked = dedup_closed_picks([_base(), other], label="test")
    assert len(out) == 2
    assert blocked == 0


def test_env_gate_disables_guard(monkeypatch):
    monkeypatch.setenv("EMITTER_DEDUP", "0")
    reemit = _base()
    reemit["id"] = "id-B"
    out, blocked = dedup_closed_picks([_base(), reemit], label="test")
    assert len(out) == 2
    assert blocked == 0


def test_key_is_deterministic():
    assert compute_dedup_key(_base()) == compute_dedup_key(_base())


def test_ensure_dedup_key_idempotent():
    p = _base()
    k1 = ensure_dedup_key(p)
    k2 = ensure_dedup_key(p)  # already stamped -> returns same value
    assert k1 and k1 == k2 == p["dedup_key"]


def test_fail_open_on_bad_rows(monkeypatch):
    """Non-dict rows are kept untouched (fail-open per row)."""
    monkeypatch.setenv("EMITTER_DEDUP", "1")
    out, blocked = dedup_closed_picks([_base(), "not-a-dict", 42], label="test")
    assert len(out) == 3
    assert blocked == 0


if __name__ == "__main__":
    sys.exit(__import__("pytest").main([__file__, "-q"]))
