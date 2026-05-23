"""Tests for `alpha_engine/etf_rebalancer.py` and the runner.

Covers (per the build prompt):
  * synthetic 252-day returns matrix → HRP weights sum ~1.0, no negatives, no NaN
  * top-N selection from synthetic monotonic price ramps
  * soft-fail to equal-weight when pypfopt unavailable
  * runner gated by ETF_SECTOR_ROTATION_ENABLED env var
  * runner with mocked fetch_prices writes the expected JSON schema
"""
from __future__ import annotations

import json
import sys
import math
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

# Make repo root importable for `tools.run_etf_sector_rotation`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.etf_rebalancer import (  # noqa: E402
    SPDR_SECTOR_ETFS,
    _equal_weights,
    hrp_weights,
    sector_rotation_signal,
)


def _synthetic_returns(n_days: int = 252, tickers=None, seed: int = 7) -> pd.DataFrame:
    """Generate a synthetic returns matrix with mild correlation structure."""
    if tickers is None:
        tickers = ["XLK", "XLV", "XLF", "XLE", "XLP"]
    rng = np.random.default_rng(seed)
    # Correlated daily returns: 0.04% drift, ~1.2% daily vol.
    base = rng.standard_normal((n_days, 1)) * 0.005
    idio = rng.standard_normal((n_days, len(tickers))) * 0.010
    rets = base + idio + 0.0004
    return pd.DataFrame(rets, columns=list(tickers),
                        index=pd.date_range("2025-01-02", periods=n_days, freq="B"))


def _synthetic_prices_with_ramp(n_days: int = 200) -> pd.DataFrame:
    """Prices that monotonically encode rank: XLK > XLV > XLF > XLE > XLP.

    Drift is large vs noise so the ranking is deterministic across seeds —
    the test is checking signal wiring, not the noise tolerance of momentum.
    """
    tickers = ["XLK", "XLV", "XLF", "XLE", "XLP"]
    growth = {"XLK": 0.005, "XLV": 0.003, "XLF": 0.001, "XLE": -0.001, "XLP": -0.003}
    rng = np.random.default_rng(11)
    rows = []
    price = {t: 100.0 for t in tickers}
    for _ in range(n_days):
        noise = rng.standard_normal(len(tickers)) * 0.001
        for t, n in zip(tickers, noise):
            price[t] *= (1 + growth[t] + n)
        rows.append({t: price[t] for t in tickers})
    return pd.DataFrame(rows, index=pd.date_range("2025-01-02", periods=n_days, freq="B"))


# ---------------------------------------------------------------------------
# hrp_weights
# ---------------------------------------------------------------------------


def test_hrp_weights_basic_invariants():
    """5-asset, 252-day synthetic returns → weights sum to 1, all non-negative + finite."""
    rets = _synthetic_returns()
    w = hrp_weights(rets)
    assert set(w.keys()) == set(rets.columns), "All input tickers must be present."
    total = sum(w.values())
    assert math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-6), f"weights sum={total}"
    assert all(v >= 0 for v in w.values()), "no negative weights"
    assert all(math.isfinite(v) for v in w.values()), "no NaN/inf weights"


def test_hrp_weights_empty_dataframe():
    """Empty input → empty dict (no crash)."""
    assert hrp_weights(pd.DataFrame()) == {}


def test_hrp_weights_single_asset_returns_equal_weight():
    """Single column degenerate case → equal-weight (which is just {t: 1.0})."""
    rets = pd.DataFrame({"XLK": np.random.default_rng(0).standard_normal(50) * 0.01})
    w = hrp_weights(rets)
    assert w == {"XLK": 1.0}


def test_hrp_weights_insufficient_history_falls_back():
    """<20 rows of clean data → equal-weight fallback."""
    rng = np.random.default_rng(2)
    rets = pd.DataFrame(rng.standard_normal((10, 4)) * 0.01,
                        columns=["A", "B", "C", "D"])
    w = hrp_weights(rets)
    assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-9)
    # Equal weight ⇒ all identical.
    vals = list(w.values())
    assert all(math.isclose(v, vals[0], rel_tol=1e-9) for v in vals)


def test_hrp_weights_soft_fails_when_pypfopt_missing():
    """If pypfopt import raises, function returns equal-weight, not crashes."""
    rets = _synthetic_returns()
    # Block the lazy import inside hrp_weights by patching sys.modules.
    with mock.patch.dict(sys.modules, {"pypfopt": None}):
        w = hrp_weights(rets)
    vals = list(w.values())
    assert math.isclose(sum(vals), 1.0, rel_tol=1e-9)
    assert all(math.isclose(v, vals[0], rel_tol=1e-9) for v in vals), \
        "Equal-weight fallback expected when pypfopt unavailable."


# ---------------------------------------------------------------------------
# sector_rotation_signal
# ---------------------------------------------------------------------------


