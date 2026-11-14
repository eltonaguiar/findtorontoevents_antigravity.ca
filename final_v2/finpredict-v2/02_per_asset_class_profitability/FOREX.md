# FOREX — Profitability Playbook

**PRIORITY: MEDIUM**
**EXPECTED EDGE: near-zero net for retail spot FX. The only defensible families are G10 carry (forward discount) and 12-month time-series momentum, harvested through listed currency ETFs or exchange-traded FX futures — never retail CFD/spot. Expected net-of-cost Sharpe is 0.2–0.5, i.e. below the project's own 1.0 gate; that expectation is a judgment, not a measurement, and is marked UNVERIFIED.**

- Class owner: PC3 (per-asset-class profitability planner)
- Status clock: 2026-11-14T21:15Z
- Evidence root: paths below are relative to `final_v2/finpredict-v2/`
- Rule: every count is copied from the named evidence file. Anything that is market-structure knowledge, an external estimate, or absent data is explicitly labelled `UNVERIFIED`.

---

## 1. Current evidence — what the repo actually contains

### 1.1 Population (verified)

| Metric | Value | Source |
|---|---:|---|
| `picks.active_raw` FOREX rows | **277** | `01_audit/sub/D_non_crypto.md:151`; `01_audit/recommendations/per_asset_class/forex_futures.md:16` |
| `OPEN` | 118 | same |
| `EXPIRED` / `_auto_expired` | 158 (57%) | `01_audit/sub/D_non_crypto.md:22` |
| `SL_HIT` | 1 | `forex_futures.md:19` |
| `picks.recent_closed` | 187 | `MASTER_AUDIT.md:264` |
| `pnl_pct == 0.0` | 273 / 277 | `forex_futures.md:21` |
| `current_price` null/0 | 242 / 277 | `forex_futures.md:22` |
| OPEN frozen (`pnl==0` and price null or == entry) | **93 / 118 (78.8%)** | `forex_futures.md:23` |
| Unique IDs | 210 (40 duplicate-ID groups, 67 extra rows) | `01_audit/sub/D_non_crypto.md:168` |
| Oldest parseable row | 2026-02-20 (267.3 d) | `forex_futures.md:24` |

### 1.2 The four defects named in the brief, with exact definitions

1. **0 / 277 pass the advertised block.** The PR #6 allowlist
   `_FOREX_ALLOWED = frozenset({"cta_cross_asset_tsmom", "forex_carry", "forex_carry_g10"})`
   lives in `evaluate_non_crypto_candidate()` (`alpha_engine/non_crypto_policy.py:698-741`) and has
   **zero call sites repo-wide**. The live gate `passes_non_crypto_policy()` (`:1026-1040`) composes
   only the FX session + ATR gates and never sees the allowlist. Recomputed against the live payload:
   **0 of 277 rows pass**. Four retired strategies supply ~95/277 rows (not one).
   Sources: `MASTER_AUDIT.md:113`; `forex_futures.md:203-246`; `04_peer_reviews/forex_futures_ci_review.md:93`.

2. **105 / 277 date-only timestamps.** Precisely: **105/277 rows carry a date-only `entry_time`**
   (not 12 — 12 is the count of date-only `timestamp` fields), and **44 more carry
   `YYYY-MM-DD HH:MM:SS EST` strings that both `datetime.fromisoformat` and
   `universal_pick_resolver._parse_timestamp` reject**. The 44 are *unparseable*, not "undated": the
   resolver simply skips their hold/TIME_EXIT branch. Sources: `MASTER_AUDIT.md:112,435`;
   `forex_futures_ci_review.md:22`; `audit_trail/universal_pick_resolver.py:743-755`.

3. **44 non-FX/ETF rows — and one additional contaminant.** Exactly **44 currency-ETF rows**
   (FXA 13, CEW 10, UUP 9, FXC 5, FXY 4, FXE 2, FXB 1) plus **5 `EURUSDT` crypto rows** =
   **49/277 (17.7%) not spot FX**. All 44 ETFs were emitted under *equity* strategy names
   (`Quality Compounders` 36, `Value + Quality` 4, `Consecutive Beats` 4).
   Sources: `D_non_crypto.md:79,167`; `forex_futures.md:27-28,114-129`.

4. **Duplicate groups.** **40 duplicate-`id` groups → 67 extra rows**, and **67 duplicate
   `symbol+strategy+direction` groups → 198 extra rows**. Example:
   `consensus_USDJPY=X_SELL_20261114_1424` appears twice. Separately, **10 symbols carry both LONG
   and SHORT rows simultaneously** inside the same class. Sources: `D_non_crypto.md:168-169`;
   `MASTER_AUDIT.md:114`.

