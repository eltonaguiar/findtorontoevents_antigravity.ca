# Deep Dive — FOREX (2026-05-31)

Trigger: CLAUDE.md Goal #1 — FOREX FAIL on policy-clean-net cohort. PF=0.037, WR=28.57%, n=28, MDD=81%, expectancy=-4.5% per pick. Worse than the 2026-05-25 snapshot in CLAUDE.md (which cited PF 0.55 / WR 40% / n=53). The class is degrading, not improving.

Sources of truth used:
- `audit_dashboard/data/pf_registry.json` → `by_asset_class_policy_clean_net.FOREX` and `by_asset_class_strategy_policy_clean_net` rows where `asset_class=FOREX`.
- `audit_dashboard/data/money_ready_verdict.json` (generated 2026-05-30T23:05:42Z) → `classes.FOREX`.
- `audit_dashboard/data/pick_summary_stats_2w.json` and `pick_summary_stats_48h.json` for recency panels (with leakage caveats applied).
- `audit_dashboard/data/dashboard_data.json` → `asset_class_health.FOREX = {}` (empty; do NOT cite stale values from prior runs).

## Current State

| Cohort | n | WR | PF | Expectancy | MDD | Notes |
|---|---|---|---|---|---|---|
| policy_clean_net (verdict cohort) | 28 | 28.57% | 0.037 | -4.50% / pick | 81.05% | Total PnL -1.247 (sum of pct). CVaR95 = -50.84. |
| raw (no policy filter) | 81 | 34.57% | 0.491 | n/a | n/a | Pre-policy cohort. Gross profit 0.94 vs gross loss 1.91. |
| 14d recency (`pick_summary_stats_2w` `by_class`) | 6028 dec. | 83.54% raw / 83.43% shrunk | **0.103** | -5.80% mean | n/a | **WR↔PF inconsistent → leakage**. Caveats: `dup_groups=58`, `EXPIRED_pos_pnl_share=76%_likely_mislabeled_WON`. Top src `alpha_engine_unified` 54.2%. Top sym `NZDUSD=X` 10.5%. |
| 48h recency | 15 closed | 53.33% (51.43% shrunk) | 1.243 | +0.054% mean | n/a | Caveats: `dup_groups=2`, `single_source_concentration=100%_via_AlphaEngine`. |

Verdict: **INSUFFICIENT_DATA** (n=28 below T2 floor of n>=100) AND every individual gate fails (`n_ok=false`, `wr_ok=false`, `pf_ok=false`, `dsr_ok=false`, `mdd_ok=false`, `cvar_ok=false`, `expectancy_ok=false`). Concentration: top_source = `multi_asset_scanner` at 39.29%; top_symbol = `USDJPY=X` at 28.57% — both under the policy 50% cap so `concentration_capped=false`, but the 48h cohort shows 100% single-source dependence on `AlphaEngine`.

## Per-Source Autopsy (policy-clean-net cohort, n=28 closed picks)

Source-level granularity is not directly broken out in `pf_registry` for FOREX; we use the strategy rows as proxy (each strategy maps cleanly to a single emitting subsystem in the FOREX class). Source concentration is documented via `money_ready_verdict.top_source_share`.

| Source (strategy) | n | wins | losses | WR | PF | gross_p | gross_l |
|---|---|---|---|---|---|---|---|
| multi_asset_scanner (TOP, 39.29% share) | 11 | 1 | 10 | 9.09% | 0.209 | 0.0061 | 0.0289 |
| cta_replicator | 6 | 2 | 4 | 33.33% | 0.498 | 0.0058 | 0.0117 |
| regime_terminal | 4 | 2 | 2 | 50.00% | **0.038** | 0.0221 | 0.5819 |
| multi_asset_copytrader | 3 | 2 | 1 | 66.67% | **2.012** | 0.0062 | 0.0031 |
| regime_accumulation | 2 | 0 | 2 | 0% | 0.000 | 0 | 0.5969 |
| alpha_engine | 1 | 1 | 0 | 100% | undef | 0.0073 | 0 |
| regime_mild_bear | 1 | 0 | 1 | 0% | 0 | 0 | 0.0722 |

Symbol-level concentration top rows:
- `multi_asset_scanner / USDJPY` n=4 WR=25% PF=2.50 (one large winner masks loss frequency)
- `alpha_engine / AUDUSD` n=3 WR=33% PF=0.009 (one win 0.0045 vs losses summing 0.5227 → catastrophic risk per trade)
- `cta_replicator / AUDUSD` n=3 WR=33% PF=0.55
- `multi_asset_copytrader / CADJPY` n=3 WR=66.67% PF=2.27 (only consistently winning combo)
- `multi_asset_scanner / NZDUSD` n=3 WR=0% PF=0
- `multi_asset_copytrader / NZDUSD` n=3 WR=0% PF=0

## Strategy Breakdown — concentration flags

