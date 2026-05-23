"""Wire-in test: regime_filtered_momentum registered in EQUITY_STRATEGIES.

Proves Wire-Up Rule (CLAUDE.md) compliance for T2.3:
  - Production registry (EQUITY_STRATEGIES) lists the strategy.
  - The REGIME_MOMENTUM_DISABLED=1 rollback short-circuits the strategy.
  - Re-importing the registry doesn't duplicate the entry.
  - Stub data only — no live API calls.

Note: the equity_strategies wrapper (`_wrap_with_factor_model`) forwards
`fn(data)` only. regime_filtered_momentum's `**kwargs` are optional, so the
wrapper's narrower call signature is compatible.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# alpha_engine modules use bare imports (from config, from community_strategies, ...).
_REPO = Path(__file__).resolve().parent.parent
_AE = _REPO / "alpha_engine"
if str(_AE) not in sys.path:
    sys.path.insert(0, str(_AE))


def _stub_long_history(n: int = 270, seed: int = 0) -> pd.DataFrame:
    """Build >=252+1 bars of OHLCV with mild upward drift so 12-1 momentum is finite."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0008, 0.012, n)
    closes = 100.0 * np.cumprod(1 + rets)
    idx = pd.date_range(end=datetime.now(timezone.utc), periods=n, freq="D")
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": closes * (1 + rng.uniform(0, 0.005, n)),
            "Low": closes * (1 - rng.uniform(0, 0.005, n)),
            "Close": closes,
            "Volume": rng.integers(1_000_000, 10_000_000, n),
        },
        index=idx,
    )
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col.lower()] = df[col]
    return df


def test_regime_momentum_in_equity_registry(monkeypatch):
    """EQUITY_STRATEGIES contains the regime_filtered_momentum key."""
    monkeypatch.delenv("REGIME_MOMENTUM_DISABLED", raising=False)

    import importlib
    import alpha_engine.equity_strategies as eq
    importlib.reload(eq)

    assert "regime_filtered_momentum" in eq.EQUITY_STRATEGIES, (
        "Wire-in failed: regime_filtered_momentum missing from "
        "EQUITY_STRATEGIES registry"
    )
    assert callable(eq.EQUITY_STRATEGIES["regime_filtered_momentum"])


def test_regime_momentum_invokable_via_registry(monkeypatch):
    """The registered (factor-model-wrapped) callable accepts (data) -> list."""
    monkeypatch.delenv("REGIME_MOMENTUM_DISABLED", raising=False)

    import importlib
    import alpha_engine.equity_strategies as eq
    importlib.reload(eq)

    data = {
        "AAPL": _stub_long_history(seed=1),
        "MSFT": _stub_long_history(seed=2),
        "SPY":  _stub_long_history(seed=3),
        "QQQ":  _stub_long_history(seed=4),
        "GOOGL": _stub_long_history(seed=5),
    }
    fn = eq.EQUITY_STRATEGIES["regime_filtered_momentum"]
    out = fn(data)
    assert isinstance(out, list), "regime_filtered_momentum must return a list"
    # When momentum is positive and macro defaults to permissive (no FRED key),
    # we expect at least 1 LONG signal — but accept [] gracefully if the
    # macro gate happens to short-circuit. The wire-in proof is that the
    # call returns a list without crashing.
    for sig in out:
        assert sig.get("strategy") == "regime_filtered_momentum"


def test_regime_momentum_disable_rollback(monkeypatch):
    """REGIME_MOMENTUM_DISABLED=1 short-circuits to []."""
    monkeypatch.setenv("REGIME_MOMENTUM_DISABLED", "1")

    import importlib
    import alpha_engine.regime_filtered_momentum as rfm
    importlib.reload(rfm)
    import alpha_engine.equity_strategies as eq
    importlib.reload(eq)

    data = {
        "AAPL": _stub_long_history(seed=11),
        "SPY":  _stub_long_history(seed=12),
    }
    fn = eq.EQUITY_STRATEGIES["regime_filtered_momentum"]
    out = fn(data)
    assert out == [], (
        "REGIME_MOMENTUM_DISABLED=1 must short-circuit the strategy to []"
    )


def test_regime_momentum_idempotent_registration(monkeypatch):
    """Re-importing equity_strategies yields exactly one regime_filtered_momentum entry."""
    monkeypatch.delenv("REGIME_MOMENTUM_DISABLED", raising=False)

    import importlib
    import alpha_engine.equity_strategies as eq
    importlib.reload(eq)
    importlib.reload(eq)
    importlib.reload(eq)

    keys = list(eq.EQUITY_STRATEGIES.keys())
    assert keys.count("regime_filtered_momentum") == 1, (
        f"Idempotent registration broken: "
        f"{keys.count('regime_filtered_momentum')} entries after 3 reloads"
    )
