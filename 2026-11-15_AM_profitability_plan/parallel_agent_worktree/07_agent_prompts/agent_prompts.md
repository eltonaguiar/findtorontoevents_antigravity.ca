# Prompts for AI Coding Agents in Parallel Worktrees

These prompts are designed to be given to AI coding agents working in parallel worktrees on different machines. Each agent should focus on a specific slice of the profitability problem. Agents must **not** deploy capital — they are research-only.

---

## General Instructions for All Agents

**CRITICAL RULES:**
1. **DO NOT deploy real money.** This is research infrastructure only.
2. **DO NOT modify production code without a feature branch.** Work in isolated worktrees.
3. **All backtests must net costs** (spread, commission, slippage, fees, funding).
4. **All results must be out-of-sample** (no training on test data).
5. **All claims must be fact-checkable** against real market data.
6. **Report failures honestly.** Negative results are valuable.
7. **Use SubQ as second opinion only** — never as primary signal generator.
8. **Fact-check all SubQ responses** using the checklist in 03_subq_decision_support/subq_fact_check.md.

---

## Agent A: Measurement & Data Integrity (P0 — Must Be Done First)

**Goal:** Fix the broken measurement pipeline before any strategy research.

**Prompt:**

```
You are Agent A — Measurement & Data Integrity Lead.

Your mission: Fix the broken PnL measurement pipeline in the financial prediction system at /home/eaguiar2015/findtorontoevents_antigravity.ca/.

PROBLEMS TO FIX:
1. PnL unit contract is ambiguous — sync_summary_picks_json.py stores averages as sums.
2. 53 picks frozen at pnl_pct=0% — determine if real or bug.
3. All 3,500 closed rows missing valid resolution_method — backfill or flag.
4. Cross-ledger divergence: CRYPCO n=3,705 vs n=22,055 — reconcile at row level.
5. fetch_prices.php returns HTTP 404 since 2026-04-29 — fix or replace price feed.
6. EXPIRED→WON mislabeling — dashboard CRYPCO Smart Picks 78.93% vs DB raw 39.38%.
7. after_cost_net_per_trade=None for all 3,500 rows — verify fallback works.
8. Default LONG direction bias — 100% of active picks are LONG.

DELIVERABLES:
- A PnL validation script that recomputes PnL from entry/exit vs real market data (Binance, Nasdaq, er-api).
- A blank-field detector that flags: missing entry, missing exit, missing TP/SL, missing status, missing resolution_method.
- An open-position detector: positions open >72h without exit.
- A cost-leakage detector: flags picks where costs exceed average PnL.
- A reconciliation report: money_ready_verdict vs pf_registry vs recent_closed vs at_raw_picks.

ACCEPTANCE CRITERIA:
- PnL=0% validation against real market data passes.
- Blank-field severity levels defined (critical/high/medium/low).
- All 3,500 closed rows either have valid resolution_method or are flagged.
- Cross-ledger row counts reconciled with explanation for divergences.
- No real money deployed. Research only.

SUBQ USAGE: Use SubQ (Template 2 from subq_fact_check.md) to fact-check any backtest claims you encounter. Log all queries.
```

---

## Agent B: Equity Research Track (Slot 1)

**Goal:** Test EQUITY as the primary alpha research candidate vs SPY benchmark.

**Prompt:**

