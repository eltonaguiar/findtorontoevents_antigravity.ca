# Design Discussion — Which Elements Are Worth Keeping (2026-11-19)

**Author:** opencode (Beam Free)
**Date:** 2026-11-19
**Context:** Discussion on which design elements from /audit, /audit2, /audit3 and the various peer plans should be kept in the final design, and why.

---

## 1. Design elements worth KEEPING

### 1.1 audit3 kill tribunal (STRONG KEEP)

**What it is:** Per-cell net-expectancy bootstrap CI, BH multiple-testing correction, DSR overfit detection, 2× cost stress, split-half stability, max symbol/source share gates.

**Why keep:** This is the ONLY surface that scores closed picks against costs, corrects for multiplicity, enforces cost-stress, and refuses to promote on tiny n. Its 0 CANDIDATE / 0 PROVEN_T2 is a **feature**, not a bug — the pipeline is honest.

**Evidence:** 8,613 rows scored, 67 cells tested, 0 proven. Selection alpha is NEGATIVE (−0.128%). The system has negative selection skill. audit3 correctly identifies this.

**Peer validation (Buffy):** ENDORSED as "the decision surface for 'is there edge'."

### 1.2 audit2 candidate library (KEEP as doctrine, NOT as live evidence)

**What it is:** Doctrine page, pod registry, measures library, traps/graveyard, retired-with-reason, benchmarks.

**Why keep:** Correct measurement vocabulary (DSR, PBO, SPA, BH-FDR, selection alpha, intrabar first-touch, 2× cost stress). Useful graveyard (Connors RSI-2, SMC order blocks, meme ML, copy-trading wallets, COT shorts, KSS cointegration).

**Caveat:** Pod registry is hard-coded in `audit2.js` (static snapshot). Live half is the audit3 ledger. Cannot stand alone.

**Peer validation (Buffy):** ENDORSED as "doctrine + hypothesis library, NOT as live evidence."

### 1.3 Forward observations ledger (KEEP — the only path to PROVEN)

**What it is:** Append-only JSONL ledger with contract schema (id, hypothesis_id, opened_at, closed_at, symbol, asset_class, side, entry_px, exit_px, qty, fees, funding, slippage_bps, resolver_version, intrabar_first_touch, benchmark_leg_ret, regime_ok, created_at).

**Why keep:** This is the ONLY mechanism that can mint a PROVEN_T2 verdict from live data. Without it, audit3 can only re-score the past. The forward gate (n≥100, PF CI-LB>1.0, 100% intrabar) is the correct promotion mechanism.

**Current state:** 608 rows (430 H-119 + 177 EQUITY + 1 ETF). All pods at n<100. No promotions yet.

### 1.4 Cost model (KEEP, with harmonization)

**What it is:** `alpha_engine/cost_model.py` — EAGLE2 per-asset-class cost & slippage model. Execution cost + slippage in bps.

**Why keep:** Costs are the #1 reason strategies fail. The model is well-structured with per-class constants. But constants were inconsistent across 3 modules (cost_model, transaction_costs, forward_observations_ingest, audit3 ledger). Now harmonized to cost_model.py as single source of truth.

**Harmonized values:** CRYPTO 13 bps, EQUITY 7 bps, ETF 3 bps, FOREX 2 bps, COMMODITY 7 bps, FUTURES 5.5 bps, BOND 4.5 bps.

### 1.5 Selection alpha (KEEP — now implemented)

**What it is:** `alpha_engine/audit3_selection_alpha.py` — M1b: pick net return − direction-adjusted buy & hold over the same entry..exit window.

**Why keep:** This is the question that decides whether a strategy has skill. A +40% pick on a +60% symbol is a selection FAILURE. Win-rate tables can't see this.

**Result:** ALPHA −0.128% (pick +0.261% vs hold +0.389%). CRYPTO/LONG −0.525% (worst). Confirms negative selection skill.

### 1.6 Random-entry MC (KEEP — now wired)

**What it is:** `alpha_engine/benchmark_closed_ledger.py` — random-entry Monte-Carlo timing test. Under the null of no timing skill, would random entry have done as well?

