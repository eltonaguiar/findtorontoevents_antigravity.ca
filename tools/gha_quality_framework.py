#!/usr/bin/env python3
"""gha_quality_framework.py - structural quality rules (Q1-Q10) for GitHub Actions workflows.

Complements, does not replace, tools/gha_health_audit.py (R1-R12 = "what is broken NOW" from run
history). This tool asks whether the workflow *file itself* is well built: offline, deterministic,
no network, no token.

Layers:
  A  inventory  - parse every workflow YAML, record triggers, cron, permissions, timeouts,
                   secrets, actions and pins, continue-on-error, `|| true`, push steps,
                   artifacts produced/consumed.
  B  rules      - Q1..Q10 (see RULES below), each fail-closed.
  C  runtime    - optionally reads GHACTIONS_LIVE/gha_health.json (R1-R12 output) to add
                   broken-now / flapping signals to the score. Skipped if the file is absent.
  D  scoring    - per-workflow 0-100 score with stated weights; repo aggregate.
  E  gate       - --check exits non-zero on any blocking rule violation.

Modes:
  python3 tools/gha_quality_framework.py --dry-run         # offline, all workflows, writes nothing
  python3 tools/gha_quality_framework.py --check           # exit 1 on blocking violations
  python3 tools/gha_quality_framework.py --workflows-dir X --dry-run
  python3 tools/gha_quality_framework.py --self-test       # Q-rule fixtures, no repo needed

Writes (only when not --dry-run/--self-test and --out given):
  GHACTIONS_LIVE/gha_quality.json and GHACTIONS_LIVE/gha_quality.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - hard dependency for this tool
    yaml = None

DEFAULT_WORKFLOWS = Path(".github/workflows")
DEFAULT_OUT = Path("GHACTIONS_LIVE")

# ---------------------------------------------------------------- rule registry
# severity: P0 = blocking under --check, P1 = blocking, P2 = advisory (reported, score only).
RULES: Dict[str, Dict[str, Any]] = {
    "Q1": {"name": "cron-stampede", "severity": "P2",
           "why": "two workflows scheduled at the same minute contend for runners and API budget"},
    "Q2": {"name": "unpinned-action", "severity": "P1",
           "why": "a mutable tag (or none) can change under you or be taken over"},
    "Q3": {"name": "write-all-default", "severity": "P1",
           "why": "a pushing workflow with no `permissions:` runs with the repo default (often write-all)"},
    "Q4": {"name": "self-push-without-skip-ci", "severity": "P2",
           "why": "a commit step without [skip ci] re-triggers the workflow (push trigger => loop)"},
    "Q5": {"name": "duplicate-producer", "severity": "P0",
           "why": "two workflows write the same artifact path (the class of bug that made /audit lag /audit3)"},
    "Q6": {"name": "orphan-artifact", "severity": "P2",
           "why": "a produced JSON that no workflow consumes (dead output, or a consumer was renamed)"},
    "Q7": {"name": "silent-failure", "severity": "P0",
           "why": "continue-on-error or `|| true` on a gate-shaped step hides a failed check"},
    "Q8": {"name": "missing-timeout", "severity": "P1",
           "why": "no timeout-minutes is the phantom-queue generator (runs hang until GitHub kills them)"},
    "Q9": {"name": "secret-sprawl", "severity": "P2",
           "why": "one secret referenced by more workflows than the fan-in bound widens blast radius"},
    "Q10": {"name": "dead-schedule", "severity": "P2",
            "why": "a cron whose workflow has not run in > 2x its interval is silently dead"},
}

BLOCKING_SEVERITIES = {"P0", "P1"}
SECRET_FANIN_BOUND = 8       # Q9: a secret used by more than this many workflows is flagged
DEAD_SCHEDULE_HOURS = 48     # Q10 fallback bound when no run history is available (2x a daily cron)

GATE_WORD_RE = re.compile(r"\b(gate|check|lint|test|verify|validate|assert|guard)\b", re.I)
# a step whose first action is one of these is not a gate, even if its text says "verify"
# (deploy/commit steps are retried or tolerated by design)
NON_GATE_ACTION_RE = re.compile(r"^(commit|deploy|push|upload|download|mirror|prepare|sync|fetch|prune|alert)\b", re.I)
# an explicit declaration that failure is tolerated: not "silent", so not a Q7 hit
TOLERANT_DECL_RE = re.compile(
    r"optional|non[- ]fatal|non[- ]blocking|best[- ]effort|advisory|informational|"
    r"preview|verification only|\(loud|soft[- ]fail|continue", re.I)
# first-party action owners: a major tag is the documented convention for them
FIRST_PARTY_OWNERS = {"actions", "github"}


# ---------------------------------------------------------------- model
@dataclass
class Workflow:
    path: str
    name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    parse_error: Optional[str] = None
    triggers: Set[str] = field(default_factory=set)
    crons: List[str] = field(default_factory=list)
    has_permissions: bool = False
    permissions: Any = None
    concurrency: Any = None
    secrets: Set[str] = field(default_factory=set)
    actions: List[Tuple[str, str]] = field(default_factory=list)   # (uses, pin)
    continue_on_error: int = 0
    or_true: int = 0
    gate_steps: List[str] = field(default_factory=list)
    silent_gate_steps: List[str] = field(default_factory=list)
    has_timeout: bool = False
    job_timeouts: Dict[str, Optional[int]] = field(default_factory=dict)
    push_steps: List[str] = field(default_factory=list)
    push_has_skip_ci: bool = False
    produces: Set[str] = field(default_factory=set)
    consumes: Set[str] = field(default_factory=set)
    writes_repo: bool = False


ARTIFACT_RE = re.compile(r"([\w.\-/]+\.(?:json|jsonl|csv|parquet|md))")
SKIP_CI_RE = re.compile(r"\[skip ci\]|\[ci skip\]|\[no ci\]|\[skip-ci\]", re.I)


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _cron_minute(expr: str) -> Optional[str]:
    parts = expr.split()
    return parts[0] if parts else None


def load_workflows(workflows_dir: Path) -> List[Workflow]:
    wfs: List[Workflow] = []
    for p in sorted(list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))):
        wf = Workflow(path=str(p))
        try:
            data = yaml.safe_load(p.read_text()) if yaml else None
            if not isinstance(data, dict):
                raise ValueError("top-level is not a mapping")
            wf.data = data
        except Exception as e:  # fail closed: an unparsable workflow is still inventoried
            wf.parse_error = f"{type(e).__name__}: {e}"
            wfs.append(wf)
            continue
        inventory(wf)
        wfs.append(wf)
    return wfs


def inventory(wf: Workflow) -> None:
    """Layer A."""
    d = wf.data
    wf.name = str(d.get("name") or Path(wf.path).stem)
    # `on` may be a string, list, or dict; YAML 1.1 makes bare `on` a bool True
    on = d.get("on", d.get(True))
    if isinstance(on, str):
        wf.triggers = {on}
    elif isinstance(on, list):
        wf.triggers = {str(x) for x in on}
    elif isinstance(on, dict):
        wf.triggers = {str(k) for k in on.keys()}
        sched = on.get("schedule") or []
        for s in _as_list(sched):
            if isinstance(s, dict) and s.get("cron"):
                wf.crons.append(str(s["cron"]))
    if "permissions" in d:
        wf.has_permissions = True
        wf.permissions = d.get("permissions")
    wf.concurrency = d.get("concurrency")
    jobs = d.get("jobs") or {}
    if isinstance(jobs, dict):
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                continue
            tmo = job.get("timeout-minutes")
            wf.job_timeouts[str(jname)] = tmo
            for step in _as_list(job.get("steps")):
                if not isinstance(step, dict):
                    continue
                _scan_step(wf, step, str(jname))
    # a workflow-level timeout does not exist in GHA; timeouts are per job
    wf.has_timeout = bool(wf.job_timeouts) and all(v is not None for v in wf.job_timeouts.values())


def _scan_step(wf: Workflow, step: Dict[str, Any], job: str) -> None:
    uses = step.get("uses")
    if uses:
        uses = str(uses)
        if "@" in uses:
            ref = uses.rsplit("@", 1)
            wf.actions.append((ref[0], ref[1]))
        else:
            wf.actions.append((uses, ""))
    run = step.get("run")
    name = str(step.get("name") or "").strip()
    if step.get("continue-on-error") in (True, "true"):
        wf.continue_on_error += 1
    if isinstance(run, str):
        if "|| true" in run or "|| :" in run:
            wf.or_true += run.count("|| true") + run.count("|| :")
        label = name or run.strip().splitlines()[0][:80]
        is_gate = (bool(GATE_WORD_RE.search(label))
                   and not NON_GATE_ACTION_RE.match(label)
                   and not TOLERANT_DECL_RE.search(label))
        if is_gate:
            wf.gate_steps.append(label)
            if step.get("continue-on-error") in (True, "true") or "|| true" in run or "|| :" in run:
                wf.silent_gate_steps.append(label)
        # artifact producers / consumers / push detection
        for m in ARTIFACT_RE.finditer(run):
            tok = m.group(1)
            esc = re.escape(tok)
            # producer: the file is written or staged, e.g. `> out.json`, `>> out.json`, `git add out.json`
            if re.search(r">>?\s*\S*" + esc, run) or re.search(r"git\s+add\s+\S*" + esc, run):
                wf.produces.add(tok)
            # consumer: the file is read, e.g. `cat out.json`, `jq ... out.json`, `open("out.json")`,
            # `< out.json`, or passed as an argument to a script that is not a write
            if (re.search(r"\b(?:cat|jq|head|tail|less|grep|wc)\b[^|;\n]*" + esc, run)
                    or re.search(r"open\(\s*['\"]?" + esc, run)
                    or re.search(r"<\s*" + esc, run)
                    or re.search(r"python3?\s+\S+\.py\s+[^|;\n]*" + esc, run)):
                wf.consumes.add(tok)
        if re.search(r"\bgit\s+(push|commit)\b", run):
            wf.push_steps.append(name or f"step in {job}")
            wf.writes_repo = True
            if SKIP_CI_RE.search(run) or SKIP_CI_RE.search(name):
                wf.push_has_skip_ci = True
        if re.search(r"\bgit\s+push\b", run) and SKIP_CI_RE.search(run):
            wf.push_has_skip_ci = True
    # secrets in env / with blocks
    for txt in (json.dumps(step.get("env") or {}), json.dumps(step.get("with") or {})):
        for m in re.finditer(r"secrets\.([A-Za-z0-9_]+)", txt):
            wf.secrets.add(m.group(1))
    if isinstance(run, str):
        for m in re.finditer(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)", run):
            wf.secrets.add(m.group(1))


# ---------------------------------------------------------------- rules (Layer B)
def _finding(rule: str, wf: str, detail: str, evidence: str = "") -> Dict[str, Any]:
    return {"rule": rule, "rule_name": RULES[rule]["name"], "severity": RULES[rule]["severity"],
            "workflow": wf, "detail": detail, "evidence": evidence}


def q1_cron_stampede(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    by_minute: Dict[str, List[str]] = defaultdict(list)
    for wf in wfs:
        for c in wf.crons:
            m = _cron_minute(c)
            if m is not None and m != "*":
                by_minute[m].append(f"{wf.name} ({c})")
    out = []
    for minute, names in sorted(by_minute.items()):
        if len(names) > 1:
            out.append(_finding("Q1", "(repo)", f"{len(names)} workflows share cron minute :{minute}",
                                "; ".join(sorted(names))))
    return out


def q2_unpinned_action(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    """Third-party actions must be pinned. First-party `actions/*` may use a major tag.

    Rationale: GitHub's own actions are the documented convention to reference by major
    (actions/checkout@v6); a SHA pin there is high churn, low value. A third-party action on a
    mutable tag is a real supply-chain risk.
    """
    out = []
    for wf in wfs:
        for uses, pin in wf.actions:
            if uses.startswith("./"):
                continue
            owner = uses.split("/", 1)[0].lower()
            if not pin:
                out.append(_finding("Q2", wf.name, f"action without version: {uses}"))
            elif owner not in FIRST_PARTY_OWNERS and not re.fullmatch(r"[0-9a-f]{40}", pin):
                out.append(_finding("Q2", wf.name, f"third-party action not SHA-pinned: {uses}@{pin}"))
    return out


def q3_write_all_default(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    out = []
    for wf in wfs:
        if wf.writes_repo and not wf.has_permissions:
            out.append(_finding("Q3", wf.name, "pushes to the repo but declares no `permissions:`"))
        elif wf.writes_repo and wf.permissions == "write-all":
            out.append(_finding("Q3", wf.name, "pushes and declares `permissions: write-all`"))
    return out


def q4_self_push_no_skip_ci(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    out = []
    for wf in wfs:
        if wf.push_steps and not wf.push_has_skip_ci:
            out.append(_finding("Q4", wf.name,
                                f"{len(wf.push_steps)} commit/push step(s) with no [skip ci]",
                                ", ".join(wf.push_steps[:4])))
    return out


def q5_duplicate_producer(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    producers: Dict[str, Set[str]] = defaultdict(set)
    for wf in wfs:
        for a in wf.produces:
            producers[a].add(wf.name)
    out = []
    for art, names in sorted(producers.items()):
        if len(names) > 1:
            out.append(_finding("Q5", "(repo)", f"{len(names)} workflows write {art}", ", ".join(sorted(names))))
    return out


def q6_orphan_artifact(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    produced: Dict[str, Set[str]] = defaultdict(set)
    consumed: Set[str] = set()
    for wf in wfs:
        for a in wf.produces:
            produced[a].add(wf.name)
        consumed |= wf.consumes
    out = []
    for art, names in sorted(produced.items()):
        if art not in consumed:
            out.append(_finding("Q6", ", ".join(sorted(names)), f"produced but never consumed: {art}"))
    return out


def q7_silent_failure(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    out = []
    for wf in wfs:
        for step in wf.silent_gate_steps:
            out.append(_finding("Q7", wf.name, f"gate-shaped step swallows failure: {step}"))
    return out


def q8_missing_timeout(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    out = []
    for wf in wfs:
        if not wf.job_timeouts:
            continue
        missing = [j for j, v in wf.job_timeouts.items() if v is None]
        if missing:
            out.append(_finding("Q8", wf.name, f"{len(missing)} job(s) without timeout-minutes",
                                ", ".join(missing[:5])))
    return out


def q9_secret_sprawl(wfs: List[Workflow]) -> List[Dict[str, Any]]:
    users: Dict[str, Set[str]] = defaultdict(set)
    for wf in wfs:
        for s in wf.secrets:
            users[s].add(wf.name)
    out = []
    for s, names in sorted(users.items()):
        if len(names) > SECRET_FANIN_BOUND:
            out.append(_finding("Q9", "(repo)", f"{s} used by {len(names)} workflows (bound {SECRET_FANIN_BOUND})"))
    return out


def q10_dead_schedule(wfs: List[Workflow], runtime: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """From the trigger side: a scheduled workflow with no run in > 2x its interval.

    Offline we can only flag schedules whose cadence is implausible (impossible minute/hour
    values) or, when the R1-R12 report is supplied, workflows whose last run is far older than
    their cron interval.
    """
    out = []
    last_run: Dict[str, float] = {}
    if runtime:
        for row in (runtime.get("rules", {}).get("R1", {}) or {}).get("rows", []) or []:
            wname = str(row.get("workflow") or "")
            age = row.get("age_hours")
            if wname and isinstance(age, (int, float)):
                last_run[wname] = max(last_run.get(wname, 0.0), float(age))
    for wf in wfs:
        if not wf.crons:
            continue
        for c in wf.crons:
            parts = c.split()
            if len(parts) != 5:
                out.append(_finding("Q10", wf.name, f"malformed cron {c!r}"))
                continue
            minute, hour = parts[0], parts[1]
            if not (minute.isdigit() or minute in {"*", "*/5", "*/10", "*/15", "*/30"} or minute.startswith("*/")):
                out.append(_finding("Q10", wf.name, f"unusual cron minute {minute!r} in {c!r}"))
            interval_h = _interval_hours(hour, parts[2])
            age = last_run.get(wf.name)
            if interval_h and age is not None and age > 2 * interval_h:
                out.append(_finding("Q10", wf.name, f"last run {age:.0f}h ago vs cron interval {interval_h:.0f}h"))
    return out


def _interval_hours(hour: str, dom: str) -> Optional[float]:
    try:
        if dom != "*":
            return 24 * 30
        if hour == "*":
            return 1.0
        if hour.startswith("*/"):
            return float(hour[2:])
        return 24.0
    except Exception:
        return None


# ---------------------------------------------------------------- scoring (Layer D)
WEIGHTS = {"parse_error": 30, "Q7": 25, "Q5": 15, "Q8": 10, "Q3": 10, "Q2": 5, "Q4": 5, "Q1": 5, "Q6": 3, "Q9": 3, "Q10": 3}


def score_workflow(wf: Workflow, findings: List[Dict[str, Any]], broken_now: bool = False) -> int:
    score = 100
    if wf.parse_error:
        score -= WEIGHTS["parse_error"]
    for f in findings:
        if f["workflow"] == wf.name or wf.name in f["workflow"]:
            score -= WEIGHTS.get(f["rule"], 3)
    if broken_now:
        score -= 10
    return max(0, score)


# ---------------------------------------------------------------- report
def build_report(wfs: List[Workflow], runtime: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    findings += q1_cron_stampede(wfs)
    findings += q2_unpinned_action(wfs)
    findings += q3_write_all_default(wfs)
    findings += q4_self_push_no_skip_ci(wfs)
    findings += q5_duplicate_producer(wfs)
    findings += q6_orphan_artifact(wfs)
    findings += q7_silent_failure(wfs)
    findings += q8_missing_timeout(wfs)
    findings += q9_secret_sprawl(wfs)
    findings += q10_dead_schedule(wfs, runtime)

    broken = set()
    if runtime:
        for row in (runtime.get("rules", {}).get("R1", {}) or {}).get("rows", []) or []:
            if row.get("workflow"):
                broken.add(str(row["workflow"]))

    scores = {wf.name: score_workflow(wf, findings, wf.name in broken) for wf in wfs}
    by_rule: Dict[str, int] = defaultdict(int)
    by_sev: Dict[str, int] = defaultdict(int)
    for f in findings:
        by_rule[f["rule"]] += 1
        by_sev[f["severity"]] += 1
    aggregate = round(sum(scores.values()) / len(scores), 1) if scores else 100.0
    return {
        "schema": "gha_quality.v1",
        "n_workflows": len(wfs),
        "n_parse_errors": sum(1 for wf in wfs if wf.parse_error),
        "aggregate_score": aggregate,
        "by_rule": dict(sorted(by_rule.items())),
        "by_severity": dict(sorted(by_sev.items())),
        "blocking_violations": sum(1 for f in findings if f["severity"] in BLOCKING_SEVERITIES),
        "rules": {k: v for k, v in RULES.items()},
        "findings": findings,
        "scores": scores,
        "weights": WEIGHTS,
        "runtime_used": runtime is not None,
    }


def render_md(rep: Dict[str, Any]) -> str:
    lines = ["# GHA quality framework (Q1-Q10)", "",
             f"- workflows scanned: {rep['n_workflows']} (parse errors: {rep['n_parse_errors']})",
             f"- aggregate score: {rep['aggregate_score']}/100",
             f"- blocking violations: {rep['blocking_violations']}",
             f"- runtime signals merged: {rep['runtime_used']}", "",
             "## Findings by rule", "", "| Rule | Name | Severity | Count |", "|---|---|---|---|"]
    for r, meta in rep["rules"].items():
        lines.append(f"| {r} | {meta['name']} | {meta['severity']} | {rep['by_rule'].get(r, 0)} |")
    lines += ["", "## Blocking findings", ""]
    blocking = [f for f in rep["findings"] if f["severity"] in BLOCKING_SEVERITIES]
    if not blocking:
        lines.append("_None._")
    else:
        lines += ["| Rule | Workflow | Detail |", "|---|---|---|"]
        for f in blocking[:80]:
            lines.append(f"| {f['rule']} | {f['workflow']} | {f['detail'].replace('|', '/')} |")
    low = sorted(rep["scores"].items(), key=lambda kv: kv[1])[:15]
    lines += ["", "## Lowest-scoring workflows", "", "| Workflow | Score |", "|---|---|"]
    for n, s in low:
        lines.append(f"| {n} | {s} |")
    lines += ["", "## Advisory findings (P2)", ""]
    advisory = [f for f in rep["findings"] if f["severity"] == "P2"]
    if not advisory:
        lines.append("_None._")
    else:
        for f in advisory[:40]:
            lines.append(f"- {f['rule']} {f['workflow']}: {f['detail']}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- self-test (Layer C fixtures)
GOOD_WF = """\
name: good-wf
on:
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: good-wf
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v6.0.0
      - name: Run tests
        run: python3 -m pytest -q
