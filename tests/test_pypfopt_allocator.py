"""Smoke tests for tools/pypfopt_allocator.py.

These exercise the import-safety contract (must import even if pypfopt
is missing) and, when pypfopt IS available, that the wrapper functions
return well-formed weight dicts that sum to ~1.0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import pypfopt_allocator as pa  # noqa: E402


def test_module_imports_safely():
    """Must always import. is_available() returns a bool either way."""
    assert isinstance(pa.is_available(), bool)


def test_diagnostic_report_shape():
    rep = pa.diagnostic_report()
    assert isinstance(rep, dict)
    assert "available" in rep
    if rep["available"]:
        assert "version" in rep
    else:
        assert "install_hint" in rep


def test_unavailable_raises_with_install_hint():
    """If pypfopt is unavailable, calling wrappers raises with a useful hint."""
    if pa.is_available():
        pytest.skip("pypfopt available; this test exercises the unavailable branch")
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"A": [0.01, 0.02], "B": [-0.01, 0.005]})
    with pytest.raises(RuntimeError, match="not installed"):
        pa.hrp_weights(df)
    with pytest.raises(RuntimeError, match="not installed"):
        pa.mean_variance_weights(df)
    with pytest.raises(RuntimeError, match="not installed"):
        pa.ledoit_wolf_covariance(df)


def _toy_returns():
    """Synthetic 3-asset, 250-period returns DataFrame for the integration tests."""
    pd = pytest.importorskip("pandas")
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(seed=42)
    n = 250
    # 3 uncorrelated-ish assets with different vols
    rets = rng.normal(loc=[0.0005, 0.001, 0.0002], scale=[0.01, 0.02, 0.005], size=(n, 3))
    return pd.DataFrame(rets, columns=["A", "B", "C"])


def test_ledoit_wolf_covariance_shape():
    if not pa.is_available():
        pytest.skip("pypfopt not installed")
    pytest.importorskip("pandas")
    df = _toy_returns()
    cov = pa.ledoit_wolf_covariance(df)
    assert cov.shape == (3, 3)
    # Symmetric, positive diagonal
    assert (cov.values.diagonal() > 0).all()
    # Symmetric within float tolerance
    assert ((cov.values - cov.values.T).max() < 1e-12)


def test_hrp_weights_sum_to_one():
    if not pa.is_available():
        pytest.skip("pypfopt not installed")
    pytest.importorskip("pandas")
    w = pa.hrp_weights(_toy_returns())
    assert set(w.keys()) == {"A", "B", "C"}
    assert all(0 <= v <= 1 for v in w.values())
    assert abs(sum(w.values()) - 1.0) < 1e-3


def test_hrp_lower_vol_gets_more_weight():
    """Sanity: HRP should down-weight the highest-vol asset."""
    if not pa.is_available():
        pytest.skip("pypfopt not installed")
    pytest.importorskip("pandas")
    w = pa.hrp_weights(_toy_returns())
    # Asset C has the lowest vol (0.005); it should NOT be the smallest weight.
    # Asset B has the highest vol (0.02); it should be the smallest.
    assert w["B"] <= w["A"] + 0.05
    assert w["B"] <= w["C"] + 0.05


def test_mean_variance_weights_sum_to_one():
    if not pa.is_available():
        pytest.skip("pypfopt not installed")
    pytest.importorskip("pandas")
    df = _toy_returns()
    w = pa.mean_variance_weights(df)
    assert set(w.keys()) == {"A", "B", "C"}
    assert abs(sum(w.values()) - 1.0) < 1e-3


def test_mean_variance_rejects_both_targets():
    if not pa.is_available():
        pytest.skip("pypfopt not installed")
    pytest.importorskip("pandas")
    df = _toy_returns()
    with pytest.raises(ValueError, match="at most one"):
        pa.mean_variance_weights(df, target_return=0.1, target_volatility=0.05)
