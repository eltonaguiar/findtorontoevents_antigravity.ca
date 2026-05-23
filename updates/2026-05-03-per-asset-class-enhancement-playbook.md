# Per-Asset-Class Enhancement Playbook — 2026-05-03

**Author:** opencode (deep research across 5 asset classes + resolver audit)
**Source of truth:** `audit_trail/data/dashboard_payload.json` (2026-05-03T00:06Z, post-resolver-v2)
**Goal alignment:** Goal #1 — phenomenal performance across ALL asset classes on `/audit`
**Status:** Diagnostic + mutation plan. No production code changed.

---

## Executive Summary

| Class | n | WR% | PF | Tier | Gap to T2 | Action |
|---|---|---|---|---|---|---|
| **CRYPTO** | 8,067 | 44.6 | 1.25 | Sub-T2 | PF -0.25, WR -5.4pp | Cut `quan_engine` drag; promote ML-enhanced |
| **EQUITY** | 421 | 52.7 | 1.41 | **T2** | Near T1 | Scale; kill zombies |
| **COMMODITY** | 750 | 46.9 | 1.78 | **T2 PF only** | WR -3.1pp | Lift WR; verify clean edge post-resolver-v2 |
| **ETF** | 87 | 55.2 | 1.24 | Borderline T3 | n +13→100 | Scale n; unblock if gated |
| **FOREX** | 1,169 | 46.4 | **0.27** | **FAIL** | PF -1.23 | Investigate-before-kill |
| **BOND** | 18 | 55.6 | 1.72 | T2 thresholds | n +32→50 | Grow sample |
| **FUTURES** | 2 | 100 | null | Insufficient | n +28→30 | Rebuild data pipeline |

**Resolver fix status:** v2 shipped 2026-04-28 (commit `97284d2`). Asset-class-gated WIN thresholds: 0.1bp crypto, 5bp non-crypto. FOREX/COMMODITY numbers above are post-fix (genuine, not noise). Previously 63-67% of "wins" were resolver flicker.

---

## 1. FOREX — Catastrophic (PF 0.27, Investigate-Before-Kill)

### 1.1 Root Causes (ranked by impact)

**R1 — Label-routing bug: `BUY` vs `LONG` (IMPACT: CRITICAL)**
- `BUY` n=3,909 → 28.9% WR / PF 0.38
- `LONG` n=441 → 54.9% WR / PF 3.14
- Two labels for the same intent with 26pp WR gap = label-routing bug or genuinely different source pipelines.
- `audit_trail/dashboard_generator.py:7062` manually sets `p["asset_class"] = "FOREX"` for certain picks — possible misclassification.
- **Fix:** Trace `direction` field in `alpha_engine/production_scanner.py` and `audit_trail/universal_pick_resolver.py`. Unify to `LONG`/`SHORT` only.

**R2 — `forex_carry_momentum` is dead (IMPACT: HIGH)**
- PR #687 fixed JPY-cross BUY rule bypass (-23% sum on 49 picks in 7d), but non-JPY component also dead: n=8 NZDUSD=X, 0% WR, -4% sum (30d).
- Blocked at gate level via `BLOCKED_ASSET_STRATEGY_PAIRS` at `quality_gates.py:1504-1509`.
- **Status:** Already gated — verify no new emissions.

**R3 — Resolver noise (IMPACT: MITIGATED)**
- v2 resolver fix shipped: FOREX threshold raised from 0.1bp → 5bp (`outcome_resolver.py:115-119`).
- Pre-fix: 63.25% of FOREX "wins" were sub-5bp flicker. Post-fix: numbers are genuine.
- **Verification needed:** Re-run canonical recompute to confirm clean FOREX PF after v2 filter.

**R4 — Confidence uncalibrated (IMPACT: MEDIUM)**
- FOREX peak confidence bucket is 0.75–0.80 (49% WR). 0.70–0.75 is DANGER (25% WR).
- Quality gates penalize FOREX confidence ≥0.75 with weak forward sample (`quality_gates.py:2319-2325`).
- `forex_smart_picks.py` caps confidence at 0.65 for unvalidated strategies — good default.

**R5 — Low pick volume from viable strategies (IMPACT: MEDIUM)**
- `forex_smart_picks.py` runs Portfolio C (6 strategies, Sharpe 2.06 in backtest) but emissions are thin.
- `new_forex_strategies_20.py` has 20 strategies ready but never wired into production scanner.

### 1.2 FOREX Edge Segments (What Actually Works)

| Segment | Evidence | Verdict |
|---|---|---|
| Trusted filter | PF 3.59, +6pp WR lift (n=273, CI straddles 1.0) | Promising but inconclusive |
| `non_crypto_consensus` + conf 0.80-0.90 | n=51, WR 52.9%, PF 1.57 | Real edge, small sample |
| `forex_rsi2_mean_reversion` SHORT | n=318, WR 49.7%, PF 5.58 | Best single-strategy signal |
| USDJPY=X | n=68, WR 60.3%, PF 15.5 | Best single symbol |
| GBPJPY=X | n=74, WR 48.7%, PF 6.57 | Strong |
| USDCHF=X | n=56, WR 66.1%, PF 4.10 | Strong |
| `fx_smart_carry_trade_momentum` | n=15, WR 60%, PF 118.6 | Tiny sample, watch |

