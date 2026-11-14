# EQUITY — Per-Asset-Class Profitability Playbook

**PRIORITY: MEDIUM**

**EXPECTED EDGE: LOW–MODERATE.** The negative evidence in this repo is about *index mean-reversion* (SPY/QQQ RSI2) and *sector rotation*, not about the individual-stock cross-section, which has never been tested here. Two mechanisms in that untested space — post-earnings-announcement drift (PEAD/SUE) and a value/quality composite — have decades of independent published support and are buildable from keyless point-in-time data. Both are capacity-limited or style-cyclical, and neither is likely to clear the full gate set on the first attempt. Expected outcome: **NOT_PROVED with a measurable, pre-registered reason.**

- **Class status:** no proved edge. Live policy-clean EQUITY is significantly *negative* (WR 42.95%, PF 0.7022, z = −3.03).
- **Evidence clock:** 2026-11-14T21:15Z. Repo is read-only for this document; only this file is written.
- **Rule:** every number is copied from a cited artifact or derived arithmetically from cited numbers (derivations labelled). Absent data is marked `UNVERIFIED`; nothing is estimated.

---

## 0. Reading conventions

| Label | Definition |
|---|---|
| **PRIORITY** | Research ordering, not a profitability claim. HIGH = plausible untested mechanism + usable data; LOW = mechanism already falsified or data unavailable. |
| **EXPECTED EDGE** | Best honest prior on whether the class can produce a gate-passing net edge on available data. |
| **Derived** | Computed in this document from cited inputs; the formula is shown. |
| **UNVERIFIED** | Not present or not reproducible from the cited artifacts. |

---

## 1. Current evidence

### 1.1 What was actually tested (pre-registered research, v1–v3)

EQUITY research in this repo used **index and sector ETFs as proxies**, never a single-stock cross-section. The full registry is `03_research/profitability/HYPOTHESES.md:8-30`; run detail is in `runs/v1/REPORT.md`, `runs/v2/REPORT.md`, `runs/v3/REPORT.md`.

| ID | What was tested | Universe | OOS Sharpe | OOS CAGR | Benchmark | Status |
|---|---|---|---:|---:|---|---|
| H7 | 2-day RSI mean-reversion, 5 bps | SPY, QQQ | **1.50** | 17.6% | 1.02 Sharpe / 18.6% | NOT_PROVED |
| H10 | H7 + idle cash at 13-week T-bill | SPY, QQQ | **1.83** | 22.0% | 1.02 / 18.6% | NOT_PROVED (exploratory) |
| H8 | Sector RSI2 + T-bill cash | 10 sector ETFs | 1.16 | 17.2% | 1.09 / 13.5% | NOT_PROVED |
| H11 | Sector RSI2 + 200d trend + cash | 10 sector ETFs | 1.04 | 11.5% | 1.09 / 13.5% | NOT_PROVED |
| H12 | Sector 12-1 momentum, top 3 + cash | 10 sector ETFs | 1.14 | 16.7% | 1.09 / 13.5% | NOT_PROVED |
| H9 | International RSI2 + cash | 10 country ETFs | 0.31 | 4.1% | 0.90 / 15.1% | NOT_PROVED |

Source: `runs/v1/REPORT.md` (H7), `runs/v2/REPORT.md` (H8–H12). All use train ≤2023-12-31 and OOS 2024-01-01..2026-11-14.

**Source note:** the brief asks for `runs/v1/VERDICT.md`; that file does not exist — v1 published `REPORT.md` only. v2/v3/v4 `VERDICT.md` exist and were read.

### 1.2 Why each test failed — exact numbers

**H7 (index RSI2).** OOS Sharpe 1.50 and max drawdown −7.7%, but OOS CAGR **17.6% < 18.6%** buy-and-hold. It fails the absolute-return and benchmark gates, and DSR **0.948 < 0.95** at N=7. 2× cost gives 1.33. The high Sharpe comes from **17% average exposure** (`runs/v1/REPORT.md`), i.e. it is mostly a cash strategy. A risk-matched benchmark (~17% SPY/QQQ + ~83% T-bill) has rf=0 Sharpe **2.168–2.285**, *above* H10's 1.83 (`runs/v2/VERDICT.md:44-46`). On excess-of-cash returns H10 wins 1.45 vs 0.78 — so the verdict depends entirely on the benchmark convention. That ambiguity is a finding, not a detail.

