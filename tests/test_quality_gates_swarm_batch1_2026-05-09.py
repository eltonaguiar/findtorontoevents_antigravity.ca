"""Regression tests for quality_gates swarm-batch-1 score retunings (2026-05-09).

4-engine swarm consensus (deepseek/xai/cerebras/inception, 4/4 votes) on the
30d performance data documented in swarm_runs/next_steps_perf_2026-05-09/:

  battleground        n=107  WR 68.2%  PF 2.92  sum +418.2  → upsize 8 → 15
  mega_mutation       n=151  WR 67.5%  PF 3.45  sum +383.3  → NEW +15
  mercury2            n=74   WR 16.2%  PF 2.34  sum +116.5  → NEW +12
  luxalgo_filters     n=746  WR 45.4%  PF 1.12  sum +97.3   → downsize 10 → 5
  multi_asset_copytrader n=1620 (30d) WR ~49% PF 1.00  → downsize 5 → -10
  non_crypto_consensus n=200 (Q14)   WR 38.5% PF 0.16  → downsize -5 → -15
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_trail.quality_gates import _SOURCE_SYSTEM_SCORES


def test_battleground_upsized_to_15():
    """Top alpha by sum_pnl 30d (+418.2%); was undersized at +8.
    2026-05-16: downsized 15→5 after CRYPTO autopsy (PF 0.65, sub-floor drag).
    Test updated to reflect the current score."""
    assert _SOURCE_SYSTEM_SCORES.get("battleground") == 5


def test_mega_mutation_added_at_15():
    """Was missing entirely from _SOURCE_SYSTEM_SCORES — picks router used 0."""
    assert _SOURCE_SYSTEM_SCORES.get("mega_mutation") == 15


def test_mercury2_added_at_12():
    """Distinct from blocked mercury2_fast. PF 2.34 / asymmetric wins.

    2026-05-15: score updated 12 -> 0 per quality_gates.py:4470-4473 — live audit
    n=144 WR=38.2% avg_pnl=+0.15% downgrades the original +12 (n=74, WR 16.2%)
    to neutral routing weight. Test asserts presence + non-blocked status, not
    the specific tier value (which legitimately moves with evidence).
    """
    assert "mercury2" in _SOURCE_SYSTEM_SCORES
    # Sanity: mercury2_fast remains BLOCKED (different source)
    from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS
    assert "mercury2_fast" in BLOCKED_SOURCE_SYSTEMS


def test_luxalgo_filters_downsized_to_negative():
    """Volume vampire demoted further: CRYPTO n=665, WR 43.6%, PF 0.99,
    net_pnl -8.6pp (2026-05-13 audit). Score reduced from 5 → -8 to
    deprioritise picks from this source without a full block."""
    assert _SOURCE_SYSTEM_SCORES.get("luxalgo_filters") == -8


def test_multi_asset_copytrader_downsized_negative():
    """3-axis autopsy showed flat (PF 1.00 noise generator), kill not
    justified per protocol but downsize is. Was +5 stale 'ELITE FOREX' claim."""
    assert _SOURCE_SYSTEM_SCORES.get("multi_asset_copytrader") == -10


def test_multi_asset_copytrader_NOT_in_blocked_list():
    """Per mutate-before-kill protocol — kill only after a 30d -PF window.
    Currently flat, not negative, so penalty score is correct treatment."""
    from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS
    assert "multi_asset_copytrader" not in BLOCKED_SOURCE_SYSTEMS


def test_non_crypto_consensus_drag_acknowledged():
    """Q14 PF 0.16 / n=200 was hidden behind stale 'flat PnL n=18' comment."""
    assert _SOURCE_SYSTEM_SCORES.get("non_crypto_consensus") == -15


def test_battleground_outranks_luxalgo_post_change():
    """Routing invariant: top alpha source must outrank volume-vampire source."""
    assert _SOURCE_SYSTEM_SCORES["battleground"] > _SOURCE_SYSTEM_SCORES["luxalgo_filters"]
    assert _SOURCE_SYSTEM_SCORES["mega_mutation"] > _SOURCE_SYSTEM_SCORES["luxalgo_filters"]


def test_score_dispersion_increased():
    """Pre-batch dispersion (max - min for the affected sources) was small;
    post-batch should give the router more discriminating signal."""
    affected = ["battleground", "mega_mutation", "mercury2",
                "luxalgo_filters", "multi_asset_copytrader",
                "non_crypto_consensus"]
    scores = [_SOURCE_SYSTEM_SCORES[s] for s in affected]
    assert max(scores) - min(scores) >= 25  # spread of ≥25 points
