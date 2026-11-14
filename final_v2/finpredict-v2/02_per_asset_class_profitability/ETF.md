# ETF — Per-Asset-Class Profitability Playbook

**PRIORITY: LOW**

**EXPECTED EDGE: LOW.** Every price-based ETF family tested here — cross-sectional momentum, short-term reversal, time-series momentum, country rotation, sector rotation, dual momentum — failed to beat a simple equal-weight or 60/40 benchmark after costs. The one apparent "profitable class" (policy-clean PF 1.8358) is n=15 and disappears under intrabar marking (PF 0.0216). The only untested family with an independent economic mechanism is a **volatility-risk-premium overlay** (covered calls / put-writing), which is high-capacity but caps upside and is crash-convex. Expected outcome: **NOT_PROVED; most likely a risk-adjusted tie or loss versus a beta-matched benchmark in the 2024–2026 bull window.**

- **Class status:** no proved edge. All 8 v3 breadth candidates failed; SPA p = 0.488 across the family.
- **Evidence clock:** 2026-11-14T21:15Z. Repo is read-only for this document; only this file is written.
- **Rule:** every number is copied from a cited artifact or derived arithmetically from cited numbers (derivations labelled). Absent data is marked `UNVERIFIED`.

---

## 0. Reading conventions

| Label | Definition |
|---|---|
| **PRIORITY** | Research ordering, not a profitability claim. LOW = mechanism families already falsified on available data and no high-prior untested candidate with clean data. |
| **EXPECTED EDGE** | Best honest prior on whether the class can produce a gate-passing net edge on available data. |
| **Derived** | Computed in this document from cited inputs; the formula is shown. |
| **UNVERIFIED** | Not present or not reproducible from the cited artifacts. |

---

## 1. Current evidence

### 1.1 What was tested (pre-registered research, v1–v3)

All ETF tests use the Nasdaq price-only panel (`data/loader.py:186-215`) and 5 bps/side. The v3 universe is **50 ETFs** (`run_v3.py:41-45`); `PROTOCOL_v3.md:10` says "up to 40" and `HYPOTHESES.md` says 50 — a documentation inconsistency, but the executed universe is the 50-symbol list. Detail: `runs/v1/REPORT.md`, `runs/v2/REPORT.md`, `runs/v3/REPORT.md`.

| ID | What was tested | Universe | OOS Sharpe | OOS CAGR | Benchmark | Status |
|---|---|---|---:|---:|---|---|
| H5 | Dual momentum, monthly | SPY/EFA/AGG/BIL | 0.99 | 16.2% | 0.99 / 9.8% | NOT_PROVED (6 changes) |
| H16 | XS 12-1 momentum, top ~7.5% of 50 (3–4 names; registry says top 3), monthly | 50 ETFs | **0.98** | 29.6% | **1.18** / 14.8% | NOT_PROVED |
| H17 | XS short-term reversal, bottom decile, weekly | 50 ETFs | 0.76 | 15.2% | 1.18 / 14.8% | NOT_PROVED |
| H18 | TSMOM breadth, 20 ETFs, vol-targeted, monthly | 20 core ETFs | 1.00 | 12.0% | 0.99 / 9.8% (60/40) | NOT_PROVED |
| H19 | Country rotation, top 3, monthly | 12 country ETFs | 0.76 | 16.8% | 0.99 / 16.6% | NOT_PROVED |
| H8 | Sector RSI2 + T-bill cash | 10 sector ETFs | 1.16 | 17.2% | 1.09 / 13.5% | NOT_PROVED |
| H11 | Sector RSI2 + 200d trend + cash | 10 sector ETFs | 1.04 | 11.5% | 1.09 / 13.5% | NOT_PROVED |
| H12 | Sector 12-1 momentum, top 3 + cash | 10 sector ETFs | 1.14 | 16.7% | 1.09 / 13.5% | NOT_PROVED |

Sources: `runs/v1/REPORT.md` (H5), `runs/v2/REPORT.md` (H8–H12), `runs/v3/REPORT.md` and `runs/v3/VERDICT.md:7-28` (H16–H19). Train ≤2023-12-31; OOS 2024-01-01..2026-11-14.

### 1.2 Why each test failed — exact numbers

