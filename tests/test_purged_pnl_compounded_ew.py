"""Purged institutional book: sum vs geometric compound (stats_cleaner)."""

from alpha_engine.stats_cleaner import compute_clean_metrics


def _pick(symbol, pnl, ts, source_system="test_sys"):
    return {
        "symbol": symbol,
        "pnl_pct": pnl,
        "timestamp": ts,
        "source_system": source_system,
        "expired_no_pnl": False,
    }


def test_purged_compound_excludes_toxic_symbol():
    rows = [
        _pick("BTCUSDT", 10.0, "2026-01-01T00:00:00"),
        _pick("TRXUSDT", 200.0, "2026-01-02T00:00:00"),
    ]
    m = compute_clean_metrics(rows, cap_pct=10.0)
    assert m["purged_pnl_raw"] == 10.0
    assert m["purged_pnl_compounded_ew"] == 10.0


def test_purged_compound_two_trades():
    rows = [
        _pick("A", 10.0, "2026-01-01T00:00:00"),
        _pick("B", 10.0, "2026-01-03T00:00:00"),
    ]
    m = compute_clean_metrics(rows, cap_pct=10.0)
    assert m["purged_pnl_raw"] == 20.0
    assert m["purged_pnl_compounded_ew"] == 21.0