def test_sector_rotation_signal_picks_top_momentum():
    """Monotonic ramp → XLK should rank #1, XLP should be excluded from top-3."""
    prices = _synthetic_prices_with_ramp(n_days=180)
    out = sector_rotation_signal(prices, lookback=60, top_n=3)
    assert out["n_sectors"] == 5
    assert len(out["top_n"]) == 3
    assert out["top_n"][0] == "XLK", f"expected XLK first, got {out['top_n']}"
    assert "XLP" not in out["top_n"], "XLP (worst) must not be in top-3"
    assert math.isclose(sum(out["weights"].values()), 1.0, rel_tol=1e-6, abs_tol=1e-6)
    assert all(w >= 0 for w in out["weights"].values())


def test_sector_rotation_signal_empty_input():
    """Empty prices → empty payload, no crash, sane defaults."""
    out = sector_rotation_signal(pd.DataFrame(), lookback=60, top_n=3)
    assert out["top_n"] == []
    assert out["weights"] == {}
    assert out["method"] == "empty_input"


def test_sector_rotation_signal_insufficient_history():
    """Lookback longer than history → 'insufficient_history' method, empty picks."""
    prices = _synthetic_prices_with_ramp(n_days=20)  # lookback=60 will not fit
    out = sector_rotation_signal(prices, lookback=60, top_n=3)
    assert out["method"] == "insufficient_history"
    assert out["top_n"] == []


# ---------------------------------------------------------------------------
# Runner — tools/run_etf_sector_rotation.py
# ---------------------------------------------------------------------------


def test_runner_gated_off_by_default(monkeypatch, tmp_path, capsys):
    """ETF_SECTOR_ROTATION_ENABLED unset → runner exits 0 without writing."""
    from tools import run_etf_sector_rotation as runner

    monkeypatch.delenv(runner.ENV_GATE, raising=False)
    out_path = tmp_path / "etf.json"
    rc = runner.main(["--output", str(out_path)])
    assert rc == 0
    assert not out_path.exists(), "Gate-off should produce no JSON."


def test_runner_with_mocked_prices_writes_schema(monkeypatch, tmp_path):
    """With mocked fetch_prices + force flag, runner produces the expected JSON."""
    from tools import run_etf_sector_rotation as runner

    fake_prices = _synthetic_prices_with_ramp(n_days=180)

    def _fake_fetch(_tickers, _lb):
        return fake_prices

    monkeypatch.setattr(runner, "fetch_prices", _fake_fetch)
    out_path = tmp_path / "etf_sector_rotation_picks.json"

    rc = runner.main([
        "--universe", *fake_prices.columns.tolist(),
        "--lookback", "60", "--top-n", "3",
        "--output", str(out_path),
        "--force",
    ])
    assert rc == 0
    assert out_path.exists(), "Force flag should write the JSON."
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["agent"] == "etf_sector_rotation"
    assert payload["lookback_days"] == 60
    assert payload["top_n"] == 3
    assert len(payload["picks"]) == 3
    weights = [p["weight"] for p in payload["picks"]]
    assert math.isclose(sum(weights), 1.0, rel_tol=1e-6, abs_tol=1e-6)
    assert all(p["weight"] >= 0 for p in payload["picks"])
    assert payload["picks"][0]["ticker"] == "XLK", \
        "Top momentum should still be XLK end-to-end through the runner."


def test_runner_dry_run_does_not_write(monkeypatch, tmp_path):
    """--dry-run + --force still skips writing the JSON."""
    from tools import run_etf_sector_rotation as runner

    fake_prices = _synthetic_prices_with_ramp(n_days=180)
    monkeypatch.setattr(runner, "fetch_prices", lambda _t, _l: fake_prices)

    out_path = tmp_path / "etf_sector_rotation_picks.json"
    rc = runner.main([
        "--universe", *fake_prices.columns.tolist(),
        "--output", str(out_path),
        "--force", "--dry-run",
    ])
    assert rc == 0
    assert not out_path.exists()


# ---------------------------------------------------------------------------
# Sanity: the SPDR ETF universe matches the report
# ---------------------------------------------------------------------------


def test_spdr_universe_has_eleven_sectors():
    """`reports/library_research_stocks_etfs_bonds_2026_04_28.md` § 3 specifies
    SPDR sector ETFs. Universe size = 11 (the canonical SPDR sector lineup)."""
    assert len(SPDR_SECTOR_ETFS) == 11
    for must_have in ("XLK", "XLF", "XLE", "XLV", "XLU"):
        assert must_have in SPDR_SECTOR_ETFS


def test_equal_weights_helper_correctness():
    """Internal helper: even allocation, sums to 1.0, all identical."""
    w = _equal_weights(["A", "B", "C", "D"])
    assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-9)
    assert all(math.isclose(v, 0.25, rel_tol=1e-9) for v in w.values())
    assert _equal_weights([]) == {}
