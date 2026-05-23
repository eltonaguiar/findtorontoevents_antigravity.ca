"""Tests for tools.run_ueps_pickers.sync_to_active_picks.

Closes the wire-up gap flagged in updates/2026-04-29-ueps-emit-verification.md
and updates/2026-04-29-claude-session-review.md: ueps_picks.json was emitting
n_long=30 every 4h but no caller promoted those picks into
alpha_engine/data/active_picks.json, so they never accumulated forward stats.

Insert-only semantics by design — the weekly value_screener_runner remains
authoritative for full refreshes; the 4h cron only adds new entries so
entry_price/created_at don't churn every cycle.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.run_ueps_pickers import sync_to_active_picks


def _ueps_pick(symbol: str, source_system: str = "value_screener", **overrides):
    """Build a minimal UEPS-shaped pick dict for tests."""
    pick = {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": 100.0,
        "asset_class": "EQUITY",
        "source_system": source_system,
        "strategy": "magic_formula_x_piotroski_x_acquirers",
        "status": "ACTIVE",
        "pick_type": "long_term_value",
        "holding_horizon": "3y+",
        "exit_mode": "thesis",
        "thesis": "test thesis",
        "intrinsic_value": 150.0,
        "score": 0.7,
    }
    pick.update(overrides)
    return pick


def _payload(long_picks, *, generated_at: str = "2026-04-29T17:06:33+00:00"):
    return {
        "generated_at": generated_at,
        "universe_size": 50,
        "filtered_universe_size": 50,
        "long_picks": long_picks,
        "short_picks": [],
        "swing_picks": [],
        "summary": {"n_long": len(long_picks), "n_short": 0, "n_swing": 0},
    }


def test_sync_inserts_new_long_picks_into_empty_ledger(tmp_path):
    path = tmp_path / "active_picks.json"
    payload = _payload([_ueps_pick("ADBE"), _ueps_pick("MSFT")])

    inserted = sync_to_active_picks(payload, active_picks_path=path)

    assert inserted == 2
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    symbols = {p["symbol"] for p in data}
    assert symbols == {"ADBE", "MSFT"}
    assert all(p.get("pick_type") == "long_term_value" for p in data)


def test_sync_dedupes_by_symbol_and_source_system(tmp_path):
    path = tmp_path / "active_picks.json"
    path.write_text(json.dumps([_ueps_pick("ADBE", entry_price=200.0)]), encoding="utf-8")

    inserted = sync_to_active_picks(
        _payload([_ueps_pick("ADBE", entry_price=999.0), _ueps_pick("MSFT")]),
        active_picks_path=path,
    )

    assert inserted == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    adbe = [p for p in data if p["symbol"] == "ADBE"]
    assert len(adbe) == 1, "ADBE should not be duplicated"
    assert adbe[0]["entry_price"] == 200.0, "existing ADBE entry_price must be preserved"


def test_sync_preserves_non_ueps_entries(tmp_path):
    path = tmp_path / "active_picks.json"
    path.write_text(
        json.dumps([
            {"symbol": "DOTUSDT", "direction": "SHORT", "pick_type": "scalp",
             "asset_class": "CRYPTO", "source_system": "genome", "status": "ACTIVE"},
            {"symbol": "BTCUSDT", "direction": "LONG", "asset_class": "CRYPTO",
             "source_system": "luxalgo", "status": "ACTIVE"},
        ]),
        encoding="utf-8",
    )

    sync_to_active_picks(_payload([_ueps_pick("ADBE")]), active_picks_path=path)

    data = json.loads(path.read_text(encoding="utf-8"))
    symbols = {p["symbol"] for p in data}
    assert symbols == {"DOTUSDT", "BTCUSDT", "ADBE"}


def test_sync_enriches_picks_with_created_at_and_id(tmp_path):
    path = tmp_path / "active_picks.json"
    payload = _payload([_ueps_pick("ADBE")], generated_at="2026-04-29T17:06:33+00:00")

    sync_to_active_picks(payload, active_picks_path=path)

    data = json.loads(path.read_text(encoding="utf-8"))
    adbe = next(p for p in data if p["symbol"] == "ADBE")
    assert adbe["created_at"] == "2026-04-29T17:06:33+00:00"
    assert adbe["id"] == "ueps_value_screener_ADBE"


def test_sync_does_not_overwrite_pre_existing_created_at(tmp_path):
    path = tmp_path / "active_picks.json"
    pre = _ueps_pick("ADBE")
    pre["created_at"] = "2026-01-01T00:00:00+00:00"
    pre["id"] = "ueps_value_screener_ADBE"
    path.write_text(json.dumps([pre]), encoding="utf-8")

    sync_to_active_picks(_payload([_ueps_pick("ADBE")]), active_picks_path=path)

    data = json.loads(path.read_text(encoding="utf-8"))
    adbe = next(p for p in data if p["symbol"] == "ADBE")
    assert adbe["created_at"] == "2026-01-01T00:00:00+00:00"


def test_sync_handles_missing_file(tmp_path):
    path = tmp_path / "subdir" / "active_picks.json"
    inserted = sync_to_active_picks(_payload([_ueps_pick("ADBE")]), active_picks_path=path)
    assert inserted == 1
    assert path.exists()


def test_sync_handles_dict_wrapper_shape(tmp_path):
    path = tmp_path / "active_picks.json"
    path.write_text(
        json.dumps({"picks": [], "version": 1, "last_updated": "old-ts"}),
        encoding="utf-8",
    )

    sync_to_active_picks(_payload([_ueps_pick("ADBE")]), active_picks_path=path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data["version"] == 1
    assert len(data["picks"]) == 1
    assert data["picks"][0]["symbol"] == "ADBE"


def test_sync_skips_picks_with_no_symbol(tmp_path):
    path = tmp_path / "active_picks.json"
    payload = _payload([
        _ueps_pick("ADBE"),
        {"direction": "LONG", "entry_price": 50.0, "source_system": "value_screener"},
    ])

    inserted = sync_to_active_picks(payload, active_picks_path=path)

    assert inserted == 1


def test_sync_promotes_short_and_swing_picks_too(tmp_path):
    path = tmp_path / "active_picks.json"
    short_pick = {
        "symbol": "TSLA", "direction": "SHORT", "entry_price": 250.0,
        "asset_class": "EQUITY", "source_system": "short_side_screener",
        "strategy": "beneish_altman_sloan", "status": "ACTIVE",
        "pick_type": "short", "score": 0.6,
    }
    payload = _payload([_ueps_pick("ADBE")])
    payload["short_picks"] = [short_pick]

    inserted = sync_to_active_picks(payload, active_picks_path=path)

    assert inserted == 2
    data = json.loads(path.read_text(encoding="utf-8"))
    symbols = {p["symbol"] for p in data}
    assert symbols == {"ADBE", "TSLA"}


def test_main_calls_sync_after_write(monkeypatch, tmp_path):
    """End-to-end: main() should write ueps_picks.json AND sync to active_picks.json."""
    from tools import run_ueps_pickers

    fake_payload = _payload([_ueps_pick("ADBE"), _ueps_pick("MSFT")])

    def fake_run_screeners(universe, **kwargs):
        return fake_payload

    monkeypatch.setattr(run_ueps_pickers, "run_screeners", fake_run_screeners)

    ueps_path = tmp_path / "ueps_picks.json"
    active_path = tmp_path / "active_picks.json"

    rc = run_ueps_pickers.main([
        "--universe", "ADBE", "MSFT",
        "--output", str(ueps_path),
        "--active-picks-output", str(active_path),
    ])

    assert rc == 0
    assert ueps_path.exists()
    assert active_path.exists()
    active = json.loads(active_path.read_text(encoding="utf-8"))
    symbols = {p["symbol"] for p in active}
    assert symbols == {"ADBE", "MSFT"}


def test_main_dry_run_skips_active_sync(monkeypatch, tmp_path):
    from tools import run_ueps_pickers

    fake_payload = _payload([_ueps_pick("ADBE")])

    def fake_run_screeners(universe, **kwargs):
        return fake_payload

    monkeypatch.setattr(run_ueps_pickers, "run_screeners", fake_run_screeners)

    ueps_path = tmp_path / "ueps_picks.json"
    active_path = tmp_path / "active_picks.json"

    rc = run_ueps_pickers.main([
        "--universe", "ADBE",
        "--output", str(ueps_path),
        "--active-picks-output", str(active_path),
        "--dry-run",
    ])

    assert rc == 0
    assert not ueps_path.exists()
    assert not active_path.exists()
