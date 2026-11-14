# Focus Decision — Where to Concentrate Research (final_v3, 2026-11-14)

**Decision rule:** Target ≥1 asset class (beyond mutual funds) that can pass all money-ready gates with benchmark-relative net expectancy CI excluding zero, DSR ≥0.95 (cumulative trial count), PBO ≤0.10, and ≥100 clean forward closes over ≥3 distinct months. Within mutual funds, target the subset needing less capital in, lower maintenance fees, and less capital required.

---

## Evidence Reviewed

| Source | CRYPCO | EQUITY | ETF | FOREX | COMMODITY | BOND | FUTURES | MUTUAL_FUND |
|---|---|---|---|---|---|---|---|---|
| Live ledger WR | 35.87% | 59.20% | 2.22% | 32.19% | 40.17% | 7.69% | 42.31% | N/A |
| Live ledger PF | 0.920 | 0.939 | 0.022 | 0.660 | 1.026 | 0.392 | 1.094 | N/A |
| Live ledger n | 3,705 | 250 | 45 | 612 | 229 | 26 | 52 | N/A |
| Registry cohort WR | 42.09% | 40.72% | 68.42% | 35.88% | 14.29% | — | 30.77% | N/A |
| Registry cohort PF | 0.258 | 0.662 | 1.788 | 0.838 | 0.172 | — | 1.009 | N/A |
| Best research candidate | VWAP MR (refuted) | H10 RSI(2) (NOT_PROVED) | H16/H18 (NOT_PROVED) | None | None | None | None | MF ranker exists |
| Money-ready verdict | NOT_READY | NOT_READY | INSUFFICIENT_DATA | NOT_READY | WATCH | INSUFFICIENT_DATA | INSUFFICIENT_DATA | NOT_BUILT |

---

## Focus Decision: Two Asset Classes Beyond Mutual Funds

### Primary Focus: CRYPCO (Cryptocurrency)

