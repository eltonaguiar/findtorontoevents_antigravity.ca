# Supply-Bottleneck Analysis (S4 round 2) — 2026-11-25

Read-only code analysis + strictly read-only SQL (SELECT/SHOW/EXPLAIN).
Baseline context (given, not re-verified): 0/9 asset classes money-ready; ~4100+ raw
picks vs ~20-22 active; Smart Picks structurally ~0; ~91k rows stuck OPEN; many cohorts
pnl_pct null/0/constant. Clean-trade supply is THE bottleneck.

Status: COMPLETE — all four research questions answered; ranked action plan included.

---

## Q1 — OPEN backlog (~91k reported): where it lives, who should close it, why they don't

### Findings (measured 2026-11-25, ejaguiar1_stocks, read-only SELECTs)

**Status distribution of the candidate pick tables:**

| table | total (sum of statuses) | OPEN rows | notes |
|---|---|---|---|
| `trading_picks` | 153,366 | **99,345** | THE backlog. Statuses: OPEN 99,345 / TIME_EXIT 33,646 / LOST 5,798 / TP_HIT 7,281 / SL_HIT 4,000 / EXPIRED 2,524 / ACTIVE 37 / CLOSED 159 |
| `at_local_picks` | ~76.3M rows (info_schema est.) | **33,515** | second OPEN pool; index `idx_status` exists; full count infeasible in 15s (76M-row table) |
| `picks` | 8,532 | 85 | small legacy table |
| `at_raw_picks` | 114,100 | 180 | healthy — hourly stale-sweep resolves it (OPEN min created 2026-11-22, i.e. no OPEN older than ~4d) |
| `trading_picks_v2` | 72,891 | 285 | clean-ledger mirror, healthy |
| `at_pick_outcomes` | 54,315 | 0 | fully resolved (WON 13,692 / LOST 19,530 / EXPIRED 29,647 / FLAT 1,046) |

Open-task figure "~91k" is the same phenomenon; direct measurement is stronger: **99,345 + 33,515 = ~132,860 OPEN rows across the two big tables**.

**Age buckets of `trading_picks.status='OPEN'` (99,345 rows, by created_at):**

| bucket | n | range |
|---|---|---|
| <7d | 5,381 | 2026-11-19 .. 2026-11-25 (legit recently-open) |
| 7-30d | 14,069 | 2026-10-27 .. 2026-11-18 |
| 30-90d | 33,756 | 2026-08-28 .. 2026-10-27 |
| **>90d** | **46,139** | 2026-02-20 .. 2026-08-28 (definitively zombie) |

Even with a generous 7-day live window, **~93,964 of 99,345 (94.6%) are past any plausible hold window** (hold windows are 48-120h; see below).

**Top strategies still emitting/stuck in OPEN (`trading_picks`):**

| strategy | OPEN n | of which >30d | newest |
|---|---|---|---|
| non_crypto_consensus | 20,181 | 15,819 | 2026-11-25 |
| forex_rsi2_mean_reversion | 11,978 | 9,139 | 2026-11-19 |
| forex_zscore_200d_fade | 11,844 | 9,784 | 2026-11-25 |
| combined_confidence | 6,111 | 4,654 | 2026-11-25 |
| short_dominant_engine | 4,883 | 4,352 | 2026-11-25 |
| futures_bb_mean_reversion | 4,398 | 3,420 | 2026-11-25 |
| smart_money_accumulation | 3,329 | 2,532 | 2026-11-24 |
| cftc_cot_commercial_signal | 3,086 | 2,597 | 2026-11-19 |
| futures_connors_rsi2 | 2,804 | 2,346 | 2026-11-18 |

Emission is still live: `trading_picks` is fed hourly by `.github/workflows/mysql-trading-sync.yml` (cron `54 * * * *`) via `alpha_engine/mysql_trading_sync.py:195` (`INSERT ... ON DUPLICATE KEY UPDATE`), which syncs JSON pick sources (`active_picks.json` etc.) with pick `status` defaulting to OPEN (`mysql_trading_sync.py:344`).

