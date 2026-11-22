# Block 4 · N1 — Low-turnover tests (pre-registered)

**Round:** N1 · **Date:** 2026-11-22 · **Seed:** 42 · **Commits:** none
**Script:** [`tools/low_turnover_test.py`](../../tools/low_turnover_test.py) → **JSON:** [`reports/low_turnover_20261122.json`](../../reports/low_turnover_20261122.json)

**Verdict up front: R1 KILL · R2 KILL · R3 KILL.** No low-turnover rule tested beats buy-and-hold SPY.
The programme-level conclusion is at the bottom.

---

## Why this test exists (the reasoning that set it)

Every mechanism tested so far in this programme died the same way:

| Prior test | Result |
|---|---|
| FX momentum (63d/21d) | net −36.88 bp, 0th percentile of null |
| FX mean-reversion (5d/5d) | gross +4.30 bp, net −5.70 bp — real effect, half eaten by cost |
| Equity breakout (20d/55d) | +1.12 %/trade but selection α −0.285 %; random entries earned +0.715 %/trade in the same window |
| GitHubCopilot's simulator | 6,610 trades, gross +$1,158, fees $6,744 → net −$5,586 |

The common failure is **turnover**, not signal quality. The only thing that survived scrutiny in the
whole programme was buy-and-hold SPY. So N1 tested the one regime whose cost profile can survive:
≤4 rebalances per year.

---

## Data actually used

`data/cache/asset_class_review/*_5y.csv` — read from disk, never re-fetched.

- **79 symbols loaded, 79 usable, 0 dropped.** Every symbol has a price on every SPY trading day
  over the window, so none had to be excluded.
- Raw date range: **2021-11-20 → 2026-11-20** (crypto rows are 7-day, ETF/futures rows 5-day).
  Reindexed onto the SPY calendar and forward-filled: **1,254 SPY trading days, 2021-11-22 → 2026-11-19.**
- **Evaluation window: 2022-11-25 → 2026-11-19** (~4.0 years, 1,000 trading days). It starts after
  the slowest warm-up (252-day momentum), and SPY and all three rules are measured on exactly the
  same window so the comparison is like-for-like.
- Asset-class composition: 20 US single stocks, 15 crypto, 12 commodities/futures, 10 bonds,
  10 FX, 8 US equity-index ETFs, 4 US sector ETFs.

### Survivorship caveat (from the actual first dates)

Every symbol's first bar is **2021-11-20 or 2021-11-22** (`first_date_min` 2021-11-20,
`first_date_max` 2021-11-22, median 1,254 bars). No symbol begins mid-window. But these 79 are
*today's* listed instruments: a symbol that was delisted, or that did not exist in 2021, simply
is not in the cache. The universe therefore looks healthier than it was. **The R1 result below is
an upper bound, not a fair estimate.**

---

## Pre-registered rules (fixed before any result was seen; all reported)

| Rule | Definition | Rebalance | Max/yr |
|---|---|---|---|
| **R1** | Rank the 79-symbol universe by trailing 252-day return; hold the top 5 equal-weight | Annual, first trading day of the year | 1 |
| **R2** | Rank the sector ETFs in the cache (XLK, XLF, XLV, XLE) by trailing 126-day return; hold the top 2 equal-weight | Quarterly | 4 |
| **R3** | Long SPY when close > 200-day SMA, else cash (Faber) — the minimum-turnover control | Daily signal check, trade only on a cross | ~2–5 |

Implementation: decisions are taken on the close of day *t* and executed on the close of day
*t+1* (next-bar execution, no same-day look-ahead). Costs are charged on traded notional at
execution: `cost = bps/1e4 × Σ|w_new − w_old|`. **Base cost 5 bp per side** (US ETF, defensible),
**stress 15 bp per side (3×)**.

### Two validation checks that the engine is not lying

- An "always hold SPY" rule reproduces buy-and-hold exactly: CAGR 17.0715 % vs 17.0715 %,
  **max absolute daily difference 0.0**.
- Shifting R1's decisions one day **later** gives CAGR 16.26 % and one day **earlier** 14.77 %
  (vs 18.05 % at the registered timing). There is no one-day look-ahead inflating the result.

---

## Benchmark

| | CAGR | Vol | Max DD | Sharpe |
|---|---|---|---|---|
| SPY buy & hold, **full window** (for reference, reproduces the programme baseline) | 10.38 % | 17.39 % | −24.50 % | 0.657 |
| SPY buy & hold, **evaluation window** (the benchmark all rules are judged against) | **17.07 %** | 15.24 % | −18.76 % | **1.114** |

The evaluation-window SPY is strong (17.07 %/yr) because it excludes the 2022 bear market that
the 252-day warm-up consumes. That is the honest bar: a rule has to beat SPY over the same period.

---

## Per-rule results

### R1 — 12-month momentum, annual, top 5

| CAGR | Vol | Max DD | Sharpe | Excess vs SPY | 95 % CI on excess CAGR | Cost drag | Trades (total / per yr) |
|---|---|---|---|---|---|---|---|
| 18.05 % | 46.92 % | −46.38 % | 0.590 | **+0.97 pp** | **[−36.48, +72.05] pp** | 0.098 pp/yr | 33 / 8.3 |

- 3× cost: CAGR 17.85 %, drag 0.294 pp.
- **Per-year excess:** 2022 +4.53, 2023 −32.05, 2024 **+66.79**, 2025 −32.61, 2026 +20.33. It is
  **one year**: 2024 carries the whole result, and two other years are −33 pp.