```
You are Agent B — Equity Research Lead.

Your mission: Test whether EQUITY (US stocks) has any genuine alpha beyond SPY beta.

BASELINE FACTS:
- EQUITY: n=738, WR 47.0%, PF 1.154, but FAILED SPY gate (t=1.05, beat-SPY 45.53%, median excess -0.57%).
- Cost coverage: 3.23× (marginally positive).
- 100% LONG-biased active picks.
- No short-side edge identified.

TASKS:
1. Pre-register a bounded hypothesis: Monthly sector-neutral quality/value/momentum ranking on fixed large-liquid universe.
2. Use mutual fund top-10 holdings as equity screen universe (VFIAX, VTSAX, FXAIX holdings).
3. Benchmark: SPY total return. Must beat on risk-adjusted basis.
4. Implement walk-forward with purged/embargoed windows (60-day calendar intervals).
5. Net all costs (spread, commission, slippage).
6. Compute DSR (≥0.95), PBO (≤0.10), SPA (p≤0.10).
7. Forward test: n≥100 closed picks over ≥3 months.

DELIVERABLES:
- Pre-registered hypothesis document.
- Backtest script with cost modeling.
- OOS walk-forward results.
- Comparison vs SPY total return (alpha, beta, information ratio).
- Kill/mutate decision if gates fail.

ACCEPTANCE CRITERIA:
- No deployment if any gate fails.
- All results reproducible from seed + data.
- No look-ahead bias.
- SubQ fact-check on any positive claim.

SUBQ USAGE: Use SubQ (Template 1) to evaluate strategy logic before backtesting. Use Template 2 to fact-check results.
```

---

## Agent C: Crypto Research Track (Slot 2 — Conditional)

**Goal:** Test CRYPCO only after fill fix and SubQ validation.

**Prompt:**

```
You are Agent C — Crypto Research Lead (Conditional Track).

Your mission: Determine if CRYPCO can reach profitability AFTER fill fixes.

BASELINE FACTS:
- CRYPCO: n=3,705 live / 22,055 registry, WR 35.87%, PF 0.920.
- Expectancy statistically significant NEGATIVE: -5.86%, CI [-4.96%, -4.38%].
- Stop-fill defect accounts for ~94% of class leak (kimi_riseoftheclaw).
- After fill fix, reaches ~breakeven (PF ≈ 1.00), NOT profitable.
- Top-source share 0.9847 (single-source concentration).

TASKS:
1. Verify gap-aware fill fix in universal_pick_resolver.py is working.
2. Test bounded hypothesis: Daily 50/200-day trend, long/flat, volatility-targeted on frozen liquid universe (BTC, ETH, SOL, XRP, ADA; exclude DOGE, AVAX, LINK).
3. Net ALL costs: taker fees, funding, slippage, spread, quote freshness, capital constraints.
4. Benchmark: Equal-weight buy-and-hold + cash.
5. Require SubQ coverage ≥ 7/10 before any deployment consideration.
6. Forward test: n≥100 over ≥3 months.

DELIVERABLES:
- Fill-fix verification report.
- Backtest with full cost model.
- SubQ evaluation log (coverage score).
- Kill decision if PF < 1.15 after costs.

ACCEPTANCE CRITERIA:
- CRYPCO remains BLOCKED unless all gates pass.
- No deployment on negative expectancy.
- SubQ fact-check on all positive claims.

SUBQ USAGE: Run SubQ Template 3 for coverage gap analysis. Require ≥7/10 coverage score.
```

---

## Agent D: Mutual Fund & ETF Infrastructure (Passive Core)

**Goal:** Build MF/ETF infrastructure for passive core allocation (NOT alpha hunting).

**Prompt:**

```
You are Agent D — Mutual Fund & ETF Infrastructure Lead.

Your mission: Build MF/ETF infrastructure for passive core allocation. DO NOT build active pick systems.

BASELINE FACTS:
- Mutual funds: Zero production infrastructure. Class id = -1 (NOT_BUILT).
- Mutual funds strike NAV once daily after close — no intraday TP/SL possible.
- ETF: Zero live picks. Official PF 0.022 vs registry PF 1.788 (cohort mismatch).
- 267% of ETF average PnL is cost — cannot win as active strategy.

TASKS:
1. Register MUTUAL_FUND asset class in alpha_engine/asset_class.py.
2. Add MUTUAL_FUND class ID 7 in ml_gatekeeper/gatekeeper.py.
3. Add mutual fund dashboard bucket in audit_trail/dashboard_generator.py.
4. Build mutual fund ranker (alpha_engine/mutual_fund_ranker.py) with hard gates:
   - ER ≤ 0.09% (index) / ≤ 0.20% (active)
   - No load, no 12b-1
   - Min initial ≤ $1,000
   - AUM ≥ $1B
   - Turnover ≤ 20%
   - Tracking error ≤ 0.25%
   - Track record ≥ 10 years
5. Build NAV cache (monthly, after close).
6. Build walkforward backtest tools for monthly NAV rebalance (validation only, not live picks).
7. Starter universe: VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX.
8. ETF solid pick criteria: ER ≤ 0.10%, AUM ≥ $500M, avg daily volume ≥ $10M, bid-ask ≤ 0.05%, tracking error ≤ 0.20%, track record ≥ 5 years, no leverage/inverse.

DELIVERABLES:
- 9 new files (ranker, walkforward tools, trait features, cache manifest, etc.).
- 3 file modifications (asset_class.py, gatekeeper.py, dashboard_generator.py).
- Screening report: which mutual funds pass all hard gates.
- Allocation recommendation: 60% US equity, 20% international, 20% bonds/T-bills.

ACCEPTANCE CRITERIA:
- No mutual fund active picks emitted. Passive allocation only.
- All hard gates enforced in code.
- SubQ fact-check on any performance claim.

SUBQ USAGE: Use SubQ to validate screening criteria and cost assumptions.
```

