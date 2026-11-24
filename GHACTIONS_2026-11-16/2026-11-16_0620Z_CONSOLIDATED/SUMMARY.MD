# GH Actions multi-worktree — CONSOLIDATED REVIEW & PRIORITIZED FIXES

**Stamp:** 2026-11-16T06:20Z · **origin/main HEAD at write:** `d929cb577aa`
**Worktrees reviewed:** `ghactions` (v1) · `ghactions-v2` (this) · `ghactions-v3` · `ghactions-v4`

Purpose: reconcile what all four GH-Actions agents did, what's merged vs pending, and the remaining
prioritized code fixes. Docs for every finding live under `GHACTIONS_2026-11-16/<timestamp>_*/`.

---

## 1. What each worktree did

| WT | Branch | Focus | Key merged fixes |
|---|---|---|---|
| **v1** | `ghactions` | Audit/picks correctness | *PENDING branch (not merged):* FOREX live hard-disable read, VIX rule combos, ETF SHORT class gate, whole-ledger card, "un-lie freshness tiles", VIX forward-n test. |
| **v2 (this)** | `docs/alpha-verify-2…` (fixes merged) | ALPHA/push infra + dashboard truth | **#811/#813/#829** ALPHA commit step (5→15m cap, then `safe_push.sh` to kill the *hang*) · **#815** disable dup ROOCODE backtest · **#825** CI cron-tests minute-tolerant · **#828** dashboard ghost-rows contradiction · **#832** push-hygiene audit + migrate 2 high-cadence pushers · PRs #819/#820 branch+jobstate audits. |
| **v3** | `fix/gha-cron-regime-hardening` | Cron inversions + queue + commit hardening | **#814 / 9b2bf9f** cron inversions: `audit-dashboard` hourly→3-hourly, `dynamic-alpha` 30-min→2-hourly · purged **29/51 phantom queued runs** · *PENDING:* `safe_push` hardening of regime-terminal / audit-impact / ueps commit steps. |
| **v4** | `fix/gha-disable-broken-workflows` | Queue audit + DB quality + feed health | **04a30246** CDP queue-audit normalization + best-practices · **f107b7d** feed-health: shadow PM sources → warning (was the one real main failure) · `gha_latest_run_check.py` 360-workflow sweep · deep DB-quality report. |

**Merged to main:** all v2 fixes; v3 cron fix; v4 queue-audit + feed-health.
**Pending branches (not merged):** v1 (audit/picks), v3 (`safe_push` hardening of 3 more workflows).
**No file conflicts found** between worktrees (v3/v2 touched different workflows; v1 touches template/engine
away from my 1-line `L911` edit).

