#!/usr/bin/env python3
"""Evaluate job_signal_matcher outputs against labeled expectations.

Usage:
  python3 eval_matcher.py --classified fixtures_matcher_cases.classified.jsonl --labels fixtures_matcher_cases.labels.json

Labels format (JSON array):
  {"case": "<case id>", "expect": {...}}
Supported expectations:
  any_track: [..]           -> at least one present in match.tracks
  certs_any: [..]           -> at least one present in match.certs
  geo_bucket_in: [..]       -> match.geo_bucket in list
  canada_remote: bool       -> eligible.canada_remote_signal
  toronto_gta_local: bool   -> eligible.toronto_gta_local
  ontario_eligible: bool    -> eligible.ontario_eligible_signal
  needs_confirm: bool       -> eligible.needs_confirm
  exclude: bool             -> eligible.exclude_signal
  hybrid_or_onsite: bool    -> eligible.hybrid_or_onsite

No deps, no network.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_classified(path: Path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        key = o.get("case") or o.get("id") or o.get("title")
        out[key] = o
    return out


def check(o: dict, expect: dict):
    m = o.get("match", {})
    elig = m.get("eligible", {}) or {}
    tracks = set((m.get("tracks") or {}).keys())
    certs = set(m.get("certs") or [])
    failures = []
    if "any_track" in expect:
        if not tracks.intersection(expect["any_track"]):
            failures.append(f"any_track expected one of {expect['any_track']} got {sorted(tracks)}")
    if "certs_any" in expect:
        if not certs.intersection(expect["certs_any"]):
            failures.append(f"certs_any expected one of {expect['certs_any']} got {sorted(certs)}")
    if "geo_bucket_in" in expect:
        if m.get("geo_bucket") not in expect["geo_bucket_in"]:
            failures.append(f"geo_bucket expected in {expect['geo_bucket_in']} got {m.get('geo_bucket')}")
    for k, elig_key in [
        ("canada_remote", "canada_remote_signal"),
        ("toronto_gta_local", "toronto_gta_local"),
        ("ontario_eligible", "ontario_eligible_signal"),
        ("needs_confirm", "needs_confirm"),
        ("exclude", "exclude_signal"),
        ("hybrid_or_onsite", "hybrid_or_onsite"),
    ]:
        if k in expect and bool(elig.get(elig_key)) != bool(expect[k]):
            failures.append(f"{k} expected {expect[k]} got {elig.get(elig_key)}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classified", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--json", action="store_true", help="emit JSON summary")
    args = ap.parse_args()
    classified = load_classified(Path(args.classified))
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    results = []
    passed = 0
    for item in labels:
        case = item["case"]
        expect = item.get("expect", {})
        o = classified.get(case)
        if not o:
            failures = ["missing classified case"]
        else:
            failures = check(o, expect)
        ok = len(failures) == 0
        passed += 1 if ok else 0
        results.append({"case": case, "ok": ok, "failures": failures})
    summary = {"total": len(labels), "passed": passed, "failed": len(labels) - passed, "pass_rate": (passed / len(labels)) if labels else 0.0, "results": results}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Matcher eval: {passed}/{len(labels)} passed ({summary['pass_rate']:.0%})")
        for r in results:
            status = "PASS" if r["ok"] else "FAIL"
            print(f"- {status} {r['case']}")
            for f in r["failures"]:
                print(f"    - {f}")
    return 0 if passed == len(labels) else 1


if __name__ == "__main__":
    raise SystemExit(main())