**H16 — the flagship ETF result (0.98 vs 1.18).** Highest OOS CAGR among the ETF candidates (29.6%) but a *lower* risk-adjusted result than the benchmark, with max drawdown **−33.3%**. It fails: OOS Sharpe < 1.0; not +0.30 over benchmark; **24 position changes < 30**; SPA p=0.488; DSR 0.386; 2× cost Sharpe 0.97 (>0.5 but still below the 1.18 benchmark); 21-day execution lag 0.83 (`runs/v3/REPORT.md:88-99`). PBO 0.36 and walk-forward 0.84 are the *only* encouraging numbers. The mechanism is real in the literature; on this data it buys more volatility, not more edge.

**H17 — short-term reversal.** 0.76 vs 1.18; 2× cost **0.55**; DSR 0.268; walk-forward 0.60 vs benchmark 0.71. Interestingly the 5-day lag Sharpe is **1.04**, higher than the contemporaneous 0.76 — a warning that the signal is not a clean same-day reversal, or that the result is noise (`runs/v3/REPORT.md:101-112`).

**H18 — TSMOM breadth (20 ETFs, vol-targeted).** 1.00 vs 0.99 on a 60/40 SPY/AGG benchmark. It does not beat by +0.30; **walk-forward Sharpe 0.37 vs benchmark 0.61** — the in-sample/OOS split is unstable; DSR 0.408; 2× cost 0.90 (`runs/v3/REPORT.md:114-124`). This is the closest "risk-managed" candidate and it still fails.

**H19 — country rotation.** 0.76 vs 0.99, CAGR 16.8% ≈ benchmark 16.6% with higher risk; **22 position changes < 30**; DSR 0.262; 2× 0.74 (`runs/v3/REPORT.md:126-136`).

**H5 — dual momentum.** 0.99 vs 0.99 benchmark, 16.2% vs 9.8% CAGR, but only **6 position changes** and DSR 0.624; it cannot be statistically distinguished from the benchmark (`runs/v1/REPORT.md:63-72`).

**H8/H11/H12 — sector rotation.** H8 1.16 vs 1.09 with **train Sharpe −0.14** and **2× cost 0.66**; H11 1.04 vs 1.09 with DSR 0.529 and 2× 0.57; H12 1.14 vs 1.09 with **22 position changes** and DSR 0.589 (`runs/v2/REPORT.md:17-65`). Sector rotation fails on cost survival and sample size.

**Family-level result:** Reality Check / SPA **p = 0.488** across all 8 v3 candidates; cumulative N=20; PBO ETF 0.36; CPCV median 0.52 (`runs/v3/VERDICT.md:18-28`, `runs/v3/REPORT.md:180-186`). The maximum observed performance is indistinguishable from the bootstrap null.

**Net:** all tested ETF return-premium families (momentum, reversal, trend, rotation, dual momentum) fail. The consistent pattern is that they **raise return and volatility together** and lose on a risk-adjusted, cost-aware basis.

### 1.3 Live-system evidence (honest cohorts only)

| Source | n | WR | PF | Comment |
|---|---:|---:|---:|---|
| `pf_registry.by_asset_class_policy_clean` | **15** | **73.33%** | **1.8358** | z = +1.81, p = 0.071; does **not** survive 9-class Bonferroni (α 0.0056) |
| `recent_closed` payload | 567 | 44.3% | 1.036 | 490/567 (86%) >30 d old |
| `money_ready_verdict` intrabar truth | 45 | **2.22%** | **0.0216** | — |
| `audit_surface_truth` | 44 | 2.3% | 0.0219 | — |
| `summary_picks` | 1,002 total / 73 resolved | **232.9%** | — | Arithmetically impossible |

Sources: `MASTER_AUDIT.md:126`, `01_audit/sub/D_non_crypto.md:232-247`, `01_audit/sub/E_statistical.md:208`.

Key integrity facts:

- **The "only profitable class" is an artifact.** Daily PF 1.8358 vs honest intrabar PF **0.0216** → **84.99× PF inflation**, the largest in the payload; WR inflation **+71.1 pp** (`01_audit/sub/D_non_crypto.md:242-244`). The class is labelled `INSUFFICIENT_SAMPLE`, `sizing_allowed=false`.
- **The curated 10 are not live.** All 10 entries equal the Yahoo **2026-11-13 close to full float precision** (USO 145.58, XLF 58.68, XLE 64.96, EFA 104.17, XLK 170.28, XLV 188.85, VLUE 189.18, XOP 184.80, KWEB 22.93, VCSH 77.25). The 0.00% PnL is `entry == current` on a Saturday, not a flat market (`01_audit/sub/D_non_crypto.md:226-230`).
- **Status/PnL contradiction:** QQQ pick entry 677.36, exit 679.63, `pnl_pct=+0.3351`, but `status=LOST`, `exit_reason=SL_HIT` (`01_audit/sub/D_non_crypto.md:232`).
- **Raw inventory:** 38 rows — 30 OPEN, 8 EXPIRED; median age 13.0 h; 8 >30 d; `current_price` null/0 on 11 (29%); `pnl_pct == 0` on 32 (84%); 15/30 OPEN frozen at 0%/null (`01_audit/sub/D_non_crypto.md:214-220`, `MASTER_AUDIT.md:101`).
- **Economic mislabel:** `VCSH` is a short-term corporate **bond** fund sitting in ETF while HYG/JNK/EMB sit in BOND (`01_audit/sub/D_non_crypto.md:244`).
- **The n=15 PF is not an edge.** Tier-2 floor is n≥100, WR≥50%, PF≥1.5; a class with n<100 must not feed EDGE, readiness, or "best class" ordering (`01_audit/recommendations/per_asset_class/equity_etf.md:326-334`).

### 1.4 Peer claims that touch ETF

| Claim | Source | Disposition |
|---|---|---|
| Variant-C selector: ETF n=120, PF 1.21, +26.5 pp | `04_peer_reviews/FP2_deepAI_profitable_v1.md:86` | **FALSIFIED as stated.** The +98.7 pp aggregate is **gross**; no slippage is subtracted, and 237 trades × 0.1–0.2% = 24–47 pp of cost (`FP2:290-300`). The book is long-biased into a rising market with no beta adjustment (`FP2:307-310`). Search family ≥54 → p≈0.06–0.17 (`FP2:313-330`). Re-running the same script on the only available same-schema payload gives **PF 0.906, −134.5 pp** (`FP2:636-640`). |
| ITERATION-005: diversified vol-targeted trend "PROVEN", Sharpe 2.13 (CI 1.25–3.25, t=5.56) | `04_peer_reviews/FP5_peer_final_folders.md:40-41,81,118` | **FALSIFIED as proof.** Buy-and-hold of the same 10 assets had Sharpe ≈2.2; t=5.56 tests "mean > 0", which beta passes. Independent TSMOM365 OOS Sharpe **0.57**, null p=0.200; PF 1.40 is a **bar ratio**, not trade PF, and is below the project's own 1.5 gate. |
| ETFs PF 0.022 / WR 2.3% (quick-win doc) | `04_peer_reviews/FP1_flaxen_hair_mega_mutation.md:219` | Consistent in direction with the intrabar truth (PF 0.0216) but **`UNVERIFIED`** as a committed artifact. Use the intrabar evidence instead. |

### 1.5 What ETF has never tested here

- No volatility-risk-premium test: covered calls, put-writing, variance/vol risk premium, VIX term structure.
- No risk-parity / inverse-vol multi-asset allocation (H18 is vol-targeted TSMOM with cash, not risk parity).
- No long/short TSMOM (H18 is long/flat; the short leg is where crisis alpha usually lives).
- No ETF-flow / creation-redemption signal.
- No factor-ETF rotation (MTUM/QUAL/VLUE/USMV/SPLV).
- No ETF-vs-constituent or ETF-vs-NAV arbitrage.
- No total-return (dividend-included) test of anything.

The last point matters: the entire ETF evidence base is **price-only**, which biases every long-only result downward relative to cash and makes cross-family comparisons unreliable (see §7.2).

---

## 2. Where an edge could actually exist

