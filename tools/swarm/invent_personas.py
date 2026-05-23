#!/usr/bin/env python3
"""Bootstrap custom personas + a test blueprint for a new problem domain.

Inspired by the Kimi filter-bug run (2026-05-04), where 3 specialists
(race / datetime / dom) plus a coordinator-synthesizer found a bug that
3 single-prompt PR reviews missed. This script lets the swarm itself
INVENT the right persona split for an arbitrary new problem domain.

Usage:
    python tools/swarm/invent_personas.py --problem-file my_problem.md
    python tools/swarm/invent_personas.py --problem-file p.md \\
        --persona-design-engine cerebras \\
        --num-personas 3 \\
        --output-dir tools/swarm/agent_personas/ \\
        [--dry-run]

The design engine reads the problem description and emits structured JSON
(see INVENT_PERSONAS_PROTOCOL.md for the schema). This script validates
the JSON, writes one .md per persona + coordinator, writes a blueprint
under `blueprints/<domain>_blueprint.md`, and appends entries to INDEX.md.

Default design-engine: `cerebras` (cheap+fast). Falls back to `inception`
then `claude` on engine error or malformed JSON. If all 3 fail the script
exits non-zero with a useful error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SWARM_DIR = REPO / "tools" / "swarm"
PERSONAS_DIR = SWARM_DIR / "agent_personas"
BLUEPRINTS_DIR = PERSONAS_DIR / "blueprints"

# Make sibling modules importable when run as a script.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.swarm import api_consult  # noqa: E402
from tools.swarm.config_loader import load_dotenv  # noqa: E402


META_PROMPT_TEMPLATE = """You are the Persona Architect for an AI agent swarm. Your job: read a problem description and design a small set of specialist personas (plus a coordinator-synthesizer) that, run in parallel, will surface the root cause better than one generalist reviewer.

The pattern you are replicating is the Kimi filter-bug split (race-condition + datetime + react-dom + coordinator) — three orthogonal specialists, each with a NARROW system prompt, that catch what a single generalist misses.

# Problem description

{problem}

# Output contract

Respond with EXACTLY ONE JSON object, no prose, no code fence. Schema:

{{
  "domain": "<short_kebab_name e.g. 'frontend-filter-bug'>",
  "personas": [
    {{
      "name": "<kebab-case persona name, e.g. 'state-machine-specialist'>",
      "filename": "<snake_case_filename.md, e.g. 'state_machine_specialist.md'>",
      "role": "<one sentence>",
      "scope": "<2-4 sentences naming the bug class this persona owns>",
      "system_prompt": "<3-6 sentences — what the persona thinks about, in first person 'You are ...'>",
      "key_analytical_moves": ["<bullet>", "<bullet>", "..."],
      "output_format": "<what every finding must contain — severity, location, root cause, fix snippet, etc.>",
      "triggers": ["<symptom or code-smell>", "..."],
      "anti_patterns": ["<anti-pattern this persona must flag>", "..."]
    }}
    // ... exactly {num_personas} personas
  ],
  "coordinator": {{
    "name": "<kebab>-coordinator-synthesizer",
    "filename": "<snake>_coordinator_synthesizer.md",
    "role": "<one sentence>",
    "rollup_format": "<the structure of FINDINGS.md the coordinator emits>",
    "ranking_criteria": "<how findings are ranked: severity x corroboration x cite-quality, etc.>"
  }},
  "blueprint": {{
    "phases": [
      {{"phase": 1, "name": "plan", "description": "...", "outputs": ["plan.md"]}},
      {{"phase": 2, "name": "parallel_specialists", "description": "...", "outputs": ["<persona>_report.md", "..."]}},
      {{"phase": 3, "name": "cross_critique", "description": "...", "outputs": ["..."]}},
      {{"phase": 4, "name": "coordinator_synthesis", "description": "...", "outputs": ["FINDINGS.md", "plan_ranked.md"]}}
    ],
    "cycles": <int 1-3>,
    "engines_per_cycle_min": <int 3-7>,
    "verification_required": "<playwright_trace | unit_tests | manual | none>",
    "ship_today_threshold": "<one sentence>"
  }}
}}