### 1.3 Honest performance (policy-clean, not curated)

| Metric | Value | Source |
|---|---:|---|
| n (policy-clean) | **438** | `MASTER_AUDIT.md:122` |
| Win rate | **35.62%** | same |
| Profit factor | **0.8339** | same |
| WR z vs 50% | **−6.02** | `MASTER_AUDIT.md:324` |
| Survives Bonferroni (|z|_crit 2.773) | **YES — significantly BELOW 50%** | same |
| `recent_closed` | n=187, WR 39.0%, sum **−29.0%**, median close age **128.1 d** | `MASTER_AUDIT.md:249,264` |
| `summary_picks.win_rate_pct` | **147.0%** — arithmetically impossible, denominator from a different population | `MASTER_AUDIT.md:202`; `forex_futures.md:347-356` |

**Interpretation:** the class is not "unproven"; on the only policy-clean sample it is
*statistically significantly negative*. Nothing in the current pipeline can be described as an edge.

### 1.4 Administrative state

FOREX is in `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}`
(`audit_trail/quality_gates.py:1724`), but `FOREX_HARD_DISABLE` computes **default OFF**
(`alpha_engine/config.py:345`), which is why 277 rows still flow. The UI copy claiming "BLOCKED"
(`audit_dashboard/template.html:909,13539`) is therefore a label, not an enforced control.

---

## 2. Where an edge could actually exist — and why retail spot FX costs it away

### 2.1 The four families that survive an academic read

| Family | Mechanism | Why it is plausibly real | Why it is small |
|---|---|---|---|
| **Carry / forward discount** | Covered interest parity: the forward is priced off the rate differential, so the high-yielder's forward sits at a discount. A long-high/short-low basket earns the differential minus crash risk. | One of the most replicated FX premia (forward-premium puzzle); mechanically tied to policy rates. | Crash risk (carry unwinds are violent and correlated), compressed G10 differentials, and the broker's swap spread takes a cut of the differential. |
| **Time-series momentum** | 1–12 month trend persistence in spot. | Documented across FX, futures, and this repo's own crypto/ETF TSMOM lineage (H1/H2/H18 — all NOT_PROVED, but the family is not disproved for FX). | Whipsaw in range regimes; monthly turnover × spread. |
| **Value (PPP / real exchange rate)** | Deviation of the real exchange rate from its long-run mean predicts slow reversal. | Long-horizon mean reversion is real in real terms. | 3–10 year horizon ⇒ cannot produce n≥30 in a 35-month OOS; unusable under the project's gates. |
| **Intervention / seasonality** | Central-bank intervention, month/quarter-end rebalancing flows, fiscal-date flows. | Documented but episodic. | Small n, event-defined, and the single most multiple-testing-prone family; not testable with a fixed pre-registered rule across 35 months. |

### 2.2 Why retail spot FX is structurally hostile

These are market-structure facts, **not measured in this repo** (`UNVERIFIED` here):

1. **You cannot trade the interbank market.** The repo prices FX from `open.er-api.com` and Yahoo
   `=X`, which are *mid reference rates*. Retail brokers quote OTC CFDs with a spread of roughly
   0.6–1.5 pips on EURUSD and 2–5 pips on crosses — 0.5–1.4 bps per side on EURUSD, materially more
   on the pairs where carry lives. A monthly carry basket pays this on every rebalance.
2. **The carry you are paid is not the carry in the forward.** Retail brokers apply an overnight
   swap *spread* around the interbank differential; in a low-differential regime the spread can
   consume most of the gross carry.
3. **No central clearing / counterparty risk.** Retail FX is an OTC claim on the broker, not a
   cleared futures position.
4. **The audit data itself is unexecutable.** `current_price == entry_price` on 93/118 OPEN rows
   (`forex_futures.md:23`) and mid-rate sourcing mean the recorded PnL has no spread, no swap, and
   often no price at all.

**Consequence:** any FOREX experiment must specify an *executable* vehicle (listed currency ETF or
exchange-traded FX future) and charge the real cost of that vehicle. A backtest on mid rates is not
evidence of a retail edge.

### 2.3 The one genuinely useful artifact already in the feed

The 44 mislabeled currency-ETF rows (§1.2.3) are, accidentally, the only retail-implementable FX
vehicles the system has ever emitted (UUP, FXE, FXY, FXB, FXA, FXC, CEW). A credible FOREX program
should *move* those rows to ETF (per `forex_futures.md` P0-3/P1-1) and then use those same tickers as
the execution layer for a carry test — not delete them.

