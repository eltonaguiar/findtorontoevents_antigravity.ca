# BOND — Profitability Playbook

**PRIORITY: HIGH**
**EXPECTED EDGE: modest but economically grounded risk premia — curve carry/roll-down and credit-spread mean reversion — expected net-of-cost Sharpe 0.3–0.6 on Treasury futures or bond ETFs after costs. Duration/term-premium timing is the only route to a Sharpe above 1.0 and it is unproven. The class currently has n=1 policy-clean, so every clean experiment is pure upside; the expectation range is a judgment, not a measurement, and is marked UNVERIFIED.**

- Class owner: PC3 (per-asset-class profitability planner)
- Status clock: 2026-11-14T21:15Z
- Evidence root: paths below are relative to `final_v2/finpredict-v2/`
- Rule: every count is copied from the named evidence file. Market-structure knowledge and absent data are labelled `UNVERIFIED`.

---

## 1. Current evidence — what the repo actually contains

### 1.1 Population (verified)

| Metric | Value | Source |
|---|---:|---|
| `picks.active` (curated) | **0** | `01_audit/MASTER_AUDIT.md:104`; `01_audit/recommendations/per_asset_class/bond_mutual_funds.md:16` |
| `picks.active_raw` | **15 rows / 5 instruments / 3 source_systems** | `bond_mutual_funds.md:17`; `01_audit/sub/D_non_crypto.md:25` |
| Unpriced seeds | **9 / 15** `current_price=None`, `pnl=0` | `bond_mutual_funds.md:18` |
| Seed age | 23.9–24.8 h; newest `2026-11-13T14:34:18Z` (~25.5 h) | `bond_mutual_funds.md:19` |
| Duplicate emission | **6 `symbol+strategy+direction` groups / 9 extra rows**; TLT SHORT emitted **3×** with different entries (79.72, 79.72, 79.20) | `D_non_crypto.md:265`; `bond_mutual_funds.md:312` |
| Emitters | `alpha_engine` (general scanner), `bond_scanner`, `orphan_emitter_bond` | `bond_mutual_funds.md:315-322` |
| Newest closed | `2026-11-10T13:52:26Z` = **98.2 h / 4.09 d** | `bond_mutual_funds.md:20`; `MASTER_AUDIT.md:350` |

### 1.2 The three headline facts in the brief

1. **0 curated active.** `picks.active` is empty; the quality strip nevertheless renders a **green
   PASS** because `threshold_pass = (active_count == 0 or …)` short-circuits the gate
   (`audit_trail/dashboard_generator.py:6824-6826`; `bond_mutual_funds.md:66-84`). The authoritative
   surfaces (`money_ready_verdict.json`, `audit_surface_truth.json`) say `INSUFFICIENT_DATA`,
   `n_resolved=1`, `policy_frozen=true`.

2. **15 raw seeds for 5 instruments.** Three independent writers emit the same economic signal:
   `alpha_engine/scanner.py:293` imports `BOND_STRATEGIES`, `bond_scanner` writes
   `active_picks_bond.json` and merges into `active_picks.json`, and `bond-agent.yml:217` writes
   `bond_picks.json`. The dashboard dedupes on `(source_system, symbol, direction, strategy)` —
   *including* `source_system` — so cross-emitter duplicates survive
   (`audit_trail/dashboard_generator.py:9831-9836`; `active_raw` is snapshotted at `:9538`, before
   the dedupe at `:9876`).

3. **n=1 policy-clean.** `pf_registry.by_asset_class_policy_clean_net[BOND]` = **n=1, 0W/1L, WR 0%,
   PF 0**, PnL −0.01159 (`MASTER_AUDIT.md:126`; `bond_mutual_funds.md:21`).

### 1.3 Realized sample — two WR definitions, do not fuse them

The same `recent_closed` cohort of **n=35** is reported two ways in the archive:

| Definition | WR | PF | Sum PnL | Source |
|---|---:|---:|---:|---|
| `status = WON` (12/35) | **34.3%** | 0.586 | — | `D_non_crypto.md:270`; `bond_mutual_funds.md:20` |
| `pnl_pct > 0` | **37.1%** | — | **−7.7%** | `MASTER_AUDIT.md:253` |

`04_peer_reviews/equity_etf_bond_mf_review.md:103,158` flags this explicitly: pick one definition and
label it. **This playbook uses `status = WON` = 34.3% as the headline, with 37.1% as the
`pnl_pct>0` cross-check.**

### 1.4 Other conflicting surfaces (all real, all named)

