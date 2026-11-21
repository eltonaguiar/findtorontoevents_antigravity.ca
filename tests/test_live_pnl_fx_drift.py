"""The forex cross-check may override yfinance only for a *plausible* gap.

2026-11-21: the tracker started preferring the forex failover feed whenever the
two disagreed by more than 0.25%, which fixed a frozen yfinance JPY leg. But a
gap that wide proves only that the feeds disagree -- an inverted or
differently-mapped failover quote also produces one, and publishing it puts a
~-99% PnL on the dashboard. So the override is bounded: staleness-sized gaps
switch feeds, implausible ones keep the primary and are left for the QA ledger's
MISMATCH check to report.
"""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "live_pnl_tracker", ROOT / "tools" / "live_pnl_tracker.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_yfinance(price):
    tkr = types.SimpleNamespace(fast_info={"lastPrice": price}, info={})
    return types.SimpleNamespace(Ticker=lambda sym: tkr)


def _pin_failover(monkeypatch, price):
    try:
        import alpha_engine.forex_price_failover as fx
    except Exception:                                  # pragma: no cover
        fx = types.ModuleType("alpha_engine.forex_price_failover")
        monkeypatch.setitem(sys.modules, "alpha_engine.forex_price_failover", fx)
    monkeypatch.setattr(fx, "fetch_forex_rate",
                        lambda sym, use_cache=False: {"price": price}, raising=False)


def test_staleness_sized_gap_switches_to_the_independent_feed(monkeypatch):
    """The case the override exists for: yfinance frozen ~0.75% off the feed."""
    mod = _mod()
    monkeypatch.setattr(mod, "yf", _fake_yfinance(159.707))
    _pin_failover(monkeypatch, 158.512)
    assert mod.fetch_price("USDJPY", "FOREX") == (158.512, "forex_failover")


def test_inverted_failover_quote_is_never_published(monkeypatch):
    """0.00631 JPY-per-USD against a 158.5 quote is a mapping error, not drift."""
    mod = _mod()
    monkeypatch.setattr(mod, "yf", _fake_yfinance(158.512))
    _pin_failover(monkeypatch, 0.00631)
    assert mod.fetch_price("USDJPY", "FOREX") == (158.512, "yfinance")


def test_agreeing_feeds_stay_on_yfinance(monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "yf", _fake_yfinance(1.0850))
    _pin_failover(monkeypatch, 1.0851)
    assert mod.fetch_price("EURUSD", "FOREX") == (1.0850, "yfinance")


def test_failover_still_prices_when_yfinance_returns_nothing(monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "yf", _fake_yfinance(None))
    _pin_failover(monkeypatch, 173.904)
    assert mod.fetch_price("EURJPY", "FOREX") == (173.904, "forex_failover")