---

## 3. Hypotheses, ranked by evidence × feasibility

Ranking rule: (strength of external evidence) × (can it be tested and executed with free/cheap data
inside the 2024-01-01→2026-11-13 OOS window) ÷ (cost drag).

> Cost figures quoted per hypothesis are market-structure estimates, not values measured in this
> repo (`UNVERIFIED`). They must be replaced by the executing broker's actual schedule before any
> proof run.

### H-FX-1 — G10 carry via listed currency ETFs / FX futures  *(rank 1)*

- **Signal:** 12-month policy-rate differential vs USD (covered-interest-parity forward discount),
  ranked cross-sectionally; long the top-3 high-yielders, short/flat the bottom-3, inverse-vol
  weighted.
- **Universe:** G10 vs USD — EUR, JPY, GBP, CHF, CAD, AUD, NZD (+ SEK/NOK as research-only).
  Execution: CME FX futures (`6E=F 6J=F 6B=F 6S=F 6C=F 6A=F 6N=F`) or the seven currency ETFs above.
- **Rebalance:** monthly (carry is slow; weekly turnover is cost-dominated).
- **Mechanism:** the forward discount is a risk premium for bearing crash risk. The strategy is
  short volatility in disguise; size for the crash, not the average.
- **Data required:** daily spot (ECB/Frankfurter), policy rates (BIS central-bank policy rates;
  FRED `DFF`, `ECBDFR`, etc.), futures/ETF prices (yfinance front-month with roll, or Nasdaq/Yahoo
  ETF closes). **Forward points must be constructed from policy rates (CIP), not assumed.**
- **Costs / capacity:** ETF: 5 bps/side + expense ratio (~0.40–0.94%/yr, ticker-specific). Futures:
  1 tick + quarterly roll (~2–3 bps/quarter) + commission. Capacity is large in FX futures; the
  binding constraint is crash correlation, not liquidity.
- **Failure mode:** carry crashes (2008, 2015, 2018, 2020, 2022) all arrive together; a G10 basket
  with compressed differentials earns less than the ETF expense ratio; retail swap spreads erase the
  rest.

### H-FX-2 — G10 12-month time-series momentum  *(rank 2)*

- **Signal:** sign of the 12-month (252-day) spot return per pair, long/short, inverse-vol weighted;
  optional 200-day filter.
- **Universe:** same 9 pairs; ETFs/futures execution.
- **Rebalance:** monthly.
- **Mechanism:** slow information diffusion and central-bank policy cycles create trend persistence.
- **Data required:** Frankfurter daily rates (free, no key) + futures/ETF prices for execution.
- **Costs / capacity:** 2 bps/side spot-equivalent base, 2× stress; monthly turnover ≈ 30–60%/yr.
- **Failure mode:** whipsaw at policy pivots (2022–2024 was exactly such a regime); the repo's own
  TSMOM tests (H1 BTC 0.60, H2 ETH 0.47, H18 ETF breadth 1.00) all failed their benchmarks, so the
  prior should be low.

### H-FX-3 — Carry + momentum composite  *(rank 3)*

- **Signal:** z-score(carry) + z-score(12m momentum), equal weight; long top-3 / short bottom-3.
- **Universe / rebalance:** as H-FX-1, monthly.
- **Mechanism:** carry and momentum are negatively correlated in crashes (momentum flips), so the
  composite historically improves Sharpe versus either leg.
- **Data / costs:** same as H-FX-1.
- **Failure mode:** the combination doubles the trial count (multiple testing) for a modest Sharpe
  improvement; if either leg is dead in 2024–2026 the composite is dead too.

### H-FX-4 — PPP / real-exchange-rate value  *(rank 4)*

- **Signal:** 5-year deviation of the real effective exchange rate (CPI-deflated) from its mean;
  long undervalued, short overvalued.
- **Universe:** G10.
- **Rebalance:** quarterly/annual.
- **Mechanism:** slow goods-market arbitrage.
- **Data required:** CPI (OECD/FRED), long spot history.
- **Costs / capacity:** very low turnover, so costs are not the issue.
- **Failure mode:** **fails the n≥30 gate by construction** — annual rebalancing over a 35-month OOS
  gives 3 observations. This hypothesis cannot be proved in the required window and should not be
  run as a proof attempt; it is a research note only.

### H-FX-5 — Month-end / quarter-end seasonality  *(rank 5)*