Constraints:
- Exactly {num_personas} personas (NOT counting the coordinator).
- Personas must be ORTHOGONAL — no two should focus on the same bug class.
- `filename` must be unique snake_case ending in `.md`.
- `domain` is a short identifier used in filenames; lowercase kebab.
- Do NOT invent personas that already exist for this domain (assume race-condition, datetime-timezone, react-dom, asset-class specialists already exist; design NEW orthogonal ones).
- Output ONLY the JSON object. No prose before or after. No ```json fence.
"""


REQUIRED_PERSONA_FIELDS = {
    "name", "filename", "role", "scope", "system_prompt",
    "key_analytical_moves", "output_format", "triggers", "anti_patterns",
}
REQUIRED_COORD_FIELDS = {"name", "filename", "role", "rollup_format", "ranking_criteria"}
REQUIRED_BLUEPRINT_FIELDS = {
    "phases", "cycles", "engines_per_cycle_min",
    "verification_required", "ship_today_threshold",
}


def extract_json(raw: str) -> dict:
    """Pull the first top-level JSON object out of a model response.

    Tolerates ```json fences, leading prose, trailing commentary. Raises
    ValueError with a useful diagnostic if no parseable object is found.
    """
    if not raw or not raw.strip():
        raise ValueError("empty response from design engine")
    text = raw.strip()
    # Strip a leading ```json or ``` fence.
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    # Find first { and matching closing }.
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no '{{' in response (head: {raw[:200]!r})")
    depth = 0
    in_str = False
    esc = False
    end = -1
    for i in range(start, len(text)):
        c = text[i]
        if esc:
            esc = False
            continue
        if c == "\\" and in_str:
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        raise ValueError(f"unbalanced braces (head: {text[:200]!r})")
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"json parse failed: {e.msg} @ line {e.lineno} col {e.colno}\n"
                         f"  candidate head: {candidate[:300]!r}") from e


def validate_design(d: dict, num_personas: int) -> list[str]:
    """Return list of validation errors. Empty list = OK."""
    errs: list[str] = []
    if not isinstance(d, dict):
        return ["top-level is not an object"]
    domain = d.get("domain")
    if not isinstance(domain, str) or not re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,40}", domain or ""):
        errs.append(f"domain missing/invalid (got {domain!r}) — need lowercase kebab")
    personas = d.get("personas")
    if not isinstance(personas, list):
        errs.append("personas missing or not a list")
    else:
        if len(personas) != num_personas:
            errs.append(f"expected {num_personas} personas, got {len(personas)}")
        seen_files: set[str] = set()
        for i, p in enumerate(personas):
            if not isinstance(p, dict):
                errs.append(f"persona[{i}] is not an object")
                continue
            missing = REQUIRED_PERSONA_FIELDS - set(p.keys())
            if missing:
                errs.append(f"persona[{i}] ({p.get('name','?')}) missing fields: {sorted(missing)}")
            fn = p.get("filename", "")
            if not re.fullmatch(r"[a-z0-9_]+\.md", fn or ""):
                errs.append(f"persona[{i}] filename invalid: {fn!r} (need snake_case .md)")
            if fn in seen_files:
                errs.append(f"persona[{i}] duplicate filename: {fn}")
            seen_files.add(fn)
            for list_field in ("key_analytical_moves", "triggers", "anti_patterns"):
                if list_field in p and not isinstance(p[list_field], list):
                    errs.append(f"persona[{i}] {list_field} must be a list")
    coord = d.get("coordinator")
    if not isinstance(coord, dict):
        errs.append("coordinator missing or not an object")
    else:
        missing = REQUIRED_COORD_FIELDS - set(coord.keys())
        if missing:
            errs.append(f"coordinator missing fields: {sorted(missing)}")
        if not re.fullmatch(r"[a-z0-9_]+\.md", coord.get("filename", "") or ""):
            errs.append(f"coordinator filename invalid: {coord.get('filename')!r}")
    bp = d.get("blueprint")
    if not isinstance(bp, dict):
        errs.append("blueprint missing or not an object")
    else:
        missing = REQUIRED_BLUEPRINT_FIELDS - set(bp.keys())
        if missing:
            errs.append(f"blueprint missing fields: {sorted(missing)}")
        if not isinstance(bp.get("phases"), list) or not bp.get("phases"):
            errs.append("blueprint.phases must be a non-empty list")
        cycles = bp.get("cycles")
        if not isinstance(cycles, int) or not (1 <= cycles <= 5):
            errs.append(f"blueprint.cycles must be int 1-5 (got {cycles!r})")
    return errs


def call_design_engine(engine: str, prompt: str) -> str:
    """Invoke a design engine via api_consult. Raises on failure."""
    if engine == "cerebras":
        content, _ = api_consult.call_cerebras(prompt, None, None)
    elif engine == "ollama_cloud":
        content, _ = api_consult.call_ollama_cloud(prompt, None, None)
    elif engine in api_consult.PROVIDERS:
        content, _ = api_consult.call_openai_compat(engine, prompt, None, None)
    elif engine == "claude":
        # Claude CLI fallback — not implemented here. Keep a clear error.
        raise RuntimeError(
            "claude fallback requires the Claude CLI worker — re-run via "
            "`python tools/swarm/worker_runner.py --engine claude` manually "
            "and feed the JSON back through this script with --design-json."
        )
    else:
        raise RuntimeError(f"unknown design engine: {engine}")
    return content


def design_personas(problem: str, num_personas: int,
                    primary_engine: str) -> tuple[dict, str, list[str]]:
    """Try primary engine, then fallbacks. Returns (design, engine_used, errors)."""
    fallback_chain = [primary_engine]
    for fb in ("cerebras", "inception", "claude"):
        if fb not in fallback_chain:
            fallback_chain.append(fb)
    prompt = META_PROMPT_TEMPLATE.format(problem=problem, num_personas=num_personas)
    errors: list[str] = []
    for engine in fallback_chain:
        try:
            print(f"[invent] trying design engine: {engine}", file=sys.stderr)
            raw = call_design_engine(engine, prompt)
        except Exception as e:
            errors.append(f"{engine}: {type(e).__name__}: {e}")
            print(f"[invent] {engine} failed: {e}", file=sys.stderr)
            continue
        try:
            design = extract_json(raw)
        except ValueError as e:
            errors.append(f"{engine} json: {e}")
            print(f"[invent] {engine} returned malformed JSON: {e}", file=sys.stderr)
            continue
        verrors = validate_design(design, num_personas)
        if verrors:
            errors.append(f"{engine} schema: {verrors}")
            print(f"[invent] {engine} schema errors: {verrors}", file=sys.stderr)
            continue
        return design, engine, errors
    raise RuntimeError(
        "all design engines failed. Errors:\n  - "
        + "\n  - ".join(errors)
    )


def render_persona_md(p: dict, *, inspired_by: str) -> str:
    """Render a persona dict to the canonical .md format (frontmatter + body)."""
    description = p.get("scope", p.get("role", "")).replace("\n", " ").strip()
    moves = p.get("key_analytical_moves") or []
    triggers = p.get("triggers") or []
    antis = p.get("anti_patterns") or []
    moves_md = "\n".join(f"{i+1}. **{m}**" if not m.startswith("**") else f"{i+1}. {m}"
                          for i, m in enumerate(moves)) or "1. (none specified)"
    triggers_md = "\n".join(f"- {t}" for t in triggers) or "- (none specified)"
    antis_md = "\n".join(f"- {a}" for a in antis) or "- (none specified)"
    body = f"""---