### Root cause: who is supposed to close them, and why they don't

Hold windows are tiny: `tools/pick_hold_windows.py:13-31` — 48h crypto/meme, 72h forex/penny, 96h equity/ETF/commodity/futures, 120h bond; `DEFAULT_HOLD_HOURS=48`. Nothing is legitimately OPEN for >7d. Three independent resolver defects let the backlog grow:

1. **Cron-scheduled resolver runs in DRY-RUN mode forever.**
   `.github/workflows/mysql-stale-picks-resolver.yml:64` — `DRY_RUN="${{ github.event.inputs.dry_run || 'true' }}"`. On a scheduled run (`cron: '25 4 * * *'`, line 5) `inputs.dry_run` is empty → defaults to `'true'` → the tool is always invoked with `--dry-run` (line 70). This is *the* tool whose docstring says "finds OPEN picks older than N days" and targets `trading_picks` (`tools/mysql_stale_picks_resolver.py:307-309`). It has therefore **never applied on a schedule** — confirmed empirically: `resolve_pick()` writes status 'WIN'/'LOSS' (`mysql_stale_picks_resolver.py:250`) but `trading_picks` contains **zero** WIN/LOSS rows either (status is varchar(20) so an apply would have stuck).
   *Fix: flip default to `'false'` (or drop the `|| 'true'`), effort S, risk low — but see risk note: WIN/LOSS labels are non-canonical (should map to TP_HIT/SL_HIT/time-exit per `tools/standardize_statuses.py` convention), so apply once in DRY-RUN audit first.*

2. **The hourly stale-pick sweep points at the WRONG TABLE.**
   `.github/workflows/outcome-resolver.yml:143` runs `python tools/resolve_stale_open_picks.py --execute --batch-size 500 --max-batches 30` — with **no `--table`**, and the CLI default is `at_raw_picks` (`tools/resolve_stale_open_picks.py:643`). The tool *does* support `trading_picks` (config at line 90: statuses OPEN+ACTIVE, resolves to `TIME_EXIT`/`TIME_EXIT_MAX_HOLD`), but the hourly job never selects it. So `trading_picks` has **no scheduled closer at all**: the only closer-by-design (mysql_stale_picks_resolver) is locked in dry-run, and the one that runs targets a different table.
   *Fix: add `--table trading_picks` as a second invocation in outcome-resolver.yml, effort S, risk low (tool is idempotent, batch-capped, oldest-first).*

