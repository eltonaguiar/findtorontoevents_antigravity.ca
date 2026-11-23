# UNMEASURED REGISTER — commission, PIT, capacity, and the rest

**Date:** 2026-11-23
**Purpose:** name exactly what this programme has *not* measured, why each gap matters, and
the precise test that would close it. A gap that is written down with an acceptance
criterion is a task. A gap that is not written down becomes an assumption — which is how
every defect found this week started.

Rule applied throughout: **an unmeasured quantity may gate a rejection, but may never
support a promotion.**

---

## 1. COMMISSION

| | |
|---|---|
| **Status** | **Tariff VERIFIED, fills NOT measured.** The Questrade schedule was read off Questrade's own pages on 2026-11-23: stock/ETF buy **$0**, sell **$0**, ECN **$0** on smart-routed orders, SEC fee `0.0000206 × sell notional`, FX **1.5%** only on currency conversion. |
| **Not measured** | Actual `commission + fees` booked on real fills. There is **no broker statement or fill log in this repo**. |
| **Why it matters** | A posted tariff is the *nominal* price. Venue fees, settlement FX spread and the SEC annual rate can all move the realised number. Our model could be structurally right and level-wrong. |
| **What would measure it** | Export a broker activity statement (CSV) covering **≥3 months** of real fills. Reconcile per-fill `commission + fees` against `CostModel` and report the residual in bp. **Acceptance: residual < 1 bp/trade on ≥50 fills.** |
| **Blocker** | Needs live account activity. Zero capital is sanctioned, so this cannot be closed from inside the programme — it needs the operator's own statements. |

## 2. POINT-IN-TIME (three separable gaps, do not conflate)

### 2a. Fundamentals filing dates
| | |
|---|---|
| **Status** | **Approximate.** The HML run used `period_end + 90 days` as a proxy for "publicly filed". EDGAR `companyfacts` carries the **actual `filed` date** — verified live: 268 of 268 AAPL `StockholdersEquity` facts carry one (coverage 2009-07-22 → 2026-11-03). The adapter parses `end` and **discards `filed`**. |
| **Why it matters** | AAPL FY2026 was `end=2026-09-26`, `filed=2026-11-03` — a **38-day** true lag, not 90. A 90-day assumption is conservative but imprecise, and imprecision cuts both ways on a rebalance boundary. |
| **What would measure it** | Persist EDGAR companyfacts to disk (path exists, never populated); parse **earliest** `filed` per `period_end`; implement `fundamentals_history_provider`. **Acceptance: for 500 names, every rebalance uses only facts with `filed ≤ date`, verified by a look-ahead test.** |
| **Effort / blocker** | ~1 day at 1 req/sec with a compliant SEC User-Agent. No blocker. |
| **Trap** | Use the **earliest** `filed` per `period_end`. Latest-filed back-fills **restated** values into periods before the restatement was public. Verified in the data: AAPL's FY2024 and FY2025 10-K facts both show `filed=2026-11-03`. |

### 2b. Universe survivorship
| | |
|---|---|
| **Status** | **NOT point-in-time.** The ticker list is today's S&P 500. Observed live: `EA`, `DFS`, `EQR` are in the list but return *"possibly delisted, no price data found"* and are silently dropped. |
| **Why it matters** | Value is supposed to own the names that get cheap *before* they recover or die. Dropping them biases HML **upward**. |
| **What would measure it** | Historical index membership by rebalance date. **Acceptance: per rebalance, report names in-membership at `t` and the count dropped for missing data.** |
| **Blocker** | No constituent-history source in the repo. Requires an external index-change history. |

### 2c. Spread time-mismatch
| | |
|---|---|
| **Status** | Spread measured on the **last ~5 trading sessions** and applied to a 2021–2026 backtest. |
| **Why it matters** | Spreads have broadly compressed, so current spreads **understate** historical cost. |
| **What would measure it** | Historical intraday quotes/bars. **Acceptance: spread estimated per-year, not once.** |
| **Blocker** | Minute bars are not available historically from the free providers used. Either buy historical intraday or accept and disclose. |

## 3. CAPACITY

| | |
|---|---|
| **Status** | **Essentially unmeasured.** What exists is a *size check*, not a capacity estimate: participation at $20k/name = **0.008%** of median ADV ($251M). |
| **Not measured** | (i) market impact at size; (ii) the dollar size at which impact equals the edge; (iii) borrow availability and rate for any short leg. |
| **Why it matters** | An edge of ~5 bp is destroyed by ~5 bp of impact. **We do not know at what size impact reaches 5 bp**, so we cannot state a capacity in dollars for anything. |
| **What would measure it** | Fit `impact = k · σ · √(Q/ADV)` and solve for the `Q` where impact equals the measured edge. **Acceptance: a capacity curve in dollars per name, with the coefficient's provenance stated.** |
| **Blocker** | The `k` must come from **our own fills** to count as measurement. Without live trading it is an imported coefficient — which this programme bans as evidence. Own fills need live trading; zero capital is sanctioned. |
| **Related, still open** | **Borrow rate** for HML's short leg (B3). Questrade does not publish it. Sensitivity known: 0.5%/yr on a 50% short leg = 25 bp/yr; 2%/yr = 100 bp/yr. Immaterial to the HML kill (net +0.02% vs 4.32%) but material to any family that *passes*. |

---

## 4. Other gaps found this session

| Item | Status | What would close it |
|---|---|---|
| COMMODITY / BOND execution cost | **PROXY** — 4.97 bp borrowed from EQUITY | Measure futures and bond execution the way EQUITY was measured |
| Mutual-fund / ETF **MERs** | Published ranges only, **not verified by us** | Pull fund fact documents / prospectus MERs for the specific share classes |
| CRYPTO carry under stress | 218 days, **no deleveraging episode** in the window | Multi-year archive incl. 2021-05, 2022-05, 2022-11 |
| Bond **credit** spreads | No data | HY/IG spread history |
| Options chain history | None | Any chain archive, then defined-risk tests |
| MF NAV / holdings | None | NAV + holdings history |
| Private credit / real assets | None | A private-credit index or REIT cash-flow series with PIT dates |
| Cross-class backtest generalisation | **One instrument per class** (AAPL, SPY, BTC-USD, EURUSD_X, GC_F, TLT) | Cross-section per class, equal-weighted |
| PBO coverage | Computed over **configs only**, not instruments | 2-D grid: instruments × configs |
| **Provenance ledger (T3)** | **The measurement backbone itself is unproven** — no CI run has ever written a ledger row. Root cause fixed (sparse-checkout), fix unverified | One real `alpha-engine-fast` run producing `n_records > 0` with chain intact |

---

## Priority order, by what it unblocks

1. **PIT 2a (filing dates)** — no blocker, ~1 day, and it is the only gap that improves a
   measurement we already trust enough to kill a strategy with.
2. **T3 verification** — until the ledger writes a row, every future "measured" result rests
   on a pipeline that has never been observed working.
3. **Capacity coefficient** — needed before any family that *passes* can be sized. Not
   needed for any kill.
4. **Commission fills** — needs operator statements; cannot be closed here.
5. **PIT 2b (universe)** — needs an external constituent history; blocks any future value
   test from being called PIT-clean.

Items 4 and 5 cannot be closed from inside this programme. Saying so is the point of the
register.

Zero capital sanctioned. Not investment advice.
