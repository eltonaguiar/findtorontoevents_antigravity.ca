# Asset-Class-Specific Fixes (final_v3, 2026-11-14)

**Source of truth:** Remote `money_ready_verdict.json` generated 2026-11-14 20:58:53 UTC; `pf_registry.json` at 21:00:20 UTC; raw 48h/14d summaries at 21:06:14 UTC.  
**Cross-ledger caveat:** `money_ready_verdict` and `pf_registry` have materially different counts — do not merge rates without row-level reconciliation.

---

## Class Verdict Table (official intrabar)

| Class | n | WR | PF | Verdict | Action |
|---|---:|---:|---:|---|---|
| CRYPCO | 3,705 | 35.87% | 0.920 | NOT_READY | Research pilot #1 |
| EQUITY | 250 | 59.20% | 0.939 | NOT_READY | Research pilot #2 |
| ETF | 45 | 2.22% | 0.022 | INSUFFICIENT_DATA | Fix cohort mismatch first |
| FOREX | 612 | 32.19% | 0.660 | NOT_READY | G10 carry basket test |
| COMMODITY | 229 | 40.17% | 1.026 | WATCH | Fix cohort mismatch first |
| BOND | 1 | 0.00% | 0.000 | INSUFFICIENT_DATA | Acquire yield/duration data |
| FUTURES | 52 | 42.31% | 1.094 | INSUFFICIENT_DATA | Real feed + contract identity |
| MEME | 10 | 10.00% | 0.023 | INSUFFICIENT_DATA | Keep blocked |
| PENNY_STOCK | 1 | 0.00% | 0.000 | INSUFFICIENT_DATA | Keep blocked |
| MUTUAL_FUND | — | — | — | NOT_BUILT | Add infra; low-fee subset focus |

---

## CRYPCO — Priority #1 for research pilot

**Current evidence:** Official intrabar n=3,705; WR 35.87%, PF 0.920. Policy-clean registry is a different cohort (n=22,055; WR 42.09%, PF 0.258).

**Bounded hypothesis to test:**
> Daily 50/200-day time-series trend, long/flat, volatility-targeted on a frozen liquid universe. Compare with equal-weight buy-and-hold and cash in bull and bear windows. Treat only as a drawdown-control hypothesis until it adds benchmark-relative return.

**Must be resolved first:**
- Reconcile ledgers (official vs registry cohorts)
- Remove re-emission duplicates; test delisted/survivorship-safe universe
- Include taker fees, funding, quote freshness, capital constraints
- Do NOT use rejected VWAP or mega_mutation claims as proof

**SubQ coverage needed:** Universe (frozen liquid), time (daily ≥3y), costs (taker+funding+spread), regimes (bull/bear/choppy), sources (multi-exchange)

---

## EQUITY — Priority #2 for research pilot

**Current evidence:** Official intrabar n=250; WR 59.20%, PF 0.939. Registry cohort n=469; WR 40.72%, PF 0.662. High WR is not profitable when losses dominate.

**Bounded hypothesis to test:**
> Monthly, sector-neutral quality/value/momentum ranking with a fixed large-liquid universe; compare to SPY/sector benchmarks and a risk-matched passive portfolio.

**Must be resolved first:**
- Reconcile class names and entry/exit ledger
- Include delisted names, dividends, split adjustments, turnover costs
- Do NOT attribute deepAI Variant C results to Faber TAA (different rule, different window)
- Use mutual fund top-10 holdings (`fund_holdings_deriver.py`) as equity screen universe

**SubQ coverage needed:** Universe (fixed large-liquid), time (monthly ≥5y), costs (turnover+spread+commission), regimes (bull/bear), sources (multi-vendor fundamental data)

---

## ETF — Fix cohort mismatch first

**Current evidence:** Official intrabar n=45; WR 2.22%, PF 0.022. Registry cohort n=19; WR 68.42%, PF 1.788. The discrepancy is a blocker, not evidence to choose the favorable number.

**Bounded hypothesis to test:**
> Monthly tactical allocation across unleveraged, liquid equity/rates/commodity ETFs with a risk-matched static allocation benchmark.

**Must be resolved first:**
- Explain the cohort mismatch; correct ETF/BOND taxonomy
- Include distributions, expense ratios, spreads, leveraged-product decay

