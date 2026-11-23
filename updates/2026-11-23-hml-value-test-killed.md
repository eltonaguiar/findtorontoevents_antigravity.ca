# HML (value) test — run once, KILLED on the gross signal being absent

**Date:** 2026-11-23
**Rule:** frozen in `docs/preregistration/HML_VALUE_TEST_2026-11-22.md` §5, unchanged
**Runner:** `tools/hml_pit_backtest.py` (read-only)
**Artifact:** `reports/hml_result.json`

---

## The rule that was applied

Kill if **either** the OOS annualised net return on committed capital ≤ **4.32%**, or
its one-sided 95% upper bound ≤ 4.32%. The bar is `HURDLE_TBILL_APR = 0.0432`
(`tools/capacity_model.py`), not a rounded 4.3%.

## What was built to run it

- **Point-in-time fundamentals.** Book equity and share count come from annual balance
  sheets, usable at a rebalance date only if `period_end + 90 days <= date`. A 10-K is
  never traded before it could have been filed. This is the discipline that stops a
  value premium being manufactured out of look-ahead.
- **Share count uses `Ordinary Shares Number`, not `Share Issued`.** `Share Issued` is
  mis-reported by **2×** for some dual-class names — XOM 2026-03-31 read 8.02B against
  a true 4.14B. `Ordinary Shares × price` reconciles to yfinance `marketCap` at ratio
  **1.000**, which is how the correct field was identified.
- **Cost from the measurement, not a constant.** 4.97 bp round trip, taken as the
  conservative maximum of the Corwin-Schultz and Roll medians plus the SEC fee.

## Result

| | |
|---|---|
| Universe | 200 requested → **186 usable** (both prices and fundamentals) |
| Rebalances | **44 monthly**, 2021-11 → 2026-11 |
| Turnover | 14.8%/month |
| Gross annual | **+0.11%** |
| Net annual | **+0.02%** |
| SE of annual net | 6.65% |
| 95% upper bound | +10.96% |
| Hurdle | 4.32% |
| **Verdict** | **KILL** (arm 1) |

## The important nuance: cost did not kill this — the signal is simply absent

Cost drag is `14.8%/month × 4.97 bp × 12 ≈ 0.09%/yr`. Gross is `+0.11%/yr`. So
**even at zero cost the family misses the 4.32% hurdle by more than four percentage
points.**

That distinction matters: a cost-driven kill is fragile to the cost constant, and open
to the objection that the constant was wrong. This kill is not. The gross value
premium is absent from this universe over this window.

## Verification that the test was real, not broken

A null is only worth reporting if the machinery works. The legs are a textbook HML
portfolio:

- **LONG (cheap):** banks and insurers — `BAC`, `C`, `COF`, `CFG`, `FITB`, `ALL`,
  `CB`, `AIZ`, `CINF`; utilities — `DUK`, `ED`, `EXC`, `EVRG`, `ES`, `ETR`; plus
  `F`, `CVS`, `BRK-B`.
- **SHORT (expensive):** high-multiple growth — `ADBE`, `AVGO`, `AMAT`, `ANET`,
  `CDNS`, `ADSK`, `CRWD`; consumer growth — `AMZN`, `CMG`, `BKNG`, `ABNB`, `DXCM`.

The sort is doing exactly what HML should do. The premium just isn't there: 20 of 44
months positive, mean monthly gross +0.009%, sd 3.67%.

## Why survivorship does not rescue it

The universe is today's S&P 500, so it is survivor-conditioned — blocker B1 is only
**partially** cleared. This was observed live rather than asserted: `EA`, `DFS` and
`EQR` sit in the ticker list but returned *"possibly delisted, no price data found"*
and were dropped, which is the survivorship mechanism happening in front of us.

The bias direction is **upward** — survivors are the winners. A true point-in-time
universe would therefore have produced a **worse** result than +0.11%. The residual
bias cannot turn a kill into a pass.

## Borrow: declared, and immaterial to this verdict

Questrade does not publish short borrow rates. **It is carried at 0 bp, which is a
stated limitation, not a finding.** Sensitivity: the short leg is 50% of committed
capital, so 0.5%/yr borrow costs 25 bp/yr of committed capital, and 2%/yr costs
100 bp/yr.

None of that can change the answer: net is `+0.02%` against a `4.32%` hurdle, and
borrow only pushes it down. B3 would matter for a family that **passed**; this one did
not.

## This is the result the pre-registration predicted

§6 recorded *before* the run that a large-cap post-2006 null is the **expected**
outcome, not a failure — sourced to Martineau (2022), whose abstract states *"For
large stocks, PEAD have been non-existent since 2006"*, with Chordia-Subrahmanyam-Tong
(2014) and Richardson-Tuna-Wysocki (2010) supporting the decay mechanism.

The observed null corroborates that premise. It is a real answer rather than an absence
of one.

## Tally

HML moves UNKNOWN → **NOT_INVESTABLE**.
`0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN over 14 rows`.

## Reproduce

```
python3 tools/equity_cost_hml.py --limit 200     # cost, writes reports/equity_cost_hml.json
python3 tools/hml_pit_backtest.py --limit 200    # HML,  writes reports/hml_result.json
```

Zero capital sanctioned. Not investment advice.
