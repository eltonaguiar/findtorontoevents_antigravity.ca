# Durable funds and genuinely zero-expense ETFs

## Bottom line

**There are real historical winners, and there are real zero-expense ETFs. Neither finding proves that we can select tomorrow's winner.**

- BNY's issuer pages currently show **BKLC and BKAG at 0.00% gross and net expense ratios**. These are ETFs, unlike Fidelity ZERO mutual funds.
- Several surviving active mutual funds beat SPY over roughly 32 years, after the fund expenses embedded in adjusted NAV. Calling every active strategy incapable of beating an index is too strong.
- Our nine preregistered selection trials did **not** establish a repeatable way to choose the next winners. No trial beat 95% of comparable random-selection baskets.
- No fund passed the entire frozen descriptive screen. **No MONEY-READY or CANDIDATE promotion, no production symbol changes, no orders.** FAIL here means failure to establish the required proof, not that the fund necessarily lost money.

This is historical research, not individualized investment advice or a promise of future returns.

## What was actually tested

H-141 was registered before downloading the new return data, in main commit
[`bdbe4ab06c0fd68bb1d89d564e4b34a974286fc0`](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/commit/bdbe4ab06c0fd68bb1d89d564e4b34a974286fc0).
The exact [frozen protocol](symbol_durability_protocol_2026-10-23.json) declares 95 symbols: 23 US equity mutual funds, 29 US equity ETFs, 30 descriptive bond/international/commodity/balanced products, and 13 Canadian products.

All 95 downloaded successfully. US histories currently stop October 21, 2026; Canadian histories include October 22 where available. The protocol end date is a ceiling, not a claim that every vendor series reaches that date. Dates are recorded per input and per comparison. The later two-ETF fee comparison is explicitly a **post-registration descriptive addendum**, not an expansion or rescue of H-141's frozen trials.

### ELI5: the important distinction

Finding the runner who won yesterday's race is easy. The useful question is whether a rule, written **before** the race, consistently chooses next year's winner. We did both: described historical winners, then separately tested three rules for choosing future holdings.

### Selection and holding rules

At each year-end, use the preceding three calendar years and at least 700 observed daily prices. Rank by:

1. Best trailing total return.
2. Best trailing daily Sharpe, with a zero cash-rate assumption.
3. Lowest trailing daily volatility.

Buy the top three in equal starting amounts at the **next observed close**, then hold until the next annual execution. Weights drift as prices change; this is not daily rebalancing. Sell and replace at each annual boundary, conservatively charging full round-trip costs even when holdings recur.

- **Holding period:** approximately one year per selection, not minutes or days.
- **Take profit / stop loss:** none. Exit is the scheduled annual rebalance or final sample valuation. These are funded fund portfolios, not price-target trade signals.
- **Position sizing:** one-third initial allocation to each selected fund, no leverage.
- **Costs:** 10 basis points per side; stress at 20 per side. Ongoing fund expenses are already embedded in adjusted NAV and are not subtracted twice.
- **Benchmark:** SPY in USD on matching dates. Canadian descriptions use ZSP.TO in CAD; CAD returns are not compared directly with USD returns.
- **Evaluation:** selectors start in 2005; the table below uses the historical 2016+ reporting interval. This is not a sealed prospective holdout.

## The less-obvious historical winners

Same interval: January 3, 1995 through October 21, 2026. SPY's matching CAGR was **11.21%**. CAGR is annual compounded growth; MDD is the largest daily peak-to-trough loss, including unrealized losses.

| Fund | Annual growth | Worst drawdown | First-half excess over SPY | Second-half excess |
|---|---:|---:|---:|---:|
| FSCSX, software/IT sector | 15.38% | 64.66% | +6.08 pp/year | +2.19 pp/year |
| FDGRX, growth | 14.91% | 71.61% | +2.23 | +5.27 |
| VPMCX, PRIMECAP | 13.70% | 52.62% | +3.62 | +1.31 |
| FCNTX, Contrafund | 13.52% | 49.19% | +3.32 | +1.26 |
| FSPHX, health care sector | 12.59% | 44.45% | +2.52 | +0.20 |

