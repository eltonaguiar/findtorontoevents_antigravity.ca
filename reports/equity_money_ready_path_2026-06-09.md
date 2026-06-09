# EQUITY Money-Ready Path — Fastest CLEAN Route to Tier-2

**Date:** 2026-06-09
**Author:** Lead money-ready agent (Claude Opus 4.8 1M)
**Goal:** EQUITY is the only class passing BOTH WR (≥50%) and PF (≥1.5) policy-clean gates. Find the fastest CLEAN path to also satisfy n≥100 without degrading the 53.5% / 1.84 edge.

> **DATA CONSTRAINT:** Live MySQL is NOT reachable from this IP. Every number below cites an exact local snapshot file + field. Where a value could not be sourced, it says "not found in snapshots."

---

## TL;DR

1. **The EQUITY edge is REAL but THIN and STRATEGY-CONCENTRATED, not symbol-concentrated.** In the canonical `pf_registry.json` (2026-06-06), one strategy — `multi_asset_copytrader` (n=21) — drives **57.2% of all gross profit**; gross-profit HHI = **0.38** (>0.30 = concentrated). Symbol HHI is fine (0.033, top symbol AMD 8%).
2. **The "needs n≥100" framing is INCOMPLETE.** Even at n=100, EQUITY would still fail three structural gates that are independent of sample size: per-strategy DSR, PBO, and the single-source artifact gate. The verdict's headline `verdict: INSUFFICIENT_DATA` masks `mdd_ok=false`, `bootstrap_ci_ok=false` (CI crosses zero), `pbo=null` (uncomputable), and `single_source.ok=false`.
3. **There is a DATA-FRESHNESS SPLIT that is currently hiding the user's fixes.** The two profitable post-fix EQUITY sleeves (`stocks_rsi2_pullback` n=20 WR 80%, `smart_money_accumulation` n=14 WR 93%) appear ONLY in the fresh `closed_picks.json` (2026-06-09). The gate-input files (`dashboard_data.json` 06-03, `deflated_sharpe_results.json` 06-06, `cpcv_pbo_results.json` 06-02) are STALE/pre-fix and still score `stocks_rsi2_pullback` on the late-May crash cohort (n=17, WR 29.4%, **DSR = −4.17, survives=False**).
4. **The fixes (commits `745b947c1a`, `cc1f7a89c7`) HELP WR and are net-positive.** They cut emission only on bad-setup days (broad-downswing breadth throttle, falling-knife RSI(14) floor, 6 chronic-loser symbols, 10× write-dup dedup). The n-growth cost is small and falls disproportionately on the picks most likely to LOSE — so they accelerate, not delay, a *clean* n=100.

---

## 1. Per-STRATEGY EQUITY breakdown

### 1a. Canonical view — `audit_dashboard/data/pf_registry.json`, key `by_asset_class_strategy_policy_clean_net` (filtered `asset_class==EQUITY`), generated_utc 2026-06-06T03:43:54Z

Sum of strategy `n` = **71**, exactly matching the class-level `by_asset_class_policy_clean_net` EQUITY `n=71` and `money_ready_verdict.json` `classes.EQUITY.n_resolved=71`.

| Strategy | n | wins | loss | WR% | PF | total_pnl% | single-source artifact |
|---|---:|---:|---:|---:|---:|---:|---|
| multi_asset_copytrader | 21 | 16 | 5 | 76.2 | 5.91 | +0.7909 | **True** |
| regime_terminal | 17 | 3 | 14 | 17.6 | 0.26 | **−0.3558** | True |
| UNKNOWN | 15 | 11 | 4 | 73.3 | 4.92 | +0.1664 | True |
| cta_replicator | 6 | 0 | 6 | 0.0 | 0.00 | **−0.1467** | True |
| vt_equity_two_day_rsi_reversal | 4 | 4 | 0 | 100.0 | undef (no losses) | +0.0523 | False |
| cta_golden_cross | 3 | 1 | 2 | 33.3 | 0.74 | −0.0055 | False |
| momentum_rider_base | 3 | 2 | 1 | 66.7 | 10.25 | +0.2655 | False |
| stocks_ema_golden_cross | 1 | 0 | 1 | 0.0 | 0.00 | −0.0242 | False |
| stocks_rsi2_pullback | 1 | 1 | 0 | 100.0 | undef (no losses) | +0.0177 | False |

(All fields verbatim from the per-row dicts. `is_single_source_artifact`, `win_rate_pct`, `profit_factor`, `total_pnl_pct`, `n`, `wins`, `losses` are exact keys.)