| Mechanism | Signal | Why it can persist | Capacity | Verdict for this repo |
|---|---|---|---|---|
| **Volatility risk premium** | Sell 1-month ~2% OTM calls / cash-secured puts; roll monthly | Insurance demand; investors pay up for crash protection; VRP is structurally positive but crash-convex | **High**: SPY/QQQ options are among the deepest markets; $1B+ plausible | **Best untested candidate.** Independent of price momentum; different failure mode (short convexity) than everything already tested |
| **Risk parity / vol targeting** | Inverse-vol weights across equity/bond/credit/gold/commodity ETFs | Diversification + volatility clustering; rebalancing premium | **High** | Cheap to test; but 2022 showed the equity-bond correlation regime break; low prior in a rate-cut/bull window |
| **TSMOM long/short** | 12m trend, long/short, vol-targeted | Crisis alpha, behavioural under/over-reaction | **High** | H18 long-only already failed (WF 0.37); the short leg may help in drawdowns but hurts in a bull |
| **ETF flows** | Shares-outstanding / creation-redemption flows; buy extreme outflows | Flow-driven price pressure and subsequent reversal | **Limited**: $10–100M; data latency and flow endogeneity | Data not held; needs issuer daily shares + NAV |
| **Factor-ETF rotation** | 12-1 momentum across MTUM/QUAL/VLUE/USMV/SPLV | Factor momentum / style persistence | **High** | Short history (most factor ETFs launched 2011–2013); already implicitly covered by ETF XS momentum which failed |
| **Cross-sectional momentum / reversal / rotation** | Price-based | — | — | **Already falsified here** (H5, H16–H19, H8/H11/H12) |
| **Dividend / quality factor ETFs** | Yield + quality screens | Value/quality premium | High | Untested but low incremental information over E-class equity factors |

Capacity figures in the table above are order-of-magnitude planning estimates, not measurements from this repo.

**Capacity summary.** ETF strategies are generally *more* capacity-friendly than single-stock strategies, which is exactly why surviving ETF anomalies are arbitraged quickly. The realistic edge is a **risk-premium harvest** (VRP, trend, risk parity) that is capacity-tolerant but offers modest Sharpe improvement over a well-chosen benchmark — not a market-beating alpha.

**Benchmark discipline is the binding issue.** H16 was judged against a 50-ETF equal-weight basket with Sharpe 1.18; H18 against a 60/40 SPY/AGG with 0.99; H8–H12 against a 10-sector equal-weight with 1.09. These are different hurdles. A candidate must declare its benchmark **ex ante**, match its average exposure/beta, and report excess return and excess Sharpe — otherwise the comparison is meaningless.

---

## 3. Ranked hypotheses (evidence × feasibility)

Scoring: **Evidence** = strength/robustness of the published mechanism plus in-repo evidence (1–5); **Feasibility** = keyless data availability, build cost, cost survival, sample size (1–5). Product ranks the list.

| Rank | ID | Hypothesis | Evidence | Feasibility | Score |
|---:|---|---|---:|---:|---:|
| 1 | **T1** | Volatility-risk-premium overlay (covered calls / put-writing) | 4 | 4 | **16** |
| 2 | **T2** | Risk parity / inverse-vol multi-asset | 3 | 5 | **15** |
| 3 | **T3** | TSMOM long/short, vol-targeted | 3 | 5 | **15** |
| 4 | **T4** | Factor-ETF rotation | 2 | 5 | **10** |
| 5 | **T5** | ETF flow / creation-redemption reversal | 3 | 2 | **6** |

T2 and T3 tie; T2 ranks higher because its data and implementation are simpler and it has not already been partially tested in this repo.

### T1 — Volatility-risk-premium overlay (rank 1, pre-registered below)

- **Signal:** Monthly sell of a ~30-DTE, ~2% OTM call against a fully collateralised SPY position (buy-write), or a cash-secured put; roll at expiry.
- **Universe:** SPY (primary), QQQ (replication). Benchmark: SPY total return and a beta-matched 60/40 SPY/cash sleeve.
- **Rebalance:** monthly, ~34 rolls in the 2.87-year OOS — just clears the n≥30 gate.
- **Mechanism:** structural demand for downside insurance makes implied volatility exceed realised volatility on average; the seller earns the premium and accepts crash convexity.
- **Data required:** CBOE daily index histories (`BXM_History.csv`, `PUT_History.csv`) for a keyless mechanism check; SPY/QQQ option chains for the implementable test; dividend-adjusted SPY total return.
- **Costs / capacity:** ~10 bps of notional per roll (half-spread + commission on a 2% OTM SPY call); stress 2×; capacity $1B+; margin fully collateralised.
- **Failure mode:** crash convexity (Feb-2018, Mar-2020 style), VRP compression in calm markets, upside truncation in a strong bull — 2024–26 is the *least* favourable window for raw return, so the test must be risk-adjusted and beta-matched.

