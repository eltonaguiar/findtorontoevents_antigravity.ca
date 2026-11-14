# INFRA / CI Consolidated Review

**Sources consolidated (5 peers):**
- **V2** (Subagent A — GitHub Actions health; CI_GATES; P0_QUICK_WINS P0-1/3/4/8/9; Subagent F — sources)
- **V3** (GLOBAL_QUICK_WINS — CI/workflow parts)
- **V4** (actions_health_report.md; proposed_fixes/infra/QUICK_WINS.md; INDEX.md — SQLite/MySQL/JSON divergence)
- **ML** (childlike-airport FIX_PROPOSED.md — DB divergence parts)

Snapshot times differ (V2 ~16:05Z, V4 ~15:52Z, live payload ~14:30Z), which explains small count deltas.

---

## 1. Consensus (all/most peers agree)

| # | Finding | Evidence |
|---|---------|----------|
| C1 | **365 GitHub workflow files** (361 active, 4 `disabled_manually`) | V2 A §1; V4 §Summary |
| C2 | **~28 workflows failing** their latest run (V4: 28; V2: 25 last-run-failed / 24 failing in 24h — snapshot delta, see Conflicts) | V4 §Recent Failures; V2 A §1 |
| C3 | **Python 3.14 masquerade** via `update-environment: false` in **197 files**; `actions/setup-python` pins `python-version: 3.11` but the flag suppresses PATH/env mutation, so jobs resolve the system interpreter (3.14) and `pandas==2.1.4` compiles from sdist → `_PyLong_AsByteArray expected 6 args, have 5` | V2 P0-3; V2 A §2 (≥9 workflows) |
| C4 | **`audit-dashboard.yml` cancellation cascade**: 61/168 runs (36%) cancelled in 7d; cron `10 * * * *` but median success runtime **84.5 min** (range 79.6–104.2) | V2 A §4; V2 P0-4 |
| C5 | **`alpha_engine/scanner.py:2942` `KeyError: 'LONG'`** — `_forex_by_sym[s["symbol"]][sig_type].append(s)` with a plain `{"BUY":[],"SELL":[]}` inner dict; FX rows carry `signal_type=LONG/SHORT`; kills **93 runs/24h** (ALPHA 47 + FAST 46) | V2 P0-1; V2 A §2 |
| C6 | **22,947 ghost rows** in `trading_picks` (10 constant-PnL cohorts; top `DOGEUSDT LONG pnl 1.3226 n=3,569 distinct_entries=1`); MEMECOIN duplicate inserts, no UNIQUE index | V2 P0-8; V4 QW-5 + INDEX |
| C7 | **Three divergent data stores** — SQLite `data/live_picks.db`, MySQL `trading_picks`, JSON dashboard files — with different counts, ages, PnL values | V4 INDEX (peer section); ML §1 |
| C8 | **Hardcoded Google API keys** tracked in `STOCKSUNIFY/scripts/lib/stock-api-keys.ts`, `STOCKSUNIFY/STOCKSUNIFY2/scripts/lib/stock-api-keys.ts`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js` | V2 P0-9; V2 CI_GATES G13 |
| C9 | **20 workflows never ran**; ~19 stale >90d (36 stale >7d per V2) | V2 A §3; V4 §Stale; V3 QW-6 |
| C10 | **Alpha Engine (primary scanner) effectively down**: V4 — last 10 runs = 9 cancelled + 1 failure; V2 — 47 fails/24h (KeyError LONG + Binance 451 + CoinMetrics 400/403) | V4 INDEX §1; V2 A §2 |
| C11 | **Silent failure masking** via `\|\| … (non-fatal)` / `continue-on-error: true` hides broken subsystems (price enricher, MySQL sync, Kalshi/Polymarket) | V4 QW-2, MF-4; V3 QW-1 |

Also agreed (secondary): stale sidecars 79–245d old (V2 P0-7); `summary_picks.json` WR > 100% arithmetic bug (V2 P0-2 / F §8); Polymarket Data API v1 retired → HTTP 410 (V2 F §2, memory constraint).

---

## 2. Unique per-peer (not restated by others)

**V2 (GitHub Actions deep audit + gates)**
- Exact run-level reconstruction: 24h = 4,109 runs (214 fail / 82 cancelled / 49 skipped); 7d = 28,187 runs (1,207 fail / 642 cancelled). Repo-level `total_count` capped at 2500, so per-workflow pagination was used.
- Per-workflow failure-cluster table incl. `pandas 2.1.4` source-build signatures and `ModuleNotFoundError: No module named 'tools'` in `refresh_daily_prices_yf.py` (AGENTS.md relative-vs-direct-script gotcha).
- 13-gate CI framework (G1–G13) mapping every invariant to a hard-fail or warn gate with verified line numbers.
- P0-5 (`UNQUOTED` quote-honesty contract), P0-6 (`sym_track_*` fed from active instead of closed pool), P0-7 (sidecar freshness manifest) — these are data-contract, not pure infra, but wire into CI.
- Source authenticity (Subagent F): `funding_rate_arb`/`btc_breakout` are ghost-excluded systems; `copy_trader_intel` named system DEAD because `data/active_picks.json` is gitignored.

**V3 (GLOBAL_QUICK_WINS CI parts)**
- Gate `tools/pi_data_hygiene.py` in CI — only 7,914/16,126 closed picks (49%) pass integrity gates; survivor-biased headline WR 41.8%/PF 0.94/compounded −99%.
- Payload staleness honesty: HTML 5-min `meta-refresh` re-serves a ~76-min-stale snapshot (`payload_lag_seconds≈4586`).
- Crypto `current_price` pinned to entry — surface true price age vs signal age (`universal_price_enricher.py`, `dashboard_freshness.js`).
- Nightly `gh api` cron to disable 20 never-run workflows (additive, disable-only).

**V4 (infra QUICK_WINS)**
- `alpha-engine-live.yml` has **58** `\|\| … (non-fatal)` / `\|\| true` instances; specific `cancel-in-progress: true` root cause for Alpha Engine cancels (QW-1).
- `hourly_update_last_run.json` 44.6h stale (QW-3); orphan pipelines Copy Trader + Claude Gainer never merged into dashboard payload (QW-4).
- `mysql_dedup_fix.yml` exists but is manual-only with `dry_run=true` default; recommend weekly cron + `UNIQUE(symbol, direction, created_at, source_system)` index (QW-5).
- TIME_EXIT limbo 4,220 picks (301/4,820 = 6.2% resolved) (MF-1); `at_signal_outcomes` 254d stale (MF-2).
- Repo bloat: `audit-dashboard.yml` commits a **44 MB** `dashboard_data.json` hourly; git pack ~19 GB → delta-sync + stop committing generated JSON (LF-1).
- Circuit-breaker workflow auto-disable after 3 consecutive failures (LF-3); unified pipeline merge orchestrator (LF-4).

**ML (childlike-airport, DB divergence)**
- `data/live_picks.db`: 129 active picks, **128 ~172d stale** (entry_time/last_checked = 2026-05-24/25) yet marked ACTIVE/OPEN; 8 sign-flipped `unrealized_pnl_pct` vs `pnl_pct`, 15 mismatch canonical `(current-entry)/entry`.
- `data/audit_trail.db` **completely empty**: all 9 consensus/feature/strategy tables 0 rows (only `bt_backtest_runs`=20, `meta`=1).
- `pick_history`: 136 rows, all `event='REGISTERED'` — no CLOSED/EXIT/TP/SL events → picks never resolve/age out.
- `asset_class` missing for 6 DB rows; `dashboard/live_picks.json` 17 picks all `asset_class='UNK'`; no mutual-fund coverage.
- `consensus_active_picks.json` fresh (1d) but EMPTY.
- ML code (`ml_ranker_fixed.py`, `ml_gatekeeper.py`) is sound — inverted-confidence is a **data** bug, not a code bug.

---

## 3. Consolidated fixes (deduped, file+line, effort/risk, proposer)

Effort: S <1h · M 1d · L 1d+. Risk: Low/Med/High.

| # | Fix | File+line | Effort | Risk | Proposer |
|---|-----|-----------|--------|------|----------|
| F1 | Guard forex direction bucket — normalize `LONG→BUY`, `SHORT→SELL`, add `OTHER` bucket | `alpha_engine/scanner.py:2937-2942` | S (30m) | Low | V2 P0-1 |
| F1b | Add `xgboost lightgbm` to fast workflow + Binance 451 backoff/jitter | `.github/workflows/alpha-engine-fast.yml:40`; `production_scanner.py:~2280` | S | Low | V2 P0-1b |
| F2 | Remove `update-environment: false` in the 8–9 failing workflows + `python -c` 3.11 assert; bump `pandas==2.1.4`→`2.2.3` after | `.github/workflows/signal_tracking.yml:35`, `alpha-engine-fast.yml:35`, `forward-test-new-strategies.yml:25`, `autonomous_trading.yml:37`, `copy-trader-intelligence.yml:30` (+rest under P1) | S (2h) | Low | V2 P0-3 |
| F3 | Space audit-dashboard cron to ≥ p95 runtime (`'10 */2 * * *'`) + fresh-payload preflight skip | `.github/workflows/audit-dashboard.yml:5,41-42,55` | S (15m) | Low | V2 P0-4 |
| F4 | Dedup + prune + CI assertion on `active_raw` (4,148→~3,851 IDs; prune EXPIRED >30d to archive JSONL; assert `unique(ids)==len(rows)` and EXPIRED ≤5%) | `audit_trail/dashboard_generator.py:9538,17481`; reuse registry key `tools/build_pf_registry.py:818-835` | M (8h) | Med | V2 P0-8 |
| F5 | Remove tracked Google API keys → env/secret + rotate; add `dbpasses.txt`/`*dbpasses*` to `.gitignore`; extend `db-password-leak-guard.yml:63` pattern to `AIza…` | `STOCKSUNIFY/scripts/lib/stock-api-keys.ts`; `STOCKSUNIFY/STOCKSUNIFY2/scripts/lib/stock-api-keys.ts`; `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`; `.gitignore` | M (0.5d) | Med (rotation) | V2 P0-9 + CI_GATES G13 |
| F6 | Run MySQL ghost-row dedup: `dry_run=true` review → `dry_run=false` apply → weekly cron + `UNIQUE` index | `.github/workflows/mysql_dedup_fix.yml`; `tools/mysql_dedup_fix.py` | M (2–3h) | Med | V4 QW-5 |
| F7 | Fix Alpha Engine cancellations: `cancel-in-progress: true → false` (or widen cron `3 */3 * * *`) | `.github/workflows/alpha-engine-live.yml` (`concurrency`); `alpha-engine-daily-picks.yml` | S (30m) | Low | V4 QW-1 |
| F8 | Surface `\|\| non-fatal` masking: post-scan step emitting `::error` per hit; convert 5 critical steps to `continue-on-error: false` | `.github/workflows/alpha-engine-live.yml` (58 instances); `audit-dashboard.yml` | M (2–4h) | Low | V4 QW-2 |
| F9 | Restart hourly update: freshness assert (`>2h` → `::error`) + `if: always()` on commit | `.github/workflows/audit-hourly-update.yml`; `audit_dashboard/generate_hourly_update.py` | M (1–2h) | Low | V4 QW-3 |
| F10 | Wire orphan pipelines (Copy Trader, Claude Gainer) into dashboard payload pre-generator merge | `.github/workflows/audit-dashboard.yml` (add 2 merge steps); `audit_trail/dashboard_generator.py` | M (4–6h) | Med | V4 QW-4 |
| F11 | Make Alpha Engine MySQL sync fail-loud + retry loop (3× backoff) | `.github/workflows/alpha-engine-live.yml:812-828`; `sync_all_picks_to_mysql.py` | M (3–6h) | Med | V4 MF-4 |
| F12 | Gate data-hygiene guardian in CI pre-publish (`pi_data_hygiene.py`, exit 1) | `.github/workflows/audit-dashboard.yml`; `tools/pi_data_hygiene.py` | S | Low | V3 QW-1 |
| F13 | Emit true payload staleness (`payload_lag`) instead of misleading 5-min refresh | `audit_trail/dashboard_generator.py`; `audit_dashboard/dashboard_freshness.js` | S | Low | V3 QW-2 |
| F14 | Stop pinning crypto `current_price` to entry; set `None` + `price_freshness` flag on fetch failure | `alpha_engine/universal_price_enricher.py` | S/M | Med | V3 QW-3 |
| F15 | Nightly `gh api` cron to disable 20 never-run + stale workflows (disable-only) | `.github/workflows/audit-dashboard.yml` (or new) | M | Low | V3 QW-6 |
| F16 | Recompute signed PnL + refresh `current_price`/`last_checked` for 129 SQLite picks; single canonical PnL source | `data/live_picks.db`; `mercury2/scanner.py:481-485`; `copy_trader_intel/outcome_resolver.py:252`; `forward_trade_executor.py:100-102` | M | Med | ML §3.1-3.2 |
| F17 | Backfill `asset_class` (6 DB + 17 UNK) via `asset_class.py`; add MUTUAL_FUND class | `alpha_engine/asset_class.py:22-62,130,191,263`; `dashboard/live_picks.json` | S | Low | ML §3.3 |
| F18 | Emit CLOSED/EXIT/TP/SL into `pick_history`; close/expire >30–60d stale picks | `data/live_picks.db` (pick_history); `audit_trail/universal_pick_resolver.py` | M | Med | ML §3.4 |
| F19 | Populate `audit_trail.db` tables (consensus, feature, strategy stats, raw picks, audit events) via `audit_sync.py` | `data/audit_trail.db`; `alpha_engine/audit_sync.py` | M | Med | ML §3.5 |
| F20 | Fix empty `consensus_active_picks.json` merger | `copy_trader_intel/non_crypto_consensus.py`; `alpha_engine/prediction_market_consensus.py` | M | Med | ML §3.6 |
| F21 | CI gate set G1–G13 (summary/quote/liveness/dedup/freshness/JSON/workflow-lint/schedule/DB/backlog/source/push/secret) — stage after P0 | `.github/workflows/ci-tests.yml`, `audit-dashboard.yml`, new `tests/test_*.py` | L (weeks) | Med | V2 CI_GATES |
| F22 | Delta-only MySQL sync + stop committing 44MB `dashboard_data.json` (gitignore + artifact upload) | `.gitignore`; `.github/workflows/audit-dashboard.yml`; `sync_all_picks_to_mysql.py` | L (1wk) | Med | V4 LF-1 |
| F23 | Rescue TIME_EXIT limbo 4,220 picks (batch resolver) + raise resolver timeout 40→60m | `tools/resolve_time_exit_backlog.py` (new); `audit-dashboard.yml`; `universal_pick_resolver.py` | L (1–2d) | Med | V4 MF-1 |
| F24 | Repair intrabar truth (`at_signal_outcomes` 254d stale) — bootstrap reresolve | `audit-dashboard.yml` resolver step; `universal_pick_resolver.py` | L (1–2d) | Med | V4 MF-2 |
| F25 | Refresh all stale JSON artifacts via `stale_artifact_refresher.py` + guardian workflow; retire `db_freshness.json` | `tools/stale_artifact_refresher.py` (new); `.github/workflows/artifact-freshness-guardian.yml` (new) | L (1–2d) | Med | V4 MF-3 |
| F26 | Alpha Engine circuit breaker (auto-disable after 3 consecutive failures) | `.github/workflows/actions-failure-guardian.yml`; `scripts/actions_failure_guardian.py` | L (3–5d) | Med | V4 LF-3 |
| F27 | Unified pipeline-merge orchestrator (normalize + dedup by `symbol+direction+source_system`) | `tools/pipeline_merge_orchestrator.py` (new); `audit-dashboard.yml` | L (1–2wk) | Med | V4 LF-4 |

**Vetoed / destructive-flagged SQL (do NOT run unattended):**
- **F6 ghost-row dedup `DELETE`** — must remain `dry_run=true` for any scheduled run; apply only via manual dispatch after a reviewed preview. Proposer V4 QW-5 explicitly gates apply behind manual dispatch.
- **F4 prune `EXPIRED` rows** — archive-only (append to `expired_archive/YYYY-MM.jsonl`), never hard-delete; keep `summary.raw_preprune_count`.
- No peer proposed `git push --force`, `git reset --hard`, or broad `data/*.json` glob triggers — consistent with the `no_force_push_to_main` / `[skip ci]` guardrails (V2 CI_GATES "Guardrails").

---

## 4. Conflicts

| # | Conflict | Detail |
|---|----------|--------|
| X1 | **`cancel-in-progress` direction is opposite across peers** | V2 P0-4 attributes `audit-dashboard.yml` cancels to `cancel-in-progress: false` (queue builds) + 85-min runtime, fix = widen cron. V4 QW-1 attributes `alpha-engine-live.yml` cancels to `cancel-in-progress: true` (kills in-flight), fix = set `false`. Both correct for *different workflows*, but a naive blanket "always false" would regress audit-dashboard. |
| X2 | **Failing-workflow count: 28 vs 25/24** | V4 = 28 "last run = failure"; V2 = 25 "last run failed" / 24 "failing in 24h" / 88 "failing in 7d". Snapshot-time + windowing differences; V4's 28 includes stale manual jobs (Backup Restore, MySQL Q-001, DB Secret Scan). The prompt's "28" matches V4's most-recent-run criterion. |
| X3 | **`dashboard_data.json` staleness: 26d vs ~1.6h** | V4 INDEX claims 26 days old (Oct 19); V2/V3 measured the **deployed** payload at ~1.4–1.6h (V2 P0-4; V3 "paylag≈4586s"). Likely V4 read the git-tracked repo file while V2/V3 read the live URL. Needs reconciliation — see UNVERIFIED U3. |
| X4 | **Secret scope: "remove tracked keys" vs "nothing to fix"** | V2 P0-9/G13 find hardcoded Google API keys in 3 tracked files + `dbpasses.txt` unignored. ML §3.7 finds no `dbpasses.txt` in its worktree and declares "nothing to fix". Reconciliation: the live keys file is `~/dbpasses.txt` (outside repo, gitignored per memory); V2's tracked-key finding is a *different* artifact (TS/JS literals). Both true, different scopes. |
| X5 | **Alpha Engine root cause: KeyError LONG vs cancel-in-progress** | V2 pins the 93 fails/24h to the `KeyError: 'LONG'` crash; V4 pins the ~24h outage to `cancel-in-progress: true` (9 cancelled + 1 failure). Both are present and compounding: crashes (KeyError) + cancels (concurrency) together kill the scanner. Fix F1 *and* F7 together. |

---

## 5. UNVERIFIED

- U1 Root errors for runs mid-retry at capture: Sports smoke + Playwright (43609430834), CI Tests (43605861085), Market Beating (43603128044), robust-edge-miner (43596188828), ALPHA Live (43603342689) (V2 A §8).
- U2 Whether the `update-environment: false`→Python 3.14 failure is specific to a self-hosted runner label (`vars.ACTIONS_RUNNER_LABEL`) or applies to cloud `ubuntu-latest`; runner label per job not captured (V2 A §8).
- U3 `dashboard_data.json` 26d (V4 repo file) vs ~1.6h (V2/V3 live URL) — which artifact is "the" canonical dashboard payload; needs path/URL confirmation before acting on V4 MF-3's "26 days stale" claim.
- U4 Repo-wide warning/deprecation census (only 19 failed logs sampled; 722 WARN / 75 Deprecation in sample) (V2 A §8).
- U5 7d count of zero-job cancelled runs (only the 82 in-24h runs were job-checked; 15 zero-job) (V2 A §8).
- U6 Exact current PnL for CRYPTO live picks (served from a separate endpoint not located in V4's audit) (V4 INDEX).
- U7 Real-time status of Kalshi/Polymarket feeds (data files 404 on live site; output path unknown) (V4 INDEX).
- U8 Windows-host peer transcript `C:\Users\zerou\Desktop\chat_transcript_2026-11-14.md` not accessible from Linux (V4 INDEX).
- U9 ML peer's SQLite findings (`live_picks.db` 172d, `audit_trail.db` empty) are peer-reported, not independently re-verified by V2/V4 (V4 INDEX "peer additions").

---

## 6. P0 order (consolidated, impact÷risk)

1. **F1 + F1b** — `KeyError: 'LONG'` guard (removes 93 fails/24h; unblocks the two Alpha scanners).
2. **F2** — `update-environment: false` Python 3.14 fix in the 8–9 failing cluster (unblocks ~5% of 24h failures).
3. **F3** — space audit-dashboard cron to 2h (kills the 61/168 cancel cascade).
4. **F7** — Alpha Engine `cancel-in-progress: true → false` (restores the primary scanner).
5. **F6** — MySQL ghost-row dedup (dry-run first, then reviewed apply) + F4 dedup/prune on `active_raw`.
6. **F5** — rotate/remove tracked Google API keys + gitignore (coordinate rotation with operator).
7. **F8** — surface `\|\| non-fatal` masking (visibility for everything downstream).
8. **F12 + F13 + F14** — honesty gates: data-hygiene gate, true payload staleness, unpin crypto price.

Then (P1): F9 hourly update, F10 orphan-pipe merge, F11 fail-loud sync, F16–F20 DB-divergence reconciliation (ML peer), F15 stale-workflow disabling.
Then (P2): F21 CI gate suite (G1–G13, staged after their P0 fixes), F22–F27 long-term infra (delta sync, telemetry, circuit breaker, merger).

Sequencing note (V2 P0_QUICK_WINS §Sequencing): P0-1 → P0-4 first (CI unblock, no data consumers), then P0-2/P0-6 (one generator run), then P0-5/P0-7/P0-8 (payload contract), then P0-9 with the operator. ML peer insists P0 = PnL calc + staleness + asset_class backfill *before* any per-asset-class work.