- **Concentration:** NVDA contributes 32.7 %, SOL-USD 22.3 %, AMD 21.1 %, NEAR-USD 21.1 % of gross.
  A handful of names carry it.
- Bootstrap p(excess ≤ 0) = 0.48. Random control: **61.2nd percentile** (null median −1.86 pp,
  p95 +17.22 pp).

### R2 — Sector momentum, quarterly, top 2

| CAGR | Vol | Max DD | Sharpe | Excess vs SPY | 95 % CI on excess CAGR | Cost drag | Trades (total / per yr) |
|---|---|---|---|---|---|---|---|
| 5.76 % | 17.16 % | −23.07 % | 0.413 | **−11.32 pp** | **[−22.53, −0.93] pp** | 0.199 pp/yr | 30 / 7.5 |

- 3× cost: CAGR 5.36 %, drag 0.597 pp.
- Per-year excess negative in 4 of 5 years (2022 +2.52, then −24.21, −10.19, −12.63, −2.03).
- The CI upper bound is **below zero**: this rule is reliably *worse* than SPY.
- Random control: 35.4th percentile.

### R3 — SPY 200-day trend filter (minimum-turnover control)

| CAGR | Vol | Max DD | Sharpe | Excess vs SPY | 95 % CI on excess CAGR | Cost drag | Trades (total / per yr) |
|---|---|---|---|---|---|---|---|
| 10.24 % | 12.24 % | −11.98 % | 0.861 | **−6.83 pp** | **[−15.65, +0.06] pp** | 0.263 pp/yr | 19 / 4.8 |

- 3× cost: CAGR 9.72 %, drag 0.788 pp.
- It **does** cut risk (max DD −11.98 % vs −18.76 %; Sharpe 0.861 vs 1.114 is still lower).
- Per-year excess: −1.35, −13.56, 0.00, −8.38, −3.92. SPY was above its 200-day MA 94 % of
  2023, 100 % of 2024, 83 % of 2025, 94 % of 2026, so the filter was mostly invested and paid the
  whipsaw cost of 20 crosses while giving up the strongest up-legs.
- Random control: 53.4th percentile.

---

## Gates (G1–G5) per rule

G1 excess CAGR > 0 · G2 CI lower bound > 0 · G3 lower max DD **or** higher Sharpe than SPY ·
G4 cost drag < 1 pp/yr · G5 ≥95th percentile of the random-selection control.

| Rule | G1 | G2 | G3 | G4 | G5 | Verdict |
|---|---|---|---|---|---|---|
| R1 | ✅ | ❌ | ❌ | ✅ | ❌ (61.2) | **KILL** |
| R2 | ❌ | ❌ | ❌ | ✅ | ❌ (35.4) | **KILL** |
| R3 | ❌ | ❌ | ✅ (drawdown) | ✅ | ❌ (53.4) | **KILL** |

Mapping: all pass → CANDIDATE; G1+G2 pass but G3 or G5 fails → WEAK; G1 or G2 fails → KILL.
Never PROVEN.

- **R1** passes G1 only on the point estimate (+0.97 pp), but the CI straddles zero and it loses to
  random selection more than a third of the time. Its 46.9 % vol and −46.4 % drawdown are worse
  than SPY on every risk measure.
- **R2** and **R3** fail G1 outright.
- **G4 passes for all three** (0.098 / 0.199 / 0.263 pp/yr). The hypothesis that low turnover keeps
  cost drag small is **confirmed** (all < 1 pp, and even at 3× cost none reaches 1 pp). But cheap
  execution does not create an edge: the gross returns are simply not high enough.

## Random-selection control

N random symbols held annually (N = the rule's holdings, 500 shuffles, seed 42), excess CAGR over
SPY:

| Rule | Rule's excess | Null median | Null p95 | Rule's percentile |
|---|---|---|---|---|
| R1 (N=5) | +0.97 pp | −1.86 pp | +17.22 pp | 61.2 |
| R2 (N=2) | −11.32 pp | −4.86 pp | +28.74 pp | 35.4 |
| R3 (N=1) | −6.83 pp | −8.65 pp | +30.10 pp | 53.4 |

All three sit in the middle of the random distribution. None is distinguishable from picking at random.

---

## Programme-level conclusion

**No rule tested in this programme beats holding the index, so the honest recommendation is to
hold the index.** Low turnover does exactly what the hypothesis asked (cost drag ≤ 0.26 pp/yr at
1× cost), and it still does not produce outperformance: the one positive point estimate (R1)
rests on a single lucky year (2024) and a few concentrated winners, sits inside a CI spanning
−36 pp to +72 pp, and lands at the 61st percentile of random selection. This is not a failure of
the round; it is the round's answer.

---

## Method note (appended 2026-11-22) — point-in-time re-run

A survivorship / point-in-time re-run of these N1 rules exists. The universe was
rebuilt per rebalance date with the first-observation approximation in
`tools/pit_universe.py` (`build_pit_universe`), and the rules were re-executed
unchanged. Results are identical to the numbers above (the PIT universe equals
the original at every date, so the survivorship contribution is 0.0 and the N1
conclusion survives). Full write-up:
`docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md`; machine-readable
results: `reports/survivorship_audit_20261122.json`. The original numbers above
were not changed.
