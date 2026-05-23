#!/usr/bin/env python3
"""
4-phase swarm runner — pre-work → brainstorm → synthesis → QA review.

Distinct from swarm_run.py (single fan-out) and swarm_followup.py (single
engine, multi-turn). This runs FOUR sequential fan-outs, each phase building
on prior outputs.

Phase 0: 1 engine pre-scopes the task (data audit, blind spots, decomposition)
Phase 1: 4-5 engines from different model families brainstorm action plans IN
         PARALLEL with Ruflo brainstorm_review (4 more free models)
Phase 2: 1 strong synthesizer consolidates all Phase 1 output into one plan
Phase 3: 2-3 cross-family critics QA the synthesized plan (regression risks,
         verification steps, future-monitoring areas)

Usage:
    python tools/swarm/swarmwithprework.py --task "<task description>"
    python tools/swarm/swarmwithprework.py --task-file path/to/input.md
    python tools/swarm/swarmwithprework.py --from <prior_run_ts>

Outputs under swarm_runs/swarmwithprework_<TS>/:
    INPUT.md, PHASE0_PREWORK.md, phase1/, PHASE2_ACTION_PLAN.md, phase3/, SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

REPO = Path(__file__).resolve().parent.parent.parent
SWARM_RUN = REPO / "tools" / "swarm" / "swarm_run.py"
RUFLO = REPO / ".ruflo" / "orchestrator.py"


def run(cmd, cwd=None, capture=True):
    print(f"$ {' '.join(shlex.quote(c) for c in cmd)}", flush=True)
    p = subprocess.run(cmd, cwd=cwd or REPO, capture_output=capture, text=True)
    if p.returncode != 0:
        print(p.stdout)
        print(p.stderr, file=sys.stderr)
    return p


def write(path: Path, txt: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt, encoding="utf-8")
    print(f"wrote {path}  ({len(txt)} chars)")


def read_raw_or_json(run_dir: Path, engine: str) -> str:
    raw = run_dir / f"{engine}.json.raw.txt"
    if raw.exists():
        return raw.read_text(encoding="utf-8", errors="replace")
    js = run_dir / f"{engine}.json"
    if js.exists():
        try:
            d = json.loads(js.read_text(encoding="utf-8"))
            return d.get("commentary_text") or d.get("response") or json.dumps(d)
        except Exception:
            return js.read_text(encoding="utf-8", errors="replace")
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--task", help="inline task description")
    g.add_argument("--task-file", help="path to task description file")
    g.add_argument("--from", dest="from_ts", help="prior run TS to build upon")
    ap.add_argument("--phase1-engines", default="deepseek,xai,inception,gemini_api,cerebras",
                    help="comma-separated engines for Phase 1 brainstorm")
    ap.add_argument("--phase0-engine", default="cerebras")
    ap.add_argument("--phase2-engine", default="deepseek")
    ap.add_argument("--phase3-engines", default="xai,gemini_api,inception")
    ap.add_argument("--skip-ruflo", action="store_true",
                    help="skip Ruflo parallel brainstorm in Phase 1")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = REPO / "swarm_runs" / f"swarmwithprework_{ts}"
    out.mkdir(parents=True, exist_ok=True)

    # ── INPUT ──
    if args.task:
        task_md = args.task
    elif args.task_file:
        task_md = Path(args.task_file).read_text(encoding="utf-8")
    else:
        prior = REPO / "swarm_runs" / f"swarmwithprework_{args.from_ts}"
        if not prior.exists():
            sys.exit(f"prior run not found: {prior}")
        task_md = (
            f"# Continuation of run {args.from_ts}\n\n"
            f"## Prior SUMMARY\n\n"
            + (prior / "SUMMARY.md").read_text(encoding="utf-8")
        )

    input_md = out / "INPUT.md"
    write(input_md, task_md)

    # ── PHASE 0 — Pre-work ──
    phase0_prompt = out / "_phase0_prompt.md"
    write(phase0_prompt,
        "# Phase 0 — pre-work scoping\n\n"
        "You are a SCOPER, not a planner. Read the task below and produce "
        "ONLY: (a) what data/files/queries to pull before any planning, "
        "(b) obvious blind spots someone might miss, (c) acceptance criteria, "
        "(d) decomposition into 3-6 sub-tasks, (e) likely failure modes. "
        "Cap 600 words. NO action plan — that comes later.\n\n"
        "## Task\n\n" + task_md
    )
    phase0_dir = out / "phase0"
    run(["python", str(SWARM_RUN),
         "--prompt-file", str(phase0_prompt),
         "--engines", args.phase0_engine,
         "--out-dir", str(phase0_dir)])
    phase0_md = out / "PHASE0_PREWORK.md"
    write(phase0_md, read_raw_or_json(phase0_dir, args.phase0_engine))

    # ── PHASE 1 — Brainstorm (Tools/Swarm + Ruflo in parallel) ──
    phase1_prompt = out / "_phase1_prompt.md"
    write(phase1_prompt,
        "# Phase 1 — multi-family brainstorm\n\n"
        "Read the task and the Phase 0 pre-scope. Produce YOUR OWN action plan "
        "(NOT a critique of Phase 0). Required structure: "
        "(a) data audit checklist, (b) wire-up sequence with file:function "
        "targets, (c) risk register, (d) kill criteria with NUMERIC thresholds. "
        "Cap 700 words.\n\n"
        "## Task\n\n" + task_md +
        "\n\n## Phase 0 pre-scope\n\n" + phase0_md.read_text(encoding="utf-8")
    )
    phase1_dir = out / "phase1"
    procs = []
    procs.append(subprocess.Popen(
        ["python", str(SWARM_RUN),
         "--prompt-file", str(phase1_prompt),
         "--engines", args.phase1_engines,
         "--out-dir", str(phase1_dir),
         "--max-parallel", "5"],
        cwd=REPO,
    ))
    if not args.skip_ruflo and RUFLO.exists():
        procs.append(subprocess.Popen(
            ["python", str(RUFLO),
             "--swarm", "brainstorm_review",
             "--tier", "hybrid", "--no-verify",
             "--task", phase1_prompt.read_text(encoding="utf-8")],
            cwd=REPO,
        ))
    for p in procs:
        p.wait()

    # gather phase1 outputs
    phase1_concat = []
    if phase1_dir.exists():
        for engine in args.phase1_engines.split(","):
            txt = read_raw_or_json(phase1_dir, engine.strip())
            if txt and len(txt) > 200:
                phase1_concat.append(f"\n=== {engine.strip()} ===\n{txt}")
    # Ruflo brainstorm output
    ruflo_compiled = REPO / "swarm_runs" / "ruflo-insights" / "COMPILED_latest.json"
    if ruflo_compiled.exists():
        try:
            d = json.loads(ruflo_compiled.read_text(encoding="utf-8"))
            for ins in (d if isinstance(d, list) else d.get("insights", [])):
                if ins.get("swarm") == "brainstorm_review":
                    phase1_concat.append(f"\n=== ruflo:brainstorm_review ===\n{ins.get('output','')}")
        except Exception as e:
            print(f"ruflo concat ERR: {e}", file=sys.stderr)
    phase1_combined = out / "PHASE1_ALL_BRAINSTORM.md"
    write(phase1_combined, "\n".join(phase1_concat) if phase1_concat else "(no engines returned)")

    # ── PHASE 2 — Synthesis ──
    phase2_prompt = out / "_phase2_prompt.md"
    write(phase2_prompt,
        "# Phase 2 — synthesize action plan\n\n"
        "Read original task + Phase 0 pre-scope + ALL Phase 1 brainstorms below. "
        "Produce ONE consolidated action plan: dedupe overlapping ideas, "
        "priority-rank by lift, drop low-confidence proposals, give concrete "
        "file:function targets, numeric thresholds, ordered execution sequence. "
        "Where engines disagree, pick one and explain why in <=2 sentences. "
        "Cap 1000 words.\n\n"
        "## Original task\n\n" + task_md +
        "\n\n## Phase 0\n\n" + phase0_md.read_text(encoding="utf-8") +
        "\n\n## Phase 1 outputs\n" + phase1_combined.read_text(encoding="utf-8")
    )
    phase2_dir = out / "phase2"
    run(["python", str(SWARM_RUN),
         "--prompt-file", str(phase2_prompt),
         "--engines", args.phase2_engine,
         "--out-dir", str(phase2_dir)])
    phase2_md = out / "PHASE2_ACTION_PLAN.md"
    write(phase2_md, read_raw_or_json(phase2_dir, args.phase2_engine))

    # ── PHASE 3 — QA critics ──
    phase3_prompt = out / "_phase3_prompt.md"
    write(phase3_prompt,
        "# Phase 3 — QA critic review\n\n"
        "You are a critic, not an author. The plan below in PHASE2_ACTION_PLAN "
        "claims certain fixes. For each major claim, produce: "
        "(a) blast radius — what breaks if it's wrong, "
        "(b) verification step a coder MUST run after implementing, "
        "(c) regression risk — what existing behavior could this break, "
        "(d) future monitoring — what to watch in the WEEKS after merge, "
        "(e) one improvement the plan missed. "
        "Do NOT rewrite the plan. Cap 500 words.\n\n"
        "## Action plan to critique\n\n" + phase2_md.read_text(encoding="utf-8")
    )
    phase3_dir = out / "phase3"
    run(["python", str(SWARM_RUN),
         "--prompt-file", str(phase3_prompt),
         "--engines", args.phase3_engines,
         "--out-dir", str(phase3_dir),
         "--max-parallel", "3"])

    # ── SUMMARY ──
    phase3_outputs = []
    for engine in args.phase3_engines.split(","):
        txt = read_raw_or_json(phase3_dir, engine.strip())
        if txt:
            phase3_outputs.append(f"\n### {engine.strip()}\n{txt}")
    summary = out / "SUMMARY.md"
    write(summary,
        f"# /swarmwithprework run {ts}\n\n"
        f"## Task\n\n{task_md.splitlines()[0] if task_md else '(no task)'}\n\n"
        f"## Roster\n"
        f"- Phase 0: {args.phase0_engine}\n"
        f"- Phase 1: {args.phase1_engines}{' + ruflo brainstorm_review' if not args.skip_ruflo else ''}\n"
        f"- Phase 2 (synth): {args.phase2_engine}\n"
        f"- Phase 3 (critics): {args.phase3_engines}\n\n"
        f"## Final action plan (Phase 2)\n\n{phase2_md.read_text(encoding='utf-8')}\n\n"
        f"## QA findings (Phase 3)\n{''.join(phase3_outputs)}\n\n"
        f"## Files\n"
        f"- `{input_md.relative_to(REPO)}`\n"
        f"- `{phase0_md.relative_to(REPO)}`\n"
        f"- `{phase1_dir.relative_to(REPO)}/<engine>.{{json,raw.txt}}`\n"
        f"- `{phase1_combined.relative_to(REPO)}`\n"
        f"- `{phase2_md.relative_to(REPO)}`\n"
        f"- `{phase3_dir.relative_to(REPO)}/<engine>.{{json,raw.txt}}`\n"
    )

    # post-phase inspect
    inspect = REPO / "tools" / "swarm" / "swarm_inspect.py"
    if inspect.exists():
        run(["python", str(inspect), str(phase1_dir)])
        run(["python", str(inspect), str(phase3_dir)])

    print(f"\n✓ Run complete: {out}")


if __name__ == "__main__":
    main()
