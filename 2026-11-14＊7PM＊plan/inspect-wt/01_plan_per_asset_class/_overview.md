# Plan per asset class → profitability (overview)

> Companion to `../04_agent_prompts/` (paste-ready prompts) and
> `../08_key_metrics_by_perspective/` (the bar). Every class plan is **benchmark-relative**:
> the event is not "positive PnL", it is **beats buy-and-hold SPY and/or 60/40, risk-adjusted,
> after costs, on forward data** — the point the November-14 analysis missed and the user
> corrected. Probabilities are subjective, updated by forward data, and conditioned on the
> stated event (SubQ independent estimates in `../subq/factcheck.md`).

## The ranking (probability of reaching *certified* profitability within 2 years, with lower permanent-loss risk)

| # | Class | P(2y) | Required style | Biggest structural obstacle | Plan file |
|---|---|---|---|---|---|
| 1 | **MUTUAL FUNDS + ETF** (allocation sleeve) | 60-70%* | monthly / long-term | infrastructure (NAV cache, PIT universe) — buildable | `mutual_funds.md`, `etf.md` |
| 2 | **EQUITY** (closed as edge; one new pre-registered trial) | 25-35% | swing (1-5d) | benchmark bar: must beat SPY, not zero | `equity.md` |
| 3 | **COMMODITY/FUTURES** (low-freq CTA) | 25-35% | position (weeks-months) | execution/roll costs + thin per-instrument n | `commodity_futures.md` |
| 4 | **BOND** (accumulate n first) | 15-25% | long-term | infrastructure/coverage (n=18-35 vs floor 100) | `bond.md` |
| 5 | **CRYPTO** (conditional on fill fix) | 20-30% | position (1-5d) + swing | costs/fills (measured: 98.8% of class loss pre-fix) | `crypto.md` |
| 6 | **FOREX** (mutation-or-kill) | 10-20% | position | costs + no residual edge at retail size | `forex.md` |

\* event = "positive net return over 10y with MDD ≤20%" — NOT "beats SPY" (that's ~25-35%).
SubQ's skeptical view of the same event: 55-70% (kept visible, not averaged).

**Universal ranking rationale (grounded):** the classes with *existing* infrastructure and
measured cost margins rank above the ones whose obstacle is measurement itself. Mutual funds
rank #1 for *probability of positive returns with lower risk* precisely because the honest
answer is beta + cost discipline — which works without alpha — while everything below it
requires proving alpha the system has never proven.

## Benchmark framing (the correction the user demanded)

Every plan's certification gate includes **all three**:
1. **Absolute:** net expectancy > 0, PF ≥ gate, n ≥ floor (Wilson CI on WR).
2. **vs buy-and-hold SPY:** excess Sharpe ≥ 0.2-0.3 over the forward window *or* comparable
   return with ≥30% lower max drawdown (Calmar basis). A strategy that returns less than
   SPY must justify itself on drawdown/vol reduction — otherwise hold SPY.
3. **vs 60/40:** the realistic alternative for capital that can't sit in equities —
   must beat it on Calmar to deserve the operational complexity.

SubQ's independent bar: ~30-36 months forward (confidence 0.17), pre-registered combo gate
(0.63). Adopt: **minimum 24 months, target 30, pre-registered, kill criteria attached.**

## Order of operations (applies to all classes)

1. Measurement truth (QA_PLAN gates) — a class cannot pass a gate measured by broken PnL.
2. Fill/cost model per class (crypto done; others via `stop_fill_replay` + broker data).
3. ONE pre-registered hypothesis per class (trial ID counted in the multiple-testing budget).
4. Split-sample + walk-forward, then **forward paper-trade ≥24 months** at stated costs.
5. Certification (`final_v4/inspect-wt/01_plan/PLAN_FINAL.md` Phase 4) → capital.
6. Parallel: the allocation sleeve (this folder's #1) deploys under its own, weaker-but-honest
   gate because it is beta capture — it does not need alpha to be the right default.