**SubQ coverage needed:** Universe (unleveraged liquid ETFs), time (monthly ≥3y), costs (ER+spread+turnover), regimes (bull/bear), sources (ETF issuer data)

---

## FOREX — G10 carry basket test

**Current evidence:** Official intrabar n=612; WR 32.19%, PF 0.660. Registry cohort n=432; WR 35.88%, PF 0.838. Raw 14-day window: 11 wins / 148 losses, PF 0.087.

**Bounded hypothesis to test:**
> A diversified G10 carry basket with a slow trend/risk-off overlay, benchmarked to a passive carry basket.

**Must be resolved first:**
- Timestamp/quote integrity; normalize pair direction
- Acquire historical policy-rate/forward-point and swap data
- Include spread, rollover, crisis gaps in cost model
- Do NOT infer edge from one-pair Sharpe

**SubQ coverage needed:** Universe (G10 pairs), time (daily ≥3y), costs (spread+rollover+swap), regimes (risk-on/risk-off), sources (central bank data)

---

## COMMODITY — Fix cohort mismatch first

**Current evidence:** Official intrabar n=229; WR 40.17%, PF 1.026 (WATCH). Registry cohort n=14; WR 14.29%, PF 0.172.

**Bounded hypothesis to test:**
> Cross-market time-series trend plus a separate term-structure carry test on liquid contracts.

**Must be resolved first:**
- Reconcile labels and ledgers; use real listed contracts, point-in-time contract chains
- Back-adjustment and explicit roll cost
- Keep blocked if current signals use crypto proxies

**SubQ coverage needed:** Universe (liquid futures contracts), time (daily ≥3y), costs (roll+spread+commission), regimes (contango/backwardation), sources (exchange data)

---

## FUTURES — Real feed + contract identity

**Current evidence:** Official intrabar n=52; WR 42.31%, PF 1.094. Registry cohort n=13; WR 30.77%, PF 1.009.

**Bounded hypothesis to test:**
> CTA-style diversified time-series trend across a declared futures universe, compared with same-market buy-and-hold and cash.

**Must be resolved first:**
- Real feed, contract/expiry identity, continuous-series construction
- Roll schedule, margin and liquidity-aware sizing
- Keep blocked if using proxy prices

**SubQ coverage needed:** Universe (declared futures universe), time (daily ≥3y), costs (roll+margin+slippage), regimes (trend/choppy), sources (exchange data)

---

## BOND — Keep INSUFFICIENT_DATA

**Current evidence:** Official verdict n=1; intrabar subfield n=26, WR 7.69%, PF 0.392. Registry cohort n=1.

**Bounded hypothesis to test:**
> Duration-managed trend/carry using Treasury yield-curve and total-return data, compared to a duration-matched benchmark.

**Must be resolved first:**
- Separate cash bonds from bond ETFs
- Acquire yield, duration, coupon/distribution, reliable mark data
- Keep `INSUFFICIENT_DATA` until then

**SubQ coverage needed:** Universe (Treasury curve), time (daily ≥3y), costs (spread+borrow), regimes (rising/falling rates), sources (Treasury/Fed data)

---

## MUTUAL_FUND — NOT_BUILT; add infra first

**Current evidence:** No established live class or clean realized cohort. 38 funds in `mutual_fund_metadata.csv`; ranker + walkforward results exist but no live picks.

**Bounded hypothesis to test:**
> Monthly NAV tactical allocation research only; no intraday pick signal.

**Must be resolved first:**
- Add MUTUAL_FUND class to `alpha_engine/asset_class.py` + `ml_gatekeeper ASSET_CLASS_MAP`
- Do NOT add stub scanner to create fake coverage
- Build universe, NAV history, fees, separate benchmark
- **Focus on low-fee subset** (see Focus Decision §I): sub-$50M AUM, sub-0.20% ER index funds, $0 min initial

**SubQ coverage needed:** Universe (index funds meeting low-fee criteria), time (monthly NAV ≥5y), costs (ER only, no load/12b-1), regimes (market cycles), sources (fund issuer NAV data)

---

## MEME/PENNY_STOCK — Keep blocked

**Current evidence:** n=10 / n=1 respectively, both insufficient and unprofitable.

**Must be resolved first:**
- Maintain no-size/blocked status until price integrity, liquidity, sample size, and a pre-registered thesis are demonstrated
