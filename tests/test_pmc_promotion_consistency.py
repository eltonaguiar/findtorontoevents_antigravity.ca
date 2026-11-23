"""prediction_market_consensus promotion-state consistency (2026-11-23).

Why this exists
    Block 49 found the strategy with two promotion verdicts at once:
    ``prediction_market_consensus_pilot.json`` said ``promotion_ready: true``
    (``min_forward_n`` 50) while ``prediction_market_consensus_state.json`` and
    the dashboard said false (``min_forward_n`` 150). ``promotion_ready`` is
    what a human or an automation reads before putting money behind a strategy,
    and the forward replay for this family was REFUTED (true WR 38.2 pct), so a
    stale ``true`` is exactly how something gets deployed.

    The pilot's ``true`` came from counting 837 "resolved" picks, 774 of which
    were backfilled history resolved BEFORE the pilot started. Counted forward
    (resolved at/after the pilot start) it is n 63, WR 47.62, PF 1.05. The flag
    was true only because the gate was fed history and ignored accuracy.

    The contract enforced here, on the real committed files:
      1. ``promotion_ready`` is never true while forward n < min_forward_n.
      2. ``promotion_ready`` is never true while forward WR < min_wr.
      3. ``promotion_ready`` equals what the forward sample actually earns
         (n, WR, PF, drawdown) under the file's own criteria.
      4. The pilot file, the state file and the dashboard agree on the flag.
      5. Both files use the same promotion thresholds.
      6. The generator's PROMOTION_CRITERIA mirror the state file's, so the
         two gates cannot drift apart again.

    The forward sample is recomputed from the pilot's picks so a hand-edit of
    a stat cannot slip past; if the picks list changes, the guard follows it.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = ROOT / "verified_strategies" / "paper_pilot"
PILOT = PILOT_DIR / "prediction_market_consensus_pilot.json"
STATE = PILOT_DIR / "prediction_market_consensus_state.json"
DASH = PILOT_DIR / "prediction_market_consensus_dashboard.json"
GENERATOR = ROOT / "tools" / "prediction_market_consensus_pilot.py"

RESOLVED_STATUSES = ("WON", "LOST", "EXPIRED", "CLOSED", "FLAT")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _forward_sample(pilot: dict) -> dict:
    """Recompute the forward sample from the pilot's picks, date-precise."""
    start = (pilot.get("pilot_started_at") or "")[:10]
    rows = [
        p for p in pilot["picks"]
        if p.get("resolved_at") and p["resolved_at"][:10] >= start
        and p["status"] in RESOLVED_STATUSES
    ]
    n = len(rows)
    wins = sum(1 for p in rows if p["status"] == "WON")
    pnls = [p["pnl_pct"] for p in rows if p.get("pnl_pct") is not None]
    gross_win = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    pf = round(gross_win / gross_loss, 4) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)

    equity = peak = 100.0
    max_dd = 0.0
    for x in pnls:
        equity *= 1 + x / 100
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100)

    return {
        "n": n,
        "wr": round(wins / n * 100, 2) if n else 0.0,
        "pf": pf,
        "max_drawdown": round(max_dd, 2),
    }


@pytest.fixture(scope="module")
def pilot():
    return _load(PILOT)


@pytest.fixture(scope="module")
def state():
    return _load(STATE)


@pytest.fixture(scope="module")
def dash():
    return _load(DASH)


@pytest.fixture(scope="module")
def criteria(state):
    return state["promotion_criteria"]


def test_not_ready_below_forward_n(pilot, criteria):
    fwd = _forward_sample(pilot)
    if pilot["promotion_ready"]:
        assert fwd["n"] >= criteria["min_forward_n"], (
            f"{PILOT.name} says promotion_ready true at forward n={fwd['n']} "
            f"< min_forward_n={criteria['min_forward_n']}")


def test_not_ready_below_min_wr(pilot, criteria):
    fwd = _forward_sample(pilot)
    if pilot["promotion_ready"]:
        assert fwd["wr"] >= criteria["min_wr"], (
            f"{PILOT.name} says promotion_ready true at forward WR={fwd['wr']} "
            f"< min_wr={criteria['min_wr']} (accuracy is a promotion criterion)")


def test_flag_matches_the_forward_evidence(pilot, criteria):
    fwd = _forward_sample(pilot)
    earned = (
        fwd["n"] >= criteria["min_forward_n"]
        and fwd["wr"] >= criteria["min_wr"]
        and fwd["pf"] >= criteria["min_pf"]
        and fwd["max_drawdown"] <= criteria["max_drawdown_pct"]
    )
    assert pilot["promotion_ready"] is earned, (
        f"{PILOT.name} promotion_ready={pilot['promotion_ready']} but the forward "
        f"sample {fwd} under {criteria} earns {earned}")


def test_pilot_state_and_dashboard_agree(pilot, state, dash):
    flags = {
        PILOT.name: pilot["promotion_ready"],
        STATE.name: state["promotion_ready"],
        DASH.name: dash["promotion_ready"],
    }
    assert len(set(flags.values())) == 1, f"promotion verdicts disagree: {flags}"


def test_both_files_use_the_same_thresholds(pilot, state):
    a = pilot["promotion_criteria"]
    b = state["promotion_criteria"]
    assert a["min_forward_n"] == b["min_forward_n"], (a, b)
    assert a["min_wr_pct"] == b["min_wr"], (a, b)
    assert a["min_pf"] == b["min_pf"], (a, b)
    assert a.get("max_drawdown_pct") == b["max_drawdown_pct"], (a, b)


def test_generator_constants_match_state_file(state):
    spec = importlib.util.spec_from_file_location("pmc_generator", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    gen = mod.PROMOTION_CRITERIA
    sf = state["promotion_criteria"]
    assert gen["min_forward_n"] == sf["min_forward_n"], (gen, sf)
    assert gen["min_wr_pct"] == sf["min_wr"], (gen, sf)
    assert gen["min_pf"] == sf["min_pf"], (gen, sf)
    assert gen["max_drawdown_pct"] == sf["max_drawdown_pct"], (gen, sf)