**H10 (H7 + T-bill carry) — the contaminated variant.** Mechanically passed at N=12 (Sharpe 1.83, CAGR 22.0%, DSR 0.978, p=0.00194, 2× 1.68), then failed adversarial review (`runs/v2/VERDICT.md:34-53`):

1. **Post-hoc, same seen OOS.** H10 is a cash-added variant of H7 created after H7's 2024–2026 OOS was inspected; it reuses that window, so the OOS is not clean.
2. **Effective multiple testing.** Counting the 27-cell parameter grid: effective N≈38 → **DSR 0.9365** and Bonferroni α 0.001316 < p 0.001802.
3. **Single-day dependence.** 2025-04-09 contributes **+11.20%** in one day; removing it drops DSR to **0.8993**; removing the top 3 days → **0.8255**.
4. **Execution fragility.** +1 day lag → Sharpe **0.696** (CAGR 8.2%); +3 days → **0.477**.
5. **Regime.** Clean 2016-11-14..2017-12-31 holdout: H10 1.755 Sharpe / 7.46% CAGR vs B&H 2.835 / 25.76%.
6. **The edge is carry.** H7 0% cash = 17.61% CAGR; H10 = 22.0%. Δ = **+4.39 pp**. Cash exposure 0.827 × 4.38% OOS T-bill = **3.62 pp**, i.e. **~82.5% of the improvement is T-bill carry** (derived; inputs `runs/v2/VERDICT.md:50-51`).
7. OOS T-bill averaged **4.38%** vs **0.90%** in the holdout (`runs/v2/VERDICT.md:49`).

**H8 (sector RSI2 + cash).** OOS 1.16 vs benchmark 1.09, but **train Sharpe −0.14** (CAGR −5.0%), DSR **0.603**, and **2× cost Sharpe 0.66** — fails the 2× gate outright (`runs/v2/REPORT.md:17-25`).

**H11 (sector RSI2 + trend + cash).** 1.04 vs 1.09, CAGR 11.5% < 13.5%, DSR 0.529, 2× 0.57 (`runs/v2/REPORT.md:47-55`).

**H12 (sector 12-1 momentum top 3).** 1.14 vs 1.09, DSR 0.589, and **n=22 rebalances < 30**; not +0.30 above benchmark (`runs/v2/REPORT.md:57-65`).

**H9 (international RSI2).** 0.31 vs 0.90, 2× cost Sharpe **−0.02** (`runs/v2/REPORT.md:27-36`).

**Net:** sector rotation and index mean-reversion both failed on cost, multiple-testing, or regime grounds. The only mechanical pass was a **T-bill-carry variant on an already-seen OOS**, which is exactly the failure mode the program was designed to catch. The honest label is **NOT_PROVED — no durable equity edge demonstrated**.

### 1.3 Live-system evidence (honest cohorts only)

Do not use the headline class tile. Six mutually inconsistent EQUITY cohorts exist (`01_audit/sub/D_non_crypto.md:123-140`):

| Source | n | WR | PF | Comment |
|---|---:|---:|---:|---|
| `pf_registry.by_asset_class_policy_clean` | **461** | **42.95%** | **0.7022** | Most defensible; z = **−3.03**, survives 9-class Bonferroni (`01_audit/sub/E_statistical.md:204`) |
| `recent_closed` payload | 738 | 47.0% | 1.154 | 649/738 (88%) >30 d old; `current_price` null 738/738 |
| `money_ready_verdict` intrabar truth | 250 | 59.2% | 0.939 | Daily-vs-intrabar divergence flagged |
| `audit_surface_truth` | 249 | 59.0% | 0.934 | — |
| `summary_picks` | 13,383 total / 820 resolved | **162.4%** | — | Arithmetically impossible; denominator bug |
| `tournament` | 288 closed | 36.8% | — | −0.40%/trade |

Key integrity facts:

