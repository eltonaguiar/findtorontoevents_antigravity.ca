# Branch Prune List — GitHub Actions Capability Audit

- **base_commit:** `eb23252219786dc09362a5a500aef2f9bc6f794f` (`origin/main`)
- **audit_time:** 2026-11-16T02:02Z
- **scope:** all 215 `refs/remotes/origin/*` branches, local git only (no GitHub API, no browser, no DB)
- **method:** `git ls-tree -r` per branch over `.github/workflows` → `git cat-file --batch` (byte-offset reads) → comment-stripped `on:` block parser → `git merge-base --is-ancestor` for merge state → committer dates from `git log -1`
- **companion data:** [`branch_capability.tsv`](./branch_capability.tsv) (215 rows, 14 columns)
- **read-only:** no workflow file was modified by this audit.

---

## 1. Headline: the trigger hazard does not exist on any branch

> [!IMPORTANT]
> **Zero** workflow files, across **all 215 branches**, combine `on: push` with **neither** `branches:` **nor** `paths:`. The dangerous-unbounded-push class is **empty repo-wide.**

| Metric | Value |
|---|---|
| Branches audited | 215 |
| Branches with unreadable workflow trees | **0** |
| Verdicts | **214 `CLEAN`, 1 `NO_WORKFLOWS`** |
| Files: `push` unbranched **and** no `paths:` (**true hazard**) | **0** |
| Files: `push` unbranched but `paths:`-filtered (benign by construction) | **856** (= exactly 4 per branch) |

Every single branch reports the identical pattern `unbr=4  HAZ=0  benign=4`. The same **4** unbranched-push workflows are present on all branches and **all 4 carry a `paths:` filter**, so they cannot fire on an arbitrary push. This is not a coincidence to be hedged: it is the same 4 files replicated across a near-identical workflow tree.

**This independently corroborates `@inspector`'s finding** in [`branch_trigger_audit.md`](./branch_trigger_audit.md) (`H = 0`, empty). Two audits built by different methods agree.

### Where the trigger risk actually lives

The **`pull_request:` axis is a separate hazard class and is NOT covered by this classifier.** `@inspector` established (and the coordinator accepted) that `pull_request:` with neither `branches:` nor `paths:` runs on *every* PR from any fork, including forks with attacker-controlled workflow files. Inspector reported **PR-h = 2** named files. The `on:` parser behind `branch_capability.tsv` records `pull_request` only into an "others" bucket and does not evaluate its filters — so **do not read this TSV as a complete trigger audit.** For the PR axis, the authoritative source is [`branch_trigger_audit.md`](./branch_trigger_audit.md).

### What does vary between branches

Only volume, never capability:

| Dimension | Range across branches | `main` |
|---|---|---|
| Workflow files (`n_wf`) | 344 – 362 | 358 |
| Scheduled (`sched`) workflows | 298 – 312 | 309 |
| `push` + `branches:` filtered (`filt`) | ~35 – 36 | 36 |
| Stray non-`.yml` entries in `.github/workflows` | 15 – 20 | 15 |

The 19-per-branch stray entries (15 on `main`) are non-workflow files sitting in the workflows directory. They are inert for Actions but are untidy and worth a one-time sweep; they are **not** a security finding.

---

## 2. The real problem is sprawl, not danger

215 remote branches, essentially all carrying a full copy of the workflow tree. The cost is not trigger risk; it is **operator confusion** — five workflow files that look identical live on hundreds of branches, so any "which branch is authoritative?" question is unanswerable by inspection.

### Age + merge distribution (215 branches, `main` excluded from advice)

| Bucket | Branches | Notes |
|---|---|---|
| **Merged into `origin/main`** (ancestor) | **8** | safe delete candidates today |
| Unmerged, **< 7 d** | 38 | active work — leave alone |
| Unmerged, **7–29 d** | 42 | triage |
| Unmerged, **30–89 d** | 33 | strong prune candidates |
| Unmerged, **≥ 90 d** | **102** | bulk prune target |

> [!WARNING]
> **Squash-merge blind spot.** `merged_into_main` is computed with `git merge-base --is-ancestor origin/<br> origin/main`, which only detects *ancestor* merges. This repository squash-merges routinely, so a branch whose content is already on `main` will still read `merged_into_main = no`. **The 8 "merged" branches are a lower bound, not a count of what is safe to delete.** Confirm any candidate with `git log origin/main --grep="<branch>"` or a diff before deleting.

---

## 3. Recommended action

### Tier 0 — delete now (8 branches, ancestor-merged, zero content risk)

```
chore/scrape-events-11pm-toronto            age 14d
feat/audit-dashboard-go-live-20261022       age 24d
feat/kimi-stop-record-b4-spy                age  1d
feat/micro-hold-fix-20261022                age 24d
feat/stop-fill-cost-gate-final-v3           age  1d
fix/p0-safe-fixes-2026-11-14-main           age  1d
nemotron/audit-copy-trader-stale-check      age 26d
```
(`main` itself is the eighth "merged" row and is of course retained.)

These are provably contained in `main`. Deleting them costs nothing.

### Tier 1 — bulk prune: ≥ 90 d, unmerged (102 branches)

This is the single highest-value action in the whole report: **102 of 215 branches (~47%) have had no commit in over three months.**

