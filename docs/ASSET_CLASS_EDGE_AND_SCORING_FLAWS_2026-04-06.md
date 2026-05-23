# Asset Class Edge And Scoring Flaws

Date: 2026-04-06

## Dataset

Primary source:

- `audit_dashboard/data/dashboard_data.json`
- `picks.recent_closed`
- 3,500 closed picks total

Asset-class breakdown in this sample:

- CRYPTO: 2,855
- EQUITY: 471
- FOREX: 147
- COMMODITY: 12
- ETF: 12
- FUTURES: 3

This is a closed-book analysis of realized outcomes, not backtest theory.

## Executive Summary

The scoring stack is not globally good or globally bad. It behaves differently by asset class.

Current edge:

- **Crypto** is the only asset class with a strong, scalable edge in the current closed book.
- **Equity** has some ranking signal, but only in the upper score and trust bands.
- **Forex** is mostly noise unless trust is high.
- **Commodity / ETF / Futures** do not have enough clean sample to justify confidence in the current scorer.

Main flaw:

- the system still acts too much like one score can mean the same thing across every asset class
- that is false in the data

## 1. Base Performance By Asset Class

| Asset | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| CRYPTO | 2855 | 48.5% | +0.221% | 1.325 |
| EQUITY | 471 | 35.5% | -0.779% | 0.667 |
| FOREX | 147 | 31.3% | -0.279% | 0.514 |
| COMMODITY | 12 | 8.3% | -0.697% | 0.489 |
| ETF | 12 | 41.7% | -0.951% | 0.338 |
| FUTURES | 3 | 0.0% | -0.449% | 0.000 |

Takeaway:

- right now the scoring system should be treated as **crypto-first**
- everything else needs stricter gating or probation until closed-book quality improves

## 2. What Actually Predicts Outcomes By Asset Class

### CRYPTO

Correlations with realized `pnl_pct`:

- `trust_score`: `+0.234`
- `score`: `+0.177`
- `confidence`: `+0.077`
- `elite_score`: `+0.057`

Correlations with win/loss:

- `trust_score`: `+0.280`
- `score`: `+0.167`

Interpretation:

- crypto edge comes mostly from **trust + score**
- raw confidence adds little
- elite score is weaker than the final score

### EQUITY

Correlations with realized `pnl_pct`:

- `score`: `+0.277`
- `elite_score`: `+0.198`
- `trust_score`: `+0.194`
- `confidence`: `+0.059`

Interpretation:

- equity scoring is still salvageable
- score matters
- trust matters
- confidence is barely informative

### FOREX

Correlations with realized `pnl_pct`:

- `trust_score`: `+0.138`
- `elite_score`: `+0.055`
- `score`: `-0.036`
- `confidence`: `-0.198`

Interpretation:

- forex score is basically not working
- confidence is actively misleading
- trust is the only signal that looks remotely useful

### Small-sample asset classes

- COMMODITY, ETF, FUTURES are too small to fit stable scoring rules from this sample alone

## 3. Score Band Lessons

### Crypto

| Score Band | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| 0-29 | 69 | 36.2% | -1.013% | 0.483 |
| 30-39 | 327 | 42.8% | -0.020% | 0.975 |
| 40-49 | 1010 | 39.9% | -0.086% | 0.883 |
| 50-59 | 1096 | 54.9% | +0.506% | 1.819 |
| 60-69 | 299 | 59.2% | +0.645% | 2.823 |
| 70+ | 54 | 70.4% | +0.854% | 3.472 |

Crypto lessons:

- score is directionally correct
- `40-49` is still a bad band
- `50+` is where the edge really begins
- `70+` is strongest, but `60-69` is also genuinely good

### Equity

| Score Band | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| 0-29 | 52 | 13.5% | -2.482% | 0.227 |
| 30-39 | 194 | 26.3% | -1.721% | 0.416 |
| 40-49 | 105 | 41.9% | -0.045% | 0.975 |
| 50-59 | 110 | 56.4% | +0.868% | 1.586 |
| 60-69 | 10 | 30.0% | +0.549% | 1.439 |

Equity lessons:

- equity needs a much higher floor than low-30s
- `50-59` is the first convincing quality band
- `40-49` is almost breakeven, not premium

### Forex

| Score Band | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| 0-29 | 13 | 23.1% | -0.180% | 0.523 |
| 30-39 | 47 | 12.8% | -0.340% | 0.368 |
| 40-49 | 38 | 42.1% | -0.097% | 0.838 |
| 50-59 | 46 | 43.5% | -0.411% | 0.360 |
| 60-69 | 3 | 33.3% | -0.010% | 0.984 |

Forex lessons:

- forex score bands are not economically reliable
- even better WR bands still lose money
- score should not be trusted as a primary forex ranker

## 4. Trust Score Is The Real Cross-Asset Separator

### Crypto trust bands

| Trust | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| 0-2.9 | 1963 | 39.8% | -0.105% | 0.859 |
| 3-4.9 | 143 | 44.8% | +0.219% | 1.279 |
| 5-6.9 | 739 | 71.9% | +1.045% | 3.149 |
| 7+ | 10 | 80.0% | +3.240% | 11.800 |

