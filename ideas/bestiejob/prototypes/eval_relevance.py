#!/usr/bin/env python3
"""Precision/recall evaluation for BESTIEJOB matcher relevance decisions.

Ground truth: `relevant` flag in labels/fixtures (in-scope target: SN/SF/Other incl.
ITSM/CMDB/ITAM roles with Toronto/GTA or Canada/Ontario-remote/global-confirm eligibility;
excludes non-build sales/admin-only-unrelated and geo-out-of-scope cases per label intent).

Prediction rules (configurable via --rule):
  track_only          : any track score > 0
  track_not_excluded  : any track and not exclude_signal
  track_geo_eligible  : any track and not exclude_signal and (toronto_gta_local or
                        canada_remote_signal or ontario_eligible_signal or needs_confirm)
  scored              : max track score >= --min-score (and not exclude_signal when --respect-exclude)
  scored_geo_eligible : max track score >= --min-score and not exclude_signal and geo eligible/confirm

Outputs per-rule metrics and per-case FP/FN. JSON with --json.

No deps, no network.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        key = o.get("case") or o.get("id") or o.get("title")
        out[key] = o
    return out


def predict(o: dict, rule: str, min_score: int = 1, respect_exclude: bool = True) -> bool:
    m = o.get("match", {})
    elig = m.get("eligible", {}) or {}
    tracks = m.get("tracks") or {}
    has_track = any((v or 0) > 0 for v in tracks.values())
    max_score = max(tracks.values()) if tracks else 0
    excluded = bool(elig.get("exclude_signal"))
    geo_ok = bool(
        elig.get("toronto_gta_local")
        or elig.get("canada_remote_signal")
        or elig.get("ontario_eligible_signal")
        or elig.get("needs_confirm")
    )
    if rule == "track_only":
        return has_track
    if rule == "track_not_excluded":
        return has_track and not excluded
    if rule == "track_geo_eligible":
        return has_track and not excluded and geo_ok
    if rule == "scored":
        ok = max_score >= min_score
        if respect_exclude:
            ok = ok and not excluded
        return ok
    if rule == "scored_geo_eligible":
        ok = max_score >= min_score and not excluded and geo_ok
        return ok
    raise ValueError(rule)


def metrics(cases, labels, rule, min_score=1, respect_exclude=True):
    by_case = load_jsonl(cases) if not isinstance(cases, dict) else cases
    tp = fp = fn = tn = 0
    details = []
    rows = []
    for l in labels:
        case = l["case"]
        gold = bool(l.get("relevant"))
        o = by_case.get(case)
        if not o:
            fn += 1 if gold else 0
            details.append({"case": case, "type": "MISSING", "gold": gold, "pred": None})
            continue
        pred = predict(o, rule, min_score=min_score, respect_exclude=respect_exclude)
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
            details.append({"case": case, "type": "FP", "gold": gold, "pred": pred})
        elif (not pred) and gold:
            fn += 1
            details.append({"case": case, "type": "FN", "gold": gold, "pred": pred})
        else:
            tn += 1
        rows.append({"case": case, "gold": gold, "pred": pred})
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "rule": rule, "min_score": min_score, "respect_exclude": respect_exclude,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
        "errors": details,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classified", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--rule", default="all", choices=["all", "track_only", "track_not_excluded", "track_geo_eligible", "scored", "scored_geo_eligible"])
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--no-respect-exclude", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    by_case = load_jsonl(Path(args.classified))
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    rules = ["track_only", "track_not_excluded", "track_geo_eligible", "scored", "scored_geo_eligible"] if args.rule == "all" else [args.rule]
    out = [metrics(by_case, labels, r, min_score=args.min_score, respect_exclude=not args.no_respect_exclude) for r in rules]
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for m in out:
            print(f"[{m['rule']}" + (f" min_score={m['min_score']}" if m['rule']=='scored' else "") + f"] tp={m['tp']} fp={m['fp']} fn={m['fn']} tn={m['tn']} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
            for e in m['errors']:
                print(f"  - {e['type']} {e['case']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
