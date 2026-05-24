# INSTITUTIONAL READINESS PLAN — 90-Day Refresh (2026-05-24 → 2026-08-22)

**Date:** 2026-05-24
**Status:** Living document — supersedes the strategy section of [SUPREME_PLAN_90days.md](./SUPREME_PLAN_90days.md) without invalidating its execution backlog. Existing 90-day pilots (COMMODITY, EQUITY, ETF) continue; this plan adds the **honesty / risk / institutional-readiness layer** identified by a 4-AI external review on 2026-05-24.
**Goal alignment:** Goal #1 (`findtorontoevents.ca/audit` — phenomenal performance across ALL asset classes, prioritized where edge is best worth the risk).
**Authority:** synthesized from the May 24 multi-AI consult (Mercury 2 + Grok + ChatGPT + Gemini — see [updates/2026-05-24-multi-ai-consult-prediction-system-review.md](../updates/2026-05-24-multi-ai-consult-prediction-system-review.md)) and the May 22 stat-validation audit (`reports/AUDIT_STAT_VALIDATION_2026-05-22.md`).

---

## 0. Strategic re-frame (the single most important change)

**Old optimization target:** "find explosive winners" — high score + high upside, freshness-weighted.
**New optimization target:** **"preserve capital while compounding asymmetrically"** — every gate, every score weight, every persona objective re-points at this.

All four external reviewers converged on this same shift. It cascades into ranking, filters, exits, portfolio construction, swarm design, and confidence systems simultaneously. Every sub-plan below is anchored to it.

---

## 1. North-star metrics & two-stage gate (replaces "find PF/WR cards that look high")

Per the 2026-05-24 swarm second-opinion (5/5 engines flagged "Sharpe>1.5 in 6 months" as **too tight** given the current PF 1.3–1.55 baseline), the gate is now **two-stage** so we can show progress without lying about institutional-readiness.

### Stage 1 — Paper-trustworthy (interim, n ≥ 100, ≥ 90 days clean)
This is the realistic floor an honest system can hit while still being below institutional bar.

| Metric | Stage-1 floor |
|---|---|
| Profit Factor | > 1.3 |
| Win Rate | > 48% |
| Sharpe (after costs) | > 1.0 |
| Max drawdown | < 25% |
| Stale-pick rate | < 2% of book |
| Calibration: top-decile score → realized WR | monotonic |

**Stage-1 success = the system is no longer mis-reporting itself.** It does NOT yet justify real capital.

### Stage 2 — Institutional-pilot-ready (real-money gate, n ≥ 100, ≥ 6 months clean)

| Metric | Tier-2 floor (size up) | Tier-1 target |
|---|---|---|
| Profit Factor | > 1.5 | > 2.0 |
| Win Rate | > 50% | > 55% |
| Sharpe (after costs) | > 1.5 | > 2.0 |
| Sortino | > 1.8 | > 2.5 |
| Max drawdown (peak-to-trough) | < 20% | < 10% |
| Calmar | > 0.8 | > 1.5 |
| Stale-pick rate | < 1% of book | 0% |
| Calibration: top-decile score → realized WR | monotonic | monotonic + lift ≥ 1.4× baseline |

**Real-money gate (all four AIs + the swarm agreed):** Stage 2 held for 6 consecutive months — *then* small-capital deployment, not before. No exceptions.

---

## 2. Workstream tree (every item is a real PR, Wire-Up-Rule-compliant)

### Workstream A — Honesty Layer (Weeks 1-3)

