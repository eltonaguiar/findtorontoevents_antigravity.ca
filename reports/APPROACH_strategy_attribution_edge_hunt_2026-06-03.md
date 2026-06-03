# APPROACH — Strategy-Level Attribution Edge Hunt (2026-06-03, for cross-review)

**Author:** Claude Opus 4.8 · **Status:** PROPOSAL (pre-implementation) · **Reviewers:** AI swarm + /consult-*

## Goal
The model-level attribution probe (PR #496) showed the tournament "edge" is crowd/beta, not skill
(deepseek_v4 alpha t=1.74, crowd_beta 0.49; no model has adequate-n + surviving alpha). Now hunt for
edge at the **strategy** level (not model_id) — is there ANY strategy whose return survives
leakage-free attribution? Push the bootstrap-CI shortlist sleeves through the #111 gate with a proper
benchmark.

## Hypothesis
At least one *strategy* (e.g. `crypto_liquidity_wick_reversal`, `prediction_market_consensus`,
`drawdown_recovery_rsi_xrp`) has residual alpha that survives attribution at n>=100 — OR none do, in
which case `money_ready=[]` is confirmed at the strategy granularity too.

## Proposed method
1. **Source data:** `alpha_engine/data/closed_picks.json` (canonical fallback, 1054 rows) +
   `audit_dashboard/data/ai_tournament_picks_latest.json` (5036 resolved). Group by `strategy` /
   `source_system` (not `model_id`).
2. **Benchmark (the key design choice — REVIEW THIS):** two legs, run both:
   - (a) **Crowd-proxy** (as in #496): mean return of ALL strategies on the same symbol → strategy
     alpha = excess over the crowd on its own symbols. Endogenous, leakage-free, no external data.
   - (b) **Real-market beta:** regress strategy returns on the matching asset-class index return
     (CRYPTO→BTC, EQUITY/ETF→SPY, etc.) using `verified_strategies/data_fetcher`. Requires aligning
     each pick to a benchmark return over its hold window — needs `signal_ts`/`entry_date`
     (recoverable via the provenance backfill, PR #484: CRYPTO 100%, OVERALL 44.8%).
3. **Gate:** the #111 `attribution_gate` — alpha>0 AND t>=2.0 AND info-ratio>=0.10. Require **n>=100**
   per strategy (small-n flukes are the failure mode we already saw).
4. **Cross-check:** compare survivors against the bootstrap-CI shortlist (PR #481/#482) and the
   single-source-artifact flag (#65). A real survivor should pass ALL: bootstrap CI lower bound >1,
   not single-source, alpha-significant.
5. **Output:** `reports/strategy_attribution_findings_2026-06-03.md` + per-strategy JSON. Report-only.

## Implementation plan
- `tools/strategy_attribution_probe.py`:
  - `build_strategy_pairs(picks, key='strategy')` → per-strategy (own_pnl, crowd_pnl_on_symbol) pairs.
  - `probe_crowd(picks)` → reuse `return_attribution.attribution_gate` per strategy (leg a).
  - `probe_market(picks, benchmark_returns_by_symbol_window)` → leg b (gated on backfilled timestamps).
  - rank by (alpha_ok, alpha_ir); flag strategies passing BOTH legs.
- Reuse: `return_attribution` (#111), `data_fetcher` (benchmark), `backfill_provenance` (timestamps).
- No new heavy deps (numpy only).

## Verification plan
1. **Synthetic unit tests:** (i) a fabricated pure-beta strategy → FAIL; (ii) a constant-alpha strategy
   → PASS; (iii) n<100 → excluded; (iv) crowd-proxy and market-proxy agree on a controlled fixture.
2. **Adversarial / negative control:** inject a known-null random strategy into the real dataset — it
   MUST fail. If it "passes," the gate is too loose.
3. **Consistency check:** any strategy that passes attribution must ALSO have bootstrap-CI lower>1
   (PR #481) and not be single-source (#65). Disagreement = surface it, don't auto-trust.
4. **Reproduce:** `python3 tools/strategy_attribution_probe.py`; deterministic (fixed seeds, no RNG in
   the real path).

## Risks / open questions (FOR REVIEWERS)
- **R1 — Crowd-proxy validity:** is "excess over the average agent on the same symbol" a sound alpha
  benchmark, or does it just measure dispersion? Should leg (a) be trusted at all, or only leg (b)?
- **R2 — Hold-window alignment:** matching each pick to a market return needs entry+exit timestamps;
  `resolved_at` is batch-stamped and `signal_ts` ~44% recoverable overall. Is symbol-level
  benchmark (ignoring exact window) good enough, or fatally biased?
- **R3 — Multiple testing:** testing ~50 strategies for alpha → apply BH-FDR (#64) across the
  strategy set before declaring any survivor? (I think YES — propose wiring #64 into the probe.)
- **R4 — Survivorship/selection:** the shortlist came from the same data; is re-testing it circular?
  Should the real test be forward-only (post-today picks)?
- **R5 — Is this the right next step at all,** or should effort go to building genuinely new
  candidate strategies (e.g. the per-class archetypes in the EAGLE2 synthesis) rather than
  re-auditing existing ones?

## Success criteria
- Either: >=1 strategy passes BOTH attribution legs + bootstrap-CI + non-single-source at n>=100
  (→ a real forward-test candidate), OR a clean negative result strengthening `money_ready=[]`.
- Negative control fails. Multiple-testing correction applied. Fully reproducible.

---

## CROSS-REVIEW VERDICT (6-model swarm, 2026-06-03)

**Tally:** STOP ×2 (deepseek-chat, paid-mode-large) · REVISE ×2 (cloudflare-llama, hybrid-large) · GO ×1 (ollama-cloud-local) · 1 no-return (nvidia, rate-limited). **Net: do NOT implement as proposed.**

**Consensus findings (raw reviews: `swrev_*.txt`):**
- **R1 — DROP the crowd-proxy.** 4/5: "excess over average-agent on same symbol" measures *dispersion*, not alpha — a zero-sum relative ranking within a noisy crowd, no risk model, no economic interpretation.
- **R2 — FATAL bias (the show-stopper).** Near-unanimous: batch-stamped `resolved_at` (~4 distinct days) destroys temporal alignment; you cannot regress on BTC/SPY without true hold windows; 44% signal_ts recovery is "a data-snooping minefield." Reject any method using `resolved_at` as trade timing.
- **R3 — BH-FDR too weak.** Strategies are highly correlated (same symbols/windows) → use a dependence-adjusted procedure (Benjamini-Yekutieli) or Holm/Bonferroni, not plain BH.
- **R4 — Circular.** Unanimous: re-testing the bootstrap-CI shortlist on its own selection data is double-dipping → must be **forward-only / out-of-sample**.
- **R5 — Wrong next step.** Several: fix the data infrastructure (true trade-level timestamps) FIRST; build NEW per-class archetypes with clean daily bars rather than re-auditing broken data.

## REVISED PLAN (supersedes the method above)
1. **Do NOT ship the crowd-proxy strategy probe.** It is unsound (R1) and the dataset is temporally broken (R2).
2. **Prerequisite — fix trade-level timestamps** (true entry/exit, not batch `resolved_at`). This is INCIDENT_OVERALL #90's fix field + the resolver work flagged repeatedly. Upstream/operator-owned.
3. **Forward-only evaluation only.** Evaluate sleeves on picks emitted AFTER a frozen cutoff (naturally out-of-sample + leakage-free), accumulated over time via the #67 shadow-size ladder. No re-testing of selection data.
4. **Real-market benchmark** (BTC/SPY over true hold window), never the crowd-proxy; gate stays #111 (alpha t>=2 + IR>=0.10) but with **Benjamini-Yekutieli** correction across the (correlated) strategy set.
5. **Parallel track:** build NEW per-class archetypes from the EAGLE2 synthesis (dual-momentum ETF, TSMOM commodity, carry FX) with clean daily-bar backtests — likely higher ROI than re-auditing the contaminated tournament ledger.

**Status: PROPOSAL REJECTED by review → revised to the prerequisite-first plan above. No flawed probe shipped.** This is the cross-review working as intended.
