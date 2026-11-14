#!/usr/bin/env python3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from tools.pi_data_hygiene import (  # noqa: E402
    classify_active,
    classify_closed,
    run,
    summarize_active,
    summarize_zombies,
    find_flat_cohorts,
)

ASOF = "2026-11-14T15:50:00+00:00"


def _active(**kw):
    base = {
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "direction": "SHORT",
        "entry_price": 66300.0,
        "current_price": 66300.0,
        "take_profit": None,
        "stop_loss": None,
        "signal_time": "2026-11-14T13:53:28Z",
    }
    base.update(kw)
    return base


def test_crypto_pinned_price_flagged():
    tags = classify_active(_active(), ASOF)
    assert "STALE_CRYPTO_PRICE" in tags


def test_crypto_live_price_not_flagged():
    tags = classify_active(_active(current_price=65730.0), ASOF)
    assert "STALE_CRYPTO_PRICE" not in tags


def test_equity_flat_close_not_flagged_as_stale():
    p = _active(symbol="ADBE", asset_class="EQUITY", entry_price=243.08,
                current_price=243.08)
    tags = classify_active(p, ASOF)
    assert "STALE_CRYPTO_PRICE" not in tags


def test_date_only_signal_seed():
    p = _active(symbol="ES=F", asset_class="FUTURES", signal_time="2026-11-14")
    tags = classify_active(p, ASOF)
    assert "DATE_ONLY_SEED" in tags


def test_null_price_flagged():
    tags = classify_active(_active(current_price=None), ASOF)
    assert "NULL_PRICE" in tags


def test_placeholder_entry_flagged():
    tags = classify_active(_active(entry_price=0.0), ASOF)
    assert "PLACEHOLDER_ENTRY" in tags


def test_frozen_closed_phantom():
    p = {
        "symbol": "EURUSD=X",
        "entry_price": 1.143903017,
        "exit_price": 1.143903017,
        "pnl_pct": 0.0,
        "exit_reason": "UNKNOWN",
        "closed_at": "2026-03-13T13:26:05Z",
    }
    assert "FROZEN_CLOSED_PHANTOM" in classify_closed(p)


def test_closed_with_real_pnl_not_phantom():
    p = {
        "symbol": "BTCUSDT",
        "entry_price": 60000.0,
        "exit_price": 64000.0,
        "pnl_pct": 6.67,
        "exit_reason": "TP_HIT",
        "closed_at": "2026-11-14T10:00:00Z",
    }
    assert classify_closed(p) == []


def test_summarize_recency():
    active = [
        _active(symbol="BTCUSDT", signal_time="2026-11-14T13:53:28Z", current_price=66300.0),
        _active(symbol="NEARUSDT", signal_time="2026-11-14T13:10:05Z", current_price=3.233),
    ]
    by = summarize_active(active, ASOF)
    crypto = by["CRYPTO"]
    assert crypto["n"] == 2
    assert crypto["live_quotes"] == 1
    assert crypto["pinned"] == 1
    assert crypto["newest_signal_age_h"] is not None


def test_run_on_synthetic_payload():
    payload = {
        "generated_at": "2026-11-14T14:30:07Z",
        "picks": {
            "active": [
                _active(),
                _active(symbol="NEARUSDT", current_price=3.2330),
                _active(symbol="TLT", asset_class="BOND", current_price=None,
                        signal_time="2026-11-13"),
            ],
            "recent_closed": [
                {
                    "symbol": "EURUSD=X", "entry_price": 1.143903017,
                    "exit_price": 1.143903017, "pnl_pct": 0.0,
                    "exit_reason": "UNKNOWN", "closed_at": "2026-03-13T13:26:05Z",
                },
            ],
        },
    }
    total = run(payload, ASOF, show=False)
    assert total >= 4


def test_summarize_zombies():
    raw = [
        _active(symbol="BTCUSDT", signal_time="2026-08-01T00:00:00Z", current_price=None),
        _active(symbol="NEARUSDT", signal_time="2026-11-14T13:00:00Z", current_price=3.22),
        _active(symbol="XRPUSDT", signal_time="2026-11-14T13:54:00Z", current_price=0.9724),
    ]
    by = summarize_zombies(raw, ASOF)
    crypto = by["CRYPTO"]
    assert crypto["n"] == 3
    assert crypto["older_7d"] == 1
    assert crypto["null_price"] == 1


def test_flat_cohort_detected():
    closed = [{"strategy": "signal_validation", "pnl_pct": 3.00} for _ in range(12)]
    assert find_flat_cohorts(closed) == {"signal_validation": 12}


def test_flat_cohort_with_real_variance_not_flagged():
    closed = []
    for pnl in (3.0, 2.4, 5.1, -1.2, 3.0, 0.8):
        closed.append({"strategy": "real_strategy", "pnl_pct": pnl})
    assert find_flat_cohorts(closed) == {}


@pytest.mark.skipif(
    not Path("/tmp/kilo/dashboard_data_latest.json").exists(),
    reason="live payload not present",
)
def test_live_payload_executes():
    import json
    payload = json.loads(Path("/tmp/kilo/dashboard_data_latest.json").read_text())
    total = run(payload, ASOF, show=False)
    assert total >= 0