- **EQUITY is significantly negative**, not merely unproven: n=461, WR 42.95%, PF 0.7022, z = −3.03 (p = 2.5×10⁻³) versus the Bonferroni |z|_crit 2.773 (`01_audit/sub/E_statistical.md:204`).
- **Daily-vs-intrabar inflation:** daily PF 1.298 vs honest 0.939 (`01_audit/sub/D_non_crypto.md:139`).
- **Two impossible AAPL entries** against the timestamp-day range: 2026-11-13 entry 315.9799 vs range 355.75–360.83 (−11.2% below the low), and 2026-11-03 entry 316.22 vs 325.33–334.50 (`01_audit/sub/D_non_crypto.md:115-118`).
- **Raw inventory:** 94 OPEN, 85 EXPIRED, 3 SL_HIT; median age 107.2 h; 82 rows >30 d (45%); `current_price` null/0 on 110 (60%); `pnl_pct == 0` on 142 (78%) (`01_audit/sub/D_non_crypto.md:96-102`).
- **The n=8 / 75% WR / PF 8.86 headline is meaningless** and its producer is `UNVERIFIED`; the traceable cohorts are n=738 / n=759 / n=461 (`MASTER_AUDIT.md:238-255`, `01_audit/recommendations/per_asset_class/equity_etf.md:375`).
- **Measurement is broken:** 40/94 OPEN rows frozen at 0%/null, and the curated panel shows 0.00% because `current_price == entry_price` (`MASTER_AUDIT.md:100`, `equity_etf.md:20`).

### 1.4 Peer claims that touch EQUITY

| Claim | Source | Disposition |
|---|---|---|
| Variant-C strategy selector: EQUITY n=112, PF 1.30, +73.1 pp | `04_peer_reviews/FP2_deepAI_profitable_v1.md:86` | **FALSIFIED as stated.** +98.7 pp is **gross**, not net: the walk-forward never calls `deduct_slippage`, and 237 trades × 0.1–0.2%/trade = 24–47 pp of cost (`FP2:290-300`). The book is 51% ETF + 47% EQUITY, long-biased in a rising market; no beta adjustment (`FP2:307-310`). The documented search family is ≥54, not 4 → p≈0.058–0.17, not <0.005 (`FP2:313-330`). The same script on the only available same-schema payload gives **PF 0.906, −134.5 pp, p=0.4825** (`FP2:636-640`). |
| "equities PF 0.934 / WR 59%" and a 4,202-row 6-source composite | `04_peer_reviews/FP1_flaxen_hair_mega_mutation.md:219` | **UNVERIFIED.** No committed artifact contains 4,202 rows or the 6-source split; quick-win docs disagree with each other. Do not cite. |
| Diversified vol-targeted trend "PROVEN" (Sharpe 2.13, CI 1.25–3.25, t=5.56) | `04_peer_reviews/FP5_peer_final_folders.md:40-41,81,118` | **FALSIFIED as proof.** Buy-and-hold of the same 10 had Sharpe ≈2.2, i.e. the t-test rejects "mean > 0", which beta passes. Independent TSMOM365 OOS Sharpe 0.57, null p=0.200; PF 1.40 < the project's own 1.5 gate. Label `PILOT / risk-premium harvest`, not proved. |

### 1.5 The real gap: what EQUITY has never tested

There is **no single-stock experiment anywhere in the research program**. Specifically untested here:

- No PEAD / standardized unexpected earnings (SUE) test.
- No value/quality composite (B/P, E/P, gross profitability, accruals, Piotroski F-score) test.
- No short-interest or days-to-cover test.
- No analyst-revision test.
- No stock-level cross-sectional momentum or reversal.
- No low-volatility / betting-against-beta test.
- No time-series momentum on equity indices (TSMOM was tested on BTC/ETH and on a 20-ETF basket, not on SPY/QQQ).

The active production strategy `magic_formula_x_piotroski_x_acquirers` (ADBE, `01_audit/sub/D_non_crypto.md:91`) has **n=0** closed trades in the `recent_closed` feed, so its economic family has no measured history (`equity_etf.md:245`). That is the single largest evidence hole in this class — and the reason priority is MEDIUM rather than LOW.

---

## 2. Where an edge could actually exist

