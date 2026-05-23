"""Wire-up regression test for ``.github/workflows/bond-agent.yml``.

The bond-agent workflow is the *scheduled emitter* for the BOND asset class
(daily on weekdays at 14:32 UTC). It must run every strategy registered in
``alpha_engine.bond_strategies.BOND_STRATEGIES`` so that newly added
strategies (e.g. ``bond_credit_spread_mean_reversion`` from PR #475) are
not silently orphaned when they exist in the registry but are not invoked
by the only thing that actually produces ``non_crypto_agent/data/bond_picks.json``.

Failure modes this test guards against:

  - A new strategy is added to ``BOND_STRATEGIES`` (so it shows up in
    ``alpha_engine/scanner.py`` via ``strategies.update(BOND_STRATEGIES)``)
    but the bond-agent.yml import block / iteration list is not updated.
    Result: the strategy is dead-code on the daily emitter even though
    it imports cleanly. This is exactly what happened between commits
    ``4c65e6698a`` (added credit-spread) and the wire-up fix on 2026-04-28.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_engine.bond_strategies import BOND_STRATEGIES


WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "bond-agent.yml"
)


@pytest.fixture(scope="module")
def workflow_text() -> str:
    assert WORKFLOW_PATH.exists(), f"bond-agent.yml missing at {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_all_registered_bond_strategies_are_invoked(workflow_text: str) -> None:
    """Every key in BOND_STRATEGIES must appear by name in the workflow.

    The workflow uses literal function names in both the ``from
    bond_strategies import (...)`` block and the ``for fn in [...]``
    iteration list. We only need each name to appear in the file at
    least once (covers both sites).
    """
    missing = [name for name in BOND_STRATEGIES if name not in workflow_text]
    assert not missing, (
        "bond-agent.yml does not invoke these registered strategies "
        f"(orphaned in scheduled emitter): {missing}. "
        "Add them to the import block + iteration list."
    )


def test_workflow_advertises_correct_strategy_count(workflow_text: str) -> None:
    """The ``strategies_run`` field in the JSON output should match
    the registered strategy count, so daily artifact metadata reflects
    reality (also exercises the perf_note self-doc).
    """
    expected = len(BOND_STRATEGIES)
    needle = f'"strategies_run": {expected}'
    assert needle in workflow_text, (
        f"Expected {needle!r} in bond-agent.yml; the registry has "
        f"{expected} strategies but the workflow advertises a different count."
    )


def test_bond_credit_spread_env_flag_is_set(workflow_text: str) -> None:
    """Regression guard for the 2026-04-30 wire-up.

    ``alpha_engine/bond_strategies.py:462`` gates
    ``bond_credit_spread_mean_reversion`` on ``BOND_ENABLE_CREDIT_SPREAD``
    (default OFF). Before this fix the env var only appeared inside a
    docstring / perf_note in the workflow — never in an ``env:`` block —
    so the strategy was imported, iterated, and silently returned ``[]``
    on every run. Empirically: 0 ``bond_credit_spread_mean_reversion``
    rows in ``audit_dashboard/data/dashboard_data.json`` for ~2 weeks
    after the strategy code merged.

    This pins the env-flag presence so a future YAML refactor can't
    silently drop it again.
    """
    assert "BOND_ENABLE_CREDIT_SPREAD: '1'" in workflow_text or \
           'BOND_ENABLE_CREDIT_SPREAD: "1"' in workflow_text, (
        "BOND_ENABLE_CREDIT_SPREAD must be set to '1' in bond-agent.yml's "
        "env block so bond_credit_spread_mean_reversion's gate can pass. "
        "If you intentionally disabled it, update updates/ and this test."
    )
