# Money-ready: current state, timeline, and the worst-case plan (2026-11-19)

Every number here is reproducible from the live payload snapshot `2026-11-19T04:04:16.807952+00:00`
and the audit3 ledger built from it.

## 1. Where the book actually stands

| Fact | Value |
|---|---|
| Closed picks in existence | 16,330 |
| Rows audit3 scores | 3,500 (21.4% of the book) |
| PROVEN_T2 cells | 0 |
| CANDIDATE cells | 1 |
| KILL cells / KILL classes | 10 / 2 |
| MONEY_READY classes | 0 of 10 |
| Pre-registered pods | 1 (`POD-EQUITY-BREAKOUT`); 1 `post_hoc`, 1 `declined` |
| Pod-1 resolved rows in the payload | 364 over 265 days |

Two facts decide everything: **nothing is money-ready**, and the one pre-registered
pod has no forward clock. `POD-EQUITY-BREAKOUT`'s strategies exist in the book
(`adx-trend-scout`, `donchian-stock-breakout`, `rs-breakout-scout`, `vol-contraction-scout`) and audit3 scores its EQUITY cells, but a pre-registration is a
promise, not a track record. Until confirmed rows accrue under it, the promotion
path has nothing to graduate.

## 2. What is scheduled — and which part can produce an edge

| Cadence | What runs | Can it produce an edge? |
|---|---|---|
| hourly :10 | `audit-dashboard.yml` rebuilds the payload | No — it re-reports existing rows |
| 6-hourly :23 | `audit3-ledger.yml` re-scores, arms the denylist, asserts health | No — same rows, better statistics |
| hourly | `db-freshness-guardian.yml` | No — it only detects staleness |
| daily | `cross-db-audit.yml` | No — it checks key consistency |
| **per pod** | **forward clock (not built yet)** | **Yes — this is the only one** |

The schedule you see is maintenance. None of it can promote a strategy, by design:
the gates are expectancy-primary, the multiplicity families are split, and only a
pre-registered pod can reach PROVEN_T2.

## 3. Timeline, from the measured emission rate

Pod-1's strategies resolved **364 rows over 265 days** —
about **41.2 rows per 30 days**. At that historical rate the
confirmation floor takes roughly **73 days** of continued
emission, before the forward clock itself starts.

Then a pod must clear, in the confirmatory namespace only:

1. **n >= 100** forward trades
2. **net CI lower bound > 0 at 2x measured slippage**
3. **IR >= 0.5 versus SPY at matched exposure**
4. **a 90-day forward clock**, with kill checks at day 30 and day 60 on CI-LB <= 0
5. **BH q <= 0.10** in the confirmatory family and **DSR >= 0.95**

So the best case is roughly **5.4 months from today** (73 days
of emission plus a 90-day clock), and only on the optimistic branch where rows keep
arriving and net CI stays positive at double cost. I cannot give you a date on
which picks become money-ready, because the clock depends on a forward ledger that
does not exist yet. What can be promised is the opposite: no strategy reaches
MONEY_READY without clearing those gates, and the current answer is 0 of 10.

The only thing that would shorten it is a pod already clearing the gates on existing
cells. That set is empty: 0 PROVEN, and the single CANDIDATE
(`luxalgo_confluence` SHORT, n=476, net +0.72%/trade)
belongs to a `post_hoc` pod that cannot confer confirmatory status.

## 4. Worst case: still not on track at day 90

**Decision rule, written now so it is not negotiated later.** If at day 90 no pod
shows a positive net CI lower bound at 2x measured slippage and IR >= 0.5, the
finding is *no deployable edge on the available data*. That is a successful result
of the programme: it is citable, it stops the spending, and it protects capital.

In order:

1. **Freeze, do not delete.** Keep audit3, the denylist and the harness — they are
   the part that stops the next round of self-deception.
2. **Write the negative result** into `reports/` with the exact cells, their n and
   the cost model used, so someone else can check it.
3. **Retire the satellite budget.** Move it to the beta core; a benchmark-tracking
   portfolio at <= 0.20% fees beats an unproven sleeve.
4. **Register no new pods** until a falsifier in section 6 changes.

### Methodology I would run

Each step can invalidate the one after it, so the order matters:

1. **Re-derive the denominator** (`alpha_engine/resolved_closed_view.py`). If the
   rows judged are not the rows traded, nothing downstream counts.
2. **Separate backtest n from realised n.** The most expensive error in this repo:
   `crypto_liquidity_wick_reversal_v1` was cited at n=4,904 while its realised
   cohort was n=43 at +0.15%/trade — below round-trip cost.
3. **Selection alpha against matched exposure.** A long book that beat nothing in a
   rising tape has no skill. It is the only beta-separation metric available, and
   without DB credentials it still reports `not available`.
4. **Cost stress at 2x measured.** ETF's measured slippage is 234.05 percent
   of its per-trade PnL; a cell that survives only one cost assumption is an
   assumption, not an edge.
5. **Multiplicity.** Confirmatory family only, BH at q <= 0.10, and every rehab
   variant must inherit its parent's cumulative trial count.
6. **Pre-register, then look.** Rule M-107. Anything found after the look is
   discovery and cannot promote.

## 5. Files and tables to review

**Artifacts**

* `audit_dashboard/data/dashboard_data.json` — `picks.recent_closed`,
  `slippage_validation`, `money_ready_verdicts`, `resolved_closed_picks_net`
* `audit_dashboard/data/audit3_ledger.json` — cells, verdicts, `coverage.denominator`
* `audit_dashboard/data/resolved_closed_picks_net.json` — the canonical rows
* `reports/audit3_confirmatory.json` — pods and their status
* `reports/hypothesis_registry.json` — pre-registrations and verdicts
* `reports/benchmark_ledger_proof*.json` — paired bootstrap versus benchmark
* `config/per_class_cost_gate.json`, `alpha_engine/data/pf_registry.json`,
  `alpha_engine/data/honest_kill_switch.json`
* `docs/*_PROTOCOL.md` — the rules being claimed

**Database** (`ejaguiar1_stocks` unless noted)

| Table | Why it matters |
|---|---|
| `trading_picks` | canonical rows; check status vs pnl sign coherence |
| `at_pick_outcomes` | resolutions; join to picks for realised n |
| `at_signal_outcomes` | the honest lane: `intrabar_status`, `intrabar_pnl_pct`, `intrabar_resolved_at` |
| `bt_backtest_trades` | backtest evidence; never count as realised |
| `at_strategy_symbol_performance` | per strategy x symbol realised stats |
| `algorithm_performance`, `algorithm_rolling_perf` | stale since Feb/Apr — verify before quoting |
| `portfolio_snapshots` | frozen since March; portfolio Sharpe claims are suspect |
| `ejaguiar1_backtests` | backtest run metadata |
| `ejaguiar1_backups` | recovery slices before any mutation |

The queries that decide it: realised n per strategy x class where
`intrabar_resolved_at IS NOT NULL`; the same restricted to forward rows only; and
per-strategy intrabar net versus the payload's measured slippage.

## 6. What would change the answer

* A pod clearing net CI > 0 at 2x cost with IR >= 0.5 on 100+ confirmed rows.
* Selection alpha positive in two regimes (needs the DB price tables).
* A class whose measured slippage falls below about 25 percent of per-trade PnL
  (ETF at 234.05 percent can only ever work at monthly cadence).
* A pre-registered hypothesis with an economic reason **and** a counterparty losing
  money — not merely a decorrelated equity curve.

Absent those, the action stays the same: hold the beta core, keep the satellite
starved, and let the clock decide.

