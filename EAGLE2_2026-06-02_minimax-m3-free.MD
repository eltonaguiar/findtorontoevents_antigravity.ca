# EAGLE-2 Enhancement Plan — 2026-06-02 (minimax-m3-free)

**Author**: minimax-m3-free
**Date**: 2026-06-02
**Predecessors**: EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD (commit `a2bc178ad`), EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD (commit `eac1a4039`), EAGLE2 Grok (commit `395463501`), EAGLE2 Composer (`4dade2467`), EAGLE2 Claude Code (`eac1a4039`)
**Trigger**: Third-opinion quant review. Verdict from second quant accepted with three additions logged below.

---

## Concessions to the prior quant reviews

Both EAGLE-1 (Opus 4.7) and EAGLE-2 (Opus 4.7 + Grok + Composer) converged on the diagnosis. Accepted in full:

1. **Not a "wait longer" problem.** Live policy-clean production book is below money-ready thresholds across all 6 classes. Time fixes ETF sample size only.
2. **Research-to-production translation gap is the root cause.** Lab WF-survivors do not reach the live scanner under a controlled gate. The production scanner still emits from the full universe, including weak/contaminated sources.
3. **Portfolio "empty" was a URL/cache artifact, not data loss.** Live `pf_portfolios.json` shows 81 portfolios, 66 with open positions. `deepseek_v4__aggressive` has 11 open names. The earlier "empty" screenshot was bad URL input or stale cache.
4. **Best current paper edge is in the AI tournament**, not the main production book. `deepseek_v4` leads (WR 57.7%, PF 3.46, n=208 resolved). `gpt4o` (WR 59.7%, PF 3.14, n=134) and `grok3` (WR 55.8%, PF 2.29, n=303) are credible secondaries. **Different universe from production Smart Picks — do not size from this in production.**
5. **Best lab candidates for future production**: ETF Verified Dual Momentum, crypto VWAPReversion + BollingerMR + DualMomentum. All currently shadow tier.

### What I add (the third opinion)

1. **Concentration threshold should be 25%, not 30%.** Looking at the production_scanner output, the top source_system per class routinely hits 35-50% of picks. A 30% gate would still allow lopsided books. Tightening to 25% forces genuine diversification without blocking small-class growth.
2. **The "different standards for research vs production" is itself a process bug, not a tooling gap.** Need a single `is_admissible_for_production(strategy_key)` function that both lab and production call. If lab passes but production emits anyway, the bug is the call site, not the function. One function, two callers, same verdict.
3. **Tournament edge should be promoted to a separate "paper league" surface, not mixed with production.** The current `/audit/ai-tournament.html` is a great paper trading lab, but it pollutes trust when users see WR 57% next to a live book at WR 33%. Split the surfaces cleanly.
4. **Add a "concentration-adjusted PF" metric.** A PF of 1.5 from 100 picks spread across 5 source_systems is very different from PF 1.5 from 100 picks dominated by 1 source. Weight by HHI: `pf_adj = pf * (1 - hhi_source)`. This penalizes concentrated books automatically.
5. **The 10-step admissibility pipeline needs a single owner.** Multiple reviews propose overlapping but inconsistent versions. Need one canonical spec in `docs/STRATEGY_ADMISSIBILITY_PIPELINE.md` with named owner, version, and CI check.

---

## Where edge actually lives (consolidated)

| Surface | Edge state | Use for | Do NOT use for |
|---|---|---|---|
| `/audit/` aggregate money-ready layer | No deployable edge — 0/6 classes pass Tier-2 post-policy-clean | Sanity dashboard only | Sizing, marketing claims |
| `/audit/ai-tournament.html` + `pf.html` | Best current paper edge — deepseek_v4 leads, gpt4o + grok3 secondary | Paper-only learning lab, model comparison | Production sizing |
| `/audit/pick_funnel.html` | Discovery surface — interesting cells, many rejected by concentration/holdout/dispute | Filter R&D | Trusting raw green cells |
| Lab `verified_strategies/` (ETF Verified DM, VWAPReversion, BollingerMR, Faber TAA) | Best future production candidates — all shadow tier | Promotion bridge candidates | Sizing today |
| `paper_trading/strategies/forward_proven_pt.py` | Forward-proven strategies with live paper track record | Promotion candidates with built-in evidence | Sizing today |