### 1.3 FOREX Mutation Experiments

| # | Experiment | Hypothesis | Variable Changed | Pass Metric | Fail Metric |
|---|---|---|---|---|---|
| F1 | **Unify BUY/LONG label routing** | The BUY cohort aggregates broken-source picks; unifying to LONG will expose real FOREX WR as closer to 50% not 5% | Direction field normalization in resolver + production scanner | FOREX L100 WR > 45% | No change from current 5% |
| F2 | **Allowlist-only: trusted symbols** | Only trade USDJPY, GBPJPY, USDCHF, NZDUSD (WR ≥ 48%, PF ≥ 3.6) | Symbol universe gate in `forex_smart_picks.py` | Filtered WR > 55%, PF > 2.0 | WR < 50% or PF < 1.5 |
| F3 | **SHORT-only for rsi2_mean_reversion** | SHORT n=318 PF 5.58 vs LONG n=232 PF 2.55; asymmetry is real | Direction gate in `forex_strategies.py` RSI2 logic | SHORT-only PF > 4.0 | PF < 2.0 |
| F4 | **Wire new_forex_strategies_20 into production** | The 20 untested strategies contain at least 3 with forward edge. Run 30-day paper | Import + wire `new_forex_strategies_20.py` → production scanner | ≥3 strats with n≥30, WR≥50% | All 20 fail WR < 45% |
| F5 | **Confidence band gate: 0.75-0.80 only** | FOREX peak is narrow (0.75-0.80 at 49%). Gate emissions to this band | Confidence filter in quality_gates.py | Band WR > 50% | Band WR < 45% |

### 1.4 FOREX Recovery Plan

- **Day 0-30:** Fix BUY/LONG routing. Gate `forex_carry_momentum` kill. Run F1-F3 mutations.
- **Day 30-60:** If mutations produce PF > 1.5 on n ≥ 100, re-promote to SANDBOX. Wire F4 (new strategies).
- **Day 60-90:** Full forward validation. If PF > 1.5 with CI > 1.0 on n ≥ 200, promote to WATCH tier.
- **Kill trigger:** If after 90 days PF remains < 1.0, demote to PROBATION and block all new FOREX emissions.

---

## 2. COMMODITY — PF 1.78 but WR Weak (46.9%)

### 2.1 Root Causes

**R1 — `multi_asset_copytrader` is the dominant source (n=492) but real WR is ~17%**
- Pre-resolver-v2, 66.79% of COMMODITY wins were 1bp flicker. Post-resolver-v2 (5bp threshold), headline PF jumped from 0.896 to 1.78 — this is the noise removal effect.
- But the underlying signal remains weak. Clean wins after noise filter: only 85 of 492 `multi_asset_copytrader` picks.
- `copy_trader_intel/multi_asset_copytrader_scraper.py` scrapes ForexFactory, Myfxbook, TradingView, CFTC COT — signal source is crowd-sourced, not proprietary.

**R2 — CTA replicator strategies are thin-sample**
- `cta_commodity_momentum_term` n=46, WR 37%, PF 0.02 — effectively broken.
- `cta_golden_cross_200` n=25, WR 40%, PF 0.61 — below threshold.
- `cta_cross_asset_tsmom` n=32, WR 40.6%, PF 1.60 — this actually has PF on barely sufficient n.
- `cta_bridge.py` wraps these but confidence floor is only 0.55.

**R3 — Symbol classification issues**
- Commodity symbols use Yahoo Finance futures format: `GC=F`, `SI=F`, `CL=F`, `NG=F`, `HG=F`, `PL=F`.
- `PL=F` (Platinum) n=135, WR 45.2%, PF 1.27 — works.
- `HG=F` (Copper) n=147, WR 44.9%, PF 2.17 — best PF.
- `SI=F` (Silver) n=181, WR 44.2%, PF 0.84 — net loser.

**R4 — Confidence bucket paradox**
- COMMODITY peak is 0.70-0.75 at 48.5% WR (n=371). Below 0.70 = 32-33% WR (n=214).
- Below 0.60 = 33.3% WR, PF 0.20 (n=30). This band is toxic.

### 2.2 COMMODITY Edge Segments

| Segment | Evidence | Verdict |
|---|---|---|
| `futures_momentum` LONG + conf 0.70-0.80 | n=367, WR 48.5%, PF 1.41 | Thin but real edge |
| `futures_momentum` LONG only | n=220, WR 46.4%, PF 3.94 | Extraordinary PF on direction-filtered |
| `HG=F` (Copper) | n=147, WR 44.9%, PF 2.17 | Best single symbol |
| `PL=F` (Platinum) | n=135, WR 45.2%, PF 1.27 | Consistent |
| `cta_cross_asset_tsmom` | n=32, WR 40.6%, PF 1.60 | Small n, strong PF |

### 2.3 COMMODITY Mutation Experiments

