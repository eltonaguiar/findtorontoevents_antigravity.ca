# MUTUAL FUNDS — Profitability Playbook

**PRIORITY: LOW**
**EXPECTED EDGE: none as a signal class. Mutual funds are not a tradable intraday instrument; there is no `current_price`, no TP/SL, and no resolver contract. The only durable, evidence-based "edge" is fee arithmetic — a lower expense ratio is a near-deterministic improvement in net return — plus asset allocation, which is beta, not alpha. A long-horizon allocation sleeve is defensible as a product; it is not a proved edge. Fund-selection persistence is weak and currently untestable without survivorship-free data (UNVERIFIED).**

- Class owner: PC3 (per-asset-class profitability planner)
- Status clock: 2026-11-14T21:15Z
- Evidence root: paths below are relative to `final_v2/finpredict-v2/`
- Rule: every count is copied from the named evidence file. Market-structure knowledge and absent data are labelled `UNVERIFIED`.

---

## 1. Current evidence — what the repo actually contains

### 1.1 Production state: NOT BUILT

| Check | Result | Source |
|---|---|---|
| Occurrences of "mutual" in `dashboard_payload.json` | **0** | `01_audit/sub/D_non_crypto.md:402`; `bond_mutual_funds.md:26` |
| Live / active / closed MF picks | **0 / 0 / 0** | `D_non_crypto.md:403,411-412` |
| MF in `summary_picks`, `pf_registry`, `money_ready_verdict`, `audit_surface_truth` | **No** | `D_non_crypto.md:402` |
| `CANONICAL_ASSET_CLASSES` | **7 classes, MF excluded** | `alpha_engine/money_ready_verdict.py:226`; `bond_mutual_funds.md:146` |
| `asset_class.py` MF mapping | **None** | `bond_mutual_funds.md:147` |
| `/audit/mutual-funds.html` deployed | **No** | `bond_mutual_funds.md:27`; `equity_etf_bond_mf_review.md:247` |
| `findmutualfunds2/` | **3 PHP debug files only** | `bond_mutual_funds.md:32`; `equity_etf_bond_mf_review.md:253` |
| DB families | `mf_` / `mf2_` recognised for **reconnaissance only** | `tools/recon_uncharted_tables.py:29-30` |
| Spec surface | `multi_asset/portfolio_defs.py:382-395,677-720` defines a `mutual_fund` universe and `tactical_fund_rotation`, but **no live module imports `portfolio_defs`** | `bond_mutual_funds.md:30,145` |

**Verdict:** MUTUAL FUNDS is a **planning artifact**, not a live asset class. It has no picks, no
page, no emitter, no resolver path, and no taxonomy entry.

### 1.2 The untracked prototype — corrected evidence

An earlier version of the per-class plan said the prototype "has never produced an output file."
That was wrong. At 16:25Z the **main checkout** (not `origin/main`, not this worktree) contains:

| Artifact | State | Size / detail | Source |
|---|---|---|---|
| `alpha_engine/mutual_fund_ranker.py` | **untracked** | 23,931 B; output path misspelled `mutut_fund_rankings.json` (line 53) | `equity_etf_bond_mf_review.md:244`; `D_non_crypto.md:404-407` |
| `alpha_engine/data/mutual_fund_metadata.csv` | **untracked** | 5,983 B / 38 lines (**37 funds** + header) | `equity_etf_bond_mf_review.md:245` |
| `audit_dashboard/data/mutut_fund_rankings.json` | **untracked output** | 39,508 B | `equity_etf_bond_mf_review.md:249` |
| `audit_dashboard/data/mutual_fund_nav_cache/` | **untracked cache** | populated CSV cache (~2.8 MB dir) | same |
| `audit_dashboard/mutual-funds.html` | **untracked page** | 206,841 B | `equity_etf_bond_mf_review.md:246` |
| `reports/mutual_fund_results.json` | **untracked results** | `generated_at 2026-10-23T04:07:06Z` | `equity_etf_bond_mf_review.md:177` |

