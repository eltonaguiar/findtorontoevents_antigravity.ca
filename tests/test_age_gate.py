#!/usr/bin/env python3
"""Tests for the strict 16+ audience gate (tools/scrapers/age_gate.py).

Policy under test: drop an event when its audience can be determined to
include anyone under 16; keep it when the age cannot be determined.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from scrapers.age_gate import (  # noqa: E402
    age_gate_reason,
    apply_age_gate,
    format_summary,
)


def _ev(**kw):
    base = {
        "id": "x",
        "title": "Some Event",
        "date": "2026-11-01T18:00:00Z",
        "description": "",
        "tags": [],
        "categories": [],
        "source": "Test",
    }
    base.update(kw)
    return base


# ── keep: age cannot be determined ───────────────────────────────────────────

def test_keeps_event_with_no_age_evidence():
    assert age_gate_reason(_ev(title="Evening Wine Tasting")) is None


def test_keeps_explicit_16_plus():
    assert age_gate_reason(_ev(description="Ages 16-18 welcome.")) is None


def test_keeps_adult_floor():
    assert age_gate_reason(_ev(description="For ages 18 and up.")) is None


def test_keeps_adult_audience_tags():
    assert age_gate_reason(_ev(tags=["Adults (18+)", "Older Adults"])) is None


# ── drop: numeric ages ───────────────────────────────────────────────────────

def test_drops_classic_kids_range():
    reason = age_gate_reason(_ev(title="Glow in the Dark Spooky Charms", description="Ages 9-12, drop in."))
    assert reason and "age range" in reason


def test_drops_open_ended_minor_floor():
    assert age_gate_reason(_ev(description="This program is for ages 13 and up."))


def test_drops_years_old_wording():
    assert age_gate_reason(_ev(description="Recommended for children 4 to 12 years."))


def test_drops_upper_limit_below_16():
    assert age_gate_reason(_ev(description="Up to 8 years old; caregiver must attend."))


# ── drop: structured audience tags / categories ──────────────────────────────

def test_drops_preschool_tag():
    assert age_gate_reason(_ev(tags=["Preschool Children (0-5)"]))


def test_drops_children_tag():
    assert age_gate_reason(_ev(tags=["Children"]))


def test_drops_teens_tag_because_floor_is_13():
    assert age_gate_reason(_ev(tags=["Teens (13-17)"]))


def test_drops_youth_tag():
    assert age_gate_reason(_ev(tags=["Youth"]))


def test_drops_family_tag_in_strict_mode():
    assert age_gate_reason(_ev(tags=["Family"]))


def test_drops_all_ages_tag_in_strict_mode():
    assert age_gate_reason(_ev(tags=["All Ages"]))


def test_drops_family_category_when_no_adult_tag():
    assert age_gate_reason(_ev(categories=["Arts", "Family"]))


def test_keeps_family_category_when_adult_tag_present():
    # The keyword categoriser files seniors/adult workshops under Family.
    reason = age_gate_reason(_ev(tags=["Older Adults"], categories=["Arts", "Family"]))
    assert reason is None


# ── drop: grades / early-years wording / title keywords ──────────────────────

def test_drops_low_grade():
    assert age_gate_reason(_ev(description="For students in Grade 3."))


def test_keeps_grade_11_and_12():
    assert age_gate_reason(_ev(description="Grade 11 and 12 students only.")) is None


def test_drops_kindergarten():
    assert age_gate_reason(_ev(description="Kindergarten playgroup."))


def test_drops_earlyon_title():
    assert age_gate_reason(_ev(title="EarlyON Family Fun Time"))


def test_keeps_adult_title_that_merely_mentions_child():
    # Broad keyword matching produced these false positives; narrow title
    # matching must not.
    assert age_gate_reason(_ev(title="Bi-Bi-Baby: Bi's Gone WILD", tags=["Party"])) is None
    assert age_gate_reason(
        _ev(title="Therapeutic Support for Adult Survivors of Child Sexual Abuse")
    ) is None


# ── apply_age_gate plumbing ──────────────────────────────────────────────────

def test_apply_age_gate_splits_and_counts():
    events = [
        _ev(id="1", title="Keep Me"),
        _ev(id="2", title="Drop Me", tags=["Kids"]),
        _ev(id="3", title="Drop Me Too", description="Ages 4-12"),
    ]
    kept, summary = apply_age_gate(events)
    assert [e["id"] for e in kept] == ["1"]
    assert summary["total_in"] == 3
    assert summary["dropped"] == 2
    assert summary["kept"] == 1
    assert sum(summary["reasons"].values()) == 2
    all_samples = [t for v in summary["samples"].values() for t in v]
    assert "Drop Me" in all_samples and "Drop Me Too" in all_samples


def test_age_gate_is_idempotent():
    events = [_ev(id="1", tags=["Preschool Children (0-5)"]), _ev(id="2")]
    once, _ = apply_age_gate(events)
    twice, _ = apply_age_gate(once)
    assert once == twice


def test_audit_log_written(tmp_path):
    log = tmp_path / "removed.jsonl"
    apply_age_gate([_ev(id="9", title="Baby Time", tags=["Children"])], log_path=str(log))
    lines = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    assert lines[0]["title"] == "Baby Time"
    assert "reason" in lines[0]


def test_format_summary_mentions_totals():
    _, summary = apply_age_gate([_ev(tags=["Kids"])])
    text = format_summary(summary)
    assert "16+ filter" in text and "1 dropped" in text