| Surface | n | WR | Note |
|---|---:|---:|---|
| `recent_closed` (status=WON) | 35 | 34.3% | PF 0.586 |
| `recent_closed` (pnl>0) | 35 | 37.1% | Σ −7.7% |
| policy-clean | **1** | 0% | PF 0 |
| tournament cohort | 503 | 58.1% | +1.066% — a different population |
| `summary_picks` | 72 resolved | **127.8%** | arithmetically impossible |
| `bond_*` strategies | `bond_duration_rotation` n=1; `bond_yield_momentum` n=1 raw / 0 policy-clean | — | `bond_mutual_funds.md:22` |

The tournament 58.1% does **not** rescue the class: it is a different cohort with no policy-clean
provenance, and the `summary_picks` 127.8% proves the denominators are broken
(`wins+losses > resolved`; `MASTER_AUDIT.md:202`).

### 1.5 Administrative and data state

- BOND is in `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}`
  (`audit_trail/quality_gates.py:1724`); the rationale at `:1727-1730` cites live PF 0.37 / n=8.
  A documented bypass exists in the comment: paper-only 60 days on HYG/LQD credit-spread strategies
  plus `bond_credit_mom` lab validation (lab PF 1.41, **not live**).
- **Price coverage is the binding defect.** `audit_trail/data/stock_prices.json` has only **HYG** of
  the 14 bond ETFs; `fetch_stock_prices.py:68-77` skips the payload because `picks` is a dict and the
  class allow-list omits `bond`; the FMP fallback calls `apikey=demo` instead of `FMP_API_KEY`
  (`dashboard_generator.py:1599`); `_EQUITY_ETF_TICKERS` knows only TLT and HYG, so 12 of the 14
  `BOND_SYMBOLS` are never quoted or closed (`universal_pick_resolver.py:433-443`).
  The canonical 14 are **TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB**
  (`equity_etf_bond_mf_review.md:154`; the older list naming TLH/GOVT/BNDX is drifted).
- **FRED is reachable but switched off on the main emitter.** `.github/workflows/etf-bond-scanner.yml:159`
  hard-codes `SKIP_FRED: '1'`; `bond-agent.yml:126-148` fetches only 1 of the 10 `FRED_SERIES`
  (`T10Y2Y`). FRED returns `DGS10 = 5.10` on 2026-11-12 (`D_non_crypto.md:280`), but **picks carry no
  yield field**, so yield-level reconciliation is `UNVERIFIED`. This is the single most important
  missing input for every hypothesis below.

---

## 2. Where an edge could actually exist — and why a bond ETF pick is not a bond strategy

### 2.1 The five families worth testing

| Family | Mechanism | Why it is plausibly real | Why it is small / hard |
|---|---|---|---|
| **Carry / roll-down (yield curve)** | A bond's expected return ≈ yield + roll-down as it ages down a positively sloped curve − financing. Steep segments pay more. | Term premium is a compensated risk; roll-down is mechanical, not a forecast. | The 2022–2024 inversion makes front-end carry negative; curve trades are low-vol, so costs are a large share. |
| **Duration / term-premium timing** | Expected excess return rises when the term premium is high and falling. | Term-premium variation predicts bond excess returns in the literature. | Term-premium estimates (ACM) are revised and slow; the Fed-policy regime drives most of it. |
| **Credit spread** | HY/IG OAS mean-reverts around a slow-moving default cycle. | Credit risk premium is one of the most robust fixed-income premia. | Spreads trend in crises — a z-score rule buys into a widening market. Liquidity gaps in HYG/JNK. |
| **TIPS breakeven** | Breakeven inflation vs a model of expected inflation; long TIP when real yield is high / breakeven cheap. | Inflation risk premium is real. | Requires an inflation model; breakeven is noisy and TIP carries duration. |
| **Convexity** | Long-duration bonds have positive convexity; a barbell has more than a bullet of equal duration. | Mathematical, not a forecast. | The convexity gain is a few bps/yr and cannot be isolated with bond ETFs (no maturity, roughly constant duration). |

### 2.2 Why "a BOND pick" in this system is not a bond strategy

This is the decisive conceptual defect and it is structural, not a data bug:

1. **A bond's return has three parts — coupon accrual, roll-down, and price change from yield.**
   The pick schema stores only `entry_price` and `current_price`. It therefore measures **price
   change only**, discarding the coupon (the largest component for most bonds) and the roll-down.
   A "winning" bond pick can be a losing bond position and vice versa.
