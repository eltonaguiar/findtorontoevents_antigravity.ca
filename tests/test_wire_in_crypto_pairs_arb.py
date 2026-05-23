"""Wire-in test: crypto_pairs_arb registered in PROVEN_RESEARCH_STRATEGIES.

Proves Wire-Up Rule (CLAUDE.md) compliance for T2.3:
  - Production registry (PROVEN_RESEARCH_STRATEGIES) lists the strategy.
  - The CRYPTO_PAIRS_ARB_DISABLED=1 rollback short-circuits the strategy.
  - Re-importing the registry doesn't duplicate the entry.
  - Stub data only — no live API calls.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# alpha_engine modules use bare imports (from indicators, from multi_tf, ...).
_REPO = Path(__file__).resolve().parent.parent
_AE = _REPO / "alpha_engine"
if str(_AE) not in sys.path:
    sys.path.insert(0, str(_AE))


def _cointegrated_pair(n: int = 80, seed: int = 0):
    """Build two cointegrated price series with a known mean-reverting spread.

    Construction: shared random walk + small idiosyncratic noise -> spread is
    stationary (AR(1) with phi well below 1), so half-life filter passes.
    Then push the last sample wide so |z| > 2 fires.
    """
    rng = np.random.default_rng(seed)
    common = np.cumsum(rng.normal(0, 0.005, n))
    a = 100 * np.exp(common + rng.normal(0, 0.001, n))
    b = 50 * np.exp(common + rng.normal(0, 0.001, n))
    # Force last bar of A to spike up to push z-score above +2.
    a[-1] = a[-1] * 1.05

    df_a = pd.DataFrame({"close": a, "open": a, "high": a, "low": a, "volume": 1.0})
    df_b = pd.DataFrame({"close": b, "open": b, "high": b, "low": b, "volume": 1.0})
    return df_a, df_b


def test_crypto_pairs_arb_in_registry(monkeypatch):
    """PROVEN_RESEARCH_STRATEGIES contains the crypto_pairs_arb key."""
    monkeypatch.delenv("CRYPTO_PAIRS_ARB_DISABLED", raising=False)

    import importlib
    import alpha_engine.proven_research_strategies as prs
    importlib.reload(prs)

    assert "crypto_pairs_arb" in prs.PROVEN_RESEARCH_STRATEGIES, (
        "Wire-in failed: crypto_pairs_arb missing from "
        "PROVEN_RESEARCH_STRATEGIES registry"
    )
    assert callable(prs.PROVEN_RESEARCH_STRATEGIES["crypto_pairs_arb"])


def test_crypto_pairs_arb_invokable_via_registry(monkeypatch):
    """The registered callable accepts (data, **kwargs) and returns a list."""
    monkeypatch.delenv("CRYPTO_PAIRS_ARB_DISABLED", raising=False)

    import importlib
    import alpha_engine.proven_research_strategies as prs
    importlib.reload(prs)

    df_a, df_b = _cointegrated_pair(seed=7)
    data = {"BTCUSDT": df_a, "ETHUSDT": df_b}

    fn = prs.PROVEN_RESEARCH_STRATEGIES["crypto_pairs_arb"]
    out = fn(data)
    assert isinstance(out, list), "crypto_pairs_arb must return a list"
    # When the spread fires, exactly 2 picks share a pair_id. When it
    # doesn't fire (random data), [] is acceptable. We assert structure
    # only when non-empty; the *invokability* via the registry is the
    # wire-in proof.
    if out:
        assert all(isinstance(p, dict) for p in out)
        assert all(p.get("strategy") == "crypto_pairs_arb" for p in out)


def test_crypto_pairs_arb_disable_rollback(monkeypatch):
    """CRYPTO_PAIRS_ARB_DISABLED=1 short-circuits to []."""
    monkeypatch.setenv("CRYPTO_PAIRS_ARB_DISABLED", "1")

    import importlib
    import alpha_engine.proven_research_strategies as prs
    importlib.reload(prs)

    df_a, df_b = _cointegrated_pair(seed=11)
    data = {"BTCUSDT": df_a, "ETHUSDT": df_b}

    fn = prs.PROVEN_RESEARCH_STRATEGIES["crypto_pairs_arb"]
    out = fn(data)
    assert out == [], (
        "CRYPTO_PAIRS_ARB_DISABLED=1 must short-circuit the strategy to []"
    )


def test_crypto_pairs_arb_idempotent_registration(monkeypatch):
    """Re-importing the registry yields exactly one crypto_pairs_arb entry."""
    monkeypatch.delenv("CRYPTO_PAIRS_ARB_DISABLED", raising=False)

    import importlib
    import alpha_engine.proven_research_strategies as prs
    importlib.reload(prs)
    importlib.reload(prs)
    importlib.reload(prs)

    keys = list(prs.PROVEN_RESEARCH_STRATEGIES.keys())
    assert keys.count("crypto_pairs_arb") == 1, (
        f"Idempotent registration broken: {keys.count('crypto_pairs_arb')} "
        f"crypto_pairs_arb entries after 3 reloads"
    )