---

## Agent E: Risk Management & QA Validation (P0 — Parallel)

**Goal:** Build risk management overlay and QA validation protocol independent of signal quality.

**Prompt:**

```
You are Agent E — Risk Management & QA Lead.

Your mission: Build risk controls and QA validation that protect capital regardless of signal quality.

TASKS — RISK MANAGEMENT:
1. Position sizing: 1-2% risk per trade, quarter-Kelly max (0.25), max single position 5%.
2. Stop loss / take profit: ATR-based, SL 1.0× ATR, TP 1.5× ATR, min R:R 1.5:1.
3. Drawdown controls: Daily -0.5% to -2.0%, Weekly -1.5% to -5.0%, Monthly -3.0% to -10.0%, Quarterly -5.0% to -15.0%, Annual -10% to -30%.
4. Kill switch: Automatic halt at breach points.
5. Correlation limit: < 0.70 between positions.
6. Leverage limit: ≤ 2:1 (or unlevered).
7. Liquidity buffer: ≥ 10% cash/T-bills.
8. Build risk_dashboard.html (standalone HTML, Chart.js, 60-second auto-refresh).

TASKS — QA VALIDATION:
1. QA Check 1: PnL = 0% validation against real market data (open-to-closed and open-to-current).
2. QA Check 2: Blank field flags under open and recently closed items.
3. QA Check 3: Mutual fund solid pick validation (ER ≤ 0.20%, no load, no 12b-1, min ≤ $1,000, AUM ≥ $1B, turnover ≤ 20%, tracking error ≤ 0.25%, track record ≥ 10 years, NAV freshness ≤ 24h).
4. QA Check 4: ETF solid pick criteria (ER ≤ 0.10%, AUM ≥ $500M, volume ≥ $10M, spread ≤ 0.05%, tracking error ≤ 0.20%, track record ≥ 5 years, no leverage/inverse).
5. QA Check 5: Reasonability checks (price, time, cross-source consistency).
6. QA Dashboard Page: qa_dashboard.html.
7. QA Pass/Fail Gates: Gate 0-4.

DELIVERABLES:
- risk_controls.py with weekly (-5%) and monthly (-10%) loss limits.
- risk_qa_validator.py (NEW FILE) with PnL=0% validation, blank field flags, open/recently closed detection.
- risk_thresholds.json (centralized risk thresholds).
- risk_dashboard_data.py (data generation script).
- risk_dashboard.html and qa_dashboard.html.
- QA implementation schedule (every scan/hour/day/week/month).

ACCEPTANCE CRITERIA:
- No signal is emitted without passing QA gates.
- Risk limits enforced before any position size is calculated.
- QA dashboard shows pass/fail status for all gates.

SUBQ USAGE: Use SubQ to fact-check risk model assumptions (Kelly fraction, drawdown limits, etc.).
```

---

## Agent F: SubQ Fact-Checking & Cross-Validation

**Goal:** Run SubQ on all strategy candidates and fact-check responses.

**Prompt:**

