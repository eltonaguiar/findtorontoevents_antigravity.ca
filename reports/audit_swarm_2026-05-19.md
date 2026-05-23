# Audit Swarm Report — 2026-05-19

**Generated:** 2026-05-19  
**Engines used:** deepseek, openrouter, ofox (combined); deepseek (P1/P2/P4); openrouter (P3)  
**Swarm run directories:** `swarm_runs/audit_20260519`, `swarm_runs/audit_20260519_p1..p4`  
**Total cost:** ~$0.0097  

---

## PART 1: GROK FEEDBACK VALIDATION

### Grok Suggestion 1: DSR Formula

```python
dsr = sharpe * norm.cdf(sharpe) - (1 - norm.cdf(sharpe))
```

**VERDICT: OVERSIMPLIFIED**

This formula simplifies to `(sharpe + 1) * norm.cdf(sharpe) - 1`. For SR=1.0, it outputs 0.683 — which is just norm.cdf(1.0), the probability of SR > 0 under normality. It resembles an expected shortfall calculation, NOT the Deflated Sharpe Ratio.

The correct DSR (Bailey & Lopez de Prado, 2014) requires:
1. **N** (number of strategies/trials tested) to compute SR* via extreme value theory: `SR* ≈ (1 - γ) * Φ⁻¹(1 - 1/N) + γ * Φ⁻¹(1 - 1/(N·e))`
2. **Skewness (γ₃) and kurtosis (γ₄)** for non-normality correction in the denominator
3. **T** (number of observations) in the PSR formula: `PSR(SR*) = Φ( (SR - SR*) * sqrt(T-1) / sqrt(1 - γ₃·SR + (γ₄-1)/4 · SR²) )`

The Grok formula has none of these. It ignores multiple-testing correction entirely, which is the entire point of DSR vs plain SR.

---

### Grok Suggestion 2: PBO Formula

```python
pbo = 1 - (np.sum(returns > 0) / n) ** 2
```

**VERDICT: FLAWED — no theoretical basis**

This reduces to `pbo = 1 - WR²`. At WR=50%, pbo=0.75 (implies 75% overfit risk — arbitrary). At WR=70%, pbo=0.51 (almost no improvement despite high WR). The formula has no connection to Lopez de Prado's PBO framework.

The correct PBO (Bailey et al. 2014/2016, CPCV) is:
- Split the T-bar time series into S sub-periods using combinatorial cross-validation
- For each of C(S, S/2) train/test combinations, find the IS-optimal strategy
- PBO = fraction of combinations where the IS-optimal strategy ranks below median in OOS
- `PBO = λ̄ / N̄` where λ̄ = fraction of IS/OOS pairs where OOS winner ≠ IS winner

Real PBO requires rank comparison across combinatorial IS/OOS splits — not a WR polynomial.

---

### Grok Suggestion 3: Hybrid Score with `forward_wr_30`

```python
final_score = (0.55 * ml_score) + (0.25 * regime_factor) + (0.15 * freshness) + (0.05 * forward_wr_30)
```

**VERDICT: FLAWED — critical lookahead bias**

`forward_wr_30` is computed from trades that occur 30 days AFTER the signal. Using it in a live scoring function — even at 5% weight — constitutes pure lookahead. A model trained with this feature would appear highly predictive in backtests because it literally uses future WR data as an input. The contamination invalidates all backtest results. Even at 5% weight, the model learns to exploit this future signal and will suppress all other feature coefficients.

**Fix:** Replace `forward_wr_30` with `rolling_wr_30` (trailing 30-day WR, computed entirely from past data), shifted by at least 1 bar.

---

### Grok Suggestion 4: `equity_momentum_regime_signal()`

```python
regime = 1 if vol < df['close'].pct_change(252).std() * 0.8 else 0
```

**VERDICT: FLAWED — lookahead in global std()**

`df['close'].pct_change(252).std()` computes a single global standard deviation across the entire DataFrame. At time t, this includes prices from t+1 to end-of-data. Every historical bar's regime classification uses future data.

**Correct fix:**
```python
annual_vol_rolling = df['close'].pct_change().rolling(252).std() * np.sqrt(252)
current_vol = df['close'].pct_change().rolling(21).std() * np.sqrt(252)
regime = (current_vol < annual_vol_rolling.shift(1) * 0.8).astype(int)
```
The `.shift(1)` ensures at time t only data through t-1 is used in the benchmark.

---

## PART 2: SWARM CONSENSUS — COMBINED 4-QUESTION PROMPT

### Q1: Lookahead Bias Patterns (Consensus across deepseek + openrouter)

Three patterns with strong consensus:

| Pattern | Code Smell | Why It Leaks | Severity |
|---------|-----------|--------------|----------|
| Global scaler fit on full dataset | `StandardScaler().fit(all_scores)` | Mean/std from future data shift current scores | HIGH |
| Min-max normalization using global extremes | `(score - min(all)) / (max(all) - min(all))` | Future extreme values compress current range | HIGH |
| Rolling features computed before train/test split | `price.rolling(14).std()` on full DataFrame | Rolling windows at bar t include bars t+1..t+13 | HIGH |

All three are instances of the same class: a statistic computed on the full dataset is used to transform data at time t, so t has access to information from t+1..T.

---

### Q2: Confidence Score Inversion Root Causes

**Consensus ranking from deepseek + openrouter:**

1. **(a) Label leakage** — MOST LIKELY. Inverted correlation is the textbook diagnostic for this. When ml_score is high, the model is identifying noise artifacts that reverse out-of-sample. If future price data leaked into training features, the model learns to predict the noise component, which mean-reverts.

