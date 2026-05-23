"""Tests for MAX_CONCURRENT_PER_SYMBOL cap + entry_time/timestamp backfill in
``alpha_engine.isolated_signal_integrator.integrate_isolated_signals``.

Per 4-AI panel P0 verdict (2026-04-29):
- ``reports/doge_cluster_investigation_2026_04_29.md``
- ``reports/findings_validation_synthesis_2026_04_29.md`` (Finding 2 + Finding 5)

Mechanism this guards against: ``quan_engine_scalp`` produced 272
strategy*symbol*day clusters with >=8 concurrent stacked positions, totaling
5,293 closes / -960% sum pnl_pct. Worst: KASUSDT 79x on 2026-03-26 (-17.90%).
Stacked LONGs all hit SL in the same price band when the resolver sweeps.

Default ``MAX_CONCURRENT_PER_SYMBOL=0`` means UNCAPPED (back-compat). Setting
to a positive integer enables the per (source_system, symbol) gate.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "alpha_engine"))


@pytest.fixture
def integrator(monkeypatch, tmp_path):
    """Import / re-import the integrator module with REPO_ROOT redirected to a
    temp dir so we can stage fake quan_engine source files without touching
    the real repo data.
    """
    # Create a fake quan_engine source file with two raw picks for the same
    # symbol+direction. We can't rely on REPO_ROOT (parent of alpha_engine)
    # because the integrator resolves it from __file__. Instead we monkeypatch
    # the module attribute after import.
    import isolated_signal_integrator as iso  # noqa: E402  imported lazily

    importlib.reload(iso)
    monkeypatch.setattr(iso, "REPO_ROOT", tmp_path)
    return iso


def _stage_quan_source(tmp_path: Path, picks: list[dict]) -> None:
    """Write fake ``quan_engine/data/active_signals.json`` under ``tmp_path``.

    The integrator reads ``quan_engine/data/active_signals.json`` (the first
    SOURCES entry) with json key ``active_picks``.
    """
    target = tmp_path / "quan_engine" / "data" / "active_signals.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"active_picks": picks}))


def _make_quan_pick(symbol: str, direction: str = "LONG", entry: float = 1.0,
                     seed: str = "") -> dict:
    """Minimal raw quan_engine pick that survives the integrator's quality
    gates (CRYPTO USDT symbol, confidence >= 0.50, ACTIVE status).
    The ``seed`` field is just used to make confidence values vary across
    picks — the dedup key is (symbol, direction) so two raw picks for the
    same pair end up needing the concurrency cap to gate them.

    Uses quan_engine_position (not quan_engine_scalp which is retired)
    so picks survive the blocklist gate.
    """
    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry,
        "take_profit": entry * 1.005,
        "stop_loss": entry * 0.993,
        "confidence": 0.65,
        "strategies_agreed": ["quan_engine_position"],
        "mode": "position",
        "status": "ACTIVE",
        # entry_time intentionally omitted to test the backfill.
        "_seed": seed,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConcurrencyCapDefaultOff:
    def test_default_env_unset_means_uncapped(self, integrator, tmp_path,
                                              monkeypatch):
        """With MAX_CONCURRENT_PER_SYMBOL unset, behavior is unchanged.
        Two raw quan picks for different (symbol, direction) keys both pass.
        """
        monkeypatch.delenv("MAX_CONCURRENT_PER_SYMBOL", raising=False)
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "LONG", 50000.0, seed="a"),
            _make_quan_pick("ETHUSDT", "LONG", 3000.0, seed="b"),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=[])
        assert len(out) == 2

    def test_explicit_zero_means_uncapped(self, integrator, tmp_path,
                                          monkeypatch):
        """MAX_CONCURRENT_PER_SYMBOL=0 is the documented opt-out value."""
        monkeypatch.setenv("MAX_CONCURRENT_PER_SYMBOL", "0")
        # Existing pick: 1 BTCUSDT quan_engine LONG already active.
        existing = [{
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "source_system": "quan_engine",
            "status": "ACTIVE",
        }]
        # New pick for ETHUSDT (different dedup key) should still pass even
        # though existing has 1 BTCUSDT open — uncapped.
        _stage_quan_source(tmp_path, [
            _make_quan_pick("ETHUSDT", "LONG", 3000.0, seed="z"),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=existing)
        assert len(out) == 1
        assert out[0]["symbol"] == "ETHUSDT"

    def test_garbage_env_means_uncapped(self, integrator, tmp_path,
                                        monkeypatch):
        """Non-numeric env value should fail-safe to uncapped, not crash."""
        monkeypatch.setenv("MAX_CONCURRENT_PER_SYMBOL", "not-a-number")
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "LONG", 50000.0),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=[])
        assert len(out) == 1


class TestConcurrencyCapEnforced:
    def test_cap_blocks_when_existing_at_limit(self, integrator, tmp_path,
                                               monkeypatch):
        """With cap=1 and 1 existing open BTCUSDT quan_engine LONG, a new
        BTCUSDT SHORT pick from quan_engine must be blocked (same source+symbol).
        """
        monkeypatch.setenv("MAX_CONCURRENT_PER_SYMBOL", "1")
        existing = [{
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "source_system": "quan_engine",
            "status": "ACTIVE",
        }]
        # Stage a SHORT raw pick — different dedup key from existing (LONG),
        # so dedup wouldn't catch it. Only the concurrency cap should.
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "SHORT", 50000.0),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=existing)
        assert out == [], (
            "MAX_CONCURRENT_PER_SYMBOL=1 should reject a 2nd quan_engine "
            "BTCUSDT pick when 1 is already open"
        )

    def test_cap_2_allows_one_more_when_one_existing(self, integrator,
                                                    tmp_path, monkeypatch):
        """With cap=2 and 1 existing BTCUSDT quan_engine open, exactly one
        new quan_engine BTCUSDT pick (SHORT) is allowed, but a 3rd would not be.
        """
        monkeypatch.setenv("MAX_CONCURRENT_PER_SYMBOL", "2")
        existing = [{
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "source_system": "quan_engine",
            "status": "ACTIVE",
        }]
        # Two new SHORT raw picks — dedup key (BTCUSDT, SHORT) collapses
        # them, but if we also include a different dedup direction we can
        # only fit one more under cap=2 (1 existing + 1 new = 2).
        # Use one SHORT (passes dedup against existing LONG) + one second
        # SHORT (would dedup against itself, so we only stage one).
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "SHORT", 50000.0),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=existing)
        assert len(out) == 1
        assert out[0]["symbol"] == "BTCUSDT"
        assert out[0]["direction"] == "SHORT"

    def test_cap_only_counts_open_status(self, integrator, tmp_path,
                                         monkeypatch):
        """A CLOSED existing pick should not count toward the cap."""
        monkeypatch.setenv("MAX_CONCURRENT_PER_SYMBOL", "1")
        existing = [{
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "source_system": "quan_engine",
            "status": "CLOSED",  # already closed — does not occupy a slot
        }]
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "SHORT", 50000.0),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=existing)
        assert len(out) == 1, (
            "Closed picks must not count toward MAX_CONCURRENT_PER_SYMBOL"
        )

    def test_cap_is_per_source_not_global(self, integrator, tmp_path,
                                          monkeypatch):
        """Cap is scoped per (source_system, symbol). A genome BTCUSDT being
        open should NOT block a quan_engine BTCUSDT (different source).
        """
        monkeypatch.setenv("MAX_CONCURRENT_PER_SYMBOL", "1")
        existing = [{
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "source_system": "genome",  # different source
            "status": "ACTIVE",
        }]
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "SHORT", 50000.0),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=existing)
        # genome's open BTCUSDT does not count against quan_engine's cap.
        assert len(out) == 1
        assert out[0]["source_system"] == "quan_engine"


class TestEntryTimeBackfill:
    def test_entry_time_and_timestamp_populated(self, integrator, tmp_path,
                                                monkeypatch):
        """Every emitted pick must have entry_time + timestamp set, even
        when MAX_CONCURRENT_PER_SYMBOL is unset (Finding 5 fix is
        unconditional).
        """
        monkeypatch.delenv("MAX_CONCURRENT_PER_SYMBOL", raising=False)
        _stage_quan_source(tmp_path, [
            _make_quan_pick("BTCUSDT", "LONG", 50000.0),
        ])
        out = integrator.integrate_isolated_signals(existing_picks=[])
        assert len(out) == 1
        pick = out[0]
        assert pick.get("entry_time"), \
            "entry_time must be backfilled at emit time (Finding 5)"
        assert pick.get("timestamp"), \
            "timestamp must be backfilled at emit time (Finding 5)"
        # Both should agree (we set them from the same _emit_ts).
        assert pick["entry_time"] == pick["timestamp"]

    def test_entry_time_preserved_when_already_set(self, integrator, tmp_path,
                                                   monkeypatch):
        """If the raw source already provides entry_time via created_at, the
        backfill should not stomp on it (uses setdefault semantics).
        """
        monkeypatch.delenv("MAX_CONCURRENT_PER_SYMBOL", raising=False)
        raw = _make_quan_pick("BTCUSDT", "LONG", 50000.0)
        # quan_engine normalizer takes created_at from raw["entry_time"].
        raw["entry_time"] = "2026-04-01T12:00:00Z"
        _stage_quan_source(tmp_path, [raw])
        out = integrator.integrate_isolated_signals(existing_picks=[])
        assert len(out) == 1
        # The created_at field carries the original timestamp through
        # _normalize_quan_engine, and the backfill stamps entry_time/timestamp
        # from created_at if they're missing on the normalized dict.
        assert out[0]["entry_time"] == "2026-04-01T12:00:00Z"
        assert out[0]["timestamp"] == "2026-04-01T12:00:00Z"
