# Full GitHub Actions sweep — all 337 workflow files

**Date:** 2026-11-26 00:45Z
**Scope:** every workflow file in `.github/workflows/`, the last 500 runs
(147 workflows, a 1.8-hour window — this repo runs 500 jobs in under two hours),
plus static analysis of all 337 files.

## Static analysis of all 337 workflow files

| check | result |
|---|---|
| YAML parse failures | **0** |
| deprecated action majors (`actions/*@v1..v3`) | **0** |
| `::set-output` / `::save-state` (removed in 2023) | **0** |
| workflows with no top-level `permissions:` | 96 (hygiene, not failure) |
| `continue-on-error: true` | 59 (36 baselined, 0 new silent maskers) |

`scripts/lint_workflow_masking.py --fail-on-new` exits 0 on `main`.

## Run history

500 runs: **456 success, 16 cancelled, 4 failure, 1 skipped, 23 in flight.**
Every workflow's *latest* run is green.

### The 4 failures — all already resolved or not on main

| run | workflow | cause | status |
|---|---|---|---|
| 45719481029 | Hub Data Sync | asserted `hub/data/systems_manifest.json` `generated_at` < 7d, but that field is **hand-curated** (2026-03-02) and nothing writes it — the gate was red from the day it landed | **fixed on main**; re-gated on `winning_combos.json` freshness + manifest shape. Green at 23:58 and 00:33. |
| 45727698681 | Forward-Test New Strategies | `Enforce strategy-generation freeze (P0 gate)` | green 2 min later (00:19); gate is conditional, not broken |
| 45725163709 | masking-policy-lint | 1 NEW silent masker `gha-failure-digest.yml` | **not on main** — it exists only on peer PR branch `ci/2026-11-25-gha-digest`. Main's lint is clean. |
| 45718551092 | CI Tests | gating tests failed on 3.11 + 3.12 | PR branch `ci/land-orphan-tool-workflows`; `main`'s CI is green (5/5 most recent) |

### 16 cancellations

PR-branch `concurrency` groups and duplicate schedules
(`realtime-challenge` ×3, `No stale DB passwords` ×3, `[torontoneto.net] Deploy Rise of the Claw` ×3).
Not failures.

## Dead workflows — none

232 active workflows had no run in the window, which is expected: 500 runs only
covers ~1.8 hours. Re-checked by parsing each `cron:` and asking which schedules
had to fire inside the window. 4 candidates, all explained:

- `battle_test.yml` — `disabled_manually` (since 2026-06-13)
- `sports-data-snapshots.yml` — `disabled_manually` (since 2026-11-16)
- `sports-smoke-and-e2e.yml` — `disabled_manually` (since 2026-11-15)
- `dynamic-alpha-engine.yml` — active, ran at 00:44 (just outside the slice)

**8 workflows are `disabled_manually`.** Those are intentional, but the sports
ones mean sports data snapshots and the sports smoke test have been off since
mid-November — worth a deliberate decision rather than drift.

## Green-but-erroring found in logs

`forward_trade_executor_v2.py` logged ~42 delisted-symbol errors per hourly run
while reporting success; 13 non-crypto instruments never got a price or ATR.
Fixed — see `updates/2026-11-26-forward-trade-executor-symbol-mapping-fix.md`.
