# Money-Ready Per-Asset-Class Synthesis — 2026-05-31

**Author:** claude-opus-4.8 (`/money-maker-readyv2`, 6-agent investigation fleet)
**Surfaces in scope:** `/audit`, `/audit/pick_funnel.html`, `/audit/ai-tournament.html`, `/audit/ai_leaderboard.html`, `/audit/hyrotrader`, and `ejaguiar1_stocks` / `ejaguiar1_backtests`.
**Canonical sources:** `pf_registry.json` + `money_ready_verdict.json` (gen 2026-05-30T23:05Z), `tournament_picks` (live DB), `*/data/closed_picks.json`, `anti_overfit_audit.json`, `cot_*` MC files, committed `reports/backtest_*.md`.

---

## THE ONE-PARAGRAPH ANSWER

We are **0/8 classes money-ready live**, but the blocker is **not** a shortage of strategies and **not** insufficient Monte-Carlo. Validation (DSR/PBO/SPA) already runs **hourly+daily** and is correctly diagnosing performance. We **already have proven *backtest* edges** in ETF, EQUITY, COMMODITY, BOND (PF 1.5–2.1) — they just don't accumulate live because of **plumbing failures** (dead/dormant emitters, a silently-failing resolver, broken workflows) and **data-integrity bugs** (asset-class mislabels, stale dashboards, over-emission). The single highest-ROI program is: **fix the pipes + wire the proven edges + fix the mislabels** — in that order. The lone exception is **CRYPTO**, which has ample n and clean validation but a genuinely **negative** edge → it is the only class that needs real strategy research (regime-conditioning + a short leg).

**Do we need more Monte-Carlo / more often?** No. MC is the *last* gate (Step 7) and only exists for COT/cotton today; expanding it is wasted compute until classes clear the n≥50 floor. Adding MC changes nothing for 8/9 classes.

---

## PER-CLASS SCORECARD

| Class | Live verdict | Best proven edge (mostly backtest) | Wired? | The real gap | Fastest bridge |
|---|---|---|---|---|---|
| **ETF** | INSUFF n=4 | `etf_cross_sectional_momentum` PF **2.05** / WR 70% / Sharpe 0.97 / MDD 16%, slippage-robust | ✅ wired + **enabled** | live n only | **Accumulate → first Tier-2.** |
| **BOND** | INSUFF n=0 | `bond_connors_rsi2` PF 1.34 / Sharpe 2.22 / n=201/21y | ✅ wired + emitting | **emitter workflow red 5 days → 0 resolved** | Fix `alpha-engine-bond.yml`. |
| **EQUITY** | INSUFF n=39† | `vt_pattern_sweep` PF 1.48/n=245; `trend_strength_200ma_adx` PF 2.06 | dormant / orphan | **P0: ~90% picks mistagged crypto** | Fix mistag → un-dormant vt_pattern_sweep. |
| **COMMODITY** | INSUFF n=9 | `gold_safe_haven` PF 1.98/n=61 (unreplicated live) | ✅ wired | **PF 1.81 is 2-trade outlier + SHIB mislabel; 78% gold** | Accrue n≥50 clean; de-concentrate; fix mislabel. |
| **FOREX** | LOSER n=28 PF 0.04 | `dxy_trend_filter` PF 1.63/n=995 (unreplicated live) | ✅ wired | **active whitelist = a confirmed loser; regime blowups** | Swap whitelist → dxy_trend_filter; hard-block regime_*. |
| **CRYPTO** | NOT_READY n=327 PF 0.89 | `ensemble` conf≥0.7 PF 1.95 (n=76, regime-decayed) | ✅ | **genuinely negative edge; regime-extinct filters** | Real research: regime layer + short leg + block-bootstrap MC. |
| **FUTURES** | FAIL n=12 PF 0.54 | TSMOM backtest PF 1.71 (commodity-overlap) | scanner emits noise | zombie / single-engine | **Merge into COMMODITY.** |
| **Tournament** | forward-test | cursor_agent WR 66% PF 2.35; llama4_scout WR 61% PF 2.26 (healthy R:R 1.6) | live | **resolver silently failing; 1,289 picks overdue** | Fix resolver → 3 models hit n≥100 instantly. |

† EQUITY n=39 is itself corrupted by the mislabel; real EQUITY n≈20.

---

## ROOT-CAUSE BUCKETS (where the gap actually lives)