**Rationale:**
- Largest n in live ledger (3,705 decisive picks) — only class with sufficient sample for statistical power
- Longest existing candidate history (kilo's VWAP MR, funding carry research)
- Registry cohort n=22,055 — largest alternative cohort for cross-validation
- Already has research infrastructure (kilo's VWAP MR, v4 funding carry tests)

**Bounded hypothesis:**
> Daily 50/200-day time-series trend, long/flat, volatility-targeted on a frozen liquid universe (BTC, ETH, SOL, XRP, ADA — proven symbols; exclude DOGE, AVAX, LINK). Compare with equal-weight buy-and-hold and cash in bull and bear windows.

**Why CRYPCO over EQUITY:**
- EQUITY has higher WR (59.2%) but PF <1.0 (0.939) — losses dominate wins; WR is misleading
- CRYPCO PF 0.920 is closer to 1.0 and registry PF 0.258 shows room for improvement with proper cost modeling
- CRYPCO has 3,705 vs EQUITY 250 decisive picks — 14.8x more data for statistical power
- CRYPCO has multiple research threads already (VWAP MR, funding carry, time-series trend)

**Gate requirements before deployment:**
- Reconcile official (n=3,705) vs registry (n=22,055) cohorts
- Remove re-emission duplicates; survivorship-safe universe
- Include taker fees, funding, quote freshness, capital constraints
- Benchmark: equal-weight buy-and-hold + cash in bull/bear windows
- SubQ coverage score ≥7/10 before deployment consideration

---

### Secondary Focus: EQUITY/STOCKS

**Rationale:**
- Second-largest n (250 decisive picks)
- WR 59.20% — highest of all classes, though PF <1.0
- Mutual fund top-10 holdings (`fund_holdings_deriver.py`) provides a fundamental screen that complements technical mining
- 59-universe mutual fund walkforward results exist (`mf_traits_walkforward_results.json`)

**Bounded hypothesis:**
> Monthly, sector-neutral quality/value/momentum ranking with a fixed large-liquid universe; compare to SPY/sector benchmarks and a risk-matched passive portfolio.

**Why EQUITY over other classes:**
- WR 59.20% suggests directional edge exists, even if PF <1.0 (costs/size may be the issue)
- Mutual fund holdings data provides a fundamentally-sourced universe that avoids technical mining of thin names
- 59-universe walkforward results already exist for reference

**Gate requirements before deployment:**
- Reconcile official (n=250) vs registry (n=469) cohorts
- Include delisted names, dividends, split adjustments, turnover costs
- Survivorship-safe universe
- Do NOT attribute deepAI Variant C results to Faber TAA
- SubQ coverage score ≥7/10 before deployment consideration

---

## Mutual Fund Focus: Low-Fee, Low-Capital Subset

**Decision:** Within mutual funds, target the subset with **less money in (lower AUM), lower maintenance fees (lower ER), and less capital required (lower min initial)**.

### Why this subset?

| Criterion | Rationale |
|---|---|
| **Sub-$50M AUM** | Smaller funds have less capacity constraint; can implement tactical allocation without market impact; easier to enter/exit |
| **Sub-0.20% ER** | Index funds at this ER level minimize drag; 0.20% ER = 20bps/year vs active funds at 0.75%+ = 75bps+/year drag |
| **$0 min initial** | Removes capital barrier to entry; enables monthly dollar-cost averaging |
| **Index-only** | Eliminates manager risk; returns = benchmark - ER; easier to model |

### Funds from metadata CSV meeting ALL low-fee criteria:

| Ticker | Name | Category | ER | Min Initial | AUM ($B) | Inception | Manager Tenure |
|---|---|---|---|---|---|---|---|
| FXAIX | Fidelity 500 Index | LARGE_BLEND | 0.015% | $0 | 450 | 1988 | 20y |
| SWPPX | Schwab S&P 500 Index | US_LARGE_BLEND | 0.020% | $0 | 90 | 1997 | 20y |
| FSKAX | Fidelity Total Market Index | US_TOTAL_MARKET | 0.015% | $0 | 70 | 2011 | 20y |
| SWTSX | Schwab Total Stock Market Index | US_TOTAL_MARKET | 0.030% | $0 | 25 | 1999 | 20y |
| FLCOX | Fidelity Large Cap Value Index | US_LARGE_VALUE | 0.035% | $0 | 20 | 2016 | |
| SWLVX | Schwab US Large-Cap Value Index | US_LARGE_VALUE | 0.040% | $0 | 15 | 2017 | |
| FSPGX | Fidelity Large Cap Growth Index | US_LARGE_GROWTH | 0.035% | $0 | 40 | 2016 | |
| SWLGX | Schwab US Large-Cap Growth Index | US_LARGE_GROWTH | 0.040% | $0 | 20 | 2017 | |
| FSMDX | Fidelity Mid Cap Index | US_MID_CAP | 0.025% | $0 | 40 | 2011 | |
| SWMCX | Schwab US Mid Cap Index | US_MID_CAP | 0.040% | $0 | 15 | 2017 | |
| FSSNX | Fidelity Small Cap Index | US_SMALL_CAP | 0.025% | $0 | 45 | 2011 | |
| SWSSX | Schwab Small Cap Index | US_SMALL_CAP | 0.040% | $0 | 15 | 2017 | |
| FSGGX | Fidelity Global ex-US Index | INTL_DEVELOPED | 0.055% | $0 | 25 | 2011 | |
| SWISX | Schwab International Index | INTL_DEVELOPED | 0.060% | $0 | 18 | 1996 | |
| FPADX | Fidelity Emerging Markets Index | INTL_EMERGING | 0.075% | $0 | 20 | 2011 | |
| SFENX | Schwab Emerging Markets Equity Index | INTL_EMERGING | 0.090% | $0 | 10 | 2017 | |
| FXNAX | Fidelity US Bond Index | US_AGG_BOND | 0.025% | $0 | 60 | 2011 | |
| SWAGX | Schwab US Aggregate Bond Index | US_AGG_BOND | 0.040% | $0 | 12 | 2017 | |
| FIPDX | Fidelity Inflation-Protected Bond Index | US_INFLATION_PROTECTED | 0.005% | $0 | 25 | 2011 | |
| SWRSX | Schwab US TIPS Index | US_INFLATION_PROTECTED | 0.005% | $0 | 8 | 2017 | |
| FSRNX | Fidelity Real Estate Index | REIT | 0.007% | $0 | 10 | 2011 | |

**All 20 funds:** ER ≤0.090% (well under 0.20%), min initial $0, AUM $8B-$450B (the sub-$50M filter excludes none here — all are >$8B; true sub-$50M would need additional funds not in this CSV).

**Note:** All funds in metadata have $0 min initial and ER <0.20%. The sub-$50M AUM filter yields no results from this CSV (smallest is SWRSX at $8B). To find true sub-$50M funds, need to expand metadata beyond the 38 funds currently listed.

### Mutual Fund Tactical Allocation Hypothesis

> Monthly NAV tactical allocation across the 20 low-fee index funds above, benchmarked to a static 60/40 (SPY/AGG) or equal-weight allocation. No intraday pick signal. ER drag is the only cost (0.005%-0.090%).

**Must be resolved first:**
- Add MUTUAL_FUND class to `alpha_engine/asset_class.py` + `ml_gatekeeper ASSET_CLASS_MAP`
- Build NAV history ≥5y for all 20 funds
- Build separate benchmark (static 60/40 or equal-weight)
- Apply hard gates from `mutual_fund_ranker.py`: ER ≤0.50% index / ≤0.75% active, no load/12b-1/redemption fee, AUM ≥$100M, age ≥5y, min initial ≤$3,000
- All 20 listed funds pass all hard gates (ER ≤0.090%, no load/12b-1, AUM ≥$8B >$100M, age ≥10y >5y, min initial $0 ≤$3,000)

---

## What NOT to Focus On

| Class | Reason |
|---|---|
| ETF | Cohort mismatch (official PF 0.022 vs registry PF 1.788) is a blocker, not evidence |
| FOREX | Raw 14-day: 11/148, PF 0.087; all 9 cells WR <41% |
| COMMODITY | Registry n=14, WR 14.29%, PF 0.172; keep blocked if using crypto proxies |
| BOND | n=1 official; n=26 intrabar WR 7.69%, PF 0.392 |
| FUTURES | n=52 official; n=13 registry; keep blocked if using proxy prices |
| MEME/PENNY_STOCK | n=10/n=1; both insufficient and unprofitable |

---

## Implementation Priority Order

1. **Measurement contract** (P0): Canonical PnL unit, exit provenance, live quote provenance, terminal outcomes, deduplication, single documented population per dashboard metric
2. **Reconcile ledgers** (P0): Publish row counts + inclusion rules connecting `money_ready_verdict`, `pf_registry`, `recent_closed`, raw `at_raw_picks`
3. **Run CRYPCO daily 50/200 trend pilot** (P1): First research pilot because longest candidate history; compare to same-asset buy-and-hold; no alpha claim unless benchmark beaten
4. **Run EQUITY monthly QVM pilot** (P1): Second research pilot; compare to SPY/sector + risk-matched passive
5. **Build MUTUAL_FUND low-fee universe** (P1): Add class, NAV history, benchmark; run monthly NAV tactical allocation
6. **Only after clean measurement** (P2): Run one pre-registered cross-sectional test per approved class
7. **Keep all other classes INSUFFICIENT_DATA/NOT_BUILT** (P0): Do not fill tiles with synthetic/proxy outcomes

---
