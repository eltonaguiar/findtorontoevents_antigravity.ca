"""Tests for tools/mutation_lifecycle_runner.py.

Synthetic mutation/closed-picks fixtures cover:
- promote-eligible (own stats meet gate)
- promote artifact-flagged (WR > 90%)
- kill-eligible by PF
- kill-eligible by WR (n>=100 path)
- hold (small n, own stats present but below promote_min_trades)
- hold (own stats null, mutation too young to expire)
- stale_expire (own stats null, age > stale_days)
- asset-class gate (FOREX requires tighter promote criteria)

Also asserts:
- dry-run does not mutate the input document
- apply_to_doc correctly flips status
- evaluate is idempotent: running it twice on a doc that already has
  applied transitions produces zero new transitions.
"""

from __future__ import annotations

import copy
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make sure tools/ is importable when running pytest from repo root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mutation_lifecycle_runner import (  # noqa: E402
    LifecycleThresholds,
    apply_to_doc,
    evaluate,
)


NOW = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)


def _mut(name: str, parent: str, *, days_old: int = 5, mtype: str = "inverse",
         parent_wr: float = 0.30, parent_trades: int = 100,
         status: str = "active", generation: int = 1) -> dict:
    return {
        "parent": parent,
        "type": mtype,
        "generation": generation,
        "status": status,
        "mutated_strategy_name": name,
        "created_at": (NOW - timedelta(days=days_old)).isoformat(),
        "parent_wr": parent_wr,
        "parent_trades": parent_trades,
        "params": {},
    }


def _picks(strategy: str, *, n: int, wins: int, avg_win: float = 0.02,
           avg_loss: float = -0.015, asset_class: str = "CRYPTO") -> list[dict]:
    """Build n closed-pick rows for a strategy with the given win count."""
    out: list[dict] = []
    for i in range(n):
        is_win = i < wins
        out.append({
            "strategy": strategy,
            "status": "WON" if is_win else "LOST",
            "pnl_pct": avg_win if is_win else avg_loss,
            "asset_class": asset_class,
        })
    return out


def _build_doc(*muts: dict) -> dict:
    return {
        "generated_at": NOW.isoformat(),
        "candidates": [],
        "donors": [],
        "mutations": list(muts),
        "promoted": [],
        "killed": [],
        "summary": {},
    }


# ---------------------------------------------------------------------------
# Decision matrix
# ---------------------------------------------------------------------------


def test_promote_when_own_stats_meet_gate():
    mut = _mut("good_mut_g1", "parent_a")
    doc = _build_doc(mut)
    picks = _picks("good_mut_g1", n=40, wins=24)  # 60% WR, healthy PF
    report = evaluate(doc, picks, now=NOW)
    assert report.n_promote_candidates == 1
    assert report.n_kill_candidates == 0
    d = report.decisions[0]
    assert d.decision == "promote"
    assert d.n_picks == 40
    assert 0.55 < d.fwd_wr < 0.65


def test_artifact_flag_when_wr_above_cap():
    mut = _mut("too_good_mut_g1", "parent_a")
    doc = _build_doc(mut)
    # 100% WR on n=40 — must be flagged, never auto-promoted.
    picks = _picks("too_good_mut_g1", n=40, wins=40)
    report = evaluate(doc, picks, now=NOW)
    assert report.n_promote_candidates == 0
    assert report.n_flag_artifact == 1
    assert report.decisions[0].decision == "flag_artifact"


def test_kill_by_pf_when_n_50():
    mut = _mut("bad_pf_mut_g1", "parent_b")
    doc = _build_doc(mut)
    # PF very low: 5 wins of 0.02 vs 45 losses of -0.05 -> PF = 0.10/2.25 ~= 0.044
    picks = _picks("bad_pf_mut_g1", n=50, wins=5,
                   avg_win=0.02, avg_loss=-0.05)
    report = evaluate(doc, picks, now=NOW)
    assert report.n_kill_candidates == 1
    assert report.decisions[0].decision == "kill"
    assert report.decisions[0].fwd_pf < 0.7


def test_kill_by_wr_when_n_100():
    mut = _mut("bad_wr_mut_g1", "parent_c")
    doc = _build_doc(mut)
    # WR 25% on n=100, but PF arranged just above 0.7 so the WR-rule fires.
    # 25 wins * 0.06 = 1.5; 75 losses * -0.02 = -1.5; PF = 1.0 (>0.7) so
    # PF rule passes — only the WR rule triggers.
    picks = _picks("bad_wr_mut_g1", n=100, wins=25,
                   avg_win=0.06, avg_loss=-0.02)
    report = evaluate(doc, picks, now=NOW)
    d = report.decisions[0]
    assert d.decision == "kill"
    assert d.fwd_wr < 0.30
    assert d.fwd_pf >= 0.7  # confirm the WR path (not PF path) fired


