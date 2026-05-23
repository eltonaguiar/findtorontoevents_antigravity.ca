# Asset-Class Edge Analysis — 2026-04-30

## What was broken

`/audit` can rank picks with **generic** metadata such as `trust_score`,
`strat_fwd_wr`, and `strat_fwd_pf`, but it still drops most of the
**asset-class-specific evidence** needed to prove or refine an edge:

- PEAD picks lose the event context that matters most: earnings surprise
  magnitude, revision momentum, and time-since-earnings.
- FX and commodity picks are not published with carry, COT, curve, or macro
  context, so the dashboard cannot tell a true high-conviction carry/COT setup
  from a generic directional call.
- Crypto microstructure features exist in the feature store, but they are not
  consistently preserved in the lightweight closed-pick contract that powers
  `/audit`.
- UEPS now emits long-term equity candidates, but the current repo snapshot
  still shows `ueps_picks.json` carrying longs while `active_picks.json` carries
  **zero** `pick_type=long_term_value` rows. The long-term book is therefore not
  building a meaningful forward record inside the main audit loop.

That is the smoking gun: the platform has started to ship class-specific
strategies, but the audit contract is still mostly class-agnostic.

## What changed

This session added **read-only analysis and planning artifacts**, not live
pipeline mutations:

- Added [`tools/asset_class_edge_audit.py`](../tools/asset_class_edge_audit.py)
  to reproduce the current `/audit` snapshot analysis from local files.
- Added [`reports/PR_ASSET_CLASS_SIGNAL_CONTRACT_2026_04_30.md`](../reports/PR_ASSET_CLASS_SIGNAL_CONTRACT_2026_04_30.md)
  as a draft PR plan for the actual implementation work.

No live emitter, gate, resolver, or dashboard logic was changed in this turn.

## Methodology

### Local files inspected

- `audit_dashboard/data/dashboard_data.json`
- `alpha_engine/data/active_picks.json`
- `audit_dashboard/data/ueps_picks.json`
- `audit_trail/dashboard_generator.py`
- `audit_trail/pick_feature_store.py`
- `alpha_engine/vt_baby_strategies.py`
- `alpha_engine/long_term_pick_contract.py`
- `baby_strategies/equity_earnings_drift_pead.py`
- `audit_trail/pead_strategy.py`
- `alpha_engine/non_crypto_policy.py`
- `audit_trail/quality_gates.py`

### Repro command

```powershell
python tools/asset_class_edge_audit.py
```

Verification run used for this note:

- `2026-04-30T12:07:09-04:00`

Important caveat:

- `dashboard_data.json`, `active_picks.json`, and `ueps_picks.json` are hot
  files updated by background jobs. Counts may drift intra-day. The structural
  conclusions below stayed stable across repeated reads:
  - trust / forward metrics separate winners from losers better than raw
    `confidence`
  - PEAD is not a live active sleeve
  - UEPS longs are still not visible as `long_term_value` picks in the active
    audit book

## Current empirical snapshot

### Closed performance by asset class

Observed from `picks.recent_closed` in `audit_dashboard/data/dashboard_data.json`:

| Asset Class | n | WR | PF | Sum PnL % |
|---|---:|---:|---:|---:|
| CRYPTO | 1524 | 40.5% | 1.042 | 51.585 |
| FOREX | 786 | 50.9% | 1.559 | 15.935 |
| COMMODITY | 660 | 42.7% | 0.970 | -4.041 |
| EQUITY | 422 | 50.0% | 1.256 | 176.387 |
| ETF | 83 | 51.8% | 1.131 | 12.891 |
| BOND | 20 | 50.0% | 1.720 | 3.411 |

### Recent-window read

The broad class headline hides where the book is actually working:

- `EQUITY` is the strongest aggregate sleeve by total closed PnL, but recent
  30-pick performance is weak (`33.3%` WR, PF `0.865`). The edge is not
  “all equities”; it is a narrow subset.
- `FOREX` is healthier than expected right now. Recent 30 picks came in at
  `60.0%` WR and PF `2.474`, suggesting the recent policy tightening has not
  killed the good sleeves.
- `COMMODITY` remains historically damaged in the full sample, but the last
  30/100 windows improved after recent sub-class kills. That improvement is
  narrow and should not be mistaken for broad commodity robustness.
- `CRYPTO` still has the biggest sample but broad-sleeve quality is mediocre.
  Recent 30 closed picks were negative (`40.0%` WR, PF `0.701`), meaning the
  winners are being diluted by too many low-quality emissions.
- `ETF` remains thin and fragile: positive all-sample, bad recent 30.

## Where the edge actually lives

### Equity

Best current pockets:

- `rs-breakout-scout LONG`: `n=18`, `77.8%` WR, PF `6.700`
- `Breakout Momentum LONG`: `n=38`, `57.9%` WR, PF `1.528`
- `quality-minus-junk LONG`: `n=18`, `61.1%` WR, PF `1.435`

Interpretation:

- Equity is working when it is **quality-filtered or strength-filtered**.
- That matches the repo’s existing direction: `quality-minus-junk`,
  `rs-breakout-scout`, and PEAD/catalyst scaffolding.

### Forex

Best current pockets:

- `cta_cross_asset_tsmom SHORT`: `n=26`, `69.2%` WR, PF `9.597`
- `fx_smart_carry_trade_momentum LONG`: `n=18`, `50.0%` WR, PF `3.086`
- `forex_rsi2_mean_reversion LONG`: `n=219`, `48.9%` WR, PF `1.395`

Interpretation:

- FX wants **trend + carry + regime discipline**, not blind carry.
- `confidence` is not the useful selector here; forward stats and trust are.

### Commodity

Best current pocket:

- `cftc_cot_commercial_signal SHORT`: `n=24`, `66.7%` WR, PF `2.991`

Interpretation:

- Commodity edge is not broad trend-following right now.
- It is concentrated in **COT-informed positioning**, which is exactly why the
  dashboard should retain COT-specific fields instead of flattening everything
  into generic score columns.

### ETF

Best current pockets:

- `intermarket-flow-scout LONG`: `n=12`, `58.3%` WR, PF `1.771`
- `quality-minus-junk LONG`: `n=12`, `50.0%` WR, PF `1.051`

Interpretation:

- ETF edge looks like **sector/flow rotation**, not broad passive exposure.
- The recent ETF blacklist work appears directionally correct, but the sleeve
  is still too thin to trust without better context fields.

### Crypto

Best current pockets:

- `atr_percentile_gate LONG`: `n=22`, `95.5%` WR, PF `13.510`
- `mega_mutation_macd_rsi_m048 LONG`: `n=15`, `86.7%` WR, PF `10.040`
- `MeanReversionBB SHORT`: `n=17`, `64.7%` WR, PF `3.248`
- `claude_ml_moderate_mut LONG`: `n=39`, `59.0%` WR, PF `2.307`

Interpretation:

- Crypto already proves the mutation concept works when seeded from a real
  parent edge.
- The problem is not lack of strategy ideas. It is that the broad live sleeve
  still admits too much junk around the winners.

## What separates winners from losers

The most useful finding from the local snapshot is simple:

- `trust_score`, `strat_fwd_wr`, and `strat_fwd_pf` consistently separate good
  rows from bad rows.
- Raw `confidence` does **not** separate well across most asset classes.

Examples from the rank-tertile analysis:

### Equity

- High `trust_score` bucket: `63.8%` WR, PF `2.417`
- Low `trust_score` bucket: `37.1%` WR, PF `0.596`
- High `strat_fwd_wr` bucket: `72.3%` WR, PF `3.443`
- Low `strat_fwd_wr` bucket: `26.4%` WR, PF `0.479`

### Forex

- High `trust_score` bucket: `58.8%` WR, PF `2.831`
- Low `trust_score` bucket: `42.7%` WR, PF `0.625`
- High `strat_fwd_wr` bucket: `59.9%` WR, PF `2.889`
- Low `strat_fwd_wr` bucket: `42.4%` WR, PF `0.172`

### Crypto

- High `trust_score` bucket: `52.0%` WR, PF `1.608`
- Low `trust_score` bucket: `29.9%` WR, PF `0.776`
- High `strat_fwd_wr` bucket: `53.0%` WR, PF `1.565`
- Low `strat_fwd_wr` bucket: `27.4%` WR, PF `0.486`

Conclusion:

- High-conviction logic should lean much harder on
  `trust_score + forward stats + class-specific evidence`.
- It should lean less on generic `confidence`.

## PEAD / long-term equity status

PEAD is present in the codebase, but not meaningfully live in the active audit
book:

- `alpha_engine/vt_baby_strategies.py` includes `vt_earnings_pead`
- `baby_strategies/equity_earnings_drift_pead.py` exists
- `audit_trail/pead_strategy.py` exists
- `alpha_engine/long_term_pick_contract.py` already defines long-term
  earnings/fundamental fields

Observed in the snapshot:

- `active long_term_value rows`: `0`
- `active PEAD-like rows`: `0`
- `recent_closed PEAD-like rows`: `8`
- PEAD-like closed strategy set: `['post-earnings-rev-scout']`

Those 8 closed PEAD-like rows were not bad:

- WR `62.5%`
- PF `1.156`
- Sum PnL `%` `+2.2902`

So the conclusion is **not** “PEAD has failed.”

The real conclusion is:

- PEAD has **insufficient live flow** into the main active/closed audit loop.
- The audit contract also discards too much event metadata to improve it with
  confidence.

## UEPS status

During the verification run, `ueps_picks.json` still showed:

- `summary.n_long = 30`
- `summary.n_short = 0`
- `summary.n_swing = 0`

At the same time, `alpha_engine/data/active_picks.json` still showed:

- `0` rows with `pick_type = long_term_value`

That means the long-term equity project is still operationally incomplete from
the perspective of the main `/audit` forward book, even though the UEPS sidecar
is emitting candidates.

## Missing data points by asset class

### Equity / PEAD / long-term value

Missing from the published audit contract:

- standardized earnings surprise (`surprise_pct` plus z-score / SUE)
- `revision_momentum_7d`
- `consecutive_beats`
- `days_since_earnings` / `hours_to_earnings`
- `sector_etf` / benchmark-relative strength
- insider cluster score from SEC Form 4
- activist score / flag from SEC Schedule 13D

Why these matter:

- PEAD and analyst revision literature points to post-announcement
  underreaction, not just raw price trend.
- The SEC’s APIs and filings already make these event streams accessible.

### ETF

Missing:

- sector / theme tag
- benchmark-relative momentum
- breadth (`% above 50DMA`, `% above 200DMA`)
- volatility regime
- correlation cluster / HRP weight
- macro sensitivity (`rates_beta`, `oil_beta`, `dxy_beta` where relevant)

### Forex

Missing:

- carry differential / rate differential
- real-rate differential
- CFTC COT net positioning z-score
- macro event proximity (CPI/FOMC/NFP etc.)
- session / liquidity regime
- volatility-scaling input

### Commodity / futures

Missing:

- CFTC disaggregated COT fields
- forward-curve slope / contango-backwardation
- roll yield
- inventory / convenience-yield proxy
- USD beta
- seasonality bucket

### Crypto

Partially present in the feature store but not consistently retained in the
lightweight audit contract:

- funding rate
- basis / premium index
- open-interest delta
- liquidation pressure
- order-book imbalance
- BTC-relative strength / market beta

## Industry-standard references used for the gap analysis

Primary sources only:

- AQR, *Quality Minus Junk*:
  <https://www.aqr.com/Insights/Research/Working-Paper/Quality-Minus-Junk>
- Moskowitz, Ooi, Pedersen, *Time Series Momentum* (SSRN):
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463>
- Moreira, Muir, *Volatility Managed Portfolios* (NBER):
  <https://www.nber.org/papers/w22208>
- Berge, Jordà, Taylor, *Currency Carry Trades* (NBER):
  <https://www.nber.org/papers/w16491>
- Brunnermeier, Nagel, Pedersen, *Carry Trades and Currency Crashes* (NBER):
  <https://www.nber.org/papers/w14473>
- CFTC Commitments of Traders overview:
  <https://www.cftc.gov/MarketReports/CommitmentsofTraders/AbouttheCOTReports/index.htm>
- CFTC disaggregated explanatory notes:
  <https://www.cftc.gov/MarketReports/CommitmentsofTraders/DisaggregatedExplanatoryNotes/index.htm>
- CME on contango/backwardation:
  <https://www.cmegroup.com/education/courses/introduction-to-ferrous-metals/what-is-contango-and-backwardation>
- SEC EDGAR APIs:
  <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>
- SEC Form 4:
  <https://www.sec.gov/submit-filings/forms-index/aboutformsform4>
- SEC Schedule 13D / 13G filing guide:
  <https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/file-schedule-13d-schedule-13-g-corresponding-amendments>
- Zhang, *Analysts’ Responsiveness and the Post-Earnings-Announcement Drift*:
  <https://business.columbia.edu/sites/default/files-efs/pubfiles/3737/zhang.pdf>
- Binance funding-rate explainer:
  <https://academy.binance.com/articles/what-are-funding-rates-in-crypto-markets>

## Recommended direction

Do **not** add more broad strategies first.

Instead:

1. Fix the audit data contract so each class keeps the fields that explain its
   actual edge.
2. Promote only the already-proven sleeves inside each class.
3. Use DNA mutations **around proven parent edges**, not around broad weak
   sleeves.

That implementation plan is written up in:

- [`reports/PR_ASSET_CLASS_SIGNAL_CONTRACT_2026_04_30.md`](../reports/PR_ASSET_CLASS_SIGNAL_CONTRACT_2026_04_30.md)

## Verification

- Ran `python tools/asset_class_edge_audit.py`
- Confirmed the helper exits `0`
- Re-read source files named in the methodology section
- Cross-checked current repo data against the last-week commit history for:
  - UEPS wire-up / active-book sync
  - PEAD integration
  - catalyst wiring
  - recent ETF / commodity kill-switch work