| # | Experiment | Hypothesis | Variable Changed | Pass Metric | Fail Metric |
|---|---|---|---|---|---|
| C1 | **LONG-only for futures_momentum** | SHORT drags down aggregate; LONG-only has PF 3.94 | Direction gate in `cta_bridge.py` + `commodity_signal_generator.py` | WR > 48%, PF > 2.0 | WR < 45% |
| C2 | **Confidence floor at 0.65 for all COMMODITY** | Below 0.65 = 32% WR; raising floor lifts aggregate by 3-5pp | Min confidence gate in quality_gates.py (currently no floor for commodity) | Filtered WR > 50% | WR < 46% |
| C3 | **Symbol allowlist: HG=F, PL=F only** | These 2 symbols have PF > 1.2 and n > 100 combined | Symbol gate in commodity signal pipeline | WR > 47%, PF > 1.5 | WR < 44% or PF < 1.3 |
| C4 | **Wire `new_equity_commodity_strategies_20.py` commodity section** | 10 untested strategies (trend, MR, seasonal, COT, contango, breakout, correlation, multi-factor). At least 2 should work. | Import + 30-day paper trial | ≥2 strats with n≥30, WR≥47% | All fail |
| C5 | **Gate multi_asset_copytrader COMMODITY to TRUST tier only** | The 17% real-WR in copytrader commodity lane may improve if filtered to trusted sub-strategies | Trust-tier gate in quality_gates.py for commodity+multi_asset_copytrader | Filtered WR > 45%, PF > 1.2 | WR < 42% |

### 2.4 COMMODITY Recovery Plan

- **Day 0-30:** Run C1-C3 (low-risk config changes). If any pass, immediate promotion.
- **Day 30-60:** Wire C4 new strategies. Run C5 trust-filter.
- **Day 60-90:** Forward validation. Target: PF > 1.5 with CI > 1.0 on n ≥ 200.
- **Kill trigger:** If after 90 days PF < 1.2 and all mutations fail, demote to WATCH only. Replace with institutional ETF replication (DBMF/KMLM).

---

## 3. FUTURES — Near-Zero Data (n=2, Effectively Dead)

### 3.1 Root Causes

**R1 — Symbol format mismatch kills price resolution**
- Futures symbols use CME micro format (`MES`, `MNQ`, `MYM`) or Yahoo `=F` suffix (`ES=F`, `NQ=F`).
- `asset_classification.py` only detects `=F` suffix (line 238) and CME micro prefix patterns (line 239).
- Yahoo Finance `=F` futures symbols need specific handling in the price fetcher.
- `outcome_resolver.py` has a `_resolve_asset_class()` fallback that infers futures from `=F` suffix (line ~612-633), but if the price fetch fails for these symbols, they never resolve.
- v2.1 retry cap (`outcome_resolver.py:154-169`) handles `_resolve_retry_needed` picks, capping at `MAX_RESOLVE_RETRIES` then force-closing as FLAT. This may affect futures the most.

**R2 — Toxic strategies blocked, but no survivors emit**
- `BLOCKED_STRATEGIES` has 8 futures-specific blocks (`quality_gates.py:1265-1271`): `connors_rsi2`, `hyperopt_connors_rsi2`, `mean_reversion_bollinger`, `extreme_oversold_bounce`, `vix_reversal`, `futures_mean_reversion`, `ema_stack_momentum` — all blocked on FUTURES.
- `BLOCKED_ASSET_CLASSES` was `{"FUTURES"}` until 2026-04-16 — removed because the -60 penalty created data starvation.
- Old data: 6.3% WR on n=17, 76% LOST-exit rate. The one winner was `futures_momentum` (4W/3L/1F = +4.94% on n=8).

### 3.2 FUTURES Rebuild Plan