### T2 — Risk parity / inverse-vol multi-asset (rank 2)

- **Signal:** inverse-volatility weights across SPY, TLT, IEF, LQD, HYG, GLD, DBC, VNQ, with a 10% portfolio vol target; monthly rebalance.
- **Universe:** 8–10 liquid multi-asset ETFs.
- **Rebalance:** monthly.
- **Mechanism:** diversification and volatility clustering; rebalancing premium; risk balancing rather than capital balancing.
- **Data required:** total-return ETF prices (dividends included).
- **Costs / capacity:** 5 bps/side; high capacity; leverage/financing must be modelled, not assumed free.
- **Failure mode:** 2022-style positive stock-bond correlation; rate-regime sensitivity; leverage cost erases the premium.

### T3 — TSMOM long/short, vol-targeted (rank 3)

- **Signal:** 12-month total return sign; long positive-trend assets, short negative-trend assets; inverse-vol weights; 10% vol target.
- **Universe:** 20–50 liquid ETFs across equity, bond, credit, commodity, real estate.
- **Rebalance:** monthly.
- **Mechanism:** time-series momentum and crisis alpha; behavioural under/over-reaction; risk management.
- **Data required:** total-return prices.
- **Costs / capacity:** 5 bps/side; high capacity; short leg borrow is small for liquid ETFs.
- **Failure mode:** whipsaw in range-bound markets; 2024–26 trendless equity/bond rotation; the long-only version already failed WF 0.37.

### T4 — Factor-ETF rotation (rank 4)

- **Signal:** 12-1 momentum across MTUM, QUAL, VLUE, USMV, SPLV, size/value/quality ETFs; top 2, monthly.
- **Universe:** US factor ETFs (inception mostly 2011–2013).
- **Rebalance:** monthly.
- **Mechanism:** factor momentum / style persistence.
- **Data required:** total-return prices; point-in-time inception-aware universe.
- **Costs / capacity:** 5 bps/side; high capacity.
- **Failure mode:** factor crowding, style reversals, short sample (~13 years, of which only 2.87 is OOS).

### T5 — ETF flow / creation-redemption reversal (rank 5)

- **Signal:** weekly change in shares outstanding / fund flows; buy extreme-outflow ETFs, sell extreme-inflow.
- **Universe:** liquid US ETFs with reliable daily shares-outstanding data.
- **Rebalance:** weekly.
- **Mechanism:** flow-driven price pressure and subsequent reversal; ETF arbitrage limits.
- **Data required:** issuer daily shares outstanding + NAV/premium; not held here → `UNVERIFIED`.
- **Costs / capacity:** 5–10 bps/side; capacity $10–100M; crowding and data latency.
- **Failure mode:** flow endogeneity (flows follow returns), stale shares data, premium/discount noise.

---

## 4. Pre-registered next experiment — `T-VRP-1`

**One experiment. Frozen before any result is inspected. Any change creates T-VRP-2 and a new forward ledger.**

### 4.1 Design

