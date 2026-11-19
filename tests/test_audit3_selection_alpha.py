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


def test_fx_symbol_candidates_strip_the_vendor_suffixes():
    # fx_prices stores the bare pair (AUDJPY); the ledger carries =X / - / /
    # forms. Before this, none of them produced the bare pair, so forex
    # selection alpha was silently 0.
    for raw in ("AUDJPY=X", "AUD-USD", "AUD/JPY"):
        c = symbol_candidates(raw, "FOREX")
        bare = raw.replace("=X", "").replace("-", "").replace("/", "")
        assert bare in c, f"{raw} -> {c}"


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


# ─────────────────────────────────────────── N5 hold-time normalisation ──
def test_alpha_is_normalised_by_hold_time():
    short = _row(pnl=8.0, closed="2026-05-01T06:00:00+00:00")   # 6h hold
    long = _row(pnl=8.0, closed="2026-05-02T00:00:00+00:00")    # 24h hold
    bars = {"CRYPTO:BTCUSDT": _bars_for(long, 100.0, 105.0)}
    res = alpha_for([short, long], bars)
    o = res["overall"]
    assert o["alpha_pct"] > 0                    # unchanged headline
    assert o["hold_days_mean"] > 0.5
    assert o["alpha_per_day_pct"] > o["alpha_pct"]
    # annualized is computed from the unrounded per-day mean, so comparing it to
    # the rounded 4dp field needs a tolerance (double-rounding differs by <0.05).
    assert abs(o["alpha_annualized_pct"] - o["alpha_per_day_pct"] * 365.0) < 0.1
    assert o["min_hold_participation"] == 0.5
    assert o["n_min_hold"] == 1
    assert o["alpha_pct_min_hold"] == 2.85


def test_min_hold_fields_present_even_when_nothing_qualifies():
    row = _row(pnl=8.0, closed="2026-05-01T01:00:00+00:00")     # 1h hold
    bars = {"CRYPTO:BTCUSDT": _bars_for(row, 100.0, 105.0)}
    o = alpha_for([row], bars)["overall"]
    assert o["n_min_hold"] == 0
    assert o["min_hold_participation"] == 0.0
    assert o["alpha_pct_min_hold"] is None


# ─────────────────────────────── G9: unmeasured is not the same as beta-only ──
def test_g9_does_not_brand_cells_without_measured_alpha():
    from alpha_engine.audit3_tribunal import apply_selection_alpha_gate
    cells = [{"asset_class": "CRYPTO", "direction": "LONG", "verdict": "WEAK", "reasons": []}]
    # the sidecar exists but carries no CRYPTO entry at all
    apply_selection_alpha_gate(cells, {"by_class": {"ETF": {"n": 50, "alpha_ci": [0.2, 0.9]}}})
    assert "beta_dominant" not in cells[0]
    assert cells[0]["alpha_gate"] == {"alpha_ci_lo": None, "passed": None,
                                      "status": "unmeasured"}


def test_g9_flags_beta_only_cells_and_demotes_proven():
    from alpha_engine.audit3_tribunal import apply_selection_alpha_gate
    cells = [{"asset_class": "ETF", "direction": "LONG", "verdict": "PROVEN_T2", "reasons": []}]
    apply_selection_alpha_gate(cells, {"by_class": {"ETF": {"n": 50, "alpha_ci": [-0.4, 0.1]}}})
    assert cells[0]["beta_dominant"] is True
    assert cells[0]["verdict"] == "CANDIDATE"
    assert any("G9" in r for r in cells[0]["reasons"])


def test_g9_keeps_proven_when_alpha_ci_lower_bound_is_positive():
    from alpha_engine.audit3_tribunal import apply_selection_alpha_gate
    cells = [{"asset_class": "ETF", "direction": "LONG", "verdict": "PROVEN_T2", "reasons": []}]
    apply_selection_alpha_gate(cells, {"by_class": {"ETF": {"n": 50, "alpha_ci": [0.05, 0.6]}}})
    assert cells[0]["verdict"] == "PROVEN_T2"
    assert "beta_dominant" not in cells[0]