- **Signal:** long/short specific pairs in the last 2 and first 2 business days of the month/quarter.
- **Universe:** G10.
- **Rebalance:** event-driven.
- **Mechanism:** rebalancing and fiscal flows.
- **Data required:** daily spot.
- **Costs / capacity:** high relative to the tiny gross edge (a few bps).
- **Failure mode:** the effect is small, unstable, and is the classic multiple-testing trap — 9 pairs
  × 2 windows × 2 directions = 36 cells from ~24 events/yr. Do not run this as a proof attempt.

---

## 4. Pre-registered next experiment (one, exact)

**Experiment FX-EXP-1: "G10 carry via CIP forwards, executed in FX futures."**
Pre-registration must be committed *before* any OOS number is inspected.

### 4.1 Data (named, public, keyless where possible)

| Input | Source | Notes |
|---|---|---|
| Daily spot | ECB reference rates via **Frankfurter** `https://api.frankfurter.app/<start>..<end>?from=USD&to=EUR,JPY,...` | Matches `research/profitability/PROTOCOL.md:22` |
| Policy rates | **BIS central-bank policy rates** (`https://www.bis.org/statistics/cbpol.htm`) and FRED (`DFF`, `ECBDFR`, `INTDSRJPYM193N`, …) | Needed to build the forward discount |
| Execution prices | **CME FX futures** front-month daily settle (`6E=F 6J=F 6B=F 6S=F 6C=F 6A=F 6N=F`) via yfinance/CME settlements; ETF closes as fallback | If futures settle data cannot be obtained, the experiment is **BLOCKED** — do not substitute retail spot mids |
| Benchmark | USD 3-month T-bill (FRED `DTB3`) + long-only equal-weight basket of the same pairs | Per `PROTOCOL.md:65` (Sharpe ≥ benchmark + 0.30) |

Manifest: symbol, source, row count, first/last date, SHA-256, committed under `data/manifest.json`
(same convention as the existing program).

### 4.2 Design

- **Universe (fixed ex ante):** 9 G10 pairs vs USD (EUR, JPY, GBP, CHF, CAD, AUD, NZD, SEK, NOK);
  a pair enters only when both spot and policy-rate history exist; no backfill.
- **Split:** train **≤ 2023-12-31** (parameter selection only); OOS **2024-01-01 → 2026-11-13**
  (last complete bar). OOS starts 2024-01-01 even though the audit clock is Nov 2026 — the split is
  fixed by the surviving protocol, and a 2024 start keeps it comparable to v1–v4.
- **Parameters (max 2 free, per `PROTOCOL.md:90`):** carry lookback (12m) and portfolio vol target
  (8%). No per-pair tuning.
- **Signal:** at close of bar *t*, rank pairs by 12m policy differential; long top-3, short
  bottom-3; inverse-vol weights; portfolio vol target 8%.
- **Rebalance:** monthly (first business day after month-end).
- **Execution:** signal at *t* close, **position from *t+1* close** (one full day of lag). Stress:
  two-day lag.
- **Concurrent capital:** gross notional cap **3× capital** (conservative versus FX-futures margin);
  report **return on capital at the 3× cap**, not notional return. No leverage beyond 3×.
- **Costs:** 2 bps/side base (matches `PROTOCOL.md:50`), **2× stress = 4 bps/side**, plus futures
  roll ≈ 2–3 bps/quarter and commission. Carry is paid at the policy differential **minus a 50%
  haircut** as the base case (broker/roll slippage), with 0% and 100% haircut as sensitivity — the
  haircut is a stated assumption, not a measured number (`UNVERIFIED`).

### 4.3 Gates (all must pass; any failure ⇒ NOT PROVED)

| # | Gate | Threshold |
|---|---|---|
| 1 | OOS net Sharpe | **≥ 1.0** and **≥ benchmark + 0.30** |
| 2 | OOS net CAGR | > 0 and > benchmark total return |
| 3 | Round trips | **n ≥ 30** (monthly ⇒ ~35 max in the window) |
| 4 | True DSR | **≥ 0.95** with `N` = every trial in the version (grid cells + variants), declared in the report |
| 5 | CSCV PBO | **≤ 0.10** (`docs/BACKTEST_ADMISSIBILITY_STANDARD.md:44`; the looser `PROTOCOL.md:70` `< 0.50` is not sufficient), `T ≥ 1000` splits |
| 6 | SPA / Reality Check | **p < 0.05** against the no-skill null over the candidate set |
| 7 | Block bootstrap | 5th-percentile Sharpe **> 0** (2,000 resamples, block 20) |
| 8 | 2× cost | Sharpe **≥ 0.5** and still **> benchmark** |
| 9 | Execution lag | 1-day lag Sharpe **≥ 1.0**; 2-day lag reported, must remain positive |
| 10 | Carry-haircut sensitivity | Strategy must still beat cash at the **100% haircut** (i.e. the cross-sectional selection, not the raw differential, must add value) |
| 11 | Data purity | No date-only timestamps, no mid-vs-execution mixing, no duplicate trades; assert `resolved + expired + open = emissions` on the output |

