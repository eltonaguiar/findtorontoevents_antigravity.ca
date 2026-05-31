"""Tests for the AI-tournament MySQL ingest into pf_registry.

Covers:
- env unset → tournament_picks NOT loaded; source_meta records absence.
- env set + connection-failure → no rows, but source_meta entry has 'error'.
- env set + mocked cursor → rows materialize with the expected pf_registry
  shape (strategy/asset_class/symbol/direction/entry_date/_origin_file).

We mock at the pymysql import boundary inside build_pf_registry so the test
suite never touches a live DB.
"""
from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import MagicMock, patch


def _reload_build_pf_registry():
    """Reload the module under test so env-var reads bind fresh each test."""
    if "tools.build_pf_registry" in sys.modules:
        del sys.modules["tools.build_pf_registry"]
    if "tools" not in sys.modules:
        # ensure repo-root is importable in test runners that don't pre-pend it
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
    return importlib.import_module("tools.build_pf_registry")


def test_tournament_env_unset_records_absence(monkeypatch):
    monkeypatch.delenv("PF_REGISTRY_INCLUDE_TOURNAMENT_DB", raising=False)
    monkeypatch.delenv("PF_REGISTRY_INCLUDE_DB", raising=False)
    monkeypatch.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mod = _reload_build_pf_registry()
    _, source_meta = mod.load_rows()
    t_entry = next(
        (s for s in source_meta if s.get("file") == "mysql://tournament_picks"),
        None,
    )
    assert t_entry is not None
    assert t_entry["present"] is False
    assert t_entry["rows"] == 0
    assert "PF_REGISTRY_INCLUDE_TOURNAMENT_DB=1" in t_entry["note"]


def test_tournament_loader_transforms_db_rows():
    """With a mocked cursor, raw rows become pf_registry-shaped rows."""
    mod = _reload_build_pf_registry()

    fake_raw = [
        {
            "strategy_name": "deepseek_v4_pro",
            "persona_id": "deepseek_v4_pro",
            "model_id": "deepseek-v4-pro",
            "asset_class": "CRYPTO",
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 100000.0,
            "exit_price": 102000.0,
            "pnl_pct": 2.0,
            "status": "WIN",
            "submitted_at": "2026-05-25T10:00:00Z",
            "resolved_at": "2026-05-26T10:00:00Z",
            "created_at": "2026-05-25T09:55:00Z",
            "data_integrity_flag": "PERSONA_ANALYSIS",
        },
        {
            "strategy_name": None,  # fall back to persona_id
            "persona_id": "llama4_scout",
            "model_id": "meta/llama4-scout",
            "asset_class": "EQUITY",
            "symbol": "AAPL",
            "direction": "LONG",
            "entry_price": 180.0,
            "exit_price": 175.0,
            "pnl_pct": -2.8,
            "status": "LOSS",
            "submitted_at": "",  # exercises created_at fallback
            "resolved_at": "2026-05-26T10:00:00Z",
            "created_at": "2026-05-24T09:55:00Z",
            "data_integrity_flag": "PERSONA_ANALYSIS",
        },
    ]

    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = fake_raw
    fake_cursor.__enter__ = MagicMock(return_value=fake_cursor)
    fake_cursor.__exit__ = MagicMock(return_value=False)
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cursor

    fake_db_env = MagicMock()
    fake_db_env.get_stocks_creds.return_value = {"host": "x", "user": "x", "password": "x", "database": "x"}
    fake_pymysql = MagicMock()
    fake_pymysql.connect.return_value = fake_conn
    fake_pymysql.cursors.DictCursor = MagicMock()

    with patch.dict(sys.modules, {"tools.db_env": fake_db_env, "pymysql": fake_pymysql}):
        rows, meta = mod._load_tournament_picks_rows(days=90)

    assert meta["loaded"] == 2
    assert {r["strategy"] for r in rows} == {"deepseek_v4_pro", "llama4_scout"}
    assert {r["asset_class"] for r in rows} == {"CRYPTO", "EQUITY"}
    assert all(r["_origin_file"] == "mysql:tournament_picks:90d" for r in rows)
    assert all(r["entry_date"] for r in rows)  # both have non-empty entry_date
    assert all(r["status"] in ("WIN", "LOSS") for r in rows)


def test_tournament_loader_handles_connection_failure():
    mod = _reload_build_pf_registry()
    fake_db_env = MagicMock()
    fake_db_env.get_stocks_creds.side_effect = RuntimeError("no creds")
    with patch.dict(sys.modules, {"tools.db_env": fake_db_env, "pymysql": MagicMock()}):
        rows, meta = mod._load_tournament_picks_rows(days=90)
    assert rows == []
    assert meta["loaded"] == 0
    assert "connect failed" in meta["error"]