2. **A bond ETF has no maturity.** It maintains a roughly constant duration by rebalancing its
   holdings, so the holder never earns the pull-to-par/roll-down that a real bond position earns as
   it ages. A bond ETF is a *duration exposure*, not a bond.
3. **The instrument's return driver is yield, and the schema has no yield.** The audit's own BOND
   rows carry no yield field (`D_non_crypto.md:280`), which is why yield-level reconciliation is
   `UNVERIFIED`. Pricing a bond ETF from an equity-style quote is exactly the class error.
4. **The audit's BOND rows are 5 ETFs, 3 emitters, 9/15 unpriced, 3× duplicated.** That is an
   equity-style pick pipeline pointed at a yield instrument; it cannot express carry, roll-down,
   duration, or credit.
5. **`bond_duration_rotation` n=1 and `bond_yield_momentum` n=1 raw / 0 policy-clean.** The two
   strategies that *do* express the right economics have essentially no sample.

**Consequence:** any BOND hypothesis must be specified in **yield/duration space** (carry, roll-down,
DV01, OAS, breakeven) and then mapped to an executable instrument (Treasury futures or a
duration-matched ETF). Price-momentum on a bond ETF is not a bond strategy and should not be tested
as one.

---

## 3. Hypotheses, ranked by evidence × feasibility

> Cost figures quoted per hypothesis are market-structure estimates, not values measured in this
> repo (`UNVERIFIED`). They must be replaced by the executing venue's actual schedule before any
> proof run.

### H-BD-1 — UST curve carry + roll-down, DV01-neutral  *(rank 1)*

- **Signal:** for each point on the curve (2y, 5y, 10y, 30y), compute expected 12-month return =
  `carry (yield − financing) + roll-down ((y_n − y_{n−1yr}) × duration) + convexity adjustment`.
  Rank the four segments; long the top segment, short the bottom, **DV01-matched** so the trade is
  curve-relative, not a level bet.
- **Universe:** Treasury futures `ZT=F` (2y), `ZF=F` (5y), `ZN=F` (10y), `ZB=F` (30y); ETF proxies
  SHY/IEF/TLT only as a fallback.
- **Rebalance:** monthly.
- **Mechanism:** roll-down is mechanical; a positively sloped curve pays the holder for ageing.
  DV01-neutrality removes the duration bet, isolating the carry/roll premium.
- **Data required:** Treasury.gov daily par yield curve (CSV/XML), FRED `DGS2,DGS5,DGS10,DGS30`
  (backfill + audit), futures settle prices for execution and costs.
- **Costs / capacity:** 1 tick per leg + quarterly roll ≈ 1–3 bps/side DV01-equivalent; base **2
  bps/side**, 2× stress. Capacity is large (Treasury futures are the deepest rates market).
- **Failure mode:** in an inverted curve the front-end carry is negative and the trade is short the
  only segment that pays; a DV01-neutral short 30y leg has a large tail if the curve bear-steepens;
  low volatility makes the cost share high.

### H-BD-2 — Credit-spread mean reversion (HY OAS)  *(rank 2)*

- **Signal:** z-score of the ICE BofA US High-Yield OAS (`BAMLH0A0HYM2`) versus its 2-year mean.
  Long HYG/JNK when z > +1.5 (spreads wide = cheap), flat/short when z < −0.5 (tight = expensive).
- **Universe:** HYG, JNK (ETFs); optionally LQD for the IG leg (`BAMLC0A0CM`).
- **Rebalance:** weekly or monthly; hysteresis to avoid churn.
- **Mechanism:** credit risk premium mean-reverts with the default cycle; spread level is a
  compensated-risk signal.
- **Data required:** FRED `BAMLH0A0HYM2`, `BAMLC0A0CM` (free, daily), ETF prices.
- **Costs / capacity:** ETF 5 bps/side + expense ratio; HYG/JNK spreads widen exactly when the
  signal fires (the strategy trades when liquidity is worst). Capacity limited in stress.
- **Failure mode:** spreads trend through a recession (2008, 2020) — a z-score rule catches a falling
  knife; ETFs can trade at a discount to NAV in stress; the "cheap" level can stay cheap for years.

### H-BD-3 — Duration / term-premium timing  *(rank 3)*

- **Signal:** long duration (IEF/TLT) when the ACM 10y term premium (`ACMTP10`) is in its top tercile
  and falling, or when 10y yield 3-month momentum is negative; otherwise cash/short duration.
- **Universe:** IEF, TLT, or `ZN=F`/`ZB=F`.
- **Rebalance:** monthly.
- **Mechanism:** expected bond excess return is increasing in the term premium; falling yields add
  capital gains.