| Mechanism | Signal | Why it can persist | Capacity | Verdict for this repo |
|---|---|---|---|---|
| **PEAD / SUE** | Earnings surprise (reported vs seasonal random walk or consensus), drift over 20–60 sessions | Investor under-reaction, limited attention, slow information diffusion, limits to arbitrage | **Limited**: strongest in small/mid caps; decays with size/liquidity; realistically ~$10–50M before impact | **Best untested candidate.** Event-driven → high statistical power; market-neutral construction removes the bull-market confound |
| **Value / quality** | B/P, E/P, gross profitability, accruals, F-score | Risk premium + limits to arbitrage + over-extrapolation of growth | **High**: works in large caps; $500M+ plausible | Strong prior, but 2024–26 growth/AI leadership is a style headwind; low turnover helps cost survival |
| **Stock-level XS momentum** | 12-1 return, top/bottom decile | Under-reaction then over-reaction; herding | **Moderate** | Never tested here; high turnover and crash risk; short leg needs borrow |
| **Low-vol / BAB** | Beta-sorted or volatility-sorted portfolios | Leverage constraints, lottery preference | **High**, but crowded | Price-only data suffices; likely lags a strong bull market on raw return |
| **Short interest** | ΔSI, days-to-cover, utilization | Short-sale constraints, divergence of opinion | **Limited**: borrow scarcity, squeeze risk, crowding | FINRA data is free but bi-monthly (lag); borrow/utilization is paid → low feasibility |
| **Analyst revisions** | Δ consensus EPS, revision breadth | Slow diffusion, analyst herding | **Limited**: data cost, small-cap | Paid point-in-time consensus required → out of scope for keyless data |
| **Intraday gap reversal** | Overnight gap vs intraday return | Liquidity provision to uninformed order flow | **Very limited**: intraday L2, HFT competition, high turnover | Needs intraday/order-book data not held here → out of scope, `UNVERIFIED` |

Capacity figures in the table above are order-of-magnitude planning estimates, not measurements from this repo.

**Capacity summary.** Only value/quality and low-vol are genuinely scalable. PEAD and short-interest are capacity-constrained — which is *why* they can survive publication, and also why they cannot be the basis of a large book. Any result must state the capital at which the edge is measured, not just the Sharpe.

**Decay risk.** PEAD is the most likely of these to be partly arbitraged: the effect is well known and has weakened since the 2000s, especially in mega caps. The test must be run on small/mid caps *and* large caps separately; a large-cap-only null is expected and is not a refutation of the mechanism.

---

## 3. Ranked hypotheses (evidence × feasibility)

Scoring: **Evidence** = strength/robustness of the published mechanism plus in-repo evidence (1–5); **Feasibility** = keyless data availability, build cost, cost-survival, sample size (1–5). Product ranks the list.

| Rank | ID | Hypothesis | Evidence | Feasibility | Score |
|---:|---|---|---:|---:|---:|
| 1 | **E1** | PEAD / SUE, event-driven, market-neutral | 5 | 4 | **20** |
| 2 | **E2** | Value/quality composite (long-only and long-short) | 5 | 4 | **20** |
| 3 | **E3** | Stock-level 12-1 cross-sectional momentum | 4 | 4 | **16** |
| 4 | **E4** | Low-volatility / BAB | 3 | 5 | **15** |
| 5 | **E5** | Short-interest / days-to-cover | 3 | 2 | **6** |

E1 and E2 tie on score. **E1 is ranked first** on a pre-declared tie-break: (a) event-driven samples give far more power in a 2.87-year OOS; (b) a beta-neutral construction directly neutralises the 2024–26 bull confound; (c) it fills a live implementation gap — the repo's existing PEAD shadow log fails **60/60** at the commit step (`MASTER_AUDIT.md:69`), so there is no working baseline to inherit.

### E1 — PEAD / SUE (rank 1, pre-registered below)

