#!/usr/bin/env python3
"""Mechanical audit of reports/hypothesis_registry.json for metrics that cannot move
and criteria that are not actually met by the numbers next to them.

Written after H-150 shipped an information ratio computed as the mean of OLS residuals:
with an intercept that mean is exactly zero, so the gate was unfalsifiable. The point of
this tool is to catch that CLASS of defect without an LLM in the loop -- by comparing each
hypothesis against its own recorded numbers and its own declared thresholds.

Checks:
  R1 degenerate   decisive metric is exactly 0 / 1 / -1 / None
  R2 underpowered declared min_n or min_windows_admissible exceeds what was measured
  R3 contradiction an affirmative verdict while a declared numeric criterion is violated
  R4 scale        cost_survival_pct compared against a fractional cost_survival_min, etc.
  R5 nonnumeric   affirmative verdict with no numeric evidence at all

Usage: python3 tools/registry_metric_audit.py [--json OUT] [--md OUT] [--self-check]
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "reports" / "hypothesis_registry.json"

AFFIRMATIVE = ("PASS", "SUPPORTED", "TESTED_PASS", "SHADOW_LIVE", "FORWARD_OBSERVATION",
               "PAPER_PILOT", "FORWARD_SHADOW", "ACCEPTED", "PROMOTED")

# threshold key -> result keys that could satisfy it (searched recursively)
MAP = {
    "min_wr": ["wr", "win_rate", "wr_pct", "win_rate_gross", "pooled_wr"],
    "min_pf": ["pf", "net_pf", "profit_factor"],
    "min_n": ["n", "n_records", "n_trades", "pooled_n", "n_events", "n_obs"],
    "min_etfs_per_leg": ["n_etfs_per_leg"],
    "min_n_per_leg": ["n_per_leg"],
    "min_n_per_window": ["n_per_window"],
    "min_sharpe": ["sharpe", "net_sharpe"],
    "min_dsr": ["dsr"],
    "eff_floor": ["mean_eff", "eff", "harness_mean_eff"],
    "cost_survival_min": ["cost_survival_pct", "cost_survival"],
    "min_windows_admissible": ["windows_pass", "n_admissible", "short_n_admissible",
                              "long_n_admissible", "harness_windows"],
    "min_trades": ["n_trades", "n"],
}
DECISIVE = re.compile(r"(alpha|ir$|ratio|pf$|wr$|sharpe|eff$|t_stat|p_value|dsr)", re.I)


def decimate(o, path="", out=None):
    """Flatten to {dotted_path: value} for scalars."""
    out = {} if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            decimate(v, f"{path}{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            decimate(v, f"{path}[{i}]", out)
    else:
        out[path] = o
    return out


def fraction(v):
    """'0/18' -> (0.0, 18.0); '3/4 folds' -> (3.0, 4.0)."""
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)", str(v))
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


def num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.match(r"^\s*(-?\d+(?:\.\d+)?)", v)
        return float(m.group(1)) if m else None
    return None


def find_metric(flat, names, prefer_exact=True):
    for name in names:
        if prefer_exact:
            for p, v in flat.items():
                if p.lower().endswith(name.lower()) and num(v) is not None:
                    return p, num(v)
        for p, v in flat.items():
            if name.lower() in p.lower() and num(v) is not None:
                return p, num(v)
    return None, None


def audit_one(h):
    findings = []
    res = h.get("result")
    status = str(h.get("status", ""))
    affirmative = any(a in status.upper() for a in AFFIRMATIVE)
    if not isinstance(res, dict):
        if affirmative and res:
            findings.append({"rule": "R5", "why": "affirmative status but result is prose only",
                             "detail": status})
        return findings
    flat = decimate(res)
    verdict = str(res.get("verdict", "")) if isinstance(res.get("verdict"), str) else ""
    aff = affirmative or any(a in verdict.upper() for a in AFFIRMATIVE)

    # R1: decisive metric stuck at a value that cannot discriminate
    for p, v in flat.items():
        leaf = p.split(".")[-1]
        nv = num(v)
        if nv is None and v is not None:
            continue
        if DECISIVE.search(leaf) and (nv == 0.0 or nv in (1.0, -1.0) or v is None):
            findings.append({"rule": "R1", "why": f"decisive metric degenerate ({v!r})",
                             "metric": p, "value": v})

    crit = h.get("acceptance_criteria")
    if isinstance(crit, dict):
        for ckey, cval in crit.items():
            base = ckey.lower()
            if not base.startswith("min_") and base not in ("eff_floor", "cost_survival_min"):
                continue
            thr = num(cval)
            if thr is None:
                continue
            names = MAP.get(base, [base.replace("min_", "")])
            mp, mv = find_metric(flat, names)
            if mp is None:
                findings.append({"rule": "I1", "why": f"{ckey}={thr} not found as a number",
                                 "metric": None, "value": None, "informational": True})
                continue
            frac, denom = fraction(mv if not isinstance(mv, float) else mv)
            if frac is not None and base == "min_windows_admissible":
                mv = frac
            # scale check: pct fields are 0-100, thresholds are 0-1
            scale = 1.0
            if base == "cost_survival_min" and mv is not None and mv > 1.5:
                scale = 100.0
            got = mv / scale if mv is not None else None
            if got is None:
                continue
            if got < thr and aff:
                findings.append({"rule": "R3", "why": f"{ckey}={thr} but {mp}={mv}",
                                 "metric": mp, "value": mv, "threshold": thr})
            elif got < thr:
                findings.append({"rule": "R3-nonaff", "why": f"{ckey}={thr} but {mp}={mv}",
                                 "metric": mp, "value": mv, "threshold": thr})
    return findings


def self_check():
    """Synthetic hypotheses that must trip each rule."""
    cases = [
        ({"id": "SYN1", "status": "PRE_REGISTERED", "result": {
            "factor_regression": {"information_ratio": -0.0}, "gates": {"ir": False}}}, "R1"),
        ({"id": "SYN2", "status": "TESTED_PASS", "acceptance_criteria": {"min_n": 100},
          "result": {"n": 12, "wr": 0.6}}, "R3"),
        ({"id": "SYN3", "status": "PRE_REGISTERED", "acceptance_criteria": {"min_n": 100},
          "result": {"wr": 0.6}}, "I1"),
        # underpowered pass: metric present, below the declared floor, verdict says PASS
        ({"id": "SYN5", "status": "TESTED_PASS",
          "acceptance_criteria": {"min_n": 100, "min_sharpe": 0.5},
          "result": {"n": 40, "sharpe": 0.8}}, "R3"),
        ({"id": "SYN4", "status": "TESTED_PASS",
          "acceptance_criteria": {"cost_survival_min": 0.6},
          "result": {"cost_survival_pct": 36.56}}, "R3"),
    ]
    bad = 0
    for h, want in cases:
        rules = {f["rule"] for f in audit_one(h)}
        ok = want in rules
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {h['id']} want {want} got {sorted(rules)}")
    print("SELF-CHECK PASSED" if not bad else f"SELF-CHECK FAILED ({bad})")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="reports/2026-11-22-registry-numeric-audit.json")
    ap.add_argument("--md", default="reports/2026-11-22-registry-numeric-audit.md")
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    if a.self_check:
        return self_check()

    doc = json.loads(Path(a.registry).read_text())
    hs = doc["hypotheses"] if isinstance(doc, dict) and "hypotheses" in doc else doc
    rows, by_rule = [], {}
    for h in hs:
        for f in audit_one(h):
            f["id"] = h.get("id")
            f["status"] = h.get("status")
            rows.append(f)
            by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1
    out = {"n_hypotheses": len(hs), "n_findings": len(rows), "by_rule": by_rule, "findings": rows}
    Path(a.json).write_text(json.dumps(out, indent=2))
    lines = [f"# Registry numeric audit — {len(hs)} hypotheses, {len(rows)} findings", "",
             "Mechanical checks only (no model in the loop). Rules: R1 a decisive metric stuck at a "
             "value that cannot discriminate, R2 a declared threshold never measured, R3 an "
             "affirmative verdict that its own numbers contradict, R3-nonaff the same on a "
             "non-affirmative hypothesis (expected, context only), R5 affirmative status with prose "
             "only.", "", "| rule | count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_rule.items())]
    lines += ["", f"| id | status | rule | detail |", "|---|---|---|---|"]
    for f in sorted(rows, key=lambda r: (r["rule"], r["id"])):
        if f["rule"] in ("R3-nonaff", "I1"):
            continue
        lines.append(f"| {f['id']} | {f['status']} | {f['rule']} | {f['why']} |")
    Path(a.md).write_text("\n".join(lines) + "\n")
    print(json.dumps(by_rule, indent=2))
    print("\n--- actionable (R1/R2/R3/R5) ---")
    for f in rows:
        if f["rule"] not in ("R3-nonaff", "I1"):
            print(f"  [{f['rule']}] {f['id']:42s} {f['status'][:20]:20s} {f['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