name: {p['name']}
description: {description}
tools:
  - Bash
  - Read
  - Grep
  - Glob
model: sonnet
inspired_by: {inspired_by}
---

{p.get('system_prompt', '').strip()}

## Scope

{p.get('scope', '').strip()}

## Key analytical moves

{moves_md}

## Required output format

{p.get('output_format', '').strip()}

## Triggers

{triggers_md}

## Anti-patterns this persona must flag

{antis_md}
"""
    return body


def render_coordinator_md(c: dict, *, inspired_by: str) -> str:
    description = c.get("role", "").replace("\n", " ").strip()
    body = f"""---
name: {c['name']}
description: {description}
tools:
  - Bash
  - Read
  - Grep
  - Glob
model: sonnet
inspired_by: {inspired_by}
---

You are a coordinator/synthesizer. You do not generate new findings — you merge specialist outputs into one ranked, citable plan.

## Role

{c.get('role', '').strip()}

## Rollup format

{c.get('rollup_format', '').strip()}

## Ranking criteria

{c.get('ranking_criteria', '').strip()}

## Anti-patterns

- A specialist report with severity claims but no `file:line` citations -> drop the finding.
- Two specialists reporting the "same" bug at different lines -> probably TWO bugs; do not collapse.
- A "fix" that is prose, not a code snippet -> request the specialist re-emit with code.
- A deploy-today bucket with > 5 items -> re-prioritize.
"""
    return body


def render_blueprint_md(domain: str, design: dict, *, problem_path: str,
                         engine_used: str) -> str:
    bp = design["blueprint"]
    personas = design["personas"]
    coord = design["coordinator"]
    phases_md = ""
    for ph in bp.get("phases", []):
        outs = ", ".join(f"`{o}`" for o in (ph.get("outputs") or []))
        phases_md += (
            f"### Phase {ph.get('phase','?')}: {ph.get('name','?')}\n\n"
            f"{ph.get('description','').strip()}\n\n"
            f"**Outputs:** {outs or '(none specified)'}\n\n"
        )
    persona_list = "\n".join(
        f"- `{p['name']}` -> `{p['filename']}` — {p.get('role','').strip()}"
        for p in personas
    )
    return f"""# Blueprint: {domain}