**None of this is on `origin/main`, none of it is wired into the live pipeline, and the ranker has no
coverage gate** (`bond_mutual_funds.md:470`). The conclusion — *not built in production* — is
unchanged; only the "never produced an output" wording was wrong
(`equity_etf_bond_mf_review.md:181,233`).

### 1.3 Two pages, and a trap

- `audit_dashboard/funds.html` **exists on `origin/main`** (206,841 B, title **"Strategy Funds"**).
  It is **not** a mutual-fund page and must not be wired as one
  (`equity_etf_bond_mf_review.md:248`; peer action M5 at `:119`).
- `audit_dashboard/mutual-funds.html` (untracked) happens to be the **same 206,841 B**. Whether the
  two files are identical or merely coincidentally the same size is **UNVERIFIED**; treat them as
  distinct until diffed.

### 1.4 Why the pick schema cannot hold a mutual fund

`multi_asset/portfolio_defs.py:714-718` states that mutual funds settle **T+1 and price only at the
NAV close**. The entire audit pipeline is built on an intraday pick with `entry_price`,
`current_price`, TP/SL, and a resolver. A once-daily NAV instrument has:

- no intraday mark, so `current_price` can only be yesterday's NAV (a stale price presented as a live
  one — exactly the frozen-price artifact audited in BOND/ETF);
- no intrabar TP/SL path, so the resolver's terminal states are meaningless;
- no realistic stop-loss, because the next executable price is tomorrow's NAV.

Forcing MF into the pick schema would manufacture the same artifact the audit exists to remove.

---

## 2. Where an edge could actually exist — and why this is not a signal class

### 2.1 The five candidate families

| Family | Mechanism | Evidence strength | Feasibility here |
|---|---|---|---|
| **Expense ratio** | Net return = gross return − fees. Within a category, the lowest-cost fund captures the most of whatever the category earns. | **Strong and near-mechanical.** The relation between cost and net performance is one of the most robust findings in the fund literature. | **High** — expense ratios are public in every prospectus. |
| **Share-class selection** | The same portfolio is sold in classes with different fee loads (retail vs institutional/admiral). | **Deterministic arithmetic**, not a forecast. | **High**, but it is an operational fix, not an edge. |
| **Asset allocation** | Allocation across equity/bond/other explains most of the variance of a diversified portfolio's return. | **Strong** (Brinson-style decomposition is standard), but it is **beta**, not alpha. | **High** — but benchmark-relative alpha is ~0 by construction. |
| **Fund-selection persistence** | Past risk-adjusted alpha persists. | **Weak post-1990s**; what persists is mostly fees and style, not manager skill. | **Low** — needs survivorship-free CRSP/Compustat; free data is biased. |
| **Fund flows** | Flows predict returns (contrarian or momentum depending on horizon). | **Moderate in the literature.** | **Very low** — needs NSCC/ICI flow data, which is not free or keyless. `UNVERIFIED` feasibility. |

### 2.2 The honest conclusion about "edge"

- **Expense ratio is not a prediction; it is arithmetic.** Choosing a 0.04% index fund over a 0.60%
  active fund in the same category raises net return by ~0.56%/yr with certainty, before any
  performance forecast. That is real, but it belongs in a **product/fee decision**, not in a
  "profitable signal" claim.
- **Asset allocation is beta.** A 60/40 sleeve earns the market's return; it does not beat a 60/40
  benchmark except by factor tilts and rebalancing, both of which are small and well known.
- **Persistence is the only true "alpha" hypothesis**, and the data needed to test it honestly
  (survivorship-free, point-in-time) is not in this repo and is not free.
- **Mutual funds are not a day-trading class.** The audit's contract — pick, mark, TP, SL, resolve —
  has no meaning for a T+1 NAV instrument.

---

## 3. Hypotheses, ranked by evidence × feasibility

> Cost figures (expense-ratio bands, rebalancing bps) are market-structure estimates, not values
> measured in this repo (`UNVERIFIED` for any specific fund set).

### H-MF-1 — Expense-ratio selection within category  *(rank 1)*

- **Signal:** within each category, rank funds by expense ratio ascending; hold the cheapest
  low-cost index option.
