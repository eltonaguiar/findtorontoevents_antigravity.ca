# GHActions / PR / Issues Review Report

**Repo:** eltonaguiar/findtorontoevents_antigravity.ca
**Review time:** 2026-11-15T07:34 UTC
**Worktree:** wire-fix-ghactions-pr-issues
**Output folder:** `GHACTIONS_PR_ISSUES/2026-11-15T0734Z_gh-actions-pr-issues-review/`

---

## 1. Executive Summary

| Domain | Count | State |
|--------|-------|-------|
| GitHub Actions workflows | ~210 files in `.github/workflows/` | ~157 active with cron, 16 disabled/retired/draft |
| Open Pull Requests | 36 | 2 newest are wired-in CI fixes (today); 34 stale (Oct/Jun 2026) |
| Open Issues | ~80 | Dominated by recurring `backup-verify` spam (5 new today, monthly cadence) |
| WIRED_IN submissions | ~23 dated folders | All converge: no active strategy has a proven edge |
| Profitability verdict | — | **Active-alpha track is NOT on the right track; only low-cost passive beta is defensible** |

---

## 2. GitHub Actions Inventory

### 2.1 Workflow counts
- Active workflows with cron schedules: **157** (from `workflow_analysis.txt`)
- Disabled/retired/draft: **16** (`*.disabled`, `*.retired`, `*.draft`)
- Total `.yml` workflow files: ~173

### 2.2 Notable active workflows reviewed

| Workfile | Key observation |
|----------|-----------------|
| `alpha-engine-daily-picks.yml` | Deploys picks to live site via **plain FTP** with `ssl:verify-certificate no`. Embeds FTP creds in step env. Sparse-checkout only `.github` + `alpha_engine`. Runs `python -m alpha_engine.main`. |
| `equities-agent.yml` | `contents: write` permission; commits `equities_picks.json` to main; uses `safe_push.sh`. Pulls `EQUITY_SYMBOLS` from `alpha_engine/config`. Zero picks currently emitted (`status: "EMPTY"`). |
| `gainer-predictor.yml` | Every 30 min; commits gainer data; retries push 3x with 5s sleep (no backoff). |
| `forward-test-new-strategies.yml` | Every 6h; `git pull --rebase origin main` then `safe_push.sh` (rebase race risk with concurrent workflows). |
| `backup-verify.yml` | **Root cause of issue spam.** Runs monthly (15th, 06:00 UTC). Opens a NEW GitHub issue on every failure with NO dedup against existing open `backup-verify` issues. 5 new issues today alone (06:03–07:34). |

### 2.3 Disabled / retired / draft (16)
`alpha-engine-bond.yml.disabled`, `alpha-suite-daily-refresh.yml.disabled`, `deploy-pages.yml.disabled`, `fast-variants-master.yml.disabled`, `forward-test-daily.yml.disabled`, `bt-backtest-trades-sync.yml.draft`, and 10 `*.retired` ml-battleground/paper-trading/rl-agent files.

### 2.4 Recent failed workflow runs (2026-11-15)
Repeated failures on `main`: "Sports endpoint smoke + Playwright", "QA Market Validation", "Mirror", "Verified pilot daily", "Backup Restore Verification". Plus repeated "CI Tests" failures on `wired-in/buffy-2026-11-15` branch.

---

## 3. Open Pull Requests (36)

Two newest (today, 2026-11-15):
- **#786** `fix(ci): restore QA price validation, snapshot pushes, and sports smoke` — `wired-in/buffy-gh-actions-fix-2026-11-15`
- **#785** `Restore audit page script tags lost on main + tracker horizon fix` — `wired-in/buffy-2026-11-15-final`

Remaining 34 are stale (Oct 2026 back to Jun 2026), all fix/feat/docs branches authored by eltonaguiar, none merged. Most are CI/infra fixes (FTP creds, BTC guard, resolver, audit empty-state, blacklist, stale tags, secret rotation).

---

## 4. Open Issues (~80)

### 4.1 Dominant pattern: `backup-verify` spam
New `backup-verify` Restore check FAILED issues opened **every month on the 15th**, multiple times per day today:
- 2026-11-15: #780, #781, #782, #783, #787 (5 issues, 06:03–07:34)
- 2026-10-15: #721–#728 (8 issues)
- 2026-09-15: #686–#694 (9 issues)
- 2026-08-15: #676–#684 (9 issues)
- ...and back to 2026-06-15.

