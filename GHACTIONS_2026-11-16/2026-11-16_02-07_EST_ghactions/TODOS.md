# TODOS — GH Actions audit, push gate

**STAMP:** 2026-11-16_02-07_EST_ghactions
**origin/main as of 02:22Z (sha at time of analysis: 29b358a09605cc321e7900f38813368dfdbea38d); main advances continuously — re-fetch before relying on any branch delta**
Local HEAD at time of writing: `89bbb6a2212` (branch `main`).

---

## 1. Deliverables — ALL PRESENT

### `GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/` (analysis stamp)
| File | Size | Owner | Status |
|---|---|---|---|
| `branch_capability.tsv` | 19,849 B | fix-manager | ✅ 215 rows, 14 cols, HAZ=0 |
| `branch_prune_list.md` | 9,803 B | fix-manager | ✅ |
| `branch_trigger_audit.md` | 9,553 B | inspector | ✅ headline: 4 push-no-filter files |
| `cron_stagger_plan.md` | 10,079 B | queue_auditor | ✅ |
| `cron_verification.md` | 6,187 B | triage-expert | ✅ |
| `orphan_items.md` | 14,795 B | analyst-2 | ✅ |
| `push_chain_impact.md` | 6,997 B | queue_auditor | ✅ |
| `site_impact_audit.md` | 8,863 B | analyst-2 | ✅ |

### `GHACTIONS_2026-11-16/2026-11-16_02-07_EST_ghactions/` (runbook stamp)
| File | Size | Owner | Status |
|---|---|---|---|
| `revert_runbook.md` | 13,370 B | fix-manager | ✅ (§0 label fix pending) |
| `TODOS.md` | this file | coordinator | ✅ |

---

## 2. Push gate

Do **NOT** push until all of these are true:

1. ✅ All 8 analysis deliverables present with STAMP headers
2. ✅ `revert_runbook.md` carries exact `git checkout origin/main -- <path>` commands + verification checklist
3. ✅ `fix-manager` reconciles `revert_runbook.md` §0: unpin `b016a61f9a2`, fix the ahead/behind label (corrected to `88367 ahead, 15 behind`; 4645d08 purged from all runnable commands)
4. ⬜ `analyst-2` appends per-file "does /audit depend on it" verdict to `site_impact_audit.md`
5. ⬜ `queue_auditor` confirms the 3-writer push race in `push_chain_impact.md`

**Staging rule (hard):** stage `GHACTIONS_2026-11-16/**` doc paths **file by file**.
**NEVER** `git add .github/workflows/` — see §3 and `revert_runbook.md` §0.

---

## 3. HAZARD — untracked `.github/workflows/lint.yml` ⚠️

Discovered in the working tree at 02:18Z. **Not committed. Do not commit it.**

```
?? .github/workflows/lint.yml      (no git history — never tracked in this repo)
```

Why it must not be pushed:

| Property | Value | Why it matters |
|---|---|---|
| Triggers | `push:` **with no `branches:` filter**, `pull_request:`, `workflow_dispatch:` | This is exactly the "whole-fleet-on-push" hazard `branch_trigger_audit.md` flags as one of only 4 such files. A push-no-filter workflow fires on **every branch**, including the ~110 throwaway `claude/*` branches. |
| Job `python` | `py_compile` over `git ls-files '*.py'` | Fleet-wide; any pre-existing syntax error in any tracked script turns every push red. |
| Job `python` step 2 | `python tools/agy_patch_kit.py --help` and `python Windows/agy_patch_cli.py --help` | **Both paths are untracked local work** (`tools/agy_patch_kit.py` = `??`, `Windows/` = `??`). On CI these files do not exist → **guaranteed red on every run**. |
| Job `powershell` | `runs-on: windows-latest`, scans `./Windows/*.ps1` | Same untracked-directory problem; also adds a Windows runner to the fleet. |

**Verdict:** this file belongs to a separate local port of the agy patch kit (`updates/2026-11-16-agy-kit-fresh-install-review-and-windows-port.md`), not to this repo's CI. It should live in that side project's own repo, or be rewritten to drop the `Windows/` + `tools/agy_patch_kit.py` steps and add a `branches: [main]` filter — before it is ever committed here.

