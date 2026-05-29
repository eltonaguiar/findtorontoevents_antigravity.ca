# GitHub Actions + Repository Bloat Review — 2026-05-29

**Generated:** 2026-05-29T05:31Z  
**Reviewer:** Grok 4.3 (xAI)  
**Branch at time of review:** `fix/dashboard-spa-tooltip-money-ready`  
**Repo root:** `/home/eaguiar2015/findtorontoevents_antigravity.ca`

---

## Executive Summary (TL;DR)

| Metric | Value | Severity |
|--------|-------|----------|
| Registered workflows (GitHub) | 358 | **CRITICAL** |
| Workflow .yml files on disk | 356 | **CRITICAL** |
| Workflows with zero runs in last 300–500 runs | **178 (50%)** | **HIGH** |
| Largest tracked bloat: `ml_crypto_predictor/production_models/*.pkl` | 14 files, **318 MB** | **CRITICAL** |
| `.git` pack size | 6.72 GB (total `.git` 6.8 GB) | **CRITICAL** |
| Chronic failing workflows (last 200 runs) | Deploy Competition (5×), CI Tests (3×) | **HIGH** |
| Specific hard-failing jobs today | Strategy Health Monitor, Forward Test Daily, Deploy Competition | **HIGH** |

**Primary disease:** The repository has **massive binary bloat** from 14 production-grade ML model `.pkl` files (20–26 MB each) that are **still tracked in git** despite a `.gitignore` line existing. The files were committed *before* the ignore rule was added; git does not auto-untrack on `.gitignore` changes.

**Secondary disease:** 50% of the 358 GitHub Actions workflows are **dormant** (no executions in recent history). This creates an enormous cognitive load, maintenance surface, and hidden failure modes.

---

## 1. Workflow Inventory & Health

### 1.1 Raw Counts

- `ls .github/workflows/*.yml *.yaml` → **356 workflow definition files**
- `gh workflow list` → **358 registered workflows** (GitHub side)
- `.github/workflows/` directory size → **2.5 MB** (YAML itself is not the problem)

### 1.2 Dormancy Analysis (last 300–500 runs window)

**178 workflows (≈50%) have zero recorded runs** in the most recent 500-run sample pulled from the GitHub API.

**Sample of completely dormant workflows** (first 20 of 178):
- `2hour-challenge`
- `A/B Analysis + Zero-PnL Audit`
- `AI Hedge Fund Simulation — Weekly Pick Resolution`
- `AI Leaderboard Refresh`
- `AI Tournament Pipeline — Daily Picks + DB Ingest`
- `AI Tournament Price Tracker`
- `ALPHA ENGINE - Bond Emitter`
- `ALPHA ENGINE - Equity 52wk High Breakout Scanner`
- `Algorithm Competition Refresh`
- `Alpha Engine - Weekly Validation Suite`
- `Asset Class Freshness Watchdog`
- `AsterDEX Paper Trader (DISABLED)`
- `Audit Impact Tracker`
- `Auto-Retire — Daily Bleeder Check`
- `Automated Reporting`
- `BTCC Live Position Monitor (REAL MONEY)`
- `Backfill OHLCV Features`
- `Backup Restore Verification`
- `Battleground Mass Backtest`
- `Battleground Mass Backtest (Part 2 - Babies)`

**Interpretation:** These workflows were created, registered, and then abandoned. They represent **technical debt surface** — they can still be triggered manually or via `workflow_dispatch`, and any hidden bugs in them will only surface when someone finally clicks "Run".

### 1.3 Disabled Workflows

At least one explicit `(DISABLED)` marker exists (`AsterDEX Paper Trader (DISABLED)`). The GitHub `state` field for most entries still reports `"active"`.

---

## 2. Failing Workflows (Last 48h Evidence)

### 2.1 Chronic Offenders (last 200 runs)

