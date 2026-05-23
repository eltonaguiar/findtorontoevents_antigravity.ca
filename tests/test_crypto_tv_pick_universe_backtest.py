"""Contract tests for TV pick-universe institutional-vector backtest artifact."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "alpha_engine" / "data" / "crypto_tv_pick_universe_backtest.json"


def test_crypto_tv_pick_universe_artifact_exists_and_schema() -> None:
    assert ART.is_file(), "run: python -m alpha_engine.backtest.crypto_tv_universe_runner"
    data = json.loads(ART.read_text(encoding="utf-8"))
    assert data.get("schema_version") is None  # file is raw runner output
    assert "generated_at" in data
    assert data.get("strategies_n") == 20
    rows = data.get("rows") or []
    errs = data.get("errors") or []
    assert len(rows) >= 400, "expected most picks × 20 strategies; got %s rows" % len(rows)
    assert isinstance(errs, list)
    assert len(errs) >= 1, "some exchange-only symbols should miss Binance 1d"
    for k in ("tv_pick", "binance_symbol", "strategy_id", "n_trades", "total_return_pct"):
        assert k in rows[0]
    sids = {r["strategy_id"] for r in rows}
    assert len(sids) == 20