def test_hold_when_n_below_promote_min_but_own_stats_present():
    mut = _mut("midband_mut_g1", "parent_d")
    doc = _build_doc(mut)
    picks = _picks("midband_mut_g1", n=20, wins=12)  # 60% WR but n<30
    report = evaluate(doc, picks, now=NOW)
    assert report.n_hold == 1
    assert report.decisions[0].decision == "hold"


def test_hold_when_young_no_own_picks():
    mut = _mut("fresh_mut_g1", "parent_e", days_old=5)
    doc = _build_doc(mut)
    report = evaluate(doc, [], now=NOW)
    assert report.n_hold == 1
    assert report.decisions[0].decision == "hold"


def test_stale_expire_when_old_no_own_picks():
    mut = _mut("ancient_mut_g1", "parent_f", days_old=45)
    doc = _build_doc(mut)
    report = evaluate(doc, [], now=NOW)
    assert report.n_stale_expire == 1
    assert report.decisions[0].decision == "stale_expire"


def test_forex_promote_requires_tighter_gate():
    """A FOREX mutation passes the default 30/50%/1.2 gate but should NOT
    promote until n>=50 + PF>=1.5 because the resolver bug taints WR there."""
    mut = _mut("fx_mut_g1", "fx_parent")
    doc = _build_doc(mut)
    # n=40, WR=60%, PF~1.6 — would promote on default thresholds, but for
    # FOREX must be held until n>=50 AND PF>=1.5. n still <50 here.
    picks = _picks("fx_mut_g1", n=40, wins=24,
                   avg_win=0.02, avg_loss=-0.012,
                   asset_class="FOREX")
    report = evaluate(doc, picks, now=NOW)
    assert report.n_promote_candidates == 0
    assert report.decisions[0].decision == "hold"


# ---------------------------------------------------------------------------
# Behavioural — dry-run preserves doc, apply mutates correctly, idempotence
# ---------------------------------------------------------------------------


def test_dry_run_does_not_mutate_input_doc():
    mut = _mut("good_mut_g1", "parent_a")
    doc = _build_doc(mut)
    snapshot = copy.deepcopy(doc)
    picks = _picks("good_mut_g1", n=40, wins=24)
    _ = evaluate(doc, picks, now=NOW)  # pure
    assert doc == snapshot, "evaluate() must not mutate its input"


def test_apply_flips_status_correctly():
    promote_mut = _mut("good_mut_g1", "parent_a")
    kill_mut = _mut("bad_mut_g1", "parent_b")
    stale_mut = _mut("ancient_mut_g1", "parent_c", days_old=45)
    doc = _build_doc(promote_mut, kill_mut, stale_mut)
    picks = (
        _picks("good_mut_g1", n=40, wins=24)
        + _picks("bad_mut_g1", n=60, wins=6,
                 avg_win=0.02, avg_loss=-0.05)
    )
    report = evaluate(doc, picks, now=NOW)
    new_doc = apply_to_doc(doc, report)

    by_name = {m["mutated_strategy_name"]: m for m in new_doc["mutations"]}
    assert by_name["good_mut_g1"]["status"] == "promoted"
    assert by_name["bad_mut_g1"]["status"] == "killed"
    assert by_name["ancient_mut_g1"]["status"] == "retired"
    assert len(new_doc["promoted"]) == 1
    # killed and stale_expire both append to 'killed' (with kill_reason).
    assert len(new_doc["killed"]) == 2
    reasons = {row.get("kill_reason") for row in new_doc["killed"]}
    assert "stale_no_data" in reasons
    assert "own_stats_failed_gate" in reasons

    # And the original input doc must remain untouched.
    assert doc["mutations"][0]["status"] == "active"


def test_idempotent_second_run_makes_no_new_transitions():
    """Running apply twice should not re-promote already-terminal rows."""
    promote_mut = _mut("good_mut_g1", "parent_a")
    doc = _build_doc(promote_mut)
    picks = _picks("good_mut_g1", n=40, wins=24)
    report1 = evaluate(doc, picks, now=NOW)
    doc1 = apply_to_doc(doc, report1)

    report2 = evaluate(doc1, picks, now=NOW)
    assert report2.n_promote_candidates == 0
    assert report2.n_kill_candidates == 0
    assert report2.n_already_terminal == 1
    doc2 = apply_to_doc(doc1, report2)
    # Nothing in 'promoted' should duplicate.
    assert len(doc2["promoted"]) == 1


def test_kill_min_n_50_floor():
    """Conservative kill floor — n=49 must hold even if PF is awful."""
    mut = _mut("borderline_mut_g1", "parent_a")
    doc = _build_doc(mut)
    picks = _picks("borderline_mut_g1", n=49, wins=4,
                   avg_win=0.02, avg_loss=-0.05)
    report = evaluate(doc, picks, now=NOW)
    assert report.n_kill_candidates == 0
    assert report.decisions[0].decision == "hold"
