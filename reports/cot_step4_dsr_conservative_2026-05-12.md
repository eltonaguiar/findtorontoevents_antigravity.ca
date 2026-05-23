# COT Step 4 — DSR Conservative Re-Verification (2026-05-12)

## Goal
Confirm DSR ≥0.85 under conservative `n_trials` assumptions (42 → 131 → 500).

## Methodology
- Source: `trading_picks` DB, strategy `cot_positioning`, symbol `CT=F`
- Query: 100 closed trades (status IN WON/LOST/WIN/LOSS/TP_HIT/SL_HIT)
- Metrics: pnl_pct array → Sharpe + DSR across multiple n_trials thresholds
- Function: `alpha_engine.deflated_sharpe.deflated_sharpe_ratio()` (Bailey & Lopez de Prado 2014)

## Results

### Sample Statistics
- **n:** 100 closed trades
- **mean pnl_pct:** 0.038414 (3.84% per trade)
- **stdev pnl_pct:** 0.024114
- **Sharpe (non-annualized):** 1.5930
- **Skewness:** −2.3392 (negative tail, survivor bias)
- **Excess Kurtosis:** 4.2417 (fat tails)

### DSR Table

| n_trials | DSR | Pass (≥0.85)? |
|---|---:|---|
| 42 (default) | **0.9999** | ✓ PASS |
| 131 (dashboard payload) | **0.9994** | ✓ PASS |
| 500 (mutation penalty) | **0.9974** | ✓ PASS |

### Verdict
**PASS** — DSR = **0.9974** at n_trials=500 remains safely above 0.85 threshold.

The strategy's observed Sharpe survives **even at 500 independent trials** correction. This is a very strong statistical signal: the probability that the 90% WR is a false positive from multiple testing bias is <1%.

## Caveats
1. **Sharpe variance assumes IID returns.** COT signals are monthly-frequency; consecutive picks may have serial correlation not captured here.
2. **Negative skew (−2.34).** The distribution has a left tail; worst-case drawdowns could be worse than mean±σ suggests.
3. **n=100 is modest.** While sufficient for DSR, a 200-pick replication would be stronger.

## Forward Gate Status
✓ **Step 4 gating criterion SATISFIED:** DSR ≥ 0.85 at n_trials=500.

Ready to proceed to **Step 5** (sample-window robustness) and **Step 6** (forward paper-pilot).
