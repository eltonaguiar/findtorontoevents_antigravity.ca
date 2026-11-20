"""P0.11 denominator + asset-class exclusion policy + promotion-gate wiring."""
import json
from pathlib import Path

import pytest

from audit_trail.headline_basis import headline_basis

ROOT = Path(__file__).resolve().parent.parent


def test_headline_basis_arithmetic():
    b = headline_basis(19170, 7919, 142)
    assert b["headline_denominator"] == 7919
    assert b["closed_excluded_from_headline"] == 11251
    assert b["headline_covers_closed_pct"] == pytest.approx(41.31, abs=0.01)
    assert b["zero_pnl_share_pct"] == pytest.approx(1.79, abs=0.01)


def test_headline_basis_degenerate():
    b = headline_basis(0, 0, 0)
    assert b["headline_denominator"] == 0
    assert b["headline_covers_closed_pct"] is None
    assert b["zero_pnl_share_pct"] is None
    assert b["excluded_closed"] == 0


def test_headline_basis_never_negative():
    b = headline_basis(10, 12, 99)  # resolved > closed, flat > resolved
    assert b["closed_excluded_from_headline"] == 0
    assert b["zero_pnl_share_pct"] == 100.0


def test_headline_fields_present_in_generator():
    src = (ROOT / "audit_trail" / "dashboard_generator.py").read_text()
    assert "_headline_basis(total_closed, total_resolved, zero_pnl_count)" in src
    assert '"headline_denominator"' in (
        ROOT / "audit_trail" / "headline_basis.py"
    ).read_text()


def test_policy_covers_every_live_entry():
    policy = json.loads(
        (ROOT / "reports" / "policy_asset_class_exclusions_2026-11-20.json").read_text()
    )
    covered = {e["id"] for e in policy["entries"]}
    assert policy["ruling"] == "RESEARCH_ONLY"
    reg = json.loads((ROOT / "reports" / "hypothesis_registry.json").read_text())
    hyps = reg.get("hypotheses", reg)
    hyps = hyps if isinstance(hyps, list) else list(hyps.values())
    live = {
        h["id"]
        for h in hyps
        if h.get("asset_class") in ("MEME", "PENNY_STOCK", "CHEAP_STOCKS")
    }
    # every live entry must be covered by an explicit ruling; new ones force a decision
    assert live <= covered, f"unruled live entries: {sorted(live - covered)}"


def test_verdict_requires_dsr_and_pbo():
    from alpha_engine.money_ready_verdict import _verdict

    ok = dict(n=500, wr=0.60, pf=1.50, avg_win=5.0, avg_loss=1.0)
    good = {"ok": True}
    bad = {"ok": False}
    neutral = {"ok": None}
    assert _verdict(dsr=good, pbo=good, spa=bad, **ok) == "MONEY_READY"
    # A failing multiple-testing gate blocks MONEY_READY. With PF>=1 and the
    # WR/PF floors passing, the class lands in WATCH -- a measurable near-miss,
    # not a promotion. Recorded explicitly so nobody "fixes" it into NOT_READY
    # and hides a class that is merely unproven.
    assert _verdict(dsr=bad, pbo=good, spa=bad, **ok) == "WATCH"
    assert _verdict(dsr=good, pbo=bad, spa=bad, **ok) == "WATCH"
    # SPA may substitute for DSR and PBO (documented design), both must be
    # satisfied by *something* multiplicity-aware.
    assert _verdict(dsr=bad, pbo=bad, spa=good, **ok) == "MONEY_READY"
    assert _verdict(dsr=neutral, pbo=neutral, spa=neutral, **ok) == "WATCH"
    # PF<1 hard-routes to NOT_READY regardless of gates.
    assert _verdict(dsr=bad, pbo=bad, spa=bad, n=500, wr=0.60, pf=0.90,
                    avg_win=5.0, avg_loss=1.0) == "NOT_READY"
