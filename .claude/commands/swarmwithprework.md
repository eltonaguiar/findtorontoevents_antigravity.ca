---
description: 4-phase swarm — pre-work insight → multi-family brainstorm → synthesized action plan → QA critic review. Builds on Tools/Swarm + Ruflo.
argument-hint: ["<task>" | chat | --from <prior_ts>] [--skip-ruflo]
---

User invoked `/swarmwithprework $ARGUMENTS`.

Goal: walk a task through 4 sequential swarm phases using model-family variety. Each phase builds on prior outputs. Produces a pre-scoped, multi-vendor brainstormed, synthesized, and QA-reviewed action plan with verification steps and future-monitoring areas.

Architecture:

| Phase | Role | Default engine(s) | Output |
|-------|------|-------------------|--------|
| 0 | Pre-work scoper | `cerebras` | `PHASE0_PREWORK.md` — data to pull, blind spots, acceptance criteria, decomposition, failure modes |
| 1 | Multi-family brainstorm | `deepseek,xai,inception,gemini_api,cerebras` + Ruflo `brainstorm_review` (~4 free models) in parallel | `phase1/<engine>.{json,raw.txt}` |
| 2 | Synthesizer | `deepseek` (largest context) | `PHASE2_ACTION_PLAN.md` |
| 3 | QA critics | `xai,gemini_api,inception` (different families from synthesizer) | `phase3/<engine>.{json,raw.txt}` |

## Dispatch

Parse `$ARGUMENTS`:

- Empty / `help` → print usage card below.
- `chat` → summarize current chat (1 paragraph + 5 bullets covering problem/scope/constraints/what's-tried/success-criteria) into `/tmp/_swarmwithprework_input.md`, then run with `--task-file`.
- `--from <ts>` → resume from prior run, build on its `SUMMARY.md`.
- Otherwise → treat `$ARGUMENTS` as the inline task description.

Use `TodoWrite` to track:
1. Capture/write INPUT
2. Phase 0 (pre-work)
3. Phase 1 (brainstorm fan-out + Ruflo parallel)
4. Phase 2 (synthesis)
5. Phase 3 (QA critics)
6. SUMMARY + swarm_inspect sanity

Then invoke the orchestrator (single command — runs all 4 phases sequentially, writing artifacts after each):

```
python tools/swarm/swarmwithprework.py --task "<task>"
# or
python tools/swarm/swarmwithprework.py --task-file /tmp/_swarmwithprework_input.md
# or
python tools/swarm/swarmwithprework.py --from 20260507T230000Z
```

Pass through optional flags from `$ARGUMENTS`:
- `--skip-ruflo` → skip Ruflo parallel brainstorm in Phase 1 (saves ~2min)
- `--phase1-engines a,b,c` → override default 5-engine roster
- `--phase0-engine x` / `--phase2-engine x` / `--phase3-engines a,b,c` → override per-phase engines

## After it finishes

1. Print the final `SUMMARY.md` path + first 80 lines.
2. Run `python tools/swarm/swarm_inspect.py swarm_runs/swarmwithprework_<TS>/phase1` and same for `phase3` so user sees response-size + suspect flags.
3. If any phase had <3 returning engines, surface a warning + recommend `/swarm engines` to check API key auth.
4. Suggest follow-ups:
   - Iterate on this run: `/swarmwithprework --from <TS>`
   - Cross-engine compare answer: `/swarm second-opinion`
   - Resume a specific engine: `/swarm resume <engine> <session-id> <prompt>`

## Building on prior runs

`--from <prior_ts>` rolls the prior run's `SUMMARY.md` into the new `INPUT.md` as a "Prior Run" appendix. Phase 0 then re-scopes against current state of repo, Phase 1 brainstorms incremental moves, Phase 2 produces a delta plan, Phase 3 critics check regression risk vs prior.

## Templates leveraged

- `tools/swarm/swarm_run.py` — per-phase fan-out
- `tools/swarm/swarm_inspect.py` — post-phase sanity
- `tools/swarm/examples/multi_model_qa.yaml` — pattern reference for engine sampling
- `.ruflo/orchestrator.py --swarm brainstorm_review --tier hybrid` — Ruflo's own 6-model brainstorm/review chain runs in parallel during Phase 1 and its compiled output is folded into the synthesis input

## Guardrails

- Each phase prompt capped at ~8KB so cerebras (~22KB context) doesn't truncate the merge.
- Engines listed in Phase 3 must NOT overlap with the Phase 2 synthesizer (keeps critic independent).
- All artifacts written to disk after each phase — partial runs survive for `--from` resume.
- If <3 engines return in Phase 1, halt with "insufficient family coverage — check `/swarm engines` auth".

## Usage card

```
/swarmwithprework — 4-phase pre-worked swarm review
  Phase 0: 1 engine pre-scopes data + blind spots
  Phase 1: 5 engines (Tools/Swarm) + ~4 free (Ruflo) brainstorm in parallel
  Phase 2: 1 strong synthesizer dedupes + priorities
  Phase 3: 2-3 cross-family critics check QA + future monitoring

USAGE
  /swarmwithprework "<task description>"
  /swarmwithprework chat                    use current chat as INPUT.md
  /swarmwithprework --from <prior_ts>       build on prior run
  /swarmwithprework "<task>" --skip-ruflo   skip Ruflo (faster, less coverage)

OUTPUTS (under swarm_runs/swarmwithprework_<TS>/)
  INPUT.md                 task + repo context
  PHASE0_PREWORK.md        pre-scope (cerebras)
  phase1/<engine>.{json,raw.txt}   per-engine brainstorm
  PHASE1_ALL_BRAINSTORM.md combined Phase 1 + Ruflo for synthesis input
  PHASE2_ACTION_PLAN.md    synthesized plan (deepseek)
  phase3/<engine>.{json,raw.txt}   critic reviews
  SUMMARY.md               final consolidated doc

SEE ALSO
  /swarm engines        auth status check before running
  /swarm-ruflo keys     ruflo paid-key status
  /swarm inspect        post-run response-size + suspect flags
```
