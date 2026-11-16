# GH Actions on non-main branches — runs, duplicates, redundancy, feeds

**Date:** 2026-11-16 04:05Z · **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Data window:** 1,200 runs, 2026-11-15T20:36:09Z → 2026-11-16T03:47:32Z (7h11m)
**Method:** read-only. `tools/gha_nonmain_audit.py` (12 pages of runs), `GET /compare/main...<branch>`
for all 213 branches, `git cat-file` against each branch tip, trigger blocks re-read **from
`origin/main`** (not from a working branch). Raw: `reports/gha_nonmain_audit.json` / `.md`.
Companion: `NONMAINBRANCHES.md`.

> **Relationship to earlier reports.** `GHACTIONS_2026-11-16/2026-11-15_22-47_EST_nonmain/NONMAIN_GH_ACTIONS_DIAGNOSIS.md`
> and `.../2026-11-16_03-00Z_branch-audit/BRANCH_AUDIT.md` covered the same ground over a 1,000-run
> window. This report re-measures with fresh data and **corrects one important reading**: the
> cancelled non-main runs are not a broken workflow on `main` — `main` is already fixed — they are
> **fork-lag**: stale branches executing their own old copy of the workflow.

---

## TL;DR

1. **54 of 1,200 runs (4.5%) are non-main.** 33 PR checks, 14 push, 7 Pages. Non-main CI is not the
   queue problem.
2. **Zero duplicate runs.** No workflow ran twice on the same commit in the window.
3. **20% of non-main runs are cancelled (11/54), and 8 of those are one workflow** —
   `branch-large-file-dup-guard` — firing from **stale branch copies** that still have
   `on: push: branches-ignore: [main]`. On `main` it is already a **weekly schedule** (fixed
   2026-11-16, comment cites 0/30 completions). No further workflow edit is needed; the branch copies
   are the problem.
4. **Three retired workflows still execute**, because `.disabled` on `main` does not deregister them:
   `secret-scan.yml`, `mysql-q001-sync.yml`, `ml-gatekeeper-ab-bootstrap.yml`. Four runs in 7 hours,
   **two failures**. 212 of 213 branches still carry all three files. This is the one thing worth
   fixing *today*, and it needs no branch deletion.
5. **Nothing on a non-main branch writes to `main`.** Zero workflows combine an any-branch push
   trigger with a main write. The only external feeds are GitHub Pages, two artifact producers, and
   one manifest regenerator that pushes to the branch it ran on.

---

## 1. Volume

| Metric | Value |
|---|---|
| Runs scanned | 1,200 |
| Non-main runs | **54 (4.5%)** |
| Events | `pull_request` 33, `push` 14, `dynamic` 7 |
| Conclusions | success 40, **cancelled 11**, failure 2, in progress 1 |
| Distinct workflows | 11 |
| Branches producing runs | 9 |
| Duplicate groups (workflow + SHA) | **0** |

### Per workflow (window)

| Workflow | Runs | Result | Caused by |
|---|---|---|---|
| `branch-large-file-dup-guard.yml` | 9 | 8 cancelled, 1 running | **branch copy** still `push: branches-ignore: [main]` |
| `no-stale-db-passwords.yml` | 8 | 7 success, 1 cancelled | `pull_request` + push `main` (`**/*.py`) |
| `db-password-leak-guard.yml` | 8 | 8 success | PR to `main`, path-filtered |
| `conflict-marker-check.yml` | 8 | 7 success, 1 cancelled | PR + push to `main`/`copilot/**`/`codebuff/**` |
| `masking-policy-lint.yml` | 7 | 7 success | PR, path-filtered to workflows |
| `pages-build-deployment` | 7 | 7 success | built-in Pages build from `gh-pages` |
| `secret-scan.yml` | 2 | 2 success | **orphan registration** (file `.disabled` on main) |
| `audit-drift-telemetry.yml` | 2 | 2 success | push, path-filtered |
| `mysql-q001-sync.yml` | 1 | **failure** | **orphan registration** |
| `ml-gatekeeper-ab-bootstrap.yml` | 1 | **failure** | **orphan registration** |
| `audit-frontend-manifest.yml` | 1 | cancelled | push, path-filtered (not branch-filtered) |

---

## 2. Duplicates: zero, but two lookalikes

`(workflow path, head_sha)` grouping over all 54 runs produced **0 groups with more than one run**.
There is no same-commit re-run churn.

Two things resemble duplication and are not:

- **Superseded runs** — 3 of the 11 cancellations are `cancel-in-progress: true` working correctly on
  a branch that received a newer push (`no-stale-db-passwords`, `conflict-marker-check`,
  `audit-frontend-manifest`).
- **Duplicate *definitions*** — the same three retired workflows executing from 212 branches that
  still carry the file. One commit, one run each — but a workflow that should not exist at all.

---

## 3. The cancellation story is fork-lag, not a main-side bug

`main`'s copy of `branch-large-file-dup-guard.yml` reads:

```yaml
on:
  # 2026-11-16: the push trigger was removed. ... 0 of its last 30 runs completed ...
  schedule:
    - cron: '0 6 * * 0'   # Sundays 06:00 UTC
  workflow_dispatch:
```

A `schedule:` cannot fire from a feature branch (GitHub only runs schedules on the default branch).
So if `main` were the only definition, this workflow could never produce a non-main run. Yet it
produced 9 — because **a push runs the workflow files of the branch being pushed**, and those
branches were cut before the fix. Their copies still contain the old trigger, the old concurrency
settings, and in several cases no `timeout-minutes`.

That is the whole mechanism. It also explains the earlier finding that every attempt to fix this
workflow "did not help" — the fix landed on `main`, and the failing runs were executing other refs'
copies.