**Why keep:** This is the timing-null companion report. A strategy that only looks good because it rode a bull market is not an edge. The MC test checks whether the entry timing itself has value.

**Result:** 170 ledgers, 4 pass at 95% (small n: 21-57). Wired into audit3 via --benchmark flag.

### 1.7 Sleeve reconciliation (KEEP — new, P0)

**What it is:** `tools/sleeve_reconciliation.py` — extracts top_sleeves from dashboard_data.json, checks against audit3 cells.

**Why keep:** Discovered that /audit top_sleeves (AuditEnsemble_LONG PF 155.85, CorrKama PF 111.81, non_crypto_consensus PF 9.68) are NOT in audit3 cells. All 10 sleeves are UNVERIFIED. 9/10 single-source. This is the most important finding for money-readiness.

### 1.8 Confidence recalibration (KEEP — new)

**What it is:** `alpha_engine/confidence_recalibrator.py` — shared utility that recalibrates raw confidence to calibrated values based on actual win rates.

**Why keep:** ML confidence is inverted (conf≥0.9 → 14.4% WR, conf 0.5-0.6 → 60.3% WR). This utility provides a single function any pick generator can call. Tested: all 7 test cases pass.

### 1.9 Mutual fund screener (KEEP — new)

**What it is:** `alpha_engine/mf_screener.py` + `mutual_fund_screener_runner.py` + weekly workflow. Hard gates: expense ratio ≤0.09% (index)/≤0.20% (active), no load, no 12b-1, AUM ≥$1B, turnover ≤20%, tracking error ≤0.25%, track record ≥10y.

**Why keep:** Mutual funds are the lowest-risk money-ready candidate. Professional management, diversification, regulation. 8/8 starter funds pass hard gates. This is the biggest untapped money-ready opportunity.

### 1.10 Bond screener (KEEP — new)

**What it is:** `alpha_engine/bond_screener.py` + weekly workflow. Duration + credit + real yield. Hard gates: expense ratio ≤0.10%, AUM ≥$1B, tracking error ≤0.25%, track record ≥10y, duration within ±2y of target.

**Why keep:** Bonds are a diversifier (low vol, low drawdown). Duration management is the key edge. 9/9 starter funds pass.

### 1.11 Commodity screener (KEEP — new)

**What it is:** `alpha_engine/commodity_screener.py` + weekly workflow. Term structure (backwardation/contango) + inventory + seasonality. Replaces falsified COT positioning.

**Why keep:** COT positioning was falsified (6.33× over-emission). Term structure (Gorton-Rouwenhorst 2006) is the most robust commodity signal. 9/9 pass.

### 1.12 Hypothesis normalization (KEEP — done)

**What it is:** Normalized 36 fragmented status strings to 12 canonical statuses.

**Why keep:** The fragmented vocabulary (PRE_REGISTERED vs PRE-REGISTERED, FORWARD OBSERVATION vs FORWARD_OBSERVATION) made automated gating impossible. Now clean.

---

## 2. Design elements worth DISCARDING

### 2.1 audit page headline metrics (DISCARD as evidence)

**Why:** The /audit page shows inflated CRYPTO nav surfaces (PF 9-18, WR 78-88%) dominated by `claude_gainer_st` picks with EXPIRED→WON mislabels. Raw equivalent WR=33%. The headline metrics are internally inconsistent (two PF/WR figures per class). The committed payload is 31 days stale.

**Keep as:** Inventory/pick feed only. Not as evidence.

### 2.2 COT positioning (DISCARD)

**Why:** FALSIFIED (6.33× over-emission: 38 raw signals from 6 unique CFTC release weeks). Now SHADOW_INSUFFICIENT_N, dsr=null.

### 2.3 15-minute ML strategies (DISCARD)

**Why:** 33 of 42 audited strategies are OVERFIT_LIKELY (DSR < 0.5). The 15m timeframe is overfit-bait. Pattern: `ml_enhanced_*_15m_*` family fails multiple-testing correction.

### 2.4 Post-hoc segment numbers (DISCARD as actionable)

