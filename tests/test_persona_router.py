"""Tests for tools/swarm/persona_router.py — Phase 1 regex-only routing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Make tools/swarm importable
import sys
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "swarm"))

import persona_router as pr  # noqa: E402


@pytest.fixture
def registry():
    return pr.load_registry()


@pytest.fixture
def tmp_log(tmp_path, monkeypatch):
    log = tmp_path / "_routing_log.jsonl"
    monkeypatch.setattr(pr, "DEFAULT_LOG_PATH", log)
    return log


def test_race_condition_match(registry):
    q = (
        "User clicks the chip rapidly and applyFilters runs twice — capture-phase listener "
        "calls stopImmediatePropagation then dispatches a synthetic click. We need a mutex."
    )
    result = pr.route(q, registry)
    assert not result["fallback_used"]
    top = result["matches"][0]
    assert top["persona"] == "race-condition-specialist"
    assert top["confidence"] >= 0.5
    assert "stopImmediatePropagation" in top["matched_keywords"]
    assert "mutex" in top["matched_keywords"]


def test_forex_match(registry):
    q = "EUR/USD pip movement on a JPY-cross with a carry trade — review forex_rsi2_mean_reversion."
    result = pr.route(q, registry)
    assert not result["fallback_used"]
    assert result["matches"][0]["persona"] == "forex-specialist"


def test_crypto_match(registry):
    q = "BTCUSDT funding rate divergence on Binance perpetuals; quan_engine drag on the elite cohort."
    result = pr.route(q, registry)
    assert not result["fallback_used"]
    assert result["matches"][0]["persona"] == "crypto-specialist"


def test_generalist_fallback_on_vague_query(registry, tmp_log):
    q = "hello world"
    result = pr.route(q, registry)
    assert result["fallback_used"] is True
    assert result["matches"][0]["persona"] == "generalist-fallback"
    assert result["matches"][0]["confidence"] == 0.0
    pr.log_routing_decision(q, result, log_path=tmp_log)
    assert tmp_log.exists()
    rec = json.loads(tmp_log.read_text(encoding="utf-8").strip())
    assert rec["fallback_used"] is True
    assert rec["matched"][0]["persona"] == "generalist-fallback"


def test_dual_match_returns_both(registry):
    q = (
        "applyFilters race condition with stopImmediatePropagation and a synthetic click — "
        "but the underlying ticker is EUR/USD on a JPY-cross carry trade with a pip-level move."
    )
    result = pr.route(q, registry, top_k=3)
    assert not result["fallback_used"]
    names = [m["persona"] for m in result["matches"]]
    assert "race-condition-specialist" in names
    assert "forex-specialist" in names
    # Higher-confidence one ranks first
    assert result["matches"][0]["confidence"] >= result["matches"][-1]["confidence"]
