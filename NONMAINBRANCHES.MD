# Non-Main Branches — GitHub Actions & Lifecycle Diagnosis
**Repo:** eltonaguiar/findtorontoevents_antigravity.ca
**Date:** 2026-11-16
**Auditor:** Antigravity coordinator (swarm synthesis of inspector + branch-differ + queue-hog-hunter reports)

## Executive Summary
- **222 remote branches** total; **221 carry ≥1 workflow file**; **220 carry cron schedules**.
- Every non-main branch holds a **near-identical superset** of main's 374 workflow files (typical branch: 377–382 `.yml`, 367–369 cron lines).
- **No workflow on any non-main branch feeds production.** GitHub only evaluates `on.schedule` from the **default branch** (`main`). The 79,938 cron lines found on non-main refs are **inert**.
- The 18 "extra" workflow names on branches are **byte-identical copies of workflows main deliberately retired** between 2026-06 and 2026-11 (secret-scan, mysql-q001, ml-gatekeeper family, 9 retired scanners). They are not unmerged work — they are stale ghosts.
- **Verdict:** These branches are **not required** for any active pipeline. They represent historical experiment/fix snapshots. They pose zero current queue pressure but are latent merge/PR landmines. **Recommendation:** delete after verifying no open PRs depend on them (1 open PR exists).

## 1. Branch Census
| Metric | Value |
|--------|-------|
| Remote heads (`git ls-remote --heads`) | 222 |
| Non-main branches | 221 |
| Branches with ≥1 workflow file | 220 |
| Branches with `cron:` trigger | 220 |
| Workflow files on `main` | 374 |
| Total `cron:` lines across non-main refs | 79,938 |
| Branches lacking any of main's 373 files | 0 |

Branch prefix spread (top): `claude/*` (96), `feat/*` (33), `fix/*` (23), `rescue/*` (4), `opencode/*` (4), remainder singletons.

## 2. What the Non-Main Workflows "Feed"
**Nothing.**  
GitHub Actions scheduled workflows are evaluated exclusively from the repository's **default branch**. Any `on.schedule` present on a non-default ref is ignored by the scheduler. The only way a non-main workflow becomes active is if:
1. The branch is merged to main (and the workflow survives review), or
2. The branch itself is promoted to default (rare, requires Settings change).

Current state: **zero risk of duplicate schedules** from these branches.

## 3. The 18 "Extra" Files — Provenance
All files present on branches but absent from `main` are resurrected copies of deliberately deleted workflows:

| File | Branches carrying | Reason main removed it |
|------|-------------------|------------------------|
| `secret-scan.yml` | 212 | Never passed (last failure 2026-06-05) |
| `mysql-q001-sync.yml` | 212 | Broken; renamed to .disabled |
| `ml-gatekeeper-ab-bootstrap.yml` | 212 | Same rename batch |
| `ml-battleground-monitor.yml.retired` | 211 | Duplicate/retired family |
| `ml-battleground-e.yml.retired` | 211 | Same |
| `ml-battleground-d.yml.retired` | 211 | Same |
| `ml-battleground-ensemble.yml.retired` | 211 | Same |
| `meme-scanner-fixed.yml` | 211 | Duplicate/retired |
| `live_trading_canada_free.yml` | 211 | Duplicate/retired |
| `db-freshness-check.yml` | 211 | Duplicate/retired |
| `cross-db-consistency.yml` | 211 | Duplicate/retired |
| (7 more minor variants) | — | Same pattern |

**Verdict:** Do **not** cherry-pick or port any of these back to main. They were removed for cause.

## 4. Why These Branches Exist & Recommendation
Most appear to be:
- Feature/experiment branches (`feat/*`, `fix/*`, `claude/*`)
- Temporary rescue / audit / wired-in fix branches
- Historical snapshots before large refactors

**Why they can be deleted:**
- No unique workflow logic survives on main.
- No open dependency from the single open PR (needs separate check).
- They bloat `git ls-remote` and increase cognitive load for anyone auditing the Actions tab.

**Safe cleanup path:**
1. Confirm the 1 open PR does not target any of these branches.
2. Delete branches in batches of 20–30 via `git push origin --delete`.
3. If any branch name pattern is still actively used (e.g., ongoing `claude/*` sessions), keep those and only delete the clearly abandoned ones.

## 5. Drop-in for Main (GHACTIONS_NONMAIN_DIAGNOSIS.md)
See companion file `GHACTIONS_NONMAIN_DIAGNOSIS.md` for the concise, cherry-pick-ready summary suitable for committing to `main`.

---

## Keep/Delete Verdict (2026-11-16 04:2xZ, branch-mapper/PAID-GROK)