- **Universe:** broad-market index funds / ETFs by category (US equity, international equity, US
  aggregate bond, TIPS, money market).
- **Rebalance:** annual (fees change rarely).
- **Mechanism:** deterministic fee drag. No forecasting.
- **Data required:** expense ratios from fund prospectuses / SEC filings / fund-company pages;
  category classification; **survivorship-free** fund list (the untracked metadata has 37 funds and
  its provenance is `UNVERIFIED`).
- **Costs / capacity:** the expense ratio *is* the cost; capacity is effectively unlimited at retail
  size.
- **Failure mode:** category mismatch (comparing an index fund to an active fund in a different
  style); ER floors (many index funds are already at 0.03–0.05%, so the remaining spread is small);
  survivorship bias if the fund list is drawn from today's survivors.

### H-MF-2 — Share-class optimization  *(rank 2)*

- **Signal:** map each holding to the lowest-cost share class of the *same* portfolio (e.g.
  institutional/admiral class) available to the investor.
- **Universe:** existing holdings.
- **Rebalance:** on eligibility change.
- **Mechanism:** pure fee arithmetic; identical portfolio, lower cost.
- **Data required:** share-class maps and eligibility minimums.
- **Costs / capacity:** none beyond the switch; capacity unlimited.
- **Failure mode:** eligibility minimums, platform availability, tax on switching in a taxable
  account. **This is an operational improvement, not an edge; it must not be marketed as alpha.**

### H-MF-3 — Low-cost allocation sleeve (glidepath / static mix)  *(rank 3)*

- **Signal:** none — a fixed or age-based allocation across 3–5 low-cost funds, rebalanced on a
  calendar.
- **Universe:** 3–5 broad index funds (e.g. US equity, international equity, US bond, TIPS, cash).
- **Rebalance:** monthly or quarterly.
- **Mechanism:** diversification and rebalancing; harvests the equity and term premia as beta.
- **Data required:** daily NAV.
- **Costs / capacity:** blended ER ≈ 0.03–0.10%; rebalancing ≈ 5 bps/event; capacity large.
- **Failure mode:** it is beta — it will not beat its own benchmark net of fees. Any "outperformance"
  is a factor tilt or a rebalancing bonus, and both are small and regime-dependent.

### H-MF-4 — Risk-adjusted persistence (Carhart 4-factor alpha)  *(rank 4)*

- **Signal:** trailing 36-month 4-factor alpha t-stat; hold the top decile next year.
- **Universe:** survivorship-free US equity mutual funds.
- **Rebalance:** annual.
- **Mechanism:** manager skill persistence.
- **Data required:** **CRSP Survivor-Bias-Free Mutual Fund Database** (paid) or an equivalent
  point-in-time source. Free Yahoo data is survivorship-biased and cannot test this.
- **Costs / capacity:** ER + turnover; capacity limited by the strategy's own AUM.
- **Failure mode:** the persistence literature's positive results are concentrated pre-1990 and are
  largely explained by fees and style; with biased data the test will produce a false positive.

### H-MF-5 — Fund-flow signal  *(rank 5)*

- **Signal:** contrarian on extreme outflows / momentum on inflows, at a 1–12 month horizon.
- **Universe:** fund categories.
- **Data required:** **NSCC / ICI weekly flow data** — not free, not keyless.
- **Costs / capacity:** low turnover; but the data is the blocker.
- **Failure mode:** infeasible today. Do not attempt with a proxy (ETF flows ≠ mutual-fund flows).

---

## 4. Pre-registered next experiment (only if the operator overrides the recommendation)

**Experiment MF-EXP-1: "Low-cost allocation sleeve vs 60/40, monthly, daily NAV."**
This is an **allocation product test**, not an edge proof. It must be labelled as such.

### 4.1 Data (named)

| Input | Source | Notes |
|---|---|---|
| Daily NAV | Fund-company NAV history / **Yahoo** (research only) | `nav_through` and `coverage_pct` required per fund; no survivorship-free claim |
| Universe | 5–10 low-cost index funds, fixed ex ante | e.g. US total market, international, US aggregate bond, TIPS, cash — the specific tickers must be listed in the pre-registration |
| Benchmark | **60/40** (60% global equity / 40% global bond) and cash | Must be a total-return benchmark |
| Metadata | `alpha_engine/data/mutual_fund_metadata.csv` (37 funds) **only after it is committed** | Currently untracked; provenance `UNVERIFIED` |