- **Data required:** FRED `ACMTP10`, `DGS10`, `DTB3`.
- **Costs / capacity:** 5 bps/side ETF; large capacity.
- **Failure mode:** the term premium is an estimate with revisions; 2022 showed that "high term
  premium" can coexist with a −30% duration drawdown; the rule is essentially a Fed-regime bet.

### H-BD-4 — TIPS breakeven value  *(rank 4)*

- **Signal:** 10y breakeven (`T10YIE`) versus a model of expected inflation (e.g. 5y5y forward or a
  survey); long TIP when breakeven is below the model by > 50 bps.
- **Universe:** TIP, STIP.
- **Rebalance:** monthly.
- **Mechanism:** inflation risk premium + real-yield mean reversion.
- **Data required:** FRED `T10YIE`, `DFII10`, `T5YIFR`; a model of expected inflation (the model is
  the research risk).
- **Costs / capacity:** 5 bps/side + ER; capacity moderate.
- **Failure mode:** the "cheap breakeven" is usually a liquidity/seasonality artifact (TIPS
  seasonality is well documented); TIP carries real duration, so the trade is contaminated by the
  duration bet in H-BD-3.

### H-BD-5 — Convexity / barbell  *(rank 5)*

- **Signal:** 2s30s curve convexity; long a 2y+30y barbell, short a duration-matched 10y bullet.
- **Universe:** `ZT=F` + `ZB=F` vs `ZN=F`.
- **Rebalance:** monthly/quarterly.
- **Mechanism:** a barbell has more convexity than a bullet of equal duration.
- **Data required:** yields + futures.
- **Costs / capacity:** 3 legs, so 3× the transaction cost for a few bps of convexity.
- **Failure mode:** the convexity gain is smaller than the cost of three legs; with ETFs it is not
  expressible at all (no maturity). **Feasibility is low; do not run this before H-BD-1.**

---

## 4. Pre-registered next experiment (one, exact)

**Experiment BD-EXP-1: "UST curve carry + roll-down, DV01-neutral, Treasury futures."**
Pre-registration committed before any OOS number is inspected.

### 4.1 Data (named, public)

| Input | Source | Notes |
|---|---|---|
| Par yield curve | **U.S. Treasury daily par yield curve** (`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/`) | 1/2/3/5/7/10/20/30y, daily |
| Yield backfill / audit | **FRED** `DGS2, DGS5, DGS10, DGS30, T10Y2Y, T10Y3M, DTB3` | Free, daily, revision-aware |
| Term premium (control, not signal) | **FRED `ACMTP10`** | Used only to describe the regime, not to select the strategy |
| Execution prices | **CME Treasury futures** settlement `ZT=F, ZF=F, ZN=F, ZB=F` (yfinance/CME) | If settle data is unavailable, the experiment is **BLOCKED**; do not substitute ETF NAV |
| Benchmark | 10y Treasury total return (IEF or a constant-maturity index) + 3m T-bill | Report excess-of-cash and benchmark-relative |

Manifest with SHA-256 per series, committed.

### 4.2 Design

- **Universe (fixed ex ante):** 4 UST points — 2y, 5y, 10y, 30y.
- **Split:** train **≤ 2023-12-31** (only the two parameters are chosen); OOS **2024-01-01 →
  2026-11-13**. The OOS window contains the 2022–2023 inversion aftermath, which is a deliberately
  hostile test for a roll-down strategy — that is the point.
- **Parameters (max 2):** roll-down horizon (12 months) and rebalance frequency (monthly). No
  per-segment tuning.
- **Signal:** expected 12m return per segment; long top-1, short bottom-1, **DV01-neutral**.
- **Execution:** signal at *t* close, position from *t+1* close. Stress: 2-day lag.
- **Concurrent capital:** DV01-neutral; gross notional cap **5× capital**; report **return on
  capital at that cap**, not notional. No leverage beyond 5×.
- **Costs:** **2 bps/side base**, **2× stress = 4 bps/side**, plus one tick per leg and quarterly
  roll. Carry/financing is embedded in the futures price and must not be double-counted.

### 4.3 Gates (all must pass; any failure ⇒ NOT PROVED)

