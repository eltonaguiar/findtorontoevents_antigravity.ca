# Site Impact Audit

**STAMP:** 2026-11-15_21-00-33_EST_ghactions

**origin/main as of 02:20Z (sha at time of analysis: 29b358a09605cc321e7900f38813368dfdbea38d); main advances continuously — re-fetch before relying on any branch delta**

## 1. Deploy Inventory (origin/main)

**Primary live-site writers (54 total, 13 target /audit explicitly):**

| Workflow | Trigger | Concurrency | FTP Target | Notes |
|----------|---------|-------------|------------|-------|
| audit-dashboard.yml | schedule: '10 * * * *' + workflow_dispatch | group: unified-audit-dashboard (cancel-in-progress: false) | /audit/ (50webs, GoDaddy, tdotevent.ca) | timeout-minutes: 115; primary /audit writer; heavy generator + commit + FTP; comment warns 90m still saw mid-step cancellations (stale /audit) |
| deploy-competition-to-site.yml | push: branches: [main] + workflow_dispatch | none declared | /audit/, /audit_dashboard/, /STOCKS/competition | cd $REMOTE_BASE/audit; mkdir -p; uploads Audit Dashboard + Portfolio Challenge files; also writes to /audit_dashboard/data |
| deploy-fte-events-json.yml | workflow_dispatch | group: fte-ftp-deploy | /audit/ | concurrency serializes with deploy-fte-index.yml |
| deploy-fte-index.yml | push: branches: [main] + workflow_dispatch | group: fte-ftp-deploy | /audit/ | concurrency serializes with deploy-fte-events-json.yml |
| deploy-alpha-dashboard.yml | push: branches: [main] + workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-battleground-ftp.yml | schedule: '15 * * * *' + workflow_dispatch + push: [main] | none declared | GoDaddy dotnet host | |
| deploy-fc-api-env-godaddy.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-fc-api-hotfix.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-fc-frontend.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-findcryptopairs-ftp.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-friendtracker.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-movieshows-all.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| deploy-movieshows3-hotfix.yml | workflow_dispatch | none declared | GoDaddy dotnet host | |
| torontoevent-deploy-competition.yml | push: branches: [main] + workflow_dispatch | none declared | /STOCKS/competition, /updates, /pine_scripts | torontoevent.net mirror; cd /STOCKS; lcd pine_scripts |
| mirror-site.yml | schedule: '0 */6 * * *' + workflow_dispatch | group: mirror-site-deploy | GoDaddy /, 50webs /tdotevent.ca | 3-destination mirror |
| db-sync-bidirectional.yml | schedule + workflow_dispatch | none declared | FTP_SERVER | lftp bidirectional |
| db-sync-to-mirror.yml | schedule + workflow_dispatch | none declared | FTP_SERVER | lftp mirror |
| ai-leaderboard-freshness.yml | schedule + workflow_dispatch | none declared | FTP_USER | writes status messages |
| ai-model-portfolios-daily.yml | schedule + workflow_dispatch | none declared | FTP_USER | uses ftplib.FTP_TLS |
| ai-tournament-pipeline.yml | schedule + workflow_dispatch | none declared | FTP_USER | |
| algorithm-competition-refresh.yml | schedule + workflow_dispatch | none declared | FTP_USER | installs lftp, mput |
| alpha-engine-daily-picks.yml | schedule + workflow_dispatch | none declared | FTP_USER | installs lftp |
| asterdex-paper-trading.yml | schedule + workflow_dispatch | none declared | FTP_USER | installs lftp |
| backtest-and-deploy.yml | schedule + workflow_dispatch | none declared | FTPGODADDYHOST_TE_DOTNET | ftplib |
| claudes-test-portfolios.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| daily-feed-summary.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| daily-top-picks-filter.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| edge-stability-refresh.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| fix-ghost-cards.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| genome-daily-pipeline.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| gha-summary-report.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| ghcopilot-paper-monitor.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| incidents-enhancements-nightly.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| incubator-pipeline.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| kimi-feb172026-live.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| meme-scanner-v2.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| pick-funnel-nightly.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| picks-now-live-pnl.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| picks-now-refresh.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| rapid-validation-CLAUDECODE_Feb152026.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| riseoftheclaw-weekly-backtest.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| send-accountability-reminders.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| social_investigation.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| sports-data-snapshots.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| sports-smoke-and-e2e.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| taste-profile-scan.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| torontoevent-algorithm-refresh.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| torontoevent-backtest-and-deploy-ROOCODE.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| torontoevent-backtest-and-deploy.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| torontoevent-deploy-live-monitor.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| torontoevent-deploy-riseoftheclaw.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| torontoevent-rapid-validation.yml | schedule + workflow_dispatch | none declared | FTP_HOST | |
| forward-test-daily.yml.disabled | schedule + workflow_dispatch | none declared | FTP_HOST | .disabled, inert |

