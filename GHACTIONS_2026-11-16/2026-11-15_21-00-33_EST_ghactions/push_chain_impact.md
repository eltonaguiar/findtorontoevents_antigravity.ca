# push_chain_impact.md

> [!WARNING]
> **origin/main advances continuously** (bot commits roughly every ~60 s). The shas below were observed at the time of analysis and are **not durable bases**. **Always `git fetch origin main` and re-run `git diff --name-status HEAD origin/main -- .github/workflows/` immediately before acting** — a pinned sha a few minutes old will read as wrong. Do not treat any sha in this document as authoritative.
>
> origin/main as of 02:14Z (sha at time of analysis: `ae3f4dc4dc1c2a1e63abd5285e8c037e6f136695`; known to have advanced since — `5e86dd18e15`, `b016a61f9a2` observed later).

**Base commit (at time of analysis):** `ae3f4dc4dc1c2a1e63abd5285e8c037e6f136695` — origin/main @ 2026-11-16T02:14Z. See caveat above.
**STAMP:** 2026-11-15_21-00-33_EST_ghactions
**Generated:** local git only — `git show origin/main:<path>` (no GitHub API)

## Lead Finding: Stale Fork of Workflows

**CRITICAL PUSH-SAFETY TRAP:** The local working tree (`89bbb6a2212`) is a **stale fork** of `.github/workflows/` relative to `origin/main`. A naive `git add .github/workflows/ && git commit && git push` would **silently revert a live production fix** and resurrect 9 deleted files.

**Delta (local HEAD vs origin/main @ 5e86dd18e15, 13 commits behind):**

| Class | File | Effect of naive commit |
|-------|------|------------------------|
| **WOULD REVERT a live fix** | `dynamic-alpha-engine.yml` | `timeout-minutes: 90` → `60` (line 115 vs 112), resurrects the exact cancel-churn the bump fixed |
| **WOULD RESURRECT a deleted file** (9) | `cross-db-consistency.yml` | deleted on main by `c2393512637` |
| | `db-freshness-check.yml` | same |
| | `live_trading_canada_free.yml` | same |
| | `meme-scanner-fixed.yml` | same |
| | `daily-price-refresh.yml.disabled` | same |
| | `ml-battleground-{d,e,ensemble,monitor}.yml.retired` (4 files) | same |
| **ALREADY REFLECTS MAIN / no-op** | `ml-gatekeeper-ab-bootstrap.yml.disabled`, `mysql-q001-sync.yml.disabled` | already renamed on main by `3d1aa94ba5e` |

**Consequence:** 12 files would change state on a naive push. **Never stage the whole `.github/workflows/` directory.** Stage only `GHACTIONS_2026-11-16/**` docs path, file by file.

**Revert runbook items (for @fix-manager `revert_runbook.md`):**
- `git checkout 4645d08eee4 -- .github/workflows/dynamic-alpha-engine.yml` (restores 90 min timeout)
- `git revert <our-sha>` for docs-only commits (safe, only touches `GHACTIONS_*` paths)
- `git checkout c2393512637^ -- .github/workflows/<name>` to restore any of the 9 deleted files if a restore is ever wanted — but note these were **deleted deliberately**, so restoring is a rollback of a cleanup, not a bugfix
- Verify checklist: (a) `git diff origin/main -- .github/workflows/ | grep -c '^[+-]'` must be 0; (b) `grep -n timeout-minutes .github/workflows/dynamic-alpha-engine.yml` must show `90`; (c) `git ls-tree -r --name-only HEAD -- .github/workflows | wc -l` must equal main's count (373 tree entries)

---

## Push-Trigger Inventory (356 workflow files @ `ae3f4dc`)

| Trigger class | Count | Notes |
|---------------|-------|-------|
| `on: push:` | 40 | 11.2 % of workflows |
| `on: push:` + `paths:` filter | 47 | some use paths, some don't |
| `on: push:` + `branches:` filter | 37 | branch-restricted pushes |
| `schedule:` + `push:` both | 26 | dual-mode files (schedule + manual push) |
| `workflow_run:` | 7 | downstream of another workflow's completion |
| `concurrency:` + `cancel-in-progress: false` | 118 | 72 % of the 164 concurrency declarations |

**Key observation:** 26 files have both `schedule:` and `push:` triggers. These are the **highest push-chain amplification risk** — a push from a scheduled run can immediately re-trigger the same workflow (or a dependent one) via the `push:` path, creating a feedback loop unless guarded by `concurrency.group` + `cancel-in-progress: false`.

---

## Push-Chain Amplification Paths

### 1. Schedule → Push (self-trigger)

**Pattern:** A scheduled workflow runs, commits/pushes results, and the `on: push:` trigger fires the same (or another) workflow.

**Risk files (26 dual-mode):**
- Any file with both `schedule:` and `push:` in the same `on:` block.
- Example: `dynamic-alpha-engine.yml` (cron `18,48 * * * *` + `workflow_dispatch`) — guarded by `concurrency.group: dynamic-alpha-engine-push` + `cancel-in-progress: false`.

**Mitigation:** All 26 dual-mode files should declare `concurrency.group` + `cancel-in-progress: false` (or `true` if later runs supersede earlier ones). Currently only 118 of 164 concurrency declarations have this guard.

### 2. Push → workflow_run (downstream cascade)

**Pattern:** A push triggers a workflow, which on completion triggers `workflow_run:` listeners (7 files).