**Aggregate check:** `gross_profit` sum = 1.6629, `gross_loss` sum = 0.9022 → PF = 1.8431 (matches verdict `pf=1.8431`).

**Edge drivers vs dead weight:**
- **Drivers (positive):** `multi_asset_copytrader` (+0.79), `momentum_rider_base` (+0.27, but n=3), `UNKNOWN` (+0.17). Just these three produce 87.5% of gross profit.
- **Dead weight (negative, killing WR/PF):** `regime_terminal` (n=17, WR 17.6%, −0.36) and `cta_replicator` (n=6, WR 0%, −0.15). Together they are **23 of 71 picks (32%)** and drag total_pnl down by −0.50. Removing them would raise class WR from 53.5% to ~71% and PF well above 3 — see §6 action #1.

### 1b. FRESH post-fix view — `alpha_engine/data/closed_picks.json` (2026-06-09T02:33, the verdict's own canonical loader source; 49 EQUITY rows, all WON/LOST)

The strategy names here DIFFER from the 06-06 registry because the resolver rebuilt the cohort after the user's 06-06 fixes:

| Strategy (closed_picks.json) | n | wins | WR% | resolver | quality flag |
|---|---:|---:|---:|---|---|
| stocks_rsi2_pullback | 20 | 16 | 80 | non_crypto_resolver **v2.1** (14/20) + None (6/20) | **CLEAN-ish** — 10× `TP_HIT_REPLAY` / 4× `SL_HIT_REPLAY` (intrabar OHLC), 8 distinct symbols, pnl −3.4%..+9.7% |
| smart_money_accumulation | 14 | 13 | 93 | **None / resolver_version None (14/14)** | **SUSPECT** — NOT resolved by trusted v2.1; 8/14 `entry_date=None`; 7/14 `TIME_EXIT` |
| cta_cross_asset_tsmom | 6 | 0 | 0 | — | dead weight |
| bond_yield_momentum | 3 | 0 | 0 | — | misclassified BOND-in-EQUITY |
| (7 more, n=1 each) | 7 | 3 | — | — | noise |

Source: per-strategy Counter over `closed_picks.json` EQUITY rows; `resolved_by`, `resolver_version`, `exit_reason`, `entry_date`, `hold_days`, `pnl_pct` fields read verbatim.

**Caveat on the post-fix winners (do NOT size on these yet):**
- `stocks_rsi2_pullback` n=20 is a **2-day entry batch** (15 rows 2026-06-05, 5 rows 2026-06-04). It even contains `UNH`, which the 06-06 sector-blocklist now excludes → confirming this batch is *pre-blocklist* data. It is reasonably trustworthy (intrabar REPLAY exits) but is one market regime, not a forward track.
- `smart_money_accumulation` n=14 WR 93% has `resolved_by=None` for all 14 rows — it is on the lower-trust resolution path. The repo's documented failure mode (memory: "BTCUSDT SELL n=100 1-day batch" false positive) applies. **Treat the 93% as provisional.**

---

## 2. Concentration check (HHI)

Computed over `pf_registry.json` EQUITY strategy/symbol rows:

- **Strategy-count HHI (by n share):** 0.2037 (1/9 = 0.111 floor; <0.30 → not concentrated by *count*).
- **Gross-profit HHI:** **0.3814 → CONCENTRATED.** `multi_asset_copytrader` alone = 57.2% of gross profit. The class edge is a single-strategy bet dressed up as a 9-strategy class.
- **Symbol HHI (by n):** 0.0329 — well diversified. Top symbol AMD = 8.0% (`top_symbol: "AMD"`, `top_symbol_share: 0.1029` in verdict; n-weighted 8.0% in the symbol view). No single-name risk.
- **Source concentration:** verdict `top_source_share: 0.3676` < the 0.40 default cap (`MAX_SOURCE_CONCENTRATION` in `money_ready_verdict.py:248`) → passes, but only just.

**Verdict:** the fragility is at the **strategy** level. If `multi_asset_copytrader` decays, the whole class drops below T2. This is exactly why the single-source gate (§3) fires.

---

## 3. DSR / PBO / promotion-gate assessment