- `multi_asset_scanner` is the dominant emitter (11/28 = 39.3% of cohort). It is the WORST performer (WR 9%, PF 0.21). This single strategy explains the asset-class verdict.
- `regime_terminal` (n=4) and `regime_accumulation` (n=2) account for the MDD blowups — combined gross loss ≈ 1.18 (out of cohort total gross loss 1.29) on just 6 picks. **Two regime_* picks alone wipe out the rest of the book.**
- `multi_asset_copytrader` (n=3) is the only profitable strategy in the cohort but too low n to gate on.
- `single_source_pct` flag — at the asset-class level 39.3% (below 50% policy cap), but at the recency 48h panel it is **100% AlphaEngine** — the FOREX class is structurally a single-source class right now.
- 14d shrunk WR 83.4% with PF 0.103 is mathematically incompatible with honest labels; this is the EXPIRED→WON resolver mislabel pathology (76% positive-PnL EXPIRED rows) flagged in CLAUDE.md for CRYPTO recently re-appearing here.

## What Is Failing — root causes

1. **`multi_asset_scanner` FOREX picks are net-losing junk.** WR 9% over n=11 with no winning symbol. This strategy should be source-suspended on FOREX immediately and routed through `STRATEGY_INVESTIGATION_BEFORE_KILL.md` for mutation.
2. **Regime-engine fat-tail blowups.** `regime_terminal` and `regime_accumulation` produce 50%+ drawdowns per losing pick (gross loss ≈ 0.58–0.60 per losing pick). No stop discipline. This is the MDD=81% driver. Even a 50% WR `regime_terminal` (2W/2L) has PF=0.038.
3. **Resolver mislabel on FOREX EXPIRED rows.** 14d panel asserts 83% WR but PF 0.10 — the same `EXPIRED_pos_pnl_share` leakage bug pattern that CLAUDE.md documents for CRYPTO. The resolver needs the same scrubbing for FOREX yfinance close-times.
4. **48h single-source dependence on AlphaEngine.** Even though 48h numbers look OK (PF 1.24, WR 53%), the entire emission is from one source — no diversification, no triangulation, fragile.
5. **n<100 floor failure.** Even with all fixes, n=28 is below T2 admissibility (n>=100). Cannot promote until volume builds with clean labels.

## External Replication Options

Each option provides an alternative or sanity-check signal so we are not betting solely on `multi_asset_scanner`+`regime_*` internal outputs.

- **DBMF (iMGP DBi Managed Futures Strategy ETF)** — replicates the SocGen CTA Index. Use the daily holdings file as an external "CTA truth-set" to validate `cta_replicator` direction calls. If DBMF goes long DXY and we are short USD-base pairs, demote the pick.
- **KMLM (KFA Mount Lucas Managed Futures Index)** — alternative CTA benchmark; correlate weekly to detect when our trend-following calls diverge from the systematic-trend industry.
- **MyFXBook public signals** — top-100 risk-adjusted FX signal providers; pull weekly leaderboard, cross-check our directional calls on the same major pairs. Cheap, public API.
- **OANDA / Dukascopy COT-equivalent positioning** — large-spec FX positioning weekly; if our pick is long USDJPY while large-spec is at 5-year extreme long, demote.
- **CME FX futures COT (Tuesday CFTC)** — same idea, US authoritative.
- **PIMCO BOND ETF / DBMF** for the carry-trade overlay leg (FX carry correlates with EM-bond spread).
- **Hyperliquid HLP USDT-pair perp funding** as a real-money FX-adjacent triangulation (USD strength implied by funding skew).
- **MTUM/QMOM** — global-equity momentum ETFs; momentum regime there bleeds into JPY/AUD carry pairs.
- **Internal**: route FOREX through `ai-tournament` (10-model fleet, see `project-ai-tournament-pipeline.md`) — currently FOREX is not in the AI-tournament asset universe. Adding majors (EURUSD/USDJPY/GBPUSD/AUDUSD/USDCAD/USDCHF) gives us a second opinion stream independent of `AlphaEngine`.

## 30 / 60 / 90 Day Rescue Plan

### 30 days (by 2026-06-30) — STOP THE BLEEDING

