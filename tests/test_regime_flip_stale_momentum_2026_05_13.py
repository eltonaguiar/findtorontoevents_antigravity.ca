"""Regression test for regime_flip_detector stale-momentum bug (2026-05-13).

Prior bug at alpha_engine/regime_flip_detector.py:458 — when
fetch_btc_momentum() returned {} on API failure, the `if momentum:` block
skipped the momentum-field writes, leaving stale RSI/ATR/drawdown values
alongside a fresh regime_last_checked timestamp. Downstream consumers
saw an asymmetrically stale report.

Fix: stamp ``momentum_fresh`` (bool) and ``momentum_last_updated`` (ISO
str or None) explicitly on every run so consumers can detect stale
momentum even when other timestamps look current.

Production evidence (2026-05-13): regime_report.json had
``regime_last_checked = 2026-05-13T19:51:45Z`` alongside ``btc_price =
70115.34`` whose source timestamp was ``2026-03-23T20:02:04Z`` — a
51-day gap. This test pins the fix so a regression would be caught.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import target module
from alpha_engine import regime_flip_detector as rfd


@pytest.fixture
def tmp_regime_report(monkeypatch, tmp_path):
    """Redirect REGIME_REPORT_PATH to a tmp file with a seeded fresh state."""
    fake = tmp_path / "regime_report.json"
    seed = {
        "regime": "CHOPPY",
        "btc_price": 90000.0,  # seed last-known-good
        "rsi_4h": 55.0,
        "atr_pct": 1.2,
        "drawdown_from_high": -5.0,
        "momentum_fresh": True,
        "momentum_last_updated": "2026-05-13T00:00:00+00:00",
    }
    fake.write_text(json.dumps(seed), encoding="utf-8")
    monkeypatch.setattr(rfd, "REGIME_REPORT_PATH", fake)
    return fake


def _fake_btc_24h_change(*args, **kwargs):
    return 0.5


def _fake_classify(*args, **kwargs):
    return "CHOPPY"


def _fake_get_regime_confidence(*args, **kwargs):
    return {"long_conf": 0.5, "short_conf": 0.5, "size_mult": 1.0}


def test_momentum_fresh_stamps_true_on_successful_fetch(tmp_regime_report, monkeypatch):
    monkeypatch.setattr(rfd, "fetch_btc_24h_change", _fake_btc_24h_change)
    monkeypatch.setattr(rfd, "classify_regime", _fake_classify)
    monkeypatch.setattr(rfd, "get_regime_confidence", _fake_get_regime_confidence)
    monkeypatch.setattr(rfd, "fetch_btc_momentum", lambda: {
        "rsi_4h": 65.0, "sma_slope": 0.1, "drawdown_from_high": -2.0,
        "price": 100000.0, "high_6bar": 105000.0, "adx": 25.0, "atr_pct": 1.5,
    })
    rfd.check_flip()
    d = json.loads(tmp_regime_report.read_text(encoding="utf-8"))
    assert d.get("momentum_fresh") is True
    assert d.get("momentum_last_updated") is not None
    assert d.get("btc_price") == 100000.0  # updated from fresh fetch
    assert d.get("rsi_4h") == 65.0


def test_momentum_fresh_stamps_false_on_api_failure(tmp_regime_report, monkeypatch):
    """API failure (empty dict) must mark momentum_fresh=False.
    Previous-run momentum_last_updated is preserved (setdefault)."""
    monkeypatch.setattr(rfd, "fetch_btc_24h_change", _fake_btc_24h_change)
    monkeypatch.setattr(rfd, "classify_regime", _fake_classify)
    monkeypatch.setattr(rfd, "get_regime_confidence", _fake_get_regime_confidence)
    monkeypatch.setattr(rfd, "fetch_btc_momentum", lambda: {})  # API failure
    rfd.check_flip()
    d = json.loads(tmp_regime_report.read_text(encoding="utf-8"))
    assert d.get("momentum_fresh") is False
    # The seed had momentum_last_updated set; setdefault preserves it.
    assert d.get("momentum_last_updated") == "2026-05-13T00:00:00+00:00"
    # Stale BTC price is retained (since the conditional skips the update);
    # consumers must check momentum_fresh BEFORE acting on btc_price.
    assert d.get("btc_price") == 90000.0


def test_momentum_last_updated_none_when_no_prior_state(tmp_path, monkeypatch):
    """Cold start + API failure: momentum_last_updated stamped as None."""
    fake = tmp_path / "regime_report.json"
    fake.write_text(json.dumps({"regime": "CHOPPY"}), encoding="utf-8")  # no momentum keys
    monkeypatch.setattr(rfd, "REGIME_REPORT_PATH", fake)
    monkeypatch.setattr(rfd, "fetch_btc_24h_change", _fake_btc_24h_change)
    monkeypatch.setattr(rfd, "classify_regime", _fake_classify)
    monkeypatch.setattr(rfd, "get_regime_confidence", _fake_get_regime_confidence)
    monkeypatch.setattr(rfd, "fetch_btc_momentum", lambda: {})
    rfd.check_flip()
    d = json.loads(fake.read_text(encoding="utf-8"))
    assert d.get("momentum_fresh") is False
    assert d.get("momentum_last_updated") is None