**Partial-blocker — per swarm critique:** A1 (freshness) and A3 (calibration) are **truly blocking** for B/E/F (everything downstream depends on honest scores + fresh data). A2 (price reconciliation), A4 (lookahead-CI), A5 (stat surface) and A6 (ghost-row / GHA fixes) are **defensive / diagnostic** and can run in parallel with B and E starting Week 2.

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| A1 | Per-pick freshness SLA (`last_update_ts`, `ingestion_ts`, `freshness_score`); auto-suppress beyond class threshold (crypto 30s, FX 10s, equity 60s, ETF 5m, MF 1d) | `audit_trail/dashboard_generator.py` + new gate in `passes_smart_gate` | Live banner "Last refreshed N min ago" on `/audit`; suppressed-count emitted to JSON |
| A2 | Cross-provider price reconciliation (≥2 of Binance-mirrors / CoinGecko / KuCoin / Polygon / TwelveData / Yahoo); `data_quality=degraded` flag on divergence | New `alpha_engine/price_reconciler.py` called from `score_pick` | Divergence-rate dashboard; suppressed-count visible |
| A3 | Score calibration (Platt or isotonic) per asset class on closed picks | `alpha_engine/score_calibrator.py` inside `calculate_smart_score` | Monotonic score-→-WR on hold-out; lift ratio reported |
| A4 | Lookahead / leakage CI guard | `pytest` guard in `tools/tests/test_no_lookahead.py` | CI fails if any pick has `entry_ts < signal_ts`; clean run on current ledger |
| A5 | Honest stat surface (already partly shipped May 22) — compounded EW return is the headline; sum-of-pct is footnote labelled "Σ Trade %"; `by_asset_class` wins+losses=closed coherence enforced | `audit_dashboard/template.html` + `dashboard_generator.py` | Audit-stat-validation pytest set passes; no card with sum-of-pct as headline |
| A6 | Refresh stale ghost-row footnote + finish `meta_strategy` ghost quarantine + fix `pymysql` GHA gap (Top-5 EQUITY backtest empty) | `audit_dashboard/audit-dashboard.yml` + `audit_trail/db_hygiene.py` | Top-5 EQUITY tile populated; ghost-row count current within 24h |

### Workstream B — Edge Quality (Weeks 2-6, runs in parallel after A1+A3 land)

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| B1 | Transaction-cost + slippage layer (per-class bps curve as f(position size, ADV)) | `alpha_engine/transaction_cost.py` consumed in `passes_smart_gate` (reject when `edge_after_costs ≤ 0`) | Backtest-vs-paper PnL gap on closed picks shrinks ≥ 50% |
| B2 | Regime classifier (trending / mean-reverting / crisis / low-liquidity) + macro-calendar blackout (CPI / FOMC / NFP) for EQUITY + FX | `alpha_engine/regime_filter.py` in `passes_active_gate` | Regime tag visible on every pick; blackout enforced in audit log |
| B3 | Vol-adjusted position sizing (target 0.5–1% portfolio risk per pick) | `alpha_engine/position_sizer.py` invoked before pick emission | Pick records carry `intended_size_pct`; portfolio vol-target hit ±20% |
| B4 | Exit-logic upgrade (ATR-trailing, decay exits on edge half-life, liquidity-aware close) | New fields in `smart_picks_engine` consumed by `alpha_engine/exit_manager.py` | Closed-pick MFE/MAE ratio improves vs current baseline |

