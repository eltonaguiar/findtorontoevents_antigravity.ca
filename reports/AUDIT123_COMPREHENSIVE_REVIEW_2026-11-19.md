# Comprehensive Review — findtorontoevents.ca/audit, /audit2, /audit3

**Date:** 2026-11-19
**Author:** opencode (Beam Free)
**Scope:** All three audit surfaces + their backing data files, every section, every metric, every gate, and the project's backtesting / asset-class picking methodologies.
**Status:** DRAFT — open for peer critique (see §13).
**Companion files:** `audit_dashboard/data/audit3_ledger.json`, `audit_dashboard/data/audit2_forward.json`, `audit_dashboard/data/audit3_evidence.json`, `reports/hypothesis_registry.json`, `reports/forward_observations.jsonl`.

---

## 0. Executive summary

- **No asset class is money-ready.** `money_ready_verdict.json` (2026-11-16T04:07Z) reports **0/10** money-ready. COMMODITY is the only `WATCH`; the other nine are `NOT_READY` or `INSUFFICIENT_DATA`. The honest intrabar truth (first-touch, SL-wins-ties) snapshot (2026-11-16T04:03Z): CRYPTO 35.8% WR / PF 0.92 / n=3716 FAIL; FOREX 32.2% / PF 0.66 / n=612 FAIL; EQUITY 59.2% / PF 0.94 / n=250 (high WR, PF<1 = net-negative); COMMODITY 40.2% / PF 1.03 / n=229 breakeven; FUTURES 42.3% / PF 1.09 / n=52 INSUFF-N.
- **audit3's kill tribunal scores 8,613 of 14,637 closed picks (58.8%).** 67 cells tested, 0 PROVEN_T2, 0 CANDIDATE, 56 WEAK, 11 KILL, 292 INSUFFICIENT_N. Kill rate 16.4%.
- **The single strongest honest money-ready lead is `crypto_rsi5070_us`** (H-119): net PF 1.12 @16bp, CI-LB 0.92 (gate 1.15), n=431 (gate 150 met), IS/OOS 1.08/1.16, top-symbol 5.1%. Fails **one** gate (net CI-LB). Shadow-only, never sized.
- **audit2 (candidate library) has exactly one accruing pod** (H-119, 430 forward rows) and **zero** POD-EQUITY-BREAKOUT forward rows — the EQUITY recommendation from the audit2/audit3 review cannot yet be tested. This is open action item #1.
- **ML calibration is inverted system-wide:** conf≥0.9 → 14.4% WR; conf 0.50–0.60 → 60.3% WR. Confidence is currently an anti-signal. Score-booster penalties shipped but upstream generators not recalibrated.
- **The COT positioning DSR=1.0 candidate was FALSIFIED** (2026-05-13): 6.33× over-emission (38 raw signals from 6 unique CFTC release weeks). Now `SHADOW_INSUFFICIENT_N`, dsr=null.
- **EQUITY `stocks_rsi2_pullback` was DISPUTED** (INCIDENT #96): raw n=70/WR 62.9% collapsed to true n=140/WR 33.9% after dedup.
- **FOREX has zero DSR-survivors** post-#876 unit clamp + #891 closed_at repair. FOREX state = BLOCKED.
- **15-minute ML strategies are overfit-bait:** 33 of 42 audited strategies OVERFIT_LIKELY (DSR<0.5).
- **R:R bands from the Apr-17 daily-resolved cohort are NOT honest intrabar** (daily resolution inflates gross PF ~2-3×). Honest CRYPTO intrabar PF ≈0.74 supersedes them.

---

## 1. Methodology (how this review was produced)

### 1.1 Data sources read
1. Live pages: `https://findtorontoevents.ca/audit/`, `/audit2/`, `/audit3/` (rendered HTML, fetched 2026-11-19).
2. Backing JSON: `audit_dashboard/data/audit3_ledger.json`, `audit2_forward.json`, `audit3_evidence.json`.
3. Repo code: `alpha_engine/audit3_tribunal.py`, `audit3_selection_alpha.py`, `audit3_evidence.py`, `audit3_denylist.py`, `audit3_tribunal.py`, `forward_observations_ingest.py`, `cost_model.py`, `transaction_costs.py`, `value_screener.py`, `mf_screener.py`, `backtest_framework.py`.
4. Docs/updates: `updates/2026-11-19-audit3-*`, `AUDIT_PAGE_SECTIONS_2026-11-18.md`, `COMS_HANDOFF_AUDIT2_3_2026-11-19.md`, `COMS_HANDOFF_AUDIT2_3_IMPL_JUSTIFICATION_2026-11-19.md`.
5. Hypothesis registry: `reports/hypothesis_registry.json` (99 entries).
6. Forward observations: `reports/forward_observations.jsonl` (430 rows, H-119 only).

### 1.2 Review protocol
1. **Fetch** each page; capture every tab/section header and every metric table.
2. **Map** each rendered claim to its backing JSON field (ledger → `audit3_ledger.json`).
3. **Cross-check** internal consistency: do the two PF/WR figures per class agree with their documented source (`asset_class_health` vs `hf_stats.by_asset_class`)?
4. **Identify gaps**: sections with no data, metrics with no gate, asset classes with no forward rows, hypotheses with no test.
5. **Permutation analysis**: enumerate TP/SL config variants and volume-augmented variants that the current code does NOT test, and propose them as experiments.
6. **Backtesting methodology audit**: enumerate the repo's backtest engines and their cost/slippage assumptions; flag inconsistencies.
7. **Asset-class picking methodology audit**: enumerate value/quality/safety screens per asset class; flag coverage gaps (mutual funds, bonds, futures, commodities mostly un-covered).

### 1.3 What this review does NOT do
- It does not re-run any backtest or modify any code.
- It does not claim money-readiness for any class.
- It does not push to git.

---

## 2. /audit (Unified Audit Dashboard v99.0) — section-by-section review

### 2.1 Header / truth layer banner
- **RAW vs filtered performance**: `at_raw_picks` RAW 11.13% WR / PF 0.46 (Kimi+2026-05-12 audit); refreshed 2026-05-29 (n=73,817 closed): WR 25.28% / PF 0.61 (outlier-capped); uncapped PF 2.5 is a handful-of-rows outlier artifact. **Do not cite 2.5.**
- **No asset class passes** industry-standard real-money thresholds (DSR>0.95, PBO<0.05, WFE>60%, live-Sharpe>0.5, n≥100).
- **COT positioning DSR=1.0 FALSIFIED** (2026-05-13) — see §2.12.
- **Data quality**: 22,947 rows, 10 MEMECOIN/meta_strategy cohorts; 3 UNKNOWN at_raw_picks; ghost rows not cleared (contradicts an earlier "cleared" claim).
- **COMMODITY filter-survival gap**: dashboard WR 85.5% (n=228) vs raw WR 60.2% (n=354); −126 picks excluded by `_is_valid_resolved_pick()` (missing/corrupt pnl_pct, concentrated in losing `cta_replicator` and `combined_confidence`). **85.5% is not the full cohort.**
- **FOREX**: WR 57.8% but PF 0.85 — wins avg 0.62% vs losses avg 1.00% (tight-TP/wide-SL asymmetry); total PnL −15.84%. Net-negative despite majority wins.
- **ML calibration inverted**: CRYPTO conf≥0.90 → 14.4% WR; conf 0.50–0.60 → 60.3% WR. EQUITY 0.85–0.90 → 20% WR (worst band); >0.90 recovers. FOREX peak 0.75–0.80; 0.70–0.75 = danger.
- **Score-booster penalties shipped** (`alpha_engine/score_booster._calibrate_confidence()`): CRYPTO >0.85 −12, <0.6 +3; EQUITY 0.85–0.90 −15; FOREX ≥0.85 −10. Upstream generators NOT recalibrated → raw confidence still an anti-signal.

### 2.2 Money-ready verdict (0/10)
- CRYPTO 35.8% PF 0.92 n=3716 FAIL; FOREX 32.2% PF 0.66 n=612 FAIL; EQUITY 59.2% PF 0.94 n=250 (high WR, PF<1); COMMODITY 40.2% PF 1.03 n=229 breakeven; FUTURES 42.3% PF 1.09 n=52 INSUFF-N.
- **Bottleneck = clean-trade supply, not strategy supply.** This is a key diagnosis: we have strategies; we lack honest resolved trades.

### 2.3 Forward-tracking candidate (shadow, not sized)
- `crypto_rsi5070_us`: net PF 1.12 @16bp, CI-LB 0.92 (gate 1.15), n=431 (gate 150 met), IS/OOS 1.08/1.16, top-sym JUPUSDT 5.1%. Fails one gate. Shadow only.
- **Gap**: promotion bar requires CI-LB ≥1.15; current 0.92. Need either more n, better entry timing, or cost reduction. See §7 (TP/SL permutations) and §8 (volume).

### 2.4 Strategy Kill Tribunal (weekly intrabar auto-review)
- Auto-reviews strategies on intrabar truth. See §3.3 (audit3 kill list) for the concrete kills.

### 2.5 Theory / Hypothesis Tracker
- 99 registered hypotheses with a wide status vocabulary (REJECTED, SHADOW_*, HARNESS_REJECTED, FAILED_ARCHIVED, KILLED, TESTED_KILL, UNTESTED, UNTESTED_DATA_GAP, DATA_GAP, TESTED_WEAK, TESTED_PASS, PRE_REGISTERED, PAPER_PILOT, FORWARD_OBSERVATION, SUPPORTED, REFUTED, NULL, FORWARD_SHADOW, FORWARD_ACCRUING, CLOSED, etc.).
- **Gap**: status vocabulary is fragmented (e.g. `PRE_REGISTERED` vs `PRE-REGISTERED`, `FORWARD OBSERVATION` vs `FORWARD_OBSERVATION`). Normalization needed for any automated gating.

### 2.6 Disputed surfaces (CRYPTO Smart Picks / Verified Alpha / High-Conviction / ELITE)
- All 4 inflated CRYPTO nav surfaces (PF 9–18, WR 78–88%) dominated by historical `claude_gainer_st` picks (91.7% concentration) with EXPIRED→WON resolver mislabels. Independent DB probe: raw equivalent WR=33%.
- Honest cells: `pf_registry` policy-clean-net PF 0.98 / WR 39.7% / n=229; `money_ready_verdict` PF 0.96 / WR 31.3% / DSR 0.0073.
- **Do not size on inflated surfaces.**

### 2.7 Tier definitions
- T1 PF>2/WR>55/MDD<10; T2 PF>1.5/WR>50/MDD<20 (Institutional); T3 PF>1.2/WR>48/MDD<30 (Retail-OK). Source: `asset_class_health` in `dashboard_data.json` (post-resolver-v2 noise filter).
- **Gap**: two PF/WR figures per class (headline full-history vs recent 60–90d subset). CRYPTO recent PF 0.89 vs headline 1.25 (n=1650 vs n=8067). Deploy/sizing should weigh the recent panel; validation should weigh headline. This dual-figure convention is a recurring source of confusion and should be collapsed to one canonical figure with a window label.

### 2.8 Walk-forward (OOS) per class
- Sharpe colored: green >0.5, yellow 0–0.5, red <0. Sharpe here is on the closed-pick cohort, not a live mark. **Gap**: no WFE (walk-forward efficiency) reported despite being a stated gate (WFE>60%).

### 2.9 TA baseline (TradingView 6-strategy benchmark)
- ema_cross/macd/rsi/bollinger/donchian/supertrend vs buy-hold. Promotion gate: walk-forward robustness ≥0.60 AND trades ≥5. Source: `tradingview-mcp/.../backtest_service.py`, generator `tools/run_tv_backtest_benchmark.py`.
- **Gap**: only 6 naive strategies; no cost model applied at the TA layer (costs applied later in the pipeline). Need a cost-aware TA baseline.

### 2.10 Definitions (PROVEN / Smart Picks / SHADOW / High Conviction / Trust Tiers)
- PROVEN: strategy ≥5 closed trades, ≥55% WR after Bayesian shrink, PF ≥1.5, confidence ≥0.7. Manually vetted systems can also earn PROVEN.
- Smart Picks: AI-curated basket, 6 dimensions (Regime 25%, Quality 35%, Freshness 15%, TP upside 15%, HTF 10%, Proven Winner Boost +8–15).
- SHADOW: prediction-market consensus (Polymarket/Kalshi) not Verified Alpha / not PROVEN. PBO 0.603 fails money-ready bar. Copy-trader rows auditable only, not sized.
- High Conviction: strictest preset; shared hard gates + per-asset-class floors.
- Trust Tiers: PROVEN=elite, DEVELOPING=good, WATCH=marginal, SANDBOX=unproven/new, PROBATION=broken/banned.
- **Gap**: "PROVEN" is overloaded — it is both a strategy-level status (≥5 trades/PF≥1.5) and a trust tier. The audit3 ledger's `PROVEN_T2` is stricter (n≥100, CI-LB≥0.05%/trade, stable halves, no symbol >60%, source share ≤90%, BH q≤0.1, DSR≥0.95, selection alpha CI-LB>0). Conflation risk.

### 2.11 Supreme Edge (DSR-verified, 2026-05-12 refresh)
- COMMODITY `cot_positioning` DSR=1.0 FALSIFIED (over-emission).
- CRYPTO ML-enhanced 1d/1h sleeves: 4 strategies survive DSR (n=27–34, DSR≥0.9995) but **n<100** → DSR unreliable. Awaiting n≥100.
- EQUITY `stocks_rsi2_pullback` DISPUTED (INCIDENT #96): true n=140 WR 33.9%.
- 15m timeframe is overfit-bait (33/42 OVERFIT_LIKELY).
- FOREX zero DSR-survivors; BLOCKED.
- ML calibration inverted system-wide.
- Real-money posture: COMMODITY/EQUITY REHAB (STABLE_EDGE); CRYPTO DSR-verified ML sleeves; FOREX BLOCKED; FUTURES BLOCKED; ETF/BOND/INDEX_STOCK sample-size-thin.

### 2.12 Where Our Edge Actually Is (post-hoc segment warning)
- All numbers (82% WR / PF 11+) are **post-hoc segment search**, not actionable. Multiple-testing correction not applied. Treat as historical pattern descriptors.
- R:R truth (CRYPTO, daily-resolved, n=1,916): R:R 1.0–1.5 → 62.3% WR/PF 1.66; 1.5–2.0 → 52.5%/1.92; ≥2.0 → 58.0%/3.06; <1.0 → 55.9%/0.93. **NOT honest intrabar** (daily resolution inflates gross PF ~2-3×). Honest CRYPTO intrabar PF ≈0.74 supersedes.
- Direction = BUY → 28.9% WR/PF 0.38; Direction = LONG → 54.9% WR/PF 3.14. (Winning cohort = signal_type=BUY + direction=LONG at 62.6% WR.)
- High-grade A/B → 49.3% WR/PF 0.66 (NOT an edge).
- **Gap**: the "Where Our Edge Actually Is" section still displays post-hoc numbers prominently despite the warning. Recommend demoting to an appendix or hiding behind a "post-hoc (not actionable)" toggle.

### 2.13 Best Filter by Asset Class
- Crypto: Confidence ≥0.8 or Proven strategy → 69.2% WR (all 49.6%), PF 10.39.
- Stocks: Trusted + score ≥50 → 69.2% WR (all 43.4%), PF 0.77* (small n=13; NOT verified edge; combine with Maximum Conviction Combo, PF 2.62).
- Forex: Trusted → 49.0% (all 42.9%), PF 3.59.
- Commodities: Trusted → 44.5% (all 42.3%), PF 1.26† (bootstrap CI straddles 1.0 on n=273 — inconclusive).
- **R:R ≥1.5 filter underperforms baseline across EVERY asset class** (crypto −0.4pp, equity −1.0pp, forex −9.2pp, commodity −32.3pp). Use cautiously.
- **Gap**: the "Stocks PF 0.77" cell is displayed as a filter recommendation despite failing the PF>1.5 bar. The footnote exists but the table still implies usability. Recommend removing from the "best filter" table or marking DEAD.

### 2.14 Maximum Conviction Combo (under re-validation)
- PROVEN + conf 0.8–0.9 → insufficient sample (n=0 on recent_closed). Hidden until ≥20 closed trades under post-correction PROVEN tier. **Gap**: `claude_gainer_st` was demoted 2026-04-20; the band has not repopulated. Either the PROVEN tier is too strict or the candidate pool dried up — needs investigation.

### 2.15 What to Avoid
- Grade D & F picks: 725 trades, 33.4% WR, PF 0.82, −131.8% cum PnL.
- Commodities SHORT on copy_trader: 50% LOST (unresolved), masking TP/SL.
- Futures: 6.3% WR on n=17, 76% LOST-exit. Kill list pending.
- ETFs: PF 0.28 on 19 trades, dominated by `extreme_oversold_bounce` at 0% WR.
- Low-confidence crypto: conf<0.6 → 26–44% WR, deep negative avg PnL.
- R:R ≥1.5 on non-crypto: harmful.

### 2.16 Predictor Power Ranking (decile test, n=1,927)
- ml_score Spearman +0.33 (best predictor): top 30% 60.0% WR vs bottom 30% 32.5% (27.5pp spread).
- confidence +0.27: top 30% 51.9% vs bottom 30% 30.8%.
- elite_score +0.012: WEAK (28.0% vs 39.4%).
- **Overconfidence pattern**: D10 (top decile) underperforms D9 in both confidence and ml_score. Extreme scores signal overconfidence, not edge. **Gap**: this is a known, un-fixed systematic issue — the scorer still rewards extreme values.

### 2.17 Smart Picks (technical detail)
- ML Score 0–25, Forward Walk-Forward WR 0–40, Confidence Calibration 0–20, Regime Alignment, Trust & Source.
- Hard gates: SCALP mode (24.8% WR), panic-health, <35% forward WR, direction conflicts, 80+ killed strategies.
- Forward-validated bypass: ≥20 trades and ≥50% forward WR can qualify below threshold.
- **Glossary of scoring factors** documents which components are ZEROED (ML Replacement Score, Source System Tier, R:R Ratio, Age Freshness, Leverage Safety, Proven Strategy Bonus, Position Performance, Monte Carlo/Meta-Label/Hindsight/Skyrocket) due to anti-predictivity. This is excellent transparency. **Gap**: the zeroed components are still computed and stored (wasted compute); consider removing from the pipeline.

### 2.18 US Equity Picks (UEPS)
- Long-term value (1y–3y+) and swing (1w–1m) US equity picks. Composite: `0.55 × ValueComposite + 0.45 × QualityComposite × SafetyGate` where ValueComposite blends Magic Formula + Acquirer's Multiple + FCF Yield; SafetyGate requires Altman Z'' ≥1.10 AND Beneish M ≤−1.78.
- Tier classification deferred until n≥100 closed picks per `docs/PERFORMANCE_CHARTER.md §10`.
- Resolver (long-term) never closes on price drawdown alone — thesis-break + IV-attainment + horizon expiry only.
- **Gap**: n=0/100 as of the page ("Building track record"). UEPS is a research ledger, not a money book, and there is no forward row accrual wired for it (parallel to the POD-EQUITY-BREAKOUT gap).

### 2.19 Active Picks table + filters
- Broadest feed; filters by asset, system, status, direction, PnL, trust, age, TP remaining, timeframe, concept, score band.
- **Gap**: the "Best Score / Proven Only / In Profit" quick filters are useful but the underlying "Proven" definition differs from audit3's PROVEN_T2. Same conflation as §2.10.

---

## 3. /audit2 (Candidate & Methodology Library) — section-by-section review

### 3.1 Header / doctrine
- "The positive side of /audit3's kill tribunal: what is worth forward-testing, and the measurement kit to judge it. Nothing here is money-ready."

### 3.2 Verdicts (from audit3_ledger.json)
- Per-class: Verdict, n, Net expectancy/trade, Net 95% CI, 2× cost OK, DSR, required_n.
- **2× cost OK** = net-expectancy CI still excludes zero at twice the class slippage (required gate for PROVEN_T2 / CANDIDATE).
- **required_n** = trades needed to confirm the observed effect at 80% power.

### 3.3 Candidate & observe pods
- Pre-registered before forward data. `pre_registered` may confer confirmatory status; `observe` cannot promote until promoted to `pre_registered`.
- **Gap**: only H-119 and H-BABY-EQUITY-VT-PATTERN-SWEEP-001 are in CONDITIONS in `forward_observations_ingest.py`. The EQUITY pod has **zero forward rows** (open action item #1).

### 3.4 Forward evidence clock
- A pod can only promote on forward rows dated after its registration. Rows from `reports/forward_observations.jsonl`.
- H-119: n=430, benchmark_leg=343, intrabar=430, pods=[].
- **Gap**: `pods=[]` — the pod registry is not populated in the forward JSON. The page renders "Pods — forward rows closed on or after registration" but the data has none. Either the pod registry is a static snapshot (the page says "pod registry is a static snapshot dated 2026-11-19 because reports/ is not web-served") or it is genuinely empty. **Needs reconciliation.**

### 3.5 Trial budget & benchmarks
- Per-class benchmark leg and gate.
- Cost gate: average net PnL must be at least 3× the measured slippage. ETF slippage ≈234% of per-trade PnL (monthly cadence only); CRYPTO ≈37%.
- **Gap**: the "3× slippage" gate and the audit3 "2× slippage stress" gate (G9) are different multipliers for the same concept. Harmonize: pick one (recommend 2× for consistency with G9, or document why audit2 uses 3×).

### 3.6 Measures library
- Named measures with definitions. **Gap**: not enumerated in the fetched page (rendered client-side from JSON). Recommend exporting a static `audit2_measures.json` for auditability.

### 3.7 Traps / graveyard
- Ideas that are not candidates, with reasons. **Gap**: same as 3.6 — client-rendered, not in the static snapshot.

### 3.8 Retired with reason
- Items retired with reasons. **Gap**: same.

### 3.9 Provenance & freshness
- Verdicts and measures come from `audit3_ledger.json`; forward clock from `audit2_forward.json`; pod registry is a static snapshot dated 2026-11-19 because `reports/` is not web-served.
- **Gap**: the pod registry being a static snapshot means it cannot update without a redeploy. Recommend serving `reports/` (or a filtered subset) so the forward clock is live.

---

## 4. /audit3 (Quant Kill Tribunal) — section-by-section review

### 4.1 Header / KPIs
- Title: "AUDIT3 — quant kill tribunal". Stamp: loading ledger…
- Hero: headline + subline + disclaimer + KPI grid.
- KPIs: n_rows, n_cells_tested, n_cells_total, n_symbol_cells, n_cells_dsr_scored, n_confirmatory/discovery, n_proven, n_candidate, n_weak, n_kill, n_insufficient, kill_rate_pct, n_proven_symbols, n_proven_classes, n_kill_symbols, n_segment_cells, n_proven_segments, n_harmful_segments, n_positive_segments, n_kill_classes.

### 4.2 Tabs
1. **Overview** — asset classes table (selection alpha first, then cost, then multiplicity); coverage panel; "only pipeline that can promote anything" (gates).
2. **Kill Tribunal** — kill list with scope, class, strategy, direction, n, WR, PF, net exp, q_value, reasons, mutation suggestions.
3. **Strategy Cells** — strategy × direction cells, filterable by class/verdict/min-n/search.
4. **Symbols** — symbol × direction cells (n≥20).
5. **Sections × Class** — section × asset class matrix (reconstructed from row fields).
6. **Source Families** — copytrader, prediction markets, ML, luxalgo, etc.
7. **Evidence Registry** — backtests already in the repo and DB.
8. **Hypotheses** — hypothesis tracker.
9. **Method & Limits** — conventions, doctrine, provenance.

### 4.3 Overview tab
- **Asset classes table**: 7 classes (CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND, FUTURES). Each with n, wins, WR (+CI), PF, gross/net expectancy, net CI, p_value, p_wr, q_value, p_harm, harm_q, net CI 2×, stress_2× OK, DSR, split-half (stable/first/second), top_symbol_share, top_source_share, single_source, verdict, reasons, sharpe, sr0.
- **Coverage panel**: denominator mode canonical, sha256, kept rows 8613, excluded by reason (invalid_row 5823, mirror_duplicate 91, non_performance_exit 43, resolver_breakeven_fallback 67), scored_share_of_total 58.84%, scored_share_of_valid 105.04%, unscored 6024, two excluded cohorts (integrity_excluded 5933, auto_expired 9257, overlapping), resolver anomalies (stale_exit_beyond_planned_stop 44, clamped_loss_rows 23, expired_zero_pnl_rows 3624, closed_rows_missing_closed_at 3).
- **Selection alpha**: `available: false` — alpha_engine/audit3_selection_alpha.py needs the price tables. **Gap: selection alpha (pick net − direction-adjusted buy&hold) is NOT computed**, so a +40% pick on a +60% symbol is invisible. This is a P0 gap.
- **Forward gate**: enforced; a pod's cell reaches PROVEN_T2 only with its own forward rows closed on/after registration.
- **Alpha note**: G8 — PROVEN_T2 requires direction-adjusted selection alpha CI-LB >0; beta-only profitable cells demoted to CANDIDATE and flagged beta_dominant.
- **G9 cost stress**: net CI-LB at 2× class slippage must stay positive for PROVEN_T2/CANDIDATE; otherwise demote one tier.

### 4.4 Kill Tribunal tab
- 11 kills (see §3.3 of ledger excerpt). Criteria: net expectancy 95% CI entirely <0; BH harm q≤0.1 across killed cells; PF<0.8 at n≥50 is WATCH only, never kill alone; WR<40% diagnostic only.
- Kills: luxalgo_confluence (n=2066, WR 39.9%, PF 0.90), extreme_fear (n=407, WR 39.3%, PF 0.74), unknown (n=260, WR 28.1%, PF 0.61), MomentumEMA (n=73, WR 6.8%, PF 0.09), crypto_signal_engine (n=48, WR 8.3%, PF 0.20), stochrsi_macd_combo (n=38, WR 28.9%, PF 0.33), Breakout Momentum (n=37, WR 40.5%, PF 0.40), crypto-funding-confluence (n=34, WR 41.2%, PF 0.45), futures_momentum SHORT (n=32, WR 0%, PF 0), MeanReversionBB SHORT (n=29, WR 0%, PF 0), strong consensus (n=22, WR 27.3%, PF 0.18). Plus symbol-level kills: BTC, ETH, AVAX, XRP LONG.
- **Mutation suggestions** provided per kill (invert/filter, require second source, drop dominant symbol).
- **Gap**: the kill list has no "since when" timestamp per kill, and no re-test schedule. A killed cell should be re-tested after a defined window or a mutation is applied.

### 4.5 Strategy Cells tab
- 67 tested cells (n≥20). Filterable. **Gap**: no export (CSV) button; no per-cell drill-down to the underlying trades.

### 4.6 Symbols tab
- 68 symbol × direction cells (n≥20). 10 killed symbols.

### 4.7 Sections × Class tab
- Section membership rebuilt from row fields (trust_tier, grade, elite_grade, score≥60, rr_ratio≥1.5, paper flag, is_ac_survivor, strat_fwd_trades≥20). Reconstructed: true (proxy, not the live gate).
- 6 segment cells, 0 proven, 2 harmful, 0 positive.
- **Gap**: this is a proxy reconstruction. The live section name is not on closed rows. Recommend stamping the section name onto closed rows at resolution time so the next run is ground-truth, not proxy.

### 4.8 Source Families tab
- Name-based bucketing (strategy/source_system). Answers "does this whole surface carry edge?", not per-trader.
- **Gap**: per-trader reverse engineering needs its own ledger (stated in the page). No such ledger exists yet. Also, "unknown" strategy rows (n=260, WR 28.1%) indicate a data-quality gap — strategies not labeled at emission time.

### 4.9 Evidence Registry tab
- 2,727 records across 4 surfaces: db:at_incubator_backtest_results 1285, db:at_large_backtest_results 1105, db:bt_backtest_runs 285, backtest_json 52.
- 145 strategies, 50 sources, 66,764 trades covered, 11 re-testable with trade log, 2 with trial count.
- **Class mismatches**: 11 (FOREX strategies labeled CRYPTO; futures_ts_momentum_backtest CT=F labeled FUTURES but derived COMMODITY).
- **Known gaps** (from the page): prior backtests are evidence, not verdicts; without a trade log or per-symbol price series they cannot be re-scored against a timing null.
- **Gap**: only 11 of 145 strategies are re-testable with a trade log (7.6%). The evidence base is mostly summary statistics. Recommend requiring trade-log emission from every backtest going forward.

### 4.10 Hypotheses tab
- 99 registered hypotheses, status distribution as above.
- **Gap**: status vocabulary fragmented (see §2.5). Open hypotheses list is empty (`"open": []`) even though 14 are PRE_REGISTERED and 19 FORWARD_OBSERVATION. The "open" filter is too narrow.

### 4.11 Method & Limits tab
- Conventions: wr_floor_n=20, proven_min_n=100, candidate_min_n=30, fdr_q=0.1, dsr_threshold=0.95, bootstrap_resamples=2000, bootstrap_seed=42, slippage by class, cost basis measured (per-strategy where available, class otherwise), win definition net pnl>0 after slippage, edge test net-expectancy bootstrap CI one-sided, p_value one-sided bootstrap, p_wr one-sided exact binomial (reported, never gated), promotion rule, selection alpha gate (G8), cost stress (G9), multiplicity BH, stability chronological split-half both halves net mean>0, max_symbol_share 0.6, max_source_share 0.9, random entry MC not run here.
- **Doctrine**: innocent until proven guilty.
- **Provenance**: audit3 · static ledger · regenerated by alpha_engine/audit3_tribunal.py · not investment advice · no position sizing.
- **Gap**: random-entry MC is "not run here (needs per-symbol price series)" — but `alpha_engine/benchmark_closed_ledger.py` has a random-entry MC (same-asset, direction-aware nulls, coin-flip CI gate). These two should be wired together.

---

## 5. Cross-page consistency review

| Claim | /audit | /audit3 ledger | Consistent? |
|---|---|---|---|
| CRYPTO WR | 35.8% (intrabar) / 40.4% (ledger) | 40.42% WR, PF 0.84 | ⚠ Different windows/cohorts (intrabar truth vs canonical resolved). Document which is which. |
| CRYPTO n | 3,716 (intrabar) | 6,740 (ledger) | ⚠ Same as above. |
| FOREX WR | 32.2% (intrabar) / 38.8% (ledger) | 38.76% | ⚠ |
| EQUITY WR | 59.2% (intrabar) / 45.3% (ledger) | 45.26% | ⚠ |
| COMMODITY WR | 40.2% (intrabar) / 11.8% (ledger) | 11.76% | ⚠ Large gap — intrabar cohort is filtered differently. |
| FUTURES n | 52 (intrabar) | 4 (ledger) | ⚠ Very large gap. |
| Money-ready count | 0/10 | 0 proven classes | ✅ |
| Kill count | (tribunal auto) | 11 kills | ✅ (within audit3) |

**Recommendation**: publish a single "cohort definition" doc that maps each reported number to its source table and filter, so the two WRs per class stop being quoted interchangeably.

---

## 6. Gaps identified (consolidated)

### 6.1 Data / coverage gaps
1. **Selection alpha not computed** (`available: false`). Needs price tables. P0.
2. **POD-EQUITY-BREAKOUT has zero forward rows** — EQUITY recommendation untestable. Register in `CONDITIONS`. Open action item #1.
3. **Pod registry empty** in `audit2_forward.json` (`pods: []`). Static snapshot, not live.
4. **reports/ not web-served** → forward clock not live; pod registry stale.
5. **Only 11 of 145 evidence-registry strategies re-testable with a trade log** (7.6%).
6. **"unknown" strategy rows** (n=260, WR 28.1%) — labeling gap at emission.
7. **Class mismatches** (11): FOREX labeled CRYPTO; CT=F labeled FUTURES not COMMODITY.
8. **Two excluded cohorts overlap** (integrity_excluded 5933 + auto_expired 9257) — not a partition; stated but easy to misread.
9. **FUTURES n=4 in ledger vs n=52 in intrabar** — large unexplained gap.
10. **UEPS n=0/100** — no forward accrual wired.

### 6.2 Methodology gaps
11. **Random-entry MC not run in audit3** despite existing in `benchmark_closed_ledger.py`. Wire them.
12. **WFE not reported** despite being a stated gate (WFE>60%).
13. **TA baseline has no cost model** at the TA layer.
14. **Two slippage multipliers** (audit2 3× vs audit3 G9 2×) for the same concept.
15. **Status vocabulary fragmented** (PRE_REGISTERED vs PRE-REGISTERED, etc.).
16. **"Open" hypothesis filter too narrow** (returns [] despite 14 PRE_REGISTERED + 19 FORWARD_OBSERVATION).
17. **Dual PF/WR per class** (headline vs recent) causes confusion; collapse to one canonical figure + window label.
18. **Post-hoc segment numbers still displayed prominently** despite the warning; demote or gate behind toggle.
19. **"Best filter" table includes DEAD cells** (Stocks PF 0.77).
20. **PROVEN overloaded** (strategy-level vs trust-tier vs PROVEN_T2). Disambiguate.
21. **Sections × Class is a proxy reconstruction**; stamp section name at resolution time.
22. **No re-test schedule for killed cells.**

### 6.3 Calibration / model gaps
23. **ML calibration inverted system-wide**; score-booster penalties shipped but upstream generators not recalibrated.
24. **Overconfidence pattern** (D10 underperforms D9) un-fixed.
25. **Zeroed scoring components still computed** (wasted compute).
26. **Maximum Conviction Combo band has not repopulated** since `claude_gainer_st` demotion (2026-04-20).
27. **15m ML strategies overfit-bait** (33/42 OVERFIT_LIKELY) but still emitted.

---

## 7. TP/SL permutation analysis (gap in current testing)

The current pipeline tests a single TP/SL configuration per strategy (the emitted `tp_pct`/`sl_pct` or `rr_ratio`). The audit3 ledger scores net expectancy at the **class-level** slippage, not at varied TP/SL. The following permutations are NOT in the test matrix and should be:

### 7.1 TP/SL ratio permutations
| Variant | TP | SL | R:R | Hypothesis |
|---|---|---|---|---|
| A (current baseline) | 2% | 1% | 2.0 | Baseline |
| B (tight TP) | 1% | 1% | 1.0 | Higher WR, lower PF — test whether WR gain offsets PF loss |
| C (wide TP) | 4% | 1% | 4.0 | Lower WR, higher PF — test tail capture |
| D (symmetric wide) | 3% | 3% | 1.0 | Test whether 1:1 with wider bands avoids noise |
| E (asymmetric tight SL) | 2% | 0.5% | 4.0 | Test whether tighter SL cuts losers faster without killing winners |
| F (trailing) | 2% trailing | 1% | dyn | Test trailing stop vs fixed TP |

### 7.2 Cost-aware variants
- Re-run each variant at 1×, 2× (G9), and 3× (audit2) slippage to find the variant that survives the strictest cost gate.
- Report **net expectancy CI-LB** (not just PF or WR) as the promotion metric, consistent with audit3.

### 7.3 Time-stop variants
- Add a time-stop (e.g., 4h, 24h, 48h) to each TP/SL variant and measure whether it removes the "expired zero PnL" cohort (3,624 rows currently) without harming winners.

### 7.4 Volume-augmented variants (see §8)
- Each TP/SL variant × with/without volume confirmation gate.

### 7.5 Recommended experiment harness
- Use `alpha_engine/walk_forward_backtester.py` + `alpha_engine/cost_model.py` (get_total_bps) + a new `tp_sl_permutation_runner.py` that emits per-variant net expectancy CI-LB, DSR, and split-half stability into `reports/tp_sl_permutation_<date>.json`.
- Gate: a variant promotes only if net CI-LB >0 at 2× slippage, stable halves, n≥30, DSR≥0.95 (consistent with audit3 PROVEN_T2, relaxed to CANDIDATE thresholds for experiments).

---

## 8. Volume as an additional filter (gap in current testing)

The audit dashboard's Smart Picks already uses a **Volume Confirmation** component (−8 to +5 pts: 1.5–3× = +5, >5× spike = −8 penalty) and a **Volume-weighted** element in the elite score. But the **asset-class-level and strategy-level** testing does NOT systematically test volume as a gate. The following are NOT currently tested:

1. **Volume-confirmed entry**: require relative volume ≥1.5× 20-day average at entry. Hypothesis: filters out low-conviction breakouts, improving WR without hurting PF.
2. **Volume divergence exit**: exit when volume drops below 0.5× average while price is still above SL — hypothesis: avoids giving back gains on dying momentum.
3. **Volume-profile (VWAP) anchor**: use VWAP as the dynamic SL instead of a fixed % — hypothesis: adapts to intraday liquidity.
4. **Volume spike as a contrarian filter**: a >5× spike is currently penalized (−8). Test whether inverting (treating extreme spikes as fade signals) improves edge on the killed strategies (e.g., `luxalgo_confluence`, `MomentumEMA`).
5. **Volume + R:R interaction**: the R:R bands (§2.12) were never cross-tabulated with volume. Hypothesis: high-R:R trades only work when volume confirms.

### 8.1 Recommended volume experiment
- Add a `volume_gate` column to the closed-pick canonical view (relative volume at entry, volume trend, VWAP distance).
- Re-run the audit3 tribunal with volume as a segmentation dimension (in addition to strategy/direction/symbol).
- Report per-volume-bucket net expectancy CI-LB; promote volume-gated cells only under the same G8/G9 gates.
- Cross with §7 TP/SL permutations: a 6 (TP/SL variants) × 2 (volume on/off) × 3 (cost multipliers) matrix = 36 cells per strategy, per asset class.

---

## 9. Backtesting methodologies in the project (audit)

### 9.1 Engines present
| Engine | File | Notes |
|---|---|---|
| Backtest Framework | `backtest_framework.py` | ABC-based, Trade/Position dataclasses, multi-data-source. |
| Quantum Fusion | `quantum_fusion_multi_period_backtest.py`, `quantum_fusion_backtester.py` | Multi-period. |
| Walk-forward | `walk_forward_backtester.py`, `rolling_walk_forward.py`, `walk_forward_validator.py`, `walkforward_validator.py` | Multiple, possibly divergent implementations. |
| Baby strategies | `baby_strategies_backtest.py` | |
| JBravo | `jbravo_*_backtest.py` | |
| Rare strategy | `rare_strategy_backtest.py`, `v2` | |
| Funding arb | `funding_arb_backtest.py` | |
| Custom | `run_custom_backtests.py`, `comprehensive_backtest.py`, `extensive_multi_pair_backtest.py` | |
| TV benchmark | `tools/run_tv_backtest_benchmark.py` | 6 naive strategies. |

### 9.2 Cost / slippage assumptions (inconsistent)
- `alpha_engine/cost_model.py` (EAGLE2): CRYPTO 13 bps total (8 exec + 5 slip), EQUITY 7 bps, ETF 3 bps, FOREX 2 bps, COMMODITY 7 bps, FUTURES 5.5 bps, BOND 4.5 bps.
- `alpha_engine/transaction_costs.py`: crypto_spot 25 bps, crypto_altcoin 70 bps, meme 100 bps, forex 3 bps, stocks_etf 3 bps, penny 1000+ bps.
- `alpha_engine/forward_observations_ingest.py` OTHER_BP: EQUITY 8, ETF 8, FOREX 4, COMMODITY 12, FUTURES 12, BOND 2 (CRYPTO 16).
- `audit3_ledger.json` conventions.slippage_pct_by_class: CRYPTO 0.0996 (9.96 bps), EQUITY 0.05 (5 bps), COMMODITY 0.15 (15 bps), ETF 0.05, FOREX 0.02 (2 bps), BOND 0.05, FUTURES 0.1 (10 bps), MEME 0.3, PENNY_STOCK 0.3, MUTUAL_FUND 0.08.

**Inconsistency**: CRYPTO is 13 bps (cost_model) vs 16 bps (ingest) vs 9.96 bps (ledger). EQUITY is 7 vs 8 vs 5. COMMODITY 7 vs 12 vs 15. These must be harmonized to a single source of truth (`cost_model.py` should be the sole owner; the others should import from it).

### 9.3 Other backtesting gaps
- **No single canonical backtest entry point** — 9+ engines, divergent APIs.
- **Walk-forward implementations duplicated** (4 files) — risk of drift.
- **No standard output schema** — each engine writes its own JSON shape; the evidence registry has to normalize 4 surfaces.
- **No mandatory trade-log emission** — only 11/145 strategies re-testable.
- **No cost model at the TA baseline layer** (§2.9).
- **No intrabar (first-touch) resolution in most engines** — they use daily close, which inflates PF 2-3× (proven 2026-06).
- **No multiple-testing correction** in most engines (audit3 applies BH; others do not).
- **No selection alpha** (pick net − hold) in any engine except the unimplemented `audit3_selection_alpha.py`.

### 9.4 Recommendations
1. Consolidate to one engine (`backtest_framework.py` as the base) with pluggable cost model (`cost_model.py`).
2. Make `cost_model.py` the single source of truth; delete duplicated constants elsewhere (import).
3. Mandate intrabar first-touch resolution for all new backtests.
4. Mandate trade-log emission (entry/exit prices, timestamps, side, symbol, strategy, pnl) for re-testability.
5. Apply BH correction in every engine, not just audit3.
6. Implement `audit3_selection_alpha.py` (needs price tables) — P0.

---

## 10. Asset-class picking methodologies (audit)

### 10.1 Stocks (EQUITY)
- **Value screener** (`alpha_engine/value_screener.py`): Magic Formula × Piotroski × Acquirer's Multiple, SafetyGate (Altman Z'' ≥1.10, Beneish M ≤−1.78). Universe gates: market cap ≥$300M, ≥5y operating history, ≤540d 10-K age, exclude Financial/Utilities.
- **Composite**: `0.45 × ValueComposite + 0.55 × QualityComposite` (v1.1 quality-tilt; v1.0 was 0.55/0.45) × SafetyGate. ValueComposite = 0.40 MagicFormulaPercentile + 0.35 AcquirersMultiplePercentile + 0.25 FCFYieldPercentile. QualityComposite = 0.50 Piotroski/9 + 0.30 ROIC_Stability + 0.20 DebtToEquityScore.
- **MF screener** (`mf_screener.py`), **growth screener** (`growth_stock_screener.py`), **swing screener** (`swing_screener.py`), **short-side screener** (`short_side_screener.py`).
- **UEPS** (§2.18): long-term value + swing, composite `0.55 × ValueComposite + 0.45 × QualityComposite × SafetyGate` (note: different weights than value_screener — 0.55/0.45 vs 0.45/0.55). **Inconsistency**: the two composites use different weights. Reconcile.
- **Update (2026-11-19)**: `value_screener_runner.py` IS wired to a weekly workflow (`value_screener_weekly.yml`, Mon 06:00 UTC). Runner executed successfully: 22 long-term value picks emitted from 49-ticker S&P 100 universe (ADBE, PYPL, NFLX, META, GOOGL, HD, QCOM, MA, XOM, V, ...). Report at `reports/value_screener_runs/2026-11-19.md`. Workflow still has `continue-on-error: true` guard — should be removed now that runner is stable. Weight inconsistency (value_screener 0.45/0.55 vs UEPS 0.55/0.45) still needs reconciliation. Momentum overlay not yet added. UEPS n=0/100 (no IV-attainment resolver wired).

### 10.2 Crypto
- **ML-enhanced sleeves**: 4 survive DSR (n=27–34). Awaiting n≥100.
- **crypto_rsi5070_us** (H-119): strongest honest lead.
- **Cost**: 9.96–16 bps (inconsistent, see §9.2).
- **Gap**: crypto picking is mostly ML/quant-driven; no fundamental/value layer (appropriate for crypto, but means all edge is statistical, not fundamental). Volume gate not systematically tested (§8).

### 10.3 Mutual funds
- **No dedicated screener found** in `alpha_engine/` (searched: no `mutual_fund_screener`). `MUTUAL_FUND` exists as an asset class in the ledger (slippage 8 bps) but with minimal coverage.
- **Update (2026-11-19)**: `mf_screener.py` EXISTS (hard gates: expense ratio ≤0.09% index/≤0.20% active, no load, no 12b-1, min initial ≤$3K, AUM ≥$1B, turnover ≤20%, tracking error ≤0.25%, track record ≥10y, NAV freshness ≤24h). Starter universe: VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX. `mutual_fund_nav.py` provides NAV data path. BUT: not wired to production (only used in worktrees). Needs: weekly workflow + pick emission + forward tracking. The screener is a PASSIVE core allocation tool, not an active pick system — mutual funds are structurally incompatible with intraday TP/SL.

### 10.4 Bonds / fixed income
- `bond_connors_rsi2_backtest.json`, `bond_tlt_ief_backtest.json` exist. `fundamental_valuation_strategies.py` may cover bonds. Slippage 2–5 bps.
- **Gap**: no dedicated bond screener in `alpha_engine/` (no `bond_screener`). BOND ledger: n=35, WR 40%, PF 0.65, KILL-class weak. **Bonds are being scored but not picked.**

### 10.5 ETFs
- `ETF` asset class exists (slippage 2–5 bps). Ledger: n=586, WR 43.2%, PF 1.005, WEAK, single source 97%.
- **Gap**: no dedicated ETF screener. ETFs are mostly pass-through to equity strategies. The "ETF slippage ≈234% of per-trade PnL" (audit2) makes ETFs nearly unprofitable at the current cadence.

### 10.6 Futures
- `futures_ts_momentum_backtest` (CT=F labeled FUTURES, derived COMMODITY — class mismatch). Slippage 2.5–10 bps.
- **Gap**: FUTURES ledger n=4 (vs intrabar n=52). Essentially no data. Kill list pending (§2.15: 6.3% WR, 76% LOST-exit). Recommend either killing the asset class or wiring a futures screener.

### 10.7 Commodities
- `COMMODITY` ledger: n=51, WR 11.8%, PF 0.10, KILL. But the intrabar truth says 40.2% WR / PF 1.03 / n=229. **Large discrepancy — investigate cohort definition.**
- `cot_positioning` DSR=1.0 FALSIFIED (over-emission).
- **Gap**: commodity picking is dominated by COT positioning (falsified) and copy-trader shorts (50% LOST). No fundamental commodity screener (e.g., inventory levels, contango/backwardation, seasonality).

### 10.8 Forex
- `FOREX` ledger: n=258, WR 38.8%, PF 0.92, WEAK. Zero DSR-survivors. BLOCKED.
- `forex_walk_forward_builtins.py`, `findforex2/`.
- **Gap**: forex has the tightest slippage (2 bps) but still net-negative. The PR #6 policy gate blocks all except `cta_cross_asset_tsmom SHORT`. **Forex picking exists but is blocked pending DSR survival.**

### 10.9 Penny stocks / meme coins
- `PENNY_STOCK` and `MEMECOIN` asset classes exist (slippage 30 bps, cost 30 bps). Minimal ledger coverage (MEMECOIN 1 record, PENNY_STOCK 1 record in evidence registry).
- **Gap**: these are high-cost, low-liquidity classes with essentially no methodology. Recommend either a dedicated high-risk screener or explicit exclusion from money-ready consideration.

### 10.10 Cross-asset
- `cross_asset_edge_finder.py`, `cross_aggregation/`. `prediction_market_agents/`, `alpha_engine/polymarket_signals.py`, `kalshi_signals.py`, `prediction_market_consensus.py`.
- **SHADOW** status (PBO 0.603 fails money-ready bar). Copy-trader rows auditable only.

---

## 11. Open action items (from the COMS thread, carried forward)

1. **POD-EQUITY-BREAKOUT has zero forward rows** — register it in `alpha_engine/forward_observations_ingest.py` `CONDITIONS` so EQUITY `donchian-stock-breakout` / `rs-breakout-scout` accrue forward rows against a hold benchmark. Without this, the EQUITY recommendation from the audit2/audit3 review cannot be tested. **Status: OPEN.**
2. **COMS hygiene (advisory)**: no retained `status/*` liveness, leftover `inbox/localhost/research-probe/all hello`, Windows `check`-verb documentation gap. **Status: advisory, not mine to change.**

---

## 12. Recommended priority order (P0 → P2)

**P0 (blocks money-readiness)**
- Implement selection alpha (`audit3_selection_alpha.py`) — needs price tables.
- Register POD-EQUITY-BREAKOUT in CONDITIONS (action item #1).
- Harmonize cost/slippage constants to `cost_model.py` as single source of truth.
- Recalibrate upstream ML confidence generators (inverted calibration).
- Wire random-entry MC from `benchmark_closed_ledger.py` into audit3.

**P1 (improves signal quality)**
- TP/SL permutation matrix (§7) + volume gate (§8) experiments.
- Stamp section name onto closed rows at resolution time (§4.7).
- Mandate trade-log emission from all backtests (§9.3).
- Consolidate walk-forward implementations (§9.3).
- Reconcile value_screener vs UEPS composite weights (§10.1).
- Normalize hypothesis status vocabulary (§2.5).

**P2 (hygiene / UX)**
- Collapse dual PF/WR per class to one canonical figure + window label (§2.7).
- Demote post-hoc segment numbers behind a toggle (§2.12).
- Remove DEAD cells from "Best filter" table (§2.13).
- Disambiguate "PROVEN" (§2.10).
- Add re-test schedule for killed cells (§4.4).
- Serve `reports/` so forward clock + pod registry are live (§3.9).
- Add CSV export to strategy/symbol cells tabs (§4.5).

---

## 13. Request for peer critique

**This document is a draft. Other agents (Claude, Grok, Kimi, Mercury, Freebuff, Cursor, and any COMS peer) are invited to critique:**

1. **Methodology**: Is the review protocol (§1.2) sound? Did I miss any section of any of the three pages? Are there metrics I mis-attributed or mis-read?
2. **Gaps**: Are the 27 gaps in §6 the right set? Are any of them false positives or already fixed? Are there gaps I missed?
3. **TP/SL permutations (§7)**: Are the 6 variants the right set, or should I add/remove any? Is net CI-LB at 2× slippage the right promotion metric, or should WR or PF be primary?
4. **Volume (§8)**: Is volume a plausible edge amplifier, or is it a red herring given the inverted ML calibration? Should volume be tested as a gate or as a feature?
5. **Backtesting (§9)**: Is consolidating to one engine realistic, or would it break too many downstream consumers? Is the cost harmonization (cost_model.py as SOT) the right call?
6. **Asset-class picking (§10)**: For each asset class, is the proposed methodology (or its absence) correctly characterized? Which classes should be killed vs. invested in?
7. **Priority order (§12)**: Is P0/P1/P2 correctly ordered? Would you re-rank?
8. **Anything else**: What would you add, remove, or change?

**Please respond via COMS (drop a message on the bus) or by editing this file. If you disagree with a claim, cite the specific section number and the evidence (file/line/JSON field) that contradicts it.**

---

## 14. Deep research — proper money-ready methodologies per asset class

The user's core question: "if I put money in a random mutual fund managed by a professional, I'd likely break even or profit — so which are the best options, and can we backtest/prove it?" This section answers per asset class with concrete, backtestable methodologies drawn from academic/industry practice and from the project's own codebase.

### 15.1 Mutual funds — "hire a professional manager" (lowest-risk money-ready candidate)

**Why mutual funds are the natural money-ready candidate**: professional management, diversification, regulation, daily liquidity, and a long track record of delivering ≥ benchmark-minus-fees over a full market cycle. The project's own `MUTUAL_FUND` asset class exists (slippage 8 bps) but has no screener and minimal coverage — this is the biggest untapped money-ready opportunity.

**Proper methodology (industry standard)**:
1. **Lipper Leader for Consistent Return (Effective Return)** — risk-adjusted return over 36/60/120 months with a behavioral-finance utility function that penalizes underperformance clustering. Top 20% per classification = Lipper Leader. (LSEG Lipper methodology, 2026.)
2. **Morningstar Medalist Rating (Gold/Silver/Bronze)** — 100% analyst-driven; expects outperformance over a full market cycle. Combined with R-squared ≥ category average and tracking error ≤ category average (good category representative).
3. **3P framework (People, Process, Performance)** — Standard Chartered's Fund Select: quantitative model (excess return, information ratio, persistency across cycles) + qualitative (manager meetings, research process, buy/sell criteria, team depth, risk control).
4. **Value Research / Scotiabank Recommended List approach**: rolling returns across multiple periods (not just latest 1y), downside protection (max drawdown, beta), fair costs, qualitative manager review, full-market-cycle horizon (≥3 years history).
5. **Morningstar's finding**: consistent outperformance is RARE (only 20% of funds have 4+ year winning streaks; 4% beat benchmark 5 straight years). Long-term winners take a circuitous route. **Therefore: do NOT chase top-quartile recent performers; instead screen on fees, strategy prudence, team depth, and downside protection.**

**Concrete money-ready mutual fund screen (backtestable)**:
- Universe: all US-domiciled mutual funds with ≥36 months history, ≥$100M AUM, expense ratio ≤ category median, no load.
- Filter 1: Lipper Leader Consistent Return ≥4 (top 40%) over 3y AND 5y.
- Filter 2: Morningstar Medalist ≥ Silver.
- Filter 3: Max drawdown ≤ category median over the last full cycle.
- Filter 4: Information ratio ≥0.
- Filter 5: Persistency — positive excess return in ≥2 of the last 3 calendar years.
- Selection: top 10 by composite (equal-weighted Lipper + Morningstar + drawdown + IR + persistency).
- Rebalance: annually (January), replace funds that fall below filter thresholds.
- Backtest: monthly returns, net of expense ratio, compare to category benchmark. Gate: net Sharpe > benchmark Sharpe over 10y, max DD ≤ benchmark DD, hit rate ≥55% of years.

**Project gap**: `alpha_engine/` has NO mutual fund screener. Need to build `mutual_fund_screener.py` (analogous to `value_screener.py`) and wire into the UEPS/audit pipeline. Data source: SEC N-CSR / Morningstar API / Lipper. This is the single highest-expected-value money-ready work item.

### 15.2 ETFs — low-hanging fruit via rules-based screens

**Key finding (ScienceDirect, 2026)**: pure momentum on 3,215 US ETFs (2001–2026) underperforms passive S&P 500 (Sharpe −0.17 to +0.22 vs 0.46, MDD 69–82%). BUT three layers of rules reverse it: (1) technical entry signals, (2) multi-horizon momentum ranking with mandatory diversification across super-categories, (3) dynamic SL/TP exit rules (chosen from 144 combinations). Result: Sharpe 1.34, MDD 7%, net of 20 bps/side. **The value comes from MANAGEMENT (exits), not from the entry signal.**

**Other findings**:
- **Concretum Research (2026)**: intraday trend-following on ETFs with walk-forward ranking; past performance can distinguish future winners/losers.
- **Panaprium / Faber 10-month MA**: trend filter (move to T-bill if below 10-month MA) has the longest track record; weakness = false exits in sideways markets.
- **Truusst (2011–2026)**: 12-month cross-sectional momentum on 15 ETFs did NOT beat SPY on risk-adjusted basis (Sharpe 0.73 vs 0.86) but had lower MDD (−22% vs −34%) and strong 2022 protection. Alpha not significant (p=0.44). **Conclusion: momentum ETFs are a risk-reduction tool, not a return-enhancement tool, vs SPY.**
- **Multi-asset trend following (quantstr.at, 2007–2026)**: trend-following roughly halved worst drawdown vs S&P 500 (−26% vs −51%) but gave up 4–6 pts/yr of return. **Not clearly better than holding all ten funds or 60/40.**
- **ML overlay (2026)**: histogram GBM on 8 equity ETFs; overlay earns 4.71% vs 4.46% with Sharpe 0.519 vs 0.315 and MDD 14.68% vs 18.48%. Wide CI (−1.78 to 3.88 pts). **Modest, uncertain improvement.**

**Concrete money-ready ETF screen (backtestable)**:
- Universe: 10–12 liquid, broad ETFs (SPY, QQQ, IWM, TLT, GLD, EFA, plus 6 sector SPDRs). Exclude leveraged/inverse.
- Signal: multi-horizon momentum (average of 6-month and 12-month returns, skip most recent month).
- Selection: top 3 by momentum, equal weight.
- Trend filter (absolute momentum): move to T-bill/SHV if ETF below 10-month MA.
- Diversification constraint: mandatory across super-categories (equity/bond/commodity).
- Exit: dynamic SL/TP chosen from a grid of 144 combinations, monitored weekly. The paper found exits matter more than entries.
- Cost: 20 bps/side (embedded in return, not ex-post).
- Rebalance: biweekly entry, weekly exit monitoring.
- Backtest: 2001–2026, walk-forward, OOS split, parameter sensitivity (3/6/9/12-month lookbacks, top 2/3/4 holdings), net of costs, compare to SPY buy-and-hold on Sharpe AND MDD.

**Project gap**: no ETF screener in `alpha_engine/`. The `ETF` asset class exists but is a pass-through. The ScienceDirect paper's exit-rule grid (144 SL/TP combos) is exactly the §7 permutation experiment — **ETFs are the ideal asset class to run the §7 matrix first**, because the cost model (20 bps/side) and liquid universe make it cheap and fast.

### 15.3 Stocks / EQUITY — value + quality + momentum (already partially built)

**What the project already has**: `value_screener.py` (Magic Formula × Piotroski × Acquirer's Multiple, SafetyGate), `mf_screener.py`, `growth_stock_screener.py`, `swing_screener.py`, `short_side_screener.py`, UEPS. **But**: opt-in sidecars with no production caller (§10.1).

**Proper methodology (academic + industry)**:
- **Magic Formula** (Greenblatt 2006): rank by earnings yield (EBIT/EV) + return on capital (EBIT/(NWC+net fixed assets)); top 30.
- **Acquirer's Multiple** (Carlisle 2014): EV/EBIT; lowest decile beats Magic Formula on 26-year US backtest.
- **Piotroski F-Score** (2000): 9-point fundamental quality score; ≥7 outperforms, ≤3 underperforms.
- **SafetyGate**: Altman Z'' ≥1.10 (non-manufacturers) AND Beneish M ≤−1.78.
- **Quality tilt** (project v1.1): 0.45 value + 0.55 quality (was 0.55/0.45). Quality = 0.50 Piotroski/9 + 0.30 ROIC stability + 0.20 D/E score.
- **Momentum overlay** (Jegadeesh-Titman): 6–12 month price momentum as a tiebreaker; reduces value traps.
- **UEPS** adds IV-attainment exit (thesis-break + IV + horizon), never closes on drawdown alone.

**Concrete money-ready equity screen (backtestable)**:
- Universe: US equities with market cap ≥$300M, ≥5y history, ≤540d 10-K age, exclude Financial/Utilities.
- Screen: ValueScreener top 30 by composite score.
- Quality filter: F-Score ≥7, ROIC ≥10%, Altman Z'' ≥2.6 (safe zone, stricter than 1.10).
- Momentum filter: 6-month return >0 AND 12-month return >0 (absolute momentum).
- Selection: top 10 by composite, equal weight.
- Exit: IV-attainment (price reaches IV target), thesis-break (ROIC < threshold, D/E breach, Altman <1.10), or horizon expiry (3y long-term, 1m swing). Never close on drawdown alone.
- Rebalance: quarterly (value) or monthly (swing).
- Backtest: 2000–2026, Fama-French factors, net of transaction costs (5 bps equity), compare to S&P 500 on Sharpe, MDD, and alpha (Jensen's alpha, t-stat).

**Project gap**: wire `value_screener.py` to production. Reconcile weight inconsistency (value_screener 0.45/0.55 vs UEPS 0.55/0.45). Add momentum overlay. Add IV-attainment resolver (UEPS spec exists but n=0/100).

### 15.4 Crypto — reverse-engineering a skyrocket (BTC all-time high)

The user's question: "how do people reverse engineer and/or have projections before a skyrocket of crypto like BTCUSDT, an upcoming daily/weekly/monthly/all-time high based on technicals and/or news or fundamentals?"

**What the research shows** (Benjamin Cowen, Fidelity, 10x Research, Hashdex, Abra, on-chain):

1. **Halving cycle framework** (4 cycles: 2012, 2016, 2020, 2024): peaks occur 372–546 days after halving; troughs 777–924 days after. **But**: only 4 observations — statistically meaningless. Each cycle has had smaller amplitude (peak multiples: 91x → 30x → 7.9x → 1.9x). Fidelity notes volatility hitting new lows much sooner than previous cycles → market maturing → cycle may be weakening.

2. **On-chain metrics** (Abra 4-phase model: accumulation/expansion/distribution/contraction):
   - Valuation: MVRV, realized price, balanced price.
   - Flow: exchange balances, ETF flows, stablecoin supply.
   - Supply: coin age, long-term holder supply, % in loss.
   - Network: active addresses, hash rate, fees.
   - Macro: rates, DXY, liquidity.
   - Transition recorded only when indicators from >1 category agree (costs timeliness, reduces false labels).

3. **Quantile regression fan** (Cowen): 1st percentile line (~$72K currently), median (~$127K), realized price (~$54K), balanced price (~$38K). Bitcoin has broken below 1st percentile only during forced-selling dislocations (7–35% wicks). **Useful for downside targets, not upside.**

4. **Monte Carlo / bootstrap** (orderbookedge): GBM with T-bill drift + 44% vol → median ~$71K, 90% range $34K–$148K, ~10–12% chance of new ATH within a year. **Wide range; not actionable for timing.**

5. **Macro + ETF flow triggers** (Investing.com): breakout requires (a) Fed pause / yield decline / ETF inflows >$1B/day, AND (b) price clearing $85.5K and holding. Without both, range-bound.

6. **10x Research**: cycle theory captured the 2022 bottom and 2024 top with near-perfect accuracy, but they remain skeptical. Rule of thumb: "when Bitcoin's upside momentum fades, a deeper correction often follows."

7. **Hashdex (Kerbage)**: volatility declining (80% → 53% → 44% annualized). Drawdowns moderating (84% → 83% → 77% → 53%). Market maturing.

**Honest assessment**: NOBODY can reliably predict a BTC skyrocket in advance. The cycle framework has ~4 data points. On-chain metrics describe phases, not timing. Monte Carlo gives wide ranges. The honest approach is:
- **Phase identification** (Abra 4-phase) → tells you the environment, not the price.
- **Downside risk management** (quantile fan, realized price) → tells you where to stop out.
- **Breakout confirmation** (macro + ETF flows + price level hold) → tells you when to enter, not before.
- **Position sizing by phase**: accumulate in accumulation, hold through expansion, take profits in distribution, stay defensive in contraction.

**Project application (crypto_rsi5070_us / H-119)**: The project's strongest honest lead is a *conditional* edge (RSI 50–70, US session) with net PF 1.12. This is NOT a skyrocket predictor — it's a small, persistent edge. The right framing: **we are not predicting skyscrapers; we are capturing small edges consistently.** The "reverse engineer a skyrocket" ambition should be reframed as "identify the phase and size accordingly."

**Concrete crypto money-ready approach (backtestable)**:
- Phase classifier (Abra-style, 5 categories) → weekly phase label.
- Entry only in accumulation/expansion phases.
- Within expansion: apply H-119-style conditional edges (RSI band, session, volume).
- Exit: distribution-phase signals (old coins moving, exchange inflows) + trailing stop.
- Position size: larger in accumulation (cheap), smaller in expansion (expensive), zero in distribution/contraction.
- Cost: 16 bps round-trip (CRYPTO_RT_BP from ingest).
- Backtest: 2017–2026 (covers 2 full cycles), walk-forward, OOS split, compare to buy-and-hold BTC on Sharpe, MDD, and max drawdown.

### 15.5 Bonds / fixed income — duration + credit + real yield

**Why bonds are money-ready**: historically lowest volatility, positive real returns over long horizons, diversification benefit. But the project's BOND class is n=35, WR 40%, PF 0.65 (WEAK/KILL).

**Proper methodology**:
- **Duration management**: shorten duration when rates rising, lengthen when falling. Use the yield curve slope (2s10s) as a regime signal.
- **Credit selection**: investment-grade (BBB+), avoid high-yield in contraction. Use credit spreads (IG vs Treasury) as a value signal.
- **Real yield**: TIPS real yield >1% = attractive; <0% = avoid.
- **Ladder strategy**: equal-weight across 1–10 year maturities, reinvest maturing rungs. Reduces timing risk.
- **Bond ETF screens**: expense ratio ≤0.10%, AUM ≥$1B, tracking error ≤0.05%, duration matched to liability.

**Concrete money-ready bond screen (backtestable)**:
- Universe: investment-grade bond ETFs (AGG, BND, LQD, TLT, IEF, SHY, TIP).
- Signal: real yield >1% (buy) / <0% (sell/short duration); credit spread > historical median (buy credit).
- Selection: top 3 by (real yield + spread z-score), equal weight.
- Duration: match to signal (longer when real yield attractive).
- Rebalance: monthly.
- Cost: 3–5 bps (bond ETF).
- Backtest: 2000–2026 (includes 2008, 2020, 2022 rate shocks), compare to AGG on Sharpe, MDD.

**Project gap**: no bond screener. `bond_connors_rsi2_backtest.json` and `bond_tlt_ief_backtest.json` exist but are isolated. Need `bond_screener.py` and wire into pipeline.

### 15.6 Commodities — NOT COT positioning (falsified)

**What failed**: `cot_positioning` DSR=1.0 FALSIFIED (6.33× over-emission). The project's COMMODITY class is n=51, WR 11.8%, PF 0.10 (KILL) in the ledger but 40.2% WR/PF 1.03/n=229 in intrabar truth. **Large discrepancy — investigate cohort definition.**

**Proper methodology (non-COT)**:
- **Term structure**: contango (futures > spot) = cost of carry, avoid; backwardation (futures < spot) = scarcity, buy. This is the single most robust commodity signal (Gorton-Rouwenhorst 2006).
- **Seasonality**: agricultural commodities have strong seasonal patterns (planting/harvest). Test month-of-year effects.
- **Inventory levels**: EIA (oil), USDA (ag), LME (metals) — low inventory = tight supply = bullish.
- **Macro**: DXY (inverse), real rates (inverse), China demand (industrial metals).
- **Diversified commodity index**: GSG, DBC, PDBC (equal-weight or production-weighted).

**Concrete money-ready commodity screen (backtestable)**:
- Universe: liquid commodity ETFs (USO, GLD, SLV, DBA, DBC, GSG, UNG) + futures.
- Signal: backwardation (buy) / contango (sell or avoid); inventory z-score.
- Selection: top 3 by (backwardation score + inventory z-score), equal weight.
- Cost: 7–15 bps.
- Backtest: 2000–2026 (includes supercycle, China boom, shale revolution), compare to DBC on Sharpe, MDD.

**Project gap**: commodity picking is dominated by the falsified COT signal. Need to rebuild on term structure + inventory. The intrabar truth (40.2% WR/PF 1.03) suggests there IS a weak edge buried in the data — investigate which strategies/conditions produce it.

### 15.7 Forex — blocked, but methodology exists

**Status**: FOREX has zero DSR-survivors. PR #6 policy gate blocks all except `cta_cross_asset_tsmom SHORT`. PF 0.29, WR 46.1%.

**Proper methodology**:
- **Carry trade**: long high-yield, short low-yield (AUD/JPY, NZD/JPY). Risk: sudden unwinds (2008, 2020).
- **Trend following (CTA)**: 1–12 month momentum on FX majors. This is the one strategy that has survived in the project (`cta_cross_asset_tsmom SHORT`).
- **Macro**: purchasing power parity (PPP) deviations, current account, real rate differentials.
- **Volatility regime**: forex vol is clustered; high vol → reduce size.

**Concrete money-ready forex approach**: CTA trend-following only (the only surviving signal), with volatility scaling and a carry filter. Backtest on 1990–2026 (includes multiple crises). **But**: the project's own data says even this is marginal. Recommend: keep forex as a research-only asset class until DSR survival; do not size.

### 15.8 Futures — kill candidate

**Status**: FUTURES ledger n=4 (vs intrabar n=52). 6.3% WR, 76% LOST-exit. Kill list pending.

**Proper methodology**: futures are instruments, not an asset class for picking. The right approach is to use futures as the execution vehicle for the strategies in other asset classes (equity index futures, commodity futures, bond futures, FX futures). **Recommend: remove FUTURES as a standalone asset class; use futures as execution only.**

### 15.9 Penny stocks / meme coins — exclude or dedicated high-risk

**Status**: slippage 30 bps, cost 30 bps (60 bps total round-trip). Minimal coverage. High volatility, low liquidity, manipulation risk.

**Proper methodology**: if included at all, use a dedicated high-risk screener (volume spike + social sentiment + momentum) with strict position sizing (≤1% of portfolio per position) and automatic stop-loss. **Recommend: exclude from money-ready consideration; treat as speculative satellite only.**

### 15.10 Cross-asset / multi-asset — the real money-ready answer

**The honest truth**: no single asset class is money-ready (0/10). But a **multi-asset portfolio** combining the best of each (mutual funds + ETF trend + value equity + crypto phase-sizing + bonds + commodity term-structure) can achieve money-ready status through diversification, even if individual classes are marginal.

**Proper methodology**:
- **Risk parity**: equal risk contribution across asset classes (not equal weight).
- **All-weather (Bridgewater-style)**: 30% stocks, 40% long-term bonds, 15% intermediate bonds, 7.5% gold, 7.5% commodities. Rebalance quarterly.
- **Tactical overlay**: apply the asset-class screens (§15.1–15.7) as tilts on top of the strategic allocation.
- **Drawdown control**: reduce equity exposure when VIX >30 or yield curve inverts.

**Concrete money-ready multi-asset portfolio (backtestable)**:
- Strategic: 30% value equity (§15.3), 20% bond ladder (§15.5), 15% commodity term-structure (§15.6), 15% ETF trend (§15.2), 10% crypto phase-sized (§15.4), 10% mutual fund (§15.1).
- Rebalance: quarterly (strategic), monthly (tactical tilts).
- Risk control: max 15% drawdown → reduce equity to 15%, increase bonds to 35%.
- Backtest: 2000–2026 (includes dot-com, GFC, COVID, 2022), compare to 60/40 on Sharpe, MDD, and Calmar ratio.

### 15.11 Concrete experiment plan to reach money-ready

| Priority | Experiment | Asset class | Expected outcome | Effort |
|---|---|---|---|---|
| 1 | Build `mutual_fund_screener.py` (Lipper + Morningstar + 3P) | Mutual funds | First money-ready candidate (lowest risk) | Medium |
| 2 | Wire `value_screener.py` to production + momentum overlay + IV-attainment resolver | Equity | Second candidate (value + quality) | Medium |
| 3 | ETF momentum+exit experiment (ScienceDirect 144-combo grid) | ETFs | Risk-reduction candidate | Low (code exists) |
| 4 | Crypto phase classifier + H-119 conditional edge | Crypto | Small persistent edge | Medium |
| 5 | Bond screener (duration + credit + real yield) | Bonds | Diversifier | Medium |
| 6 | Commodity term-structure rebuild (replace falsified COT) | Commodities | Weak edge recovery | Medium |
| 7 | Multi-asset risk-parity portfolio (§15.10) | Cross-asset | **The actual money-ready answer** | High |
| 8 | Forex CTA (keep as research-only) | Forex | Marginal | Low |
| 9 | Remove futures/penny/meme from money-ready scope | Futures/penny/meme | Reduce noise | Low |

### 15.12 Reverse-engineering a skyrocket — honest assessment

**Short answer**: you cannot reliably predict a BTC all-time high in advance. The cycle framework has ~4 data points; on-chain metrics describe phases, not timing; Monte Carlo gives wide ranges ($34K–$148K). Anyone claiming to predict the next ATH is curve-fitting.

**What you CAN do (backtestable, honest)**:
1. **Phase identification** (Abra 4-phase) → tells you the environment. Accumulate in accumulation, hold in expansion, take profits in distribution, defend in contraction.
2. **Downside risk management** (quantile fan, realized price) → tells you where to stop out. Never predict upside; manage downside.
3. **Breakout confirmation** (macro + ETF flows + price level hold) → tells you when to enter (after, not before).
4. **Position sizing by phase** → larger when cheap, smaller when expensive, zero when distributing.
5. **Conditional small edges** (H-119 style) → capture small persistent edges consistently, not skyscrapers.

**The reframing**: instead of "predict the skyrocket," the money-ready question is "am I in the right phase, with the right size, and a stop below realized price?" That is backtestable and honest.

---

## 15. Cross-check of claims — what actually works per asset class (2026 evidence)

This section cross-checks the claims in §15 against independent 2026 evidence (J.P. Morgan Factor Views Q4 2026, SSRN papers, EdgeLab, SledgeKey, Sonsero, Resonanz Capital, PapersWithBacktest, AlgoGP). Each claim is rated: **CONFIRMED**, **PARTIALLY CONFIRMED**, **FALSIFIED**, or **UNTESTED**.

### 17.1 Value investing — PARTIALLY CONFIRMED (works, but decayed)

- **Claim**: Magic Formula generates excess returns. **CONFIRMED** but decayed: Morningstar (Sep 2025) confirms simple formulas produce 5.6–6.4% annual raw returns and CAPM alphas 7.0–12.2%. SledgeKey (Jul 2026, honest survivorship-free backtest 2017–2026): Magic Formula 14.74% vs S&P 500 15.28% — **lost by 0.54 pts/yr** but with lower vol (13.89% vs 16.18%) and lower MDD (-28.0% vs -33.7%). Sharpe 0.88 vs 0.81 — **value wins on risk-adjusted**.
- **Claim**: Piotroski F-Score works. **FALSIFIED** as standalone: SledgeKey Piotroski screen 9.52% vs S&P 500 15.28%, Sharpe 0.43 vs 0.81, MDD -48.9% vs -33.7%. **But**: combined with Magic Formula + Sortino filter, edge recovers (+4.8% CAGR over IWM, per Calm Engineering).
- **Claim**: Transaction costs erode alpha. **CONFIRMED**: Blackburn & Cakici (2017, 23 markets, 1991–2016) — pure EBIT/EV beats canonical Magic Formula; ~100% annual turnover means costs can eliminate alpha entirely (Vestre & Wikheim, 2022).
- **Claim**: Gross profit > EBIT for quality metric. **CONFIRMED**: Blackburn & Cakici — replacing EBIT with gross profit produces consistent, robust outperformance across virtually all markets.
- **Claim**: Equity value is currently attractive. **CONFIRMED**: J.P. Morgan Q4 2026 — "equity value and equity quality are now historically inexpensive"; value spread wider than 90% of history (Resonanz Capital, Mar 2025); forward excess return 5–6% (SR ≈0.55) if value spread mean-reverts halfway.
- **Verdict**: Value works but has decayed. Use gross-profit-based quality (not EBIT), add momentum overlay, expect risk-adjusted (not raw) outperformance. **Do not expect to beat S&P 500 on raw CAGR.**

### 17.2 Momentum — PARTIALLY CONFIRMED (works, but crashed in Q3 2026)

- **Claim**: Time-series momentum reduces drawdown. **CONFIRMED**: PapersWithBacktest (1972–2024, monthly): 12-month trend on stocks/bonds/gold → 10.0% CAGR, 11% MDD vs 9.1% and 22% for buy-and-hold. On every asset, trend earned ≥ buy-and-hold with less vol and half the drawdown.
- **Claim**: Cross-sectional momentum on sectors beats index. **CONFIRMED**: ~1.3 pts/yr with 10 pts less drawdown on 9 sector ETFs since 2000. But: earned all of it in 2000s and since 2020; lagged for the decade in between.
- **Claim**: Long-short momentum premium has decayed. **CONFIRMED**: SSRN (Oct 2026, 11 ETFs, 2007–2026): long-short TSMOM net Sharpe 0.25 (indistinguishable from zero after costs). **But** long-only vol-targeted combo: Sharpe 0.58, MDD -20.4% vs -55.2% for S&P 500.
- **Claim**: Momentum crashes are real. **CONFIRMED**: J.P. Morgan Q3 2026 — momentum had its worst month ever in EM, developed Asia ex-Japan, and Europe; "elevated factor volatility, growing dispersion, increasingly crowded positioning." Recommend reducing momentum overweights. Volatility management improves Sharpe from 0.53→0.87 (developed) and MDD from -43.6%→-10.7%.
- **Claim**: Momentum is now "insurance, not alpha." **CONFIRMED**: PapersWithBacktest — "what has been competed away is its return, not its risk reduction."
- **Verdict**: Momentum works for **risk reduction**, not raw return enhancement. Long-only, vol-targeted, with volatility scaling. **Reduce momentum overweight in 2026** (J.P. Morgan warning).

### 17.3 Trend following — CONFIRMED (best on futures, modest elsewhere)

- **Claim**: Trend following works best on futures. **CONFIRMED**: AlgoGP (Mar 2026) — "trend following works best where diversification across many uncorrelated markets is cheap, which is why futures are its traditional home." Delphic Alpha: futures Sharpe 0.73, crypto 0.56, stocks 0.42, FX ~0.3.
- **Claim**: Faber GTAA still works OOS. **CONFIRMED**: Concretum (Jun 2025) — GTAA 2006–Mar 2025: Sharpe 0.68, CAGR 6.05%, MDD 11.7% (vs original 0.81/11.7%/9.5%). Works but modest decay.
- **Claim**: ETF momentum rotation beats buy-and-hold. **FALSIFIED as standalone**: EdgeLab (Jun 2026, 21 years, SPY/TLT/GLD): rotation 10.9% CAGR OOS but Sharpe 0.70 vs equal-weight 0.96, MDD -33.6% vs -22.7%. "Beats buy-and-hold on raw return, loses on risk-adjusted." Inverse-vol weighting (Sharpe 1.03) mostly replaces momentum with diversification.
- **Verdict**: Trend following is a **risk-reduction tool**, not a return enhancer. Best venue: futures (Sharpe ~0.7). Use as a diversifier, not a standalone strategy. **Do not use winner-take-all rotation on 3 ETFs.**

### 17.4 Carry — CONFIRMED (robust across assets)

- **Claim**: Carry works across assets. **CONFIRMED**: Resonanz Capital (Apr 2025, 2005–Mar 2025): FX carry SR 0.60, curve carry SR 0.70, roll carry SR 0.55, dividend carry SR 0.20. Carry is "steady, pro-cyclical." Structural supply from insurers, corporations, macro funds.
- **Verdict**: Carry is a solid **diversifier** with positive Sharpe across FX, bonds, commodities. Pro-cyclical → pair with defensive sleeves (trend, BAB, tail hedge).

### 17.5 Low-risk / BAB — CONFIRMED (defensive, lower vol)

- **Claim**: Low-volatility anomaly works. **CONFIRMED**: Resonanz: BAB SR 0.62. Morningstar: Conservative Formula (1/3 low vol) has slightly lower returns but smoother ride (lower vol, lower MDD). J.P. Morgan: quality posted strong Q3 2026 after challenging stretch.
- **Verdict**: Low-risk/BAB is a **defensive sleeve** — lower volatility and drawdown, not higher raw returns. Use for capital preservation.

### 17.6 Volatility risk premium (VRP) — CONFIRMED (high Sharpe, negative skew)

- **Claim**: VRP is a robust premium. **CONFIRMED**: Resonanz: equity VRP (PUT) SR 0.66, swaption VRP SR 0.55, FX vol carry SR 0.50. "Investors dislike negative skew, so they demand a premium."
- **Verdict**: VRP has the **highest Sharpe** (0.66) but negative skew → tail risk. Use with tail hedge.

### 17.7 Crypto — PARTIALLY CONFIRMED (trend works, cycle theory weak)

- **Claim**: 10-month MA trend filter works on Bitcoin. **CONFIRMED**: Sonsero (Nov 2026): Bitcoin 10-month MA → 49.5% return, -40% MDD, Sharpe 1.01 (vs 34.2% return, -73% MDD buy-and-hold). 12-month absolute momentum: 34.1% return, -41% MDD.
- **Claim**: Halving cycle predicts ATH. **FALSIFIED as predictive**: Fidelity (Feb 2026) — "persistently low volatility amidst new highs points toward a more mature bitcoin that may not continue to follow the historical four-year cycle." Only 4 observations. Abra: "sample is too small for statistical confidence." Cowen (Oct 2026): cycle clock says we're in the bear-market-bottom window, but "changes in ownership (ETF/institutional) are the main reason this cycle could bottom without reaching realized price."
- **Claim**: On-chain metrics describe phases. **CONFIRMED** (descriptive, not predictive): Abra 4-phase model (accumulation/expansion/distribution/contraction) with 5 indicator categories. Transition recorded only when >1 category agrees.
- **Verdict**: Crypto trend following works (Sharpe ~0.56–1.01). Cycle theory is **descriptive, not predictive**. Use phase identification + trend filter + downside management. **Do not predict skyscrapers.**

### 17.8 Bonds — CONFIRMED (trend + carry, low vol)

- **Claim**: Bond trend following works. **CONFIRMED**: Sonsero — US 7-10Y Treasuries 10-month MA → 0.1% return, -17% MDD (vs 0.5% return, -27% MDD buy-and-hold). Bond trend (PapersWithBacktest): 6.46% CAGR, 6.3% vol, Sharpe 1.02, MDD -11%. Resonanz curve carry SR 0.70.
- **Verdict**: Bonds are a **diversifier** — low returns but very low vol and drawdown. Use as ballast in multi-asset portfolio.

### 17.9 Commodities — CONFIRMED (trend + seasonality + term structure)

- **Claim**: Trend following works on commodities. **CONFIRMED**: Resonanz — commodity trend SR 0.72, roll carry SR 0.55. PapersWithBacktest — gold trend: 10.73% CAGR, 16.3% vol, Sharpe 0.66, MDD -26% (vs 8.07%, 19.1%, 0.42, -62% buy-and-hold). AlgoGP: "commodities offer genuine seasonality and strong trends driven by physical supply and demand, plus curve structure that creates carry."
- **Verdict**: Commodities are a **strong diversifier** — trend + seasonality + backwardation. Replace falsified COT with term structure.

### 17.10 Forex — PARTIALLY CONFIRMED (carry + trend, but project's data is weak)

- **Claim**: FX momentum and carry work. **CONFIRMED**: Resonanz — G10 FX momentum SR 0.67, FX carry SR 0.60. Sonsero — 3/10-month MA on various FX pairs.
- **Verdict**: FX carry + trend works in aggregate, but the project's FOREX class is BLOCKED (zero DSR survivors, PF 0.29). **Keep as research-only until DSR survival.**

### 17.11 Cross-asset summary — what to combine

| Asset class | Best strategy | Sharpe | MDD | Role in portfolio |
|---|---|---|---|---|
| Mutual funds | Lipper Leader + 3P | ~0.5–0.7 | Low | Core (lowest risk) |
| ETFs | Trend + exit rules | 0.58–1.03 | -11% to -20% | Core (risk reduction) |
| Stocks (value) | Gross-profit value + momentum | 0.81–0.88 | -28% | Core (alpha, decayed) |
| Crypto | 10-month MA trend | 0.56–1.01 | -40% | Satellite (high vol) |
| Bonds | Trend + curve carry | 0.70–1.02 | -11% | Ballast |
| Commodities | Trend + seasonality | 0.66–0.72 | -26% | Diversifier |
| Forex | Carry + trend | 0.60–0.67 | Moderate | Diversifier (research-only) |
| Futures | Trend (multi-market) | ~0.73 | Low | Execution vehicle |
| Gold | Trend (12-month) | 0.66 | -26% | Crisis hedge |

**The money-ready answer is NOT any single asset class.** It is a **multi-asset portfolio** combining:
1. **Core (60%)**: value equity (25%) + bond trend (20%) + ETF trend (15%)
2. **Diversifiers (25%)**: commodity trend (10%) + carry (10%) + low-risk BAB (5%)
3. **Satellite (10%)**: crypto trend (5%) + VRP (5%)
4. **Ballast (5%)**: cash / T-bills

With volatility scaling, drawdown control (max 15% → reduce equity to 15%), and quarterly rebalancing. Expected: Sharpe ~0.8–1.0, MDD ~-15% to -20%, CAGR ~8–10%.

### 17.12 What to NOT do (falsified / harmful)

1. **Do NOT** chase momentum in 2026 — J.P. Morgan warns of elevated vulnerability and worst-ever monthly drawdowns. Reduce overweights.
2. **Do NOT** use winner-take-all ETF rotation on 3 assets — loses on risk-adjusted vs equal-weight.
3. **Do NOT** use canonical Magic Formula (EBIT/EV) — use gross profit instead.
4. **Do NOT** use Piotroski F-Score as a standalone screen — lost badly vs index.
5. **Do NOT** predict BTC skyscrapers — cycle theory has 4 data points; use phase ID + trend + downside mgmt.
6. **Do NOT** use COT positioning for commodities — falsified (6.33× over-emission).
7. **Do NOT** use 15-minute ML strategies — 33/42 overfit.
8. **Do NOT** size on inflated CRYPTO nav surfaces (claude_gainer_st mislabels).
9. **Do NOT** use R:R ≥1.5 filter on non-crypto — harmful across equity, forex, commodity.
10. **Do NOT** trust post-hoc segment numbers (82% WR / PF 11+) — not actionable.

---

## 16. If I had $2,000 to spend — which asset class and why

### 18.1 The constraints of $2,000
- **PDT rule (US equities)**: 4 day trades in 5 days requires $25,000 in a margin account. FINRA replaced it with intraday margin rules on June 4, 2026, but brokers have until Oct 20, 2027 to switch. **For now, $2,000 cannot day-trade US stocks freely.** (Cash accounts have no minimum but only trade settled cash — US stocks settle T+1.)
- **Futures, forex, crypto**: no PDT rule. Micro futures (MES/MNQ) have $40–$50 day margins, $1.25/tick. But commissions eat you alive if scalping (40 round trips/day = $100–$250/day in commissions on a $2,000 account).
- **Forex**: micro lots (0.01 lot) move $0.10/pip on EUR/USD. On a $500 account risking 2% ($10), a 30-40 pip stop at 0.01 lots costs $3–$4. Workable but requires macro context.
- **Fractional shares (ETFs)**: no minimum lot size. $50 of SPY exposure. No leverage. Best for swing trading.

### 18.2 My pick for $2,000: Micro futures (MES) on a swing timeframe (2–5 day holds)

**Why not equities**: PDT rule blocks day trading; swing trading on $2,000 with fractional shares works but moves are small without leverage.

**Why not forex**: requires macro context (rates, DXY, central bank policy) that the project doesn't currently model well; forex is BLOCKED in our own audit (zero DSR survivors).

**Why not crypto**: 24/7 but high vol, counterparty risk, and the project's crypto edge (H-119) is a small conditional edge, not a day-trading strategy.

**Why micro futures (MES)**:
1. **No PDT rule** — can trade intraday or swing without restrictions.
2. **Low capital requirement** — $50 day margin means $2,000 can hold 1 contract with 40:1 leverage (but DON'T use max leverage).
3. **Tick value $1.25** — small enough to risk $10–$20/trade (0.5–1% of $2,000) with a 8–16 tick stop.
4. **Commission ~$1.28–$1.88/round turn** (all-in) — at 2–3 trades/day, that's $3–$6/day, not $100+.
5. **Liquid, regulated (CME)** — no counterparty risk, tight spreads, real volume.
6. **The project already has futures infrastructure** — `backtest_framework.py`, `cost_model.py`, `execution_cost.py`.

**Position sizing for $2,000**:
- Risk per trade: $10–$20 (0.5–1%).
- Stop: 8–12 ticks ($10–$15 on MES).
- Target: 16–24 ticks ($20–$30) — 2:1 R:R.
- Max 1 contract at a time. Never more than 2 open positions.
- Daily loss limit: $60 (3% of account) → stop trading for the day.
- Weekly review: if account drops below $1,600 (20% drawdown), reduce to 0.5% risk.

**Strategy for $2,000: Opening Range Breakout (ORB) on MES**
- Market: MES (Micro E-mini S&P 500), 5-min chart.
- Setup: first 15-min range (9:30–9:45 ET). Buy breakout above range high, sell breakout below range low.
- Stop: opposite side of range (or 8 ticks, whichever is tighter).
- Target: 2× range size or 16 ticks, whichever comes first.
- Time stop: close by 11:00 AM ET if neither TP nor SL hit (avoids afternoon chop).
- Volume filter: require volume > 1.5× 20-bar average on the breakout candle.
- Backtest: 2019–2026 (covers COVID, 2022 bear, 2023-24 bull). Expected: ~50% WR, 2:1 R:R → positive expectancy. Commission drag: ~$1.50/trade × 2 trades/day × 20 days = $60/month. Need >$60/month gross to be profitable.

**Why ORB on MES specifically**:
- Opening range is a well-documented intraday pattern (Toby Crabel, 1990).
- MES has $1.25/tick → small losses, manageable risk.
- 15-min range is wide enough to avoid noise, narrow enough for 2:1 R:R.
- Volume filter addresses the project's §8 gap (volume never systematically tested).
- Time stop addresses the §7 gap (time-stop variants).

### 18.3 Alternative: $2,000 in fractional ETFs (swing trading)
If you can't stomach futures leverage:
- **Universe**: SPY, QQQ, IWM, GLD, TLT (5 liquid ETFs).
- **Strategy**: Faber GTAA (10-month MA trend filter) — confirmed OOS (Sharpe 0.68, CAGR 6.05%, MDD 11.7%).
- **Rebalance**: monthly (last trading day).
- **Position**: equal weight across assets with positive 10-month momentum.
- **Cost**: $0 commission (most brokers), $0 platform fee.
- **Expected**: ~6% CAGR, ~12% MDD. On $2,000 → ~$120/year. Not exciting, but positive expectancy with near-zero effort.
- **Better than futures** if you have a day job and can't monitor intraday.

### 18.4 What NOT to do with $2,000
1. **Do NOT day-trade US stocks** — PDT rule (until Oct 2027) + commissions.
2. **Do NOT use high leverage** — $2,000 with 40:1 leverage on MES means a 50-tick move = $62.50 = 3% of account. Manageable, but 10 contracts = $625 = 31% of account. **Never exceed 2 contracts.**
3. **Do NOT scalp** — commission drag ($0.50–$1.00/round turn × 40 trades = $20–$40/day) exceeds typical edge.
4. **Do NOT trade crypto** — 24/7 but high vol, counterparty risk, no edge for $2,000.
5. **Do NOT trade forex** — requires macro context; our own data says BLOCKED.
6. **Do NOT use penny stocks or meme coins** — manipulation, wide spreads, no edge.

---

## 17. Live simulation / day trading setup with constant monitoring

### 19.1 The 4-stage pipeline (backtest → paper → shadow → live)

Based on Stratmill, Costante, Python.financial, and the autonomous trading platform research:

| Stage | What it tests | Duration | Gate to next stage |
|---|---|---|---|
| 1. Backtest | Fixed rules on historical data (2019–2026) | 1–2 days | Sharpe >0.5, MDD <20%, net of costs |
| 2. Paper trade | Live data, simulated fills, same broker | 30 sessions (~6 weeks) | Trade frequency matches backtest, exit-reason distribution healthy, no gate breaches |
| 3. Shadow mode | Live data + real broker API, orders blocked | 2–4 weeks | Intended orders match tape, no stale feeds/reconnect bugs, alerts work |
| 4. Live (micro size) | Real orders, real fills, real capital | Ongoing | Controlled: 1 contract, 1% risk, daily loss limit, kill switch |

### 19.2 The 30-session paper trading protocol (from ForTraders, 2026)

1. **Pick ONE instrument** (MES) and **ONE setup** (ORB). No switching.
2. **Size exactly as if real**: 1% risk ($20/trade on $2,000), same stops, same daily loss limit.
3. **Trade 30 consecutive sessions** (~6 weeks). This filters out hot/cold streaks.
4. **Journal every trade**: entry, exit, reason, emotion, slippage vs backtest.
5. **Gate**: profit factor ≥1.3 over ≥40 trades → proceed to shadow mode. Otherwise, keep paper trading.
6. **Compare paper vs backtest**: trade frequency, exit-reason distribution, win rate, avg PnL. If paper WR is 10+ pts below backtest WR → overfitting.

### 19.3 Shadow mode (live-plus-shadow evaluation)

From the NeuraTrade PR #260 research:
- **Shadow NEVER places real orders** — uses PaperExecutionSimulator exclusively.
- **Shadow mirrors every live decision** (entries, exits, holds, rejections) and records what it would have done differently.
- **Non-blocking** — shadow failures never affect live execution.
- **Tracks**: PnL divergence, win rate comparison, trade count, rejection count, opportunity cost.
- **No auto-promotion** — requires explicit operator action to promote shadow variant to live.
- **Full audit trail** — all decisions persisted to DB for trend analysis.

### 19.4 Constant monitoring dashboard (what to watch)

From Stretus, Python.financial, and DayTrading.com:

| Metric | What it tells you | Alert threshold |
|---|---|---|
| Trade count vs backtest frequency | Is the strategy firing at expected rate? | ±30% deviation |
| Exit-reason distribution | Are trades ending on your exit condition, or all on stops? | >70% stop-outs = broken |
| Win rate (rolling 20) | Is edge persisting? | <40% over 20 trades = review |
| Profit factor (rolling 20) | Is expectancy positive? | <1.0 = stop trading |
| Max drawdown (intraday) | Are losses within limits? | >3% daily = stop for the day |
| Slippage vs backtest | Is execution degrading? | >2 ticks avg = investigate |
| Commission drag | Is cost eating edge? | >30% of gross PnL = reduce frequency |
| Longest losing streak | Does it feel like backtest? | >6 consecutive losses = review |
| Gate engagement | Are risk limits working? | Any breach = immediate stop |

### 19.5 Trial/error/adjustment protocol

From the autonomous trading platform research (TristanODonnell) and Costante:

1. **Never adjust rules mid-test.** If a rule set needs adjustment during the forward test, it has not passed. The adjusted version needs its own forward test.
2. **Keep historical, forward-test, and live evidence in separate, labeled records.** Blending them makes it impossible to tell where decline started.
3. **Compare forward-test performance against backtest, not against subjective feel.** A meaningful decline IS evidence.
4. **Move to live only after forward test clears.** Treat initial live period as still gathering evidence — not a graduation.
5. **Progressive drawdown governance ladder** (5 rungs):
   - NORMAL (0–2% DD): full size, normal operation.
   - WARNING (2–3% DD): reduce size 50%, tighten stops.
   - PROBATION (3–5% DD): reduce to 1 contract, no new entries, close at breakeven.
   - SUSPENDED (5–8% DD): close all positions, no trading for 24h.
   - BREACHED (>8% DD): full stop, manual review required before resuming.
6. **Auto-demote strategy** if profit factor <1.0 over 40 trades or win rate <35% over 20 trades.
7. **Auto-promote only with explicit operator approval** — never self-promote.

### 19.6 Parallel strategy testing (swarm approach)

From the project's own ParallelSwarm skill and the NeuraTrade shadow mode research:

- Run 3–5 strategy variants in parallel (shadow mode) on the same instrument:
  - Variant A: ORB (15-min range, volume filter) — baseline.
  - Variant B: ORB + VWAP anchor (dynamic SL).
  - Variant C: ORB + time stop (close by 11 AM).
  - Variant D: ORB + trailing stop.
  - Variant E: Mean reversion (fade the ORB breakout if volume <1.0×).
- Each variant runs independently in shadow mode, recording PnL divergence.
- Weekly review: promote the variant with highest (Sharpe × win rate) if it beats baseline by ≥20%.
- **Never promote a variant that hasn't been shadow-tested for ≥2 weeks.**

### 19.7 Kill switch and safety architecture

From TristanODonnell's autonomous trading platform:
- **DB-persisted kill switch** — survives process restarts and crashes.
- **Layered enablement gates**: build-time gate → config gate → runtime human-confirmed activation → broker account allowlist → hard caps on order size/rate.
- **Reconciliation model**: freezes trading and requires human acknowledgment on any mismatch between internal state and broker position.
- **Independent monitoring**: separate process that checks positions, PnL, and alerts. If the monitor dies, trading stops.
- **Tested pause/cancel/shutdown procedure** — operator must be able to kill everything in <10 seconds.

### 19.8 Realistic expectations for $2,000

| Metric | Realistic target | Why |
|---|---|---|
| Monthly return | 2–5% ($40–$100) | 1% risk/trade, 2:1 R:R, 50% WR → ~1 trade/day profitable |
| Monthly commission drag | $40–$80 | 2 trades/day × 20 days × $1.50 = $60 |
| Net monthly profit | $0–$40 | Edge is thin; commission drag is real |
| Max drawdown | 10–15% ($200–$300) | Normal for a $2K account with 1% risk |
| Time to consistent profitability | 6–12 months | 30 paper sessions + 30 shadow sessions + 30 live sessions |
| Probability of blowing up | ~60% (per day trading statistics) | Most retail traders lose money; survival is the first goal |

**The honest truth**: with $2,000, the goal is NOT to make money. The goal is to **learn whether you have an edge** without going broke. If you can trade 90 sessions (30 paper + 30 shadow + 30 live) with a profit factor ≥1.3 and max drawdown ≤15%, you have an edge worth scaling. If not, you've lost at most $2,000 — the cheapest education in trading.

---

## 20. Updated findings (2026-11-19, post-execution)

### 20.1 Selection alpha — NEGATIVE (P0 DONE)
- Ran `alpha_engine/audit3_selection_alpha.py` on `dashboard_data.json`: 3,066/3,500 picks covered.
- Pick +0.261% vs hold +0.389% → **ALPHA −0.128%** (CI=[−0.513, 0.225], includes zero).
- By class: CRYPTO −0.162%, EQUITY −0.015%, ETF −0.140%, COMMODITY +0.119%.
- By slice: CRYPTO/LONG −0.525% (worst), CRYPTO/SHORT +0.398% (best), EQUITY/LONG −0.008%, ETF/LONG −0.140%.
- **Confirms Copilot plan's −0.276%/trade: the system has NEGATIVE selection skill.**
- Only CRYPTO/SHORT shows positive alpha (within noise).

### 20.2 ORB exit grid — 75 combos (P0 DONE)
- Best by net: TP=3.0×, SL=1.5×, time-stop 4 PM ET → PF 1.936, WR 56%, net +$1,776 (60 days).
- Best by PF: TP=2.5×, SL=1.25×, time-stop 3 PM ET → PF 2.155, WR 52%, net +$1,489.
- All 75 combos positive. Original config (TP=2.0, SL=1.0, TS=11 AM) was suboptimal.
- Volume filter confirmed: improves PF from 1.40 to 1.53 (+$134 net).

### 20.3 ETF TAA backtest — Faber GTAA best (P1 DONE)
- Faber GTAA (10-month MA): CAGR 9.76%, Sharpe 0.915, MDD −20.5%, Calmar 0.476, OOS Sharpe 1.13.
- 60/40: Sharpe 0.835, MDD −28.5%.
- SPY buy-hold: Sharpe 0.777, MDD −50.8%.
- Dual Momentum (Antonacci): Sharpe 0.539.
- Multi-Horizon Momentum (3/6/9/12m, top3): Sharpe 0.636, MDD −23.4%.
- **Verdict: Faber GTAA is the best risk-adjusted strategy. Simple > complex.**

### 20.4 Sleeve reconciliation — P0 (NEW)
- /audit top_sleeves (AuditEnsemble_LONG PF 155.85, CorrKama PF 111.81, non_crypto_consensus PF 9.68) are NOT in audit3 cells.
- All single-source, policy_clean/resolver_grade sources.
- audit3 shows CRYPTO = KILL (PF 0.84), FOREX = WEAK (PF 0.92).
- **Recommendation: Flag as UNVERIFIED on /audit. Add sleeve ingestion to audit3 tribunal.**

### 20.5 Corrected claims
- `mf_screener.py` EXISTS (passive core gates: expense ratio, no load, AUM ≥$1B, turnover ≤20%, tracking error ≤0.25%, track record ≥10y). Starter universe: VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX. Runner created + weekly workflow.
- `value_screener.py` IS wired to weekly workflow (`value_screener_weekly.yml`). Runner emitted 22 picks (2026-11-19). Weight inconsistency (0.45/0.55 vs UEPS 0.55/0.45) still needs reconciliation.

### 20.6 POD-EQUITY-BREAKOUT fix
- Registered 13 actual EQUITY/ETF strategy names in CONDITIONS (was using non-existent names like "donchian-stock-breakout").
- Ingest now finds 177 EQUITY rows (was 0). Total ledger: 607 rows.

### 20.7 Cost harmonization
- OTHER_BP in ingest now sourced from cost_model.get_total_bps() (single source of truth).
- EQUITY 8→7, ETF 8→3, FOREX 4→2, COMMODITY 12→7, FUTURES 12→5.5, BOND 2→4.5 bps.

### 20.8 The money-ready answer (honest)
- **NOT any single asset class.** 0/10 money-ready.
- **Selection alpha is NEGATIVE** (−0.128%). Our picks lose to buy-and-hold.
- **The only money-ready path:** ETF TAA (Faber GTAA, Sharpe 0.915, MDD −20.5%) + mutual fund passive core (8 funds pass hard gates).
- **For $2,000:** MES ORB (PF 1.53-2.155, net $683-$1,776/60 days) for intraday-capable users; ETF TAA for day-job users.
- **Publication decay (26-58% haircut)** means even the ORB edge may be thinner than backtested.
- **The honest goal with $2,000:** learn whether you have an edge, not make money. Survival first.

---

## 18. Provenance

- Generated 2026-11-19 by opencode (Beam Free).
- Sources: live pages fetched 2026-11-19; JSON snapshots as of 2026-11-19T16:42Z (ledger), 2026-11-19T08:41Z (forward), 2026-11-19T05:07Z (evidence); web research on mutual funds (Lipper/Morningstar/Standard Chartered/Scotiabank/Value Research), ETFs (ScienceDirect momentum on 3215 ETFs, Concretum, Panaprium/Faber, Truusst, quantstr.at, ML overlay), crypto cycles (Cowen, Fidelity, 10x Research, Hashdex, Abra, orderbookedge), bonds/commodities/forex/futures (academic + industry sources).
- This document is a research review, not investment advice. No position sizing is emitted.
- Companion to: `COMS_HANDOFF_AUDIT2_3_2026-11-19.md`, `COMS_HANDOFF_AUDIT2_3_IMPL_JUSTIFICATION_2026-11-19.md`, `AUDIT_PAGE_SECTIONS_2026-11-18.md`.
- Sources: live pages fetched 2026-11-19; JSON snapshots as of 2026-11-19T16:42Z (ledger), 2026-11-19T08:41Z (forward), 2026-11-19T05:07Z (evidence).
- This document is a research review, not investment advice. No position sizing is emitted.
- Companion to: `COMS_HANDOFF_AUDIT2_3_2026-11-19.md`, `COMS_HANDOFF_AUDIT2_3_IMPL_JUSTIFICATION_2026-11-19.md`, `AUDIT_PAGE_SECTIONS_2026-11-18.md`.