Generated by `tools/swarm/invent_personas.py` from problem file `{problem_path}` using design engine `{engine_used}`.

## Personas in this blueprint

{persona_list}
- `{coord['name']}` -> `{coord['filename']}` (coordinator)

## Phases

{phases_md}
## Cycle count

**{bp.get('cycles')}** cycle(s), minimum **{bp.get('engines_per_cycle_min')}** engines per cycle.

## Verification required

`{bp.get('verification_required')}`

## Ship-today threshold

{bp.get('ship_today_threshold','').strip()}

## Recommended invocation

```bash
# Phase 2 — parallel specialists (fan out to N engines, one per persona):
python tools/swarm/swarm_run.py \\
    --prompt-file <your_prompt.md> \\
    --engines deepseek,xai,kilo,cerebras \\
    --persona {personas[0]['name'] if personas else '<persona-name>'} \\
    --max-parallel 4

# Phase 4 — coordinator synthesis on the run dir:
python tools/swarm/worker_runner.py \\
    --engine claude \\
    --prompt-file swarm_runs/<run>/_coordinator_input.md \\
    --persona {coord['name']} \\
    --out-file swarm_runs/<run>/FINDINGS.json
```
"""


def write_file_safe(path: Path, content: str, *, force: bool = False) -> tuple[Path, bool]:
    """Write UTF-8 with LF endings. If file exists and not force, write to <name>.invented.md
    and return (actual_path, True) for warned. Otherwise return (path, False)."""
    warned = False
    if path.exists() and not force:
        new_path = path.with_name(path.stem + ".invented" + path.suffix)
        path = new_path
        warned = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path, warned


def append_to_index(domain: str, personas: list[dict], coord: dict) -> None:
    idx = PERSONAS_DIR / "INDEX.md"
    existing = idx.read_text(encoding="utf-8") if idx.exists() else ""
    section_header = f"## Invented personas — {domain} (generated)"
    if section_header in existing:
        # Don't double-append.
        return
    rows = "\n".join(
        f"| {p['name']} | `{p['filename']}` | {p.get('role','').strip()} | invented |"
        for p in personas
    )
    rows += f"\n| {coord['name']} | `{coord['filename']}` | {coord.get('role','').strip()} | invented (coordinator) |"
    block = f"""

{section_header}

Generated by `tools/swarm/invent_personas.py` (see `INVENT_PERSONAS_PROTOCOL.md`).
Blueprint: `blueprints/{domain}_blueprint.md`.

