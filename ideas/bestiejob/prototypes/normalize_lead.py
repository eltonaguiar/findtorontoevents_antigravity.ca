#!/usr/bin/env python3
"""Prototype: normalize scan_boards.py leads into a draft canonical record.

- Reads JSON array or JSONL of leads (scan_boards.py --read output shape).
- Attaches track/geo/cert evidence via job_signal_matcher.classify (best-effort).
- Emits JSONL draft records for downstream verify -> dedupe -> inbox-merge stages.

This is a starter mapping (not authoritative). Do not publish unverified leads.
No deps, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

try:
    from job_signal_matcher import classify
except Exception:  # pragma: no cover
    classify = lambda job: {"tracks": {}, "certs": [], "geo_bucket": "Other/unknown", "eligible": {}, "reasons": []}

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref", "source"}


def _slug(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlsplit(url.strip())
        if p.scheme not in ("http", "https") or not p.netloc:
            return url.strip()
        q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith(_TRACKING_PREFIXES) and k.lower() not in _TRACKING_KEYS]
        query = urlencode(q, doseq=True)
        path = re.sub(r"/+$", "", p.path) or "/"
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, query, ""))
    except Exception:
        return url.strip()


def _dedupe_key(lead: dict, posting_url_norm: str) -> str:
    # Prefer stable source+posting identity; then source+req; then normalized URL; then content fingerprint.
    src = str(lead.get("source") or lead.get("source_id") or "")
    pid = str(lead.get("posting_id") or "")
    req = str(lead.get("req_id") or lead.get("refNumber") or "")
    if src and pid:
        base = f"ats:{src}:posting:{pid}"
    elif src and req:
        base = f"ats:{src}:req:{req}"
    elif posting_url_norm:
        base = f"url:{posting_url_norm}"
    elif req:
        base = f"req:{req}"
    else:
        base = "fp:" + "|".join([
            _slug(str(lead.get("title") or "")),
            _slug(str(lead.get("publisher") or lead.get("company") or "")),
            _slug(str(lead.get("location_as_listed") or lead.get("location") or "")),
        ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _split_tracks(lead: dict, match: dict) -> list[str]:
    tracks = sorted([t for t, s in (match.get("tracks") or {}).items() if s > 0])
    if tracks:
        return tracks
    raw = lead.get("candidate_tracks")
    if isinstance(raw, list):
        return [str(t) for t in raw if t]
    if isinstance(raw, str) and raw.strip():
        return [t for t in (x.strip() for x in raw.split(";")) if t]
    return []


def normalize(lead: dict) -> dict:
    title = str(lead.get("title") or lead.get("role") or "")
    company = str(lead.get("publisher") or lead.get("company") or lead.get("organization") or "")
    url_raw = str(lead.get("posting_url") or lead.get("url") or "")
    apply_raw = str(lead.get("apply_url") or lead.get("applyUrl") or "")
    corr_raw = lead.get("corroborating_urls") or lead.get("corroborating_url") or []
    if isinstance(corr_raw, str):
        corr_raw = [corr_raw] if corr_raw else []
    url = normalize_url(url_raw)
    apply_url = normalize_url(apply_raw)
    corr_urls = [normalize_url(u) for u in corr_raw if normalize_url(u)]
    location_raw = str(lead.get("location_as_listed") or lead.get("location") or lead.get("location_summary") or "")
    desc = str(lead.get("description") or lead.get("snippet") or lead.get("body") or lead.get("developer_evidence") or "")
    req_id = str(lead.get("req_id") or lead.get("refNumber") or "")
    posting_id = str(lead.get("posting_id") or "")

    enrich = dict(lead)
    enrich.setdefault("description", desc)
    enrich.setdefault("location", location_raw)
    match = classify(enrich)

    posted_val = lead.get("time_value") or lead.get("posted_at") or lead.get("posted_on") or lead.get("releasedDate") or None
    time_field = lead.get("time_field") or ("posted_on" if lead.get("posted_on") else None)

    return {
        "schema": "bestiejob.normalized_lead_draft.v0",
        "identity": {
            "dedupe_key": _dedupe_key(lead, url),
            "source_id": lead.get("source") or lead.get("source_id"),
            "posting_id": posting_id or None,
            "req_id": req_id or None,
        },
        "source": {
            "adapter": lead.get("ats") or lead.get("adapter"),
            "publisher": company or None,
            "observed_at_utc": lead.get("observed_at_utc") or lead.get("checked_utc"),
            "provenance": {"input": "scan_boards_lead_or_snapshot"},
        },
        "urls": {
            "posting": url or None,
            "posting_raw": url_raw or None,
            "apply": apply_url or None,
            "corroborating": corr_urls,
        },
        "company": {
            "name": company or None,
            "client": lead.get("employer_or_client"),
            "hiring_channel": lead.get("hiring_channel"),
        },
        "title": title or None,
        "location": {
            "raw": location_raw or None,
            "mode_as_listed": lead.get("mode_as_listed") or lead.get("workplaceType") or lead.get("mode"),
            "geo_bucket": match.get("geo_bucket"),
            "eligible": match.get("eligible", {}),
        },
        "dates": {
            "posted_at": None,  # require verified absolute source date before publish
            "time_field": time_field,
            "time_value_raw": posted_val,
            "closes_on": lead.get("closes_on"),
            "valid_through": lead.get("valid_through"),
        },
        "content": {"description": desc or None, "snippet": (desc[:500] if desc else None)},
        "classification": {
            "tracks": _split_tracks(lead, match),
            "certs": match.get("certs", []),
            "track_scores": match.get("tracks", {}),
            "evidence": match.get("reasons", []),
            "status": lead.get("status") or "lead_only",
        },
        "liveness": {
            "state": lead.get("active_state") or lead.get("liveness_state") or "unknown",
            "http_status": lead.get("http_status_hint") or lead.get("http_status"),
            "access_level": lead.get("access_level"),
        },
        "rights": {"reuse": "unknown"},
        "review": {"needs_verification": True, "notes": []},
    }


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="Leads JSON/JSONL (omit with --demo)")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo or not args.input:
        leads = [{
            "source": "eqbank", "publisher": "EQ Bank", "ats": "lever", "posting_id": "abc123",
            "title": "ServiceNow Developer", "posting_url": "https://jobs.lever.co/eqbank/abc123?utm_source=x",
            "apply_url": "https://jobs.lever.co/eqbank/abc123/apply",
            "location_as_listed": "Toronto, Ontario", "mode_as_listed": "Hybrid",
            "time_field": "", "time_value": "", "candidate_tracks": "ServiceNow",
            "status": "lead_only", "observed_at_utc": "2026-11-18T00:00:00Z",
            "description": "Build ITSM workflows, GlideRecord, Script Includes. CSA preferred."
        }]
    else:
        leads = list(iter_records(Path(args.input)))
    for lead in leads:
        print(json.dumps(normalize(lead), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