- **Signal:** SUE_q = (EPS_q − EPS_{q−4}) / σ(ΔEPS over the prior 8 quarters), where EPS is reported diluted EPS known at the SEC filing timestamp. Long top tercile; optional short bottom tercile.
- **Universe:** US operating companies on NYSE/Nasdaq, price > $5, ADV > $3M, market cap > $300M, exclude ETFs/ADRs/financials if the data join is unreliable.
- **Rebalance:** event-driven entry the session after the filing is public; hold 40 trading days or until the next earnings filing; exits daily.
- **Mechanism:** post-earnings under-reaction; prices drift in the direction of the surprise for weeks.
- **Data required:** SEC EDGAR `submissions` + `companyfacts` (XBRL `EarningsPerShareDiluted`, with `filed` dates) for point-in-time EPS; Nasdaq daily closes; Nasdaq earnings calendar to validate filing/announcement dates.
- **Costs / capacity:** 10 bps/side + 10 bps slippage for mid caps (40 bps round trip); stress 2×. Capacity ~$10–50M before market impact dominates; max 2% per name.
- **Failure mode:** restated/backfilled EPS destroys point-in-time validity; earnings-date errors create look-ahead; the effect may be confined to micro caps where costs and impact eat it; mega-cap dominance in 2024–26 can make an equal-weight book lag on raw return even when alpha is positive.

### E2 — Value/quality composite (rank 2)

- **Signal:** equal-weight z-score of book-to-price, earnings yield, gross profitability (GP/assets), low accruals, and Piotroski F-score. Long top quintile; short bottom quintile in the market-neutral variant.
- **Universe:** liquid US operating companies, point-in-time fundamentals, price > $5, ADV > $5M.
- **Rebalance:** quarterly, one session after the 10-K/10-Q filing; 60-session formation buffer to avoid look-ahead.
- **Mechanism:** value and quality risk premia plus correction of growth over-extrapolation.
- **Data required:** SEC XBRL companyfacts (filed dates), Nasdaq prices. No analyst estimates.
- **Costs / capacity:** 10 bps/side; low turnover (~4×/yr) → cost-tolerant; capacity $500M+ in large caps.
- **Failure mode:** value drawdowns and style cyclicality; sector concentration (financials/energy); survivorship in the Nasdaq price panel; accounting-rule changes across the sample.

### E3 — Stock-level 12-1 cross-sectional momentum (rank 3)

- **Signal:** 12-month return skipping the most recent month; long top decile, short bottom decile, beta-neutral.
- **Universe:** liquid US stocks, price > $5, ADV > $5M.
- **Rebalance:** monthly.
- **Mechanism:** under-reaction/continuation, herding, slow diffusion.
- **Data required:** Nasdaq daily prices; a point-in-time universe (current-index membership is survivorship-biased).
- **Costs / capacity:** 10 bps/side; monthly turnover ~100%+ per leg; borrow 50 bps/yr on the short leg; capacity moderate.
- **Failure mode:** momentum crashes (2009/2020-style reversals), short-leg borrow/squeeze, turnover cost, 2024–26 mega-cap concentration.

### E4 — Low-volatility / BAB (rank 4)

- **Signal:** 60-day realised vol or market beta; long lowest quintile, short highest, beta-neutral; or long-only low-vol with leverage to match market beta.
- **Universe:** liquid US stocks.
- **Rebalance:** monthly.
- **Mechanism:** leverage constraints and lottery preference push high-beta stocks to be overpriced.
- **Data required:** prices only.
- **Costs / capacity:** 10 bps/side; high capacity; leverage financing cost must be modelled explicitly (do not assume free leverage).
- **Failure mode:** rate sensitivity, crowding, underperformance in strong bull markets; the anomaly is partly a sector bet (utilities/staples).

### E5 — Short interest / days-to-cover (rank 5)

- **Signal:** change in short interest and days-to-cover; long low-SI, short high-SI (or the squeeze variant).
- **Universe:** US stocks with reliable FINRA short-interest records.
- **Rebalance:** bi-monthly, aligned to the FINRA settlement/publication lag.
- **Mechanism:** short-sale constraints and divergence of opinion; high-SI names carry a speculative premium that can reverse.
- **Data required:** FINRA short interest (free, bi-monthly); borrow fee/utilization is paid → `UNVERIFIED` availability.
- **Costs / capacity:** 10 bps/side + borrow; capacity small and crowded; squeeze risk is the dominant tail.
- **Failure mode:** 2-week data lag, crowding, squeeze losses, borrow recall.

---

## 4. Pre-registered next experiment — `E-PEAD-1`

**One experiment. Frozen before any result is inspected. Any change creates E-PEAD-2 and a new forward ledger.**

### 4.1 Design