"""

BAD_WF = """\
name: bad-wf
on:
  schedule:
    - cron: '0 0 * * *'
  push:
concurrency:
  group: bad-wf
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: some/action@main
      - name: Lint gate
        continue-on-error: true
        run: python3 tools/lint.py || true
      - name: Commit report
        run: |
          git add out.json
          git commit -m "report"
          git push
      - name: Write
        run: echo '{}' > out.json
"""

BAD_WF2 = """\
name: bad-wf2
on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v6
      - name: Commit report
        run: |
          git add out.json
          git commit -m "report"
          git push
"""

SPRAWL_WF = """\
name: sprawl-wf
on: workflow_dispatch
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Use a popular secret
        env:
          TOKEN: ${{ secrets.SHARED_TOKEN }}
        run: echo ok
"""
SPRAWL_USERS = 9  # one more than SECRET_FANIN_BOUND


def _wf_from_text(text: str, name: str) -> Workflow:
    wf = Workflow(path=f"<fixture:{name}>")
    wf.data = yaml.safe_load(text) or {}
    inventory(wf)
    return wf


def self_test() -> Tuple[bool, List[str]]:
    log: List[str] = []
    if yaml is None:
        return False, ["PyYAML not available"]
    good = _wf_from_text(GOOD_WF, "good")
    bad = _wf_from_text(BAD_WF, "bad")
    bad2 = _wf_from_text(BAD_WF2, "bad2")
    sprawl = [_wf_from_text(SPRAWL_WF.replace("sprawl-wf", f"sprawl-wf-{i}"), f"sprawl{i}")
              for i in range(SPRAWL_USERS)]
    allw = [good, bad, bad2]
    checks = {
        # bad and bad2 share cron minute 0
        "Q1": lambda: q1_cron_stampede(allw),
        "Q2": lambda: q2_unpinned_action(allw),
        "Q3": lambda: q3_write_all_default(allw),
        "Q4": lambda: q4_self_push_no_skip_ci(allw),
        # bad and bad2 both write out.json
        "Q5": lambda: q5_duplicate_producer([bad, bad2]),
        "Q6": lambda: q6_orphan_artifact([bad]),
        "Q7": lambda: q7_silent_failure(allw),
        "Q8": lambda: q8_missing_timeout(allw),
        "Q9": lambda: q9_secret_sprawl(sprawl),
        "Q10": lambda: q10_dead_schedule([_wf_from_text(BAD_WF.replace("'0 0 * * *'", "'bad cron'"), "badcron")]),
    }
    ok = True
    for rule, fn in checks.items():
        try:
            found = fn()
        except Exception as e:  # a rule that crashes on a fixture fails
            ok = False
            log.append(f"{rule}: EXCEPTION {type(e).__name__}: {e}")
            continue
        good_hit = any("good" in f["workflow"] for f in found)
        fired = len(found) > 0
        if fired and not good_hit:
            log.append(f"{rule}: PASS (fires on bad, silent on good) - {len(found)} finding(s)")
        else:
            ok = False
            log.append(f"{rule}: FAIL fired={fired} good_hit={good_hit} findings={found[:2]}")
    # Q3 intentionally cannot fire on GOOD_WF (it has permissions)
    return ok, log


# ---------------------------------------------------------------- main
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflows-dir", default=str(DEFAULT_WORKFLOWS))
    ap.add_argument("--dry-run", action="store_true", help="offline inventory + rules, writes nothing")
    ap.add_argument("--check", action="store_true", help="exit 1 when a blocking (P0/P1) rule fires")
    ap.add_argument("--self-test", action="store_true", help="run the Q-rule fixtures and exit")
    ap.add_argument("--out", default=None, help="directory for gha_quality.json/.md (default GHACTIONS_LIVE)")
    ap.add_argument("--runtime-report", default="GHACTIONS_LIVE/gha_health.json",
                    help="optional R1-R12 report to merge runtime signals")
    ap.add_argument("--baseline", default=None,
                    help="baseline JSON report; --check fails only on blocking findings NOT in it")
    ap.add_argument("--write-baseline", default=None,
                    help="write the current blocking findings as a baseline file, then exit 0")
    ap.add_argument("--no-runtime", action="store_true", help="ignore the R1-R12 report even if present")
    ap.add_argument("--json", action="store_true", help="print the JSON report to stdout")
    args = ap.parse_args(argv)

    if yaml is None:
        print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
        return 2

    if args.self_test:
        ok, log = self_test()
        for line in log:
            print(line)
        print("\nSELF-TEST", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    wdir = Path(args.workflows_dir)
    if not wdir.is_dir():
        print(f"ERROR: workflows dir not found: {wdir}", file=sys.stderr)
        return 2
    wfs = load_workflows(wdir)

    runtime = None
    if not args.no_runtime:
        rp = Path(args.runtime_report)
        if rp.is_file():
            try:
                runtime = json.loads(rp.read_text())
            except Exception:
                runtime = None

    rep = build_report(wfs, runtime)
    rep["generated_at"] = None  # filled by caller/CI to keep output diff-stable
    if args.json:
        print(json.dumps(rep, indent=1))
    elif args.dry_run or args.check:
        print(render_md(rep))
    if not args.dry_run and not args.check:
        outdir = Path(args.out or DEFAULT_OUT)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "gha_quality.json").write_text(json.dumps(rep, indent=1))
        (outdir / "gha_quality.md").write_text(render_md(rep))
        print(f"wrote {outdir/'gha_quality.json'} and {outdir/'gha_quality.md'}")
    if args.write_baseline:
        base = {"schema": "gha_quality_baseline.v1",
                "keys": sorted(_finding_key(f) for f in rep["findings"]
                               if f["severity"] in BLOCKING_SEVERITIES)}
        Path(args.write_baseline).write_text(json.dumps(base, indent=1))
        print(f"wrote baseline with {len(base['keys'])} blocking finding(s) to {args.write_baseline}")
        return 0
    if args.check:
        blocking = [f for f in rep["findings"] if f["severity"] in BLOCKING_SEVERITIES]
        if args.baseline and Path(args.baseline).is_file():
            known = set(json.loads(Path(args.baseline).read_text()).get("keys", []))
            new = [f for f in blocking if _finding_key(f) not in known]
            print(f"\n--check (baseline): {len(new)} NEW blocking violation(s) "
                  f"of {len(blocking)} total", file=sys.stderr)
            for f in new[:40]:
                print(f"  NEW {f['rule']} {f['workflow']}: {f['detail']}", file=sys.stderr)
            return 1 if new else 0
        print(f"\n--check: {len(blocking)} blocking violation(s)", file=sys.stderr)
        return 1 if blocking else 0
    return 0


def _finding_key(f: Dict[str, Any]) -> str:
    return f"{f['rule']}|{f['workflow']}|{f['detail']}"


if __name__ == "__main__":
    sys.exit(main())