3. **`trading_picks`' other close path matches at most ONE row per symbol+direction and only when *something else* already computed the exit.**
   `audit_trail/mysql_client.py:815-824` (`mysql_close_trade`): `WHERE symbol=%s AND direction=%s AND status IN ('OPEN','ACTIVE','CLOSED','FLAT') ... LIMIT 1` — it closes the *latest* row only and only when a closing event with exit_price/pnl arrives from a resolver run. `alpha_engine/outcome_resolver.py:2012-2014` updates `trading_picks` by `id` — but only for picks in its in-memory `resolved_picks` list, i.e. only picks whose TP/SL/time condition the resolver observed (comment at `outcome_resolver.py:1858`: "the DB row stays OPEN/unresolved" when pnl can't be computed). Rows whose price fetch failed (`mysql_stale_picks_resolver.py` `skipped_no_price`) are retried forever, never expired lazily.

Nobody runs a lazy "expire anything past max-age" mutation on `trading_picks` in cron: `tools/db_p0_integrity_remediation.py:46` has exactly such a 45-day EXPIRED sweeper but is **not referenced by any workflow** (`grep db_p0_integrity_remediation .github/workflows/*.yml` → 0 hits).

**Why it matters for supply:** OPEN rows are excluded from every clean-trade ledger/closed-cohort metric (dashboards treat `pnl_pct` of OPEN as not-yet-real), so 99k zombie rows simultaneously (a) inflate "raw" counts while (b) contributing zero closed trades.

## Q2 — PnL backfill gaps: where pnl_pct gets set, and which cohorts are broken

### Findings (measured 2026-11-25)

**A. `trading_picks` closed rows (status in TP_HIT/SL_HIT/LOST/EXPIRED/TIME_EXIT/CLOSED, n=53,415) — mostly healthy:**

| status | n | NULL pnl | =0 pnl | distinct pnl |
|---|---|---|---|---|
| TIME_EXIT | 33,646 | 86 (0.3%) | 2,174 (6.5%) | 12,686 |
| TP_HIT | 7,281 | 110 (1.5%) | 17 | 3,100 |
| LOST | 5,798 | 73 (1.3%) | 27 | 2,136 |
| SL_HIT | 4,000 | 23 (0.6%) | 0 | 967 |
| EXPIRED | 2,524 | 120 (4.8%) | **2,026 (80.3%)** | 364 |
| CLOSED | 159 | 0 | 0 | 150 |

Overall NULL only 0.8% — but **EXPIRED is a near-constant zero cohort (80% = 0.0, 364 distinct over 2,524 rows)** and TIME_EXIT still carries 2,174 zeros.

Worst `trading_picks` strategies by zero share (n>50, zero >10%):

| strategy | n | =0 | %0 |
|---|---|---|---|
| smart_money_accumulation | 442 | 211 | **47.7%** |
| forex_rsi2_mean_reversion | 4,989 | 1,703 | 34.1% |
| stocks_ema_golden_cross | 347 | 111 | 32.0% |
| cot_positioning | 139 | 64 | 46.0% |
| futures_momentum | 2,395 | 349 | 14.6% |
| stocks_rsi2_pullback | 1,620 | 320 | 19.8% |

**B. `at_raw_picks` closed rows (n=110,xxx of 114,100) — much worse, this is where "null/0/constant cohorts" live:**

| asset_class | n | NULL | =0 | NULL+0 share | distinct |
|---|---|---|---|---|---|
| CRYPTO | 69,456 | 6,194 | 17,898 | **34.7%** | 31,555 |
| FOREX | 15,830 | 1,540 | 1,515 | 19.3% | 6,655 |
| EQUITY | 14,601 | 1,239 | 1,332 | 17.6% | 3,219 |
| FUTURES | 8,638 | 888 | 468 | 15.7% | 4,073 |
| MEMECOIN | 2,001 | 525 | 741 | **63.3%** | 568 |
| PENNY_STOCK | 494 | 236 | 231 | **94.5%** | 26 |
| UNKNOWN | 672 | 152 | 520 | **99.9%** | **1** |

Strategy-level constant cohorts (`at_raw_picks`, n>50, (NULL+0)/n > 30%) — exact constants are a data-integrity defect, not a market outcome:

| strategy | n | NULL | =0 | distinct |
|---|---|---|---|---|
| incubator_gainer | 5,124 | 9 | 4,794 (93.6%) | 322 |
| audit_trail_local | 468 | 6 | 462 | **1** |
| goldmine_meme | 297 | 0 | 297 | **1** |
| SCALP | 282 | 0 | 282 | **1** |
| FearGreedReversal | 297 | 156 | 141 | **1** |
| macd_crossover | 229 | 1 | 225 | 2 |
| CCIReversal | 217 | 13 | 204 | 1 |
| coinglass_leverage_squeeze | 219 | 101 | 118 | 1 |
| yahoo_analyst_consensus | 374 | 321 (86% NULL) | 3 | 47 |
| cta_tsmom_blend | 281 | 256 (91% NULL) | 0 | 25 |
| binance_smart_money | 245 | 233 (95% NULL) | 12 | 1 |
| IRB Hoffman | 234 | 228 (97% NULL) | 6 | 1 |
| Correlation - HMA Trend | 261 | 238 (91% NULL) | 23 | 1 |
| coingecko-trending-spike-scout | 434 | 293 (68% NULL) | 137 | 5 |

**Never-computed vs legit 0%:** the NULL-heavy strategies above are *closed* (terminal status) but never got an exit computation — i.e. "closed by status, not by price". The 0-heavy ones wrote `0.0` as a *default*, notably `alpha_engine/outcome_resolver.py:2000` — `pnl_raw = pick.get("pnl_pct", 0) or 0` → the universal close path **coerces missing pnl to 0.0** before writing (~line 2005 `pnl = round(float(pnl_raw), 4)`). Correlation with stuck OPEN is distinct: OPEN rows (Q1) are `pnl_pct IS NULL` by construction and are excluded from closed cohorts, so the "91k stuck OPEN" and the "closed-but-NULL/0" problems are two separate leaks out of the same funnel.

### Root causes (file:line)

1. **Zero-as-missing at close time:** `alpha_engine/outcome_resolver.py:2000-2005` writes `pnl = 0.0` whenever the source pick has no `pnl_pct`. Every close without a price becomes a fake 0% trade → contaminates WR/PF averages of the cohorts above.
2. **Emitters that close without prices at all:** `at_raw_picks` strategies like IRB Hoffman / binance_smart_money / Correlation-HMA / cta_tsmom_blend are 91-97% NULL even in terminal status — their emit/close path marks terminal without an exit price (they come in via `mysql_record_raw_pick`, `audit_trail/mysql_client.py:537`, whose only pnl input is `pick.get('pnl_pct')`).
3. **Constant-zero legacy cohorts** (`audit_trail_local`, `goldmine_meme`, `SCALP`, `FearGreedReversal` — distinct = 1) were imported/resolved with a hard-coded 0 and nothing ever re-derived them from prices.
4. **`EXPIRED` semantics:** `mysql_close_trade` (`audit_trail/mysql_client.py:740-786`) maps reason TIME_EXIT/MAX_HOLD/EXPIRED → status EXPIRED; without an exit price the earlier fill (line 765 `if _pnl is None and _exit is not None`) is skipped, leaving the 0.0/NULL that produces the 80% zero EXPIRED cohort.

### Existing backfill tooling and why it missed

| tool | scope | scheduled? | why it misses |
|---|---|---|---|
| `tools/backfill_null_pnl.py` | `trading_picks` WHERE `pnl_pct IS NULL` + terminal status (line 61-66), LIMIT param | daily, `auto-shutdown-monitor.yml:27` (08:06 UTC) | covers NULL only, never the 0-default cohort; skip rules at line 88-91 mark sign-contradictory rows and leave them |
| `audit_trail/zero_pnl_detector.py` | detects `ABS(COALESCE(pnl_pct,0)) < 0.0001` terminal rows, `--limit 500` (line 64, 80-92) | daily, `ab_analysis.yml:70` (05:16 UTC) | **detect-only: prints the UPDATE it would run (line 145), applies nothing.** 500-row cap even if it did |
| `tools/backfill_time_exit_pnl.py` | `trading_picks` TIME_EXIT with 0/NULL (line 73) | **no workflow** (grep → 0 hits) | manual one-shot; explains why only 2,174 zeros remain of the ~33k it targeted |
| `tools/backfill_resolved_pnl.py`, `backfill_null_pnl_safe.py` | trading_picks | no workflow | manual, status-gated to ('TP_HIT','SL_HIT','LOST','TIME_EXIT') (`backfill_null_pnl_safe.py:52`) — misses EXPIRED and everything in `at_raw_picks` |
| `tools/resolve_stale_open_picks.py --backfill-pnl-null` | maps 0.0 → NULL **only for `UNMEASURABLE_PNL_EXIT_REASONS`** (line 286-335) | workflow runs it without this flag | direction is zero→NULL (cohort hygiene), not a recomputation; and never scheduled with the flag |
| `tools/backfill_closed_smart_scores.py` | smart_score (see Q3) | no workflow | n/a |

Net: NULL backfill is scheduled but narrow (trading_picks only, skips EXPIRED/0-cohorts); zero detection runs daily but never mutates; every `at_raw_picks` constant cohort has **no** scheduled backfill at all.

Note: "`at_raw_picks` closed rows (n=110,xxx)" above = 113,920 terminal rows (WON 34,018 + LOST 34,654 + EXPIRED 11,262 + CLOSED 22,201 + ABANDONED 11,785).

### Q2 fix options
- **Option 1 — stop writing 0-as-missing (effort S, risk low):** in `alpha_engine/outcome_resolver.py:2000`, treat missing `pnl_pct` as `None` instead of `0 or 0` and let the close path leave pnl NULL when no price exists (NULL is honest and the scheduled `backfill_null_pnl` can fill later; 0.0 is a lie baked into WR/PF math). Behavior change requires re-checking the sign-coherence DB check (`chk_pnl_sign_coherence`) tolerates NULL — low risk, code-level only.
- **Option 2 — give zero_pnl_detector teeth (effort S, risk medium):** convert `audit_trail/zero_pnl_detector.py`'s printed UPDATE (line 145) into an applied, price-recomputed, sign-checked UPDATE behind an `--execute` flag + schedule it. Risk: recomputing stale exit prices can inject wrong pnl if entry/exit scale mismatch (mitigate with the existing |pnl|>5.0 guard already in `mysql_stale_picks_resolver.py:230-240`).
- **Option 3 — scheduled at_raw_picks constant-cohort remediation (effort M, risk low):** one-off + weekly job: for terminal `at_raw_picks` rows with pnl NULL/0 and an exit price derivable, backfill from prices; for constant-cohort imports (`audit_trail_local`, `goldmine_meme`, `SCALP`) whose distinct = 1 and no price trail exists, quarantine them from statistics (flag, don't rewrite history). No quality-bar change — it removes corrupt observations instead of trusting them.

## Q3 — smart_score / trust_tier stamping (code-only)

### Where they are WRITTEN

**smart_score — computed at READ time, never stamped by emitters:**
- `audit_trail/quality_gates.py:10859` — `"smart_score": calculate_smart_score(pick)` (smart-pick payload build)
- `audit_trail/integrate_quality_gates.py:33` — same, at gate integration
- `audit_trail/dashboard_generator.py:18357` — `pick_copy["smart_score"] = calculate_smart_score(pick_copy)` (render-time copy; original untouched)
- `audit_trail/non_crypto_smart_score.py:162` — non-crypto variant, computed
- `tools/backfill_closed_smart_scores.py:43` — backfill for closed picks (manual, no workflow)
- Explicit confirmation that it is never persisted: `tools/edge_finder.py:205` — `d["smart_score"] = None  # not persisted in trading_picks`. Schema check: **no `smart_score` column exists on `trading_picks` or `at_raw_picks`**; only `at_pick_surface_eval` and `sp_picks` (snapshot tables) and Mongo-style feature store DDL (`audit_trail/pick_feature_store.py:90`) have it, i.e. it never reaches the pick-of-record.

**trust_tier — written by exactly one production stamper, for exactly one source:**
- `audit_trail/stamp_pick_quality.py:468,478` — stamps PROVEN/WATCH/MONITOR/AVOID from `strat_fwd_wr`/`strat_fwd_trades`, plus hf_conviction_tier/hf_quality_score; **saves back to the pick file** (`active_picks.json`).
- Invoked **only** in `.github/workflows/alpha-engine-live.yml:268`: `python -m audit_trail.stamp_pick_quality alpha_engine/data/active_picks.json || echo '...non-fatal'` — single file, failure swallowed as non-fatal. (File header claiming it "Runs as a step in audit-dashboard.yml" is stale — grep finds no such step.)
- Ad-hoc writers: `alpha_engine/sandbox_mutation_experiments.py:118` (SANDBOX), `alpha_engine/strategies/etf_decay_shorts.py:227` + `strategies/vix_reversal.py:168,219,291` ("DEVELOPING"), `alpha_engine/quan_engine_scalp_hybrid_inverse.py:368` (hard-coded "SANDBOX"), `alpha_engine/phase5_dashboard_integration.py:63` (defaults to "UNPROVEN" when missing — so most picks surface as UNPROVEN).

### Top active emitters that stamp NEITHER

The MySQL pick ingest syncs `JSON_PICK_SOURCES` from `audit_trail/dashboard_generator.py:3718+` — **66 sources** (alpha_engine, battleground, mercury2, paper_trading, ml_bg_a..f, crypto_signal_engine, coinglass, rl_agent, genetic_programmer, audit_ensemble, mape_evolver, ensemble_evolver, neat_neural, hyperparam_dna, momentum_evolver, multitf_evolver, contrarian_evolver, regime_terminal, ml_crypto_pred, riseoftheclaw, rapid_fire, quan_engine, meme_scanner, live_spike_trader, multi_asset, ai_challenge_*, smart_money, meta_strategy, copy_trader_*, bond_scanner, ml_gatekeeper, ml_consensus, stocksunify2, wired_in_childlike, consensus_picks, ...).

- **Only `alpha_engine`'s file receives trust_tier.** The other 65 ship no trust_tier (dashboard falls back to UNPROVEN via `phase5_dashboard_integration.py:63`).
- **No emitter ships smart_score for any source** — it is synthesized at render time, so anything that reads picks before the dashboard (mysql_trading_sync, smart-picks pre-filter, ledgers) sees nothing.

### Minimal stamping point (shared path)

Two genuine chokepoints exist; the elected one should be (1)+(2):

1. **`alpha_engine/mysql_trading_sync.sync()` — after the JSON load loop (`mysql_trading_sync.py:884-905`), before the upsert loop.** Precedent: this exact spot already does an "Elite-score backfill before sync" (`mysql_trading_sync.py:911-915`, added 2026-05-09 because 92% of picks had elite_score=NULL and were invisible downstream — same class of bug as smart_score/trust_tier today).
2. **`audit_trail/stamp_pick_quality.py` invoked per source**: make the alpha-engine-live step loop `JSON_PICK_SOURCES` active files instead of one hardcoded path (the tool already takes `--file`). Cheap: WR-based tier needs only closed_picks history, which every source has.

Schema caveat: `trading_picks` has `trust_score INT` but **no `trust_tier`/`smart_score` column** and `at_raw_picks` carries only `raw_payload` JSON — so DB persistence needs either an `ALTER TABLE ADD smart_score/trust_tier` (small migration) or stamping into the JSON sources pre-sync (zero schema change, works for the dashboard, which reads JSON sources first anyway).

Fix options:
- **A (effort S, risk low):** loop `stamp_pick_quality --file <each active file>` in `mysql-trading-sync.yml`/`alpha-engine-live.yml`; results land in JSON sources; no schema change. Adds trust_tier to 65 sources.
- **B (effort M, risk low-medium):** A + call `calculate_smart_score()` in the same loop and write `smart_score` into the JSON picks (still no schema change).
- **C (effort M, risk medium):** `ALTER TABLE trading_picks/at_raw_picks ADD smart_score, trust_tier` and stamp inside `mysql_trading_sync.sync()`/`recorder.record_raw_pick` — persist at the DB chokepoint, survives JSON churn, but schema migration + resolver/dashboard reads must learn the columns.

## Q4 — Gate funnel: raw -> gated -> active

### Findings (measured 2026-11-25)

- **Raw:** `at_raw_picks` lifetime 114,100 rows; last 7 days 993 new raw rows. (Dashboard-side "~4100 raw" is the JSON-source funnel window, taken as given.)
- **Gated:** `at_filter_log` last 7 days = 356 rejected rows; top 3 gate reasons:

| rank | filter_reason | n (7d) | share |
|---|---|---|---|
| 1 | `incubator_strategy` | 266 | 74.7% |
| 2 | `no_consensus` | 40 | 11.2% |
| 3 | `banned_strategy` | 26 | 7.3% |

| also: demoted_system 14, wr_suppressed 4, staleness 4, banned_purge 2 |

- **Lifetime ingest flags** (`at_raw_picks`, n=114,100): `was_banned` 11,901 (10.4%), `was_stale` 3,400 (3.0%), **`was_demoted` 0, `was_wr_suppressed` 0** — two flag columns are never written even though `recorder.py:395-396` maps those reasons; they only survive in `at_filter_log`. Any funnel reading the columns undercounts gates by 18/44 of reason types.
- **Active:** taken as given ~20-22 (not re-verified).
- **Funnel telemetry is broken in two places:** (a) `at_pick_flow_daily` reports `rejected_total=0` and empty `reject_top_reason` for all 36 rows in the last 7 days (raw_emitted 861, closed 697) — the daily funnel's rejection tracking is dead; (b) `pick_funnel_views` last generated 2026-05-29, `at_discord_gate_log` has 0 rows in 14 days. So the dashboard's funnel counts cannot currently self-report gate reasons — only `at_filter_log` is alive.

### Root cause of low active supply (no quality bars touched)

The funnel is not primarily *rejecting* — it is **starving**:
- Only ~7-14% of recent raw picks are filtered (356/993 in 7d by filter log; 861 raw emitted vs 697 closed in `at_pick_flow_daily`). The choke is downstream: 94.6% of `trading_picks` OPEN rows never resolve (Q1), so closed-trade cohorts never reach the Tier-2/3 sample floor.
- **Sample-size floor proximity (measured):** Tier 2/3 requires `n >= 100` (`audit_trail/dashboard_generator.py:6485-6486, 6512-6514, 11936-11938`; below-floor = "Building"). 8 strategies sit just under it in `trading_picks`: pm_whale_0x6e1d50 n=93, ensemble n=88, claude_ml_moderate_mut n=87, **etf_rsi2_pullback n=87** (matches the documented ETF n=87 "below charter floor" at `dashboard_generator.py:6108-6147`), inverse_ml_enhanced_RENDERUSDT_1h n=78, pm_whale_0xeee92f n=76, inverse_ml_enhanced_RENDERUSDT_4h n=74, cftc_cot_commercial_signal n=72 (20 of which are NULL/0-polluted).
- **Single change that raises clean supply WITHOUT lowering any quality bar: fix resolve-time (Q1 wiring)** — point the hourly stale sweep at `trading_picks` and unlock the daily resolver's apply mode. It converts up to ~93,964 aged OPEN rows into resolved TIME_EXIT/time-based closes with price-derived pnl. Capacity math: the hourly job runs `--batch-size 500 --max-batches 30` = 1,500 rows/hour headroom, so the backlog drains in ~63 hours of runs; closed-trade cohorts grow from 53,415 to potentially ~147k (+175%), which pushes every 72-99-n strategy across the n=100 floor with the *existing* PF/WR thresholds untouched. Gate-latency and floor changes were considered and rejected: gate staleness accounts for only 4/356 filter rows (negligible), and lowering the n=100 floor would weaken the bar (out of scope).

## Ranked Action Plan (top 5)

| # | change | expected supply impact | risk | owner-decision? |
|---|---|---|---|---|
| 1 | **Wire the hourly stale sweep to `trading_picks`**: add a second invocation `python tools/resolve_stale_open_picks.py --execute --table trading_picks --batch-size 500 --max-batches 30` in `.github/workflows/outcome-resolver.yml:143` | Drains the 99,345-row OPEN backlog (93,964 aged >7d) at up to 1,500/run/hr; closed cohorts 53k -> ~147k (+175%); pushes 8 near-floor strategies over n>=100; biggest single unlock | Low — tool is idempotent, oldest-first, batch-capped at TIME_EXIT with `TIME_EXIT_MAX_HOLD` reason; cohorts stay separable; spot-check first run for pnl plausibility | **Y/N** (touches production UPDATE cadence) |
| 2 | **Unlock the daily resolver's apply mode**: in `.github/workflows/mysql-stale-picks-resolver.yml:64` change `|| 'true'` -> `|| 'false'`, and map `resolve_pick()`'s WIN/LOSS (`tools/mysql_stale_picks_resolver.py:250`) to canonical TP_HIT/SL_HIT/TIME_EXIT first | Same backlog, second pump (runs daily 04:25); currently 100% dry-run = zero effect since the 2026-05-23 re-registration | Medium until labels canonicalized (WIN/LOSS would enter a status vocabulary the rest of the stack filters with `IN ('TP_HIT','SL_HIT',...)` and silently vanish from some queries) — land label mapping in same PR | **Y/N** |
| 3 | **Fix close-time pnl coercion**: `alpha_engine/outcome_resolver.py:2000` missing pnl -> None, not 0.0; plus scheduled `--execute` mode for `zero_pnl_detector.py` limited to price-recomputable rows | Removes fake-0 trades from WR/PF: directly repairs smart_money_accumulation (47.7% zeros), EXPIRED (80.3% zeros), forex_rsi2 (34.1%); smaller headcount effect but large *cleanliness* effect — zero-polluted n stops counting as evidence | Medium — NULL flows into downstream `COALESCE(pnl,0)` aggregators, so audit those first (many exist; `zero_pnl_detector` itself uses COALESCE at line 84) | **Y/N** |
| 4 | **Stamp trust_tier + smart_score at the shared chokepoint** (Q3 options A+B): loop `audit_trail.stamp_pick_quality --file` over every `JSON_PICK_SOURCES` active file (in `alpha-engine-live.yml:268` or `mysql-trading-sync.yml`) + write `calculate_smart_score()` alongside; no schema change | Un-suppresses Smart Picks: 65 of 66 sources currently ship neither field (all surface UNPROVEN); removes the structural ~0 Smart Picks cause without loosening any gate | Low — stamping adds information gates consume; worst case tiers default as today. Watch: AVOID tier may *reduce* active count initially (intended) | **Y/N** |
| 5 | **Repair funnel telemetry** so this stays measurable: re-enable `at_pick_flow_daily.rejected_total`/`reject_top_reason` feed (currently 0/empty for 7 straight days), record `was_demoted`/`was_wr_suppressed` flags in `at_raw_picks` (both 0/114,100 despite `recorder.py:395-396`), regenerate `pick_funnel_views` (stale since 2026-05-29) | Neutral for supply, essential for verification: without it, none of #1-#4 can be measured from the dashboard; `at_filter_log` remains the only living gate log | Low — read-mostly repairs; flag write touches insert path (additive columns already exist) | **Y/N** |

## Method / appendix
- All SQL: read-only SELECT/SHOW/EXPLAIN against `ejaguiar1_stocks` via `tools/db_env.get_stocks_creds()` credential pattern (variable names only; no secret values in this file), 15s read timeout, sequential. Two transient timeouts on large `GROUP BY` (76M-row `at_local_picks`) were retried as indexed/partial queries instead of widened.
- ~22 successful SELECTs total (Q1: 10, Q2: 5, Q3: 1 schema probe, Q4: 6); timeout/failed statements reported as such. `information_schema` statistics (indexes/table_rows) used where full scans exceeded the 15s cap — table_rows estimates are stale (e.g. `trading_picks` estimate 46,135 vs measured 153,366), so measured COUNTs are used everywhere except `at_local_picks`.
- Backtests DB (`ejaguiar1_backtests`) was not needed — all four questions resolved against stocks DB + code. `smart_picks_engine.py` and `check_active_picks.py` were NOT run (per standing instruction). No files outside this report were created/modified; no git commands executed.