### 4.2 Design

- **Split:** train **≤ 2023-12-31**; OOS **2024-01-01 → 2026-11-13** = **35 monthly observations**.
- **Parameters (max 2):** equity/bond weight and rebalance frequency. No tactical timing.
- **Rebalance:** monthly, at the first NAV after month-end.
- **Execution:** trade at the **next published NAV (T+1)**; 1-month lag stress. No intraday assumption.
- **Concurrent capital:** 100% invested, **no leverage**.
- **Costs:** blended expense ratio + **5 bps** per rebalance; 2× stress = ER + 10 bps.

### 4.3 Gates — and the honest power caveat

The standard gates apply (DSR ≥ 0.95 at declared N, CSCV PBO ≤ 0.10 with T ≥ 1000 —
`docs/BACKTEST_ADMISSIBILITY_STANDARD.md:44` — SPA p < 0.05,
2× cost, 1-period lag, n ≥ 30). **But the binding constraint is statistical power:**

> 35 monthly OOS observations cannot support a DSR/PBO decision at any meaningful power. A 35×k
> returns matrix gives a CSCV PBO that is technically computable and practically uninformative, and
> `n ≥ 30` is met only by counting months, not independent bets.

Therefore:

- **This experiment cannot produce a "PROVED" verdict.** It can only produce a descriptive
  benchmark-relative result and a forward ledger.
- A credible persistence/allocation test needs **10+ years (≥120 months)** and a survivorship-free
  universe — which conflicts with the mandated OOS start of 2024-01-01.
- **Recommendation: do not run MF-EXP-1 as a proof attempt.** If an allocation sleeve is shipping as
  a product, run it as a **forward paper ledger** with a benchmark, and publish it as a product
  track record, not as an edge.

---

## 5. Kill criteria

Kill the mutual-fund **signal** program immediately if any of these hold (they all hold today):

1. **The proposal is to emit picks, signals, `current_price`, TP/SL, or win rates.** A T+1 NAV
   instrument cannot support them (§1.4). This is a structural kill, not a performance kill.
2. **The "edge" is fee arithmetic.** Expense-ratio selection is a product decision; marketing it as
   a signal is misrepresentation.
3. **The persistence test uses survivorship-biased data** (Yahoo, current fund list). Any positive
   result is a survivorship artifact.
4. **The sleeve cannot beat a 60/40 benchmark net of fees over a full cycle** — then it is a
   benchmark-hugging product and should be sold as such, with no alpha claim.
5. **NAV coverage < 90%, or `nav_through` older than 10 business days, or < 60 months of history per
   fund** — the coverage gate in `bond_mutual_funds.md:470` is the minimum.

---

## 6. What NOT to do

1. **Do not add MUTUAL FUNDS to `CANONICAL_ASSET_CLASSES` (`money_ready_verdict.py:226`) or to
   `_PER_ASSET_CLASSES` (`dashboard_generator.py:6763`).** That creates a permanently n=0 class and
   re-opens the vacuous-PASS bug (`bond_mutual_funds.md:600`).
2. **Do not build a mutual-fund pick emitter** to satisfy a class-count KPI. NAV-only instruments
   would get synthetic marks (`bond_mutual_funds.md:604`).
3. **Do not wire `audit_dashboard/funds.html`.** It is a "Strategy Funds" page, not a mutual-fund page
   (`equity_etf_bond_mf_review.md:119,248`).
4. **Do not copy the untracked prototype into production without review.** Its output path is
   misspelled (`mutut`), it has no coverage gate, and its `_pct_rank` returns a neutral 50 for a
   single fund (`bond_mutual_funds.md:470-472`; `D_non_crypto.md:407`).
5. **Do not deploy a live-looking page** until the "no `current_price` / `tp` / `sl` / `pnl_pct` /
   `win_rate`" invariant test passes in CI (`bond_mutual_funds.md:606`).