**Risk:** If the upstream workflow is itself push-triggered, a single developer push can cascade through the entire chain.

**Mitigation:** Ensure every `workflow_run:` listener also declares `concurrency.group` to serialize against its own upstream.

### 3. Stale-fork amplification (this tree)

**Pattern:** The local tree is 13 commits behind `origin/main`. Any workflow edit we stage from this tree risks reverting live fixes (e.g., the 90→60 timeout regression).

**Mitigation:** Never stage `.github/workflows/` wholesale. Build patches against `origin/main`'s blob, not the local file.

---

## Named Hazard: FTP Deployers vs `/audit` — the three-deployer question, answered

**Question (from board #118):** do `deploy-competition-to-site.yml`, `deploy-fte-index.yml`, and `deploy-battleground-ftp.yml` all fire on the same `push` with no shared concurrency group, making a simultaneous 3-writer race at `/audit/`?

**Answer: no — the race is not 3-wide, but one of the three is a real unguarded `/audit` writer.**

Verified against `origin/main` (blobs read at 02:22Z via `git show origin/main:.github/workflows/<file>`):

| File | push filter | Deploy mechanism | FTP target | Writes `/audit`? | `concurrency:` |
|------|-------------|------------------|------------|------------------|----------------|
| `deploy-competition-to-site.yml` | `branches:[main]` + `paths:` (`STOCKS/competition/**`, `audit_dashboard/**`, `updates/index.html`, `cross_aggregation/data/**`, …) | `lftp` | `/findtorontoevents.ca` | **YES** — `audit_dashboard/**` is in its path filter | **none** |
| `deploy-fte-index.yml` | `branches:[main]` + `paths:` (`TORONTOEVENTS_ANTIGRAVITY/index.html`, `next_htaccess`) | `lftp` | site root | no | **none** |
| `deploy-battleground-ftp.yml` | `branches:[main]` + `paths:` (`battleground/**`) | `ftplib` | `findtorontoevents.ca` root | no | **none** |

**Why the 3-way race does not occur:** all three are `paths`-filtered and the filters are **disjoint** (`audit_dashboard` / `STOCKS/competition` vs `TORONTOEVENTS_ANTIGRAVITY` vs `battleground`). A single commit touching only one of those trees fires exactly one deployer. A commit touching two fires two, but they write to **different sub-trees of the same FTP account** — filesystem-level collision only if the same path were written, which the filters prevent.

**The real hazard that does exist:** `deploy-competition-to-site.yml` is the **only** deployer with `/audit` in its push path filter, and it declares **no `concurrency:` group**. Two pushes to `audit_dashboard/**` in quick succession (routine here — bots push on a ~60 s cadence) produce two concurrent `lftp` sessions writing the same remote `/audit` files. Last-writer-wins, with no ordering guarantee and no cancellation of the stale run.

**One-line mitigation** (add to `deploy-competition-to-site.yml`, at top level, alongside `permissions:`):

```yaml
concurrency:
  group: ftp-deploy-audit-dashboard-${{ github.ref }}
  cancel-in-progress: false   # never cancel mid-upload; queue instead
```

Use `cancel-in-progress: false` deliberately: cancelling an `lftp` mid-transfer can leave a partially uploaded `/audit` JSON, which is worse than a delayed run. A shared group name across all three deployers (`ftp-deploy-${{ github.ref }}`) is the conservative alternative if cross-tree FTP contention is ever observed — but on current path filters it would serialize disjoint deploys for no gain.

**Not a push-chain finding:** none of the nine resurrectable deletions is one of these three, so the stale-fork hazard does not interact with this one.

---

## Concurrency Coverage Gap

**Current:** 164/356 files (46.1 %) declare `concurrency:`, 118 with `cancel-in-progress: false`.

**Gap:** 192 files have no concurrency guard. Of these, 26 are dual-mode (`schedule:` + `push:`) and are the highest-risk for push-chain feedback loops.

**Recommended canonical group expression:** `${{ github.workflow }}-${{ github.ref }}` (or a short hash thereof) for consistency. Mixed naming observed (`ab-analysis`, `${workflow}-${ref}`) — consolidate to one pattern.

---

## Push-Safety Checklist (before any commit from this tree)

1. **Verify HEAD is not stale:** `git rev-parse HEAD` vs `git rev-parse origin/main` — if behind by >0 commits, `git pull --rebase` first.
2. **Never stage `.github/workflows/` wholesale.** Stage only `GHACTIONS_2026-11-16/**` docs.
3. **If editing a workflow:** read `origin/main`'s blob, apply change, verify `git diff origin/main -- <path>` shows only the intended hunk.
4. **For `dynamic-alpha-engine.yml` specifically:** confirm `timeout-minutes: 90` (line 115) before staging.
5. **Verify no resurrection:** `git ls-tree -r --name-only HEAD -- .github/workflows | wc -l` must equal main's count (373 tree entries); any discrepancy indicates a deleted file would be resurrected.

---

**References (local git only):**
- `git show ae3f4dc4dc1c2a1e63abd5285e8c037e6f136695:.github/workflows/dynamic-alpha-engine.yml` for the 90-min timeout + concurrency guard.
- `git diff --name-status HEAD origin/main -- .github/workflows/` for the 12-file delta.
- `/tmp/qa3/blobs/*` for push-trigger counts (40 push, 26 schedule+push, 7 workflow_run).
