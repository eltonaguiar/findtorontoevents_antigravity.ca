# OOS Validation Report — Pre-Registered Split
**Generated:** 2026-05-16T05:49:17Z
**IS period:** pre-2026-04-01 (n=830)
**OOS period:** 2026-04-01 onward (n=4,170 total, closed picks only for metrics)
**Bootstrap:** 5,000 iterations, seed=42
**Multiple-testing correction:** DSR adjusted for n=18 systems tested

## System Rankings (OOS, closed picks only)

| System                       |     n |     WR |  OOS PF | CI-95-lo | CI-95-hi | P(PF>1.5) |   DSR |   AC1 | Tier |
|-----------------------------|-------|--------|---------|----------|----------|-----------|-------|-------|--------|
| kimi_signal_tracking         |   135 |  88.9% |   15.94 |    10.47 |    27.88 |    100.0% |  1.00 | -0.06 | ✅T1 |
| aggregated_picks             |   383 |  78.1% |    7.02 |     5.71 |     8.71 |    100.0% |  0.00 | 0.24⚠ | ✅T1 |
| stocks_competition           |    53 |  67.9% |    3.71 |     2.28 |     5.98 |     99.9% |  0.00 | 0.74⚠ | ✅T1 |
| signal_validation            |   179 |  55.3% |    1.82 |     1.41 |     2.36 |     89.5% |  0.00 | 0.18 | ✅T2 |
| rapid_fire                   |    47 |  51.1% |    1.67 |     1.01 |     2.72 |     62.7% |  0.00 | 0.06 | ⚠️Mon |
| luxalgo_filters              |   350 |  41.4% |    1.39 |     1.15 |     1.67 |     24.4% |  0.00 | 0.21⚠ | ⚠️Mon |
| quan_engine                  |   628 |  33.0% |    1.27 |     1.10 |     1.46 |      2.5% |  0.00 | 0.44⚠ | ⚠️Mon |
| dna_winner_picks             |   388 |  34.3% |    1.07 |     0.89 |     1.28 |      0.2% |  0.00 | 0.29⚠ | ❌Sub |
| signal_engine_mutations      |   110 |  34.5% |    1.00 |     0.69 |     1.39 |      2.2% |  0.00 | 0.25⚠ | ❌Sub |
| copy_trader_intel            |   142 |  35.2% |    0.95 |     0.71 |     1.28 |      0.4% |  0.00 | -0.10 | ❌Sub |
| copy_trader_highscore        |   183 |  36.1% |    0.93 |     0.72 |     1.20 |      0.1% |  0.00 | 0.60⚠ | ❌Sub |
| dna_rapid_fire_mutations     |   132 |  33.3% |    0.82 |     0.59 |     1.10 |      0.1% |  0.00 | 0.55⚠ | ❌Sub |
| ml_crypto_pred               |   837 |  35.1% |    0.82 |     0.73 |     0.92 |      0.0% |  0.00 | 0.21⚠ | ❌Sub |
| claude_gainer_st             |   112 |  28.6% |    0.71 |     0.48 |     0.99 |      0.0% |  0.00 | 0.59⚠ | ❌Sub |
| alpha_engine                 |   307 |  30.0% |    0.67 |     0.55 |     0.82 |      0.0% |  0.00 | 0.23⚠ | ❌Sub |
| mutation_lab                 |    39 |  10.3% |    0.19 |     0.04 |     0.40 |      0.0% |  0.00 | 0.45⚠ | ❌Sub |
| battleground                 |    27 |   0.0% |    0.00 |     0.00 |     0.00 |      0.0% |  0.00 | -0.10 | ❌Sub |

## Key Findings

### Tier 1 (CI-lower ≥ 2.0, P(PF>1.5) ≥ 90%)
- **kimi_signal_tracking**: OOS PF=15.94, WR=88.9%, n=135, CI=[10.47, 27.88]
- **aggregated_picks**: OOS PF=7.02, WR=78.1%, n=383, CI=[5.71, 8.71]
- **stocks_competition**: OOS PF=3.71, WR=67.9%, n=53, CI=[2.28, 5.98]

### Tier 2 (CI-lower ≥ 1.0, P(PF>1.5) ≥ 80%)
- **signal_validation**: OOS PF=1.82, WR=55.3%, n=179, CI=[1.41, 2.36]

### Monitoring (CI-lower ≥ 1.0 but P(PF>1.5) < 80%)
- **rapid_fire**: OOS PF=1.67, n=47, CI-lower=1.01
- **luxalgo_filters**: OOS PF=1.39, n=350, CI-lower=1.15
- **quan_engine**: OOS PF=1.27, n=628, CI-lower=1.10

### Sub-floor (CI-lower < 1.0 — do not size)
- **dna_winner_picks**: OOS PF=1.07, n=388
- **signal_engine_mutations**: OOS PF=1.00, n=110
- **copy_trader_intel**: OOS PF=0.95, n=142
- **copy_trader_highscore**: OOS PF=0.93, n=183
- **dna_rapid_fire_mutations**: OOS PF=0.82, n=132
- **ml_crypto_pred**: OOS PF=0.82, n=837
- **claude_gainer_st**: OOS PF=0.71, n=112
- **alpha_engine**: OOS PF=0.67, n=307
- **mutation_lab**: OOS PF=0.19, n=39
- **battleground**: OOS PF=0.00, n=27

## Serial Correlation Warnings
Systems with lag-1 autocorrelation |AC1| > 0.2 have correlated returns —
effective sample size is smaller than n. Bootstrap CI may be too optimistic.

- **aggregated_picks**: AC1=0.238 — reduce effective n by ~76%
- **stocks_competition**: AC1=0.738 — reduce effective n by ~26%
- **luxalgo_filters**: AC1=0.214 — reduce effective n by ~78%
- **quan_engine**: AC1=0.436 — reduce effective n by ~56%
- **dna_winner_picks**: AC1=0.292 — reduce effective n by ~70%
- **signal_engine_mutations**: AC1=0.247 — reduce effective n by ~75%
- **copy_trader_highscore**: AC1=0.603 — reduce effective n by ~39%
- **dna_rapid_fire_mutations**: AC1=0.546 — reduce effective n by ~45%
- **ml_crypto_pred**: AC1=0.215 — reduce effective n by ~78%
- **claude_gainer_st**: AC1=0.590 — reduce effective n by ~41%
- **alpha_engine**: AC1=0.235 — reduce effective n by ~76%
- **mutation_lab**: AC1=0.447 — reduce effective n by ~55%

---
*NOT FINANCIAL ADVICE. All figures from OOS period only.*
*Split pre-registered at 2026-04-01 before examining system performance.*