| Workflow | Failure Count | Notes |
|----------|---------------|-------|
| **Deploy Competition to Live Site** | **5×** | Most chronic |
| CI Tests | 3× | Branch-specific + main |
| Branch Large File Duplicate Guard | 2× | Expected on feature branches with large files |
| Strategy Health Monitor | 1× (hard failure today) | See §2.2 |
| Forward Test Daily | 1× (hard failure today) | See §2.3 |
| Fast Trading Variants Master Scheduler | 1× | |
| FINDTORONTOEVENTS.CA Database Backups | 1× | |
| Mercury 2 Signal Scanner | 1× | |
| Claude Gainer ML Live Scanner | 1× | |
| Claude's Test - Portfolio Manager | 1× | |
| Audit Hourly Update | 1× | |
| Sports endpoint smoke + Playwright | 1× | |
| Swarm Pick Review | 1× | |
| Incidents + Enhancements — Nightly Page Render | 1× | Intermittent |

### 2.2 Strategy Health Monitor — Root Cause (run 26619871547)

**Error:**
```
TypeError: Object of type Decimal is not JSON serializable
File ".../strategy_health/monitor.py", line 305, in upsert_health
    json.dumps(snapshot)
```

**Location:** `strategy_health/monitor.py:305` (and caller at 393)

**Trigger:** The monitor queries closed trades, builds a snapshot dict containing `Decimal` objects (from SQL or `decimal` module math), then passes the raw dict to `json.dumps` without a `default=` handler or prior conversion.

**Status:** Hard failure every time this job runs until the serialization bug is fixed. No fallback path.

### 2.3 Forward Test Daily — Root Cause (run 26619837260)

**Error:**
```
python3: can't open file '.../STOCKS/competition/forward_test.py': [Errno 2] No such file or directory
```

**Diagnosis:** The workflow `forward-test-daily.yml` (or similar) still references `STOCKS/competition/forward_test.py`, but the file has been moved, renamed, or deleted. The workflow was never updated.

**Status:** Permanent failure until the path is corrected or the workflow is retired.

### 2.4 Deploy Competition to Live Site — Root Cause (multiple runs, e.g. 26619757931)

**Error (most recent):**
```
put: .../audit_dashboard/data/claudes_test_state.json: No such file or directory
```

**Context:** The deploy step does an `sftp` batch `put` of several files including:
- `audit_dashboard/data/claudes_test_state.json`
- `audit_dashboard/data/claudes_test_dashboard.json`

These files **exist locally** in the working tree (`audit_dashboard/data/`), but they are **not present in the runner checkout** for that particular run.

**Likely causes:**
1. A preceding step that is supposed to generate/regenerate them was skipped or failed silently.
2. The files are listed in `.gitignore` (or one of the many bloat-fix entries) and therefore not checked out on a fresh `actions/checkout`.
3. Race condition with the generator workflow.

**Evidence:** `ls audit_dashboard/data/claudes_test*.json` succeeds locally, but the runner `put` fails.

This workflow has now failed **5 times** in the last 200 runs — the single largest source of red X's.

---

## 3. Repository Bloat Audit (The 6.8 GB Problem)

### 3.1 Current Working Tree Largest Tracked Files

| Rank | Size | Path |
|------|------|------|
| 1–14 | 20–26 MB each | `ml_crypto_predictor/production_models/*_USDT_production.pkl` (14 files) |
| **Subtotal** | **≈318 MB** | **ML production models** |
| 15 | 11 MB | `events.json` |
| 16 | 11 MB | `next/events.json` |
| 17 | 3.5 MB | `updates/index.html` |
| 18 | 2.7 MB | `audit_dashboard/data/ai_tournament_picks_latest.json` |
| 19 | 2.5 MB | `alpha_engine/data/wrong_guesses_log.json` |
| ... | ... | (many 1–2 MB live state JSONs) |

**Top-level directory sizes (working tree):**
- `ml_crypto_predictor/` → **4.0 GB** (models + training artifacts)
- `alpha_engine/` → 180 MB
- `incubator/` → 141 MB
- `reports/` → 104 MB

### 3.2 The Smoking Gun: `ml_crypto_predictor/production_models/`

- 14 files × ~23 MB average = **318 MB**
- **Git status:** Explicitly tracked (`git ls-files` returns all 14)
- **Gitignore line exists** (line 226): `ml_crypto_predictor/production_models/*.pkl`
- **But `git check-ignore -v` returns "NOT IGNORED"** for the files

