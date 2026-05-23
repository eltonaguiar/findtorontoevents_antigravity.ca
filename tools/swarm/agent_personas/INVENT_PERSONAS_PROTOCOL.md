# INVENT_PERSONAS Protocol

When you face a NEW problem domain that the existing persona library doesn't cover, do not hand-write a generalist prompt. Instead, ask a fast/cheap model (Cerebras/Mercury) to DESIGN a multi-specialist split for you, validate the structured output, and let the script materialize the persona files + a test blueprint.

Driver: `tools/swarm/invent_personas.py`. Slash command: `/swarm-invent`.

---

## When to invent personas (decision tree)

1. **Does an existing persona obviously fit?** Check `INDEX.md` first. If `forex-specialist` or `race-condition-specialist` covers it, USE that — don't invent.
2. **Is the problem trivial (1-line patch, single subsystem)?** Don't invent — overhead of 3 specialists + coordinator is wasted. Use one general reviewer.
3. **Does the symptom touch 2+ orthogonal subsystems** (e.g. concurrency + data + UI)? **Invent.**
4. **Is the problem statement vague?** Sharpen it FIRST. The design engine produces garbage from "the site is slow"; it produces a useful split from "the homepage event grid renders past events when This Month is selected; React filter shows 6892 but DOM shows ~14000; bug is in the imperative overlay in `index.html` lines 3441-3575".

---

## The meta-prompt

Saved as `META_PROMPT_TEMPLATE` in `invent_personas.py`. The design engine is asked for ONE JSON object with this shape:

```jsonc
{
  "domain": "<short-kebab>",
  "personas": [ /* exactly --num-personas items */
    {
      "name": "kebab-name",
      "filename": "snake_name.md",
      "role": "...",
      "scope": "...",
      "system_prompt": "...",
      "key_analytical_moves": ["...", "..."],
      "output_format": "...",
      "triggers": ["..."],
      "anti_patterns": ["..."]
    }
  ],
  "coordinator": {
    "name": "<domain>-coordinator-synthesizer",
    "filename": "<domain>_coordinator_synthesizer.md",
    "role": "...",
    "rollup_format": "...",
    "ranking_criteria": "..."
  },
  "blueprint": {
    "phases": [ {"phase": 1, "name": "plan", "description": "...", "outputs": ["plan.md"]}, ... ],
    "cycles": 1-5,
    "engines_per_cycle_min": 3-7,
    "verification_required": "playwright_trace | unit_tests | manual | none",
    "ship_today_threshold": "..."
  }
}
```

The script validates schema; on schema fail it falls back: `cerebras` -> `inception` -> `claude`. If all 3 fail, it errors out with a useful diagnostic.

---

## Required fields per persona

- `name` — kebab-case, used in `--persona <name>` resolution.
- `filename` — snake_case with `.md` suffix, must be unique within the run.
- `role` — one sentence, surfaced in `INDEX.md`.
- `scope` — 2-4 sentences naming the bug class.
- `system_prompt` — the body the model sees as preamble; first-person ("You are ...").
- `key_analytical_moves` — list of bullets the persona applies mechanically.
- `output_format` — what every finding must contain (severity, location with `file:line`, root cause, fix snippet).
- `triggers` — symptoms / code smells that should spawn this persona.
- `anti_patterns` — patterns the persona MUST flag.

The script renders these into the same canonical format as `race_condition_specialist.md` (frontmatter + body sections).

---

## Blueprint structure

The blueprint is a separate `blueprints/<domain>_blueprint.md` file describing how to RUN the personas:

- **Phases** — typically: plan → parallel specialists → cross-critique → coordinator synthesis.
- **Cycles** — how many times to run the loop (1 for a quick triage, 3 for the full Kimi pattern).
- **Engines per cycle min** — the floor on parallel coverage; 3 catches most fabrications, 5 is the Kimi-pattern default.
- **Verification required** — what kind of live test must pass before "ship today" (Playwright trace, unit test, manual, none).
- **Ship-today threshold** — one sentence describing what counts as a shippable finding (severity bar + cite quality + corroboration).

---

## Worked example: the filter bug

Input: `reports/filter_bug_investigation_2026_05_03.md` describing two cooperating root causes in `TORONTOEVENTS_ANTIGRAVITY/index.html` (eventData-gated past-events guard + data-layer drift).

If we'd run `invent_personas.py --problem-file reports/filter_bug_investigation_2026_05_03.md` from the start, we'd expect the design engine to produce roughly the Kimi split:

- **race-condition-specialist** — capture-phase listener / `stopImmediatePropagation` / synthetic-click swallowing.
- **datetime-timezone-specialist** — UTC↔local / ISO parse / year-wrap / "today" computation.
- **react-dom-specialist** — vanilla-JS↔React seam / MutationObserver loops / inline-style mutation.
- **filter-bug-coordinator-synthesizer** — merges the three reports, ranks, buckets.

With a blueprint of 1 cycle, ≥4 engines per cycle, verification=`playwright_trace`, ship-today threshold = "CRITICAL severity, ≥2-specialist corroboration, file:line cited, fix is a code snippet".

In practice today, since these 4 personas already exist, the protocol short-circuits at decision-tree step 1.

---

## Limits / gotchas

- **Do not invent personas for trivial bugs.** A 1-line patch does not need a multi-specialist split. The script enforces a 50-char minimum on the problem description but cannot judge triviality — that is the operator's call.
- **Do not run against a vague problem statement.** "The dashboard is slow" produces a split that is not useful. Add file paths, line ranges, observed-vs-expected, and a hypothesis or two BEFORE invoking.
- **Sanity-check the blueprint cycle count.** If the design engine returns `cycles: 5`, that is 5x the cost. For typical bugs, 1-2 cycles suffice. Edit the blueprint before dispatch.
- **Defensive overwrite policy.** If a persona filename already exists in `agent_personas/`, the script writes to `<name>.invented.md` instead and prints a WARN. Use `--force` only if you intend to clobber a hand-crafted file.
- **The design engine can hallucinate filenames or domain ids.** Schema validation catches the obvious failure modes (missing fields, wrong shape, bad filename pattern). It does NOT catch semantic drift — review the generated files before fanning out a paid swarm against them.

---

## See also

- `multi_specialist_debugging_strategy.md` — the pattern this is bootstrapping.
- `INDEX.md` — registry of existing personas (check first).
- `tools/swarm/AGENTS_HOWTO.md` §"Need novel personas for a new problem".
- `.claude/commands/swarm-invent.md` — slash command wrapper.
