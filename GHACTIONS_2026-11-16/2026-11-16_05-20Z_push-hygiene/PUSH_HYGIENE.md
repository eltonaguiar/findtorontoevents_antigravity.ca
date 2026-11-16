# GH Actions push-hygiene audit + best-practice notes (2026-11-16)

Context: 40+ workflows push `main` at overlapping cadences. The ALPHA incident (run 43799911205:
`git pull --rebase … 2>/dev/null` HUNG the full 15-min step) is not unique — it's a repo-wide pattern.

## Audit (origin/main, static scan of `.github/workflows`)
- **48 workflows run `git push`.**
- **19 use the hardened `safe_push.sh` / `safe_commit_push`** (90s `GIT_NET_TIMEOUT` per op, shallow
  deepen+merge fallback, jittered backoff, fail-fast auth) — GOOD.
- **29 use fragile INLINE git push** (`git pull --rebase … 2>/dev/null` + `git push` with no per-op
  timeout) — HANG RISK (same class as ALPHA).

### Migrated this pass (highest cadence = highest risk)
| Workflow | Cron | Change |
|---|---|---|
| `alpha-quant-stack.yml` | `5,35 * * * *` (every 30 min) | inline 5-retry loop → `bash .github/scripts/safe_push.sh` (fatal on fail, as before) |
| `ghcopilot-paper-monitor.yml` | `20 * * * *` (hourly) | inline pull-rebase loop → `bash .github/scripts/safe_push.sh` |

### Remaining backlog (27 inline-push workflows) — lower cadence, same latent hang risk
Daily/weekly unless noted: `edge-stability-refresh`, `gate-config-emit`, `beta-portfolio-refresh`,
`ab_analysis`, `poc-picks-checkpoint`, `macd-rsi-m048-shadow-daily`, `daily-top-picks-filter`,
`strategy-perf-by-class-rebuild`, `h103-forward-logger`, `alpha-engine-etf`, `hyro-bridge-regen`,
`picks-now-refresh`, `research-orchestrator`, `paper-pilot-daily`, `audit-frontend-manifest`,
`pick-funnel-nightly`, `daily-scrutiny-engine`, `sports-smoke-and-e2e`, `quant-auditor-deep-nightly`,
`ai-tournament-price-tracker`, `incidents-enhancements-nightly`, `dxy-state-update`,
`alpha-equity-breakout`, `ai-model-portfolios-daily`, `h004-backtest`, `fix-battleground`,
`pick-flow-snapshot-fast`.
Migration recipe: replace the `push_ok=false; for i in …; git pull --rebase … 2>/dev/null; git push …`
block with `bash .github/scripts/safe_push.sh` (add `|| echo "::warning::…"` if the step is meant to be
non-fatal on push failure). Preserve fatal vs non-fatal semantics per file.

## Best practices to look for (tailored to this repo)
1. **Kill hangs, not just slow runs.** A step `timeout-minutes` cannot rescue an infinite `git` hang —
   every network `git` op needs its own `timeout` (safe_push: `GIT_NET_TIMEOUT=90`). This was the ALPHA
   root cause; the 5→15m bump alone was insufficient.
2. **Single-writer / central publisher.** 48 pushers → constant `main` contention + rebase churn. Ideal:
   data workflows emit artifacts; ONE publisher job commits (fewer races, fewer force-runs). Big refactor.
3. **Per-domain `concurrency` groups with `cancel-in-progress: false`** for pushers to serialize same-DB
   writers (some already do; standardize).
4. **Jittered exponential backoff** (safe_push) — avoids re-collision after a failure.
5. **Fail-fast on auth / permanent rejection** (GH001/GH006/GH007/403) — no point retrying (safe_push).
6. **`timeout-minutes` on every job** — 79 workflows still lack it → 6h default hog risk (see APPROACH.md).
7. **Cron staggering** — peer shipped crc32 stagger of 310 crons (kills the `:00` herd).
8. **Don't `2>/dev/null` git errors** — hid the ALPHA hang for 15 min; surface them (safe_push sanitizes tokens).
9. **Shallow-clone rebase needs `--deepen`** (safe_push does `--deepen=150` with a 90s cap + merge fallback).
10. **Disable, don't delete** (`*.yml.disabled`); never `on: {}` (invalid — caused the earlier spurious failures).

## Verification
- Both migrated workflows: `python3 -c yaml.safe_load` OK; no fragile `git pull --rebase …2>/dev/null`
  in executable code; `safe_push.sh` invocations present.
- ALPHA's own migration (PR #829) outcome is being verified on the next post-merge run (scheduled check).