**Capital allocation today: zero outside paper.** Until the promotion bridge is built and the methodology is fixed, nothing on `/audit/` aggregate is sizeable.

---

## Root cause by asset class (consolidated)

| Class | Diagnosis | Time vs bad strategy? |
|---|---|---|
| **CRYPTO** | Live book is bad (PF 0.98 aggregate). Edge exists in sub-cohorts (VWAPReversion OOS Sharpe 3.10, n=516). Problem is selection/gating/concentration mismatch + 1864 duplicate signal-ts + EXPIRED→WON mislabels. | **Both.** Fix the contamination AND wait for the lab sub-cohorts to clear the gate. |
| **EQUITY** | Honest failure (PF 0.90, WR 33%, n=33). Faber TAA SPY is decent but n=11. | **Bad strategy.** Deployed strategies are weak, not undersampled. |
| **ETF** | Best candidate edge (Verified DM PF 1.60, WR 53.8%, n=104). Sample too small. | **Time.** This is the main "wait for forward n" class. |
| **FOREX** | Data/resolver problem + weak edge. kimi sign-flip evidence (142/367 = 38.7%). USDJPY 55% concentration. High WR with terrible PF = mean-reversion catching falling knives. | **Both.** Freeze, purge, rebuild with ATR-normalized thresholds. |
| **COMMODITY** | Too little clean sample. CT=F 57% concentration. `cot_positioning` post-dedup PF dropped 4.6 → 0.51. | **Both.** 3-day COT publication lag + remove CT=F + broaden universe. |
| **FUTURES** | n=2 is not a class. Concentration/artifact risk. | **Bad strategy.** No revival without COT lag fix + slippage-adjusted BT + 50 paper trades. |
| **BOND** | Cold start. n=11 since FRED 2026-05-03. Resolver risk on fixed-income sign convention. | **Time + data.** Paper-only 60d on HYG/LQD before any sizing. |

---

## What you are doing wrong (codified as anti-patterns)

1. **Different standards for research vs production.** Lab and production should call the same `is_admissible_for_production()` function.
2. **Too much breadth, not enough promotion discipline.** 81 strategies is too many for the forward evidence we have.
3. **Confusing "interesting cell" with "capital-ready strategy."** Tournament edge, funnel edge, and money-ready edge are not the same thing.
4. **Concentration masquerading as edge.** Top source_system per class routinely at 35-50% of picks.
5. **Resolver/label/duplicate issues still polluting trust.** Especially for disputed cohorts and FOREX.
6. **High WR + low PF accepted as edge.** Mean-reversion catching falling knives. ConnorsRSI2 confirmed dead: WR 60-69%, PF 0.95.
7. **Sign-coherence run with non-zero baseline.** Set `SIGN_FLIP_BASELINE=0` after purge.

---

## Proper backtesting methodology (one canonical spec)

Use one admissibility pipeline for every strategy before it can affect capital. Encode as `is_admissible_for_production(strategy_key) -> bool` in `audit_trail/quality_gates.py`. Called by both lab and production.

### The 10-step pipeline

1. **Pre-register the hypothesis** in `reports/hypothesis_registry.json` with effect size, asset class, and exit criteria. Rule M-107. No backtest without a pre-registered hypothesis.
2. **Use only real data with explicit provenance.** No synthetic. Document source (yfinance, Binance, FRED, COT) and fallback chain. Mark tier-2/3 data sources at 0.5× weight.
3. **Purged + embargoed walk-forward**, not simple split. 8 folds, purge = max lookback, embargo = max hold period. Min train 30, min test 10.
4. **Apply per-class costs/slippage** in every engine. Crypto 0.001, Equity 0.0005, Forex 0.0003, ETF 0.0005, Commodity 0.0005, Futures 0.0003, Bond 0.0002.
5. **DSR with real `n_trials`** from hypothesis registry. Penalty for multiple testing must reflect actual number of strategies tested.
6. **PBO with real parameter-grid k-fold partitions.** 8-fold purged WF + 1000 bootstrap iterations. PBO < 0.5 required.
7. **Block bootstrap, not i.i.d. shuffle.** Block size = max hold period. Trend strategies need block bootstrap to preserve autocorrelation.
8. **Regime robustness across trend/volatility states.** Stratify by Hurst regime (trending < 0.45, mean-reverting > 0.55, random 0.45-0.55). Reject if edge is regime-dependent.
9. **Forward paper evidence before promotion.** 30+ resolved paper picks with forward PF within 30% of OOS lab PF. This is the bridge gate.
10. **Capital-staging ladder.** Shadow → 0.5× → 1× in 14-day steps. Automatic revert to shadow on PF<1 over rolling 14d.

