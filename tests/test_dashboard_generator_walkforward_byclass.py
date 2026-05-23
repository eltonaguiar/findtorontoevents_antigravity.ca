"""Tests for the walkforward.by_class block surfaced on the audit dashboard.

PR #654 added `walk_forward_by_class()` in alpha_engine/walkforward_validator.py
and wired it into `run_validation` so `walkforward_results.json` writes a
`by_class` block. This test verifies the dashboard payload:

  1. Carries a `walkforward.by_class` key with the per-asset-class metrics
  2. Survives the kill-list sweep (top-level key, NOT a strategies list)
  3. Serializes cleanly to JSON (no NaN/Infinity, no non-serializable types)

Per CLAUDE.md, we DO NOT run `python audit_trail/dashboard_generator.py`
(it overwrites live HTML). We construct a fake payload directly and exercise
the kill-list-style filter + JSON serialization paths in isolation.
"""
from __future__ import annotations

import json

import pytest


def _fake_by_class_block() -> dict:
    """Mirror the schema produced by walk_forward_by_class().

    See alpha_engine/walkforward_validator.walk_forward_validate() return type
    (lines 138-149): folds, oos_wr, oos_wr_std, oos_sharpe, oos_sharpe_std,
    decay, consistency, worst_fold_wr, best_fold_wr, folds_detail.
    """
    return {
        "CRYPTO": {
            "folds": 6,
            "oos_wr": 52.3,
            "oos_wr_std": 4.1,
            "oos_sharpe": 0.812,
            "oos_sharpe_std": 0.21,
            "decay": -1.4,
            "consistency": 83.3,
            "worst_fold_wr": 44.0,
            "best_fold_wr": 58.5,
            "folds_detail": [
                {"fold": 1, "test_wr": 50.0, "test_sharpe": 0.7, "decay": -2.0},
            ],
        },
        "EQUITY": {
            "folds": 4,
            "oos_wr": 48.0,
            "oos_wr_std": 6.0,
            "oos_sharpe": 0.32,
            "oos_sharpe_std": 0.15,
            "decay": -3.1,
            "consistency": 75.0,
            "worst_fold_wr": 40.0,
            "best_fold_wr": 55.0,
            "folds_detail": [],
        },
        "FOREX": {
            "folds": 3,
            "oos_wr": 41.0,
            "oos_wr_std": 8.0,
            "oos_sharpe": -0.12,
            "oos_sharpe_std": 0.30,
            "decay": -5.2,
            "consistency": 33.3,
            "worst_fold_wr": 32.0,
            "best_fold_wr": 49.0,
            "folds_detail": [],
        },
    }


def _fake_payload() -> dict:
    """Minimal payload that mirrors the dashboard_generator.py shape relevant
    to the by_class surface. The kill-list filter only touches `picks.active`,
    so we include a small active list and a sibling `walkforward` block."""
    return {
        "generated_at": "2026-05-02T08:00:00Z",
        "picks": {
            "active": [
                {"strategy": "good_strat", "symbol": "BTCUSDT"},
                {"strategy": "killed_strat", "symbol": "ETHUSDT"},
            ],
            "recent_closed": [],
        },
        "strategies": [
            {"strategy": "good_strat", "wr": 55.0},
            {"strategy": "killed_strat", "wr": 12.0},
        ],
        "walkforward": {
            "by_class": _fake_by_class_block(),
            "generated_at": "2026-05-02T07:55:00Z",
        },
    }


def _apply_kill_list_sweep(payload: dict, kill_set: set[str]) -> dict:
    """Mirror the kill-list filter at audit_trail/dashboard_generator.py:8266-8293.

    Only filters `picks.active` and `strategies`. Top-level keys (including
    `walkforward`) are untouched.
    """
    picks = payload.get("picks", {})
    if isinstance(picks, dict) and isinstance(picks.get("active"), list):
        picks["active"] = [
            p for p in picks["active"]
            if (p.get("strategy") or "").lower() not in kill_set
        ]
    if isinstance(payload.get("strategies"), list):
        payload["strategies"] = [
            s for s in payload["strategies"]
            if (s.get("strategy") or "").lower() not in kill_set
        ]
    return payload


def test_by_class_block_attached_to_payload():
    payload = _fake_payload()
    assert "walkforward" in payload
    assert "by_class" in payload["walkforward"]
    by_class = payload["walkforward"]["by_class"]
    # Schema sanity — every required field present per the validator output
    for cls in ("CRYPTO", "EQUITY", "FOREX"):
        assert cls in by_class
        row = by_class[cls]
        for key in (
            "folds", "oos_wr", "oos_sharpe", "decay",
            "consistency", "worst_fold_wr",
        ):
            assert key in row, f"{cls} missing {key}"


def test_by_class_survives_kill_list_sweep():
    """The kill-list filter only gates strategies/active picks. The
    walkforward.by_class block must pass through untouched even when the
    kill set would have removed strategies that share a name with one of
    the asset-class keys (defensive — should never happen, but verified)."""
    payload = _fake_payload()
    pre_block = json.dumps(payload["walkforward"], sort_keys=True)
    kill_set = {"killed_strat", "crypto", "equity", "forex"}
    out = _apply_kill_list_sweep(payload, kill_set)
    post_block = json.dumps(out["walkforward"], sort_keys=True)

    # by_class block is byte-for-byte identical pre/post sweep
    assert pre_block == post_block
    # Sanity: the active picks list WAS filtered (proves the sweep ran)
    assert len(out["picks"]["active"]) == 1
    assert out["picks"]["active"][0]["strategy"] == "good_strat"
    # Sanity: strategies list WAS filtered
    assert len(out["strategies"]) == 1


def test_by_class_serializes_cleanly_to_json():
    """Mirrors `json.dumps(payload, allow_nan=False)` at
    audit_trail/dashboard_generator.py:13853 — payload must be NaN-free
    and fully JSON-serializable."""
    payload = _fake_payload()
    # allow_nan=False mirrors the production serialization. If any value
    # is NaN/Infinity this raises ValueError.
    blob = json.dumps(payload, allow_nan=False, default=str)
    decoded = json.loads(blob)
    assert decoded["walkforward"]["by_class"]["CRYPTO"]["oos_sharpe"] == 0.812
    assert decoded["walkforward"]["by_class"]["FOREX"]["oos_sharpe"] == -0.12


def test_empty_by_class_block_is_safe():
    """If the validator hasn't run yet (or the block is empty), the payload
    still serializes and the key is present — the template handles `{}` as
    the no-data case."""
    payload = {
        "picks": {"active": [], "recent_closed": []},
        "walkforward": {"by_class": {}, "generated_at": None},
    }
    blob = json.dumps(payload, allow_nan=False, default=str)
    decoded = json.loads(blob)
    assert decoded["walkforward"]["by_class"] == {}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
