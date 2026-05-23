"""Tests for tools/backfill_pick_features.py (Fork 1 — research/sidecar).

Pure stdlib, no network, no DB. Verifies symbol resolution, regime classifier,
and that qlib factor functions are wired and bounded.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import backfill_pick_features as B  # noqa: E402


def test_to_yf_ticker_forex_futures_passthrough():
    assert B.to_yf_ticker("USDJPY=X") == "USDJPY=X"
    assert B.to_yf_ticker("CT=F") == "CT=F"


def test_to_yf_ticker_crypto_mapping():
    assert B.to_yf_ticker("BTCUSDT") == "BTC-USD"
    assert B.to_yf_ticker("MATICUSDT") == "MATIC-USD"


def test_to_yf_ticker_equity_and_unresolvable():
    assert B.to_yf_ticker("AAPL") == "AAPL"
    assert B.to_yf_ticker("") is None
    assert B.to_yf_ticker(None) is None
    assert B.to_yf_ticker("USDT") is None  # bare quote, no base


def test_classify_regime_bull():
    closes = [100 + i for i in range(40)]  # steady uptrend
    label, score = B.classify_regime(closes)
    assert label == "BULL" and score == 1


def test_classify_regime_bear():
    closes = [200 - i for i in range(40)]  # steady downtrend
    label, score = B.classify_regime(closes)
    assert label == "BEAR" and score == -1


def test_classify_regime_unknown_on_short_series():
    label, score = B.classify_regime([100, 101, 102])
    assert label == "UNKNOWN" and score == 0


def test_qlib_functions_bounded():
    closes = [100 + (i % 5) for i in range(60)]
    vols = [1000 + (i % 7) * 10 for i in range(60)]
    pc = B.compute_price_volume_corr(closes, vols)
    vr = B.compute_volume_ratio(vols)
    rv = B.compute_realized_vol(closes)
    assert -1.0 <= pc <= 1.0
    assert -1.0 <= vr <= 1.0
    assert 0.0 <= rv <= 1.0


def test_entry_dt_parsing():
    from datetime import date
    assert B._entry_dt({"entry_date": "2026-04-23"}) == date(2026, 4, 23)
    assert B._entry_dt({"timestamp": "2026-04-23T06:50:53+00:00"}) == date(2026, 4, 23)
    assert B._entry_dt({}) is None
