# Execution plan — path to profitability (realistic, gated)

## Phase 0 (now, 1–3 days) — truth + safety
- **T0.1** Freeze a “truth baseline” document: which files are source of truth (canonical closed JSON/DB view) and which are displays. Reference `audit_surface_truth.json`, `db_health.json`, and the v2 MASTER_AUDIT reconciliation.
- **T0.2** PnL unit contract + backfill + remove ingest heuristics that guess fractions (per `scratch-hippodraco.MD` P0). Add CI check: recompute PnL from prices for a sample; fail on unit ambiguity.
- **T0.3** Reconcile active counts: publish one number for “active tradable (priced, fresh, not expired)”; move zombies to `expired`/archived views. Do **not** use the vetoed mass-UPDATE/mass-DELETE patterns from peer `proposed_fixes` without a reviewed migration plan.
- **T0.4** Surface resolver/dashboard freshness in JSON (YELLOW/RED) so dashboards cannot show “stale warning false”.
- **T0.5** Apply only **safe** peer fixes agreed in v2 reviews: mark ghosts (not delete) with dedup strategy if designed carefully; fix `summary_picks` math in the correct generator path (and fix fallback paths per v1/v2 notes); fix TP-before-SL resolution order where proven — each as its own PR with tests.

**Exit gate Phase 0:** can you answer “what is the canonical closed set, with units and n?” from one documented pipeline?

## Phase 1 (3–14 days) — regenerate evidence surfaces
- **T1.1** Rebuild registry/pf stats from canonical closed set.
- **T1.2** Regenerate `money_ready_verdict.json` (and any CI gates that compare to it).
- **T1.3** Regenerate `benchmark_ledger_proof.json` using `alpha_engine/benchmark_closed_ledger.py` with direction-aware benchmarks per class and current truth data (not Oct snapshot).
- **T1.4** Run `tools/ci_gate_money_ready_vs_registry` (and add/adjust gates per v2 `CI_GATES.md` ideas where safe).

**Exit gate Phase 1:** verdict + benchmark JSONs are **fresh** and consistent with the same closed set; no known unit/freshness lies in those feeds.

## Phase 2 (2–6 weeks) — per-class scoring (one class at a time)
Pick **one** class to “make honest first” (suggested order below), then repeat:
- **T2.1** Confirm data plumbing (prices, costs model, timestamps, classifier correctness).
- **T2.2** Build walk-forward OOS schedule (embargo/purge consistent with holding period/label horizon). No refit leakage.
- **T2.3** Compute: n, PF, WR, expectancy after costs, MDD/CVaR, concentration. Apply DSR with real `nb_trials` (count all tested variants in that search episode), SPA/White’s RC where feasible, PBO only if ≥5 strategies with power.
- **T2.4** Fill a row in `PRODUCTION_READINESS_FRAMEWORK.md` §5 style table (or equivalent tracked doc).
- **T2.5** Benchmark paired test vs class-appropriate benchmark; record `frac_positive`/MC only as supporting (paired headline gate).

**Suggested order (pragmatic):**
1. **EQUITY or ETF** if quote/classifier plumbing is fixable and you have volume — but fix the n-disagreement bug first.
2. **CRYPTO** only after unit/backlog/fabricated-cohort cleanup and cost model (fees/funding/slippage tiers); expect most “edges” to vanish.
3. **FOREX** only with spread/roll costs and enforceable allowlist + corrected direction/sync math.
4. **BOND/COMMODITY/FUTURES/MF**: defer **promotion** until structural fixes (see `PER_ASSET_CLASS.md`) — in many cases the right answer is “not tradable here yet”, not “optimize harder”.

**Exit gate Phase 2 (per class):** Charter 7 gates pass on rolling 90d **and** frozen walk-forward OOS; `money_ready_verdict` reflects that class (or stays NOT_READY honestly). Otherwise stay paper.

## Phase 3 — controlled paper / micro-live (only classes that pass Phase 2)
- **T3.1** Implement risk caps in live wrapper (Charter §7), not docs only.
- **T3.2** Shadow for ≥30 days with the same resolution/cost assumptions.
- **T3.3** Only then consider size-up via Charter §8 promotion steps (monthly clean metrics).

## What NOT to do
- Do not merge finpredict-v4 `proposed_fixes/*` destructive items.
- Do not unblock FUTURES/COMMODITY by removing blocklists while feeds/mapping/costs are wrong.
- Do not claim “profitability” from in-sample backtests or from any single snapshot without OOS + costs + MT correction.
- Do not trust `summary_picks`-style WR aggregates until math is fixed and validated.