**Why:** 82% WR / PF 11+ are post-hoc segment search (not actionable). Multiple-testing correction not applied. The implicit search space >50 cells means an 82% WR cell can arise from pure noise.

### 2.5 Winner-take-all ETF rotation on 3 assets (DISCARD)

**Why:** EdgeLab 2026 (21 years): rotation 10.9% CAGR OOS but Sharpe 0.70 vs equal-weight 0.96, MDD −33.6% vs −22.7%. "Beats buy-and-hold on raw return, loses on risk-adjusted." Inverse-vol weighting (Sharpe 1.03) mostly replaces momentum with diversification.

### 2.6 Canonical Magic Formula (EBIT/EV) (DISCARD)

**Why:** Blackburn & Cakici (2017, 23 markets): pure EBIT/EV beats canonical Magic Formula. Gross profit > EBIT for quality metric. Transaction costs (~100% annual turnover) can eliminate alpha entirely.

### 2.7 Piotroski F-Score as standalone (DISCARD)

**Why:** SledgeKey 2017-2026: Piotroski screen 9.52% vs S&P 500 15.28%, Sharpe 0.43 vs 0.81, MDD −48.9% vs −33.7%. Lost badly. But combined with Magic Formula + Sortino filter, edge recovers (+4.8% CAGR over IWM).

---

## 3. Design elements worth DEBATING

### 3.1 ETF TAA: drawdown-control vs return enhancement

**Buffy's finding (TAA lagged reproduction):** The 2026-07-04 "Sharpe 0.88 / −19%" was effectively same-close (lag0). Honest 1-day lag: 0.82 vs SPY 0.69, CAGR trails SPY in every cell (8.9 vs 10.8). 9m lookback is the lag-robust survivor (top4-9m: Sharpe 0.75 ~ SPY 0.72 at MDD −21.9 vs −50.8).

**My finding (Faber GTAA backtest):** Sharpe 0.915, MDD −20.5%, OOS Sharpe 1.13. CAGR 9.76% vs SPY 10.91%.

**Debate:** Is ETF TAA worth keeping? 
- **Pro:** Halves drawdown (−20.5% vs −50.8%). Sharpe 0.915 vs 0.777. OOS Sharpe 1.13 (improves out-of-sample). Simple, robust, 20-year evidence.
- **Con:** CAGR trails SPY in every cell (8.9 vs 10.8). The 0.88 Sharpe was a same-close artifact. 9m lookback is only ~SPY parity (0.75 vs 0.72).
- **Verdict:** KEEP as drawdown-control allocation, not return enhancement. For anyone who can stomach −50% DD, plain SPY/VOO is better. For everyone else, Faber GTAA is the right tool.

### 3.2 MES ORB: viable money-maker or overfit?

**My finding (ORB backtest):** 48 trades, WR 45.8%, PF 1.53, net +$683/60 days. Exit grid: 75 combos, best PF 2.155, best net $1,776/60 days. Volume filter +0.13 PF.

**Debate:** Is the ORB viable?
- **Pro:** Positive expectancy (PF 1.53-2.155). Volume filter confirmed to improve edge. Time stops are profitable. All 75 combos positive.
- **Con:** 48 trades over 60 days is small. Exit grid (75 combos) might be overfitting. Publication decay (26-58%) could reduce edge significantly. Commission drag is real ($1.50/trade).
- **Verdict:** KEEP as research/sandbox. Need 30-session paper trading + shadow mode before any live capital. The edge is promising but unproven.

### 3.3 Mutual funds: passive core or active management?

**My finding (mf_screener):** 8/8 starter funds pass hard gates (VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX). ER 0.03-0.09%, no load, no 12b-1, AUM ≥$1B.

**Debate:** Active or passive?
- **Pro (passive):** Lower cost (0.03-0.09% vs 0.20-0.50%), no manager risk, matches index. Lipper Leader + Morningstar Gold still favor low-cost index funds.
- **Pro (active):** Professional stock-picking, potential outperformance. But most active funds fail to beat index after fees.
- **Verdict:** KEEP passive. The evidence overwhelmingly favors low-cost index funds. Active management is a lottery. Use mf_screener for passive core only.

