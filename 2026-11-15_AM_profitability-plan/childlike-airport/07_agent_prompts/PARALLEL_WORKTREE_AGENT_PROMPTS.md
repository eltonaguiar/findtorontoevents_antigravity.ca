# 07 — Prompts for Parallel AI Coding Agents (Worktrees / Machines)

**Purpose:** narrow, falsifiable missions to find (or rule out) *real*, repeatable profitability per asset class — especially the top 1–2. Optimized for parallel execution.

## Global non-negotiables (prepend to every prompt)
- **No profitability claims** without: canonical reconciled data; net-of-all-costs (fees, spread, slippage, funding, roll, borrow, taxes/turnover); benchmark-relative results; leak-safe design (no look-ahead; next-bar/intrabar/NAV realism); gap-aware fills; effective-N/multiple-testing controls (DSR/PBO/trial count); stability across regimes/subperiods; and **forward paper/shadow** evidence on live marks.
- **Benchmarks mandatory (beating 0% is not enough):** equity/ETF alpha vs **SPY/total-market buy-and-hold (total return)** risk-matched, net; cash hurdle **T-bills/SGOV-like**; allocations vs matched blend (e.g. 60/40). Active strategies must beat the relevant buy-and-hold benchmark on a net, risk-adjusted basis.
- **Data truth first:** recompute PnL from verified marks; disposition every 0%/null/blank for open & recently-closed (≤30d, flag ≤7d) as `VALIDATED_ZERO|VALIDATED_NONZERO|SUSPECT_ZERO_FLAT_BUG|SUSPECT_STALE_OR_UNQUOTED|SUSPECT_BAD_REFERENCE|INSUFFICIENT_DATA`. No silent coercion.
- **Output contract:** (a) pre-registered hypothesis/rules/params, (b) cohort/hash/filters, (c) gross & net metrics (PF, WR, expectancy, Sharpe/Sortino/Calmar, MDD, CVaR, CAGR), (d) n/effective-N & concentration, (e) costs/slippage/fill assumptions, (f) benchmark comparison & alpha/beta, (g) OOS/walk-forward + regimes/subperiods, (h) DSR/PBO/trial accounting & sensitivity, (i) verdict `PROMOTE_PAPER | HOLD | KILL` + falsification.
- **Safety:** default `sizing_allowed=false`. No capital deployment, no force-push, no edits to others’ deliverables, no printing/committing secrets (`dbpasses.txt`). SubQ is decision support only — fact-check against primary data/principles.
- **Reality:** no proven profitable class today; prioritize falsification and simple, liquid, low-turnover ideas.

## Prompts

### 0 — Measurement & 0%/blank truth (P0, `wt-measurement`)
Build a trustworthy canonical cohort. Recompute net PnL from verified marks; disposition 0%/blanks; audit leakage, fill realism (intrabar/next-bar/gap-aware), tz/calendar/roll, provenance/freshness, dupes. Deliver reconciliation + machine-readable dispositions and “trusted cohort” spec.

### 1 — Low-cost ETF/MF baseline & TAA (`wt-beta-core`)
Prove best risk-managed baseline (beta/smart-beta), not alpha. (A) passive buy-and-hold/rebalance (ultra-low ER, $0-min/no-load, next-NAV aware) and (B) simple TAA/dual-momentum on liquid ETFs. Net-of-fee vs SPY/60-40/T-bills: CAGR, vol, Sharpe/Sortino/Calmar, MDD, CVaR, turnover, subperiods. Walk-forward + paper-forward plan. Label beta vs alpha.

### 2 — EQUITY vs SPY pre-registered alpha (`wt-equity-spy`)
1–2 simple liquid hypotheses, pre-registered. Net-of-cost vs **SPY total return** (risk-matched): alpha/beta, risk metrics, expectancy, capacity, regime stability, DSR/PBO. Paper-forward spec only if passing. Kill if beta-only/cost-erased/unstable.

### 3 — CRYPTO narrow sleeves (`wt-crypto-sleeves`, post-integrity)
1–2 candidates (e.g. diversified TSMOM/vol-targeted trend or regime-filtered MR core, liquid majors). Full costs+funding, gap-aware fills. Benchmark vs B&H and risk-matched; DSR/PBO, concentration. No scalping without intrabar proof. Paper-forward + kill rules.

### 4 — COMMODITY/FUTURES (`wt-commodity-futures`)
Clean contract-aware data/rolls/marks/costs. Test diversified TSMOM/breakout or carry net-of-costs vs cash/T-bill. Kill on mark ambiguity or negative net expectancy.

### 5 — FOREX mutation-or-kill (`wt-forex`)
One pre-registered liquid-major test net-of-spread/roll. No stable net benchmark-relative edge across regimes ⇒ KILL/BLOCK.

### 6 — BOND ballast/overlay (`wt-bond`)
Validate marks/feeds; duration/rate-regime. Allocation role net/risk-adjusted vs bond/T-bill benchmarks. Kill predictive claims lacking data.

### 7 — Prediction markets Kalshi/Polymarket (`wt-prediction-markets`)
Timestamped, net, capacity-aware scorecard (not copy bot). Reconstruct signal-vs-executable, fees/spread/limits, resolution, full PnL; test latency/adverse selection and calibration (Brier) vs baselines. Explain structural failures (zero-sum minus fees, bot dominance, adverse selection, late fills, size/survivorship bias, missing hedges, resolution/model risk, non-stationarity, copy-fidelity errors) and what would evidence real edge.

### 8 — Statistical validity & overfit auditor (`wt-stats-audit`)
Independently re-derive “winners”: n/effective-N, leakage, benchmark, costs, fills; DSR (true trials), PBO/CSCV, stability, sensitivity. Verdict `VALIDATED|INCONCLUSIVE|REFUTED` with reproducible code.

### 9 — Portfolio, risk & paper-trading harness (`wt-risk-paper`)
Verify TWR, drawdown/CVaR, exposure/concentration, benchmark-relative reporting. Enforce risk/kill-switches (per-trade, daily/weekly/monthly DD, staleness/recon breaks, leverage/capacity). Run paper-forward ledger with weekly scorecards.

## Coordination
Run 0 and 8 early; gate others on trusted cohort. One hypothesis family per worktree; rotate out after 2–3 null cycles. Favor simple, liquid, low-turnover ideas.
