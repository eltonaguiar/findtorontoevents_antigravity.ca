"""A class with no trial-count baseline must SKIP the DSR gate, never pass it.

Before 2026-11-21, ``_dsr_gate`` looked the class baseline up with
``NB_TRIALS_BY_CLASS.get(_cls, 1)`` with the
comment "we're testing the class aggregate, not a selected-best strategy".
``NB_TRIALS_BY_CLASS`` existed at module level and was never read. A Deflated
Sharpe Ratio with ``nb_trials=1`` applies *zero* multiple-testing correction, so
EQUITY / ETF / BOND — classes with no recorded trial count — reported
``ok=True`` on a number that had never been deflated. The absence of a baseline
was being rendered as evidence of edge.

Contract now: no baseline -> ``ok=None`` + ``skipped=True`` + a note naming the
missing input, and ``_verdict`` cannot promote on it (SPA may still carry the
class, because SPA is family-wise).

Offline: no DB, no network.
"""

from alpha_engine.money_ready_verdict import (
    NB_TRIALS_BY_CLASS,
    _dsr_gate,
    _verdict,
)

# n=80, positive mean, non-degenerate variance.
RETURNS = [0.4, -0.2] * 40


def test_class_without_baseline_is_skipped_not_passed():
    # MUTUAL_FUND is the remaining class with no tested strategy cell; EQUITY
    # gained a measured baseline on 2026-11-21 (tests/test_dsr_trial_baselines.py).
    r = _dsr_gate(RETURNS, "MUTUAL_FUND")
    assert r["ok"] is None, "a class with no trial baseline must not report a pass"
    assert r.get("skipped") is True
    assert r["dsr_score"] is None, "no undeflated score may be published"
    assert "baseline" in r["note"].lower()


def test_missing_asset_class_is_skipped():
    r = _dsr_gate(RETURNS)
    assert r["ok"] is None and r.get("skipped") is True
    assert r["nb_trials"] is None


def test_class_with_baseline_actually_uses_it():
    r = _dsr_gate(RETURNS, "CRYPTO")
    # A baseline exists, so this is a computed result, not a skip — whatever the
    # computation returns for this fixture's moments.
    assert r.get("skipped") is not True
    assert r["nb_trials"] >= NB_TRIALS_BY_CLASS["CRYPTO"] > 1
    if r["ok"] is None:
        # The alternating fixture has degenerate higher moments; failing closed
        # is correct, and it must still say why.
        assert r["note"], "a null ok must carry a reason"


def test_baseline_lookup_is_case_insensitive():
    assert _dsr_gate(RETURNS, "crypto")["nb_trials"] == NB_TRIALS_BY_CLASS["CRYPTO"]


def test_every_baseline_class_has_at_least_two_trials():
    """A baseline of 1 would silently reintroduce the undeflated pass."""
    for cls, n in NB_TRIALS_BY_CLASS.items():
        assert n >= 2, f"{cls} baseline {n} applies no correction"


def test_skipped_dsr_cannot_reach_money_ready_on_its_own():
    ok = dict(n=500, wr=0.60, pf=1.50, avg_win=5.0, avg_loss=1.0)
    skipped = {"ok": None, "skipped": True}
    verdict = _verdict(dsr=skipped, pbo={"ok": True}, spa={"ok": False}, **ok)
    assert verdict != "MONEY_READY"
    # SPA is family-wise, so it may still carry the class — documented design.
    assert _verdict(dsr=skipped, pbo={"ok": True}, spa={"ok": True}, **ok) == "MONEY_READY"
