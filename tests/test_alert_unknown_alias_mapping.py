"""Regression tests for the alert strategy-name mapping (naming gap).

Finding (2026-11-16): `cross_aggregation.performance_alerts._strategy_degradation`
bucketed closed rows by `p.get("strategy") or p.get("signal_type") or "unknown"`.
51 kimi_riseoftheclaw closed rows carry `strategy` literally stamped "unknown"
(no algorithm / signal_type) and all merged into one `unknown` degradation
alert, so the REDUCE verdict could not be attributed to an emitter. The rows
must map to their REAL emitter name via alpha_engine.config.resolve_strategy_name
(strategy -> strategy_name -> algorithm -> mutation_name -> source_system,
alias-canonicalised through STRATEGY_TRACK_ALIASES).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.config import resolve_strategy_name
from cross_aggregation.performance_alerts import (
    _resolve_alert_strategy_name,
    _strategy_degradation,
)

NOW = datetime.now(timezone.utc)


def _closed_row(strategy, source_system, pnl, age_days, **extra):
    row = {
        "symbol": "ETH-USD",
        "strategy": strategy,
        "source_system": source_system,
        "pnl_pct": pnl,
        "closed_at": (NOW - timedelta(days=age_days)).isoformat(),
    }
    row.update(extra)
    return row


def _degrading_ledger(strategy, source_system, **extra):
    """20 prior winners (50% baseline) + 12 recent losers (0% recent WR)."""
    rows = [
        _closed_row(strategy, source_system, 1.0, age_days=30 + i, **extra)
        for i in range(20)
    ]
    rows += [
        _closed_row(strategy, source_system, -1.0, age_days=i % 7, **extra)
        for i in range(12)
    ]
    return rows


def test_unknown_stamped_rows_map_to_real_emitter():
    rows = _degrading_ledger("unknown", "kimi_riseoftheclaw")
    alerts = _strategy_degradation([], rows, [])
    assert alerts, "degrading kimi ledger should raise STRATEGY_DEGRADATION"
    names = {a["details"]["strategy"] for a in alerts}
    assert "unknown" not in names, "unknown-stamped rows must not bucket as `unknown`"
    assert names == {"kimi_riseoftheclaw"}
    assert alerts[0]["message"].startswith("kimi_riseoftheclaw:")
    assert alerts[0]["action"] == "REDUCE"


def test_algorithm_only_rows_keep_emitter_name():
    rows = _degrading_ledger(
        None, "kimi_riseoftheclaw", algorithm="crypto-momentum-scout"
    )
    alerts = _strategy_degradation([], rows, [])
    assert alerts
    assert {a["details"]["strategy"] for a in alerts} == {"crypto-momentum-scout"}


def test_signal_type_is_not_used_as_strategy_name():
    rows = _degrading_ledger(None, "alpha_engine", signal_type="BUY")
    alerts = _strategy_degradation([], rows, [])
    assert alerts
    names = {a["details"]["strategy"] for a in alerts}
    assert "BUY" not in names
    assert names == {"alpha_engine"}


def test_resolve_strategy_name_precedence():
    assert resolve_strategy_name({"strategy": "forex_rsi2_mean_reversion"}) == (
        "forex_rsi2_mean_reversion"
    )
    assert resolve_strategy_name(
        {"strategy": "unknown", "algorithm": "crypto-momentum-scout"}
    ) == "crypto-momentum-scout"
    assert resolve_strategy_name({"strategy": "unknown"}) == "unknown"
    assert (
        resolve_strategy_name({"strategy": "unknown", "source_system": "kimi_riseoftheclaw"})
        == "kimi_riseoftheclaw"
    )
    assert resolve_strategy_name({}) == "unknown"


def test_resolve_strategy_name_canonicalises_aliases():
    # STRATEGY_TRACK_ALIASES variant -> canonical form
    assert (
        resolve_strategy_name({"strategy": "mean_reversion_bollinger"})
        == "MeanReversionBB"
    )
    assert (
        resolve_strategy_name({"strategy": "connors_rsi2"})
        == "connors_rsi2_scanner"
    )


def test_alert_helper_matches_resolver():
    pick = {"strategy": "unknown", "source_system": "kimi_riseoftheclaw"}
    assert _resolve_alert_strategy_name(pick) == resolve_strategy_name(pick)