| Persona | File | One-line description | Source |
|---|---|---|---|
{rows}
"""
    with idx.open("a", encoding="utf-8", newline="\n") as f:
        f.write(block)


def print_summary(design: dict, written: list[tuple[Path, bool]],
                  engine_used: str, problem_path: str) -> None:
    domain = design["domain"]
    print()
    print("=" * 72)
    print(f"INVENT_PERSONAS — domain: {domain}")
    print(f"Design engine used: {engine_used}")
    print(f"Problem: {problem_path}")
    print("=" * 72)
    print(f"{'File':<60} {'Status':<10}")
    print("-" * 72)
    for path, warned in written:
        status = "INVENTED" if warned else "NEW"
        try:
            rel = path.relative_to(REPO)
        except ValueError:
            rel = path
        print(f"{str(rel):<60} {status:<10}")
    print()
    persona0 = design["personas"][0]["name"] if design["personas"] else "<persona>"
    print("Recommended next-step invocation:")
    print()
    print(f"  python tools/swarm/swarm_run.py \\")
    print(f"      --prompt-file {problem_path} \\")
    print(f"      --engines deepseek,xai,kilo,cerebras \\")
    print(f"      --persona {persona0} \\")
    print(f"      --max-parallel 4")
    print()
    print(f"Then synthesize with the coordinator:")
    print(f"  --persona {design['coordinator']['name']}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--problem-file", required=True, type=Path)
    ap.add_argument("--persona-design-engine", default="cerebras",
                    help="design engine (default cerebras). Falls back to inception, then claude.")
    ap.add_argument("--num-personas", type=int, default=3,
                    help="how many specialist personas to invent (default 3, plus 1 coordinator)")
    ap.add_argument("--output-dir", type=Path, default=PERSONAS_DIR)
    ap.add_argument("--dry-run", action="store_true",
                    help="print plan; don't write files")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing persona files (default: write to <name>.invented.md)")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    load_dotenv()

    if not args.problem_file.exists():
        print(f"problem file not found: {args.problem_file}", file=sys.stderr)
        return 2
    problem = args.problem_file.read_text(encoding="utf-8")
    if len(problem.strip()) < 50:
        print("problem description is too short (<50 chars). Be specific.", file=sys.stderr)
        return 2

    try:
        design, engine_used, prior_errors = design_personas(
            problem, args.num_personas, args.persona_design_engine,
        )
    except RuntimeError as e:
        print(f"[invent] FATAL: {e}", file=sys.stderr)
        return 5

    if prior_errors:
        print(f"[invent] note: {len(prior_errors)} engine(s) failed before "
              f"{engine_used} succeeded:", file=sys.stderr)
        for er in prior_errors:
            print(f"  - {er[:200]}", file=sys.stderr)

    domain = design["domain"]

    if args.dry_run:
        print("[invent] DRY RUN — would create:")
        for p in design["personas"]:
            print(f"  {args.output_dir / p['filename']}")
        print(f"  {args.output_dir / design['coordinator']['filename']}")
        print(f"  {BLUEPRINTS_DIR / (domain + '_blueprint.md')}")
        print()
        print(json.dumps(design, indent=2))
        return 0

    inspired = f"invented by {engine_used} from {args.problem_file.name}"
    written: list[tuple[Path, bool]] = []

    args.output_dir.mkdir(parents=True, exist_ok=True)
    BLUEPRINTS_DIR.mkdir(parents=True, exist_ok=True)

    for p in design["personas"]:
        target = args.output_dir / p["filename"]
        actual, warned = write_file_safe(
            target, render_persona_md(p, inspired_by=inspired), force=args.force,
        )
        if warned:
            print(f"[invent] WARN: {target.name} already exists; wrote to {actual.name}",
                  file=sys.stderr)
        written.append((actual, warned))

    coord = design["coordinator"]
    coord_target = args.output_dir / coord["filename"]
    actual, warned = write_file_safe(
        coord_target, render_coordinator_md(coord, inspired_by=inspired), force=args.force,
    )
    if warned:
        print(f"[invent] WARN: {coord_target.name} already exists; wrote to {actual.name}",
              file=sys.stderr)
    written.append((actual, warned))

    bp_target = BLUEPRINTS_DIR / f"{domain}_blueprint.md"
    bp_content = render_blueprint_md(
        domain, design,
        problem_path=str(args.problem_file),
        engine_used=engine_used,
    )
    actual, warned = write_file_safe(bp_target, bp_content, force=args.force)
    if warned:
        print(f"[invent] WARN: {bp_target.name} already exists; wrote to {actual.name}",
              file=sys.stderr)
    written.append((actual, warned))

    # Save the raw design JSON as a sidecar for reproducibility / debugging.
    design_json_path = BLUEPRINTS_DIR / f"{domain}_design.json"
    design_json_path.write_text(json.dumps(design, indent=2),
                                 encoding="utf-8", newline="\n")
    written.append((design_json_path, False))

    append_to_index(domain, design["personas"], coord)

    print_summary(design, written, engine_used, str(args.problem_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