2. **(b) Overfit on in-sample period** — Likely secondary cause. Model memorized noise patterns anti-correlated with forward returns in the test period. With n=426 for EQUITY, dataset is small enough for this to matter.

3. **(c) Regime change** — Possible. Deepseek notes: "if 14/14 hypotheses fail, regime change would typically affect some hypotheses differently" — arguing against this being primary.

4. **(d) Wrong loss function** — Least likely. Would produce flat predictions, not inverted correlation.

**Key diagnostic:** Pull a sample of high-ml_score picks and check whether any feature value was computed using data from after the pick's signal time. If yes, it's (a). Run a simple linear regression of ml_score on forward_return in expanding window — if the negative correlation appeared only after a specific date, it's (c).

---

### Q3: Correct DSR and PBO Formulas

**Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014):**

```
SR* = Φ⁻¹(1 - 1/N) * sqrt( (1 - γ₃·SR_b + (γ₄-1)/4 · SR_b²) / (T-1) )

DSR = Φ( (SR̂ - SR*) * sqrt(T-1) / sqrt(1 - γ₃·SR̂ + (γ₄-1)/4 · SR̂²) )
```

Where:
- N = number of strategies/trials tested
- T = number of observations
- γ₃ = skewness of strategy returns
- γ₄ = excess kurtosis of strategy returns  
- SR_b = benchmark Sharpe (typically 0)
- Φ = standard normal CDF

**Probability of Backtest Overfitting (Bailey et al. 2016 CPCV):**

```
PBO = fraction of C(S, S/2) combinatorial IS/OOS splits where
      the IS-optimal strategy ranks ≤ median in OOS performance
```

Both Grok's simplified formulas are **mathematically incorrect** — the DSR formula is missing N, γ₃, γ₄ and T; the PBO formula `1-WR²` has no theoretical derivation.

---

### Q4: Highest-Conviction Action Given 0/14 Passing

**Deepseek recommendation: (d) Ensemble of weak signals**

Statistical argument: If each hypothesis has true efficiency μᵢ ≈ 0.05 (below the 0.30 gate), individual signal variance σ ≈ 0.5 means P(passing gate) ≈ 0. But an equal-weighted ensemble of 14 hypotheses reduces variance by √14, so σ_ensemble ≈ 0.134. The ensemble expected efficiency stays ≈ 0.05 but the noise suppression is dramatic — the gate has a real chance of passing if real edge exists.

**Openrouter recommendation: (a) Better data/intraday**

Argument: Daily data has ~78x fewer observations than 5-min bars. At daily resolution, 14-day windows contain only 14 observations — not enough statistical power. Switching to intraday data gives ~1,092 observations per 14-day window, making the gate test meaningful.

**Synthesis:** The two are complementary, not competing. The ensemble approach (d) reduces noise from the signal side; better data (a) reduces noise from the test side. Recommended order: first try ensemble on existing daily signals (zero cost), then upgrade to intraday data if ensemble still fails.

---

## PART 3: INDIVIDUAL PROMPT RESULTS

### P1 (Lookahead Audit) — deepseek
Three patterns identified: global scaler lookahead, global min-max lookahead, rolling feature computed before split. All HIGH severity. Consensus with combined prompt.

### P2 (Strategy Regeneration) — deepseek
Deepseek identified three structural failure modes for sign-flip pattern:
1. **Non-stationary regime-dependent factor loading** — same hypothesis correct in opposite directions depending on latent regime. Fix: condition on regime indicator.
2. **Data snooping bias from multiple comparisons** — 14 hypotheses selected from larger pool, selection bias causes them to fail OOS. Fix: apply Bonferroni/BH correction before hypothesis generation.
3. **Microstructure noise at low resolution** — signal operates intraday, daily aggregation destroys it. Fix: switch to 5-min bars.

### P3 (Confidence Fix) — openrouter
Rankings: (1) label leakage, (2) overfit, (3) regime change, (4) wrong loss. Full mechanistic explanations and diagnostic tests for each.

### P4 (GHA Gates) — deepseek
Three concrete GHA steps designed:
1. `detect-lookahead-bias-regression` — checks if first OOS window is >20% better than later windows (classic lookahead signature)
2. `check-confidence-score-inversion` — Spearman correlation of ml_score vs forward_wr per hypothesis, fail if < -0.3 (p<0.05)
3. `validate-walk-forward-gate-integrity` — detects >5% weakening of any gate threshold vs main branch baseline

Full YAML workflow skeleton included in raw output at `swarm_runs/audit_20260519_p4/deepseek.json.raw.txt`.

---

## SUMMARY TABLE

| Topic | Verdict | Key Finding |
|-------|---------|------------|
| Grok DSR formula | OVERSIMPLIFIED | Missing N (trials), skewness/kurtosis, T scaling |
| Grok PBO formula | FLAWED | `1-WR²` has no theoretical basis; real PBO needs CPCV |
| Grok hybrid score with forward_wr_30 | FLAWED (LOOKAHEAD) | forward_wr_30 is future data — invalidates all backtests |
| Grok regime signal global std() | FLAWED (LOOKAHEAD) | .std() on full column includes future bars; use rolling |
| Confidence inversion root cause | Label leakage #1 | Overfit #2, regime change #3, wrong loss #4 |
| Best action for 0/14 gate passes | Ensemble + intraday | Reduce signal noise (ensemble), then test power (intraday) |
