"""Deterministic tests for tools/price_freshness_sla.py (no DB)."""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.price_freshness_sla import (  # noqa: E402
    DAY_MS,
    _to_ms,
    evaluate,
    table_requirements,
)

NOW = int(datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)


def test_every_gated_class_has_a_table_and_a_tolerance():
    """The SLA must cover exactly the classes the selection-alpha gate can measure."""
    from alpha_engine.audit3_selection_alpha import TABLE_FOR, TOLERANCE_MS

    req = table_requirements()
    covered = {k for rec in req.values() for k in rec["classes"]}
    assert covered == set(TABLE_FOR)
    assert covered == set(TOLERANCE_MS)


def test_shared_table_is_checked_once_at_the_tightest_tolerance():
    """etf_daily_ohlcv gates both ETF and BOND — one row, tightest tolerance wins."""
    req = table_requirements()
    etf = req["etf_daily_ohlcv"]
    assert etf["classes"] == ["BOND", "ETF"]
    from alpha_engine.audit3_selection_alpha import TOLERANCE_MS
    assert etf["tolerance_ms"] == min(TOLERANCE_MS["ETF"], TOLERANCE_MS["BOND"])


def test_a_fresh_table_passes_and_a_stale_one_fails():
    req = table_requirements()
    tol_days = req["equity_daily_ohlcv"]["tolerance_ms"] / DAY_MS
    today = datetime.fromtimestamp(NOW / 1000, tz=timezone.utc).date()
    fresh = evaluate({"equity_daily_ohlcv": today}, now_ms=NOW)
    assert [v["ok"] for v in fresh if v["table"] == "equity_daily_ohlcv"] == [True]

    old = date.fromordinal(today.toordinal() - int(tol_days) - 2)
    stale = evaluate({"equity_daily_ohlcv": old}, now_ms=NOW)
    rec = next(v for v in stale if v["table"] == "equity_daily_ohlcv")
    assert rec["ok"] is False and rec["status"] == "STALE"
    assert "unmeasured" in rec["reason"]


def test_todays_bar_is_zero_days_old_not_one():
    """A DATE column read as midnight must not make today's bar look a day old."""
    today = datetime.fromtimestamp(NOW / 1000, tz=timezone.utc).date()
    ms = _to_ms(today, "date")
    assert ms is not None and NOW - ms < DAY_MS


def test_empty_table_is_a_failure_not_a_pass():
    """No rows means structurally unmeasurable — never silently fresh."""
    verdicts = evaluate({"fx_prices": None}, now_ms=NOW)
    rec = next(v for v in verdicts if v["table"] == "fx_prices")
    assert rec["ok"] is False and rec["status"] == "EMPTY"
    assert rec["age_ms"] is None


def test_crypto_ms_table_is_compared_in_milliseconds():
    req = table_requirements()
    assert req["crypto_ohlcv"]["kind"] == "ms"
    recent = NOW - 3600_000  # 1h ago
    verdicts = evaluate({"crypto_ohlcv": recent}, now_ms=NOW)
    rec = next(v for v in verdicts if v["table"] == "crypto_ohlcv")
    assert rec["ok"] is True


def test_a_future_timestamp_is_not_reported_stale():
    """Clock skew or a bad row must not fail the gate for being 'negative' old."""
    verdicts = evaluate({"crypto_ohlcv": NOW + 60_000}, now_ms=NOW)
    rec = next(v for v in verdicts if v["table"] == "crypto_ohlcv")
    assert rec["ok"] is True