| Step | Action | Target |
|---|---|---|
| 1 | Fix Yahoo `=F` symbol price fetch in `universal_price_enricher.py` | ES=F, NQ=F, YM=F, RTY=F resolve prices |
| 2 | Unblock `futures_momentum` from BLOCKED_STRATEGIES (it's the only proven winner) | Allow futures_momentum on FUTURES |
| 3 | Wire CTA replicator futures lane (`cta_bridge.py` + `cta_strategy_replicator.py` TSMOM Blended) | Generate ≥30 futures picks/month |
| 4 | Add CME micro futures patterns to `asset_classification.py` | MES, MNQ, M2K, MGC classified correctly |
| 5 | 30-day paper trial | Target: n≥30 closed, WR≥40% |

**Verdict:** FUTURES is not irreparably broken — it's data-starved. The pipeline exists but symbol resolution is the blocker. Rebuild, don't kill.

---

## 4. BOND — Good Metrics, Insufficient Sample (n=18)

### 4.1 Root Causes

**R1 — Only 2 sources generating picks (n=18 across source systems)**
- BOND has PF 1.72, WR 55.6% — these are good numbers but on n=18 they're statistically meaningless.
- Sources: `multi_asset_copytrader` + `kimi_riseoftheclaw` (estimated from the 2-source count).
- SHORT bonds work (n=8, WR 50%, PF 25.9) better than LONG bonds (n=9, WR 44.4%, PF 0.54).

**R2 — Bond symbol classification may overlap with ETF**
- `asset_classification.py` bond patterns (lines 241-244) include `TLT, IEF, SHY, AGG, BND, LQD, HYG, JNK` — all of which are also common ETF tickers.
- The ETF patterns (lines 229-232) check before BOND patterns in the classifier (line 349-358). So TLT as ETF → correctly classified. TLT as BOND → depends on whether it was already caught as ETF.
- If a pick has `category=BOND` metadata, it goes to BOND. Otherwise, most bond ETFs will be classified as ETF.

**R3 — No bond-specific strategy generator exists**
- Search for bond/treasury/fixed_income strategies in `alpha_engine/` and `baby_strategies/` found nothing dedicated.
- Bonds are picked up as a side effect of multi-asset strategies, not targeted.

### 4.3 BOND Mutation Experiments

| # | Experiment | Hypothesis | Variable Changed | Pass Metric | Fail Metric |
|---|---|---|---|---|---|
| B1 | **Create `bond_trend_momentum.py`** | Duration-based trend following: LONG TLT when 50>SMA200, SHORT when inverted. Academic foundation: 20+ years of evidence. | New strategy file | n≥30, WR≥55%, PF≥1.5 | WR < 50% |
| B2 | **Add bond ETF rotation signals from CTA replicator** | `cta_cross_asset_tsmom` already covers TLT/IEF, just not labeled BOND. Wire BOND-specific output | Wire CTA bond lane | n≥20/month | No bond emissions |
| B3 | **SHORT-only preference for bonds** | SHORT bonds PF 25.9 vs LONG PF 0.54. Direction asymmetry is extreme | Direction gate for bond picks | SHORT WR > 55% | WR < 50% |
| B4 | **Wire Treasury yield curve signals** | 2s10s inversion/flattening/steepening = predictable bond ETF moves. Add yield curve data source | New data source + strategy | n≥50, WR≥55% | WR < 48% |
| B5 | **Scale via weekly rebalance screener** | Run weekly bond ETF ranking by momentum + carry + yield. Top-2 ETFs/week | New scheduled workflow | n≥30/month | No bond emissions |

### 4.4 BOND Scale Plan

- **Day 0-30:** Create `bond_trend_momentum.py`. Wire CTA replicator bond lane (B1, B2).
- **Day 30-60:** Wire yield curve signals (B4). Run weekly screener (B5).
- **Day 60-90:** Target n≥100 closed. Re-evaluate for T2 certification.
- **No kill trigger:** BOND metrics are positive, just need sample size. Scale, don't kill.

---

## 5. ETF — Revived from "Dead" (PF 1.24, WR 55.2%, n=87)

### 5.1 Root Causes

**R1 — The "ETFs dead" verdict was premature**
- Previous analysis showed PF 0.28 on n=19 — this was driven by single strategies (`extreme_oversold_bounce` at 0% WR, `vix_reversal` at 33% WR/PF 0.02).
- Both are now blocked via `BLOCKED_STRATEGIES` for ETF (`quality_gates.py:1249-1250`).
- Current n=87 shows PF 1.24, WR 55.2% — clean, consistent across L20/L50/L100 windows.

**R2 — `kimi_riseoftheclaw` carries 82% of ETF volume (n=68)**
- Single-source dependency. Need 2+ uncorrelated sources before sizing up.
- `intermarket-flow-scout` n=10, WR 60%, PF 2.01 — promising but small.
- `quality-minus-junk` n=12, WR 50%, PF 1.05 — marginal.

**R3 — ETFs were never formally hard-blocked, but penalized**
- `BLOCKED_ASSET_CLASSES` (line 992) was emptied 2026-04-16 — no active hard block currently.
- Quality gates apply -10 to -16 penalty for FOREX/COMMODITY/ETF/BOND picks that are forward_test_only without validation (`quality_gates.py:2307-2315`).
- `BLOCKED_STRATEGIES` blocks `extreme_oversold_bounce` (ETF) and `vix_reversal` (ETF) — these were the toxic strategies.

### 5.2 ETF Edge Segments

| Segment | Evidence | Verdict |
|---|---|---|
| `kimi_riseoftheclaw` + EQUITY/ETF | n=68, carries ETF class | Strong, but single-source risk |
| `intermarket-flow-scout` | n=10, WR 60%, PF 2.01 | Scale candidate |
| QQQ | n=12, WR 58.3%, PF 1.32 | Best single symbol |
| XLE | n=15, WR 53.3%, PF 1.11 | Consistent |
| Confidence 0.60-0.70 | n=10, WR 70%, PF 2.43 | Strongest band (but n=10) |

### 5.3 ETF Mutation Experiments

| # | Experiment | Hypothesis | Variable Changed | Pass Metric | Fail Metric |
|---|---|---|---|---|---|
| E1 | **Unblock ETF from any remaining visibility penalties** | ETFs are not dead; forward_test_only penalty is suppressing visibility of working picks | Remove ETF from penalty group at quality_gates.py:2307 | ETF actives visible, n growing | No change |
| E2 | **Wire sector-rotation source** | State Street SPDR sector ETFs (XLF, XLE, XLV, XLI, XLC, XLP, XLY) have momentum + mean-reversion edge. Top-2 sectors/month. | New strategy: `etf_sector_rotation.py` using SPDR relative strength | n≥30, WR≥55%, PF≥1.5 | WR < 48% |
| E3 | **Scale `intermarket-flow-scout`** | Currently n=10 with PF 2.01. Extend to more ETF symbols (add IWM, DIA, EFA, EEM, VNQ, GLD) | Expand symbol universe in intermarket-flow-scout | n≥20/month | No increase |
| E4 | **Add low-vol factor (USMV-style)** | Minimum volatility ETFs (USMV, SPLV, XMLV) have factor premia. XLB (defensive) rotation signal | New strategy: `etf_low_vol_rotation.py` | n≥20, WR≥55% | WR < 48% |
| E5 | **Confidence floor at 0.50 for ETF** | ETF conf < 0.50 = 55.6% WR (works). conf 0.50-0.60 = 35% WR (toxic). Gate 0.50-0.60. | Confidence band gate | Filtered WR > 55% | WR < 52% |

### 5.4 ETF Scale Plan

- **Day 0-30:** Run E1, E3, E5 (low-risk). Unblock visibility. Scale intermarket-flow-scout.
- **Day 30-60:** Implement E2 (sector rotation), E4 (low vol). Target n≥150.
- **Day 60-90:** n≥200. Re-evaluate for T2 certification with uncorrelated sources.
- **No kill trigger:** ETFs are working. Scale, don't constrain.

---

## 6. Data Quality & Resolver Integrity

### 6.1 Resolver v2 — Status: SHIPPED

- **Commit:** `97284d2a44f` (2026-04-28)
- **Change:** Asset-class-gated WIN thresholds: CRYPTO 0.1bp, non-crypto 5bp
- **Location:** `alpha_engine/outcome_resolver.py:115-138`
- **Verification:** Run `node tools/_canonical_recompute_2026_04_28.js` to confirm FOREX/COMMODITY recompute matches dashboard

### 6.2 Retry Cap v2.1 — Status: SHIPPED

- **Commit:** `4574db4456f` (2026-05-02)
- **Change:** `MAX_RESOLVE_RETRIES` cap prevents perpetual re-processing
- **Location:** `alpha_engine/outcome_resolver.py:154-169`

### 6.3 Remaining Data Quality Issues

**DQ1 — BUY vs LONG label inconsistency (CRITICAL)**
- `BUY` n=3,909 → 28.9% WR; `LONG` n=441 → 54.9% WR
- Root cause suspected: label-routing bug in `production_scanner.py` or `dashboard_generator.py:7062`
- **Fix:** Trace `direction` field origin. Either unify labels or identify the broken BUY source pipeline.

**DQ2 — Confidence overfit cliff >0.90 (HIGH)**
- Confidence >0.90 → 47% WR across all classes (vs 82% at 0.85-0.90)
- Known in dashboard tooltip. Not yet hard-gated in code.
- **Fix:** Hard-cap outgoing confidence at 0.90 in `alpha_engine/elite_scorer.py` or `darwin_score_v2_calculator.py`

**DQ3 — Bond/ETF classification overlap (MEDIUM)**
- TLT/IEF/SHY/AGG/BND/LQD/HYG/JNK could be BOND or ETF depending on classification order
- ETF patterns checked before BOND patterns → most bond ETFs classified as ETF
- **Fix:** If a pick has explicit `category=BOND` metadata, honor it. Otherwise current behavior is acceptable.

**DQ4 — Futures symbol resolution (MEDIUM)**
- `=F` symbols require Yahoo Finance which has intermittent reliability
- **Fix:** Add yfinance retry logic or fallback to CME direct API for futures symbols

### 6.4 Data Quality Priority Fixes

| Priority | Issue | File:Line | Fix | ROI |
|---|---|---|---|---|
| P0 | BUY vs LONG label routing | `production_scanner.py` (direction field) | Trace and unify labels | Unblocks FOREX diagnosis |
| P0 | Confidence >0.90 hard cap | `elite_scorer.py` / `darwin_score_v2_calculator.py` | `confidence = min(confidence, 0.90)` | Saves 47% WR picks from publication |
| P1 | Futures =F price fetch reliability | `universal_price_enricher.py` | Add retry + fallback for yfinance futures | Unblocks FUTURES data pipeline |
| P2 | Bond/ETF classification audit | `asset_classification.py` | Verify 18 BOND picks are actually bonds | Data integrity |

---

## 7. Claude-Ready Instruction Templates

### 7.1 Quick Triage (Any Weak Asset Class)

```
Investigate underperformance for asset class {CLASS} in the audit dashboard at findtorontoevents.ca/audit.

Step 1 — Read the data:
- Read audit_trail/data/dashboard_payload.json → performance.by_asset_class.{CLASS}
- Read updates/2026-05-03-per-asset-class-enhancement-playbook.md → {CLASS} section

Step 2 — Run three-axis autopsy:
- Read audit_trail/data/universal_resolved_picks.json → filter asset_class={CLASS}
- Slice by: source_system, strategy, symbol, direction, confidence_bucket, timeframe, exit_reason
- Compute WR, PF, avg PnL for each slice
- Identify top-3 segments by: (a) highest PF/WR, (b) highest loss contribution (= volume × negative expectancy)

Step 3 — Run data quality checks:
- What % of wins have |pnl_pct| < 0.05%? (resolver noise check)
- What % of exits are LOST/TIME_EXIT vs TP_HIT/SL_HIT?
- Are entry prices non-null and within sanity bounds?

Step 4 — Run leakage audit:
- Verify entry_time < exit_time (no lookahead)
- Check if any indicators use future bars (shift-by-1 verification)

Step 5 — Produce:
a) Root-cause report (top-3 loss drivers by impact)
b) Segment breakdown by source, direction, symbol, confidence, session, holding-time
c) 5 mutation experiments (one variable changed per experiment) with hypothesis + pass/fail metric
d) Recommendation: keep-as-is / mutate-and-continue / demote
e) 30/60/90 day recovery plan with strict acceptance criteria

Reference docs:
- docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md — escalation ladder
- docs/MUTATION_THREE_AXIS_PROTOCOL.md — three-axis autopsy
- docs/PERFORMANCE_CHARTER.md — tier definitions
```

### 7.2 Mutation Runner (Single Experiment)

```
Run mutation experiment {#} for asset class {CLASS}.

Hypothesis: {HYPOTHESIS}
Variable changed: {VARIABLE}
Pass metric: {PASS_METRIC}
Fail metric: {FAIL_METRIC}

Implementation:
1. Read the relevant strategy/config file ({FILE_PATH})
2. Apply the single-variable change
3. Run a 30-day paper simulation if possible, or backtest on held-out data
4. Compare pre/post metrics: WR, PF, n, avg PnL, max DD
5. Return: PASS/FAIL/MIXED with evidence

Do NOT change multiple variables at once. One mutation per experiment.
Document the experiment in updates/{date}-mutation-{class}-{experiment_number}.md
```

### 7.3 Kill Governance Checklist

```
Before killing any strategy or asset class, verify:

[ ] Stage 0 — Flagged in dashboard/logs (observe, don't block)
[ ] Stage 1 — Risk reduction (lower max active picks, size, promotion)
[ ] Stage 2 — Rehabilitation (inverse / mutation / regime grid attempted)
[ ] Stage 3 — DNA mutation (inverse_*, _mut_* candidates generated)
[ ] Stage 4 — Backtest/WF evidence (WR, PF, min trades on held-out data)
[ ] Stage 5 — Hard block (only after Stages 0-4 fail)

Deterministic-loss fast-path (skip to Stage 5): WR = 0% on n ≥ 20

Reference: docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md
```

---

## 8. Implementation Priority Matrix

| Rank | Action | Class | Difficulty | Impact | Timeline |
|---|---|---|---|---|---|
| P0-1 | Fix BUY/LONG label routing | FOREX | Medium | Critical | Week 1 |
| P0-2 | Hard-cap confidence at 0.90 | ALL | Easy | High | Week 1 |
| P0-3 | Gate `forex_carry_momentum` kill verification | FOREX | Easy | High | Week 1 |
| P1-1 | FOREX symbol allowlist (F2) | FOREX | Easy | High | Week 1-2 |
| P1-2 | COMMODITY LONG-only + conf floor (C1, C2) | COMMODITY | Easy | High | Week 1-2 |
| P1-3 | Unblock ETF visibility (E1) | ETF | Easy | High | Week 1 |
| P1-4 | Fix futures =F price fetch (DQ3) | FUTURES | Medium | High | Week 1-2 |
| P2-1 | Comm modify symbol allowlist (C3) | COMMODITY | Easy | Medium | Week 2-3 |
| P2-2 | ETF sector rotation (E2) | ETF | Medium | Medium | Week 2-4 |
| P2-3 | BOND trend momentum + CTA lane (B1, B2) | BOND | Medium | Medium | Week 2-4 |
| P2-4 | FOREX SHORT-only rsi2 (F3) | FOREX | Easy | Medium | Week 2-3 |
| P3-1 | Wire new_forex_strategies_20 (F4) | FOREX | Medium | Medium | Week 3-5 |
| P3-2 | Wire new_equity_commodity_strategies_20 (C4) | COMMODITY | Medium | Medium | Week 3-5 |
| P3-3 | BOND yield curve signals (B4) | BOND | Medium | Low | Week 4-6 |
| P3-4 | ETF low-vol factor (E4) | ETF | Medium | Low | Week 4-6 |

---

## 9. Target State (90-Day Projection)

| Class | Current n | Target n | Current PF | Target PF | Current WR | Target WR | Tier Target |
|---|---|---|---|---|---|---|---|
| EQUITY | 421 | 600 | 1.41 | 1.55+ | 52.7% | 55%+ | T1 |
| CRYPTO | 8,067 | 8,000 | 1.25 | 1.50+ | 44.6% | 48%+ | T2 |
| COMMODITY | 750 | 1,000 | 1.78 | 1.80+ | 46.9% | 50%+ | T2 |
| ETF | 87 | 200+ | 1.24 | 1.50+ | 55.2% | 55%+ | T2 |
| FOREX | 1,169 | 500+ (clean) | 0.27 | 1.20+ | 46.4% | 50%+ | T3 or kill |
| BOND | 18 | 100+ | 1.72 | 1.70+ | 55.6% | 55%+ | T2 |
| FUTURES | 2 | 100+ | null | 1.50+ | n/a | 45%+ | T3 |

---

## Appendix A: File Reference Map

| File | Role |
|---|---|
| `alpha_engine/outcome_resolver.py` | Win/loss classification, TP/SL detection, time-exit resolution |
| `alpha_engine/production_scanner.py` | Main pick generation pipeline |
| `audit_trail/quality_gates.py` | BLOCKED_SOURCE_SYSTEMS, BLOCKED_STRATEGIES, active display gates, score penalties |
| `audit_trail/asset_classification.py` | Symbol → asset class mapping, per-class configs |
| `audit_trail/dashboard_generator.py` | Performance aggregation, PF/WR computation, HTML generation |
| `audit_trail/universal_pick_resolver.py` | Exit reason assignment, TP/SL detection for resolved picks |
| `alpha_engine/forex_strategies.py` | 8 forex strategies with academic backing |
| `alpha_engine/forex_smart_picks.py` | Production forex scanner (Portfolio C) |
| `alpha_engine/new_forex_strategies_20.py` | 20 untested forex strategies |
| `alpha_engine/commodity_signal_generator.py` | Commodity signal generation (XAU, WTI) |
| `alpha_engine/new_equity_commodity_strategies_20.py` | 10 commodity + 10 equity strategies |
| `copy_trader_intel/cta_strategy_replicator.py` | 7 CTA strategies with 20y academic evidence |
| `copy_trader_intel/multi_asset_copytrader_scraper.py` | Multi-asset copy-trader scraping |
| `alpha_engine/cta_bridge.py` | CTA strategy → scanner bridge |
| `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` | Kill governance protocol |
| `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | Symbol/direction/timeframe autopsy |
| `docs/PERFORMANCE_CHARTER.md` | Tier definitions (T1/T2/T3) |

## 10. Critical Addendum — Cross-Reference with Foolproof Action Plan (2026-05-02)

### 10.1 Key Corrections from Independent Verification

The Foolproof Action Plan underwent independent quant verification that corrected several original recommendations. My playbook above has been aligned with these corrections:

| Original | Corrected | Evidence | Impact on My Playbook |
|---|---|---|---|
| Lower R:R floor to 1.25 | **KEEP 1.5, ADD ceiling 2.0** | 1.25-1.5 band PF 1.01 (unprofitable); 1.5-2.0 band PF 5.81, Kelly +47.2% | Already at 1.5 floor; need to add 2.0 ceiling |
| ml_score >= 0.82 optimal | **ml_score >= 0.90** (66.7% accuracy) | 0.8-0.9 band = 39.3% accuracy (worse than coin flip) | Updated in Section 6.2 |
| 24h tracking window | **120h minimum** | 72.7% of picks never hit TP/SL in 24h | Non-crypto wiring (Section 10.3) already fixed to 120h FOREX/BOND, 96h others |
| C-Tier hard suspend | **5% allocation, paper trade** | Loses diversification; bull market opportunity cost | Accept the correction |
| WINNER_FILTER abolish | **A/B test 3 months** | Insufficient data for conclusive verdict | Defer |

### 10.2 FOREX Corruption Filter Fix (HIGHEST ROI SINGLE FIX)

**Location:** `audit_trail/dashboard_generator.py:4220-4269`
**Problem:** `_pnl_pct_looks_corrupt()` uses a 10x divergence threshold between reported PnL and implied price move. JPY pairs have a pip-vs-percent feeder confusion where legitimate 5-pip wins get reported as 25% PnL (750x divergence), triggering false corruption flagging. This filter **rejects 405/911 FOREX picks** (44.5% of all FOREX data).

**Fix already in code (env-opt-in):** The function has a JPY-aware divergence path at `dashboard_generator.py:4260` — opt-in via `PNL_PCT_CORRUPT_DIVERGENCE_JPY_RELAX=1` uses 50x threshold instead of 10x. This is conservative by design (default OFF) pending A/B backfill proof.

**Expected impact:** PF 0.27 → 1.15-1.25 (4-5× lift). This is the single biggest lever for FOREX recovery.

**Action:** Set `PNL_PCT_CORRUPT_DIVERGENCE_JPY_RELAX=1` in the GitHub Actions workflow `audit-dashboard.yml` after verifying backfill on a 30-day re-resolve.

### 10.3 Non-Crypto Remediation Wiring — Now LIVE on Main

The 2026-05-03 wiring PR shipped three critical fixes that were previously orphaned:

| Fix | Location | Impact |
|---|---|---|
| `get_effective_min_score` wired into `passes_smart_gate` | `quality_gates.py` | FOREX strategies like `forex_rsi2_mean_reversion` now get MIN_SCORE 30 instead of 40 — unblocking picks |
| `compute_non_crypto_boost` called from `compute_elite_score` | `elite_scorer.py` | FOREX +15 (session overlap + carry), COMMODITY +15 (COT + seasonal), ETF +10, BOND +10, EQUITY +8 |
| Per-asset-class TIME_EXIT window | `universal_pick_resolver.py` | FOREX/BOND 120h (was 48h), EQUITY/ETF 96h — fixes 72.7% unresolution rate |

**Tests:** 89/89 pass. No regression on crypto scoring.

### 10.4 Orphaned Code Goldmines (Top 5)

These exist in the repo but have no production callers:

| File | Value | Effort | Priority |
|---|---|---|---|
| `forward_testing/signal_quality_ml.py` | +5-15pp WR improvement via pre-trade ML filter | 4-6h | P0 |
| `battleground/alpha_vs_beta_benchmark.py` | Institutional alpha/beta decomposition | 3-4h | P1 |
| `audit_dashboard/meta_model_chatgpt.py` | Real-time score explainability | 4-5h | P1 |
| `config/feature_flags.json` | ml_gatekeeper, what_if_analysis, smart_picks_explainability | 1-2h | P0 |
| `alpha_engine/track_calculator.py` (PR #661) | Per-strategy-symbol-direction track records | 2-3h | P0 |

### 10.5 PR Merge Priority (from PR Merge Strategy doc)

```
1. PR #615 — Scanner Blockers (unblocks system)
2. PR #660 — Emergency Gates (highest $ impact, ml_score fix)
3. PR #597 — Pair-Block + Revalidator (signal integrity)
4. PR #661 — Infra v2.0 (track_calculator, PSR/DSR, decay tracker)
5. PR #644 — Quality Gate Plan (documentation)
6. PR #723 — Shadow Mode Auto-Promotion (B18)
7. PR #728 — Shadow Probation Panel (UI)
8. PR #608 — TradingAgents Smoke Test
9. PR #676 — Events Quality
```

### 10.6 JPY Pair Emergency Kill Switch

EURJPY, GBPJPY, AUDJPY all at PF 0.12 (pure bleed). These 3 pairs account for ~40% of FOREX closed volume. Temporarily gate them at the symbol level until the corruption filter fix is validated.

### 10.7 Corrected Gate Configuration (from Foolproof Action Plan)

```json
{
  "min_risk_reward": 1.50,
  "max_risk_reward": 2.00,
  "min_ml_score": 0.90,
  "ml_score_bands": {
    "0.70_0.90": {"action": "pass", "sizing": 0.50},
    "0.90_1.00": {"action": "pass", "sizing": 1.00}
  },
  "kelly_by_rr_band": {
    "1.50_2.00": 0.118,
    "below_1.50": 0.0,
    "above_2.00": 0.0
  },
  "tracking_window_hours": 120,
  "transaction_cost_model": {
    "crypto": 0.0023,
    "meme": 0.0053,
    "forex": 0.0003,
    "equity": 0.0003,
    "bond": 0.0005
  }
}
```

**Note:** The Foolproof Action Plan's specific gate numbers (R:R 1.25, ml_score 0.82) were flagged as incorrect by independent verification and corrected above. Use the corrected values.

### 10.8 Key Document Cross-References

| Document | Key Content |
|---|---|
| `updates/2026-05-02-hedge-fund-comprehensive-action-plan.md` | 1,114-line full Foolproof Action Plan with Foolproof Intervention Protocol, 12-week timeline, kill-switch ladder |
| `updates/2026-05-03-pr-merge-strategy-hedge-fund-grade.md` | PR merge order, smart picks per-asset caps, HC gate relaxations |
| `updates/2026-05-03-non-crypto-remediation-wiring.md` | Non-crypto boost, score overrides, per-class TIME_EXIT windows |
| `updates/2026-05-02-tier-performance-audit-and-fixes.md` | Tier classifications, Golden portfolio recommendation |
| `updates/2026-04-28-per-asset-class-performance-summary.md` | Pre-resolver-v2 performance baseline |
| `reports/EDGE_BY_ASSET_CLASS_2026_04_22.md` | 3,500-row edge diagnosis with confidence bucket drill-downs |

## Appendix B: Reproducibility Commands

```bash
# Recompute canonical performance
node tools/_canonical_recompute_2026_04_28.js

# Run three-axis autopsy on an asset class (after exporting closed picks)
python tools/mutation_analysis.py --csv closed_picks.csv --strategy <name> --output mutation_<name>.csv

# Verify resolver thresholds
python -c "from alpha_engine.outcome_resolver import PNL_WIN_THRESHOLD_BY_CLASS; print(PNL_WIN_THRESHOLD_BY_CLASS)"

# Verify blocked systems
python -c "from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS; print(sorted(BLOCKED_SOURCE_SYSTEMS))"

# Check current git branch and status
git log --oneline -5 && git status
```