| Item | Specification |
|---|---|
| **Hypothesis** | A systematic SPY buy-write (short ~2% OTM 30-DTE calls) earns a positive net volatility risk premium and beats a **beta-matched** benchmark after costs, without exceeding a 25% drawdown budget. |
| **Signal** | On the third Friday of each month, sell the nearest 30-DTE SPY call with strike ≈ 2% above spot (delta ≈ 0.25–0.35), fully collateralised by 100% SPY. Hold to expiry; cash-settle; re-sell next month. Replication sleeve: QQQ, 50% capital cap. |
| **Universe** | SPY primary; QQQ replication. No single-name options, no leveraged ETFs. |
| **Rebalance** | Monthly; ~34 rolls in OOS (clears n≥30 by 4). |
| **Mechanism** | Implied volatility exceeds realised volatility on average because investors pay for crash protection; the seller harvests the premium and bears tail risk. |
| **Train / OOS** | Train ≤ **2023-12-31**; OOS ≥ **2024-01-01** through the last complete session. Strike/DTE/roll rules fixed here; no OOS tuning. |
| **Costs** | **10 bps of notional per roll** (half-spread + commission); stress **2× = 20 bps/roll** (≈2.4%/yr). Underlying SPY rebalance 5 bps/side. |
| **Execution** | Strike selected from the prior close; roll executed at the third-Friday close; if a holiday, next session. No same-bar fills; lag test rolls one month later. |
| **Concurrent capital** | 100% SPY notional, fully collateralised, **no leverage**; QQQ sleeve ≤ 50%; one roll per month; cash buffer 2%. |
| **Data source (exact)** | CBOE historical index CSVs: `https://cdn.cboe.com/api/global/us_indices/daily_prices/BXM_History.csv` and `.../PUT_History.csv` (both total-return index constructions) for the keyless mechanism check. Implementable test: SPY/QQQ option chains from CBOE delayed quotes or Nasdaq option chain, plus dividend-adjusted SPY from Nasdaq prices + `https://api.nasdaq.com/api/quote/SPY/dividends`. |
| **Benchmarks** | (a) SPY **total return**; (b) **beta-matched** 60/40 SPY/cash sleeve (match the strategy's realised beta, not a fixed 60/40); (c) T-bill. Report all three. |

### 4.2 Gates (all must pass; DSR at true N)

| # | Gate | Threshold |
|---:|---|---|
| 1 | Net OOS Sharpe (excess of cash) | ≥ **1.0** and ≥ **beta-matched benchmark + 0.30** |
| 2 | Net OOS CAGR / total return | > 0 and > beta-matched benchmark, **total-return basis** |
| 3 | Sample | ≥ **30 monthly rolls** (OOS provides ~34) |
| 4 | **True DSR at all trials** | N = 38 (prior effective) + 15 (T1–T5 × 3 variants) + 12 (this grid) = **65**; DSR ≥ **0.95**; stress at **N=130** |
| 5 | **CSCV PBO** | 16 blocks, purge/embargo 1 month; **PBO < 0.50** |
| 6 | **SPA / Reality Check** | Stationary bootstrap, 5,000 resamples, block 20; **p < 0.05** across the T-family |
| 7 | **2× cost** | Net Sharpe ≥ **0.5** and > beta-matched benchmark |
| 8 | **Execution lag** | Roll one month later: Sharpe ≥ **1.0** and > benchmark |
| 9 | Drawdown / tail | OOS max drawdown **≤ 25%**; worst month reported; crash stress on 2018-02 and 2020-03 labelled **in-sample** |
| 10 | Concentration | No single month contributes > 50% of total excess return; ex-top-3-month DSR ≥ 0.95 |
| 11 | Total-return consistency | Result must not flip sign between price-only and dividend-adjusted data |
| 12 | Economic significance | Net excess over T-bills ≥ **2%/yr** on capital actually committed (not notional) |

### 4.3 Pre-registered expected result

The 2024–2026 window is a **strong bull with low realised volatility** — the worst environment for a covered-call overlay on *raw* return, and a favourable one for premium harvesting on *risk-adjusted* return. The honest prior is: **beats SPY total return on Sharpe but not on CAGR; likely fails gate 1 against the beta-matched benchmark by a small margin; almost certainly fails gate 12.** A failure here does not disprove the VRP; it proves it cannot be promoted on this OOS, and the mechanism must be re-tested on a longer or different window with frozen parameters.

---

## 5. Kill criteria

Stop the program (not just the candidate) if any of these hold:

1. **No risk-adjusted excess.** Net Sharpe < beta-matched benchmark + 0.30 for every variant.
2. **No multiple-testing survival.** DSR < 0.95 at N=65.
3. **PBO ≥ 0.50** on the frozen candidate matrix.
4. **SPA p ≥ 0.05** across the family.
5. **Cost death.** 2× cost net Sharpe < 0.5.
6. **Lag death.** One-month-later roll Sharpe < 1.0.
7. **Dividend flip.** Sign reverses when total-return data replaces price-only data.
8. **Concentration.** > 50% of excess from one month, or ex-top-3-month DSR < 0.95.
9. **Tail budget breach.** OOS max drawdown > 25%, or a single-month loss > 10%.
10. **Underpowered.** Fewer than 30 rolls in OOS — report as inconclusive, not negative.

---

## 6. What NOT to do

1. **Do not quote ETF PF 1.8358 (n=15) as evidence of a profitable class.** Intrabar truth is PF 0.0216 with 84.99× daily inflation; the class is `INSUFFICIENT_SAMPLE`.
2. **Do not run more cross-sectional momentum, reversal, rotation, or dual-momentum variants.** H5, H16–H19, H8, H11 and H12 have exhausted these families; more variants only inflate N.
3. **Do not mix benchmarks.** A 3-ETF book compared to a 50-ETF equal-weight basket (or a 60/40) is not a like-for-like test. Declare the benchmark and match beta/exposure ex ante.
4. **Do not use price-only Nasdaq data for total-return claims.** The loader is price-only; dividends are missing (see §7.2).
5. **Do not build a signal from the 10 curated ETF rows.** All 10 equal the 2026-11-13 close to float precision and were never repriced.
6. **Do not use the daily-resolved PnL / EDGE feed.** It is 120 d median-aged, capped at 3,500 rows, and inflates ETF PF by 84.99×.
7. **Do not short KWEB/EWZ/EWY without a borrow and currency cost.** The v3 cross-section includes country ETFs whose short leg is not free.
8. **Do not treat H18's 1.00 vs 0.99 as an edge.** Walk-forward Sharpe is 0.37 vs 0.61; the in-sample fit does not survive.
9. **Do not ignore 2024–26 beta.** A long-only ETF result in this window is mostly market exposure; require beta-matched excess.
10. **Do not declare a VRP strategy "proven" on 34 monthly rolls** — it clears n≥30 by four observations and has no crisis observation in the OOS.

---

## 7. Confounds that must be addressed

### 7.1 The 2024–2026 bull-market confound

- The OOS is **2.87 years** (2024-01-01..2026-11-14; 1,049 rows in `runs/v3/oos_returns.csv`) — **one regime**.
- Benchmark performance was exceptional: 50-ETF equal-weight **Sharpe 1.18 / CAGR 14.8%**; 60/40 SPY/AGG **0.99 / 9.8%**; 10-sector equal-weight **1.09 / 13.5%** (`runs/v3/REPORT.md:88-136`, `runs/v2/REPORT.md:17-25`).
- **H16 illustrates the trap:** CAGR 29.6% vs benchmark 14.8%, but Sharpe 0.98 vs 1.18 and max drawdown −33.3%. On raw return it "wins"; on risk-adjusted return it loses. Reporting only CAGR would have produced a false positive.
- **Power:** using Lo (2002), SE(annualised Sharpe) ≈ √((1 + 0.5·S²)/T). With S≈1.1 and T=2.87, **SE ≈ 0.75** (derived). The H16 gap of 0.20 Sharpe is **0.26 SE** — not distinguishable from zero. "NOT_PROVED" means *underpowered*, not *proven absent*.
- **Rate regime:** the OOS 13-week T-bill averaged **4.38%** vs **0.90%** in the 2016–17 holdout (`runs/v2/VERDICT.md:49`). Cash-heavy strategies (H8, H11, H12, H18) get a regime-specific boost.
- **Required controls:** beta-matched benchmark; excess-of-cash Sharpe; sub-period sign consistency (2024 / 2025 / 2026 YTD); report raw and risk-adjusted results side by side; do not use the 2016–17 holdout as OOS.
- **For T1 specifically:** a covered-call overlay has **beta < 1** and capped upside, so a bull market mechanically hurts raw return. It must be judged against a beta-matched sleeve, not against SPY alone. A raw-return loss in 2024–26 is expected and is not, by itself, a refutation.

### 7.2 Dividend omission in Nasdaq price-only data

- `data/loader.py:186-215` (`nasdaq_daily`) returns **`tradesTable.close` only** — price-only, ~10-year cap, no dividends. `SCORECARD.md:12` records this explicitly (data provenance 7/10: "Nasdaq price-only, no dividends").
- **Direction of bias:** every long-only ETF benchmark and strategy is **understated** by its distribution yield. The cash sleeve is **not** (the 13-week T-bill series is a coupon-equivalent yield, i.e. a total return). This systematically **favours cash-augmented strategies** (H8, H11, H12, H18) and **penalises** income-heavy ETFs (HYG, LQD, TLT, VNQ, XLU, XLP).
- **Magnitude:** for bond, high-yield, REIT and dividend-equity ETFs the omission is on the order of **hundreds of basis points per year** — one to two orders of magnitude larger than the **5 bps/side** cost assumption. Exact per-symbol yields for this 50-ETF universe are `UNVERIFIED` here and must be sourced; the qualitative conclusion does not depend on the precise figure.
- **Signal contamination:** ex-dividend price drops create artificial negative daily returns (monthly for bond ETFs), which can trigger RSI2/reversal entries and stop-outs. This affects H8/H11/H12/H17 mechanically, not just their benchmarks.
- **Consistency trap for T1:** CBOE `BXM`/`PUT` are **total-return** index constructions, while the Nasdaq SPY series is price-only. Never compare the two directly. Build a dividend-adjusted SPY total-return series and apply the same dividend treatment to the overlay and the benchmark.
- **Required fix before any promotion:** re-run every ETF candidate on **total-return (adjusted) prices**; publish the per-symbol dividend yield and a price-only-vs-total-return delta; a result that survives only on price-only data is killed.

---

## 8. UNVERIFIED / missing

- `03_research/profitability/NEXT_DATA_REQUIREMENTS.md` is referenced by `05_final/reference_final_2026_11_14/FINAL_SYNTHESIS.md:170` but **does not exist** in the tree.
- Per-symbol dividend/distribution yields for the 50-ETF universe.
- SPY/QQQ option-chain history and live bid-ask spreads (needed for the implementable T1 test); CBOE index histories are the fallback.
- Whether `BXM`/`PUT` histories are available from the exact CBOE URL at run time.
- ETF shares-outstanding / flow data for T5.
- The `financials` inclusion rule for E-class joins and the precise point-in-time EPS coverage (see EQUITY.md).
- Whether any genuinely unseen OOS remains: the 2024–2026 window has been inspected for all eight v3 candidates.
- The exact producer of the n=15 policy-clean ETF cohort and why it disagrees with the n=45 intrabar cohort.

---

## 9. Evidence index

| File | Used for |
|---|---|
| `01_audit/MASTER_AUDIT.md` | Class status, per-class significance, closed-pick ages, PEAD/QQQ integrity |
| `01_audit/sub/D_non_crypto.md` | ETF curated/raw/closed numbers, 84.99× inflation, VCSH mislabel |
| `01_audit/sub/E_statistical.md` | ETF n=15 z=+1.81, Bonferroni threshold |
| `01_audit/recommendations/per_asset_class/equity_etf.md` | P1-6 ETF significance policy, do-not-do list |
| `03_research/profitability/runs/v1/REPORT.md` | H5 dual momentum |
| `03_research/profitability/runs/v2/REPORT.md` | H8–H12 sector rotation |
| `03_research/profitability/runs/v3/REPORT.md` | H16–H19 detail (Sharpe, WF, CPCV, PBO, SPA, lag, 2× cost) |
| `03_research/profitability/runs/v3/VERDICT.md` | Family verdict, SPA p=0.488, PBO 0.36 |
| `03_research/profitability/HYPOTHESES.md` | Full 23-candidate registry |
| `03_research/profitability/PROTOCOL_v3.md` | Universe/cost/gate definitions (40-vs-50 universe note) |
| `03_research/profitability/run_v3.py` | Executed 50-ETF universe and benchmark construction |
| `03_research/profitability/data/loader.py` | Price-only Nasdaq loader |
| `03_research/profitability/SCORECARD.md` | Data-provenance and version results |
| `04_peer_reviews/FP2_deepAI_profitable_v1.md` | Variant-C ETF claim and its falsification |
| `04_peer_reviews/FP5_peer_final_folders.md` | ITERATION-005 trend claim correction |
| `04_peer_reviews/FP1_flaxen_hair_mega_mutation.md` | Unverifiable per-class quick-win numbers |
| `05_final/reference_final_2026_11_14/FINAL_SYNTHESIS.md` | Program-level verdict and next steps |

---

## Addendum (final_v2, FP6)

**Cost gate.** Do not emit an ETF pick whose class-average PnL is under **3× round-trip cost**;
ETF cost is currently **267% of PnL**, so the class fails outright.

**Horizon.** Intraday ETF picks should stop; the defensible horizon is monthly (or event-driven
with a beta-matched benchmark). No more price-only ETF sweeps on the same window.
