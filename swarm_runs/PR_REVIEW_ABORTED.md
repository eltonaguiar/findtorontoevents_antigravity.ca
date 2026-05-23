# PR Review Run Aborted — 2026-05-03T17:04Z

**Run dir:** `swarm_runs/pr_review_20260503T170445Z/`
**Briefing:** `swarm_runs/_pr_review_brief.md`
**Engines invoked:** claude, deepseek, xai (max-parallel=3)
**PRs targeted:** 724, 723, 676, 661, 660, 644, 615, 608, 597 (9 open PRs)
**Cost spent vs cap:** ~$0.039 of $1.00 (deepseek 4 jobs, xai 3 jobs, claude 3 jobs)
**Decision:** **ABORTED** — wholesale fabrication detected on all engines; do not consolidate.

## Suspect-flag breakdown (per `tools/swarm/swarm_inspect.py`)

```
run_kind=fanout  engines=10  healthy=7  suspect=3
```

`swarm_inspect` flags:
- 3 × Claude — `TINY,PARSE_FAILED` (raw bytes 32-59 each; output is "Ready. Awaiting PR review task." — the prompt never reached the agent loop)
- 7 × DeepSeek/XAI — flagged HEALTHY by automated checks (valid JSON envelopes)

Automated rate: **30%** (below 50% abort threshold).

## Why automated check missed the real problem

The HEALTHY-flagged DeepSeek + XAI envelopes are **schema-valid but content-fabricated**. The pr_review.md prompt instructs each worker to run `gh pr view <N>` and `gh pr diff <N>`, but API-only engines (DeepSeek, XAI) cannot execute shell commands — they only receive prompt text. They confabulated reviews from the PR title or pure invention.

### Manual content audit — 3/3 PRs sampled, 100% fabrication on API engines

| PR | Real title (from `gh pr view`) | DeepSeek summary | XAI summary |
|---:|---|---|---|
| 724 | investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies. **Files:** `reports/deep_dive_FOREX_2026_05_03.md`, `reports/forex_corrupt_filter_analysis_2026_05_03.md`, etc. (6 markdown files) | "PR adds Event Details page with React EventCard component, useEvents hook…" — **fabrication** | "PR introduces UI dropdown for event filtering…" — **fabrication** |
| 723 | feat(B18): shadow-mode auto-promotion for zero-closed-history strategies. **Files:** `audit_trail/dashboard_generator.py`, `audit_trail/quality_gates.py`, `tests/test_shadow_promotion.py`, etc. | "Adds Events Near Me geolocation feature with API endpoint, frontend, DB migration…" — **fabrication** | "UI improvements for event listing + bug fix in event filtering…" — **fabrication** |
| 676 | data(events): quality follow-up — remove duplicates + SVG placeholders. **Files:** `EVENT_DATA_QUALITY_REPORT.md`, `events.json`, `next/events.json` | "Adds Events carousel to homepage with new CSS file, navigation update…" — **fabrication** | "UI for event filtering improvement…" — **fabrication** |

Every reviewed PR cited file paths and components that **do not exist in the diff**. Both API engines wrote `"engine": "claude-sonnet"` in their JSON envelopes (copied from the prompt template's example) instead of self-identifying — another tell that they didn't run any verification commands.

### Effective fabrication rate

- Claude (CLI agent): 3/3 produced no review at all (TINY)
- DeepSeek (API): 4/4 produced fabricated reviews
- XAI (API): 3/3 produced fabricated reviews

**10/10 = 100% suspect**, well past the 50% spec threshold.

## Root cause

`tools/swarm/prompts/pr_review.md` issues shell instructions like `gh pr view <N>` to all engines, but only CLI-style agents with bash tool access (Claude Code, Gemini, Kilo, OpenCode, Copilot) can execute them. API-only engines (DeepSeek, XAI, Cerebras, Inception, Ollama Cloud) are pure text→text — they will hallucinate `gh` output. There is no diff context in the prompt itself.

Two symptoms in this run:

1. **API engines:** prompt is "go run gh pr diff …" but they have no tools, so they fabricate. (DeepSeek + XAI in this run.)
2. **CLI engine:** something in the worker_runner harness for `claude` is delivering only the system header without the per-PR prompt, leaving the agent at "Ready. Awaiting PR review task." (3/3 zero-content responses.)

## What's needed before re-running

Two prerequisites for a non-fabricated PR review pass:

1. **For API engines:** modify the dispatch flow to fetch `gh pr view` + `gh pr diff` output **server-side** (in the dispatch script) and embed the captured diff into the per-PR prompt as static context. The engines should never be asked to run shell commands they can't run. This is a `swarm_dispatch.ps1` / `worker_runner.py` enhancement, not a prompt tweak.
2. **For Claude CLI engine:** investigate why the per-PR prompt isn't propagating — the worker started but never received the review task. Likely a session-priming bug or argument-passing issue in `worker_runner.py`'s claude transport.

Until both are fixed, **do not** dispatch PR reviews via this swarm. Action plan generation is paused.

## Cost

| Engine | Jobs | tokens_in | tokens_out | Cost USD |
|---|---:|---:|---:|---:|
| deepseek | 4 | 2,480 | 4,963 | $0.00174 |
| xai | 3 | 1,722 | 1,883 | $0.03685 |
| claude | 3 | 0 | 0 | $0 (CLI bundled) |
| **TOTAL** | 10 | 4,202 | 6,846 | **$0.03859** |

Well under the $1.00 cap. No further spend.

## Files preserved for forensics

- `swarm_runs/pr_review_20260503T170445Z/pr_*.{deepseek,xai,claude}.json` — raw envelopes (10 jobs)
- `swarm_runs/_pr_dispatch_20260503T170445Z.log` — dispatcher log
- `swarm_runs/_pr_review_brief.md` — original briefing
- This file: `swarm_runs/PR_REVIEW_ABORTED.md`

## What to do instead (manual fallback)

A human reviewer (or a single Claude-Code instance with bash tools running interactively, NOT through swarm_dispatch) should triage these 9 PRs by hand. The asset_class_health baseline is in `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` and the goal-1 ranking heuristic in `swarm_runs/_pr_review_brief.md` is still valid — only the dispatch path is broken.

Highest-priority candidates to triage first based on title alone (NOT engine-validated, NOT a merge recommendation):

- **PR #724** — investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies — directly targets the only sub-floor class (FOREX PF 0.27)
- **PR #660** — P0 Emergency Gate Fixes — `elite_score` replacement / WINNER_FILTER abolition — touches gate logic that affects all classes
- **PR #597** — P0 fixes + USDCHF investigation — pair-block + revalidator targeting FOREX concentration risk

These three should be triaged manually before any of the others; the rest (B18 shadow promotion, infra v2.0, scanner blockers, B26 smoke, docs, events quality) are infra/cleanup with lower direct goal-1 lift.

## Append-only log

Per task spec, also appending Run #5 entry to `swarm_runs/SESSION_SUMMARY.md`.