## 2. /audit/ Writers vs Readers

**Writers to /audit/ (live site directory):**
- `audit-dashboard.yml` — primary, hourly cron + dispatch, 115-min timeout, FTP to 3 mirrors
- `deploy-competition-to-site.yml` — push + dispatch, mkdir -p $REMOTE_BASE/audit, uploads dashboard + portfolio challenge files
- `deploy-fte-events-json.yml` — dispatch, concurrency: fte-ftp-deploy
- `deploy-fte-index.yml` — push + dispatch, concurrency: fte-ftp-deploy

**Readers of /audit/ (or /audit/data/dashboard_data.json):**
- `asset-class-freshness-watchdog.yml` — curls `https://findtorontoevents.ca/audit/data/dashboard_data.json` (read-only monitoring)

## 3. Cross-Reference of 12 Stale-Fork Workflows Against Deploy Set

**Class (a) 1 would-revert:**
- `dynamic-alpha-engine.yml` — timeout-minutes: 90 @ main vs 60 @ HEAD; landing local would revert churn-fix; **not in deploy set** (no FTP steps).

**Class (b) 9 would-resurrect:**
- All 9 absent from main (deleted in c2393512637, side-branch only).
- **None carry `push:` trigger.**
- **None have FTP/deploy/lftp/ftplib steps.**
- 5 mention `/audit` in comments (read-only context); 0 write to it.
- 3 are schedule + workflow_dispatch; 2 are workflow_dispatch-only; 4 are .retired/.disabled (inert).
- **Answer to the mandated one-sentence question:** **No** — none of the 9 resurrected workflows would write to the live `/audit` directory.

**Class (c) 2 no-op renames:**
- `.disabled`/`.retired` renames on local only; would remain inert even if pushed; **not in deploy set**.

## 4. The 9 Deleted Workflows (Verified at 707a07092a1b)

| File | push: | FTP/deploy | /audit mentions | Present on main |
|------|-------|------------|-----------------|-----------------|
| cross-db-consistency.yml | 0 | 0 | 3 (comments) | NO |
| db-freshness-check.yml | 0 | 0 | 3 (comments) | NO |
| live_trading_canada_free.yml | 0 | 0 | 0 | NO |
| meme-scanner-fixed.yml | 0 | 0 | 0 | NO |
| daily-price-refresh.yml.disabled | 0 | 0 | 0 | NO |
| ml-battleground-*.yml.retired (4) | 0 | 0 | 2 (comments) | NO |

All 9 verified **ABSENT ON MAIN**. None would start writing to `/audit` if resurrected.

## 5. Pre-Push Guard

```bash
# Required before any push
git fetch origin main
git diff --name-status HEAD origin/main -- .github/workflows/
# Must show 0 rows; if any row touches a deploy workflow or audit writer, abort.
```

**Risk flag:** `deploy-competition-to-site.yml` and `deploy-fte-index.yml` both have `push: branches: [main]` and write to `/audit/`. Any resurrect that lands either would immediately begin live writes on next push.


---

## 6. Verdict on the 12-File Delta — does any live `/audit` producer depend on each file?

Question answered per file: **if this file lands on `origin/main` as it exists on `HEAD`, does anything that currently produces live `/audit` content stop working, or does a new writer start?**

Pinned for this analysis: `origin/main` as of 02:31Z (sha at time of analysis: `b129d094d8002c331b8e5a0923276dccb35cf37b`; main advances continuously — re-fetch before relying on any branch delta). File contents for the 9 deletions read at `707a07092a1b1e9227c3930311c8a5f2e318291f`.

**Re-verified at 02:31Z after #124:** the 12-row delta is **unchanged** against `b129d094d80` (same 9 `D` + 1 `M` + 2 `R`, byte-identical file list). Spot-checked on the fresh sha: `db-freshness-guardian.yml` still **present**, `cross-db-consistency.yml` still **absent**, `audit-dashboard.yml` / `deploy-competition-to-site.yml` / `deploy-fte-index.yml` all still **present**, and `dynamic-alpha-engine.yml` still **90 lines / `timeout-minutes: 90` on main vs 60 on HEAD**. The verdicts below are therefore current, not inherited.

**Short answer: no. All 12 are dependency-free with respect to live `/audit` production.** Three of them (`cross-db-consistency`, `db-freshness-check`, `live_trading_canada_free`) write reports into `audit_dashboard/data/`, which *is* a `/audit` publish surface — but the specific files they write are either not in that publish path or are already produced by a surviving workflow. Detail below is per file.

### 6.1 The 9 deletions