### Gate definitions (sourced)
- **T2 charter / hard money gate:** `alpha_engine/eagle_gates.py:588-678` `passes_hard_money_gates(min_n=100)`: requires n≥100, PF≥1.5 (`:621`), WR≥0.50 (`:623`), strategy NOT in DSR noise set (`:627-629`), WFE≥0.60 (`:632`), MinTRL (`:637-640`), global PBO<0.50 strict (`:643-645`, `_EAGLE6_MAX_PBO_GLOBAL=0.5` at `:210`), symbol concentration<30% (`:649`).
- **Per-class verdict gates:** `alpha_engine/money_ready_verdict.py`: `MIN_N_CLASS=100` (`:155`), `MIN_PF=1.5` (`:159`), EQUITY WR floor 0.52 (`CLASS_WR_FLOORS`), DSR threshold 0.95 (`:160`), PBO threshold 0.55 (`:161`), PBO needs ≥2 strategies w/ n≥20 then ≥5 for power (`:895-905`, `MIN_N_STRATEGY=20` `:166`, `MIN_STRATEGIES_FOR_PBO=5` `:164`).

### What EQUITY actually scores today

From `money_ready_verdict.json` `classes.EQUITY` (2026-06-08):
- `dsr_ok: true, dsr_score: 1.0` — but this is the **class-aggregate** equity curve, not per-strategy.
- `pbo: null`, `pbo_ok: null` — `details.pbo.note: "need ≥2 strategies with n≥20, got 1"`. **PBO is uncomputable** because only one EQUITY strategy reaches n≥20 in the verdict's data slice.
- `spa_ok: true, spa_p: 0.0, n_spa_pass: 1`.
- `mdd: 0.3304, mdd_ok: false` — 33% drawdown FAILS the MDD gate (`_mdd_cvar_gate_ok: false`).
- `bootstrap_ci_lower: -0.001344, bootstrap_ci_upper: 0.021268, bootstrap_ci_ok: false` — **the 95% bootstrap CI on mean pnl INCLUDES ZERO.** The edge is not yet statistically distinguishable from noise.
- `single_source.ok: false`, `single_source_strategies: ["stocks_rsi2_pullback"]`, note: "all profitable sleeves are single-source (artifact edge)".
- `wf_oos_ok: true` (OOS PF 1.96 > IS PF 1.52, ratio 1.29 — good).
- `expectancy_ok: true` (+0.0089 net of 10bps slippage).

### Per-strategy DSR (the binding gate for promotion)

`tools/deflated_sharpe_results.json` (2026-06-06): `stocks_rsi2_pullback` → `trades:17, win_rate_pct:29.4, avg_pnl_pct:-1.2967, dsr:-4.1726, survives:false`. This is the **pre-fix late-May crash cohort** (sourced from `dashboard_data.json` `picks.recent_closed`, which `deflated_sharpe.py:128` reads — and that file is dated **2026-06-03, stale**, with `stocks_rsi2_pullback` n=17 WR 29% resolved 05-27..06-01).

`tools/cpcv_pbo_results.json` (2026-06-02): **global `pbo: 1.0`, "FAIL backtest overfit (PBO≥0.7)"**, 56 strategies. `passes_pbo_global_gate(strict=True)` (`eagle_gates.py:283`) blocks ALL real-money promotion while global PBO≥0.50. **This is a cross-class blocker, not EQUITY-specific** — even a perfect EQUITY cohort cannot promote until the global strategy set is pruned and PBO drops below 0.50. EQUITY strategies present in that matrix: `stocks_rsi2_pullback`, `regime_mild_bear`, `regime_accumulation`, `smart_money_accumulation` (per `per_strategy` list).

### Would EQUITY's current cohort plausibly pass DSR/PBO?

- **DSR (class-aggregate):** YES today (1.0). **DSR (per-strategy promotion gate):** NO — the lead strategy is currently in the DSR noise set at −4.17, but that score is computed on STALE crash data. On the fresh n=20 WR-80% cohort it would very likely flip to survives=True. **It cannot be re-scored without refreshing `dashboard_data.json`, which requires the dashboard generator/DB (not runnable here).**
- **PBO (per-class):** NO — cannot even be computed (1 eligible strategy, need ≥2 at n≥20 and ≥5 for power). To make PBO computable, EQUITY needs at least 2 independent strategies each at n≥20 (and ideally 5 for statistical power).
- **PBO (global):** NO — global PBO=1.0 blocks everything. Independent of EQUITY.
- **MDD:** NO — 33% > gate.
- **Bootstrap CI:** NO — crosses zero.

**Conclusion:** EQUITY is NOT close to passing the full promotion gate today. n→100 alone fixes only one of five failing conditions. The thin edge (PF 1.84 but mean-pnl CI crossing zero, MDD 33%) needs to *widen*, not just *lengthen*.