**Root cause:** `backup-verify.yml` step "Open failure issue" creates a new issue on every failure with no check for an existing open issue with the same title/label. → issue spam.

### 4.2 Other notable open issues
- **#748** Production resolver predates `_priceless_close` → `exit_price=0.0` flat closes in `recent_closed` (2026-10-20)
- **#764** [Security] Monthly Secret Rotation Reminder — November 2026 (and Sep/Oct/Jul/Aug — recurring monthly)
- **#654** Weekly event gap scan DEGRADED (scrapers blocked, 56/10614 events)

---

## 5. What Needs to Be Fixed (GHActions/PR/Issues)

### Fix 1 — `backup-verify.yml` issue spam (P0)
**Problem:** A new issue is opened on every monthly failure with no dedup. 5 issues today alone.
**Fix:** Before creating an issue, search open issues with label `backup-verify` and title containing "Restore check FAILED — <today's date>"; if one exists, comment on it instead of creating a new one. Close resolved issues on success.
**File:** `.github/workflows/backup-verify.yml` (add a deduplication step using `gh issue list` / `github-script`).

### Fix 2 — Plain FTP without certificate verification (P0)
**Problem:** `alpha-engine-daily-picks.yml` deploys picks via FTP with `ssl:verify-certificate no` and FTP creds exposed in step env.
**Fix:** Switch to FTPS with certificate verification, or move deploy to the existing `deploy-vetted-picks.yml`/`safe_push.sh` git-based pattern. Never log FTP creds.
**File:** `.github/workflows/alpha-engine-daily-picks.yml`

### Fix 3 — Concurrent push rebase races (P1)
**Problem:** `forward-test-new-strategies.yml` and `equities-agent.yml` both push to main via `safe_push.sh` with `git pull --rebase -X theirs`. Multiple workflows on 6h/12h schedules collide.
**Fix:** Add a `concurrency` group with `cancel-in-progress: true` to push-heavy workflows (like `equities-agent.yml` already has). Serialize main pushes.
**Files:** `forward-test-new-strategies.yml`, `gainer-predictor.yml`

