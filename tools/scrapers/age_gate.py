#!/usr/bin/env python3
"""
age_gate.py — strict "16+ only" audience gate for the findtorontoevents.ca feed.

Policy (operator decision, 2026-10-10 — see updates/
2026-10-10-age-gate-16plus-and-thumbnail-banner-crop.md):

    Drop an event when its audience can be determined to include ANYONE
    under 16. If the age cannot be determined, KEEP the event.

Evidence consulted, in priority order:

    1. Structured audience/type tags and categories the scrapers attach
       (e.g. "Preschool Children (0-5)", "Teens (13-17)", "Family").
    2. Numeric age ranges written in the title or description
       ("Ages 0 to 6", "ages 4-12", "6-10 years old").
    3. School grades / early-years wording ("Grade 3", "Kindergarten", "JK").
    4. Narrow, high-precision kid-program words in the TITLE only
       ("EarlyON", "toddler", "storytime"). Title matching is deliberately
       kept narrow: scanning 4,480 feed events that carry no audience tag,
       broad words like "child"/"baby" matched nightlife/adult talks
       ("Bi-Bi-Baby: Bi's Gone WILD", "Therapeutic Support for Adult
       Survivors of Child Sexual Abuse") — false positives the narrow set
       does not produce.

Every call returns a reason string (used for audit logging) or None to keep.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

MIN_AGE = 16

# ── 1. Structured audience evidence ──────────────────────────────────────────
# Exact tag strings as emitted by the BiblioCommons gateway (TPL), plus the
# short forms used by ROM / Harbourfront / Eventbrite scrapers.
UNDER16_TAGS = {
    "Preschool Children (0-5)",
    "School Age Children (6-12)",
    "Children",
    "Kids",
}
# Teens/Youth admit 13-15 year olds, so their floor is below 16.
TEEN_TAGS = {
    "Teens (13-17)",
    "Youth",
}
# Strict mode: "All Ages"/"Family" events are not 16+ events either.
ALL_AGES_TAGS = {
    "Family",
    "All Ages",
}
# Categories follow the same rule (the TPL categoriser tags kids/teen/family
# programme types with "Family"). The keyword categoriser is noisy though — it
# also files "Gentle Group Exercise for Seniors" and "Public Speaking for
# Newcomers" under Family — so the category rule yields to an explicit adult
# audience tag when one is present.
UNDER16_CATEGORIES = {"Family"}
ADULT_TAGS = {"Adults (18+)", "Older Adults", "Younger Adults (18-24)"}

TAG_REASON = {t: f"audience tag {t!r} is under-16" for t in UNDER16_TAGS}
TAG_REASON.update({t: f"audience tag {t!r} admits ages under 16" for t in TEEN_TAGS})
TAG_REASON.update({t: f"audience tag {t!r} is an all-ages/family event" for t in ALL_AGES_TAGS})

# ── 2. Numeric ages in free text ─────────────────────────────────────────────
# "Ages 6 to 12" / "ages 6-12" / "ages 6 & up" style ranges.
AGE_RANGE_RE = re.compile(
    r"\bages?\b[\s:–—-]*(\d{1,2})\s*(?:-|–|—|\bto\b|through|&|\band\b)\s*(\d{1,2})",
    re.IGNORECASE,
)
# A single lower bound: "ages 6", "ages 6+", "ages 6 and up". The negative
# lookahead stops it firing when the number is actually the start of a range
# (already handled by AGE_RANGE_RE).
AGE_MIN_RE = re.compile(
    r"\bages?\b[\s:–—-]*(\d{1,2})\b"
    r"(?!\s*(?:-|–|—|\bto\b|through|&|\band\b)\s*\d)",
    re.IGNORECASE,
)
# "6-10 years old" / "4 to 12 years"
YEARS_RE = re.compile(
    r"\b(\d{1,2})\s*(?:-|–|—|\bto\b)\s*(\d{1,2})\s*years?\b(?!\s*(?:old|age))",
    re.IGNORECASE,
)
YEARS_MIN_RE = re.compile(r"\b(?:up to|under|younger than|below)\s+(\d{1,2})\s*years?\b", re.IGNORECASE)

# ── 3. Grades / early years ──────────────────────────────────────────────────
GRADE_RE = re.compile(r"\b(?:grade|gr\.?)\s*([1-9]|1[0-2])\b", re.IGNORECASE)
EARLY_WORDS_RE = re.compile(
    r"\b(kindergarten|nursery school|preschool|pre-school|junior kindergarten|"
    r"senior kindergarten|\bjk\b|\bsk\b)\b",
    re.IGNORECASE,
)

# ── 4. Narrow title keywords ─────────────────────────────────────────────────
TITLE_KID_RE = re.compile(
    r"\b(earlyon|early\s*on|toddler[s]?|preschool(er)?|story\s*time|storytime|"
    r"baby\s*time|kids?[\' ]+(club|night|zone)|for\s+kids|for\s+children|"
    r"teens?|youth)\b",
    re.IGNORECASE,
)


def _clean(event: Dict) -> str:
    title = event.get("title") or ""
    desc = event.get("description") or ""
    return f"{title}\n{desc}"


def age_gate_reason(event: Dict) -> Optional[str]:
    """Return why `event` must be dropped under the 16+ policy, else None."""
    tags = [t for t in (event.get("tags") or []) if isinstance(t, str)]
    for tag in tags:
        if tag in TAG_REASON:
            return TAG_REASON[tag]

    if not (ADULT_TAGS & set(tags)):
        for cat in (event.get("categories") or []):
            if isinstance(cat, str) and cat in UNDER16_CATEGORIES:
                return f"category {cat!r} is an under-16 audience"

    text = _clean(event)

    m = AGE_RANGE_RE.search(text)
    if m:
        lo = min(int(m.group(1)), int(m.group(2)))
        if lo < MIN_AGE:
            return f"stated age range {m.group(0)!r} starts below {MIN_AGE}"
    m = AGE_MIN_RE.search(text)
    if m and int(m.group(1)) < MIN_AGE:
        return f"stated minimum age {m.group(0)!r} is below {MIN_AGE}"

    m = YEARS_RE.search(text)
    if m and min(int(m.group(1)), int(m.group(2))) < MIN_AGE:
        return f"stated age range {m.group(0)!r} starts below {MIN_AGE}"
    m = YEARS_MIN_RE.search(text)
    if m and int(m.group(1)) < MIN_AGE:
        return f"stated upper age limit {m.group(0)!r} is below {MIN_AGE}"

    m = GRADE_RE.search(text)
    if m:
        grade = int(m.group(1))
        # Grade 10 is roughly age 15-16, so anything up to grade 10 admits
        # under-16s; grade 11/12 (16-18) is allowed to stay.
        if grade <= 10:
            return f"school grade {m.group(0)!r} is under-16"

    if EARLY_WORDS_RE.search(text):
        return f"early-years wording {EARLY_WORDS_RE.search(text).group(0)!r}"

    m = TITLE_KID_RE.search(event.get("title") or "")
    if m:
        return f"kids/teen programme in title ({m.group(0)!r})"

    return None


def apply_age_gate(
    events: List[Dict],
    log_path: Optional[str] = None,
    sample_per_reason: int = 5,
) -> Tuple[List[Dict], Dict]:
    """Split `events` into (kept, summary).

    `summary` counts drops per reason and keeps up to `sample_per_reason`
    example titles per reason so the workflow log doubles as an audit trail.
    When `log_path` is set, every dropped event is appended there as JSONL.
    """
    kept: List[Dict] = []
    reasons: Counter = Counter()
    samples: Dict[str, List[str]] = {}
    log_fh = open(log_path, "a", encoding="utf-8") if log_path else None
    try:
        for ev in events:
            if not isinstance(ev, dict):
                kept.append(ev)
                continue
            reason = age_gate_reason(ev)
            if reason is None:
                kept.append(ev)
                continue
            reasons[reason] += 1
            bucket = samples.setdefault(reason, [])
            if len(bucket) < sample_per_reason:
                bucket.append(ev.get("title") or "<untitled>")
            if log_fh:
                log_fh.write(
                    json.dumps(
                        {
                            "id": ev.get("id"),
                            "title": ev.get("title"),
                            "date": ev.get("date"),
                            "source": ev.get("source"),
                            "reason": reason,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    finally:
        if log_fh:
            log_fh.close()

    summary = {
        "total_in": len(events),
        "dropped": sum(reasons.values()),
        "kept": len(kept),
        "reasons": dict(reasons.most_common()),
        "samples": samples,
        "log_path": log_path,
    }
    return kept, summary


def format_summary(summary: Dict) -> str:
    lines = [
        "[age-gate] 16+ filter: {dropped} dropped / {total_in} in "
        "({kept} kept)".format(**summary)
    ]
    for reason, count in summary["reasons"].items():
        lines.append(f"[age-gate]   {count:6d}  {reason}")
        for title in summary.get("samples", {}).get(reason, []):
            lines.append(f"[age-gate]            e.g. {title}")
    if summary.get("log_path"):
        lines.append(f"[age-gate] full audit log: {summary['log_path']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "next/events.json"
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    events = data if isinstance(data, list) else data.get("events", [])
    kept, summ = apply_age_gate(events, log_path=sys.argv[2] if len(sys.argv) > 2 else None)
    print(format_summary(summ))
    print(f"[age-gate] {path}: {len(events)} -> {len(kept)}")