**Consequence for remediation:** editing the workflow again on `main` changes nothing. The options
are (a) delete/refresh the stale branches, or (b) merge `main` into the handful of branches that are
still actively pushed. `BRANCH_AUDIT.md` names the eight:

```
hermes/forex-session-window-fix          wired-in/buffy-gh-actions-fix-2026-11-15
wired-in/buffy-2026-11-15                feat/finpredict-final-v001
audit/live-audit-2026-11-14              claude/fervent-knuth-09ksmm
bestiejobs-v3                            videos-pipeline
```

Both are owner actions — merging into another agent's branch is not something this session should
do unilaterally.

---

## 4. `.disabled` does not disable — three registrations still live (P0)

On `main` these exist only as `*.yml.disabled` (9 `.disabled` files total). Yet in the 7-hour window:

| Workflow | Runs | Result |
|---|---|---|
| `secret-scan.yml` (M-043) | 2 | success |
| `mysql-q001-sync.yml` | 1 | **failure** |
| `ml-gatekeeper-ab-bootstrap.yml` | 1 | **failure** |

Mechanism: GitHub keeps the workflow **registration** and runs the definition found on the pushed
branch. **212 of 213 branches** still contain all three `.yml` files (**636 branch-tip references**).
Renaming on `main` only silences `main`.

This is the only finding in this report that is currently producing failing red runs, and it has a
reversible, non-destructive fix that the earlier reports did not propose — disable the
**registration**, not the file:

```bash
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows --paginate \
  --jq '.workflows[] | select(.path|test("secret-scan|mysql-q001-sync|ml-gatekeeper-ab-bootstrap"))
        | "\(.id)\t\(.path)\t\(.state)"'

# per returned id (state should currently be "active"):
gh api -X PUT repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/<ID>/disable
# reverse with /enable
```

Branch deletion would also stop them eventually, but only once no branch carries the file — the
disable is immediate and independent of the cleanup argument below.

---

## 5. Where non-main runs feed

| Workflow (main's version) | Writes | Artifacts | Feeds |
|---|---|---|---|
| `no-stale-db-passwords.yml` | `contents: read` | — | PR status check |
| `db-password-leak-guard.yml` | `contents: read` | — | PR status check |
| `conflict-marker-check.yml` | `contents: read` | — | status check |
| `masking-policy-lint.yml` | `contents: read` | — | status check |
| `audit-drift-telemetry.yml` | `contents: read` | yes | telemetry artifact |
| `audit-frontend-manifest.yml` | `contents: write` | — | regenerates `audit_dashboard/audit_frontend_manifest.json` **on the branch it ran on** (bare `git push`) |
| `branch-large-file-dup-guard.yml` (branch copies) | `contents: write` | yes | findings artifact + `updates/job-health.md` alert — when a run survives long enough |
| `pages-build-deployment` | — | — | **GitHub Pages** from `gh-pages` (`.nojekyll` present) |
| the three orphans | — | — | nothing; output is red/green in the Actions UI |

**Direct answers:**

- **Nothing on a non-main branch writes `main`.** A strict scan of all 356 workflow files found **0**
  combining an any-branch `push:` with `HEAD:main` / `push origin main` / `safe_commit_push.sh` /
  `safe_push.sh`.
- **41 of 54 runs feed the merge gate** (status checks) and nothing else. With **0 open PRs** at
  sample time, that gate is momentarily idle — the 33 PR events mean PRs are opened and closed
  quickly, not that the checks are pointless.
- **One production feed: Pages.** `gh-pages` → Pages is the only non-main path that reaches a served
  surface, and it is deliberate.
- **One near-miss:** `audit-frontend-manifest.yml` has a path filter but **no `branches:` filter**, so
  a feature-branch push touching `audit_dashboard/template.html` commits a regenerated manifest to
  that branch. It cannot reach `main` from there, but the file is main-only content and the merge
  regenerates it anyway (P4, cosmetic).

---

## 6. Proposals

| # | Action | Scope | Why | Risk |
|---|---|---|---|---|
| **P0** | Disable the 3 orphan **registrations** by workflow id | API, no file | They still run from 212 branches; 2 of 4 runs failed | none, reversible via `/enable` |
| P1 | Delete the 12 branches whose work is fully in `main` | 12 refs | Zero information loss, removes 12 fork-lag copies | none |
| P2 | Owner merge-back of `main` into the 8 actively-pushed branches | 8 refs, by owners | Kills the pathological guard copies without deleting anyone's work | needs owner consent |
| P3 | Enable *Settings → Automatically delete head branches* | repo setting | Stops the pile-up at the source | none |
| P4 | `audit-frontend-manifest`: add `branches: [main]` to `push:` | 1 file | Keeps a main-only data file main-only | none |

**Not proposed:** another edit to `branch-large-file-dup-guard.yml`. `main` is already correct, and
that is exactly why editing it again would do nothing.

## 7. Verification after applying

```bash
python3 tools/gha_nonmain_audit.py --pages 12
```

Expect: non-main runs 54 → ~41 (dup-guard 9 + orphans 4 gone), cancelled share 20% → under 4%,
duplicate groups still 0, and `secret-scan` / `q001` / `gatekeeper` absent from the per-workflow
table. `pages-build-deployment` should remain the only non-check feed until P4 lands.

## 8. Limitations

- **7h11m window.** Captures current steady state, not weekly patterns.
- `origin/main` triggers were re-read for every workflow cited; the **run history** is API truth
  regardless of which copy executed.
- "Orphan" = registration present + file absent on `main` + file present on branch tips; confirmed
  by the runs themselves.
- Per-run durations were not stored per workflow here; cancellation counts are the waste metric.
- `ahead_by == 0` from `/compare` proves no unique commits, not byte-identical trees in every edge
  case.