6. **Do not claim mutual-fund performance.** There are **0 picks and 0 resolved outcomes**; any
   number would be invented (`MASTER_AUDIT.md:404`).
7. **Do not use ETF flows as a proxy for mutual-fund flows.** They are different populations with
   different redemption mechanics.

---

## 7. Recommendation — `NOT_BUILT / de-advertise`

**Recommendation: keep MUTUAL FUNDS as `NOT_BUILT` and de-advertise it as an asset class. Do not
build a live pick surface. Optionally, and separately, build a long-horizon allocation sleeve with
daily NAV — explicitly not a signal class.**

### 7.1 Justification from evidence

1. **Nothing exists in production.** 0 payload occurrences, 0 picks, no taxonomy entry, no emitter,
   no resolver path, no deployed page (§1.1). The only implementation is an **untracked prototype**
   with a misspelled output path and no coverage gate (§1.2).
2. **The instrument cannot support the pipeline's contract.** NAV is struck once daily, T+1
   (`portfolio_defs.py:714-718`); `current_price`, TP/SL, and the resolver are structurally
   inapplicable. Forcing MF into the schema reproduces the exact frozen-price artifact the audit
   documents in BOND/ETF.
3. **The advertised surface is dead code.** `portfolio_defs.py` is not imported by any live module;
   removing the claim is a one-line edit, not a product removal (`bond_mutual_funds.md:456`).
4. **Adding the class re-opens the vacuous-PASS bug.** A new class with `activeCount=0` rendered a
   green PASS until the class-status fix; an MF tile would sit permanently at `INSUFFICIENT_DATA`
   while consuming UI and gate complexity (`equity_etf_bond_mf_review.md:165`).
5. **The only defensible "edge" is fees, not signals.** Expense-ratio selection is arithmetic
   (§2.2). It belongs in a product/fee decision, not in a profitability claim.
6. **The persistence hypothesis is untestable with available data.** It needs survivorship-free CRSP;
   free data guarantees a false positive.

### 7.2 If the operator overrides and wants a product

Build the **allocation sleeve**, not a pick class, with these hard invariants:

- **Artifact:** a weekly/monthly **NAV-only** ranking or allocation table. No `current_price`, no
  `tp`, no `sl`, no `pnl_pct`, no `win_rate`.
- **Coverage gate:** `coverage_pct ≥ 0.90`, `nav_through` ≤ 10 business days, ≥ 60 months of history
  per fund; on failure write `{"status":"DATA_GAP",...}` and **exit 2** — never write rankings.
- **Provenance:** every row carries `nav_through`, `coverage_pct`, `source`, `metadata_as_of`.
- **Banner:** "RESEARCH / ALLOCATION ONLY — NOT A PICK. NAV is end-of-day; no intraday TP/SL."
- **Benchmark:** 60/40 total return. Published as a **product track record**, never as a "proved
  edge".
- **No wiring:** the artifact must not be referenced by `dashboard_generator`, the resolver, or any
  sizing module (invariant test).

This is the smallest credible surface and it does not touch the pick schema
(`bond_mutual_funds.md:464-478`).

---

## 8. UNVERIFIED register

| Item | Why |
|---|---|
| Any mutual-fund performance number | 0 picks, 0 resolved outcomes; nothing to compute. |
| Whether the untracked ranker's output is trustworthy | Output and NAV cache exist untracked, but the coverage gate, `nav_through` freshness, and runtime behaviour are unverified (`equity_etf_bond_mf_review.md:295`). |
| Whether `mutual-funds.html` and `funds.html` are the same file | Both are 206,841 B; not diffed. |
| Provenance/content of `mutual_fund_metadata.csv` (37 funds) | Untracked; contents not validated. |
| Fund-selection persistence in 2024–2026 | Needs survivorship-free CRSP; not available. |
| NSCC/ICI flow data feasibility | Not free, not keyless; not tested. |
| Whether any consumer reads `summary_picks.json` beyond diagnostics | `MASTER_AUDIT.md:402`. |