**Root cause:** Classic gitignore anti-pattern. The files were `git add`ed *before* the ignore rule was written. Adding a `.gitignore` entry never removes already-tracked files from the index.

**Commit history evidence:**
```
... production_models/ETH_USDT_production.pkl | Bin 0 -> 25876857 bytes
... (multiple large binary blobs introduced in same commit window)
```

These 14 blobs have been re-packed into the 6.72 GB pack file repeatedly.

### 3.3 Other Notable Bloat Sources Still Tracked

- `events.json` + `next/events.json` (11 MB each) — live event data, regenerable
- Many `*_live.json`, `active_picks.json`, `scan_*.json` variants (some have `!` negations, some don't)
- `alpha_engine/data/closed_picks*.json` and archives (multiple rounds of bloat-fix entries tried to catch these)
- `tools/data/snapshots/dashboard_data_*.json`
- Large PNG screenshots in `reports/kimi_edge_audit_*/`

The `.gitignore` file itself is now **667 lines** with 11+ iterative "bloat fix vN" comment blocks — evidence of repeated after-the-fact cleanups.

---

## 4. Impact Analysis — "What Happens If We Gitignore X?"

### 4.1 Scenario A: `git rm --cached` the 14 production `.pkl` files (318 MB)

**Immediate local effect:**
- Files disappear from `git ls-files` and future `git add -A` / `git commit -a`.
- Working tree files remain on disk (they are not deleted).
- Next commit will be dramatically smaller.

**Git history / remote effect:**
- **History is immutable.** The 6.72 GB pack file on GitHub will **not shrink**.
- Clone time for new users stays long until a history rewrite.
- `git clone --depth 1` users are unaffected for day-to-day work.

**To truly shrink the remote repository** one would need:
1. `git filter-repo` or `git filter-branch --tree-filter` (or BFG Repo-Cleaner) to rewrite history removing the blobs.
2. Force-push the rewritten branch(es).
3. **All open PRs, all developer forks, all CI caches, all local clones become invalid or require re-clone.**
4. GitHub may retain the old objects for some time (dangling objects).

**Risk:** Extremely high for a repo this large with many contributors/agents. A botched filter-repo can destroy work. Recommended only during a planned "repo reset" window with full team coordination.

**Recommendation:** Add the ignore (already done), `git rm --cached` the files in a dedicated "bloat cleanup" commit, document the history bloat as accepted technical debt, and rely on `--depth 1` clones + GitHub's CDN for day-to-day contributors. Do **not** attempt history rewrite unless the repo is about to be archived or forked for a clean v2.

### 4.2 Scenario B: Gitignoring the 11 MB `events.json` / `next/events.json`

**Low risk.** These are clearly runtime artifacts (events scraped for the live site). They have production consumers but are overwritten constantly. The live site reads from FTP-deployed copies anyway.

**Action:** Ensure the `!` negation rules that exist for a few critical live JSONs (`live_competition.json`, `super_signals.json`, etc.) are complete. If `events.json` is needed by a deploy step that runs on the runner, add a targeted negation or generate it in the workflow before the deploy step.

### 4.3 Scenario C: Gitignoring more "live state" JSONs (`active_picks*.json`, `scan_log.json`, etc.)

**Medium risk.** Many of these already have broad ignore patterns with specific negations for files that **must** be present in a fresh `actions/checkout` for deploy or competition workflows.

**Current pattern in .gitignore (v6–v8):**
```
**/data/active_picks.json
...
!KIMI_RISEOFTHECLAW/data/active_picks.json
!cross_aggregation/data/super_signals.json
...
```

This is the correct approach. The danger is **incomplete negation lists** — a new deploy workflow is added that consumes a file that is now ignored, causing exactly the "Deploy Competition" class of failure we saw today.

**Recommendation:** Before adding any new broad `**/*_live.json` or `**/data/scan*.json` pattern, audit every workflow that does `actions/checkout` followed by an FTP/S3/rsync step and enumerate the exact files it expects to be present.

### 4.4 Dormant Workflow Impact

**Cost:** Near-zero direct compute (they don't run on schedule).  
**Cost:** Very high **human + agent** context switching and accidental triggering.

Every dormant workflow is:
- A potential vector for secret leakage if it has overly broad permissions.
- A source of confusion ("did this job ever work?").
- A maintenance burden when shared libraries or DB schemas change.

**Recommended action:** Create a `DECOMMISSIONED/` directory (or move to `.github/workflows/decommissioned/`) and/or add a top-of-file comment block:

```yaml
# DECOMMISSIONED 2026-05-29 — no runs in 90+ days.
# If you need to revive this, move it back to ../ and update schedules/secrets.
```

Then delete or heavily comment out the `on:` triggers so they cannot be accidentally dispatched.

---

## 5. Other Hygiene Issues Observed

1. **Workflow YAML bloat:** 356 files × average ~7 KB = 2.5 MB of YAML. Not fatal, but the directory is hard to navigate. Consider grouping related families into subdirectories if GitHub Actions ever supports that (currently it does not — all must live at `.github/workflows/`).

2. **Inconsistent naming:** Mix of `alpha-engine-*.yml`, `ALPHA ENGINE *.yml`, `ml-battleground-*.yml`, `ML Battleground *.yml`. This makes regex-based cleanup or bulk operations error-prone.

3. **Missing artifact dependency declaration:** The "Deploy Competition" workflow assumes certain JSON files will exist because a previous scheduled job ran. There is no `workflow_run` trigger or `needs:` guard ensuring the generator actually succeeded.

4. **Python deprecation warnings** in Strategy Health Monitor (uses `datetime.utcnow()`). Minor, but adds noise to every run log.

5. **No central "workflow health" dashboard.** The repo has many watchdog jobs but no single place that says "X of 358 workflows are currently healthy."

---

## 6. Recommended Immediate Actions (Prioritized)

| Priority | Action | Owner | Risk if Ignored |
|----------|--------|-------|-----------------|
| P0 | `git rm --cached ml_crypto_predictor/production_models/*.pkl` + commit the removal | Core | Every future push continues to bloat history by ~300 MB |
| P0 | Fix `strategy_health/monitor.py:305` — add `default=str` or `Decimal` encoder to `json.dumps` | Quant Eng | Strategy Health Monitor remains red permanently |
| P1 | Fix or delete `forward_test.py` reference in Forward Test Daily workflow; or retire the workflow | Stocks/Competition | Permanent red X |
| P1 | Make "Deploy Competition to Live Site" either (a) generate the missing `claudes_test_*.json` itself or (b) guard the `put` with `if [ -f ... ]` + warning instead of hard failure | Deploy | 5+ failures/week |
| P2 | Move 100+ dormant workflows to `decommissioned/` or add `# DECOMMISSIONED` header + comment out `on:` triggers | Maintenance | Cognitive load, accidental triggers |
| P2 | Audit all `workflow_run` / `actions/checkout` + FTP deploy steps for files that are now gitignored | CI | More "file not found on put" incidents |
| P3 | Add a weekly "GHA Health" job that reports % of workflows that have run successfully in last 7 days | Observability | No visibility into the 50% dormant problem |

---

## 7. Appendix — Raw Data Sources

- `gh workflow list --json name,state,id,path` (358 entries)
- `gh run list --limit 500` (multiple pulls, 2026-05-29 04:00–05:30Z window)
- `git ls-files | xargs ls -lh | sort -k5 -rh` (top 50 tracked)
- `du -sh ml_crypto_predictor/production_models` (318 MB)
- Individual `gh run view <id> --log-failed` for:
  - 26619871547 (Strategy Health Monitor)
  - 26619837260 (Forward Test Daily)
  - 26619757931 (Deploy Competition)
- `.gitignore` (full 667-line file with v1–v11 bloat fix history)

---

**End of report.**  
Next review recommended in 30 days or immediately after the P0 bloat-removal commit.

---

## 8. Hidden Warnings, Errors & Systemic Masking — Deep Dive (2026-05-29)

This section was added after the user requested a second pass specifically looking for **hidden** warnings/errors and the dedicated "job health status" workflows.

### 8.1 The Primary "Job Health Status" Workflow

**File:** `.github/workflows/actions-failure-guardian.yml`

- **Schedule:** Every 30 minutes (`*/30 * * * *`)
- **Purpose:** Explicitly "monitors failed GitHub Actions and automatically retries them". It is the closest thing this repo has to a central job health radar.
- **What it actually does:**
  - Fetches recent runs via GitHub API (600 runs / 359 workflows in the latest execution).
  - Identifies "unresolved failures" (latest run on a workflow+branch is a failure with no newer success).
  - Attempts to trigger `rerun` on those runs when possible.
  - Also detects chronically cancelled workflows and stale data files.
  - Writes a detailed report to `reports/actions_failure_guardian.json` and commits it.

**Latest execution evidence (run 26618919478, 2026-05-29T04:58Z, conclusion=success):**

From the live `reports/actions_failure_guardian.json` (1687 lines):
- 15 unresolved failures detected
- Auto-rerun **attempted** on (among others):
  - Swarm Pick Review (resolve + weekly + patterns...)
  - Deploy Competition to Live Site
  - Claude Gainer ML Live Scanner
  - Mercury 2 Signal Scanner
  - CI Tests
- 160 stale workflows flagged (names match the dormant list from the first half of this review)
- 2 badly stale data files:
  - `claude_gainer_ml/tracker/short_term_active.json` (79.5h old)
  - `battleground/data/active_picks.json` (79.6h old)
- 1 disabled workflow explicitly called out: "Send Morning Goal Follow-Ups (disabled)"

**Important observation:** The guardian job itself reporting **success** does **not** mean the fleet is healthy. It means "the detector ran and wrote a report." The real health signal lives inside the JSON artifact.

### 8.2 Other Dedicated Health / Watchdog / Audit Workflows

| Workflow File | Display Name | Schedule | Last Known Status | Notes |
|---------------|--------------|----------|-------------------|-------|
| gha-stale-workflows-audit.yml | GHA stale workflows audit | Daily 05:30 UTC | Success (2026-05-28) | Calls `tools/find_stale_github_workflows.py` (30-day threshold) + sparse-safe push checker |
| gha-summary-report.yml | gha-summary-report | Every 6 hours | Success (recent) | Full fleet HTML + JSON report generation + FTP deploy of `reports/gha_actions_summary.*` |
| db-freshness-guardian.yml | DB Freshness Guardian | Hourly + push on the checker script | Mixed (has `continue-on-error: true`) | Explicitly documents that exit code 1 = YELLOW (warning only), 2 = RED |
| strategy-health-monitor.yml | Strategy Health Monitor | (presumably scheduled) | Hard failure today (Decimal JSON bug) | One of the few that still fails hard |
| asset-class-freshness-watchdog.yml | Asset Class Freshness Watchdog | ? | Never run in recent windows | Dormant despite name |
| ml-staleness-watchdog.yml, tv-paper-tpsl-watchdog.yml, etc. | Various narrow watchdogs | Varies | Mixed | Many are narrow in scope |

The `gha-stale-workflows-audit` and `gha-summary-report` are the two secondary "fleet health" jobs. Both appear to be functioning (their own runs succeed).

### 8.3 The Real Problem: Systemic "Green Job" Masking Culture

A broad `grep -r continue-on-error .github/workflows/` returned **hundreds of occurrences** across dozens of workflow files. This is not occasional defensive usage — it is a pervasive design pattern.

**Examples of heavy users (partial list):**
- `audit-dashboard.yml` — dozens of `continue-on-error: true` (one comment explicitly says it was flipped from `true` to `false` after a "Kimi audit" on 2026-05-20 because silent failures were hiding resolver bugs)
- `alpha-engine-live.yml` — many steps wrapped
- `sports-betting-refresh.yml` — extremely heavy use; multiple comments state "so a failure never blocks picks" and "every scheduled run so PM context tracks live odds"
- `ai-tournament-pipeline.yml` — 15+ `continue-on-error` + `|| echo "::warning title=..."`
- `copy-trader-intelligence.yml`, `social-prediction-tracker.yml`, `refresh-stocks-portfolio.yml`, `meme-scanner-v2.yml`, `worldclass-pipeline.yml`, etc.

**Typical pattern observed in many files:**
```yaml
- name: Do important thing
  continue-on-error: true
  run: |
    python do_thing.py || echo "::warning title=thing_failed::do_thing.py failed — downstream will be stale"
```

**Consequence for the guardian:**
Because the step never fails the job, the overall workflow conclusion is often still `success` or `skipped`. The actions-failure-guardian (which only looks at `conclusion` in `BAD_CONCLUSIONS`) therefore never sees these as "unresolved failures" even when critical data is missing or stale.

This explains the gap between "guardian only sees 15 unresolved" and the lived experience of many red X's + known broken flows.

### 8.4 Explicit ::warning:: Annotations (Intentional Hiding)

Dozens of workflows deliberately emit `::warning::` (and sometimes `::error::` that still doesn't fail the job) so that the GitHub UI shows a yellow triangle instead of a red X.

Notable concentrations:
- `ai-tournament-pipeline.yml` — almost every major sub-step has a warning fallback title
- `sports-smoke-and-e2e.yml`, `quant-auditor-deep-nightly.yml`, `claudes-test-portfolios.yml`
- Many FTP deploy steps across the fleet

These warnings are **not bugs** — they are the designed escape hatch so that expensive scheduled jobs (some with 360-minute timeouts) do not turn red on every transient FTP hiccup, missing optional secret, or third-party scraper blip.

### 8.5 Fleet-Wide Deprecation Warning Already Leaking Into "Success" Runs

In the most recent `actions-failure-guardian` run (itself green), the log ended with this GitHub-provided warning:

```
##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/checkout@v4, actions/setup-python@v5. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. ...
```

This warning will appear in **every** workflow that still uses the v4/v5 pinned actions once the June 2 cutoff hits. With 356 workflow files, this is a looming fleet-wide yak shave.

No workflow in the current corpus appears to have `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` or the newer action versions yet.

### 8.6 Recommendations Specific to Hidden / Masked Issues

| Priority | Finding | Recommended Action |
|----------|---------|--------------------|
| P0 | Pervasive `continue-on-error` on data-generating steps | Audit the top 10 heaviest users (audit-dashboard, alpha-engine-live, sports-betting-refresh, ai-tournament-pipeline). For each critical data file they produce, decide: "must this step be green for downstream consumers, or is stale data acceptable?" Flip the ones that matter back to hard-fail. |
| P1 | Guardian only sees "job level" failures | Enhance `actions_failure_guardian.py` (or add a companion job) to also parse step-level logs or look for `::warning title=...` patterns that indicate known-bad data states. Surface "green but lying" jobs. |
| P1 | Node 20 deprecation arriving 2026-06-02 | Create a one-time "Node 24 readiness" PR that bumps `actions/checkout` and `actions/setup-python` (and any other Node-based actions) across the fleet, or adds the opt-in env var as a stop-gap. |
| P2 | `gha-stale-workflows-audit` and `gha-summary-report` are good but narrow | Consider wiring their outputs (the JSON they produce) into the existing `actions_failure_guardian.json` or a single "GHA Fleet Health" dashboard page so operators have one place to look. |
| P2 | Many `::warning::` emissions have no follow-up | Add a weekly job (or extend the guardian) that counts `::warning::` occurrences in the last 24–48h of logs and fails (or alerts) if the count exceeds a threshold. This turns the current "we know it's yellow but we ignore it" into actionable signal. |
| P3 | `workflow_health_check.py` / `.sh` only exist in old worktrees | Either promote the best version into `scripts/` (or `.github/scripts/`) under version control, or delete the copies so future agents don't get confused. |

### 8.7 Bottom Line on "Hidden" Issues

The repo does **not** lack health monitoring — it has at least 4–5 dedicated watchdog/guardian/audit jobs.

What it **does** have is a deeply entrenched engineering culture of "make the job green even when the important thing inside it failed," implemented via `continue-on-error: true` + `|| echo "::warning::..."` on hundreds of steps.

The `actions-failure-guardian` is correctly reporting the failures it can see. The much larger invisible problem is the set of jobs that are **designed** to never surface their real problems to the guardian (or to any human looking at the Actions tab).

Until the masking pattern is systematically reduced on data-critical paths, any "job health" dashboard will continue to under-report the true operational pain.

---

**End of hidden-issues addendum.**  
Appended 2026-05-29 after follow-up request for deeper warning/error sweep.