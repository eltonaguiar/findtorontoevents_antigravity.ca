"""Absolute OPEN-bloat gate (P0, 2026-11-16 cross-PC data-quality fleet).

Fixtures pinned by the fleet finding:
    91,855 open / 21 active -> FAIL  (the incident ledger)
        21 open / 21 active -> GREEN
       300 open / 21 active -> GREEN
"""
from datetime import datetime, timezone, timedelta

from audit_trail.quality_gates import (
    OPEN_BLOAT_PREDICATE,
    check_open_bloat_health,
    evaluate_open_bloat_gate,
)


# ---------------------------------------------------------------------------
# Pure gate fixtures (the contract)
# ---------------------------------------------------------------------------

def test_fleet_fixture_91855_open_21_active_fails() -> None:
    gate = evaluate_open_bloat_gate(91855, 21)
    assert gate["tier"] == "FAIL"
    assert gate["bloated"] is True
    assert gate["tier_cap"] == "FAIL"


def test_fixture_21_open_21_active_green() -> None:
    gate = evaluate_open_bloat_gate(21, 21)
    assert gate["tier"] == "GREEN"
    assert gate["bloated"] is False
    assert gate["tier_cap"] is None


def test_fixture_300_open_21_active_green() -> None:
    gate = evaluate_open_bloat_gate(300, 21)
    assert gate["tier"] == "GREEN"
    assert gate["bloated"] is False


def test_bloat_message_format() -> None:
    gate = evaluate_open_bloat_gate(91855, 21)
    assert gate["message"] == (
        "OPEN bloat: 91855 open vs 21 active — resolver backlog"
    )


def test_predicate_text() -> None:
    assert OPEN_BLOAT_PREDICATE == "open_count > max(500, 10 * active_count)"
    gate = evaluate_open_bloat_gate(91855, 21)
    assert gate["predicate"] == OPEN_BLOAT_PREDICATE


# ---------------------------------------------------------------------------
# Threshold boundary semantics: max(500, 10 * active_count)
# ---------------------------------------------------------------------------

def test_absolute_floor_boundary_at_21_active() -> None:
    # limit = max(500, 10*21=210) = 500 -> 500 green, 501 fails
    assert evaluate_open_bloat_gate(500, 21)["tier"] == "GREEN"
    assert evaluate_open_bloat_gate(501, 21)["tier"] == "FAIL"


def test_ratio_leg_scales_with_active_count() -> None:
    # limit = max(500, 10*200=2000) = 2000: 1500 green (over the 500 floor but
    # healthy for a 200-active book), 2001 fails (ratio bloat at scale).
    assert evaluate_open_bloat_gate(1500, 200)["tier"] == "GREEN"
    assert evaluate_open_bloat_gate(1500, 200)["limit"] == 2000
    assert evaluate_open_bloat_gate(2001, 200)["tier"] == "FAIL"


def test_zero_active_uses_floor() -> None:
    assert evaluate_open_bloat_gate(500, 0)["tier"] == "GREEN"
    assert evaluate_open_bloat_gate(501, 0)["tier"] == "FAIL"


def test_negative_active_clamped_to_floor() -> None:
    assert evaluate_open_bloat_gate(501, -5)["tier"] == "FAIL"
    assert evaluate_open_bloat_gate(501, -5)["limit"] == 500


# ---------------------------------------------------------------------------
# Wiring: check_open_bloat_health verdict is capped on absolute bloat
# ---------------------------------------------------------------------------

def _picks(open_n: int, active_n: int, closed_n: int) -> list[dict]:
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = [{"id": f"o{i}", "status": "OPEN", "timestamp": old} for i in range(open_n)]
    rows += [{"id": f"a{i}", "status": "ACTIVE", "timestamp": old} for i in range(active_n)]
    rows += [{"id": f"c{i}", "status": "CLOSED", "timestamp": old} for i in range(closed_n)]
    return rows


def test_monitor_capped_on_absolute_bloat_despite_fine_ratio() -> None:
    # Ratio-only view: 600 open of 2000 = 30% -> "healthy". The absolute gate
    # (600 open vs 0 active -> 600 > max(500, 0)) must cap the verdict.
    result = check_open_bloat_health(_picks(open_n=600, active_n=0, closed_n=1400))
    assert result["status"] == "pause"
    assert result["action"] == "OPEN bloat: 600 open vs 0 active — resolver backlog"
    assert result["open_bloat_gate"]["bloated"] is True
    assert result["open_bloat_gate"]["tier"] == "FAIL"


def test_monitor_passes_clean_book_through() -> None:
    result = check_open_bloat_health(_picks(open_n=10, active_n=5, closed_n=50))
    assert result["status"] == "healthy"
    assert result["open_bloat_gate"]["bloated"] is False
    assert result["open_bloat_gate"]["tier"] == "GREEN"


def test_monitor_splits_open_and_active_counts() -> None:
    # 91855-open/21-active shape at reduced scale: 605 stuck OPEN + 5 ACTIVE.
    gate = check_open_bloat_health(_picks(open_n=605, active_n=5, closed_n=0))[
        "open_bloat_gate"
    ]
    assert gate["open_count"] == 605
    assert gate["active_count"] == 5
    assert gate["tier"] == "FAIL"