**Interpretation:** VPMCX and FCNTX are worth further diligence as historical active-fund counterexamples, not buy recommendations. FSCSX's apparent advantage is heavily concentrated in a sector and came with a 65% fall; FDGRX fell roughly 72%. None resembles a low-risk secret money machine.

Surviving funds were selected with hindsight. Growth/sector risk, changing managers, share-class duplication, and the absence of dead or merged funds prevent interpreting these differences as proven manager skill. Current purchase eligibility, minimums, historical loads and platform restrictions were not independently established. Do not assume these are available to a Canadian beginner or open to new investors.

### Did they survive bad calendar years?

These are **calendar-year total returns**, not intrayear drawdowns:

| Fund | 2008 | 2020 | 2022 |
|---|---:|---:|---:|
| FSCSX | -42.14% | +45.55% | -29.13% |
| FDGRX | -40.90% | +67.42% | -33.86% |
| VPMCX | -32.09% | +17.16% | -15.21% |
| FCNTX | -37.16% | +32.48% | -28.31% |
| FSPHX | -32.49% | +24.57% | -12.82% |

A profitable full calendar year can conceal a severe temporary crash. That is why daily drawdown is reported separately.

## Could the preregistered rules find those winners?

Historical 2016+ results; matched SPY CAGR **14.96%**. All nine trials are shown, including failures. Random percentile compares daily Sharpe with 500 random baskets drawn from each year's same eligible universe, at the same costs.

| Universe | Rule | CAGR | MDD | Random percentile | Paired annual excess 95% interval |
|---|---|---:|---:|---:|---|
| Mutual funds | Past return | 15.01% | 39.73% | 18.6 | [-4.02, +5.45] pp |
| Mutual funds | Past Sharpe | 13.46% | 39.73% | 5.0 | [-4.94, +3.47] |
| Mutual funds | Low volatility | 12.25% | 36.66% | 31.0 | [-5.01, -0.21] |
| ETFs | Past return | 14.19% | 34.82% | 27.4 | [-4.14, +4.04] |
| ETFs | Past Sharpe | 9.09% | 37.95% | 1.0 | [-9.37, -0.39] |
| ETFs | Low volatility | 9.77% | 31.99% | 24.4 | [-10.18, -0.16] |
| Combined | Past return | 13.04% | 38.10% | 10.0 | [-5.51, +3.39] |
| Combined | Past Sharpe | 8.86% | 40.02% | 0.2 | [-9.81, -0.36] |
| Combined | Low volatility | 9.56% | 31.45% | 21.6 | [-10.11, -0.63] |

The mutual-fund return rule's roughly 0.05 percentage-point annual advantage is **not convincing evidence**: its uncertainty interval spans losses, and its risk-adjusted performance was below most random baskets.

### ELI5: what these tests mean

- **Random-selection percentile; gate 95:** did our fund-picking rule beat a monkey choosing three eligible funds each year? The best result was 31.0, not 95. This is **not** the GROK random-entry test; it does not establish entry timing skill.
- **Paired block interval; lower bound must exceed zero:** resample matching roughly monthly stretches of strategy-minus-SPY returns. Every lower bound was below zero. These are intervals for annualized arithmetic excess, not CAGR or PF intervals.
- **Daily drawdown; screen ceiling 20%:** measure how far the piggy bank fell along the way. Every selector lost at least 31.45% peak-to-trough.
- **Both halves and forward windows:** don't let one lucky era carry the whole story. Individual historical survivors can pass this descriptive check without proving that our selection rule could have identified them.
- **Lucky-guess correction / sealed forward evidence:** still unverified. A list of nine new trials is not the complete history of all ideas tried across the repository.

The existing edge-stability harness was also run without relaxing its thresholds. Sparse annual fund observations do not create enough populated 14-day windows for its usual live-pick test. Its UNTESTED diagnostic is not an admissibility pass.

## Genuine zero-expense ETFs: matched-date comparison