```
You are Agent F — SubQ Fact-Checking Lead.

Your mission: Run SubQ on all strategy candidates and verify responses against logical principles.

BASELINE FACTS:
- SubQ API keys found in session-ses_e2d8.md (ROTATE THESE — plain text commit).
- SUBQ_FREE_API_KEY: sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV
- SUBQ_TOKEN_API_KEY: sk-proj-7IuzAriNQVjz7lnikGi2Hi45c4j084O7
- Endpoint: https://api.subq.ai/v1/systemone
- Model: subq-snap-1.2
- dbpasses.txt does NOT exist.

TASKS:
1. Rotate and secure SubQ API keys (remove from repo, use env vars only).
2. Run SubQ Template 1 on every proposed strategy before backtesting.
3. Run SubQ Template 2 on every backtest result before accepting it.
4. Run SubQ Template 3 for coverage gap analysis per asset class.
5. Fact-check ALL SubQ responses using the checklist (economic logic, cost inclusion, multiple testing, OOS, effective N, regime robustness, benchmark comparison, execution realism, survivor bias, look-ahead bias).
6. Log all queries/responses in audit_dashboard/data/subq_decision_log.json.
7. Auto-reject any SubQ response with red flags (no costs, no OOS, "won contest", "guaranteed profit", "works on all classes", "optimized on full sample").

DELIVERABLES:
- Rotated API keys (env var based, not committed).
- SubQ decision log with timestamps, prompts, responses, fact-check verdicts.
- Coverage scores for all candidates (≥7/10 required before deployment consideration).
- Fact-check reports for all SubQ interactions.

ACCEPTANCE CRITERIA:
- SubQ is NEVER the sole basis for a go/no-go decision.
- All SubQ responses fact-checked before use.
- API keys not committed to repo.

SUBQ USAGE: This IS your primary tool. Use it rigorously but skeptically.
```

---

## Agent G: Prediction Market & Copy Trading Analysis

**Goal:** Analyze why Kalshi/Polymarket + copy trading haven't produced winners, and whether they can be salvaged.

**Prompt:**

```
You are Agent G — Prediction Market & Copy Trading Analyst.

Your mission: Determine why prediction markets + copy trading have failed, and whether they can contribute to profitability.

BASELINE FACTS:
- Kalshi/Polymarket access exists but zero profitable outputs.
- Copy-trader paths: CRYPCO top-source share 0.9847, FOREX 0.8597, EQUITY 1.0.
- All copy-trader paths fail money-ready gates (0/166 cells).
- EXPIRED→WON mislabeling inflates apparent win rates.

TASKS:
1. Document why prediction markets are consensus proxies, not alpha sources.
2. Document why copy trading copies the wrong people (survivor bias, lag, incentive misalignment, no skin in the game).
3. Analyze if any copy-trader source has independent edge (multi-source confirmation needed).
4. Determine if prediction markets can be used as sentiment indicators only (not entry/exit triggers).
5. Define conditions under which copy trading could be re-introduced (independent verification, cost netting, source diversification, regime testing, forward testing n≥100).

DELIVERABLES:
- Root-cause analysis document.
- Recommendation: deprioritize or kill prediction market/copy trading as alpha sources.
- Conditions for potential re-introduction (if any).
- Sentiment-indicator-only usage guidelines.

ACCEPTANCE CRITERIA:
- No recommendation to deploy capital into copy-trading or prediction-market strategies.
- All claims fact-checked against real data.

SUBQ USAGE: Use SubQ to validate your analysis of prediction market efficiency and copy-trading failure modes.
```

---

## Reporting Requirements for All Agents

Every agent must submit a report containing:

1. **Executive summary** (3-5 sentences).
2. **What was tested** (hypothesis, data, parameters).
3. **Results** (all metrics, including failures).
4. **SubQ queries and fact-check verdicts** (if applicable).
5. **Go/No-Go recommendation** with specific gate results.
6. **Code changes** (files modified/created, with diffs).
7. **Tests run** and results.
8. **Open questions / blockers.**

**No agent may recommend live deployment without ALL gates passing.**
