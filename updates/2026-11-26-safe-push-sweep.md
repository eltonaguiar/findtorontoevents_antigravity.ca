# Sweep: every hand-rolled git push loop now goes through safe_push.sh

**Date:** 2026-11-26
**Follows:** `updates/2026-11-25-gha-cancellation-root-cause-and-failure-digest.md`

## Why

Two workflows (`portfolio-tracker`, `realtime-challenge`) were being killed at their own
`timeout-minutes` because an inline `git push || { git pull --rebase --autostash; sleep 5; }`
loop hung for ~9.5 minutes after a rejected push. The commit was created and never pushed, and
GitHub reports a timeout-killed job as `conclusion: cancelled`, so nothing flagged it.

`.github/scripts/safe_push.sh` already existed for exactly this reason — its header documents the
2026-05-06 cancellation incident — and 209 workflows already call it. This sweep removes the
remaining hand-rolled copies.

## What changed

`bash .github/scripts/safe_push.sh` (90s cap per git call, 8 retries with jittered backoff,
shallow-repo deepen, `-X theirs` on data-file rebase conflicts, token preflight) replaced the
inline loop in **21 workflows**:

`ai-tournament-price-tracker`, `alpha-engine-etf`, `alpha-equity-breakout`, `audit3-evidence`,
`audit3-ledger`, `auto-retire-daily`, `crypto-intraday-sim`, `daily-top-picks-filter`,
`dxy-state-update`, `edge-stability-refresh`, `forward-observations-ingest`, `gate-config-emit`,
`h103-forward-logger`, `macd-rsi-m048-shadow-daily`, `paper-pilot-daily`,
`peer-claim-verification`, `pick-funnel-nightly`, `quant-auditor-deep-nightly`,
`research-orchestrator`, `sleeve-daily`, `strategy-perf-by-class-rebuild`.

Plus three files that had unbounded `git pull --rebase` / `git push` with no loop at all —
`kalshi-snapshot`, `gha-health-audit`, `hyro-bridge-regen` — and `signal-recorder`, which already
called `safe_push.sh` but preceded it with an unbounded `git pull --rebase origin main || true`
(safe_push does its own bounded pull, so that line was pure hang risk).

### Failure semantics were preserved deliberately

Each site keeps its original behaviour on total push failure, so this cannot turn a silent
housekeeping job into a red build (or vice versa):

| mode | sites | behaviour on failure |
|---|---|---|
| fatal | `audit3-evidence`, `audit3-ledger`, `crypto-intraday-sim`, `forward-observations-ingest`, `peer-claim-verification`, `sleeve-daily`, `kalshi-snapshot`, `gha-health-audit` | step fails (was `::error` + `exit 1`) |
| `warn` | `ai-tournament-price-tracker`, `daily-top-picks-filter`, `dxy-state-update`, `h103-forward-logger`, `macd-rsi-m048-shadow-daily`, `pick-funnel-nightly`, `research-orchestrator`, `strategy-perf-by-class-rebuild` | step succeeds with `::warning` (was: failure swallowed) |
| flag (`pushed` / `_pushed` / `push_ok`) | `edge-stability-refresh`, `gate-config-emit`, `auto-retire-daily`, `paper-pilot-daily`, `quant-auditor-deep-nightly`, `alpha-engine-etf`, `alpha-equity-breakout` | sets the same variable the surrounding code already tests |

## Deliberately NOT changed

| workflow | why |
|---|---|
| `deploy-bestiejob-page` | pushes `HEAD:gh-pages`; safe_push.sh pushes `HEAD:main` |
| `growth-stock-screener-daily` | pushes `HEAD:${GITHUB_REF_NAME}`, not main |
| `fix-battleground` | pushes `HEAD:gh-pages --force` |
| `qa-market-validation` | already bounded (`timeout 120 git push`), and its comment records why rebase is *forbidden* here: a depth-1 checkout unshallows multi-GB history and sat 26 min until the run was cancelled. safe_push's rebase path is the wrong tool. |
| `picks-now-refresh` | builds the commit with plumbing on an isolated temp index (`commit-tree` + `push $commit:refs/heads/main`) so the worktree is never touched; safe_push pushes `HEAD` and cannot reproduce that. Its push is already wrapped in 5 attempts and `continue-on-error`. |

## Verification

- `yaml.safe_load` parses all 25 changed files (each has `jobs`).
- `actionlint -shellcheck=shellcheck` findings across the whole workflow directory:
  **328 before → 321 after** — no new findings, seven fewer because the deleted loops carried
  unquoted variables.
- `actionlint -shellcheck=` (native checks) reports only the pre-existing `concurrency: queue: max`
  syntax notices, none in touched lines.
- Residual grep for unbounded `git pull --rebase` in the touched files returns only a comment.

## Rollout risk

The first scheduled run of each workflow is the real test. Two signals to watch on the next
digest run (`gha-failure-digest.yml`, issue `[CI] GitHub Actions failure digest`):

1. No workflow should newly appear as `cancelled` at exactly its `timeout-minutes`.
2. Push-failure steps should now fail (or warn) *fast* — safe_push.sh's 90s cap — rather than
   sitting silently for 9+ minutes.