| Item | Specification |
|---|---|
| **Hypothesis** | SUE-based PEAD produces positive net alpha after costs, survives multiple-testing correction, and is not explained by market beta. |
| **Signal** | `SUE = (EPS_q − EPS_{q−4}) / stdev(EPS_q − EPS_{q−4} over the prior 8 quarters)`, using **as-reported diluted EPS** with the SEC `filed` timestamp as the only availability time. No analyst consensus, no restatement, no backfill. |
| **Entry** | Top SUE tercile, subject to liquidity filters; enter at the **next session's close** after the filing timestamp. |
| **Exit** | 40 trading days after entry, or the next earnings filing, whichever is first. |
| **Universe** | US operating companies (ex-ETF, ex-ADR, ex-OTC): price > $5, 20-day median dollar volume > $3M, market cap > $300M at entry. Financials included only if XBRL tags reconcile. |
| **Construction** | Equal-weight, **max 2% per name**, max 50 names, 5% cash buffer. Two books reported separately: (a) long-only vs equal-weight universe; (b) long/short (100% long / 100% short, beta-hedged with SPY). |
| **Train / OOS** | Train ≤ **2023-12-31**; OOS ≥ **2024-01-01** through the last complete session. Parameters (tercile, 40-day hold, liquidity floors) are fixed here and not tuned on OOS. |
| **Costs** | Base **10 bps/side + 10 bps slippage** (40 bps round trip); stress **2× = 80 bps round trip**. Short leg adds **50 bps/yr borrow**. No cost-free fills. |
| **Execution** | Signal is public at filing; trade at t+1 close. Lag test: t+2 and t+5 entry. Never same-bar. |
| **Concurrent capital** | 100% notional long book, **no leverage**; long/short variant 200% gross, 0% net beta target. Position cap 2%, sector cap 25%. |
| **Data source (exact)** | SEC EDGAR: `https://data.sec.gov/submissions/CIK##########.json` and `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (XBRL `us-gaap:EarningsPerShareDiluted`, `filed` date). Prices: `https://api.nasdaq.com/api/quote/<SYM>/historical?assetclass=stocks`. Earnings-date cross-check: `https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD`. |
| **Benchmark** | Equal-weight eligible universe (same filters, same dates), **total-return** (dividends included). Also report vs SPY total return. |

### 4.2 Gates (all must pass; DSR at true N)

| # | Gate | Threshold |
|---:|---|---|
| 1 | Net OOS Sharpe (excess of cash) | ≥ **1.0** and ≥ benchmark **+0.30** |
| 2 | Net OOS CAGR / total return | > 0 and > benchmark, **total-return basis** |
| 3 | Sample | ≥ **300 events** and ≥ **30 monthly cohorts** in OOS |
| 4 | **True DSR at all trials** | N = 38 (prior effective) + 15 (E1–E5 × 3 variants) + 12 (this grid) = **65**; DSR ≥ **0.95**; stress at **N=130** |
| 5 | **CSCV PBO** | 16 blocks, purge 5 / embargo 5 sessions; **PBO < 0.50** (report the full distribution) |
| 6 | **SPA / Reality Check** | Stationary bootstrap, 5,000 resamples, block 20; **p < 0.05** across the E-family |
| 7 | **2× cost** | Net Sharpe ≥ **0.5** and > benchmark |
| 8 | **Execution lag** | t+2 entry Sharpe ≥ **1.0** and > benchmark; t+5 reported |
| 9 | Beta neutrality | Long/short market-beta-adjusted alpha **t ≥ 2.0** |
| 10 | Sub-period consistency | Positive excess in **each** of 2024, 2025, 2026-YTD; no single month > 50% of total excess |
| 11 | Robustness | Ex-top-3-month DSR ≥ 0.95; sector-neutral variant retains ≥ 50% of alpha |
| 12 | Data integrity | Point-in-time SUE reconstructible for ≥ 80% of events; entry price inside the entry-day range for ≥ 99% of events |

### 4.3 Pre-registered expected result

Given the 2.87-year OOS and a likely effect of 0.3–0.6 gross Sharpe in mid caps, the honest prior is **fail gates 1/7/8 or 12**, most likely on cost survival and point-in-time EPS coverage. A failure is informative: it converts "we never tested PEAD" into "PEAD does not survive costs on keyless data in 2024–26."