### Workstream C — Portfolio Construction (Weeks 4-8)

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| C1 | `portfolio_constraints.py` — correlation cap (pairwise ≤ 0.6 across active book), sector concentration ≤ 30%, factor exposure budget, vol-targeting | Runs *after* Smart Picks, *before* publication to `dashboard_data.json` | Active book never exceeds caps in any 24h window |
| C2 | Pairs / co-integration sleeve (Gemini's market-neutral path) — predict *spread*, not direction, on correlated pairs (AAPL/MSFT, BTC/ETH, XOM/CVX, TLT/IEF) | New `alpha_engine/pairs_engine.py` — **opt-in sidecar** with `## Wiring Plan` targeting institutional bucket (see Workstream D) | Backtest co-integration p < 0.05 on chosen pairs; shadow forward-test active |
| C3 | Risk-budget enforcement — every pick contributes ≤ 5% of portfolio VaR | Inside `portfolio_constraints.py` | VaR contribution emitted per pick |

### Workstream D — Structural Splits (Weeks 5-9)

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| D1 | **Step 1 (Weeks 5-6, ship first):** `speculative_flag` boolean on every pick + visual separation on `/audit` (institutional vs speculative tabs read from the same JSON). **Step 2 (Weeks 7-9, only if Step 1 surfaces real gate-leakage):** full `alpha_engine/speculative_engine.py` split. Per the swarm 2/5 over-engineered concern — start with the flag, escalate to a separate engine only when justified. | Step 1: `passes_active_gate` sets `speculative_flag=True` for penny/IPO/microcap. Step 2 (conditional): `alpha_engine/speculative_engine.py` | Step 1: `/audit` shows clean tab separation. Step 2: only opened if ≥10 institutional picks per month carry contamination from speculative gates |
| D2 | Speculative-bucket gates: float, dilution probability, borrow availability, halt frequency, social-velocity anomaly | `alpha_engine/speculative_engine.py` | Rejection-reason coverage > 95% on penny/IPO inputs |
| D3 | Institutional-bucket gates: factor exposures (size/value/quality/momentum), options flow, analyst revisions, insider activity | Inside the institutional path | Each institutional pick carries factor-exposure vector |

### Workstream E — Swarm-AI Redesign (Weeks 4-10)

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| E1 | Replace stylistic LLM personas with **factor-orthogonal specialist roster**: Macro Hawk · Volatility Hunter · Mean-Reversion · Momentum · Liquidity-Stress · On-Chain Analyst · Microstructure · Sentiment · Quality-Factor · Fraud Detector · **Gatekeeper (veto-only)** | `tournament_runner.py` + per-persona prompt files | Each persona sees a *different* feature slice (anti-collusion per Gemini); Gatekeeper veto rate logged |
| E2 | Swarm-diversity guardrail — nightly PCA on rolling 30d agent-return matrix; if top 2-3 PCs explain > 80%, flag most-correlated agent | New `tools/swarm/diversity_audit.py` writing to `dashboard_data.json::swarm_diversity` | Diversity score column on AI tournament leaderboard |
| E3 | Aggregation upgrade — weighted vote = (Wilson-lower-95% CI of agent Sharpe) × (1 − max pairwise corr); meta-learner regulariser penalises correlated agents | `tournament_aggregator.py` consumed by `dashboard_generator.py` | Aggregator weights visible per round on `/audit/ai-tournament.html` |

### Workstream G — Governance, monitoring, rollback (Weeks 3-13, runs in parallel — added per swarm critique)

All 5 swarm engines flagged the same gap: the plan was strong on edge mechanics but thin on operational risk. Adding G as a first-class workstream.

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| G1 | Real-time monitoring & alerting (score drift, calibration decay, freshness misses, stale-pick spikes) | New `tools/monitoring/audit_health.py` writing to `audit_dashboard/data/health.json` + email/Slack on threshold breach | Alert fires within 5 min of breach in synthetic injection test |
| G2 | Rollback / circuit-breaker — if Stage-1 floor (§1) violated for ≥ 3 consecutive days, auto-quarantine the offending class | `audit_trail/circuit_breaker.py` consumed by `dashboard_generator.py` | Breaker fires + writes audit log in shadow test |
| G3 | Data lineage & versioning — every pick carries `source_id`, `feature_set_hash`, `model_version`, `gate_set_version` | Added to pick records in `score_pick` / `passes_smart_gate` | Lineage trail reconstructable for any closed pick |
| G4 | CI/CD regression — back-test on a frozen golden hold-out set on every PR touching `alpha_engine/` or `audit_trail/` | New `.github/workflows/regression-backtest.yml` | PR blocked if PF on golden set drops > 5% vs main |
| G5 | Explainability surface — per-pick "why it fired" (gate names that passed, feature vector top-3 contributors, persona votes) on `/audit` | `audit_dashboard/template.html` pick-detail modal | Every pick shows 3+ explanatory facts |
| G6 | Stress / scenario tests — synthetic 2008, 2020-Mar, 2022-LUNA, 2018-Q4 crypto rollovers replayed against the gate stack | `tools/stress_test_replay.py` quarterly | Stage-1 floor held in 3/4 historical regimes |

### Workstream F — Coverage gaps + new products (Weeks 6-13)

| # | Item | Wire-up target | Acceptance |
|---|---|---|---|
| F1 | Wire missing ETF / Bond / Commodity emitters into the active JSON pipeline (carried from May 21 6-gate findings) | `audit_trail/dashboard_generator.py` ingestion list | All 8 asset-class tiles populated, no "n=0" cards |
| F2 | Low/no-fee no-min mutual-fund ranker — composite `0.30·(1−ER) + 0.25·Sharpe + 0.20·Liquidity + 0.15·5y-Perf + 0.10·ESG` + Upside/Downside Capture + IR | New `alpha_engine/mutual_fund_ranker.py` + `/audit/mutual-funds.html` surface | Ranked board live; entry threshold ER ≤ 0.50%, 5y alpha > 0, max-DD < 25%, AUM > $100M |
| F3 | Per-class metric expansion (crypto: funding/OI/liquidations/stablecoin flows; equity: float/short/insider/options flow/factor; FX: rate diff/carry/COT; bonds: duration/convexity/real yields/breakevens; commodities: curve/inventory/seasonality) | Feature columns in `dashboard_data.json` consumed by respective gates | Each class emits the full metric vector; gates that ignore a metric explicitly say so |

---

## 3. Per-asset-class verdict (informs workstream priorities)

| Class | Current (post-resolver-v2) | Verdict | Primary workstream |
|---|---|---|---|
| EQUITY | PF 1.41 / WR 52.7% / n=421 | T2-candidate; closest to institutional | A + B + D3 + E1 |
| ETF | PF 1.24 / WR 55.2% / n=87 | Borderline; easiest institutional surface | A + B + F1 + C2 |
| COMMODITY | PF 1.78 / WR 46.9% / n=750 | T2 PF met, lift WR | A + B + B2 (regime) |
| BOND | PF 1.72 / WR 55.6% / n=18 | T2 PF+WR but below n-floor | A + F1 + F3 |
| CRYPTO | PF 1.25 / WR 44.6% / n=8067 | Sub-T2 — cut `quan_engine` + `unknown` source volume share | A + B + D + E |
| FOREX | PF 0.27 / WR 46.4% / n=1169 | Genuinely sub-floor; mutate-before-kill protocol | Deep-dive doc + B2 (macro blackout) before any new gates |
| FUTURES (financial) | n=0 in own tile | Routing bug → merge into unified CTA or deprecate | Deferred until D1 lands |
| PENNY/MEME | PF 0.19–0.50 / WR 7–16% | Full quarantine → speculative bucket | D1 + D2 |
| MUTUAL FUNDS | not yet ingested | New surface | F2 |

---

## 4. Sequencing & timeline (revised per swarm critique)

```
W1-W3   Workstream A (honesty) — A1+A3 blocking; A2/A4/A5/A6 parallel
W2-W6      └─ Workstream B (edge quality) starts after A1+A3 land
W3-W13     └─ Workstream G (governance / monitoring / rollback) parallel
W4-W8         └─ Workstream C (portfolio construction)
W5-W6            └─ Workstream D1 Step 1 (speculative flag — cheap)
W4-W10              └─ Workstream E (swarm redesign — parallel)
W6-W13                 └─ Workstream F (coverage + new products)
W7-W9                     └─ Workstream D1 Step 2 (engine split — only if Step 1 surfaces contamination)
W13     90-day checkpoint: STAGE-1 gate evaluation per §1 (Sharpe>1.0 / MDD<25% / 90 days clean)
W13+    Stage-2 institutional gate begins its own 6-month clock
```

---

## 5. Decision points (kill / continue gates)

| Day | Gate | Action if failed |
|---|---|---|
| 21 | Workstream A complete; freshness banner live; calibration monotonic on EQUITY hold-out | Halt all other workstreams; root-cause A before proceeding |
| 45 | Backtest-vs-paper PnL gap (with TC layer) ≤ 50% of pre-TC gap on EQUITY | Pause B; investigate slippage model under-/over-fit |
| 60 | EQUITY or ETF active book holds correlation cap + sector cap for 14 consecutive days | Pause D scaling; review constraint thresholds |
| 90 | At least one asset class meets **Stage-1** gate (§1) — PF>1.3 / WR>48% / Sharpe>1.0 / MDD<25% / monotonic calibration | Extend window to 120d; do NOT promote to Stage-2 clock until floor holds |
| 90+ | Stage-2 clock starts only after Stage-1 holds 90 consecutive days on the same class | No real-money capital deployment until Stage-2 held 6 consecutive months |

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Calibration breaks elite-strategy ranking (top performers down-weighted) | Medium | High | A3 runs in shadow first; compare ranked top-20 before/after; freeze elite strategies during cutover |
| Freshness SLA suppresses too many picks during low-data windows (weekends, holidays) | High | Medium | Per-class thresholds; "low-data mode" allows wider SLA; audit log of suppression reasons |
| Pairs sleeve (C2) generates anti-correlated paper losses that cancel real wins on the same pair | Medium | Medium | Opt-in sidecar only; never auto-sized into book; shadow forward-test first |
| Persona redesign (E1) breaks the existing tournament leaderboard continuity | Low | Medium | Versioned tournament — v1 (current) keeps running in parallel for 30 days |
| Speculative/institutional split (D1) leaks penny logic into institutional gates | Medium | High | Hard router boundary; CI test that grep-asserts no penny-only module is imported in the institutional path |
| Real-money gate gets pressure-tested before §1 metrics actually hold | Low | Catastrophic | Documented elsewhere too (Goal #1 banner); reject every "let's go live early" until 6-month clean window confirmed |

---

## 7. What this plan does NOT do (out of scope, deferred)

- Live execution / OMS / smart-order-routing (institutional-only; out of scope until §1 gate hit on a class).
- Cross-node failover for live trading (Gemini's "Mesh Integrity" point) — deferred to post-pilot.
- Regulatory / compliance buildout — deferred.
- New strategy invention beyond what's already in the catalog — this plan is about making the existing catalog trustworthy, not adding more candidates.

---

## 8. Swarm second-opinion (2026-05-24)

The first draft of this plan was fanned to 5 engines via `tools/swarm/swarm_run.py` (deepseek, groq, inception, pollinations gave structured answers; gemini_api + ofox failed to return JSON). Their critique drove the revisions documented above.

| Engine | Blocking-A verdict | Thresholds | D1 split | Grade |
|---|---|---|---|---|
| deepseek | partial (A1+A3 only) | too tight | right call | B |
| groq | partial | too tight | right call | B |
| inception | partial | too tight | over-engineered | B |
| pollinations | full blocking | too tight | over-engineered | C |
| **consensus** | **partial (A1+A3 block; rest parallel)** | **too tight** | **mixed — phase it (D1 Step 1 first)** | **B** |

**Missing items all 5 raised** (now folded in as Workstream G):
- Real-time monitoring & alerting → G1
- Rollback / circuit-breaker → G2
- Data lineage & versioning → G3
- CI/CD regression on golden hold-out → G4
- Explainability surface → G5
- Stress / scenario tests → G6

**Highest-risk assumption flagged (deepseek + inception agreed):** that raw PF 1.3–1.55 will survive transaction costs + regime blackouts + portfolio constraints to land at Sharpe > 1.5. Likely won't without a real edge upgrade — which is why the gate is now two-stage (Stage 1 = honest paper; Stage 2 = institutional).

Raw swarm outputs preserved at `swarm_runs/iret-review-20260524T054451Z/` and `swarm_runs/iret-review-fan-20260524T054507Z/`.

---

## 9. Cross-refs

- Multi-AI consult that drove this plan: [updates/2026-05-24-multi-ai-consult-prediction-system-review.md](../updates/2026-05-24-multi-ai-consult-prediction-system-review.md)
- Original 90-day exec plan: [SUPREME_PLAN_90days.md](./SUPREME_PLAN_90days.md)
- Per-class plans (each gets a "2026-05-24 Institutional-Readiness Refresh" appendix): [BOND](./asset_class_90day_plan_BOND_2026-05-15.md) · [COMMODITY](./asset_class_90day_plan_COMMODITY_2026-05-15.md) · [CRYPTO](./asset_class_90day_plan_CRYPTO_2026-05-15.md) · [EQUITY](./asset_class_90day_plan_EQUITY_2026-05-15.md) · [ETF](./asset_class_90day_plan_ETF_2026-05-15.md) · [FOREX](./asset_class_90day_plan_FOREX_2026-05-15.md) · [FUTURES](./asset_class_90day_plan_FUTURES_2026-05-15.md) · [PENNY/MEME](./asset_class_90day_plan_PENNY_MEME_2026-05-15.md)
- Stat-validation audit (May 22): `reports/AUDIT_STAT_VALIDATION_2026-05-22.md`
- 90-day gap analysis: [90day_gap_analysis_2026-05-15.md](./90day_gap_analysis_2026-05-15.md)
- Baby-strategy 90-day expansion: [continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md](./continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md)
- HTML companion: [audit_dashboard/institutional_readiness_plan.html](../audit_dashboard/institutional_readiness_plan.html)
