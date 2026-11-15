# Algorithm Specifications — Per Asset Class

**Package:** WIRED_IN/2026-11-15_0135/inspect-wt
**Author:** inspect-wt (worktree `.inspect-wt`)
**Date:** 2026-11-15
**Companion:** `final_v4/inspect-wt/03_risk_management/backtest_rotation.py` (pre-registered sleeve spec),
`final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py` (variant-C walk-forward)

---

## Overview

Two algorithm families survive all audits. Everything else is either measurement infrastructure
or eliminated (see `../elimination_rationale/`):

- **Family A — allocation sleeve (no alpha required):** monthly momentum rotation across
  asset-class proxies. Deployable in MF/ETF form today; bond sleeve reuses the same engine.
- **Family B — strategy selection (the proven procedure):** variant C — monthly reselection of
  the system's own strategies by trailing profit factor. This is an *algorithm over algorithms*,
  and it is the only edge claim in the repo that beats a randomization null after Bonferroni
  correction.

---

## 1. MUTUAL FUNDS / ETF — allocation sleeve (primary pick)

**Algorithm:** monthly momentum rotation, dual-momentum (GTAA-style, Faber/acceleration family).

- **Universe:** `SPY EFA EEM TLT IEF GLD VNQ DBC QQQ IWM` (AGG reserved for the 60/40 bench).
  For the MF share-class deployment: US total / intl / EM / short-duration / TIP-class,
  ER ≤ 0.20% screen, share-class dedup, point-in-time universe.
- **Signal:** 12-1 trailing total return (`close[t-13] → close[t-1]`, no lookahead).
- **Filter (absolute/dual momentum):** hold an asset only if its 12-1 return > rf 2.5%/yr;
  else that slot earns cash.
- **Weights:** inverse trailing 12-month vol (window ending t-1), normalized across selected
  assets, 50% position cap, remainder in cash at rf.
- **Costs:** 0.05% one-way on traded notional; MF variant adds 0.15%/yr expense drag
  `(1-0.0015)^(1/12)`.
- **Frequency:** monthly (21 trading days); rebalance at month close.
- **Overlays (tested, honest):** 12% annual vol target = **neutral** (v2: Sharpe 0.53→0.59,
  kept as option); 15% portfolio DD-stop = **REJECTED** (v3: Sharpe 0.53→0.27, whipsaw —
  reported like the peers' failed COT test); absolute-momentum filter = **KEEP** (it is the
  core of v1).
- **Stage:** research-proven, forward-trackable. Gate to capital: net Sharpe ≥ 0.7,
  MDD ≤ 20%, Calmar ≥ 60/40's Calmar, forward paper ≥ 3 monthly rebalances, then tranched
  deployment. Kill: sleeve MDD > 20% intracycle or 3 consecutive months negative excess
  vs 60/40 → fall back to plain 60/40.

## 2. EQUITY — variant-C host + one pre-registered trial

**Algorithm B (running, this is where variant C actually trades):**

- Each month, using **only prior-month data**: group closed trades by `strategy`; keep
  strategies with ≥20 training trades; rank by training profit factor; take the **top 6 with
  PF > 1.3**; trade those 6 strategies next month. No re-tuning, ever — the rule was
  pre-specified before seeing its result.
- Live walk-forward result (Apr→Nov 2026): n=237, WR 47.3%, PF 1.26, +98.7pp, randomization
  0/800 → p<0.0013, Bonferroni (4 variants) survives at p<0.005. Concentrated in
  **ETF n=120 PF 1.21 (+26.5pp)** and **EQUITY n=112 PF 1.30 (+73.1pp)** — crypto naturally
  excluded by the training-PF gate.
- **Sizing:** full Kelly 9.86% → **¼ Kelly 2.46%/trade**; kill criteria: two consecutive
  PF<0.5 months or 3-month rolling PF<1.0; cost guard: halt if realized costs > 0.416%/trade
  (the measured breakeven buffer).

**Algorithm (single new trial, pre-registered):** RSI(2)-style short mean reversion on
S&P-500 constituents, hold 1–5 days, entered at the signal close (never next open),
0.10% round-trip cost, point-in-time constituent list (survivorship = fake alpha).
Gate: net PF ≥ 1.15 ∧ excess Sharpe vs SPY ≥ 0.2 ∧ n ≥ 500 ∧ Wilson CI WR > 50% ∧ both
halves PF > 1.0. **Equity is otherwise CLOSED as a source of edge** (#773 `NO_ALPHA_BETA`:
t=1.05, median pick −0.57% vs SPY, 54% underperform) — reopening requires this new trial ID,
not a re-run with different thresholds.

## 3. CRYPTO — conditional vol-targeted trend (the only remaining alpha candidate)