| # | Gate | Threshold |
|---|---|---|
| 1 | OOS net Sharpe (excess of cash) | **≥ 1.0** and **≥ benchmark + 0.30** |
| 2 | OOS net CAGR | > 0 and > benchmark total return |
| 3 | Round trips | **n ≥ 30** (monthly ⇒ ~35 max) |
| 4 | True DSR | **≥ 0.95**, `N` = every trial in the version (grid cells + variants), declared |
| 5 | CSCV PBO | **≤ 0.10** (`docs/BACKTEST_ADMISSIBILITY_STANDARD.md:44`), `T ≥ 1000` splits |
| 6 | SPA / Reality Check | **p < 0.05** |
| 7 | Block bootstrap | 5th-percentile Sharpe **> 0** |
| 8 | 2× cost | Sharpe **≥ 0.5** and still > benchmark |
| 9 | Execution lag | 1-day lag Sharpe **≥ 1.0**; 2-day lag reported and positive |
| 10 | Regime robustness | Must be positive in **both** sub-periods 2024 and 2025–2026, and in both curve-slope states |
| 11 | Data purity | Yields point-in-time; no revised-vintage splice; `resolved + expired + open = emissions` |

### 4.4 Explicit design safeguard

The experiment must report the **carry-only** and **roll-down-only** decomposition. If the signal is
profitable only because it is long duration during a rally, the curve claim is withdrawn (that is
H-BD-3, not carry).

---

## 5. Kill criteria

Kill the BOND research program (not just the candidate) if:

1. **OOS Sharpe < 0.5 at 1× costs** for both H-BD-1 and H-BD-2 — the class has no economically
   meaningful premium after realistic costs.
2. **2× cost stress turns the Sharpe negative**, or the trade is profitable only before the roll
   cost.
3. **The signal's return is fully explained by duration** (correlation with IEF > 0.9) — then it is a
   level bet, not a curve/credit strategy.
4. **PBO > 0.10**, SPA p ≥ 0.05, or DSR < 0.95 at the declared N.
5. **n < 30 OOS rebalances** (kills annual/quarterly designs).
6. **The experiment cannot obtain yield + futures-settle data** — a price-only bond ETF test is not a
   bond test.
7. **The class remains `BLOCKED` and no clean paper accrual exists after 90 days** — the freeze is
   correct and should stay.

---

## 6. What NOT to do

1. **Do not unfreeze BOND to make the panel look populated.** Policy-clean n=1 cannot be promoted;
   complete the documented bypass first (`bond_mutual_funds.md:597`).
2. **Do not stamp `current_price = entry_price`** — the exact mechanism behind the frozen-pick
   artifact (`bond_mutual_funds.md:598`). v1's "stamp entry as current" recommendation is rejected
   by the peer review (`equity_etf_bond_mf_review.md:80`).
3. **Do not write a FRED yield (DGS10/T10Y2Y) into `current_price`.** Yield is not price; that
   fabricates a mark. FRED is for signals/enrichment only (`bond_mutual_funds.md:599`).
4. **Do not call a bond-ETF price move a "bond strategy."** It has no coupon, no roll-down, and no
   maturity (§2.2).
5. **Do not treat the tournament 58.1% / n=503 cohort as evidence** while policy-clean is n=1; it is
   a different population with no policy provenance.
6. **Do not cite `summary_picks` BOND WR 127.8%.** It is arithmetically impossible
   (`bond_mutual_funds.md:191-198`).
7. **Do not dedupe by `pick_id`** — IDs are source-prefixed and never match across emitters; use
   `(asset_class, symbol, direction, strategy)` (`bond_mutual_funds.md:601`).
8. **Do not add BOND to any "money-ready" narrative** while `money_ready_verdict` says
   `INSUFFICIENT_DATA` and `policy_frozen=true`.

---

## 7. UNVERIFIED register

| Item | Why |
|---|---|
| Any net-of-cost Sharpe for H-BD-1..5 | No experiment has been run; 0.3–0.6 is a judgment, not a measurement. |
| Post-fix BOND `win_rate_pct` | The SQL fix changes the cohort; only the old 127.8% is proven invalid. |
| Yield-level reconciliation | Picks carry no yield field; only ETF prices can be reconciled (`D_non_crypto.md:280`). |
| Whether yfinance is blocked from GitHub Actions runner IPs | Asserted in `bond_scanner.py:218-220`; not re-tested here. |
| Emitter attribution for the 13:39Z `alpha_engine_*` BOND rows | Inferred from ID prefix; no run log inspected (`bond_mutual_funds.md:616`). |
| `live_picks.db` PnL sign/magnitude defects | The ML peer's 8 sign inversions / 15 mismatches were read from its report, not re-queried. |
| Current live `asset_class_summary` | All quotes are from the archived 14:30Z payload. |
| Whether any consumer reads `summary_picks.json` beyond diagnostics | `MASTER_AUDIT.md:402` also marks this UNVERIFIED. |