Scope of this section: **the per-prefix decision list**, i.e. exactly the gap §4 left open ("delete in batches of 20–30" with no named verdicts). The census figures above (222 heads / ~79,938 `cron:` lines / GHA-schedules-only-run-on-default-branch) are **accepted as given per coordinator instruction** and are not re-derived here. Only the branch/prefix counts in the tables below are mine.

### A. What I actually measured (and one reconciliation)

| Metric | Value | Source |
|---|---|---|
| Remote heads seen via `git for-each-ref refs/remotes/origin` @ 2026-11-16T04:10Z | 213 (incl. `main`) → **212 non-main** | my pass |
| Non-main branches with ≥1 commit in last 7 days | **35** | my pass |
| Median / p90 / max age since last commit | **85d / 156d / 163d** | my pass |
| Branches >90 days stale | **101** (48% of all non-main) | my pass |

**Reconciliation flag — not a contradiction, a ref-timing delta.** §1 reports 221 non-main heads from `git ls-remote --heads`; my local `for-each-ref` sees 212. The 9-branch gap is remote refs never fetched into this clone plus refs renamed/pruned since §1 ran — the *per-branch* prefix table below is complete for every branch my ref set contains, so no verdict is missing, but a `git fetch --prune` immediately before executing any delete batch is mandatory. Also note `deliver-docs` and `feature/*`/`cursor/*`/`dependabot/*` (named in the coordinator's brief) **do not exist as prefixes in this repo** — 0 branches each. `deliver-docs` is a *worktree checkout*, not a remote head.

### B. Divergence from `main` — and why no branch is a merge candidate

`git rev-list --left-right --count origin/main...origin/<b>` groups every branch into:

| Group | `behind main` | # branches | Reading |
|---|---|---|---|
| A | >200k commits | 103 | essentially **no shared ancestry** (squashed-import history) |
| B | 40k–200k | 71 | same, shallower break |
| C | 5k–40k | 20 | mid-history fork |
| D | 500–5k | 16 | genuinely recent fork |
| E | <500 | 3 (`main`, `gh-pages`, `fix/etf-short-gate-vix-combos-2026-11-15`) | current |

> [!IMPORTANT]
> These "behind" magnitudes are not conflict risk — they are evidence that the branch's history was disconnected from `main`'s. **Consequence: no non-main branch can be merged or cherry-picked wholesale.** Only individual commits (max observed `ahead` is 45, on `job-search-2026-11-03-ledger`) are portable. Any "just merge the branch" plan is wrong.

### C. ★ Per-prefix KEEP / DELETE / ARCHIVE

| prefix | # branches | newest commit | verdict | one-line reason |
|---|---|---|---|---|
| `claude/*` | 96 | 2026-09-08 | **DELETE** | 65 in divergence-grp A; all June-2026 `fervent-knuth-*` scratch sessions; max age 163d; `ahead` ≤ handful. Zero review value. |
| `feat/*` | 32 | 2026-11-14 | **ARCHIVE → DELETE** | 19 in grp A are pre-June experiments; 4 grp-C branches (2026-11-14) may hold unreviewed wiring — diff those 4 before deleting the other 28. |
| `other` (no prefix) | 39 | 2026-11-16 | **SPLIT — see C2** | Mixed bag: contains `gh-pages` (KEEP) and the `job-search-*`/site-page orphans (DELETE). Cannot be one verdict. |
| `fix/*` | 23 | 2026-11-15 | **KEEP 7 / DELETE 16** | 7 carry 2026-11-15/16 commits (`blob-guard`, `etf-short-gate-vix`, `feature-signals-safe-push`, `gha-backup-verify-dedup`, `kilo-ci-tests`, …) — live work; the other 16 are grp A/B stale. |
| `audit*` | 5 | 2026-11-15 | **KEEP** | Audit/report branches, ≤1 ahead, harmless, actively reused as scratch for audits; `backup/gha-audit-2026-11-16` is a deliberate pre-change snapshot. |
| `opencode/*` | 4 | 2026-10-20 | **DELETE** | Abandoned 27d ago, grp A/B, superseded by `oc-winning-candidate` (which itself is already merged-equivalent, see C2). |
| `rescue/*` | 4 | 2026-10-19 | **DELETE** | "Rescue" attempts from Oct that never landed; nothing references them; grp B. |
| `nemotron*` | 3 | 2026-10-20 | **DELETE** | June-2026 nemotron audit family; oldest members 163d; superseded. |
| `docs/*` | 3 | 2026-11-14 | **KEEP** | Recent doc-only branches, ≤50k behind (grp B), zero runtime impact, cheap to hold. |
| `wired-in/*` | 2 | 2026-11-15 | **KEEP** | Only 2.4k behind (grp D), current WIRED_IN work, actively referenced by other swarm findings. |
| `gh-pages` | 1 | 2026-11-16 | **KEEP — NEVER DELETE** | Live Pages publish branch; ahead 3829, last commit `deploy: ff7dad4…` today 03:34Z. Deleting it breaks the public site. Exclude from every batch. |
| `copilot/*` | 1 | 2026-11-01 | **DELETE** | 31k behind, single abandoned Copilot suggestion, 15d idle. |
| `feature/*`, `cursor/*`, `dependabot/*`, `deliver-docs` | **0** | — | **N/A** | These prefixes do not exist in this repo. `deliver-docs` is a worktree, not a branch. |

**Net effect of the table: DELETE 96+28+16+4+4+3+1 ≈ 152 branches; ARCHIVE-then-review 4; KEEP ≈ 56 (incl. `gh-pages` and 7 live `fix/*`).** That is ~72% of non-main refs reclaimable with no pipeline impact.

### C2. The no-prefix long tail (39 branches — the actual orphans)

**KEEP (3):**
- `gh-pages` — live deploy (see above).
- `hermes/forex-session-window-fix` (2026-11-15, +4/−1675) and `hilarious-seer-to-main` (2026-11-15, +11/−1594) — grp D, tiny divergence, 1 day old, plausibly still-open work.

**DELETE — orphaned / feeding nothing (the job-board & site-page cluster, 11):**
`job-search-2026-11-03`, `-fresh-48h`, `-jd-scoring`, `-ledger`, `-rounds21-27`, `job-hunting-skills-catalog`, `add-kilo-additional-skills`, `add-kilo-todays-servicenow-salesforce-jobs`, `bestiejobs-v3`, `techfinds-page-oct12`, `huggle-agent-2026-10-30`.
These are all **non-trading site/job-board experiments** — they carry the workflow superset but their own commits only touch job-scraping/HTML. They feed **no** trading pipeline and **no** deployed path. Note: `job-search-*` has the highest `ahead` counts in the repo (42–45) purely because they were squashed imports of one job-search project, not because they hold 45 valuable commits.

**DELETE — abandoned one-offs (14):**
`oc-winning-candidate`, `oc/fund-walkforward-review-fixes`, `buffy/batch-close-rootcause`, `grok-audit-framework`, `research/ghcopilot-symbol-durability`, `scrub/inception-mercury-2026-11-12`, `chore/scrape-events-11pm-toronto`, `swarmmethodquality-v2`, `swarmmethodquality-v4`, `samagain-v4`, `multi4-v3`, `ollama-checks`, `ollama-checks-v3`, `salesforceagain-v3`. Iteration siblings (`-v2/-v3/-v4` families) where the newest is already represented; all 12–32d idle, `ahead` ≤11, grp B/C.

**ARCHIVE (2):**
- `wiring` (2026-11-14, +10/−7082) and `videos-pipeline` (2026-11-14, +1/−3054) — small, dated, but could hold the last wiring artefact; tag `archive/2026-11` then delete.

**DELETE — pre-June archaeology (8):**
`archive/oct3-branch-june-commits`, `refute/crypto-short-rsi5070-regime-0622`, `worktree-equity-reachability-tp-2026-06-13`, `plan/forex-long-pilot-2026-06-13`, `kilo-strategy-kill-2026-06-12`, `forex-carry-amplify-2026-06-12`, `money-ready-picks-now-2026-06-06`, `pr/money-ready-bridge-truth`. All >150d, grp A/B, names encode work that is either shipped or abandoned.

> [!WARNING]
> **`pr/money-ready-bridge-truth` is +31/−304438 — the single largest `ahead` count outside the job-search cluster.** The one open PR in the repo (noted in §Executive Summary) may target it. **Verify with `gh pr list --state open` / the GitHub UI before deleting this one branch.** Everything else in the DELETE lists is PR-free to the best of this pass's evidence (no `gh` token available here, so this specific claim is UNVERIFIED).

### D. Execution order (safe, reversible)

1. `git fetch --prune` (reconciles the 221→212 delta).
2. Resolve the 1 open PR's head branch; remove that branch from the DELETE set.
3. Tag before delete: `git tag archive/nonmain-2026-11 <batch>` so reflog expiry can't lose anything.
4. Delete in the order `claude/*` (96) → `feat/*` (28) → `fix/*` (16) → long-tail orphan clusters → archaeology (8). Batch size 20–30, matching §4.
5. Never touch `gh-pages`, `main`, `wired-in/*`, `docs/*`, the 5 `audit*`, or the 7 live `fix/*`.

**Confidence:** prefix counts and ages are measured (high). Delete-worthiness of individual long-tail branches is inferred from name + age + divergence (medium). The open-PR exception is UNVERIFIED and must be checked by a human or a `gh`-authed agent before step 4.

---

**End of NONMAINBRANCHES.MD**
