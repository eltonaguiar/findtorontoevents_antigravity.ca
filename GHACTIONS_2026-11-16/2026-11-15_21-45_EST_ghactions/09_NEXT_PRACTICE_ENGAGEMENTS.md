# 09 — Next-Practice Layer + Engagement Results

**STAMP:** 2026-11-15_21-45_EST_ghactions · research + engagements 05:18–05:25 UTC. Companions:
`06` (practice layer v1), `07` (/audit deep check), `08` (R7 re-diagnosis). All changes: fix + doc,
per-file reverts, `backup/gha-audit-2026-11-16` anchor.

## 1. Research: what else matters for THIS setup (grounded in official docs, 2026-11-16)

| Practice | Docs evidence | Our measured pain | Status |
|---|---|---|---|
| `run-name` | omitted ⇒ run name = **commit subject** for push/PR events | 8 "failures" tonight were `Merge branch 'main'…` titles; triage cost real time | **ENGAGED** — 19 push/data-writers |
| pip caching in `setup-python` | built-in `cache: 'pip'` + `cache-dependency-path` | "Install dependencies" = #1 infra-flake (59 fails/7d on signal_tracking alone) | **ENGAGED** — 25 steps / 10 files |
| No total-silence masks | — (hardening) | 2× `>/dev/null 2>&1 \|\| true`, 1× success-mask on `safe_commit_push` | **ENGAGED** — loud now |
| Cancel-bucketing in health tooling | `timeout-minutes` kills surface as `cancelled` (mechanics, 08 §3) | R7 misdiagnosis burned triage | **ENGAGED** — guardian classifier + 16 tests |
| `permissions:` least-privilege | unspecified ⇒ `none` for unlisted scopes; `pull_request_target` grants R/W even from forks | repo mixed (FTP-only jobs already `contents: read` = good) | Next batch (scope taken this round) |
| Deployment environments + required reviewers | environments gate prod deploys | 54 FTP writers deploy to prod ungated | **Owner decision** (policy) |
| Action SHA-pinning | tag pins float | 7 aging 3rd-party pins (watchlist in 07/§silent-scan D) | Next batch |
| `concurrency: queue: group` | newer property — ticks WAIT instead of being replaced | 06 §4 decided it for must-not-drop ticks; applied nowhere yet | Next batch |
| Timezone-aware `schedule` (new docs) | `cron` + `timezone:` per schedule entry | market-close schedules (21:35 etc.) would benefit from `America/New_York` semantics | Evaluate (changes fire times — needs owner sign-off) |

## 2. Engagement A — CI hygiene (31 files, 72+/3−) — LANDED

- **`run-name` ×19**: `${{ github.workflow }} · ${{ github.event_name }} · ${{ github.sha }}` on the
  push/data-writer family. Effect: run list titles stop being commit subjects on the next push run.
- **pip cache ×25 steps / 10 files** (`cache: 'pip'` + `cache-dependency-path: requirements.txt`):
  signal_tracking, verified-pilot-daily, edge-stability ×2, audit-dashboard, dna_strategy_pipeline,
  worldclass-pipeline, mutation-lab, mega-mutation-tracker, genome-daily-pipeline. 3 victims already
  cached (robust-edge-miner, pead-shadow-collector, academic-strategies — pre-existing good hygiene).
  Note: 2 files carry redundant legacy `actions/cache` pip blocks — harmless, consolidation candidate.
- **3 masks loud**: `alpha-engine-daily-picks:274` + `academic-strategies:69` (`|| true` → `::warning::`),
  `ml-gatekeeper-train-ab:164` (success-mask dropped; its no-op path already guarded upstream).
  `masking_manifest.yaml` checked — zero drift.
- Validation: 435 YAMLs safe-load ✓, `on:`-blocks byte-identical ✓, strict diff-line audit ✓.

## 3. Engagement B — guardian cancel-bucketing (R7 correction) — LANDED

`tools/gha_health_audit.py` R7 rewritten + R6 amended + `tests/test_gha_health_audit.py` (16 tests).

`classify_cancel_run(run, jobs, job_timeouts_s, *, siblings, newer_run, tolerance_s=30, stack_window_s=120)`:
**timeout-shaped** (jobs started, lifetime ≈ job timeout ±30s — the +5m05/+10m06/+15m04 signature) →
**eviction-shaped** (0 jobs) → **stack-kill** (same-workflow cancels within 120s of a newer run) →
**pr-close** → **external residual = the only true R7 signal** (should be near-empty; listed by run id).
R6 churn ratio now excludes timeout-shaped (a 14m50s commit-stall killed at 15m is a TIMEOUT problem,
reported with its step name via `cancel_killing_step`). Verified here: 16/16 tests, `py_compile`,
offline `--dry-run` exit 0. Sample: `timeout-shaped: 3 · eviction: 17 · stack-kill: 3 · pr-close: 2 ·
external: 1`.

## 4. Rule re-reads queued (from B's audit of 06 §2 under the corrected lens)

R1/R2 `BAD_CONCLUSIONS` excludes `cancelled` ⇒ timeout-only workflows never surface as broken ·
R3 flapping undercounts timeout problems (reuse `cancel_killing_step`) · R4 phantom-queue note
overlaps the eviction bucket (pending runs ARE group-evictable) · R5 p90 baseline polluted by
timeout-killed lifetimes · R6 + R9 cached baselines ("dup-guard 0/15", "235 stale", "tribunal 12/15")
need re-derivation at run-ID level. All documented; implementation = guardian v1.1 next round.

## 5. Verification map

| Fix | Next-run proof |
|---|---|
| run-name ×19 | next push-triggered run titles (immediate) |
| pip cache ×25 | "Install dependencies" flake rate on signal_tracking et al. (days) |
| 3 loud masks | next failing step emits `::warning::` or fails red instead of vanishing |
| guardian R7 | 08:37 scheduled run's CANCEL BUCKETS section (first live classifier output) |

Watchers: 06:22 deploy-effect re-verify · 08:00 monitor cron · 08:37 first scheduled guardian.