---

## 4. n→100 path: live emitters, rate, realistic timeline

### Live EQUITY emitters (sourced from `copy_trader_intel/multi_asset_copytrader_scraper.py`)
- `scan_stocks_rsi2_pullback` (`:1249`) → emits `stocks_rsi2_pullback` EQUITY (`:1323`).
- `scan_stocks_ema_momentum` (`:1335`) → `stocks_ema_golden_cross` (`:1364`).
- `yahoo_analyst_consensus` (`:1471`).
- `smart_money_accumulation` (`:2397`).

### Cron cadence (sourced from `.github/workflows/`)
- `multi-asset-scanner.yml`: `cron: '*/30 * * * *'` (every 30 min).
- `copy-trader-intelligence.yml`: `cron: '7,52 * * * *'` (2×/hour).
- `copy-trader-forward-test.yml`: `cron: '17 * * * *'` (resolves outcomes hourly).
- `daily-scrutiny-engine.yml`: `cron: '30 7 * * *'` (per-class scrutiny, DB-dependent).

### Emission/resolution dynamics
- After the 06-06 day-level dedup (commit `cc1f7a89c7`), `smart_money_accumulation` emits **≤1 unique pick per symbol per day** (`signal_timestamp` pinned to start-of-UTC-day, `scraper:2408-2411`). Pre-fix it wrote ~10×.
- `stocks_rsi2_pullback` emits only on non-broad-downswing days (breadth throttle returns empty when >5 symbols are RSI(2)<10-above-200SMA, `:1297`), and only for symbols passing RSI(14)≥30 and not in the 6-symbol blocklist.
- Resolution is fast for these mean-reversion sleeves: EQUITY `hold_days` median 0.8, mean 4.8 (`closed_picks.json`). RSI2 winners resolved same-day (`hold_days` 0 or 0.85) via intrabar replay.

### Realistic clean-n timeline
- Today's clean EQUITY base is **n=71** (registry) / n=49 (fresh closed_picks). Need +29 to +51 to reach 100.
- The two profitable sleeves are producing roughly the post-fix batch we see: ~20 rsi2 + ~14 smart_money across a ~5-day window (06-04..06-09), i.e. **~6–8 clean resolved EQUITY picks/day on active trading days** combined — but heavily clustered (the rsi2 batch was a single oversold-cluster event, not steady state).
- Discounting the clustered batch to a steady-state of **~3–5 clean resolved/day** (mean-reversion sleeves don't fire daily; the throttle suppresses bad days), reaching +29 clean takes **~7–10 trading days** and +51 takes **~12–17 trading days**.
- **Estimate: n=100 clean in ~2–3.5 calendar weeks** IF (a) the resolver keeps stamping v2.1 intrabar exits, (b) no second broad-downswing wipes a week of rsi2 emission, and (c) `smart_money_accumulation` gets moved onto the trusted resolver so its rows count as clean. This is an emitter-rate estimate from the observed 5-day batch, NOT a DB query.

**The binding constraint is NOT emission rate — it is (1) the global PBO=1.0 block, (2) the stale DSR/dashboard inputs, and (3) needing a 2nd independent EQUITY strategy at n≥20 so PBO/single-source become computable + passable.**

---

## 5. Impact of the recent fixes (commits `745b947c1a`, `cc1f7a89c7`)

### `745b947c1a` — rsi2 breadth throttle >5, RSI(14)≥30 floor, 6-symbol blocklist
- **Helps WR:** removes exactly the falling-knife / crash-cluster / chronic-loser picks that produced the WR 29% / DSR −4.17 cohort. The blocklist (GOOGL/WMT/AMZN/UNH/QCOM/PEP) targeted 0–17% WR symbols.
- **n-growth cost:** SMALL and ASYMMETRIC. The throttle returns empty only on broad-downswing days (those are the lowest-WR days). RSI(14)≥30 and the blocklist remove a minority of setups. Net: it removes more *losers* than *winners*, so it raises clean-n quality and arguably reaches a *passing* n=100 faster (you stop padding n with picks that fail DSR).
- **Net:** clearly net-positive for T2. The only risk is over-tightening if a real pullback day shows 6 oversold symbols — but the commit message documents the >5 threshold was calibrated on May 7-12 good-day unique counts (4-6) vs crash counts (6-8).

### `cc1f7a89c7` — smart_money day-level dedup, RENDERUSDT kill, forex NULL guard, DXY gate
- **The smart_money dedup HELPS data integrity, does NOT hurt n.** It removes ~10× *duplicate* rows that were artificially inflating apparent WR (and apparent n) — those duplicates were never independent trades. After dedup, n drops to the true unique count, which is the honest base for T2. So it *lowers raw n* but the lost rows were fake; clean n is unaffected or more accurate.
- **Net:** net-positive. It directly addresses the "single batch / 10× write-duplication artifact" failure mode the repo memory repeatedly flags.

### Tradeoff summary
There is **no real tradeoff**: both fixes remove low-quality picks (crash-day losers + duplicate inflation), which *raises* the WR/PF of the clean cohort and makes the eventual n=100 a *passing* n=100 rather than a padded one. The slower raw-n growth is illusory — it was padding that would have failed DSR/single-source anyway.

---

## 6. RANKED next actions — grow clean n WITHOUT degrading 53.5% / 1.84

> Ranked by (edge protection × n-acceleration) ÷ risk. Items 1–3 are the high-leverage moves; 4–6 are supporting.

### #1 — Quarantine the two confirmed EQUITY bleeders (`regime_terminal`, `cta_replicator`) from the EQUITY clean cohort
- **Why:** they are 23/71 picks (32%) at WR 17.6% / 0% and drag total_pnl by −0.50. Removing them lifts EQUITY WR ~53.5%→~71% and PF ~1.84→>3, and *reduces* the n you need from clean *winners* to clear the WR/PF floors with margin.
- **Evidence:** `pf_registry.json` EQUITY rows (§1a). `cta_replicator` `top_source: "cta_replicator"` single-source, 0 wins. `regime_terminal` `top_source: "regime_terminal"` single-source, WR 17.6%.
- **How (safe):** add `regime_terminal::EQUITY` and `cta_replicator::EQUITY` to `BANNED_SOURCES` per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate-before-kill). **Requires the mutation-analysis step before kill** — do not expand BLOCKED_SOURCE_SYSTEMS without it (CLAUDE.md Key Commands). Defer the actual edit to the operator pending mutation export (DB-gated).
- **Risk:** LOW for WR/PF; but n drops by 23 raw. Net positive because those 23 were failing every quality gate.