### 4.4 Falsification conditions built into the design

- If OOS returns are fully explained by a **static long-high-yield basket** (i.e. the ranking adds
  nothing), the research question is answered negatively and the "carry" claim is withdrawn.
- If the only surviving variant requires a haircut of 0% and 1× costs, it is not a retail strategy.

---

## 5. Kill criteria

Kill the FOREX program (not just the candidate) if any of these hold:

1. **Any candidate's OOS Sharpe < 0.5 at 1× costs**, or its return is ≤ cash after the 50% carry
   haircut. FX carry that cannot beat T-bills after a realistic haircut is not a business.
2. **2× cost stress turns the Sharpe negative** — the edge is inside the spread.
3. **PBO > 0.10**, or SPA p ≥ 0.05, or DSR < 0.95 at the declared N.
4. **n < 30 OOS round trips** (which also kills any annual/quarterly design).
5. **The signal's sign flips** between 2024 and 2025–2026 halves — that is regime beta, not an edge.
6. **The strategy cannot be executed in a listed vehicle** (ETF or futures) with a documented price
   source. Mid-rate backtests do not qualify.
7. **The class fix (0/277 → enforceable policy) is not shipped first.** Any FOREX research performed
   on the current feed is research on contaminated rows (17.7% non-FX, 57% expired, 87% unpriced).

---

## 6. What NOT to do

1. **Do not run FX research on the existing picks.** The 277 rows are not a strategy sample: 0/277
   pass the advertised allowlist, 49/277 are not spot FX, and 93/118 OPEN rows have no mark. Any
   edge found there is a data artifact.
2. **Do not backfill date-only timestamps with `T00:00:00Z`.** It fabricates a midnight entry and
   corrupts hold-window math (`forex_futures.md:364`).
3. **Do not stamp `current_price = entry_price`** to make rows look priced — the exact mechanism
   behind the frozen-pick artifact (`01_audit/recommendations/per_asset_class/bond_mutual_funds.md:598`;
   `01_audit/sub/D_non_crypto.md:426-427`).
4. **Do not "fix" 147.0% WR by dividing by `wins+losses`.** Make wins/losses a strict subset of
   `resolved`; emit `None` / `DATA_INCONSISTENT` when the identity fails.
5. **Do not test carry on retail spot mids.** If forward points and an executable vehicle are not
   available, mark the experiment BLOCKED.
6. **Do not add pairs or windows after seeing OOS.** That is the exact failure mode documented in
   `03_research/profitability/runs/v2/VERDICT.md:34-54`.
7. **Do not use `cta_cross_asset_tsmom` as a "known good" baseline.** It is allowlisted in
   `non_crypto_policy.py:724` and blacklisted in `config.py:298`; the conflict is unresolved
   (`forex_futures.md:380`).
8. **Do not ship a "FOREX desk" product narrative.** The class is significantly *negative* on the
   only policy-clean sample (n=438, WR 35.62%, z −6.02).

---

## 7. UNVERIFIED register

| Item | Why |
|---|---|
| Any net-of-cost Sharpe for H-FX-1..5 | No experiment has been run; the 0.2–0.5 expectation is judgment, not measurement. |
| Retail broker spread/swap schedule for this project | Not in the repo; representative ranges are market-structure knowledge. |
| Exact forward points used by any broker | CIP construction is an assumption; the basis is not observed. |
| Whether yfinance FX futures front-month history has usable rolls | Not tested from this environment. |
| Live value of `FOREX_HARD_DISABLE` | Repo default computes `False`; the deployed env var is unobservable from a read-only worktree (`forex_futures.md:379`). |
| Realized slippage/fill quality | No live fills exist in the repo (`forex_futures.md:382`). |
| Age count "158 rows >30 d" | Not reproducible as an age count; 158 is the EXPIRED count. Among 233 parseable rows, **114 are >30 d**; 44 have no parseable timestamp (`forex_futures.md:378`). |