- **D0 (today):** add `multi_asset_scanner` (FOREX only) to `BLOCKED_SOURCE_SYSTEMS` with a precondition that mutation analysis must pass first; route via `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `MUTATION_THREE_AXIS_PROTOCOL.md` (export closed CSV → `python tools/mutation_analysis.py`).
- **D0:** add per-strategy max-loss circuit breaker for `regime_terminal` and `regime_accumulation` on FOREX: any single pick with realized loss > 0.15 of notional auto-quarantines the strategy for 7d.
- **D+3:** patch the resolver EXPIRED→WON mislabel for FOREX. Apply the same `PNL_WIN_THRESHOLD_BY_CLASS` style guard from `alpha_engine/outcome_resolver.py:115-126` and validate that 14d panel WR↔PF reconcile.
- **D+7:** wire DBMF + KMLM weekly holdings ingestion into `tools/external_replication/` (sidecar; per CLAUDE.md Wire-Up Rule, ship with a Wiring Plan PR if not yet a caller). Begin recording direction-agreement rate.
- **D+14:** add FOREX majors to AI-tournament universe; collect first 2-week shadow cohort.
- **D+21:** re-evaluate. Acceptance gate to continue: clean-cohort n>=50, WR>=40%, PF>=0.8.

### 60 days (by 2026-07-30) — REBUILD EDGE ON SURVIVING STRATEGIES

- Mutate `multi_asset_scanner` parameters on the FOREX leg (lookback, threshold, ATR sizing) and re-test offline before re-enabling.
- Promote `multi_asset_copytrader` (only profitable FOREX strategy, PF 2.01 / WR 67%) — increase its emission allowance up to a 40% share cap, with strict per-symbol concentration (no symbol >25%).
- Stand up external-replication gate: any FOREX pick that disagrees with both DBMF direction AND MyFXBook top-decile direction gets confidence -= 0.20.
- Tournament-cohort consolidation: require 2-of-3 agreement (AlphaEngine + Tournament + DBMF) before emission.
- Target: n>=100 clean cohort, WR>=45%, PF>=1.2, MDD<=25%.

### 90 days (by 2026-08-30) — T2 CANDIDACY

- Final acceptance run with all gates live for >=30 days continuous emission.
- Target: T2 minimum per `reports/hedge_fund_performance_review_*.md` → PF>1.5, WR>50%, MDD<20%, DSR>=0.6, no source concentration >50%, no symbol concentration >30%.
- If still failing, FOREX gets indefinitely demoted to research-only (not eligible for Smart Picks / High Conviction / Money Ready) per CLAUDE.md hard rule below.

## Risk Register

| ID | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| FX-R1 | EXPIRED→WON resolver mislabel masks true edge state | Critical | Confirmed (14d panel inconsistent) | Apply class-aware PnL win threshold + audit unique signal_ts groups |
| FX-R2 | `regime_*` strategies produce fat-tail losses with no stop | Critical | Active (n=2 of 28 caused 60%+ of cohort loss) | Per-strategy max-loss circuit breaker; force `tp/sl` per `tv-paper-trade` rules |
| FX-R3 | 100% single-source AlphaEngine on 48h cohort = fragility | High | Active | Add Tournament fleet + external replication signals |
| FX-R4 | Promoting `multi_asset_copytrader` on n=3 = false confidence | High | Likely if rushed | Hold promotion until n>=20 with WR>50% confirmed |
| FX-R5 | Source-concentration gate not enforced before DSR/SPA (per CLAUDE.md P0) | Medium | Confirmed (cross-class issue) | Wait for source-concentration gate fix; do NOT cite DSR as passing |
| FX-R6 | yfinance FOREX close-time skew vs broker session bleeds into resolver | Medium | Plausible | Use ICE BoFA or OANDA REST as cross-check on resolved closes |
| FX-R7 | Going live before MDD<20% achieved | Critical | Only if rule ignored | Hard rule below |

## Acceptance Criteria

Promotion from current FAIL to "real-money eligible" requires ALL of:

1. n_resolved >= 100 (policy_clean_net cohort)
2. WR >= 50% with 95% CI lower bound > break-even (>= ~47%)
3. PF >= 1.5
4. MDD <= 20% (from current 81%)
5. CVaR95 >= -10% (from current -50.84)
6. Expectancy per pick >= +0.10% after 5bp slippage
7. Top-source share <= 50% AND top-symbol share <= 30% (concentration gate)
8. DSR score >= 0.6 AND SPA p-value < 0.05 AND PBO < 0.5 (with at least 2 strategies of n>=20 to compute)
9. Drift gate clean: no 14d-vs-90d WR delta worse than -10pp
10. Resolver leakage caveats CLEAR on both 14d and 48h panels (no `EXPIRED_pos_pnl` mislabels, dup_groups <= 5)

## Hard Rule (Until Met)

Until ALL acceptance criteria above are met, FOREX is RESEARCH-ONLY. Specifically:

- FOREX picks may NOT enter Smart Picks, High Conviction, or Money Ready surfaces on `/audit`.
- No FOREX position may be placed in live or paper TradingView accounts that influence operator decisions, except inside an explicit shadow/research portfolio labeled `FOREX_SHADOW`.
- No "FOREX is improving" claim is permitted in `updates/index.html` cards unless backed by a clean policy_clean_net cohort row in this report's source files with n>=50.
- The `multi_asset_scanner` FOREX leg remains disabled until mutation analysis produces a parameter set that beats break-even out-of-sample on n>=30.
- Any agent or model that quotes the 14d panel WR (83%) for FOREX without quoting the PF (0.103) AND the leakage caveat is in violation of CLAUDE.md "DO NOT trust unsourced model claims about /audit numbers."

Owner: alpha_engine maintainers. Review cadence: weekly until first acceptance gate (n>=50) is cleared; then per /money-maker-readyv2 rules.