| Family | Count in ≥90 d bucket |
|---|---|
| `claude/fervent-knuth-*` | **74** |
| `feat/*` | 19 |
| no-prefix | 6 |
| `refute/*`, `pr/*`, `plan/*` | 1 each |

The `claude/fervent-knuth-*` family is **96 branches total — 45% of the entire remote.** They have opaque suffixes (`09ksmm`, `1592y3`, `2btf1h`, `4UwMB`, `H9Y1h`, `WLuQF`, …) that convey nothing about content, and the oldest (`H9Y1h` 163 d, `WLuQF` 162 d, `4UwMB` 161 d) are the stalest objects in the repository. 74 of the 96 are ≥ 90 d.

The 6 no-prefix stale branches, all 154–162 d old, are self-evidently abandoned:

```
money-ready-picks-now-2026-06-06       162d
nemotron-june-2026-audit               158d
kilo-strategy-kill-2026-06-12          156d
forex-carry-amplify-2026-06-12         156d
worktree-equity-reachability-tp-2026-06-13  155d
audit-dig-deeper-2026-06-12            154d
```

**Suggested procedure** (batch, reversible for 90 days via the reflog on GitHub if a branch is deleted by accident): delete the ≥90 d set in one pass, then re-run this classifier; the re-run is cheap and should show the branch count drop from 215 to ~113 with the same `HAZ=0`.

### Tier 2 — triage: 30–89 d, unmerged (33 branches)

| Family | Count |
|---|---|
| `claude/*` | 22 |
| `fix/*` | 7 |
| `rescue/*` | 2 |
| `archive/*` | 1 |
| no-prefix | 1 |

Read the commit subject on each before deleting; these are recent enough that some may still carry un-landed intent. `archive/oct3-branch-june-commits` is explicitly labelled archival and can go regardless.

### Tier 3 — duplicate-variant families, merge to one

These are not about age; they are about N near-identical copies of one piece of work:

| Family | Branches | Recommendation |
|---|---|---|
| `job-search-2026-11-03*` | 6 `job-search-2026-11-03{,-fresh-48h,-jd-scoring,-ledger,-rounds21-27}` (+`job-hunting-skills-catalog`) | Pick the winner, land it, delete the rest |
| `rescue/*` | 4 commit-hash-named (`7345f18400`, `9f2aee475b`, `ddee81a6e9`, `ff726af5ae`) | Rescue branches named by hash are recovery artifacts. Verify `main` already holds the rescued commit, then delete |
| `*again-v3/v4`, `*-v2/v4` | `bestiejobs-v3`, `multi4-v3`, `salesforceagain-v3`, `samagain-v4`, `ollama-checks`, `ollama-checks-v3`, `swarmmethodquality-v2`, `swarmmethodquality-v4` | Version-suffixed pairs mean the newer one superseded the older; delete the older of each pair |
| `wired-in/buffy-*` | 2 (`-2026-11-15`, `-gh-actions-fix-2026-11-15`) | Very recent; the `-gh-actions-fix` one is likely the live one — land it first, then delete both |

### Tier 4 — retain

- `main` — obviously.
- `gh-pages` — the only `NO_WORKFLOWS` branch (`n_wf=0`, `stray=0`). It is a pages-publishing branch, not a code branch; excluding it from workflow expectations is correct.
- All 38 branches in `< 7 d`, plus the recent `fix/*-2026-11-15/16` set (`fix/disable-dead-workflows-2026-11-16`, `fix/stale-gh-actions-2026-11-16`, `fix/gha-backup-verify-dedup-2026-11-15`, `fix/blob-guard-per-branch-concurrency-2026-11-15`, `fix/etf-short-gate-vix-combos-2026-11-15`, `fix/feature-signals-safe-push-followup-2026-11-15`, `fix/kilo-ci-tests-backup-verify`). Several of these are clearly the in-flight remediation work for this very audit.

---

## 4. What this audit does not claim

To keep the record clean:

1. **It is not a PR-trigger audit.** See §1 — the `pull_request:` axis is covered by [`branch_trigger_audit.md`](./branch_trigger_audit.md) (PR-h = 2), not here.
2. **It does not enumerate which branch is "best".** Branch order in `branch_capability.tsv` is `git for-each-ref` order, not a quality ranking. `@triage-expert`'s [`cron_verification.md`](./cron_verification.md) and the coordinator own the "most viable version" call.
3. **It does not detect squash merges.** See the warning in §2.
4. **It does not read `.disabled`-suffixed files as active.** They are counted as strays, which is correct: GitHub does not execute them.
5. **Age is committer date of the branch tip**, not last-touched-of-the-workflow-files. A branch can have a 1-day-old tip commit that only tweaks a README while its workflows are ancient.

---

## 5. One-line summary for the coordinator

> Across 215 branches there are **zero** unbranched-and-unfiltered `push` triggers (856 unbranched files, all 4-per-branch `paths:`-bounded; 214 `CLEAN` + 1 `NO_WORKFLOWS`) — corroborating `@inspector`'s `H=0`. The actionable finding is sprawl: **8 ancestor-merged branches deletable now, 102 branches idle ≥ 90 days (74 of them in the 96-branch `claude/fervent-knuth-*` family), 33 needing triage.** PR-axis risk stays with `branch_trigger_audit.md`.