**Action:** leave untracked. If it must be committed, it needs its own review, not this audit's push.

---

## 4. Resolved questions

### `daily-price-refresh.yml` — RESOLVED: do not port to main

User question #6 ("is it on stale branches but deleted on main — investigate why it was removed, does it have use, should it be ported?").

| Check | Command | Result |
|---|---|---|
| Present on main? | `git cat-file -e origin/main:.github/workflows/daily-price-refresh.yml` | **absent** |
| Removal commit on main? | `git log --diff-filter=D origin/main -- …/daily-price-refresh.yml` | **no output** — it was never on main's history, so it was not "removed"; it only ever existed on side branches |
| `.disabled` variant on main? | `git log origin/main -- …/daily-price-refresh.yml.disabled` | **no output** |
| Replacement on main? | `git show origin/main:.github/workflows/daily-prices-yf-refresh.yml` | **exists** — header comment: *"Replaces the DEAD fetch_prices.php (HTTP 404) that froze daily_prices at 2026-04-29."* |

**Conclusion:** no restoration needed, and nothing to port. `daily-prices-yf-refresh.yml` on main is the live successor (`cron: 40 22 * * 1-5`, `concurrency: daily-prices-yf-refresh`, `cancel-in-progress: false`, runs `tools/refresh_daily_prices_yf.py`) and explicitly documents that the endpoint the old workflow called is dead. Restoring the old file would reintroduce a 404-calling job.

The ~50 stale branches that still carry `daily-price-refresh.yml` are covered by `branch_prune_list.md`; each one fires that workflow on its own pushes, which is a branch-cleanup problem, not a main-porting problem.

### `site_impact_audit.md` — downstream /audit impact

Answer delivered (analyst-2, seq 113) and documented: **none of the 9 resurrectable deletions writes to the live `/audit` directory.** Verified at the parent-of-deletion commit `707a07092a1b`: no `lftp`/`rsync`/`ftplib`/`FTP_HOST`/`deploy`/`/audit` references in `cross-db-consistency`, `db-freshness-check`, `live_trading_canada_free`; `meme-scanner-fixed.yml` only curls the findcryptopairs PHP API read-only; `daily-price-refresh.yml.disabled` only curls `$ENDPOINT` to `/tmp`; the 4 `ml-battleground` `.retired` files are inert. None of the 9 carries a `push:` trigger.

The live `/audit` writers that **do** matter are inventoried in `site_impact_audit.md` §1 (54 writers, 13 targeting `/audit` explicitly) — chief among them `audit-dashboard.yml` (hourly, `cancel-in-progress: false`, 115 min timeout) and `deploy-competition-to-site.yml`.

---

## 5. Commit plan (when gate clears)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
git fetch origin main

# Stage docs ONLY — file by file, never the workflow dir
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/branch_capability.tsv
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/branch_prune_list.md
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/branch_trigger_audit.md
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/cron_stagger_plan.md
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/cron_verification.md
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/orphan_items.md
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/push_chain_impact.md
git add GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/site_impact_audit.md
git add GHACTIONS_2026-11-16/2026-11-16_02-07_EST_ghactions/revert_runbook.md
git add GHACTIONS_2026-11-16/2026-11-16_02-07_EST_ghactions/TODOS.md

# Verify NOTHING from .github/workflows/ or Windows/ is staged
git diff --cached --name-only | grep -E '^\.github/workflows/|^Windows/' && echo "ABORT" || echo "clean"
```

**Revert of this push:** docs only, so `git revert <sha>` is sufficient and touches no workflows. See `revert_runbook.md` for the workflow-side reverts of anything already on main.

---

## 6. Model swap log

| Time (Z) | Agent | Old | New | Reason |
|---|---|---|---|---|
| 02:02 | `queue_auditor` | `ULTRA_FREE_CLOUD_LARGE` | `ULTRA_FREE_CLOUD` | 429 quota, swapped lighter |
| 02:22 | all | — | — | converged; no further swaps needed |
