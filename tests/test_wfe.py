"""Tests for tools.wfe.

Regression target (found 2026-11-20): the module docstring claimed the IS/OOS
split was performed "with embargo" while ``walk_forward_split`` was a plain
contiguous slice with no purge. A contiguous split leaks whenever labels
overlap in time -- the last IS observation and the first OOS observation can
describe the same price move -- which inflates WFE.

These tests fail on the old implementation: ``test_embargo_creates_a_gap``
asserts a boundary gap that a pure ``r[:k], r[k:]`` slice cannot produce.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.wfe import walk_forward_efficiency, walk_forward_split


# ---------------------------------------------------------------------------
# Split + embargo
# ---------------------------------------------------------------------------

def test_default_split_is_contiguous_70_30():
    r = np.arange(100.0)
    is_r, oos_r = walk_forward_split(r)
    assert len(is_r) == 70
    assert len(oos_r) == 30
    assert is_r[-1] == 69.0
    assert oos_r[0] == 70.0, "default must not purge (back-compat)"


def test_embargo_creates_a_gap():
    """The substantive fix: an embargoed split must drop boundary rows.

    A plain ``r[:k], r[k:]`` always yields ``oos[0] - is[-1] == 1``. With
    ``embargo=n`` the gap must be ``2n + 1`` because n observations are
    purged from each side.
    """
    r = np.arange(100.0)
    embargo = 5
    is_r, oos_r = walk_forward_split(r, embargo=embargo)

    assert len(is_r) == 65, "embargo must shorten the IS window"
    assert len(oos_r) == 25, "embargo must shorten the OOS window"

    gap = oos_r[0] - is_r[-1]
    assert gap == 2 * embargo + 1, (
        f"expected a {2 * embargo + 1}-wide boundary gap, got {gap}"
    )


def test_embargo_does_not_change_the_windows_beyond_the_boundary():
    """Purge only touches the boundary; the far ends stay identical."""
    r = np.arange(100.0)
    plain_is, plain_oos = walk_forward_split(r)
    emb_is, emb_oos = walk_forward_split(r, embargo=7)

    assert emb_is[0] == plain_is[0], "IS start must be unchanged"
    assert emb_is[1] == plain_is[1]
    assert emb_oos[-1] == plain_oos[-1], "OOS end must be unchanged"
    assert emb_oos[-2] == plain_oos[-2]


def test_embargo_zero_is_identical_to_omitting_it():
    r = np.random.default_rng(0).normal(size=50)
    a_is, a_oos = walk_forward_split(r)
    b_is, b_oos = walk_forward_split(r, embargo=0)
    assert np.array_equal(a_is, b_is)
    assert np.array_equal(a_oos, b_oos)


def test_negative_embargo_rejected():
    with pytest.raises(ValueError, match="embargo must be >= 0"):
        walk_forward_split(np.arange(50.0), embargo=-1)


def test_excessive_embargo_rejected_not_silently_truncated():
    """An embargo that empties a window must raise, never return a stub."""
    with pytest.raises(ValueError, match="too few observations"):
        walk_forward_split(np.arange(100.0), embargo=1000)


def test_embargo_boundary_case_keeps_two_observations():
    """Largest embargo that still leaves 2 rows per side must succeed."""
    r = np.arange(100.0)  # is=70, oos=30
    is_r, oos_r = walk_forward_split(r, embargo=28)
    assert len(is_r) == 42
    assert len(oos_r) == 2


# ---------------------------------------------------------------------------
# WFE ratio
# ---------------------------------------------------------------------------

def test_wfe_is_ratio_of_oos_to_is_sharpe():
    rng = np.random.default_rng(11)
    is_r = rng.normal(0.002, 0.01, 500)
    oos_r = rng.normal(0.001, 0.01, 200)
    wfe = walk_forward_efficiency(is_r, oos_r)
    assert 0.0 <= wfe <= 2.0


def test_wfe_clipped_to_two():
    """OOS Sharpe far above IS is noise, not skill -> clipped at 2.0."""
    rng = np.random.default_rng(3)
    is_r = rng.normal(0.0001, 0.02, 400)
    oos_r = rng.normal(0.05, 0.01, 400)
    assert walk_forward_efficiency(is_r, oos_r) == 2.0


def test_wfe_floor_zero_on_negative_oos():
    rng = np.random.default_rng(5)
    is_r = rng.normal(0.003, 0.01, 400)
    oos_r = rng.normal(-0.003, 0.01, 400)
    assert walk_forward_efficiency(is_r, oos_r) == 0.0


def test_wfe_returns_zero_on_short_input():
    assert walk_forward_efficiency([1.0, 2.0], [1.0]) == 0.0


def test_wfe_returns_zero_when_is_sharpe_is_zero():
    is_r = np.zeros(200)
    oos_r = np.random.default_rng(1).normal(0.001, 0.01, 200)
    assert walk_forward_efficiency(is_r, oos_r) == 0.0