### Equity trust bands

| Trust | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| 0-2.9 | 292 | 26.0% | -1.685% | 0.409 |
| 3-4.9 | 67 | 49.3% | +1.052% | 1.569 |
| 5-6.9 | 91 | 48.4% | +0.391% | 1.282 |
| 7+ | 21 | 66.7% | +0.908% | 2.002 |

### Forex trust bands

| Trust | N | WR | Avg PnL | PF |
|---|---:|---:|---:|---:|
| 0-2.9 | 86 | 26.7% | -0.296% | 0.416 |
| 3-4.9 | 24 | 25.0% | -0.940% | 0.122 |
| 5-6.9 | 37 | 45.9% | +0.191% | 1.468 |

Takeaway:

- trust is the single most reusable cross-asset quality feature
- if a pick has low trust, almost every asset class deteriorates fast
- current scorer should lean even harder on trust

## 5. Confidence Is Asset-Specific And Often Misleading

### Crypto

- confidence is mildly useful
- best buckets are `0.70-0.89`
- confidence is not the main driver

### Equity

- `0.90+` is actually one of the better equity buckets in this sample
- low/mid confidence is weaker than expected

### Forex

- high confidence is actively bad
- `0.80+` forex confidence is especially dangerous

Takeaway:

- confidence should not have one global interpretation
- it needs calibration by **strategy family × asset class**

## 6. R:R Does Not Mean The Same Thing Across Assets

### Crypto

- `2.0+` R:R: 52.3% WR, PF 2.318
- `1.5-1.99` R:R: 43.0% WR, PF 0.928

Crypto lesson:

- the system should stop assuming `1.5-2.0` is always the sweet spot
- wider R:R crypto setups are actually better in this closed sample

### Equity

- `2.0+` R:R: 28.0% WR, PF 0.506
- `1.5-1.99` R:R: 40.6% WR, PF 0.831

Equity lesson:

- wide-R:R equity setups are mostly fantasy targets
- equity prefers tighter targets than crypto

### Forex

- all R:R buckets are weak overall
- `2.0+` forex is especially bad here

Takeaway:

- current scorer is over-globalizing R:R logic
- R:R should be evaluated per asset class

## 7. Edge By Asset Class

### Best current edge: Crypto

Where the edge is:

- `score >= 50`
- especially `score >= 60`
- `trust_score >= 5`
- `strong = true`
- R:R `>= 2.0`

Best crypto systems in this sample:

- `signal_validation`
- `super_signals`
- `mercury2`
- `dna_winner_picks`
- `claude_gainer_st`

### Conditional edge: Equity

Where the edge is:

- `score >= 50`
- `trust_score >= 3`, preferably `>= 5`
- avoid low-score equity entirely

Equity is not broadly good, but it is not random either. It has a usable upper tail.

### Weak edge: Forex

Forex only starts to look usable when:

- `trust_score >= 5`

Even then, the sample is not strong enough to call the current scorer robust.

## 8. Flaws In Current Scoring

### Flaw 1: One score language across all assets

False assumption:

- a `55` in crypto means the same thing as a `55` in forex or equity

Data says:

- not true

### Flaw 2: Confidence is over-trusted outside calibrated contexts

Data says:

- equity and crypto do not use confidence the same way
- forex confidence is often anti-helpful

### Flaw 3: R:R logic is too global

Data says:

- crypto likes wide targets
- equity does not
- forex is weak regardless

### Flaw 4: Non-crypto is still being surfaced as if it is portfolio-ready

Data says:

- equity, forex, ETF, commodity are mostly sub-1 PF

### Flaw 5: The mid-score dead zone remains under-addressed

Data says:

- `40-49` is not a quality cohort in crypto
- it is only marginal in equity

## 9. Recommendations

### Crypto

- keep crypto as the primary asset class
- maintain a premium cohort at `score >= 60`
- treat `trust_score >= 5` as a major upgrade
- reward `strong = true`
- stop penalizing wider R:R by default

### Equity

- require `score >= 50`
- require higher trust
- cut low-score equity aggressively
- de-emphasize confidence until calibrated

### Forex

- heavily gate forex unless `trust_score >= 5`
- reduce the weight of score and confidence
- consider a forex probation mode until more clean profitable data exists

### Commodity / ETF / Futures

- keep in low-confidence / probation mode
- do not infer “edge” from these samples yet

### Cross-asset scorer design

Recommended priority order:

1. trust
2. asset-class-specific score floor
3. asset-class-specific R:R handling
4. asset-class-specific confidence calibration

## 10. Bottom Line

If you force one scoring language across all asset classes, the book gets worse.

The current evidence says:

- **Crypto:** real edge, scorer mostly works
- **Equity:** upper-tail edge only, needs stricter gating
- **Forex:** scorer is not trustworthy without high trust
- **Everything else:** insufficient evidence, keep on probation
