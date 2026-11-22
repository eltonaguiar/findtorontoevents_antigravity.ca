"""H-201 forward pod: frozen spec, benchmark leg, time-only exit.

The pod is only evidence if (a) its spec cannot drift after registration, (b) it
exits the way the registered backtest exited, and (c) the benchmark leg is
recorded so a beta result cannot be mistaken for alpha.
"""
import datetime as dt

import pytest

import tools.forward_book as fb


def _bars(n=60, start=100.0, step=0.005, day0=dt.date(2026, 1, 1)):
    out, px = [], start
    for i in range(n):
        px *= (1 + step)
        d = day0 + dt.timedelta(days=i)
        out.append([d.isoformat(), px, px * 1.02, px * 0.98, px])
    return out


@pytest.fixture
def book():
    return {"schema": 1, "created_at": None, "entries": []}


def test_h201_spec_is_frozen(monkeypatch):
    spec = fb.RULES["xsmom_equity_top3_6m"]
    assert spec["sl_pct"] is None and spec["tp_pct"] is None, (
        "the registered backtest had no TP/SL; adding one forward tests a different strategy")
    assert spec["max_hold_days"] == 21
    assert spec["top_k"] == 3 and spec["lookback_days"] == 126
    assert spec["registered_hypothesis"] == "H-201"
    assert fb.EQ_UNIVERSE == ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
                              "META", "JPM", "XOM", "UNH", "JNJ"]


def test_emit_records_pod_benchmark_and_no_levels(book, monkeypatch):
    monkeypatch.setattr(fb, "bars_for", lambda sym, cls="CRYPTO", days=600: _bars())
    e = fb.emit(book, "AAPL", "xsmom_equity_top3_6m", "test", "note",
                asset_class="EQUITY", benchmark="SPY", pod="H-201", spec_ref="H-201")
    assert e["benchmark"] == "SPY" and e["pod"] == "H-201" and e["spec_ref"] == "H-201"
    assert e["take_profit"] is None and e["stop_loss"] is None
    assert e["asset_class"] == "EQUITY" and e["cost_bps"] == 10
    assert e["entry_date"] == _bars()[-1][0]
    assert e["registered_at"] and e["status"] == "OPEN"


def test_resolve_is_time_exit_only_and_books_the_benchmark(book, monkeypatch):
    monkeypatch.setattr(fb, "bars_for", lambda sym, cls="CRYPTO", days=600: _bars())
    e = fb.emit(book, "AAPL", "xsmom_equity_top3_6m", "test", "n",
                asset_class="EQUITY", benchmark="SPY", pod="H-201", spec_ref="H-201")
    # forward bars must start AFTER the entry bar, else there is no window at all
    entry_day = dt.date.fromisoformat(e["entry_date"])
    fwd = lambda sym, cls="CRYPTO", days=600: _bars(
        step=0.02, day0=entry_day + dt.timedelta(days=1))  # noqa: E731
    monkeypatch.setattr(fb, "bars_for", fwd)
    fb.resolve(book)
    r = e["resolution"]
    assert r["reason"] == "TIME"
    assert r["bars_walked"] == 21
    assert r["benchmark_symbol"] == "SPY"
    assert r["benchmark_pct"] is not None
    assert r["excess_pct"] == pytest.approx(r["net_pnl_pct"] - r["benchmark_pct"], abs=1e-6)
    assert e["status"] == "RESOLVED"


def test_publish_exposes_pod_level_stats_with_benchmark(book, monkeypatch):
    monkeypatch.setattr(fb, "bars_for", lambda sym, cls="CRYPTO", days=600: _bars())
    fb.emit(book, "AAPL", "xsmom_equity_top3_6m", "test", "n",
            asset_class="EQUITY", benchmark="SPY", pod="H-201", spec_ref="H-201")
    entry_day = dt.date.fromisoformat(book["entries"][0]["entry_date"])
    monkeypatch.setattr(fb, "bars_for", lambda sym, cls="CRYPTO", days=600: _bars(
        step=0.01, day0=entry_day + dt.timedelta(days=1)))
    fb.resolve(book)
    monkeypatch.setattr(fb, "PUBLISHED", __import__("pathlib").Path("/tmp/_fb_test_publish.json"))
    out = fb.publish(book)
    pod = out["by_pod"]["H-201"]
    assert pod["benchmark"] == "SPY" and pod["n_resolved"] == 1
    assert pod["mean_benchmark_pct"] is not None and pod["mean_excess_pct"] is not None
    __import__("pathlib").Path("/tmp/_fb_test_publish.json").unlink(missing_ok=True)