### 1. Broken / stalled pipelines (highest ROI — fixes unlock existing edge)
- **Tournament resolver silently failing** (INCIDENT #43): workflows return "success" in <50s, resolve ~nothing; 1,289 short-TF picks overdue >5d; throughput 1,725/day (05-24) → 0. Fixing it pushes deepseek_v4/cursor_agent/llama4_scout each past n≥100 from existing backlog.
- **BOND emitter workflow red 5 days** (INCIDENT #3): `alpha-engine-bond.yml` failing → 0 resolved bonds despite 5 open picks + a wired PF-1.34 strategy.
- **Silent stale validators** (INCIDENT #45): `anti_overfit_audit.json` 20d stale, `walkforward.by_class` 6wk empty — both behind `|| echo non-fatal`. The per-strategy DSR table & OOS detector run on stale data.

### 2. Proven edges not emitting (wire / un-dormant — ENHANCEMENT #54)
- ETF `etf_cross_sectional_momentum` (PF 2.05) — enabled, just young.
- EQUITY `vt_pattern_sweep` (PF 1.48, n=245) — **wired but 0 live emissions**; sibling `vt_thematic_etf_momentum` (PF 2.14) `.py` missing on disk (recover from git).
- EQUITY `trend_strength_200ma_adx` (PF 2.06 Tier-1) — orphan, no emitter.
- COMMODITY `diwali_gold` (PF 1.98), `commodity_seasonal` (PF 1.76) — orphan/partial.
- EQUITY `PEAD` (62% OOS WR) — wired but `PEAD_EQUITY_ENABLED=0`; flip to live-shadow (near-zero effort).

### 3. Data-integrity bugs that make verdicts lie
- **~90% EQUITY picks mistagged crypto** (P0 INCIDENT #7).
- **SHIBUSDT mislabeled COMMODITY** inflating commodity PF (INCIDENT #6, COMMODITIES).
- **Tournament dashboard JSON is a stale 1/4 subset** — 1,037 published vs 4,419 in DB (INCIDENT #44).
- **`cot_positioning` TIER-1 headline falsified** — 7.33× over-emission; deduped n=6, cum PnL −$6,547 (INCIDENT #7, COMMODITIES).
- **DISPUTED CRYPTO banner 6d stale** (INCIDENT #5).
- **`dashboard_data.json` 52h stale** (INCIDENT #33).

### 4. Genuine strategy gaps (real research needed — only here)
- **CRYPTO**: n=327, full validation battery, **fails on merits** (PF 0.89, DSR 0, PBO 0.65 fail, SPA p=0.87). Needs regime-conditioning + a SHORT leg + diversification off BTC-only scalps. The `ensemble` below-200MA edge is **regime-extinct** (0/162 below-200 signals in last 30d).
- **FOREX**: every n≥20 cohort loses; the active whitelist (`cta_cross_asset_tsmom`) is a confirmed loser. Needs `dxy_trend_filter` live-reproduction or a genuinely new directional strategy.

---

## R:R / TP-SL OPTIMIZATION FINDINGS (the user's specific question)
- Winsorization counterfactual is **misleading** — always price-path backtest (memory saved). Tightening SL **collapses** PF on real BTC 1m paths (whipsaw).
- **Loosening** the stop to ~2% lifts both BTC scalps over Tier-2 on real paths: `crypto_liquidity_wick_reversal_v1` PF 1.50→**1.999**, `atr_percentile_gate` 1.10→**1.865**. But both are single-symbol BTC scalps, n<100 — leads, not sleeves. (ENHANCEMENT #4/#5)
- Tournament R:R is healthy (median reward:risk 1.61, avgWin 3.75% vs avgLoss 3.28%) → the high WRs are genuine positive expectancy, not hit-rate artifacts.

---

## RECOMMENDED PROGRAM (ranked by edge-per-effort)

1. **Fix the tournament resolver** (P1) → 3 models reach n≥100 from existing backlog. Then compute net-of-cost PF; paper-trade EQUITY/COMMODITY/ETF picks (exclude FOREX/BOND where the models lose).
2. **Fix the BOND emitter workflow** (P1) → start accruing BOND n on a wired PF-1.34 sleeve.
3. **Fix the EQUITY crypto-mistag P0** → every EQUITY number becomes trustworthy; then un-dormant `vt_pattern_sweep` (expand universe to ~40-50 names for n≥30 in 60-90d).
4. **Push ETF**: confirm gate ON (done — defaults ON), accumulate → **most likely first Tier-2 class**.
5. **Swap the FOREX whitelist** to `dxy_trend_filter`; hard-block `regime_accumulation`/`regime_terminal`.
6. **CRYPTO research** (longer): regime-conditioned `ensemble` + short leg + block-bootstrap MC; OOS-validate genome `mega_mutation_MACD_RSI`.
7. **Repoint the tournament dashboard at the DB**; refresh stale validators; fix mislabels.

**Numeric money-ready bar (per class):** n≥50 (gate `MIN_N_CLASS=50`) clean policy-clean, PF_CI_lo>1.5, WR>50%, MDD<20%, single-symbol concentration <60%, passing (DSR or SPA) and (PBO or SPA); for sizing add a block-bootstrap MC with RoR<5% at $10k and a 4-week live confirmation.

---
*All findings tracked in `ejaguiar1_stocks` INCIDENT_*/ENHANCEMENT_* → `findtorontoevents.ca/audit/incidents.html`. Investigation was read-only; no production strategy code modified.*
