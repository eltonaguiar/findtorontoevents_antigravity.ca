import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.write_public_status import STALE_HOURS, build_status  # noqa: E402

NOW = datetime(2026, 11, 20, 4, 0, tzinfo=timezone.utc)


def _ledger(age_h=0):
    gen = (NOW - timedelta(hours=age_h)).isoformat()
    return {
        "schema": "audit3.v1",
        "generated_at": gen,
        "coverage": {"scored_rows": 8769, "total_closed_picks": 16341,
                     "valid_closed_picks": 8769,
                     "valid_closed_picks_basis": "canonical_kept_rows",
                     "denominator": {"mode": "canonical"}},
        "summary": {"n_proven": 0, "n_candidate": 0, "n_weak": 59, "n_kill": 8},
        "persistence": {"available": True},
        "verdict_churn": {"n_flipped": 0, "n_tracked": 444},
        "denylist_hits": {"n": 55, "by_class": {"CRYPTO": 33, "COMMODITY": 8}},
        "forward_gate": {
            "enforced": True, "n_rows": 430,
            "pods": {"POD-A": {"eligible": False}},
            "hypotheses": {"H-119": {"eligible": False,
                                     "reasons": ["coverage 80% < 90%"]}},
        },
    }


def test_status_contract_fields_and_freshness():
    s = build_status(_ledger(age_h=1), None, now=NOW)
    assert s["schema"] == "audit3.public_status.v1"
    assert s["age_hours"] == 1.0 and s["stale"] is False
    assert s["coverage"]["mode"] == "canonical"
    assert s["coverage"]["valid_basis"] == "canonical_kept_rows"
    assert s["verdicts"]["kill"] == 8
    assert s["denials"]["n"] == 55
    assert s["forward"]["rows"] == 430 and s["forward"]["enforced"] is True
    assert s["forward"]["eligible_pods"] == 0
    assert s["forward"]["blocked"][0]["hypothesis"] == "H-119"


def test_status_marks_stale_past_threshold():
    s = build_status(_ledger(age_h=STALE_HOURS + 1), None, now=NOW)
    assert s["stale"] is True


def test_missing_generated_at_is_stale_not_crash():
    led = _ledger()
    led.pop("generated_at")
    s = build_status(led, None, now=NOW)
    assert s["stale"] is True and s["age_hours"] is None


def test_forward_gate_reasons_override_from_sidecar():
    fwd = {"by_hypothesis": {"H-119": {"gate": {
        "eligible": False, "reasons": ["net PF CI-LB 0.9213 <= 1.0"]}}}}
    s = build_status(_ledger(), fwd, now=NOW)
    assert "PF CI-LB" in s["forward"]["blocked"][0]["reason"]
