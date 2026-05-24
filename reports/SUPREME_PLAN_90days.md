# SUPREME PLAN — 90-Day Execution Roadmap (May 15 – Aug 15, 2026)

**Date:** 2026-05-15  
**Status:** Living Document | Author: Grok (Senior Quant) + Subagent Fleet  
**Goal:** Turn the platform into a focused, edge-compounding machine capable of supporting real-money allocation in at least one diversified asset class within 90 days.

**Core Principle:**  
One production-grade, diversified asset class with trustworthy forward results beats seven half-baked ones. Cotton (CT=F) is promising but **one symbol**. We must diversify or explicitly cap risk.

## Latest Update (2026-05-15, post deep_dive_cotton_2026-05-15.md + PRs #1060/#1061/#1065/#1068 + swarm)

- The Phase 2-D kill of CT=F was data-flawed: the panel cited 8.3% WR / n=12, but the actual PRE-kill 12 picks resolved to 66.7% WR / PF 3.50 / +32.30% in the resolver-v2 ledger.
- **Verdict: HOLD_KILLED_PENDING_DATA** (corrected from an earlier REVIVE_SHADOW draft after 3-engine swarm review). Raw n=41 collapses to effective independent n ≈ 3-4 — 39/41 picks share weekly COT signals. 100% SHORT in a downtrend = regime-survivorship risk. No revival until: effective-n ≥ 20 by signal-cluster, regime decomposition passes, friction-adjusted DSR, survivorship check. See `reports/deep_dive_cotton_2026-05-15.md`.
- The Phase 2-D panel's cited sample sizes do not reconcile with the resolver-v2 ledger at all (GC=F cited n=91 → ledger n=3; CT=F/KC=F cite identical "n=12 WR 8.3%"). Kill verdicts are not reproducible. See `reports/phase2d_kill_audit_2026-05-15.md`.
- **Real root cause (swarm + peer consensus): kill-threshold mis-calibration** — small-n rolling-window kills with no statistical guardrail; thresholds tuned on in-sample dead strategies → a self-reinforcing ratchet that destroys evidence faster than it accumulates.
- **M-055 shipped (PR #1068):** `audit_trail/kill_gate.py` — a statistical kill-gate (min-n + binomial p-value + Wilson 95% CI). Replayed against the Phase 2-D kills it blocks 4 of 5 (CL=F/CT=F/KC=F on min-n, SI=F on non-significance). Opt-in sidecar; wire-in is the next step.
- Correct sequence: **M-055 (done) → wire kill_gate into quality_gates → M-056 incubator → M-057 decouple score_booster from crypto-gating → M-058 auto-spawn last.**
- Priority shift: EQUITY (VIX-regime 12-1 momentum on clean large-caps) + ETF (sector rotation + VIX gate) as near-term primary pilots. COMMODITY secondary (data hygiene + diversify beyond CT=F; cotton stays HOLD_KILLED). BOND scanner gap (2/14 symbols, TLT 75% concentration) is genuinely actionable.
- Meta-lesson: 5 senior-quant AIs converged on "cotton = real-money pilot" — all wrong, all reading the same stale inputs. Convergence ≠ verification.
- **Data-supplement companion shipped:** `reports/asset_class_data_supplements_2026-05-15.md` — per-asset-class free APIs, prediction-market feeds (Kalshi/Polymarket), and copytrader sources, each with free-tier limits + the existing repo module to wire into. Headline: most needed data is already coded but unwired (`bond_data_fred.py` curve unused via `SKIP_FRED=1`; `commodity_carry_momo.json` has no caller; `kalshi_signals.py` exists with a no-key API). Highest-leverage adds: set `FRED_API_KEY` (unblocks EQUITY/ETF/FOREX/BOND/COMMODITY) and wire Kalshi for macro/rate/weather gating across 5 classes. Honest copytrader verdict: real free feeds exist only for CRYPTO (Hyperliquid) + FOREX (ZuluTrade/MyFXBook); for COMMODITY/BOND/FUTURES use CFTC COT/TFF positioning; for PENNY_MEME filter copytrader output out (net-negative).

---

## 1. Current State Snapshot (Verified, Not Trusted from Old Reports)

Using latest `dashboard_data.json` (generated 2026-05-15) + recent audits + DB forensics:

**Top Performers (Live / Recent Closed):**
- **COMMODITY** — Strongest risk-adjusted edge (PF often 2.0+ in recent windows). Driven heavily by cotton COT positioning. n is reasonable but universe is narrow.
- **EQUITY** — Best diversified candidate. Decent sample size, improving metrics in some regimes.
- **ETF** — Respectable win rates in pockets but low overall n. Not yet scalable.
- **CRYPTO** — Highest volume by far, but quality is poor. Many toxic systems and low-liquidity symbols drag the class.
- **FOREX & BOND** — Statistically weak or insufficient sample. Not ready for material capital.

**Critical Systemic Gaps (The Real Blockers):**
- Outcome tracking is still terrible (`at_signal_outcomes` coverage << 5% in many periods; paper_trades nearly empty).
- DB freshness and ghost rows remain a problem (DB Freshness Guardian is partially built but not fully enforced).
- Symbol universe coverage per class is poorly documented and likely contains too many low-liquidity names (especially crypto/penny).
- No systematic pruning/inversion process for failing strategies.
- Execution realism (slippage, position sizing, concentration, drift breakers) is still mostly scaffolding.

---

## 2. 90-Day Strategic Priorities (Ranked)

### Priority 1: Foundation (Weeks 1-3) — Do Not Skip
- Make **DB Freshness Guardian** production-grade with real GHA enforcement (fail on RED).
- Force reliable outcome tracking (`at_signal_outcomes` + `paper_trades` + `paper_portfolio_daily`).
- Run full symbol universe + liquidity audit per major asset class (free data only: yfinance, CoinGecko, FRED, CME delayed, etc.).
- Clean up test suite to <5 failures on main.

### Priority 2: COMMODITY Pilot — Diversify or Explicitly Limit (Weeks 1-12)
**Primary bet for the 90 days.**

- Cotton (CT=F) COT edge is real but **one symbol = unacceptable concentration** for serious money.
- Must expand to 4–6 other liquid commodity futures with decent history (GC gold, SI silver, CL crude, NG natural gas, ZS/ ZC grains, etc.).
- Deliver full COT lag-correction + MATCH gate + friction-adjusted DSR (fix the 0.08 vs 0.0008 bug).
- Wire real position sizing, slippage model, kill switches, and concentration limits (Phase J safety modules from the clean cherry-pick).
- Run disciplined paper pilot with 0.5–1% portfolio risk per trade and 30–60 day track record.

**Go/No-Go at Day 60:** If we cannot diversify beyond cotton with positive expectancy after costs, treat COMMODITY as a high-conviction single-strategy sleeve with hard limits rather than a full asset class.

### Priority 3: EQUITY — Build the Broad Book (Weeks 4-12, Parallel)
- Strongest candidate for a diversified, multi-strategy book.
- Focus on earnings surprise + post-earnings drift (PEAD) using free SEC EDGAR + Yahoo data.
- Add VIX + yield curve regime filters.
- Aggressive pruning of low-quality equity strategies (delete or invert).

### Priority 4: ETF — Lower-Effort Parallel Track
- Sector rotation + macro regime models.
- Only scale if COMMODITY pilot shows real promise.

### Priority 5: CRYPTO — Major Cleanup, Not Expansion
- Shrink universe to top 20–30 liquid coins only.
- Kill or quarantine the toxic systems dragging the class (many identified in previous audits).
- Do not allocate new capital until quality improves dramatically.

### De-prioritize (Maintenance Mode)
- **FOREX & BOND**: Data collection and small research only. Not ready for production capital in this 90-day window.

---

## 3. Per-Asset-Class 90-Day Plans — Full Coverage Complete

All asset classes in the `findtorontoevents.ca/audit` dropdown now have dedicated, subagent-generated 90-day plans (using the `money-maker-continual-improve` skill). Full set:

- **[COMMODITY](./asset_class_90day_plan_COMMODITY_2026-05-15.md)** — Strongest surface edge but 73% concentration on CT=F + COT over-emission falsification (true n tiny). Must diversify or de-risk heavily.
- **[EQUITY](./asset_class_90day_plan_EQUITY_2026-05-15.md)** — Best diversified candidate. Powerful unshipped VIX-regime 12-1 momentum (backtest PF 5.37). Production universe too narrow + speculative.
- **[ETF](./asset_class_90day_plan_ETF_2026-05-15.md)** — High-ROI activate-now opportunity (sector rotation + VIX gate = Tier-1 backtests). Low effort, good diversification.
- **[CRYPTO](./asset_class_90day_plan_CRYPTO_2026-05-15.md)** — Highest volume, lowest quality. Requires brutal universe shrink + toxic system quarantine.
- **[FOREX](./asset_class_90day_plan_FOREX_2026-05-15.md)** — Sub-floor performance. Data improvements + carry/momentum research only for 90 days.
- **[BOND](./asset_class_90day_plan_BOND_2026-05-15.md)** — n=11, PF 0.66, extreme TLT concentration. **De-prioritize** for 90 days (research/opt-in sidecar only).
- **[FUTURES](./asset_class_90day_plan_FUTURES_2026-05-15.md)** — n=0 in the FUTURES tile (commodity futures routed to COMMODITY via classification bug). **Merge** financial futures into unified CTA or deprecate the separate class.
- **[Penny Stocks + Meme Coins](./asset_class_90day_plan_PENNY_MEME_2026-05-15.md)** — PF 0.19–0.50, WR 7–16%, massive drag. **Full quarantine** (0% allocation, research-only, no dedicated sleeve).

Additional deep-dive subagents are queued for FOREX, BOND, FUTURES, and Low-Quality Equities (Penny Stocks + Meme Coins) — the categories explicitly noted as weak or missing in the `/audit` asset class dropdown.

**Master Summary View (Current Assessment):**
- **COMMODITY**: Best edge but cotton concentration is the #1 risk to solve. Diversify or cap.
- **EQUITY**: Best "broad" candidate for a multi-strategy book. Focus here for diversification.
- **ETF**: Marginal — good WR in spots, low n. Worth light parallel work.
- **CRYPTO**: Volume king, quality problem. Needs brutal universe reduction.
- **FOREX / BOND**: Not investment-grade yet. Data only.

---

## 4. Success Metrics (End of 90 Days — Measurable)

- At least one asset class (target: diversified COMMODITY or strong EQUITY) with:
  - 60+ day trustworthy paper trading track record
  - PF > 1.6 and Sortino > 1.8 after realistic costs
  - Max drawdown < 12–15%
  - Clear, documented edge with known failure modes
- Outcome tracking coverage > 40% for new signals
- Main CI green (< 5 failures)
- Symbol universe + liquidity audit complete and documented for top 4 classes

---

## 5. Immediate Next Actions (This Week)

1. Finish and enforce DB Freshness Guardian.
2. Fix outcome tracking pipeline (resolver + paper trading).
3. Launch symbol universe audit scripts (free data sources).
4. Clean cherry-pick of Phase J safety modules (d3995f5ac4d) for COMMODITY pilot.
5. Begin COT lag + MATCH productionization (fix friction rate bug).
6. Start subagent-generated per-class deep dive reports (already in flight).

---

**This document is the single source of truth for the next 90 days.** All other M-IDs in the old master plan are de-prioritized unless they directly support the above.

Detailed per-asset-class execution plans (with specific symbols, data sources, backtest frameworks, and pruning lists) will be linked here as the subagents complete their work.

*Generated with the `money-maker-continual-improve` skill + live subagent fleet.*
---

## 2026-05-24 — Institutional-Readiness Refresh (overlay, does not invalidate the May-15 backlog)

A 4-AI external consult (Mercury 2 + Grok + ChatGPT + Gemini) reviewed the live `/audit` surface on 2026-05-24, and a 5-engine swarm second-opinion (deepseek + groq + inception + pollinations + ofox) reviewed the resulting plan. Both passes are folded into [INSTITUTIONAL_READINESS_PLAN_2026-05-24.md](./INSTITUTIONAL_READINESS_PLAN_2026-05-24.md) — the **honesty + risk + governance layer** on top of this document.

**What changed vs the May-15 plan:**

- **Optimization target re-framed** from "find explosive winners" → **"preserve capital while compounding asymmetrically."** This is the single biggest change; it cascades into ranking, filters, exits, portfolio construction, swarm design.
- **Two-stage gate** replaces the single institutional gate. Stage 1 (Sharpe>1.0 / MDD<25% / 90 days clean / monotonic calibration) is the realistic 90-day target; Stage 2 (Sharpe>1.5 / MDD<20% / 6 months) is the real-money gate. The original "Sharpe>1.5 in 6 months" was flagged as too tight by 5/5 swarm engines given the current PF 1.3–1.55 baseline.
- **New Workstream G (Governance / Monitoring / Rollback)** — real-time alerting, circuit-breaker on Stage-1 floor violation, data lineage, CI/CD regression on a frozen golden hold-out, explainability surface, quarterly stress replays.
- **D1 (speculative/institutional split) is now two-step** — Step 1 ships a `speculative_flag` boolean (cheap, 1 week); Step 2 splits engines only if Step 1 surfaces contamination.
- **Calibration of `smart_score`** (Platt / isotonic) added as a P0 — addresses the May-22 inverted-confidence finding.
- **Per-pick freshness SLA** with class-specific thresholds and auto-suppression (crypto 30s, FX 10s, equity 60s, ETF 5m, MF 1d). The May-15 plan called for "DB Freshness Guardian" generically; this hard-codes the SLAs and pushes them to the gate, not just the dashboard.

**Pilot priorities unchanged:** COMMODITY (diversify beyond CT=F) + EQUITY (broad book) + ETF (sector rotation + VIX gate) remain primary. CRYPTO universe shrink + toxic-system quarantine still mandatory. FOREX + BOND still maintenance-mode. FUTURES + PENNY/MEME folded into the speculative bucket per D1.

**Authority:** [INSTITUTIONAL_READINESS_PLAN_2026-05-24.md](./INSTITUTIONAL_READINESS_PLAN_2026-05-24.md) supersedes the *strategy* sections of this doc going forward; the *execution backlog* below (M-IDs, per-class pilots, ghost-row cleanup, etc.) continues unchanged.

Source: [updates/2026-05-24-multi-ai-consult-prediction-system-review.md](../updates/2026-05-24-multi-ai-consult-prediction-system-review.md) + `swarm_runs/iret-review-{20260524T054451Z,fan-20260524T054507Z}/`.
