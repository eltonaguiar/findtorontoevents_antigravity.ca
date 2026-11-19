"""Unit tests for audit3_selection_alpha (no DB: synthetic bars only)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_selection_alpha import (  # noqa: E402
    _close_at,
    alpha_for,
    symbol_candidates,
)

H = 3600_000


def _row(symbol="BTCUSDT", ac="CRYPTO", direction="LONG", pnl=1.0,
         issued="2026-05-01T00:00:00+00:00", closed="2026-05-01T06:00:00+00:00"):
    return {"symbol": symbol, "asset_class": ac, "direction": direction,
            "pnl_pct": pnl, "timestamp": issued, "closed_at": closed}


def _bars_for(row, start=100.0, end=105.0):
    """Bars at every hour across the row's window."""
    from datetime import datetime
    t0 = datetime.fromisoformat(row["timestamp"])
    t1 = datetime.fromisoformat(row["closed_at"])
    n = int((t1 - t0).total_seconds() // 3600)
    out = []
    for i in range(n + 2):
        ts = int(t0.timestamp() * 1000) + i * H
        step = (end - start) / max(1, n)
        out.append((ts, start + i * step))
    return out


# ─────────────────────────────────────────────────────────── symbols ──
def test_crypto_symbol_candidates_cover_the_vendor_variants():
    c = symbol_candidates("BTC-USD", "CRYPTO")
    assert "BTCUSDT" in c
    assert "BTC-USD" in c
    c2 = symbol_candidates("ETHUSDT", "CRYPTO")
    assert "ETHUSDT" in c2
    # non-crypto keeps the symbol and adds dot/dash swaps
    eq = symbol_candidates("BRK.B", "EQUITY")
    assert "BRK-B" in eq


# ─────────────────────────────────────────────────────────── alignment ──
def test_close_at_takes_the_first_bar_at_or_after_the_signal():
    series = [(0, 10.0), (H, 11.0), (2 * H, 12.0)]
    assert _close_at(series, 0, H) == 10.0
    assert _close_at(series, H + 1, H) == 12.0      # fills on the next bar
    assert _close_at(series, 2 * H + 1, H) is None  # beyond the last bar
    assert _close_at(series, 0, 0) == 10.0


def test_close_at_respects_staleness_tolerance():
    series = [(0, 10.0)]
    assert _close_at(series, 10 * H, H) is None  # a stale quote is not a fill


# ──────────────────────────────────────────────────────── alpha maths ──
def test_long_pick_that_underperforms_its_own_hold_has_negative_alpha():
    row = _row(direction="LONG", pnl=2.0)
    bars = {"CRYPTO:BTCUSDT": _bars_for(row, 100.0, 105.0)}  # hold ~+5%
    res = alpha_for([row], bars)
    assert res["covered"] == 1
    o = res["overall"]
    assert o["hold_net_pct"] > 3.0
    assert o["alpha_pct"] < 0            # pick 2% vs hold ~5% => negative alpha


def test_short_pick_is_scored_against_a_short_benchmark():
    row = _row(direction="SHORT", pnl=2.0)
    bars = {"CRYPTO:BTCUSDT": _bars_for(row, 100.0, 95.0)}  # symbol -5%
    res = alpha_for([row], bars)
    o = res["overall"]
    assert o["hold_net_pct"] > 3.0        # a short hold earns the down-move
    assert o["alpha_pct"] < 0             # 2% captured out of a 5% move


def test_pick_beating_its_hold_has_positive_alpha():
    row = _row(direction="LONG", pnl=8.0)
    bars = {"CRYPTO:BTCUSDT": _bars_for(row, 100.0, 105.0)}
    res = alpha_for([row], bars)
    assert res["overall"]["alpha_pct"] > 0


def test_missing_prices_are_counted_not_silently_dropped():
    row = _row(symbol="NOPRICEUSDT")
    res = alpha_for([row], {})
    assert res["covered"] == 0
    assert res["missing"].get("no_price:CRYPTO") == 1
    assert res["overall"]["n"] == 0


def test_rows_without_timestamps_are_reported():
    row = _row()
    row["timestamp"] = ""
    row["closed_at"] = ""
    res = alpha_for([row], {"CRYPTO:BTCUSDT": [(0, 1.0)]})
    assert res["missing"].get("no_timestamp") == 1


def test_small_slices_are_not_aggregated():
    # 4 rows: too few for a bootstrap interval, and far too few for a slice.
    rows = [_row(pnl=1.0) for _ in range(4)]
    bars = {"CRYPTO:BTCUSDT": _bars_for(rows[0], 100.0, 105.0)}
    res = alpha_for(rows, bars)
    assert "CRYPTO/LONG" not in res["by_slice"]
    assert res["by_class"]["CRYPTO"]["alpha_ci"] == [None, None]


def test_buy_direction_is_long_and_never_lands_in_a_question_mark_bucket():
    rows = []
    for _ in range(20):
        r = _row(direction="BUY", pnl=1.0)
        r["strategy"] = "s1"
        rows.append(r)
    out = alpha_for(rows, {"CRYPTO:BTCUSDT": _bars_for(rows[0])})
    assert out["covered"] == 20
    assert "CRYPTO/LONG" in out["by_slice"]
    assert "CRYPTO/s1/LONG" in out["by_strategy"]
    assert "?" not in "".join(out["by_strategy"])
    # The benchmark must be real: a BUY row held a rising series, so alpha is
    # strictly below the gross pick return.
    assert out["by_strategy"]["CRYPTO/s1/LONG"]["hold_net_pct"] > 0


def test_rows_without_an_entry_stamp_get_no_zero_benchmark():
    r = _row()
    r.pop("timestamp")
    r["created_at"] = r["closed_at"]
    out = alpha_for([r], {"CRYPTO:BTCUSDT": _bars_for(_row())})
    assert out["covered"] == 0
    assert out["missing"].get("degenerate_window") == 1