| # | File (deleted on `origin/main`) | Any live `/audit` producer depend on it? | Rationale |
|---|---|---|---|
| 1 | `cross-db-consistency.yml` | **No** — standalone diagnostic | Writes `audit_dashboard/data/cross_db_report.json`. `audit-dashboard.yml` globs `audit_dashboard/data/*.json` → `/audit/data`, so the file *would* be published if it existed, but **nothing reads it**: 0 references anywhere in `audit_dashboard/` (HTML/JS/Python), and `db_health_check.py` only cross-references the *script* `tools/db_freshness_check.py` in a code comment. Its only output is a git commit + a failing/warning CI check. Removing it removes a report nobody consumes — `/audit` loses nothing. |
| 2 | `db-freshness-check.yml` | **No** — superseded, not depended on | Writes `audit_dashboard/data/db_freshness.json` (a `/audit`-published path — the one genuine overlap). But **`db-freshness-guardian.yml` survives on main and writes the same file to the same path**, on a *stronger* trigger (`schedule '0 * * * *'` hourly + `push [main]` filtered to `tools/db_freshness_check.py` + dispatch). `db-freshness-check.yml` was `workflow_dispatch`-only, i.e. a manual legacy duplicate. Deleting it changes nothing that `/audit` sees. **This is the file most worth stating explicitly for a reader** — the name overlap with a live producer is a false positive. |
| 3 | `live_trading_canada_free.yml` | **No** — unrelated domain | Crypto trading bot (`schedule '0 */4 * * *'`, `DRY_RUN` default `true`). No FTP, no `/audit` path, no `audit_dashboard/data` write, 0 `/audit` mentions. Its outputs are trading state, not audit content. |
| 4 | `ml-battleground-d.yml` | **No** — `audit` mention is a comment only | 2 `/audit` mentions, both read-only comments. No FTP step, not in the deploy set. |
| 5 | `ml-battleground-e.yml` | **No** — comment only | Same as #4 (2 comment mentions). |
| 6 | `ml-battleground-ensemble.yml` | **No** — comment only | Same as #4 (2 comment mentions). |
| 7 | `daily-price-refresh.yml.disabled` | **No** — inert | `.disabled` suffix, 0 `/audit` mentions. GitHub does not load it. |
| 8 | `meme-scanner-fixed.yml` | **No** | 0 `/audit` mentions, no FTP step, not a deploy workflow. |
| 9 | *(9th row of the `D` set — see §4)* | **No** | All 9 share: 0 `push:` triggers, 0 FTP/deploy/lftp/ftplib steps, 0 `/audit` writes. Verified per-file in §4. |

### 6.2 The 1 modification

| File (modified; `HEAD` differs from `origin/main`) | Any live `/audit` producer depend on it? | Rationale |
|---|---|---|
| `dynamic-alpha-engine.yml` | **No** — but it is the one row that is *not* a no-op | Not in the deploy set, no `/audit` writes. The delta is main 90 lines @115 vs HEAD 60 lines @112 — landing `HEAD` reverts a churn reduction. Zero `/audit` impact, but it is a **real content regression**, unlike the 9+2 which are renames/inerts. Do not bundle it with them: the "same blob on both sides" signal does **not** apply here (main `d2ec26fef7183ad3…` vs HEAD `c2dce7bb2d41a4f…`). |

### 6.3 The 2 renames

| File (renamed) | Any live `/audit` producer depend on it? | Rationale |
|---|---|---|
| `daily-price-refresh.yml` → `.disabled` | **No** — stays inert | Renaming to `.disabled`/`.retired` means GitHub never loads it. If the rename is what lands, behaviour is identical to the delete. |
| *(second rename, same pair class)* | **No** — stays inert | Same reasoning; both renames target a `.disabled`/`.retired` suffix. |

### 6.4 The one thing that would change this verdict

The verdict above is specific to **these 12 files**. It does **not** extend to other workflows in the fork that touch `/audit`:

- `deploy-competition-to-site.yml` — `push: branches: [main]` + `workflow_dispatch`, **no concurrency group**, and it does `mkdir -fp $REMOTE_BASE/audit; cd $REMOTE_BASE/audit`. If this resurrects, it becomes a live `/audit` writer on the very next push, racing `audit-dashboard.yml` and `deploy-fte-index.yml`.
- `deploy-fte-index.yml` — `push: branches: [main]` + dispatch, group `fte-ftp-deploy`, writes `/audit/`.

Neither is in the 12-file delta, so the current delta is safe. The risk lives next to it, not in it.

**Pre-push restatement:** the §5 guard is the operational form of this section — if `git diff --name-status HEAD origin/main -- .github/workflows/` returns 0 rows, §6's analysis is moot; if it returns rows, this table says which of them can be allowed to land (any, in isolation) and which must be checked against the deploy set first (anything named `deploy-*`, `audit-dashboard`, or `torontoevent-deploy-*`).