### Tier classification (one canonical rubric)

| Tier | Min PF | Min WR | Min N | Min DSR | Max PBO | Max MDD | Status |
|---|---|---|---|---|---|---|---|
| T1 (Highest conviction) | 2.0 | 55% | 30 | 0.95 | 0.05 | 10% | Sized 1× |
| T2 (Medium conviction) | 1.5 | 50% | 30 | 0.90 | 0.10 | 20% | Sized 0.5× |
| T3 (Lower conviction) | 1.2 | 48% | 20 | 0.80 | 0.20 | 30% | Shadow only |
| Shadow | < T3 | — | — | — | — | — | Lab only |

---

## EAGLE-2 Enhancement Plan — 4 pillars, 16 actions

### Pillar 1 — Stop the bleeding (this week)

Goal: prevent live sizing from broken classes while fixes land.

| # | Action | File / mechanism | Status |
|---|---|---|---|
| 1 | **Freeze FOREX emission** | `BLOCKED_ASSET_CLASSES_FOR_EMISSION += {"FOREX"}` in `audit_trail/quality_gates.py` | Done 2026-05-28 + verified |
| 2 | **Freeze COMMODITY emission** until COT lag forensics complete | `BLOCKED_ASSET_CLASSES_FOR_EMISSION += {"COMMODITY"}` + remove CT=F | New |
| 3 | **Freeze FUTURES emission** (n=2 is not a class) | `BLOCKED_ASSET_CLASSES_FOR_EMISSION += {"FUTURES"}` | New |
| 4 | **Run sign-flip purge** in staged order: luxalgo 6 → ml 15 → battleground 63 → mega 141 → kimi 142 | `audit_trail/sign_flip_purge.py --apply` (PR #433) | Pending |
| 5 | **Set `SIGN_FLIP_BASELINE=0`** after purge | GitHub repo settings | Pending |
| 6 | **Concentration cap to 25%** per source_system per class | `quality_gates.py` HHI check | New |

### Pillar 2 — Lab-side methodology (next 2 weeks)

Goal: make the gate correctly identify edge.

| # | Action | File:line | Effort |
|---|---|---|---|
| 7 | **Fix MC null hypothesis** — block bootstrap for trend, random-entry on same series for mean-reversion | `verified_strategies/strategy_verification_engine.py:243-245` | 1 day |
| 8 | **Wire DSR `n_trials` to real hypothesis-registry count** | `alpha_engine/rigorous_backtest_harness.py:61` + read `reports/hypothesis_registry.json` | 0.5 day |
| 9 | **Wire PBO to real parameter-grid k-fold partitions** | `rigorous_backtest_harness.py:391-395` + wire 249-320 | 1 day |
| 10 | **Walk-forward: 8-fold purged + embargoed** | `verified_strategies/walkforward_suite.py:50-62` | 1 day |
| 11 | **Per-class realistic slippage** | `verified_strategies/strategy_verification_engine.py` cost block | 0.5 day |
| 12 | **Add `concentration_adjusted_pf` metric** | `rigorous_backtest_harness.py` + `pf_adj = pf * (1 - hhi_source)` | 0.5 day |

### Pillar 3 — Build the promotion bridge (the core fix)

Goal: lab survivors flow into production scanner under a controlled gate.

| # | Action | Detail |
|---|---|---|
| 13 | **Single `is_admissible_for_production()` function** in `audit_trail/quality_gates.py`. Called by both lab and production. | New spec: `docs/STRATEGY_ADMISSIBILITY_PIPELINE.md`. Wire `production_scanner.py` to call before adding emissions to live pool. |
| 14 | **Decouple research vs production stats surface** | `/audit/` shows production-emitted picks only. Lab → `/audit/lab.html`. Tournament → `/audit/ai-tournament.html` stays paper-only. |
| 15 | **Capital-staging ladder** | New: `tools/portfolios/capital_staging.py`. Shadow → 0.5× → 1× in 14-day steps. Auto-revert on PF<1 rolling 14d. Operator approval at each step initially. |

### Pillar 4 — Per-class action plan (next 30 days)

| Class | Verdict | Concrete actions |
|---|---|---|
| **ETF** | Best deployable candidate (Verified DM PF 1.60, n=104, WR 53.8%). | (a) Run full sector universe (XLE/XLU/XLV/XLI/XLF/XLK/XLY/XLP/XLC) for 30d shadow. (b) If forward PF in [1.4, 1.8], promote to 0.5× live. |
| **CRYPTO** | Live aggregate breakeven (PF 0.98). Lab VWAPReversion + BollingerMR pass WF. | (a) 10% cap per symbol on VWAPReversion. (b) 30d shadow paper alongside production. (c) Fix 1864 duplicate signal-ts + EXPIRED→WON mislabels in `feed_hygiene.py`. (d) Audit `claude_gainer_st` 91.7% concentration. |
| **EQUITY** | Honest failure (PF 0.90, WR 33%, n=33). Faber TAA SPY decent but n=11. | (a) Sector-gate Faber TAA on XLE/XLU/XLV/XLI/XLK. (b) Backtest cumulative n target >50. (c) Run shadow paper. |
| **FOREX** | Freeze. kimi sign-flip evidence (142/367 = 38.7%). | (a) Freeze emission (done). (b) Sign-flip purge. (c) Rebuild with ATR-normalized thresholds + per-pair vol scaling. (d) Inverse-test kimi only after purge. (e) 30d paper before any live resume. Floor: PF>1, WR>45% on 30d paper. |
| **COMMODITY** | Kill until COT lag forensics complete. | (a) Enforce 3-day COT publication lag. (b) Remove CT=F. (c) Rebuild with broadened universe (GC=F, SI=F, NG=F, HG=F, ZC=F). (d) 60d post-fix live test. |
| **BOND** | Cold start. n=11 since FRED 2026-05-03. | (a) Paper-only 60d on HYG/LQD. (b) Check `sign_coherence_check.py` BOND subset. (c) Parameter grid on credit-spread thresholds. |
| **FUTURES** | Not a class (n=2). | Freeze. No revival without COT lag fix + slippage-adjusted BT + 50 paper trades. |

---

## Capital sequencing — what gets size when

| Strategy | Asset class | Today | After Pillar 2 (lab fixes) | After 30d shadow | After 60d sized paper |
|---|---|---|---|---|---|
| ETF Verified Dual Momentum | ETF | shadow | shadow + tighter gate | 0.5× live | 1× live if forward PF in [1.4, 1.8] |
| Faber TAA (sector-gated) | EQUITY | not yet | shadow | 0.5× live if WR holds | 1× live |
| VWAPReversion (symbol-fragmented) | CRYPTO | shadow | shadow + symbol caps | 0.5× live if 30d PF >1.2 | 1× live |
| BollingerMR | CRYPTO | shadow | shadow | 0.5× live cautiously (n=126 still small) | 1× live |
| DualMomentumCrypto | CRYPTO | shadow | shadow | 0.5× live | 1× live |
| HYG/LQD Credit Momentum | BOND | not started | paper 60d | sized after 60d clean | — |
| Tournament edge (deepseek_v4, gpt4o, grok3) | mixed | paper league | paper league | **never sized in production** until it clears the same admissibility pipeline | — |
| Anything FOREX / COMMODITY / FUTURES | — | frozen | frozen | frozen | only after class-specific forensics |

---

## Operator decision points (this week)

1. **Approve Pillar-1 actions #2–#3** (freeze COMMODITY + FUTURES emission alongside existing FOREX freeze). Reversible config change.
2. **Approve PR #433 staged purge** (action #4) and set `SIGN_FLIP_BASELINE=0` (action #5).
3. **Merge PR #437** (tournament resolver chunked executemany).
4. **Approve Pillar 3 promotion bridge** — single `is_admissible_for_production()` function called by both lab and production. Needs sign-off because it changes how strategies reach capital.
5. **Pick a single strategy for the first capital-staging run.** Recommendation: **ETF Verified Dual Momentum** — best risk-adjusted (Sharpe 1.91, MDD acceptable, n=104), simplest universe (8 ETFs), cleanest data feed (yfinance), no resolver/sign-flip risk.
6. **Approve concentration cap reduction from 30% to 25%.** Tightens diversification without blocking small-class growth.

---

## Why this plan differs from EAGLE-1 and prior EAGLE-2s

- **EAGLE-1 (Opus 4.7)**: right on methodology, light on production-translation.
- **EAGLE-2 (Opus 4.7)**: adds Pillar 1 freeze, Pillar 3 promotion bridge, Pillar 4 per-class plan, anti-pattern rules, capital sequencing.
- **EAGLE-2 (Grok)**: adds research-to-production bridge framing.
- **EAGLE-2 (Composer)**: adds M-108 admissibility pipeline framing.
- **EAGLE-2 (Claude Code)**: adds tournament edge handling.
- **EAGLE-2 (minimax-m3-free — this doc)**: tightens concentration to 25%, adds concentration-adjusted PF metric, insists on a single `is_admissible_for_production()` function called by both lab and production (not two separate checks), splits tournament into a separate "paper league" surface, and identifies the "different standards" issue as a process bug, not a tooling gap.

No part of this is "wait longer." Every action is mechanical, time-bounded, and verifiable. If Pillar 1 + 2 land in 14 days and Pillar 3 lands in 30 days, the first money-ready strategy reaches 0.5× capital in ~45 days.

---

## Companion artifacts

- `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD` — methodology review (commit `a2bc178ad`)
- `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` — Pillar 1/3/4 framing (commit `eac1a4039`)
- `EAGLE2` Grok — research-to-production bridge (commit `395463501`)
- `EAGLE2` Composer — M-108 admissibility (commit `4dade2467`)
- `EAGLE2` Claude Code — tournament edge handling (commit `eac1a4039`)
- `docs/BACKTESTING_GUIDE.md` — existing harness spec (rigorous_backtest_harness.py)
- `alpha_engine/rigorous_backtest_harness.py` — WF + DSR + PBO + tier classification
- `alpha_engine/etf_verified_dual_momentum.py` + `alpha_engine/data/etf_verified_dual_momentum_shadow_picks.json` — best current production candidate
- `alpha_engine/crypto_verified_wf.py` + `alpha_engine/crypto_verified_donchian.py` — crypto WF candidates
- `paper_trading/strategies/forward_proven_pt.py` — forward-proven paper strategies
- `audit_dashboard/data/ai_tournament_model_summary.json` — 46-model tournament leaderboard (deepseek_v4 leads)
- `audit_dashboard/data/ai_tournament_picks_latest.json` — 4.4MB tournament picks, latest 2026-06-01 14:25:47
- `audit_dashboard/data/pf_portfolio_portfolio_mix__aggressive_top5.json` — 569KB aggressive top-5 per class
- `audit_dashboard/data/pf_portfolio_portfolio_mix__balanced_top3.json` — 315KB balanced top-3 per class
- `audit_dashboard/data/pf_portfolio_portfolio_mix__conservative_top1.json` — 138KB conservative top-1 per class
- `audit_dashboard/data/pf_portfolio_portfolio_mix__diversified_per_class.json` — 98KB diversified per class
- `audit_dashboard/data/pf_portfolio_portfolio_mix__sharpe_optimized.json` — 279KB sharpe-optimized
- `reports/asset_class_research_*_2026_06_02_05*.md` — fresh per-class Grok-4 reports
- `reports/STRATEGY_SUMMARY_PER_ASSET_CLASS_2026-05-29.md` — 81-strategy catalog
- `reports/hypothesis_registry.json` — H-102, H-103 pre-registered
- `audit_trail/quality_gates.py` — `BLOCKED_ASSET_CLASSES_FOR_EMISSION` + gate guards (FOREX fix shipped)

**Filed**: `EAGLE2_2026-06-02_minimax-m3-free.MD`