## 2. Reconciled state of the fleet (as of 06:20Z)
- **~~No active broken workflow~~ → one exception:** `Feed Health Check` failed 04:48Z (shadow PM feeds) — **fixed by v4** `f107b7d`.
- **CI Tests RED since 05:27Z** — `ImportError: audit_trail.dashboard_generator not in sys.modules` (~20 tests/5 files). Latest main **compiles + imports OK locally** ⇒ order-dependent/transient; co-fires with v4 `f107b7d`. **See P2.**
- **ALPHA commit step:** old inline `git pull --rebase … 2>/dev/null` **hung** the whole 15-min step (run 43799911205). Now uses `safe_push.sh` (my #829) **and** peer raised cap to 30m — belt-and-suspenders. Post-#829 outcome verification queued (cron now 2-hourly; next ~08:13Z).
- **Cron herd:** peer staggered 310 crons + fixed 2 inversions. Healthy.

## 3. PRIORITIZED remaining code fixes

### P1 — data integrity feeding `/audit` (highest business impact; from v4's DB audit)
1. **Frozen resolution lanes** (silent, months): `trading_picks.intrabar_resolved_at` frozen **2026-06-09** (5mo); `lm_signals.resolved_at` frozen **2026-02-16** (9mo, 110,985 rows expired≠resolved). → fix the resolver schedulers / `tools/db_freshness_check.py` thresholds; re-run resolution.
2. **PnL-poison rows**: 2 closed rows dominate class aggregates — `SHIBUSDT` pnl **1,000,000%**, `ARBUSDT` **18,611%** (bad entry/exit). → cap at source (|pnl|>100% → quarantine) in the pick-ingest / resolver, not just dashboard capping.
3. **Open-row bloat**: `trading_picks` **91,855 OPEN vs 21 ACTIVE** (63.5%; 74,394 >30d). `at_local_picks` **108M ACTIVE rows / 13.8 GB**. → archival/expiry job + stop emitting unresolvable opens (worst: multi_asset_copytrader 25,231, non_crypto_consensus 14,408).
4. **Duplicates + degenerate geometry**: 14,568 dup groups → **105,669 excess rows**; **2,688** impossible TP/SL in trading_picks (5,808 in at_raw_picks); 1,810 inverted `closed_at`. → dedup on `(symbol,direction,strategy,DATE(created_at))`; add geometry validation at ingest.

### P2 — CI/observability & runner hygiene
5. **CI Tests red (05:27Z)** — root-cause the `dashboard_generator not in sys.modules` (likely conftest/`sys.modules` isolation after v4 `f107b7d`; module imports fine standalone). Files: `tests/test_derive_asset_class_precedence.py` + conftest. → fix isolation or mark order-dependence; re-run.
6. **Branch Large File Dup Guard = 0/15 (v3: "highest-value remaining fix")** — global concurrency group + a **2–3 h all-213-branch scan** capped at 180m ⇒ every run cancels; provides zero protection while holding a runner. Options: (a) scan only the pushed ref (fast), (b) per-ref group + scan-scope reduction, (c) disable it (currently zero-value). File: `.github/workflows/branch-large-file-dup-guard.yml`. **Owner decision — don't blind-change (deliberate global design).**
7. **27 remaining inline-push workflows → `safe_push.sh`** (my PUSH_HYGIENE backlog): same hang class as ALPHA. Migrate high-cadence first: `picks-now-refresh`, `daily-top-picks-filter`, `alpha-engine-etf`, `sports-smoke-and-e2e`.
8. **Zombie `Master Automation Scheduler`** — all 3 job groups skip every fire; looks green but schedules nothing (v4). → fix its cron-literal gates or delete.
9. **21 phantom queued runs** (v3) — API can't purge (409/403); all from one 2026-11-11 stampede; P3 cosmetic → GitHub Support ticket.

### P3 — cleanup / decisions
10. **19 never-run workflows** (v4) — archive→observe→delete (7 are intentionally-disabled sports).
11. **Dashboard decision items** (v2): PM `whale/kalshi` signals gitignored+ephemeral (commit-or-drop); **23/24 `WIRED_IN` dirs unwired**; AsterDEX `daily-summary` dead gate (needs Discord-post OK); Money-Ready box self-healed.
12. **79 no-timeout workflows** (v2) — canary-wave `timeout-minutes` rollout (APPROACH.md §6).
13. **`Discord Bot — Persistent`** — 24/7 runner by design; owner keep-vs-stop.
14. **ALPHA `safe_push` outcome** — verify first post-#829 2-hourly run (queued ~08:13Z).

## 4. Where the files are
All deliverables: `findtorontoevents_antigravity.ca/GHACTIONS_2026-11-16/<UTCstamp>_<topic>/` on `main`.
| Topic | Folder |
|---|---|
| Approach/best-practices playbook | `2026-11-16_02-55Z_approach_and_playbook/APPROACH.md` |
| ALPHA hang/verification | `2026-11-16_03-45Z_alpha-fix-verification/VERIFICATION.md`, `04-45Z_alpha-safe-push/FIX.md` |
| Push-hygiene audit + backlog | `2026-11-16_05-20Z_push-hygiene/PUSH_HYGIENE.md` |
| Dashboard deep-check (ghost-rows, boxes, PM) | `2026-11-16_04-10Z_audit-dashboard-deepcheck/DASHBOARD_DEEPCHECK.md` |
| Branch audit / job-state | `2026-11-16_03-00Z_branch-audit/`, `03-02Z_jobstate-sweep/` |
| Deep-check (fleet) | `2026-11-16_04-05Z_deep-check/DEEP_CHECK.md` |
| Peers: cron+queue+DB-quality | v3 `GHACTIONS_2026-11-16/{TODO.md,ACTION_PLAN.md,2026-11-16_2030_EST_REPORT.md}` · v4 `2026-11-16_05-35Z_stale-jobs-and-db-quality/` |
| **This review** | `2026-11-16_0620Z_CONSOLIDATED/SUMMARY.MD` |

## 5. Do-not-reopen (recorded so peers don't thrash)
- 190 sampled 24h "failures" had later success (noise). Historical "97-98% fail" = concurrency-slot replacement, `jobs_executed=0`.
- 7 `disabled_manually` sports/ai-tournament workflows = intentional (owner call) — don't re-enable.
- Mass identical-timestamp cancellations across unrelated workflows = external cleanup, not self-churn — don't edit their concurrency.
- `on: {}` is INVALID GHA (use `*.yml.disabled`).
