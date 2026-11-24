import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.class_verdict_audit import audit, rederive  # noqa: E402


def row(**kw):
    """A class row shaped exactly like ledger classes[] entries."""
    base = {
        "asset_class": "TEST",
        "n": 6926,
        "required_n": 917,
        "wr": 0.3939,
        "pf": 0.7886,
        "pf_basis": "net",
        "net_expectancy_pct": -0.4183,
        "net_ci_pct": [-0.699, -0.1602],
        "net_ci_pct_2x": [-0.7984, -0.2595],
        "stress_2x_ok": False,
        "split_half": {"stable": False, "first_half_mean": -0.2871,
                       "second_half_mean": -0.5496},
        "top_symbol_share": 0.0858,
        "top_source_share": 0.5866,
        "verdict": "KILL",
        "alpha_gate": {"alpha_ci_lo": -0.9095, "alpha_coverage_ok": False,
                       "status": "unproven", "passed": False},
    }
    base.update(kw)
    return base


def test_insufficient_n_wins():
    assert rederive(row(n=37)) == "INSUFFICIENT_N"


def test_negative_ci_and_low_pf_is_kill():
    assert rederive(row()) == "KILL"


def test_negative_ci_but_pf_above_floor_is_weak():
    assert rederive(row(pf=0.95)) == "WEAK"


def test_positive_ci_but_fails_2x_stress():
    assert rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2,
                        stress_2x_ok=False)) == "CANDIDATE_CAP_2X_COST"


def test_positive_ci_2x_ok_but_unstable_halves():
    assert rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2, stress_2x_ok=True,
                        split_half={"stable": False,
                                    "first_half_mean": 0.2,
                                    "second_half_mean": -0.1})
                   ) == "CANDIDATE_CAP_HALVES"


def test_concentration_caps():
    assert rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2, stress_2x_ok=True,
                        split_half={"stable": True,
                                    "first_half_mean": 0.2,
                                    "second_half_mean": 0.2},
                        top_symbol_share=0.61)) == "CANDIDATE_CAP_CONCENTRATION"


def test_clean_row_is_candidate_never_more():
    v = rederive(row(net_ci_pct=[0.10, 0.40], pf=1.2, stress_2x_ok=True,
                     split_half={"stable": True,
                                 "first_half_mean": 0.2,
                                 "second_half_mean": 0.2},
                     top_symbol_share=0.2))
    assert v == "CANDIDATE"
    assert v not in ("PROVEN", "INVESTABLE")


def test_audit_flags_a_mismatch():
    r = row(verdict="WEAK")          # stored says WEAK, stats say KILL
    out = audit([r])
    assert out[0]["stored"] == "WEAK"
    assert out[0]["rederived"] == "KILL"
    assert out[0]["match"] is False


def test_audit_passes_when_consistent():
    out = audit([row()])             # stored KILL, rederived KILL
    assert out[0]["match"] is True