---

## 5. Kill criteria

Stop the program (not just the candidate) if any of these hold:

1. **No cost survival.** 2× cost net Sharpe < 0.5 for every variant.
2. **No multiple-testing survival.** DSR < 0.95 at N=65 for every variant.
3. **PBO ≥ 0.50** on the frozen candidate matrix.
4. **SPA p ≥ 0.05** across the family.
5. **Beta explains it.** Long/short alpha t < 2 after beta hedging.
6. **Dividend-sensitive.** Result flips sign when total-return prices replace price-only prices.
7. **Single-month dependence.** Removing the top 3 months drops DSR below 0.95.
8. **Data integrity.** Point-in-time SUE is reconstructible for < 80% of events, or > 1% of entries are outside the entry-day range.
9. **Survivorship dominance.** Dropping the top 20% best-performing surviving names removes > 50% of alpha.
10. **Underpowered.** Fewer than 300 OOS events or 30 cohorts — the test cannot reject, and must be reported as inconclusive rather than negative.

---

## 6. What NOT to do

1. **Do not run more RSI2/mean-reversion variants on SPY/QQQ.** H7, H10 and the 27-cell grid exhausted that family; more variants only inflate N.
2. **Do not add a T-bill cash sleeve to rescue a weak signal.** That is exactly how H10 was contaminated; cash carry explains ~82.5% of its improvement and vanishes at 0.90% rates.
3. **Do not quote the n=8 / 75% WR / PF 8.86 cohort** or `summary_picks`' 162.4% WR. Both are artifacts.
4. **Do not use the 3,500-row `recent_closed` feed as a research dataset.** Median close age is 120.1 d for EQUITY, `current_price` is null on all 738 rows, and `resolution_method` is absent on all 3,500.
5. **Do not use daily-resolved PnL without intrabar stop checks.** Daily PF 1.298 vs honest 0.939 on the same cohort.
6. **Do not test on current index membership** without an explicit survivorship stress; the Nasdaq panel has no delisted names.
7. **Do not call the existing PEAD shadow log a baseline.** It fails 60/60 in `Commit shadow log` (`MASTER_AUDIT.md:69`) and has produced no evidence.
8. **Do not cite the "equities PF 0.934 / WR 59%" quick-win number** — it is `UNVERIFIED` and contradicted by the policy-clean registry.
9. **Do not treat 5 bps as a sufficient cost model** while ignoring dividends; the omission is larger than the cost assumption.
10. **Do not report a long-only equity result without a beta/benchmark decomposition.** In 2024–26 beta, not skill, is the default explanation.

---

## 7. Confounds that must be addressed

### 7.1 The 2024–2026 bull-market confound

- The OOS is **2.87 years** (2024-01-01..2026-11-14, 1,049 daily rows in `runs/v1/oos_returns.csv`) — **one regime**.
- Benchmarks were strong: SPY/QQQ buy-and-hold Sharpe **1.02, CAGR 18.6%**; the 50-ETF equal-weight basket **1.18**. Any long-biased strategy earns beta and looks good in absolute terms.
- **Statistical power is the binding constraint.** Using the Lo (2002) iid approximation, SE(annualised Sharpe) ≈ √((1 + 0.5·S²)/T). With S≈1.1 and T=2.87, **SE ≈ 0.75** (derived). The H16-vs-benchmark gap of 0.20 Sharpe is **0.26 SE** — statistically indistinguishable from zero. "NOT_PROVED" therefore means *underpowered*, not *proven absent*.
- The 2024–26 rate regime flatters cash: OOS 13-week T-bill averaged **4.38%** vs **0.90%** in the 2016–17 holdout (`runs/v2/VERDICT.md:49`). Any strategy with a cash sleeve or low exposure gets an artificial boost.
- **Required controls:** excess-of-cash Sharpe; a **risk-matched** benchmark (match average exposure and beta, not just asset); a beta-hedged variant; sub-period sign consistency (2024 / 2025 / 2026 YTD); total-return benchmarks.
- **Do not** use the 2016–17 holdout as OOS — it is in-sample for design and can only be reported as a labelled regime stress.

### 7.2 Dividend omission in Nasdaq price-only data