### Fix 4 — Stale PR hygiene (P2)
**Problem:** 34 open PRs dating back to Jun 2026 are abandoned/stale.
**Fix:** Close or rebase the stale PRs; keep only the two wired-in CI fixes (#785, #786) active.

---

## 6. WIRED_IN Review (Profitability Track)

**Folder:** `WIRED_IN/` — dated submissions, one per worktree, answering 4 questions (algorithm spec, pick justification, backtest/research, elimination). Convention: additive only, reproducible numbers, "a well-evidenced NO is valid."

### 6.1 Submissions reviewed
| Folder | Worktree | Core conclusion |
|--------|----------|-----------------|
| `2026-11-15_0125/finpredict-v4/` | finpredict-v4 | Faber 200d MA + defensive rotation; live picks VTI/TLT/SGOV/BND; risk-adjusted win but **worse wealth vs SPY**; 0/11 proof-protocol |
| `2026-11-15_0128_buffy/` | buffy | 0/8 rules beat benchmark; beta core 10.76%/yr DSR 0.99; **no edge over buy-and-hold** |
| `2026-11-15_AM_profitability_plan/` | (main) | **0/37 combos passed money-ready gates**; all 9 asset classes `sizing_allowed: false`; recommend low-cost index ETF/MF passive allocation |
| `2026-11-15T0700Z_scratch-hippodraco/` | scratch-hippodraco | **Zero asset classes pass all 10 proof gates** |

### 6.2 Subagent verification (independent, 5 subagents)

All subagent findings confirm the WIRED_IN conclusions:

1. **Artifact reproducibility** ✅: `tools/sim_path_forward.py` and `tools/forward_tracker.py` compile and run; buffy headline numbers (FABER10_SPY 8.33% CAGR DSR 0.99; BH_SPY 10.76% DSR 0.99; RSI2_SPY 0.21%; 2× cost stress) reproduced exactly. Blocker: no pre-shipped `data/cache/sim/` (needs Yahoo API network).

2. **Equity** ❌: 0/7 gates passed; all strategies negative after costs; Faber worse wealth vs SPY; zero forward-validated equity picks; `equities_picks.json` status `EMPTY`. **Verdict: shadow/paper-only, do not deploy.**

3. **Crypto** ❌: BTC_TREND200 best result but DSR 0.84 < 0.95 bar; SPY-relative excess is crypto beta not skill; zero forward trades (clock started today); CRYPTO_AUDIT: zero strategies pass all 10 gates. **Verdict: shadow/paper-only, do not deploy.**

4. **Bonds & ETF** ❌: No standalone alpha; all excess negative; proof protocol failed; 200dma TLT/BND kill rule not implemented as live guard. **Verdict: do not deploy.**

5. **Prediction markets** ❌: Structurally rejected (zero-sum, bot dominance, adverse selection, taker fees 3.5–6.3% of stake, no measured class, PBO 0.603). **Verdict: shadow only as data source, reject as trading venue.**

---

## 7. Overall Profitability Verdict

**Are we on the right track to profitability? No — not as an active-alpha strategy.**

- **No asset class passes the proof protocol** (0/11 for Faber; AM plan: zero asset classes passed money-ready gates).
- **No active strategy beats its benchmark (SPY for equity, BTC for crypto) after costs on clean data.**
- **The only defensible deployment is low-cost passive beta** (VTI/VXUS/BND 60/20/20) outside the prediction system, per the `active_strategy_benchmark_requirement` constraint.

**Recommended direction:** Shift all active strategies to shadow/paper-only with pre-registered kill rules; deploy nothing to live capital until an asset class passes all 10 proof gates after costs. The Faber/buffy survivors are drawdown-risk-controls on beta, not alpha.

---

## 8. Fix Documents

See `fixes/` subfolder for per-fix documentation:
- `fixes/FIX-001-backup-verify-issue-dedup.md`
- `fixes/FIX-002-ftp-cert-verification.md`
- `fixes/FIX-003-concurrent-push-serialization.md`
- `fixes/FIX-004-stale-pr-hygiene.md`

---

## 9. Actions Taken (2026-11-15 follow-up)

### 9.1 Stale PRs closed
Closed **34 stale PRs** (#562–#766) with a pointer to this review; superseded or abandoned. Open PRs reduced from 36 to 2 active (my #790 + a peer's #788; #785/#786 were merged/closed externally during the session).

### 9.2 Fixes applied — PR #790 (`fix/gha-backup-verify-dedup-2026-11-15`)
| Fix | File | Change |
|---|---|---|
| FIX-001 | `.github/workflows/backup-verify.yml` | Dedup: comment on existing open `backup-verify` issue for today instead of creating a new one each failure. |
| FIX-003 | `.github/workflows/forward-test-new-strategies.yml` | Added `concurrency` group; removed redundant manual `git pull --rebase` (safe_push.sh handles it). |
| FIX-005 | `.github/workflows/sports-smoke-and-e2e.yml` | Pinned `smoke` job to `ubuntu-24.04` — Playwright 1.58.2 does not support Ubuntu 26.04. |
| enhancement | `tools/run_verified_pilots_daily.py` | Print + persist `failed_steps` so the CI log names which pilot broke (additive; no pass/fail change). |

Verified: all changed workflows parse with `yaml.safe_load`; `tools/run_verified_pilots_daily.py` passes `py_compile`.

### 9.3 Failing jobs intentionally NOT forced green
| Job | Why left failing | Owner action |
|---|---|---|
| QA Market Validation | 191 critical flags are **real** (93 UNPRICED blank fields + 98 FOREX MISMATCH). Suppressing would let unvalidated PnL through. | Fix producer (blank `current_price`/`pnl_pct`) + reconcile FOREX quote source. See FIX-006. |
| Verified pilot daily | One of 17 paper-pilot sub-steps returns non-zero (real signal, `ok=False`). | Use the new `failed_steps` field to identify and fix the failing pilot. |
| Mirror | FTP flakiness on 50webs/GoDaddy (environmental). | Infra/retry work; cert verification also disabled (`ssl:verify-certificate no`). |
| CI Tests (branch) | Belongs to a feature branch PR, not main. | Addressed in that PR. |

*End of report.*