Issuer sources retrieved during this audit:

- [BKLC, BNY US Large Cap Core Equity ETF](https://www.bny.com/investments/us/en/individual/products/etf/fund/bny-mellon-us-large-cap-core-equity-etf.html): **0.00% gross and net expense ratios**. The issuer notes a 3-for-1 share split on July 17, 2026; adjusted prices must handle it.
- [BKAG, BNY Core Bond ETF](https://www.bny.com/investments/us/en/individual/products/etf/fund/bny-mellon-core-bond-etf.html): **0.00% gross and net expense ratios**.
- [Fidelity index-fund comparison](https://www.fidelity.com/mutual-funds/investing-ideas/index-funds): FXAIX and FSKAX each **0.015%** expense ratio, dated February 1, 2026.

These are different exposures, so compare equities with equities and bonds with bonds. No additional trading/FX/tax/platform costs are included in this descriptive buy-and-hold table.

| Comparable basket | Fund | Annual growth | Worst drawdown |
|---|---|---:|---:|
| US large caps, Apr 14 2020-Oct 21 2026 | BKLC, 0% expense ETF | 18.42% | 26.14% |
| Same dates | FNILX, Fidelity ZERO mutual fund | 18.28% | 25.40% |
| Same dates | FXAIX, 0.015% index mutual fund | 18.33% | 24.50% |
| Same dates | SPY | 18.23% | 24.50% |
| Same dates | FCNTX, active mutual fund | 20.02% | 32.59% |
| Same dates | VPMCX, active mutual fund | 19.89% | 25.25% |
| Same dates | FSCSX, sector mutual fund | 14.09% | 37.06% |
| Total US, Aug 3 2018-Oct 21 2026 | FZROX, Fidelity ZERO mutual fund | 14.15% | 34.96% |
| Same dates | FSKAX, 0.015% index mutual fund | 14.01% | 35.01% |
| Same dates | VTI | 14.03% | 35.00% |
| Bonds, Apr 24 2020-Oct 21 2026 | BKAG, 0% expense ETF | -0.25% | 18.52% |
| Same dates | AGG | -0.22% | 18.43% |
| Same dates | BND | -0.20% | 18.58% |

**Key findings:** free does not mean worse, but it also does not mean better. BKLC was competitive with low-cost alternatives. BKAG lost money over this window despite no fund expense: bond prices can fall when rates rise. FSCSX, the best 1995+ retrospective performer above, substantially lagged the cheap broad-market choices over this later common period.

The equity ETF windows begin after the initial March 2020 crash because the ETFs did not yet exist. They cannot establish survival through 2008 or the initial COVID collapse. No invented prelaunch history is used. The difference between near-zero-fee funds is not solely a fee effect: indices, holdings, timing and tracking also differ. Fidelity's dynamic product pages did not expose usable current minimum/access facts in this retrieval; those details remain unverified rather than copied from a model answer.

## Canadian starter context, kept separate

Issuer-verified current fee fields:

| Fund | Management fee | Reported MER | Interpretation |
|---|---:|---:|---|
| [XEQT](https://www.blackrock.com/ca/investors/en/products/309480/ishares-core-equity-etf-portfolio) | 0.17% | 0.19% | Management fee reduced December 18, 2025 |
| [VBAL](https://www.vanguard.ca/en/product/etf/asset-allocation/9578/vanguard-balanced-etf-portfolio) | 0.17% | 0.22% | MER is not the same as the management fee |

On $1,000 held for a year at a constant balance, those reported MERs are approximately **$1.90 and $2.20**, respectively. They are embedded expenses, not a guarantee of a specific dollar bill. We did not establish that a permanently zero-MER Canadian all-in-one product does not exist; a categorical claim would exceed this search.

Matched August 14, 2019-October 22, 2026, in CAD:

| Fund | CAGR | MDD |
|---|---:|---:|
| XEQT | 14.41% | 29.74% |
| VEQT | 14.41% | 30.45% |
| VBAL | 8.68% | 21.19% |
| VGRO | 11.55% | 25.36% |
| ZSP, Canadian-listed S&P 500 exposure | 16.99% | 26.94% |

The balanced fund had lower returns and smaller drawdown, not a guaranteed loss cap. Global all-in-one exposure differs from a US-only index, so this is not an equal-risk manager competition. XBAL and XGRO's longer vendor series cross earlier mandates; those full-series descriptions must not be advertised as the modern all-in-one strategy's historical track record.

[Wealthsimple pricing](https://www.wealthsimple.com/en-ca/pricing) currently advertises $0 stock commissions; its [fractional-order documentation](https://help.wealthsimple.com/hc/en-ca/articles/4413542937627-Understanding-fractional-orders) requires at least $1 **for supported symbols**. This does not verify fractional eligibility for every ticker, waive FX charges, establish TFSA eligibility/contribution room, or make the underlying fund fee zero. BNY ETFs are US-listed; Canadian broker access and FX costs need checking.

## Limitations that prevent certification

1. Current survivors only; no point-in-time dead/merged-fund universe. Many share classes duplicate portfolios.
2. Eligibility requires subsequent full holding-year data, creating a disclosed future-completeness selection bias. This is not certifiable causal OOS evidence.
3. Adjusted prices come from a single vendor. Cached hashes prove reproducibility, not independent price accuracy. Distribution adjustments and historical revisions remain vendor dependencies.
4. No current fee is subtracted from historical NAV again; actual historical loads, trading restrictions, taxes, FX and platforms remain incompletely modeled.
5. Overlapping 1/3/5-year windows are dependent observations; sectors and mixed assets are not like-risk SPY alpha tests.
6. No DSR/PBO or matched random-entry proof, calibrated winning probability, sealed forward track record, or portfolio-level capacity test.
7. Frozen daily data can be incomplete or revised. Input manifests and actual observed endpoints are part of the deliverable.

## Reproduce

From the isolated research checkout, with existing numpy/pandas/pytest dependencies:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_fund_durability.py -q -p no:cacheprovider
python3 tools/fund_durability.py --help
python3 tools/fund_durability.py fetch --cache /path/to/cache --output /path/to/cache/manifest.json
python3 tools/fund_durability.py run --cache /path/to/cache --output /path/to/results.json
python3 tools/fund_durability.py fetch --symbols BKLC BKAG --cache /path/to/extra --output /path/to/extra/manifest.json
python3 tools/fund_durability.py compare --cache /path/to/cache --extra-cache /path/to/extra --symbols BKLC FNILX FXAIX SPY FCNTX VPMCX FSCSX --output /path/to/large-cap.json
python3 tools/fund_durability.py compare --cache /path/to/cache --extra-cache /path/to/extra --symbols BKAG AGG BND --output /path/to/bonds.json
python3 tools/fund_durability.py compare --cache /path/to/cache --symbols FZROX FSKAX VTI --output /path/to/total-us.json
python3 tools/fund_durability.py compare --cache /path/to/cache --symbols XEQT.TO VEQT.TO VBAL.TO VGRO.TO ZSP.TO --output /path/to/canada.json
```

Re-fetching later may change vendor-adjusted history; identical-cache reruns are the determinism check. Compact results, all trials and cache manifests accompany this report; raw vendor payloads remain local research evidence.

## QA and independent review

The 12 targeted tests passed, including a real subprocess invocation against synthetic hashed cache files. The complete nine-trial run was repeated and was byte-identical. Independent review identified a latent skipped-year risk-metric issue; missing schedule days now remain explicit zero-yield cash observations. All nine frozen trials have zero calendar gaps, and the review correction left their results byte-identical.

Full-result SHA256: `ca3e56dc680f1802c8a6b33299ad32ea5718168cb986c79390f441d9a9528204`.

Machine-readable deliverables: [all symbols/trials/manifests](fund_durability_results_2026-10-23.json) and [matched fee comparisons](fund_fee_comparisons_2026-10-23.json). Full repository CI was not run; the previously observed unrelated pandas `freq="ME"` collection problem was not patched.