- `data/loader.py:186-215` (`nasdaq_daily`) returns **`tradesTable.close` only** — price-only, ~10-year cap, no dividends. `SCORECARD.md:12` records this as a data-provenance limitation (7/10: "Nasdaq price-only, no dividends").
- **Direction of bias:** long-only equity/ETF benchmarks are **understated** by the dividend yield; the cash sleeve is **not** (the 13-week T-bill series is a coupon-equivalent yield, a total return). This systematically *favours* cash-augmented strategies such as H8/H10/H11/H12 and *penalises* dividend-heavy buy-and-hold.
- **Magnitude:** for broad US equity, bond, REIT and high-yield ETFs the omission is on the order of **hundreds of basis points per year** — one to two orders of magnitude larger than the **5 bps/side** cost assumption. Exact per-symbol yields for this universe are `UNVERIFIED` here and must be sourced from a dividend feed. The conclusion does not depend on the precise number: **the cost model is not the dominant return-level error; the missing dividend is.**
- **Signal contamination:** ex-dividend price drops create artificial negative daily returns (quarterly for equity, monthly for bond ETFs) that can trigger RSI2/reversal entries and stop-outs. This is a mechanism-level bug, not just a benchmark-level one.
- **Required fix before any promotion:** re-run every candidate on **total-return (adjusted) prices**. Acceptable sources: issuer distribution files, Nasdaq `api.nasdaq.com/api/quote/<SYM>/dividends`, or CBOE total-return index histories; Yahoo adjusted close only as a cross-check (HTTP 429 risk). Publish the dividend yield per asset and a price-only-vs-total-return delta. A result that survives only on price-only data is killed.

---

## 8. UNVERIFIED / missing

- `03_research/profitability/NEXT_DATA_REQUIREMENTS.md` is referenced by `05_final/reference_final_2026_11_14/FINAL_SYNTHESIS.md:170` but **does not exist** in the tree.
- `runs/v1/VERDICT.md` does not exist (v1 published `REPORT.md` only).
- Exact full-sample EQUITY PF: aggregators disagree (0.7022 policy-clean, 1.154 `recent_closed`, 8.86 n=8); the n=8 producer was not located (`MASTER_AUDIT.md:401`).
- Per-symbol dividend yields for the ETF/equity universe.
- Point-in-time analyst consensus (not used by E-PEAD-1; would be needed for a consensus-SUE variant).
- Borrow fee/utilization data for the short leg and for E5.
- Whether any genuinely unseen OOS remains: every 2024–2026 window used so far has been inspected at least once.

---

## 9. Evidence index

| File | Used for |
|---|---|
| `01_audit/MASTER_AUDIT.md` | Class status, per-class significance, cohort conflicts, PEAD 60/60 failure |
| `01_audit/sub/D_non_crypto.md` | EQUITY curated/raw/closed numbers, impossible AAPL entries, cohort table |
| `01_audit/sub/E_statistical.md` | Per-class z, Bonferroni threshold, survivorship |
| `01_audit/recommendations/per_asset_class/equity_etf.md` | P0/P1 diagnosis, do-not-do list, UNVERIFIED list |
| `03_research/profitability/runs/v1/REPORT.md` | H7 |
| `03_research/profitability/runs/v2/REPORT.md` | H8–H12 |
| `03_research/profitability/runs/v2/VERDICT.md` | H10 contamination, lag/DSR/regime numbers |
| `03_research/profitability/runs/v3/{REPORT,VERDICT}.md` | ETF/sector/rotation breadth, SPA/PBO |
| `03_research/profitability/HYPOTHESES.md` | Full 23-candidate registry and statuses |
| `03_research/profitability/SCORECARD.md` | Version results, data-provenance note |
| `03_research/profitability/data/loader.py` | Price-only Nasdaq loader |
| `04_peer_reviews/FP1_flaxen_hair_mega_mutation.md` | Unverifiable per-class quick-win numbers |
| `04_peer_reviews/FP2_deepAI_profitable_v1.md` | Variant-C EQUITY claim and its falsification |
| `04_peer_reviews/FP5_peer_final_folders.md` | ITERATION-005 "proven trend" correction |
| `05_final/reference_final_2026_11_14/FINAL_SYNTHESIS.md` | Program-level verdict and next steps |
