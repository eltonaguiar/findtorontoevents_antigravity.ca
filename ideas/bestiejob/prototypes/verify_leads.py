#!/usr/bin/env python3
"""Offline verification stub for normalized BESTIEJOB lead records.

Purpose: apply deterministic, no-network checks to move leads toward
pass/review/reject states with explicit reasons (per VERIFICATION_STAGE.md).

Input: JSON array or JSONL of normalized records (e.g. normalize_lead.py output).
Output: JSONL records with added/updated `verification` and adjusted review hints.
Optionally writes a JSON summary with --summary.

Checks (offline, no HTTP): identity/URL shape, dedupe key, date evidence (absolute
posted_at vs raw time fields), geo/eligibility/confirm/exclude signals, track/cert
evidence presence, basic liveness hints, rights placeholder.

Does NOT fetch pages, does NOT fabricate posted_at, does NOT mark network failures
as dead. Promote to publish only after authoritative verification + rights + merge rules.

No deps, no network.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?$")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_records(path: Path):
    data = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(data)
        if isinstance(obj, list):
            yield from obj
            return
    except json.JSONDecodeError:
        pass
    for line in data.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def valid_http_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def is_absolute_date(val: str | None) -> bool:
    if not val or not isinstance(val, str):
        return False
    v = val.strip()
    if not ISO_RE.match(v):
        return False
    try:
        # basic parseability
        if len(v) == 10:
            datetime.strptime(v, "%Y-%m-%d")
        else:
            x = v.replace("Z", "+00:00")
            datetime.fromisoformat(x)
        return True
    except Exception:
        return False


def verify(rec: dict) -> dict:
    out = dict(rec)
    reasons: list[str] = []
    gates: dict[str, str] = {}
    identity = out.get("identity") or {}
    urls = out.get("urls") or {}
    dates = dict(out.get("dates") or {})
    loc = out.get("location") or {}
    elig = (loc.get("eligible") or {}) if isinstance(loc, dict) else {}
    cls = out.get("classification") or {}
    tracks = cls.get("tracks") or []
    liveness = dict(out.get("liveness") or {})
    rights = dict(out.get("rights") or {})

    # identity / urls
    if not identity.get("dedupe_key"):
        reasons.append("missing_dedupe_key")
        gates["identity"] = "review"
    else:
        gates["identity"] = "pass"

    posting = urls.get("posting")
    if valid_http_url(posting):
        gates["posting_url"] = "pass"
    else:
        reasons.append("invalid_or_missing_posting_url")
        gates["posting_url"] = "review"

    # dates
    posted_at = dates.get("posted_at")
    raw_time = dates.get("time_value_raw")
    time_field = dates.get("time_field")
    if is_absolute_date(posted_at):
        gates["date"] = "pass"
    elif raw_time:
        reasons.append(f"unverified_date_evidence:{time_field or 'unknown_field'}")
        gates["date"] = "review"
    else:
        reasons.append("missing_posted_date_evidence")
        gates["date"] = "review"
    # never fabricate
    if posted_at and not is_absolute_date(posted_at):
        dates["posted_at"] = None
        reasons.append("posted_at_not_absolute_reset_null")

    # geo / eligibility
    if elig.get("exclude_signal"):
        reasons.append("geo_excluded_signal")
        gates["geo_eligibility"] = "reject"
    elif elig.get("needs_confirm"):
        reasons.append("geo_needs_confirm")
        gates["geo_eligibility"] = "review"
    elif elig.get("toronto_gta_local") or elig.get("canada_remote_signal") or elig.get("ontario_eligible_signal"):
        gates["geo_eligibility"] = "pass"
    else:
        reasons.append("geo_unknown_or_out_of_scope")
        gates["geo_eligibility"] = "review"

    # duty/track evidence (pre-verify signal quality)
    max_score = 0
    scores = cls.get("track_scores") or {}
    if isinstance(scores, dict) and scores:
        try:
            max_score = max(int(v or 0) for v in scores.values())
        except Exception:
            max_score = 0
    has_track = bool(tracks) or max_score > 0
    if not has_track:
        reasons.append("no_track_match_signal")
        gates["track_evidence"] = "review"
    elif max_score and max_score < 2:
        reasons.append("weak_track_signal")
        gates["track_evidence"] = "review"
    else:
        gates["track_evidence"] = "pass"

    # liveness (offline hints only)
    state = str(liveness.get("state") or "unknown").lower()
    if state in {"dead", "removed", "closed"} or liveness.get("http_status") in {404, 410, 451}:
        reasons.append("liveness_dead_or_removed_hint")
        gates["liveness"] = "reject"
    elif state in {"listed", "live"}:
        gates["liveness"] = "review"  # still needs authoritative check
        reasons.append("liveness_needs_authoritative_check")
    else:
        gates["liveness"] = "review"
        reasons.append("liveness_unknown_offline")

    # rights
    reuse = str(rights.get("reuse") or "unknown").lower()
    if reuse in {"denied", "prohibited"}:
        reasons.append("rights_denied")
        gates["rights"] = "reject"
    elif reuse == "unknown":
        reasons.append("rights_unknown")
        gates["rights"] = "review"
    else:
        gates["rights"] = "pass"

    # overall decision: reject if any reject gate, else review if any review/reason, else pass
    gate_vals = list(gates.values())
    if "reject" in gate_vals:
        status = "reject"
    elif "review" in gate_vals or reasons:
        status = "review"
    else:
        status = "pass"

    # preserve original needs_verification semantics: pass here means "offline checks ok, still verify before publish"
    review = dict(out.get("review") or {})
    review["needs_verification"] = True if status != "reject" else review.get("needs_verification", True)
    review["offline_status"] = status
    notes = list(review.get("notes") or [])
    for r in reasons:
        if r not in notes:
            notes.append(r)
    review["notes"] = notes

    out["dates"] = dates
    out["liveness"] = liveness
    out["rights"] = rights
    out["review"] = review
    out["verification"] = {
        "status": status,
        "checked_at": now_iso(),
        "mode": "offline_stub",
        "gates": gates,
        "reasons": reasons,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Normalized JSON/JSONL file")
    ap.add_argument("--output", "-o", help="Write verification JSONL (default: stdout)")
    ap.add_argument("--summary", help="Write JSON summary to this path")
    args = ap.parse_args()
    records = [verify(r) for r in iter_records(Path(args.input))]
    counts = {"pass": 0, "review": 0, "reject": 0}
    reasons: dict[str, int] = {}
    for r in records:
        st = (r.get("verification") or {}).get("status", "review")
        counts[st] = counts.get(st, 0) + 1
        for reason in (r.get("verification") or {}).get("reasons") or []:
            reasons[reason] = reasons.get(reason, 0) + 1
    summary = {"total": len(records), "counts": counts, "reasons": reasons, "generated_at": now_iso(), "mode": "offline_stub"}

    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    text = "\n".join(lines) + ("\n" if lines else "")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
