# Branch vs main divergence audit — findings (2026-11-16)

Method: read-only local git plumbing + `git ls-remote` (no REST rate-limit consumed).

## Population
| Metric | Value |
|---|---|
| Live remote branches | **214** |
| Stale >30 days (tracking refs) | **159 / 245 (65%)** |
| `claude/*` throwaways (June-era `claude/fervent-knuth-*`) | **96 (45%)** |
| Active (updated since 2026-10-18) | ≤86 |

## Duplicate-CI cost: NONE
- Every branch-only workflow file is **`schedule`/`workflow_dispatch`/`pull_request`-only** or `.disabled`/`.retired`.
- Schedules fire **only from the default branch**, so ~370 branch copies cost **zero runtime**.
- The only branch-unique push workflow (`mermaid-test-deploy.yml` on `bestiejobs-v3`) is scoped to
  `branches: [wiring]` and **cannot fire** on that branch.
- Branch workflow trees are simply **fork-lag** (missing main's newer files, retaining deleted ones) —
  not a second running copy. **No need to fix branch copies; landing fixes on main is sufficient.**

## One real, narrow risk: stale `branch-large-file-dup-guard.yml`
Main's guard is fixed (global group, `cancel-in-progress: false`, `timeout-minutes: 15`). But the guard is
`on: push: branches-ignore: [main]` and **runs the pushed branch's copy**. These *recently-active*
branches still carry pathological pre-2026-11-15 variants (no timeout / cancel-in-progress / no
concurrency) — the exact configs documented to cause hours-long pileups and "0 of last 15 completed":

| Branch | Guard variant |
|---|---|
| `hermes/forex-session-window-fix` | per-ref group, cancel=true, no timeout |
| `wired-in/buffy-gh-actions-fix-2026-11-15` | global, cancel=true, no timeout |
| `wired-in/buffy-2026-11-15` | global, cancel=true, no timeout |
| `feat/finpredict-final-v001` | global, cancel=true, timeout kept |
| `audit/live-audit-2026-11-14` | **no concurrency, no timeout** (worst) |
| `claude/fervent-knuth-09ksmm` | no concurrency, no timeout |
| `bestiejobs-v3`, `videos-pipeline` | global, cancel=true, no timeout |

Cost is zero **until** a push hits one of these branches; then the bad copy re-runs instead of main's fix.

## Recommendation (safe)
- **Do nothing destructive.** Fixing branch copies needs force-push/merge-back into others' branches →
  invasive, violates "only push your own changes." Since these branches are mostly stale, risk is low.
- For the few **actively-pushed** branches, the clean remedy is a one-time **merge-back of main** (which
  carries the fixed guard), done by the branch owner — not by this session.
- Optional hygiene: dry-run stale-branch cleanup for the 96 `claude/fervent-knuth-*` throwaways
  (deletion still requires explicit owner approval — documented, not executed).