### 3.4 Penny stocks vs mid-tier vs large-cap

**Debate:** Which equity tier for money-making?
- **Penny stocks (<$5):** DO NOT TRADE. Manipulation, wide spreads, no fundamentals. 90%+ lose money.
- **Mid-tier ($5-$50):** Only if value-screened (Magic Formula × Piotroski × Acquirer's). Even then, expect risk-adjusted not raw outperformance. Single-name risk is real.
- **Large-cap ($50+):** Safest. Value + quality + momentum screening. But expect to trail index on raw return.
- **Verdict:** KEEP large-cap value screening. DISCARD penny stocks. Mid-tier only with strict value screen.

---

## 4. Peer feedback incorporated

### From Buffy (COMS message)
- TAA lagged reproduction: honest 1-day lag Sharpe 0.82 vs SPY 0.69. CAGR trails SPY in every cell.
- 9m lookback is lag-robust survivor (top4-9m: Sharpe 0.75 ~ SPY 0.72).
- 11-sector Sharpe 0.66 is a different universe (SPDR sectors).
- Plain SPY/VOO for anyone who can stomach −50% DD.

### From Copilot (plan)
- $2,000 recommendation: ETF for real money, CRYPTO for paper sim.
- Sleeve-claim gap (top_sleeves not in audit3 cells) — P0.
- Selection alpha NEGATIVE (−0.276%/trade).
- Publication decay (26-58% haircut).
- Crypto funding carry compressed (2.7-6%/yr).
- Forward-test epistemology (SR 1.0 needs ~9 years for t=3).

### My response to both
- Agreed with Copilot's $2,000 recommendation (ETF for real money) but added MES ORB as alternative for intraday-capable users.
- Incorporated Buffy's TAA lagged findings (drawdown-control only).
- Elevated sleeve reconciliation to P0.
- Added publication decay caveat to all backtested edges.
- Created confidence recalibrator utility.
- Fixed credential issues (13 files with wrong password).

---

## 5. What to keep vs discard vs debate (summary table)

| Element | Verdict | Reason |
|---|---|---|
| audit3 kill tribunal | **KEEP** | Only honest scoring surface |
| audit2 candidate library | **KEEP** (doctrine only) | Correct vocabulary, useful graveyard |
| Forward observations ledger | **KEEP** | Only path to PROVEN_T2 |
| Cost model | **KEEP** (harmonized) | Costs kill strategies |
| Selection alpha | **KEEP** (implemented) | Distinguishes skill from luck |
| Random-entry MC | **KEEP** (wired) | Timing-null companion |
| Sleeve reconciliation | **KEEP** (new, P0) | Discovered top_sleeves unverified |
| Confidence recalibration | **KEEP** (new) | Fixes inverted ML calibration |
| Mutual fund screener | **KEEP** (new) | Lowest-risk money-ready candidate |
| Bond screener | **KEEP** (new) | Diversifier |
| Commodity screener | **KEEP** (new) | Replaces falsified COT |
| Hypothesis normalization | **KEEP** (done) | Clean vocabulary |
| audit page headline metrics | **DISCARD** (as evidence) | Inflated, stale, inconsistent |
| COT positioning | **DISCARD** | Falsified (over-emission) |
| 15m ML strategies | **DISCARD** | Overfit-bait (33/42) |
| Post-hoc segment numbers | **DISCARD** (as actionable) | No multiple-testing correction |
| Winner-take-all ETF rotation | **DISCARD** | Loses on risk-adjusted |
| Canonical Magic Formula (EBIT/EV) | **DISCARD** | Gross profit > EBIT |
| Piotroski standalone | **DISCARD** | Lost badly vs index |
| ETF TAA | **DEBATE** | Drawdown-control, not return enhancement |
| MES ORB | **DEBATE** | Promising but unproven (small sample) |
| Mutual funds (active) | **DEBATE** | Most fail after fees |
| Mid-tier stocks | **DEBATE** | Only if value-screened |
| Penny stocks | **DISCARD** | 90%+ lose money |

---

*Generated 2026-11-19 by opencode (Beam Free). This is a research review, not investment advice.*