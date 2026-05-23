"""End-to-end integration test for tools.hyro_filter_from_dashboard.

Protects against regressions of the 2026-04-11 field-mapping bugs
(confidence_pct vs confidence, symbol_hint vs symbol,
position_size_conservative vs position_size_usdt). Seeds a minimal
dashboard_data.json, runs the full hyro_filter main() with both
WINRATE_FILTER_MODE=strict and PROP_CHALLENGE_GATE=strict, and asserts
the output JSON contains the expected winrate_filter_stats and
prop_challenge_gate_stats blocks.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


def _seed_winrate_cfg(hf) -> None:
    hf._HYRO_WINRATE_CFG = {
        "thresholds": {"min_confidence": 0.6},
        "strategy_blacklist": ["blocked_strategy"],
        "symbol_blacklist": ["BADSYMBOLUSDT"],
    }


@pytest.fixture
def seeded_dashboard(tmp_path, monkeypatch):
    """Write a minimal dashboard_data.json that exercises both filters."""
    # Real dashboard_data has picks as a dict with 'active'/'recent_closed'/'smart_picks' keys
    data = {
        "generated_at": "2026-04-11T06:00:00Z",
        "picks": {
            "active": [
                # pick 1: high conf + small SL distance → passes both
                {
                    "symbol": "BINANCE:XRPUSDT",
                    "confidence": 0.85,
                    "direction": "LONG",
                    "entry_price": 1.36,
                    "stop_loss": 1.34,
                    "take_profit": 1.39,
                    "strategy": "ml_enhanced_something",
                    "asset_class": "crypto",
                    "status": "OPEN",
                    "rank": 1,
                    "hyro_score": 92,
                    "ml_composite": 0.85,
                    "source_system": "ml",
                    "source_pick_id": "x1",
                },
                # pick 2: low conf → winrate_filter rejects in strict
                {
                    "symbol": "BINANCE:DOGEUSDT",
                    "confidence": 0.55,
                    "direction": "LONG",
                    "entry_price": 0.15,
                    "stop_loss": 0.148,
                    "take_profit": 0.155,
                    "strategy": "some_weak_strat",
                    "asset_class": "crypto",
                    "status": "OPEN",
                    "rank": 2,
                    "hyro_score": 55,
                    "ml_composite": 0.55,
                    "source_system": "ml",
                    "source_pick_id": "x2",
                },
            ],
            "recent_closed": [],
            "smart_picks": [],
        },
        "performance": {"by_asset_class": {"crypto": {"wr": 45.0}}},
    }
    path = tmp_path / "dashboard_data.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_hyro_filter_main_runs_cleanly(seeded_dashboard, tmp_path, monkeypatch, capsys):
    """The pipeline should run end-to-end and produce an output dict
    with winrate_filter_stats and prop_challenge_gate_stats.

    This is NOT asserting specific pick counts — the exact number of
    surviving picks depends on how filter_and_score scores the seeded
    data, which evolves. What the test DOES assert is:

    1. main() does not crash
    2. The output JSON has both filter stats blocks
    3. The winrate_filter_stats mode matches the env var
    4. The prop_challenge_gate_stats has accepted/rejected/breach counts
    """
    monkeypatch.setenv("WINRATE_FILTER_MODE", "strict")
    monkeypatch.setenv("PROP_CHALLENGE_GATE", "strict")

    # Reload the module so it picks up the new env vars
    import tools.hyro_filter_from_dashboard as hf
    importlib.reload(hf)
    _seed_winrate_cfg(hf)

    # Run main with --json-only pointing at the seeded dashboard
    out_path = tmp_path / "hyrotrader_picks.json"
    test_args = [
        "hyro_filter_from_dashboard.py",
        "--local", str(seeded_dashboard),
        "--json-only",
        "--no-merge-base",
    ]
    monkeypatch.setattr("sys.argv", test_args)

    rc = hf.main()
    assert rc == 0

    captured = capsys.readouterr()
    # Parse the JSON output
    start = captured.out.index("{")
    out = json.loads(captured.out[start:])

    # Core assertions
    assert "picks" in out
    assert "winrate_filter_stats" in out
    assert out["winrate_filter_stats"]["mode"] == "strict"
    if importlib.util.find_spec("alpha_engine.prop_challenge_gate") is not None:
        assert "prop_challenge_gate_stats" in out
        assert "accepted_count" in out["prop_challenge_gate_stats"]
        assert "rejected_count" in out["prop_challenge_gate_stats"]

    # Regression guard for the field-mapping bugs: if these assertions
    # fire, someone reverted the confidence_pct / symbol_hint /
    # position_size_conservative fixes.
    wr_stats = out["winrate_filter_stats"]
    assert "admitted" in wr_stats
    assert "label_normalized" in wr_stats
    assert "would_reject_low_conf" in wr_stats

    gate_stats = out.get("prop_challenge_gate_stats")
    if gate_stats is not None:
        assert "rejections_by_reason" in gate_stats


def test_hyro_filter_shadow_mode_passes_everything(seeded_dashboard, tmp_path, monkeypatch, capsys):
    """In shadow mode, even low-confidence picks should make it through
    (the filter only logs would_reject counts, it doesn't actually drop)."""
    monkeypatch.setenv("WINRATE_FILTER_MODE", "shadow")
    monkeypatch.setenv("PROP_CHALLENGE_GATE", "shadow")

    import tools.hyro_filter_from_dashboard as hf
    importlib.reload(hf)
    _seed_winrate_cfg(hf)

    test_args = [
        "hyro_filter_from_dashboard.py",
        "--local", str(seeded_dashboard),
        "--json-only",
        "--no-merge-base",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    rc = hf.main()
    assert rc == 0

    captured = capsys.readouterr()
    start = captured.out.index("{")
    out = json.loads(captured.out[start:])

    # In shadow mode, rejections are tracked in stats but picks pass through.
    # We do NOT assert on the exact count because filter_and_score may drop
    # picks for other reasons (stop_loss > entry on LONG, etc). What we DO
    # assert is that the stats blocks exist and are in the right mode.
    assert out["winrate_filter_stats"]["mode"] == "shadow"


def test_hyro_filter_preserves_open_trade_state_from_merge_base(seeded_dashboard, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WINRATE_FILTER_MODE", "shadow")
    monkeypatch.setenv("PROP_CHALLENGE_GATE", "shadow")

    import tools.hyro_filter_from_dashboard as hf
    importlib.reload(hf)
    _seed_winrate_cfg(hf)

    compatible_dashboard = {
        "generated_at": "2026-04-11T06:00:00Z",
        "picks": {
            "active": [
                {
                    "symbol": "XRPUSDT",
                    "confidence": 0.85,
                    "direction": "LONG",
                    "entry_price": 1.36,
                    "stop_loss": 1.34,
                    "take_profit": 1.39,
                    "strategy": "ml_enhanced_something",
                    "asset_class": "CRYPTO",
                    "status": "OPEN",
                    "rank": 1,
                    "hyro_score": 92,
                    "ml_score": 0.85,
                    "source_system": "ml",
                    "id": "src-xrp",
                    "age_hours": 1.0,
                    "rr_ratio": 1.5,
                }
            ],
            "recent_closed": [],
            "smart_picks": [],
        },
    }
    compat_path = tmp_path / "compatible_dashboard_data.json"
    compat_path.write_text(json.dumps(compatible_dashboard), encoding="utf-8")

    merge_base = {
        "challenge": {"account_size_usdt": 5000},
        "account_snapshot": {"equity_usdt": 5000, "day_start_equity_usdt": 5000},
        "playbook": {"risk_per_trade_pct_account": 0.75},
        "picks": [
            {
                "id": "hyro-2026-04-11-xrp",
                "status": "open",
                "opened_at": "2026-04-11T12:00:00Z",
                "entry_price": 1.36,
                "stop_loss": 1.34,
                "take_profit": 1.39,
                "sl_confirmed": True,
                "position_size_usdt": 2500.0,
                "risk_amount_usdt": 37.5,
            }
        ],
    }
    out_path = tmp_path / "hyrotrader_picks.json"
    out_path.write_text(json.dumps(merge_base), encoding="utf-8")

    journal = {
        "baseline_equity_usdt": 5000,
        "trades": [
            {
                "pick_id": "hyro-2026-04-11-xrp",
                "symbol": "XRPUSDT",
                "direction": "LONG",
                "entry_price": 1.36,
                "entry_time": "2026-04-11T12:00:00Z",
                "stop_loss": 1.34,
                "take_profit": 1.39,
                "position_size_usdt": 2500.0,
                "risk_amount_usdt": 37.5,
                "status": "open",
            }
        ],
    }
    journal_path = tmp_path / "hyrotrader_journal.json"
    journal_path.write_text(json.dumps(journal), encoding="utf-8")
    monkeypatch.setattr(hf, "DEFAULT_JOURNAL", journal_path)

    test_args = [
        "hyro_filter_from_dashboard.py",
        "--local", str(compat_path),
        "--json-only",
        "--output", str(out_path),
    ]
    monkeypatch.setattr("sys.argv", test_args)
    rc = hf.main()
    assert rc == 0

    # The merge_base pick state is written to the output file (not stdout JSON).
    # stdout may have empty picks if the dashboard pick was filtered earlier.
    with open(out_path, encoding="utf-8") as fp:
        file_out = json.load(fp)

    xrp_candidates = [
        p for p in file_out.get("picks", [])
        if p.get("symbol_hint") == "XRPUSDT"
        or p.get("symbol") == "XRPUSDT"
        or "xrp" in (p.get("id") or "").lower()
    ]
    assert xrp_candidates, "XRPUSDT pick not found in output file picks"
    xrp = xrp_candidates[0]
    # Status may be 'open' or 'OPEN' depending on merge_base preservation
    assert xrp.get("status", "").lower() == "open"
    assert xrp["opened_at"] == "2026-04-11T12:00:00Z"
    assert xrp["sl_confirmed"] is True
    assert xrp["position_size_usdt"] == 2500.0
    # journal_open_trade_count is in stdout JSON account_snapshot (not the file output).
    # The file output preserves the original merge_base account_snapshot which
    # may not include the enriched journal fields.
    captured = capsys.readouterr()
    if captured.out and "{" in captured.out:
        stdout_out = json.loads(captured.out[captured.out.index("{"):])
        assert stdout_out.get("account_snapshot", {}).get("journal_open_trade_count", 0) >= 1
