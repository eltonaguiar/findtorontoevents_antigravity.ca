"""Wire-in test: sentiment_macro_contrarian registered in confluence dispatch.

Proves Wire-Up Rule (CLAUDE.md) compliance for T2.3:
  - Production caller (run_confluence_strategies) can locate + invoke the
    strategy.
  - The SENTIMENT_MACRO_DISABLED=1 rollback kills the strategy at the
    module level even when the dispatcher tries to call it.
  - The SENTIMENT_MACRO_WIRED=0 dispatcher-level off-switch removes it
    from the dispatch list entirely.
  - Stub data only — no live API calls.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# alpha_engine modules use bare imports (from config, from indicators, ...);
# add alpha_engine/ to sys.path so reloads pick up the same path resolution
# as production scanner.
_REPO = Path(__file__).resolve().parent.parent
_AE = _REPO / "alpha_engine"
if str(_AE) not in sys.path:
    sys.path.insert(0, str(_AE))


def _stub_ohlcv(n: int = 60, base: float = 100.0, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, 0.01, n)
    closes = base * np.cumprod(1 + rets)
    idx = pd.date_range(
        end=datetime.now(timezone.utc),
        periods=n,
        freq="D",
    )
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": closes * (1 + rng.uniform(0, 0.005, n)),
            "Low": closes * (1 - rng.uniform(0, 0.005, n)),
            "Close": closes,
            "Volume": rng.integers(1_000_000, 5_000_000, n),
        },
        index=idx,
    )
    # Lower-case mirrors for strategies that read those columns.
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col.lower()] = df[col]
    return df


def test_sentiment_macro_registered_in_confluence_dispatch(monkeypatch):
    """run_confluence_strategies dispatch includes sentiment_macro_contrarian."""
    monkeypatch.delenv("SENTIMENT_MACRO_DISABLED", raising=False)
    monkeypatch.setenv("SENTIMENT_MACRO_WIRED", "1")

    # Force re-import so module-level _sentiment_macro_contrarian binds fresh.
    import importlib
    import alpha_engine.confluence_strategies as cs
    importlib.reload(cs)

    assert cs._sentiment_macro_contrarian is not None, (
        "sentiment_macro_contrarian should import successfully"
    )

    data = {"BTC-USDT": _stub_ohlcv(seed=1), "ETH-USDT": _stub_ohlcv(seed=2)}
    macro_stub = {
        "regime": {"usd": "weak", "curve": "steep", "vol": "elevated"},
        "indicators": {"VIXCLS": {"value": 30.0, "date": "2026-05-08"}},
    }
    # FGI=15 + weak USD -> should produce CRYPTO BUY signals.
    out = cs.run_confluence_strategies(
        data, fear_greed=15, macro=macro_stub
    )
    assert isinstance(out, list)
    sm_signals = [s for s in out if s.get("strategy") == "sentiment_macro_contrarian"]
    assert sm_signals, (
        "sentiment_macro_contrarian should fire in the wired dispatcher under "
        "extreme-fear + weak-USD stub macro"
    )
    for sig in sm_signals:
        assert sig.get("direction") == "BUY"
        assert sig.get("asset_class") == "CRYPTO"


def test_sentiment_macro_module_disable_rollback(monkeypatch):
    """SENTIMENT_MACRO_DISABLED=1 silences the strategy even when dispatched."""
    monkeypatch.setenv("SENTIMENT_MACRO_DISABLED", "1")
    monkeypatch.setenv("SENTIMENT_MACRO_WIRED", "1")

    import importlib
    import alpha_engine.sentiment_macro_contrarian as smc
    importlib.reload(smc)
    import alpha_engine.confluence_strategies as cs
    importlib.reload(cs)

    data = {"BTC-USDT": _stub_ohlcv(seed=3)}
    out = cs.run_confluence_strategies(
        data, fear_greed=15, macro={
            "regime": {"usd": "weak", "curve": "steep", "vol": "elevated"},
            "indicators": {"VIXCLS": {"value": 30.0, "date": "2026-05-08"}},
        },
    )
    sm_signals = [s for s in out if s.get("strategy") == "sentiment_macro_contrarian"]
    assert sm_signals == [], (
        "SENTIMENT_MACRO_DISABLED=1 must short-circuit the strategy to []"
    )


def test_sentiment_macro_dispatcher_off_switch(monkeypatch):
    """SENTIMENT_MACRO_WIRED=0 removes the strategy from the dispatcher entirely."""
    monkeypatch.delenv("SENTIMENT_MACRO_DISABLED", raising=False)
    monkeypatch.setenv("SENTIMENT_MACRO_WIRED", "0")

    import importlib
    import alpha_engine.confluence_strategies as cs
    importlib.reload(cs)

    data = {"BTC-USDT": _stub_ohlcv(seed=4)}
    out = cs.run_confluence_strategies(
        data, fear_greed=15, macro={
            "regime": {"usd": "weak", "curve": "steep", "vol": "elevated"},
            "indicators": {"VIXCLS": {"value": 30.0, "date": "2026-05-08"}},
        },
    )
    sm_signals = [s for s in out if s.get("strategy") == "sentiment_macro_contrarian"]
    assert sm_signals == [], (
        "SENTIMENT_MACRO_WIRED=0 must drop the strategy from the dispatch list"
    )


def test_sentiment_macro_dispatcher_idempotent_on_reimport(monkeypatch):
    """Re-importing the dispatcher does not duplicate the strategy."""
    monkeypatch.delenv("SENTIMENT_MACRO_DISABLED", raising=False)
    monkeypatch.setenv("SENTIMENT_MACRO_WIRED", "1")

    import importlib
    import alpha_engine.confluence_strategies as cs
    importlib.reload(cs)
    importlib.reload(cs)
    importlib.reload(cs)

    data = {"BTC-USDT": _stub_ohlcv(seed=5)}
    out = cs.run_confluence_strategies(
        data, fear_greed=15, macro={
            "regime": {"usd": "weak", "curve": "steep", "vol": "elevated"},
            "indicators": {"VIXCLS": {"value": 30.0, "date": "2026-05-08"}},
        },
    )
    sm_signals = [s for s in out if s.get("strategy") == "sentiment_macro_contrarian"]
    # 1 stub symbol -> at most 1 fire per dispatch; never N>1 from duplication.
    assert len(sm_signals) <= 1, (
        "Idempotent registration: multiple reloads must not duplicate the "
        f"dispatch entry (got {len(sm_signals)} signals from 1 symbol)"
    )