- **Universe:** BTC/ETH only (liquid, dual-sourced Binance+KuCoin).
- **Signal:** trend on monthly re-rank, position horizon 1–5 days, vol-targeted sizing,
  0.15% round-trip cost.
- **Pre-conditions (all mandatory):** fill fidelity first — every strategy's claimed edge must
  exceed 2× its measured slippage (`tools/stop_fill_replay.py --truncate-at-exit` per
  strategy); **kill CRYPTO SWING emission** (n=243, PF 0.457, −328.6pp — peer-unanimous P0);
  route `kimi_riseoftheclaw` through the intrabar resolver.
- **Gate:** forward PF ≥ 1.3, WR ≥ 55%, n ≥ 100, dual-source, **and** beat buy-and-hold BTC
  risk-adjusted (Sharpe basis — the TSMOM objection: beating zero ≠ beating holding BTC).
- **Honest state:** fill fix bought +67.5pp (PF 0.768 → ~0.80), not breakeven. Conditional,
  not eliminated — it is the only class with API-native execution, free dual-source data and
  an existing fill model.

## 4. COMMODITY / FUTURES — CTA trend (research-only, feed-blocked)

- **Algorithm (pre-registered):** one rule for all instruments — Donchian/200-day hybrid
  exit, monthly rebalance, 8–12 liquid futures (ES NQ CL GC ZN 6E ZC HG class), **costs from
  actual roll schedules** (back-adjusted contracts; continuous contracts hide roll cost —
  the #1 reason retail futures backtests lie).
- **Gate:** net PF ≥ 1.3, n ≥ 100 across instruments, beats BCOM on Calmar, Sharpe ≥ 0.6 net,
  both-halves PF > 1.0; 2015–2020 CTA-decay window reported as a standalone regime.
- **Stage:** vetoed for emission (no real feed; 422% cost/PnL ratio in the focus screen);
  COT feature test **failed 4/4** and may not be silently re-tested. Historical PF ~1.78/WR ~47%
  is coherent with trend-following signature but is pre-cost, pre-feed — not evidence.

## 5. BOND — inherits the sleeve engine (accumulating n)

- **Algorithm (option 2 of 3, pre-selected):** ETF/fund rotation — AGG/TLT/IEF/SHY/TIP
  relative strength at monthly frequency with the same absolute-momentum filter as Family A.
  (Option 1 duration/curve stance and option 3 credit-spread timing were rejected for low
  n-accrual and extra data dependencies.)
- **Gate:** beat AGG buy-and-hold AND T-bill net; MDD ≤ 6% sleeve-level; excess vs AGG
  t-stat ≥ 1.6. **Honest near-term answer:** hold low-cost intermediate bonds as ballast —
  carry is already profitable without prediction; the system's bond job must beat *that*.
- **Stage:** n=18–35 vs floor 100 (needs ~3–5 years at 12 decisions/yr for trade-level n, or
  a pre-registered decision-level bootstrap gate). Infrastructure problem, not signal problem.

## 6. FOREX — kill-or-cure (at most two mutations)

- **Mutation 1:** London/NY-session entries only, daily-horizon trend filter, carry proxy as
  feature, cost model from REAL per-pair per-session broker spreads (historically modeled ~0 —
  the core defect behind PF 0.27 on honest n).
- **Mutation 2 (only if 1 shows life):** RSI(2)-class mean reversion at session extremes on
  EURUSD/GBPUSD/USDJPY only during high-liquidity hours.
- **Gate:** net PF ≥ 1.3, n ≥ 150, both-halves PF > 1.0, dual source, benchmark = cash +
  spot-futures carry proxy.
- **Pre-registered kill:** both mutations fail at n → mark class `KILLED — no edge at retail
  cost structure` on the dashboard. A documented kill is a deliverable; keeping a dead class
  alive pollutes the multiple-testing count.

---

## Cross-cutting rules (apply to every class)

1. **Measurement truth first:** no gate may be computed on unverified PnL (QA_PLAN:
   PnL=0% independent repricing, blank-field quarantine, exit replay). `resolution_method`
   must be recorded intrabar-vs-nominal before any PF is certifiable.
2. **One pre-registered hypothesis per class**, trial ID counted in the multiple-testing budget
   (B8 discipline); no threshold shopping after a miss.
3. **Benchmark-relative certification:** absolute gate AND vs SPY (excess Sharpe ≥ 0.2 or equal
   return with ≥30% lower MDD) AND vs 60/40 (Calmar) — a strategy that returns less than SPY
   must justify itself on drawdown reduction, otherwise hold SPY.
4. **Forward paper ≥ 24 months** at stated costs (SubQ-confirmed bar: 30–36 months, confidence
   0.17; we adopt min 24, target 30), kill criteria attached, all certification CI-green.
