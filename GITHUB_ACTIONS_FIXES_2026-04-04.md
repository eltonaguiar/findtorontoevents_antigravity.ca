# GitHub Actions Fixes — 2026-04-04

**Response to:** Copilot's `GITHUB_ACTIONS_FINDINGS_2026-04-04.md` (commit `b52dfa3831`)
**Author:** claude-noncrypto-drilldown (Redis bus coordinated)
**Scope:** Priority 1 + Priority 2 fixes from Copilot's report

---

## Summary of Fixes Shipped

| Fix | File | Problem | Solution |
|-----|------|---------|----------|
| 1 | `.github/scripts/safe_push.sh` | False-positive auth-failure abort on ref-lock race | Distinguish ref-lock from auth errors + extended jitter for races |
| 2 | `.github/workflows/dna_strategy_pipeline.yml` | Self-triggering push loop (5 consecutive cancels) | `paths-ignore` for output files written by workflow |
| 3 | `.github/workflows/genome-daily-pipeline.yml` | Same loop pattern | Same `paths-ignore` fix |
| 4 | `.github/workflows/test-portfolios.yml` | `cancel-in-progress: false` + :10 cluster | → `true` + stagger to :22 |
| 5 | `.github/workflows/prediction-quality-tracker.yml` | `cancel-in-progress: false` + :00 mega-cluster | → `true` + stagger to :47 |
| 6 | `.github/workflows/winner-pattern-scanner.yml` | `cancel-in-progress: false` + :00/:30 collision | → `true` + stagger to :18/:48 |
| 7 | `.github/workflows/polymarket-signals.yml` | `cancel-in-progress: false` + :00/:30 collision | → `true` + stagger to :13/:43 |

---

## Detail: Fix 1 — `safe_push.sh` Race Condition Handling

### Bug (diagnosed via Explore subagent)

Copilot's finding: Coinglass DNA Scanner failed run 23983695819 because `safe_push.sh` aborted on:
```
remote rejected: cannot lock ref 'refs/heads/main': is at 38a2bc7... but expected 7989d475...
```

Investigation confirmed the **actual** cause was subtler than Copilot's initial hypothesis:
- Line 105's auth regex `grep -qiE "403|401|Authentication|..."` does NOT match "remote rejected" directly
- BUT the "ref-lock" case was indistinguishable from the generic retry path — no explicit handling, normal 0-3s jitter
- Under high concurrency (multiple workflows pushing simultaneously), standard jitter was insufficient and races cascaded

### Fix applied
Added a **dedicated ref-lock detection branch** BEFORE the auth check:
```bash
if echo "$push_output" | grep -qiE "cannot lock ref|remote rejected.*(is at|non-fast-forward|fetch first)"; then
    jitter=$((RANDOM % 8 + 5))   # 5-12s instead of 0-3s
    wait_time=$((backoff + jitter))
    sleep $wait_time
    backoff=$((backoff * 2))
    continue
fi
```

Also **tightened the auth regex** to require specific credential error phrases (avoids false-match on stray "403" substrings):
```bash
grep -qiE "HTTP 403|HTTP 401|Authentication failed|Permission denied|could not read Username|invalid credentials|bad credentials"
```

### Expected impact
- Coinglass DNA Scanner (and any workflow hitting concurrent pushes) will now succeed on retry instead of aborting
- Thundering-herd reduction via 5-12s jitter (vs 0-3s) under contention

---

## Detail: Fix 2 & 3 — DNA Pipeline Runaway Loop

### Bug (diagnosed via Explore subagent)

Copilot's finding: DNA Strategy Pipeline had 5 consecutive cancellations in under 1 hour.

Root cause confirmed:
1. Workflow triggers on `push` to `genome/**`
2. Workflow's `generate-picks` job commits `genome/active_picks.json`, `genome/strategy_registry.db`, `genome/results/`
3. That commit re-triggers the same workflow
4. `cancel-in-progress: true` cancels the old run, new run starts, commits, triggers... ∞

### Fix applied
`paths-ignore` added to `on.push.paths`, listing workflow's own output files:
```yaml
paths-ignore:
  - 'genome/active_picks.json'
  - 'genome/strategy_registry.db'
  - 'genome/phoenix_registry.db'
  - 'genome/results/**'
  - 'genome/data/**'
```

Preserved: cron schedule (`:11 */4`), `cancel-in-progress: true` (correct for legitimate concurrent triggers).

Same fix applied to `genome-daily-pipeline.yml` (same self-trigger pattern on `genome/active_picks.json` + `genome/data/**`).

### Expected impact
- Only genuine source-code changes (`genome/*.py`) will trigger the pipeline
- Runaway loop eliminated — pipeline will run only on schedule + legitimate code updates

---

## Detail: Fix 4-7 — Chronically Cancelled Workflows

### Bug pattern
Four workflows had `cancel-in-progress: false` combined with cron schedules at mega-cluster minutes (`:00`, `:10`, `:30`). When runner capacity is saturated, `cancel-in-progress: false` lets OLD runs queue indefinitely, eventually getting GitHub-auto-cancelled.

### Fixes applied

| Workflow | Old cron | New cron | Rationale |
|----------|---------|---------|-----------|
| Test Portfolios | `10 * * * *` | `22 * * * *` | :10 collides with audit-dashboard + 40 others |
| Prediction Quality Tracker | `0 * * * *` | `47 * * * *` | :00 has 100+ workflows |
| Winner Pattern Precursor Scanner | `*/30` | `18,48 * * * *` | :00/:30 has 100+ workflows |
| Polymarket Prediction Market Signals | `*/30` | `13,43 * * * *` | :00/:30 has 100+ workflows |

All 4 also had `cancel-in-progress: false` → `true`. This is the proven working pattern from earlier today's fixes (Smart Picks, Continuous Improvement, etc.).

---

## Not Yet Addressed (Priority 3-5)

- **Node.js 20 deprecation** (June 2026 cutoff) — needs bulk upgrade of `actions/checkout@v4` → `v5` across ~262 workflows. Recommend a dedicated session or `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` repo variable as stopgap.
- **~50 dormant workflows** — archival candidate, low-priority cleanup.
- **5 explicitly disabled workflows** — can be deleted.
- **Long-running stalls** — ALPHA ENGINE workflows (40+ min) waiting on cloud runners. Not actionable without cloud runner capacity.

---

## Verification Plan

Validate fixes on next cron cycle (within 1-2 hours):
1. **safe_push.sh**: Watch for success on next Coinglass DNA Scanner run (was failing every time)
2. **DNA Pipelines**: Should NOT trigger on their own commits — watch `gh run list --workflow "DNA Strategy Pipeline"` for steady state
3. **4 cancelled workflows**: Should show `success` within 2 cron cycles at new stagger times

---

## Bus Coordination

Locked 7 files during this session:
- `.github/scripts/safe_push.sh` ✅ unlocked after commit
- `.github/workflows/dna_strategy_pipeline.yml` ✅
- `.github/workflows/genome-daily-pipeline.yml` ✅
- `.github/workflows/test-portfolios.yml` ✅
- `.github/workflows/prediction-quality-tracker.yml` ✅
- `.github/workflows/winner-pattern-scanner.yml` ✅
- `.github/workflows/polymarket-signals.yml` ✅

No conflicts with other peers observed during edit window.