### #2 — Refresh the STALE gate-input files so the post-fix wins are scored (unblocks per-strategy DSR + makes the verdict trustworthy)
- **Why:** the binding promotion gate reads `dashboard_data.json` (06-03, stale) → `deflated_sharpe_results.json` (06-06, pre-fix, `stocks_rsi2_pullback` DSR −4.17). The fresh `closed_picks.json` (06-09) shows the SAME strategy at n=20 WR 80%. Until these propagate, the harness will keep failing EQUITY's lead strategy on dead crash data.
- **How:** this is a **workflow/operator action**, not a local edit — `dashboard_data.json` is regenerated by `audit-dashboard.yml` (`cron '10 * * * *'`) + the DB; `cpcv_pbo_results.json` needs `tools/build_cpcv_pbo_results.py` which is `pymysql`-gated (line 20). I CANNOT run these (DB unreachable, and CLAUDE.md forbids running dashboard generators locally). **Action for operator:** confirm `audit-dashboard.yml` and the DSR/PBO regen ran AFTER 06-06, then re-read `money_ready_verdict.json`.
- **Risk:** none (read/refresh only). Highest leverage of all items — it may flip `single_source.ok` and `pbo` from null once 2+ EQUITY strategies are scored on fresh data.

### #3 — Promote `smart_money_accumulation` to the TRUSTED resolver (v2.1 intrabar) so it counts as a 2nd clean EQUITY strategy
- **Why:** PBO and the single-source gate are uncomputable/failing precisely because only ONE EQUITY strategy reaches n≥20 on trusted data. `smart_money_accumulation` has n=14 (close to 20) but ALL 14 rows are `resolved_by=None / resolver_version=None` (lower-trust path) → they don't count toward the clean cohort the gates trust. Getting it onto `non_crypto_resolver v2.1` (intrabar OHLC replay) would give EQUITY a 2nd independent strategy, making PBO computable and the single-source gate passable (multi-strategy edge).
- **Evidence:** `closed_picks.json` per-strategy resolver Counters (§1b).
- **How (operator/DB):** ensure the resolver picks up `smart_money_accumulation` EQUITY rows; verify `entry_date` is populated (8/14 are None now → they may be silently dropped by the registry's `trade_date_fallback`). Investigate the `entry_date=None` rows first — that is a likely emitter bug worth a small EQUITY-scoped fix.
- **Risk:** LOW; do NOT size on the provisional 93% WR until intrabar-resolved.

### #4 — Add a 2nd genuinely-independent EQUITY strategy to reach the PBO power threshold (≥5 strategies at n≥20 is ideal; ≥2 minimum)
- **Why:** even with rsi2 + smart_money, PBO has near-zero power below 5 strategies (`money_ready_verdict.py:899`). Candidates already emitting: `momentum_rider_base` (PF 10.25 but n=3), `vt_equity_two_day_rsi_reversal` (WR 100% n=4), `yahoo_analyst_consensus` (`scraper:1471`, n not found in EQUITY clean snapshots). Grow these toward n≥20.
- **Risk:** MEDIUM — must verify each is multi-symbol and not a single-batch artifact before counting (per the BTCUSDT-batch failure mode).

### #5 — Fix the BOND/crypto miscategorization polluting EQUITY
- **Why:** `closed_picks.json` EQUITY contains `bond_yield_momentum` (n=3) and `cta_cross_asset_tsmom` (n=6); the symbol view contains `WLD-USD`, `XLM-USD`, `HYPE-USD` (crypto) tagged EQUITY. These add noise to the EQUITY DSR/MDD aggregate.
- **How:** EQUITY-scoped `asset_class` re-tag in the resolver/registry (cite the exact rows). Small, safe, but verify against DB before committing.
- **Risk:** LOW.

### #6 — Track EQUITY in the paper-forward pilot (currently absent)
- **Why:** `pilot_forward_dashboard.json` (06-06) has sleeves for ETF/crypto/faber/bootstrap but **no EQUITY sleeve**. EQUITY has zero verified forward track — its entire case rests on policy-clean resolved picks. A forward pilot for `stocks_rsi2_pullback` (the cleanest sleeve) would build sizing-grade n in parallel with the live cohort and is the only path to "verified paper forward" trust-tier evidence.
- **How:** add an EQUITY sleeve to the pilot loop (mirror the ETF sleeve pattern). Opt-in sidecar, flag default OFF, per the Wire-Up Rule.
- **Risk:** LOW (sidecar).

---

## 7. No code edit made this session

I evaluated making a safe local edit (e.g. re-running `tools/deflated_sharpe.py` to refresh the DSR file), but it would read the STALE `dashboard_data.json` (2026-06-03) — so it would NOT pick up the post-fix wins and could *overwrite* the DSR file with equally-stale numbers under a fresher timestamp, masking the staleness. **Refreshing the DSR file is only valuable after `dashboard_data.json` itself is regenerated (DB/workflow, operator action #2).** Actions #1, #3, #5 require the mutation-before-kill protocol and/or DB verification (CLAUDE.md), which are operator-gated. I therefore made no edit and leave the ranked actions for the operator.

---

## Source files cited (all read this session)
- `audit_dashboard/data/money_ready_verdict.json` (2026-06-08) — `classes.EQUITY.*`, `details.*`, `drift.per_class.EQUITY`, `summary`.
- `audit_dashboard/data/pf_registry.json` (2026-06-06) — `by_asset_class_strategy_policy_clean_net`, `by_asset_class_policy_clean_net`, `by_asset_class_strategy_symbol`, `methodology`, `counts`.
- `alpha_engine/data/closed_picks.json` (2026-06-09) — per-strategy n/WR/resolver/exit_reason/hold_days/pnl_pct.
- `audit_dashboard/data/dashboard_data.json` (2026-06-03, STALE) — `picks.recent_closed` (DSR input).
- `tools/deflated_sharpe_results.json` (2026-06-06) — `stocks_rsi2_pullback` DSR −4.17.
- `tools/cpcv_pbo_results.json` (2026-06-02) — global PBO 1.0.
- `audit_dashboard/data/pilot_forward_dashboard.json` (2026-06-06) — no EQUITY sleeve.
- `audit_dashboard/data/top_notch_money_ready.json` (2026-06-06) — EQUITY top_notch, "Watch promotion_gate + DSR/PBO".
- `audit_dashboard/data/pick_summary_stats_{14d,48h}.json` (trend direction only, NOT sizing-grade).
- `alpha_engine/eagle_gates.py`, `alpha_engine/money_ready_verdict.py`, `copy_trader_intel/multi_asset_copytrader_scraper.py`, `.github/workflows/*.yml`.
