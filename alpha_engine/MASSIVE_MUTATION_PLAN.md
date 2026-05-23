# Massive Mutation Plan: Scaling to 1M+ Strategy Backtests

**Date:** 2026-03-15
**Context:** genome_evolution_v2.py runs 60 genomes x 100 generations = 6,000 backtests.
We want 1,000,000+ while AVOIDING the G51883 overfitting disaster (98.6% IS -> 96% OOS collapse).

---

## 1. Scaling to Millions of Mutations

### Current Bottleneck Analysis

v2 runs ~6,000 backtests across 4 symbols with 1000 candles each. Each backtest is pure Python with O(n) loops over candles. Profiling breakdown:

| Component | Time per eval | Notes |
|---|---|---|
| `backtest_genome()` per symbol | ~5ms | Python for-loop over 1000 candles |
| Walk-forward (5 folds x 4 symbols) | ~100ms | 20 backtest calls |
| Noise robustness (3 seeds x 4 symbols) | ~60ms | 12 more backtest calls |
| **Total per genome** | **~160ms** | 32 backtest calls |
| **6,000 genomes** | **~16 min** | Current v2 runtime |
| **1,000,000 genomes at 160ms** | **~44 hours** | Not feasible |

**Target: 1M evaluations in <6 hours (GitHub Actions limit)**
Required: ~5ms per genome evaluation = **32x speedup**

### 1A. Vectorized Backtesting (numpy — 50-100x speedup)

Replace the Python for-loop backtest with numpy array operations. The core Keltner compression strategy is entirely vectorizable.

```python
import numpy as np

def backtest_genome_vectorized(closes, highs, lows, volumes, genes):
    """Vectorized backtest — NO Python loops over candles.

    All 1000 candles processed simultaneously via numpy broadcasting.
    ~0.05ms per symbol vs ~5ms = 100x speedup.
    """
    n = len(closes)

    # ── Indicators (vectorized) ──
    # EMA via scipy or manual cumulative
    ema_vals = ema_numpy(closes, genes["ema_period"])
    atr_vals = atr_numpy(highs, lows, closes, genes["atr_period"])
    hma_vals = hma_numpy(closes, genes["hma_period"])
    vol_sma = sma_numpy(volumes, 20)
    atr_sma = sma_numpy(atr_vals, 30)

    # ── Channel width (vectorized) ──
    widths = genes["channel_mult"] * atr_vals / (ema_vals + 1e-12)

    # ── Rolling Q25 of widths (vectorized with stride_tricks) ──
    comp_window = genes["comp_window"]
    # Use pd.Series.rolling().quantile() or custom rolling_quantile
    q25 = rolling_quantile_numpy(widths, comp_window, 0.25)
    compressed = widths < q25  # boolean array

    # ── ATR ratio gate ──
    atr_ratio = atr_vals / (atr_sma + 1e-12)
    not_extreme = atr_ratio <= genes["vol_gate_extreme"]
    half_size = atr_ratio > genes["vol_gate_high"]

    # ── Channel breakout ──
    upper = ema_vals + genes["channel_mult"] * atr_vals
    lower = ema_vals - genes["channel_mult"] * atr_vals

    # ── HMA trend ──
    hma_slope = np.diff(hma_vals, prepend=hma_vals[0]) / (closes + 1e-12)
    trend_min = genes["trend_strength_min"]
    hma_rising = hma_slope > trend_min
    hma_falling = hma_slope < -trend_min

    # ── Volume confirmation ──
    vol_ratio = volumes / (vol_sma + 1e-12)
    vol_ok = vol_ratio >= genes["volume_confirm"]

    # ── Signal mask (boolean arrays — no loops!) ──
    long_signal = compressed & not_extreme & (closes > upper) & hma_rising & vol_ok
    short_signal = compressed & not_extreme & (closes < lower) & hma_falling & vol_ok

    # ── Cooldown filter (vectorized) ──
    # Apply reentry_cooldown by masking signals too close together
    long_signal = apply_cooldown_mask(long_signal, genes["reentry_cooldown"])
    short_signal = apply_cooldown_mask(short_signal, genes["reentry_cooldown"])

    # ── Simulate trades (the only part that needs a small loop) ──
    # But signals are sparse (typically 10-50 per 1000 bars)
    # so this loop is over ~30 entries, not 1000
    signal_indices = np.where(long_signal | short_signal)[0]

    trades = []
    for idx in signal_indices:
        direction = "LONG" if long_signal[idx] else "SHORT"
        entry = closes[idx]
        a = atr_vals[idx]
        tp_dist = genes["tp_atr_mult"] * a
        sl_dist = genes["sl_atr_mult"] * a
        max_hold = genes["max_hold"]

        # Vectorized exit scan over max_hold bars
        future_highs = highs[idx+1 : idx+1+max_hold]
        future_lows = lows[idx+1 : idx+1+max_hold]

        if direction == "LONG":
            tp_hit = np.where(future_highs >= entry + tp_dist)[0]
            sl_hit = np.where(future_lows <= entry - sl_dist)[0]
        else:
            tp_hit = np.where(future_lows <= entry - tp_dist)[0]
            sl_hit = np.where(future_highs >= entry + sl_dist)[0]

        # First exit wins
        tp_bar = tp_hit[0] if len(tp_hit) > 0 else 9999
        sl_bar = sl_hit[0] if len(sl_hit) > 0 else 9999

        if tp_bar <= sl_bar and tp_bar < 9999:
            pnl = tp_dist / entry * 100
        elif sl_bar < 9999:
            pnl = -sl_dist / entry * 100
        else:
            exit_px = closes[min(idx + max_hold, n - 1)]
            pnl = (exit_px - entry) / entry * 100 * (1 if direction == "LONG" else -1)

        scale = 0.5 if half_size[idx] else 1.0
        trades.append(pnl * scale)

    return np.array(trades)


def ema_numpy(values, period):
    """Exponential moving average using numpy cumulative operations."""
    alpha = 2.0 / (period + 1)
    result = np.empty_like(values)
    result[0] = values[0]
    for i in range(1, len(values)):  # This loop is unavoidable for EMA
        result[i] = alpha * values[i] + (1 - alpha) * result[i-1]
    return result
    # NOTE: For ultimate speed, use numba @jit on this function


def apply_cooldown_mask(signals, cooldown):
    """Zero out signals that fire within cooldown bars of a previous signal."""
    if cooldown <= 0:
        return signals
    result = signals.copy()
    last_signal = -9999
    for i in range(len(result)):
        if result[i]:
            if i - last_signal < cooldown:
                result[i] = False
            else:
                last_signal = i
    return result
```

**Expected speedup:** 50-100x for the indicator calculation portion. The trade simulation loop runs over ~30 sparse signal points, not 1000 candles, so it's already fast.

### 1B. Multi-Fidelity Funnel (1M -> 1K -> 50)

The key insight: **most genomes are garbage**. Don't waste full walk-forward + noise evaluation on them.

```
TIER 1 (cheap screen):     1,000,000 genomes  x  0.5ms each  =   8 min
  - 100-candle backtest, single symbol (BTCUSDT), no walk-forward
  - Kill if: <3 trades, WR <40%, PF <0.8, or net PnL negative
  - Pass rate: ~5% = 50,000 survivors

TIER 2 (medium screen):       50,000 genomes  x  10ms each  =   8 min
  - 500-candle backtest, 2 symbols (BTC + SOL), simple 2-fold walk-forward
  - Kill if: OOS WR <45%, OOS PF <1.0, <10 OOS trades
  - Pass rate: ~2% = 1,000 survivors

TIER 3 (full evaluation):      1,000 genomes  x  160ms each =   3 min
  - Full v2 pipeline: 1000 candles, 4 symbols, 5-fold WF, 3x noise
  - Deflated Sharpe Ratio correction applied
  - Cross-symbol validation (must be profitable on 3+ symbols)
  - Pass rate: ~5% = 50 survivors

TIER 4 (deep validation):         50 genomes  x  2s each    =   2 min
  - 2000-candle backtest (84 days), 6 symbols, 8-fold WF
  - Bootstrap confidence intervals (1000 resamples)
  - Regime-specific testing (trending, ranging, crash)
  - Final output: top 20 genomes for forward testing
```

```python
def multi_fidelity_evolve(total_mutations=1_000_000):
    """Three-tier funnel: cheap screen -> medium -> full validation."""

    # Prefetch data at all resolutions
    btc_100 = fetch_candles("BTCUSDT", "1h", 100)
    btc_500 = fetch_candles("BTCUSDT", "1h", 500)
    sol_500 = fetch_candles("SOLUSDT", "1h", 500)
    full_data = {sym: fetch_candles(sym, "1h", 1000) for sym in SYMBOLS}
    deep_data = {sym: fetch_candles(sym, "1h", 2000) for sym in SYMBOLS + ["ETHUSDT", "XRPUSDT"]}

    # Convert to numpy arrays once
    btc_100_np = candles_to_numpy(btc_100)

    # ── TIER 1: Cheap screen ──
    log.info(f"TIER 1: Screening {total_mutations:,} genomes on 100 BTC candles...")
    tier1_survivors = []

    for batch_start in range(0, total_mutations, 10000):
        batch = [random_genome() for _ in range(10000)]
        for g in batch:
            trades = backtest_genome_vectorized(*btc_100_np, g.genes)
            if len(trades) >= 3 and np.mean(trades > 0) >= 0.40 and np.sum(trades) > 0:
                g.fitness = np.sum(trades)  # Rough fitness
                tier1_survivors.append(g)

    log.info(f"  TIER 1: {len(tier1_survivors):,} / {total_mutations:,} passed")

    # ── TIER 2: Medium screen ──
    tier1_survivors.sort(key=lambda g: g.fitness, reverse=True)
    tier2_candidates = tier1_survivors[:50000]  # Cap at 50K

    tier2_survivors = []
    for g in tier2_candidates:
        # 2-fold walk-forward on BTC+SOL at 500 candles
        oos_pnl = simple_2fold_eval(btc_500, sol_500, g.genes)
        if oos_pnl > 0:
            g.fitness = oos_pnl
            tier2_survivors.append(g)

    log.info(f"  TIER 2: {len(tier2_survivors):,} / {len(tier2_candidates):,} passed")

    # ── TIER 3: Full v2 evaluation ──
    tier2_survivors.sort(key=lambda g: g.fitness, reverse=True)
    tier3_candidates = tier2_survivors[:1000]

    for g in tier3_candidates:
        calculate_fitness_v2(g, full_data, all_folds)

    tier3_survivors = [g for g in tier3_candidates if g.fitness > 0.5]
    tier3_survivors.sort(key=lambda g: g.fitness, reverse=True)
    tier3_survivors = tier3_survivors[:50]

    log.info(f"  TIER 3: {len(tier3_survivors)} / {len(tier3_candidates)} passed")

    return tier3_survivors
```

### 1C. Surrogate Model (predict fitness without backtest)

After evaluating ~10,000 genomes, train a Random Forest to predict fitness from gene values. Use it to pre-filter the remaining 990,000 genomes.

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor

class SurrogateModel:
    """kNN/RF model that predicts genome fitness without running a backtest.

    After 10K real evaluations, the surrogate can predict which genomes
    are worth the full evaluation with ~70% accuracy.
    """

    def __init__(self, model_type="rf"):
        self.X_train = []  # gene vectors
        self.y_train = []  # fitness values
        self.model = None
        self.model_type = model_type
        self.is_fitted = False
        self.min_samples = 5000  # Don't fit until we have enough data

    def add_observation(self, genes: dict, fitness: float):
        """Record a real evaluation result."""
        vec = [genes[k] for k in sorted(GENE_RANGES.keys())]
        self.X_train.append(vec)
        self.y_train.append(fitness)

    def fit(self):
        """Train the surrogate model."""
        if len(self.X_train) < self.min_samples:
            return

        X = np.array(self.X_train)
        y = np.array(self.y_train)

        if self.model_type == "rf":
            self.model = RandomForestRegressor(
                n_estimators=100, max_depth=8,
                min_samples_leaf=20, n_jobs=-1
            )
        else:
            self.model = KNeighborsRegressor(n_neighbors=10, weights="distance")

        self.model.fit(X, y)
        self.is_fitted = True

    def predict(self, genes: dict) -> float:
        """Predict fitness without running backtest."""
        if not self.is_fitted:
            return None
        vec = np.array([[genes[k] for k in sorted(GENE_RANGES.keys())]])
        return float(self.model.predict(vec)[0])

    def should_evaluate(self, genes: dict, threshold_percentile=70) -> bool:
        """Should this genome get a real evaluation?

        Only run the expensive backtest if surrogate predicts
        fitness above the 70th percentile of observed fitnesses.
        """
        predicted = self.predict(genes)
        if predicted is None:
            return True  # No model yet, evaluate everything

        cutoff = np.percentile(self.y_train, threshold_percentile)
        return predicted >= cutoff
```

**Usage in the evolution loop:**

```python
surrogate = SurrogateModel()

for gen in range(NUM_GENERATIONS):
    for genome in new_population:
        # After 10K evals, use surrogate to skip hopeless genomes
        if surrogate.is_fitted and not surrogate.should_evaluate(genome.genes):
            genome.fitness = 0.0  # Skip — surrogate says it's bad
            continue

        # Full evaluation
        fitness = calculate_fitness_v2(genome, all_candles, all_folds)
        surrogate.add_observation(genome.genes, fitness)

    # Retrain surrogate every 20 generations
    if gen % 20 == 0:
        surrogate.fit()
```

### 1D. Parallel Processing

```python
from multiprocessing import Pool
from functools import partial

def evaluate_genome_worker(genes_dict, candles_dict, folds_dict):
    """Worker function for multiprocessing pool."""
    genome = Genome(genes=genes_dict)
    calculate_fitness_v2(genome, candles_dict, folds_dict)
    return genome.fitness, genome.details

def parallel_evaluate(population, all_candles, all_folds, n_workers=8):
    """Evaluate all genomes in parallel using multiprocessing."""
    worker = partial(evaluate_genome_worker,
                     candles_dict=all_candles, folds_dict=all_folds)

    with Pool(n_workers) as pool:
        results = pool.map(worker, [g.genes for g in population])

    for genome, (fitness, details) in zip(population, results):
        genome.fitness = fitness
        genome.details = details
```

**GitHub Actions runners:** 4 vCPUs available on standard runners. Use `n_workers=4`. This alone gives ~3.5x speedup (not full 4x due to overhead).

**Combined speedup estimate:**

| Technique | Speedup | Cumulative |
|---|---|---|
| Vectorized numpy backtest | 50x | 50x |
| Multi-fidelity funnel (skip 99% of full evals) | 20x | 1000x |
| Surrogate pre-filter | 3x | 3000x |
| Multiprocessing (4 cores) | 3.5x | 10,500x |
| **Total** | **~10,000x** | 1M evals in ~16 min |

---

## 2. Anti-Overfit Techniques That Scale

### 2A. Walk-Forward Anchored Validation (ALREADY IN v2)

Current: 5-fold anchored walk-forward on 1000 candles.
**Upgrade for 1M scale:** Use 8 folds on 2000 candles for tier-3/4 validation.

### 2B. Noise Injection (ALREADY IN v2)

Current: 0.1% OHLCV noise, 3 seeds, take worst score.
**Upgrade:** At tier 4, use 10 noise seeds with 0.2% noise. If worst-case Sharpe drops >50% from median, the genome is fragile.

### 2C. Deflated Sharpe Ratio (Lopez de Prado, 2014)

The critical correction when testing millions of strategies. Standard Sharpe has a selection bias: if you test 1M strategies, the best one's Sharpe is inflated by sqrt(2 * ln(N)).

```python
import math
from scipy import stats

def deflated_sharpe_ratio(observed_sharpe, num_trials, avg_sharpe_all,
                          std_sharpe_all, num_trades, skewness=0, kurtosis=3):
    """Lopez de Prado's Deflated Sharpe Ratio (2014).

    Corrects for multiple testing: if you test 1M strategies,
    the best Sharpe is expected to be ~5.3 even with no real edge.

    Args:
        observed_sharpe: Sharpe of the strategy being tested
        num_trials: Total number of strategies tested (e.g., 1,000,000)
        avg_sharpe_all: Mean Sharpe across ALL tested strategies
        std_sharpe_all: Std dev of Sharpe across ALL tested strategies
        num_trades: Number of trades in the observed strategy
        skewness: Skewness of the strategy's returns
        kurtosis: Kurtosis of the strategy's returns (3 = normal)

    Returns:
        p-value: probability that observed Sharpe is due to chance.
        A genome is REAL if p < 0.05.
    """
    # Expected maximum Sharpe under null (Euler-Mascheroni approximation)
    euler_mascheroni = 0.5772
    e_max_sharpe = avg_sharpe_all + std_sharpe_all * (
        (1 - euler_mascheroni) * stats.norm.ppf(1 - 1/num_trials)
        + euler_mascheroni * stats.norm.ppf(1 - 1/(num_trials * math.e))
    )

    # Standard error of the observed Sharpe (corrected for non-normality)
    se_sharpe = math.sqrt(
        (1 + 0.5 * observed_sharpe**2 - skewness * observed_sharpe
         + ((kurtosis - 3) / 4) * observed_sharpe**2) / (num_trades - 1)
    )

    if se_sharpe < 1e-12:
        return 1.0

    # Test statistic: is observed Sharpe above the expected maximum?
    z = (observed_sharpe - e_max_sharpe) / se_sharpe

    # One-tailed p-value
    p_value = 1 - stats.norm.cdf(z)

    return p_value


# Usage in tier 3/4 validation:
def validate_with_dsr(survivors, total_tested):
    """Apply Deflated Sharpe Ratio to final survivors."""
    all_sharpes = [g.details.get("wf_sharpe", 0) for g in survivors]
    avg_sharpe = np.mean(all_sharpes)
    std_sharpe = np.std(all_sharpes) if len(all_sharpes) > 1 else 1.0

    validated = []
    for g in survivors:
        obs_sharpe = g.details.get("wf_sharpe", 0)
        n_trades = g.details.get("total_oos_trades", 0)

        p = deflated_sharpe_ratio(
            observed_sharpe=obs_sharpe,
            num_trials=total_tested,  # 1,000,000
            avg_sharpe_all=avg_sharpe,
            std_sharpe_all=std_sharpe,
            num_trades=n_trades,
        )

        g.details["dsr_p_value"] = round(p, 6)

        if p < 0.05:  # Statistically significant after multiple-testing correction
            validated.append(g)
            log.info(f"  DSR PASS: {g.genome_id} sharpe={obs_sharpe:.3f} p={p:.4f}")
        else:
            log.info(f"  DSR FAIL: {g.genome_id} sharpe={obs_sharpe:.3f} p={p:.4f}")

    return validated
```

**Why this matters:** Testing 1M strategies, you EXPECT the best Sharpe to be ~5.3 purely by chance (with normally distributed returns). DSR tells you whether a genome's Sharpe is genuinely above what luck would produce.

### 2D. Minimum Trade Count Gates (ALREADY IN v2)

Current: 30 trades across all folds.
**Upgrade by tier:**

| Tier | Min trades | Rationale |
|---|---|---|
| Tier 1 (100 candles) | 3 | Just not zero |
| Tier 2 (500 candles) | 10 | Basic statistical signal |
| Tier 3 (1000 candles) | 30 | Current v2 gate |
| Tier 4 (2000 candles) | 60 | p < 0.05 with 55% WR requires ~60 trades |

The math: to distinguish 55% WR from 50% coin-flip with p < 0.05, you need N >= (1.645 / (0.55 - 0.50))^2 * 0.5 * 0.5 = 271 trades. For 60% WR, N >= 68. Our 60-trade gate at tier 4 catches genuine 60%+ WR strategies.

### 2E. Cross-Symbol Validation

```python
def cross_symbol_gate(genome, all_candles, all_folds, min_symbols=3):
    """Genome must be profitable OOS on at least min_symbols different assets.

    This kills curve-fitted strategies that only work on one symbol.
    v2 already tracks symbols_profitable — we just make it a hard gate.
    """
    profitable_symbols = 0
    symbol_results = {}

    for symbol in SYMBOLS:
        if symbol not in all_folds:
            continue
        wf = walk_forward_evaluate(all_folds[symbol], genome.genes)
        symbol_results[symbol] = wf["total_oos_pnl"]
        if wf["total_oos_pnl"] > 0 and wf["total_oos_trades"] >= 5:
            profitable_symbols += 1

    passed = profitable_symbols >= min_symbols

    if not passed:
        log.info(f"  Cross-symbol FAIL: {genome.genome_id} "
                 f"profitable on {profitable_symbols}/{len(SYMBOLS)} "
                 f"(need {min_symbols})")

    return passed, symbol_results
```

**Symbols for cross-validation (6 minimum):**
- BTC-USD (king, low vol)
- ETH-USD (correlated but distinct microstructure)
- SOL-USD (high beta, narrative-driven)
- BNB-USD (exchange token, different driver)
- DOGE-USD (meme, high noise)
- XRP-USD (legal catalyst, different regime)

A strategy that works on BTC + SOL + DOGE is genuinely capturing market structure, not a BTC-specific artifact.

### 2F. Bootstrap Confidence Intervals (Tier 4 only)

```python
def bootstrap_confidence(trades_pnl, n_resamples=1000, ci=0.95):
    """Bootstrap confidence interval for mean trade PnL.

    If the lower bound of the 95% CI is still positive,
    the strategy has a real edge with 95% confidence.
    """
    trades = np.array(trades_pnl)
    n = len(trades)

    if n < 10:
        return 0.0, 0.0, False

    boot_means = np.zeros(n_resamples)
    for i in range(n_resamples):
        sample = np.random.choice(trades, size=n, replace=True)
        boot_means[i] = np.mean(sample)

    boot_means.sort()
    lower_idx = int((1 - ci) / 2 * n_resamples)
    upper_idx = int((1 + ci) / 2 * n_resamples)

    lower = boot_means[lower_idx]
    upper = boot_means[upper_idx]

    return lower, upper, lower > 0  # True = edge survives bootstrap
```

### 2G. Parameter Regularization (ALREADY IN v2 — upgrade)

Current: L2 penalty from defaults.
**Upgrade: Bayesian-style prior favoring parameter ranges that have worked before.**

```python
def adaptive_regularization(genes, historical_winners):
    """Regularize toward the centroid of historically successful genomes,
    not just the defaults.

    After 10 generations, we know which parameter regions work.
    Penalize genomes far from the 'winning zone' more than those near it.
    """
    if len(historical_winners) < 20:
        # Fall back to default L2 penalty until we have data
        return calc_regularization_penalty(genes)

    # Compute centroid and std of winning gene values
    penalty = 0.0
    for name in GENE_RANGES:
        winner_vals = [w.genes[name] for w in historical_winners]
        centroid = np.mean(winner_vals)
        spread = max(np.std(winner_vals), 1e-6)

        # Gaussian penalty: more penalty for being far from winning zone
        dist = abs(genes[name] - centroid) / spread
        penalty += min(dist ** 2, 4.0)  # Cap at 4 to avoid killing exploration

    return penalty / len(GENE_RANGES)
```

---

## 3. Mutation Operators for Diversity

### 3A. Differential Evolution (DE/best/1/bin)

The most effective mutation operator for continuous optimization. Much better than Gaussian perturbation for escaping local optima.

```python
def differential_mutation(population, best_genome, F=0.8, CR=0.9, generation=0):
    """DE/best/1/bin: child = best + F * (rand1 - rand2)

    F = 0.8: differential weight (how far to push)
    CR = 0.9: crossover rate (how many genes to take from donor)

    This is the workhorse of professional quant optimization.
    Better than Gaussian mutation because the step size adapts
    to the actual spread of the population.
    """
    children = []
    gene_names = list(GENE_RANGES.keys())

    for target in population:
        # Pick two random genomes (not the target)
        r1, r2 = random.sample([g for g in population if g != target], 2)

        # Donor vector: best + F * (r1 - r2)
        donor_genes = {}
        for name in gene_names:
            lo, hi, dtype = GENE_RANGES[name]
            donor_val = best_genome.genes[name] + F * (r1.genes[name] - r2.genes[name])
            # Clip to valid range
            if dtype == "int":
                donor_genes[name] = max(int(lo), min(int(hi), int(round(donor_val))))
            else:
                donor_genes[name] = max(lo, min(hi, round(donor_val, 4)))

        # Binomial crossover: mix donor with target
        child_genes = {}
        j_rand = random.randint(0, len(gene_names) - 1)  # Ensure at least 1 gene from donor
        for j, name in enumerate(gene_names):
            if random.random() < CR or j == j_rand:
                child_genes[name] = donor_genes[name]
            else:
                child_genes[name] = target.genes[name]

        children.append(Genome(genes=child_genes, generation=generation))

    return children
```

### 3B. CMA-ES (Covariance Matrix Adaptation)

Learns the shape of the fitness landscape. If `ema_period` and `hma_period` are correlated in good solutions, CMA-ES will mutate them together.

```python
class SimpleCMAES:
    """Simplified CMA-ES for genome evolution.

    Learns which gene combinations produce good results and
    generates mutations along the discovered correlations.

    Full CMA-ES is complex; this captures the key insight:
    use the covariance of good genomes to guide search.
    """

    def __init__(self, gene_names, initial_sigma=0.3):
        self.gene_names = gene_names
        self.n = len(gene_names)
        self.mean = np.zeros(self.n)  # Will be set from population
        self.sigma = initial_sigma
        self.C = np.eye(self.n)  # Covariance matrix (starts as identity)
        self.generation = 0

    def update_from_population(self, top_genomes):
        """Update mean and covariance from the top genomes."""
        if len(top_genomes) < 4:
            return

        # Normalize genes to [0, 1] range
        vectors = []
        for g in top_genomes:
            vec = []
            for name in self.gene_names:
                lo, hi, _ = GENE_RANGES[name]
                normalized = (g.genes[name] - lo) / (hi - lo + 1e-12)
                vec.append(normalized)
            vectors.append(vec)

        vectors = np.array(vectors)

        # Update mean (weighted by rank)
        n_top = len(vectors)
        weights = np.log(n_top + 1) - np.log(np.arange(1, n_top + 1))
        weights /= weights.sum()

        self.mean = np.average(vectors, axis=0, weights=weights)

        # Update covariance (rank-mu update, simplified)
        diff = vectors - self.mean
        weighted_diff = diff * weights[:, np.newaxis]
        self.C = 0.8 * self.C + 0.2 * (weighted_diff.T @ diff)

        # Ensure positive definite
        self.C = (self.C + self.C.T) / 2
        eigvals = np.linalg.eigvalsh(self.C)
        if eigvals.min() < 1e-8:
            self.C += np.eye(self.n) * 1e-6

        self.generation += 1

    def sample(self, n_samples=10):
        """Generate new genome candidates from learned distribution."""
        try:
            samples = np.random.multivariate_normal(self.mean, self.sigma**2 * self.C, n_samples)
        except np.linalg.LinAlgError:
            samples = np.random.normal(self.mean, self.sigma, (n_samples, self.n))

        genomes = []
        for s in samples:
            genes = {}
            for j, name in enumerate(self.gene_names):
                lo, hi, dtype = GENE_RANGES[name]
                val = lo + s[j] * (hi - lo)  # Denormalize
                val = max(lo, min(hi, val))
                if dtype == "int":
                    genes[name] = int(round(val))
                else:
                    genes[name] = round(val, 4)
            genomes.append(Genome(genes=genes))

        return genomes
```

### 3C. Novelty Search (reward behavioral diversity)

Stop optimizing ONLY for fitness. Also reward genomes that behave differently from the population. This prevents convergence to a single local optimum.

```python
def novelty_score(genome, population, k=5):
    """Compute behavioral novelty: average distance to k nearest neighbors
    in behavior space (not gene space).

    Behavior = [num_trades, win_rate, avg_hold_time, long_pct, sharpe]

    A genome that makes 50 quick trades is behaviorally different from
    one that makes 10 long-hold trades, even if their fitness is similar.
    """
    def behavior_vector(g):
        d = g.details
        return np.array([
            d.get("total_oos_trades", 0) / 100,  # Normalize
            d.get("oos_wr", 50) / 100,
            d.get("wf_sharpe", 0),
            d.get("noise_score", 0),
            d.get("symbols_profitable", 0) / len(SYMBOLS),
        ])

    target_bv = behavior_vector(genome)
    distances = []

    for other in population:
        if other.genome_id == genome.genome_id:
            continue
        other_bv = behavior_vector(other)
        dist = np.linalg.norm(target_bv - other_bv)
        distances.append(dist)

    if not distances:
        return 0.0

    distances.sort()
    k_nearest = distances[:k]
    return float(np.mean(k_nearest))


def fitness_with_novelty(genome, population, novelty_weight=0.2):
    """Combined fitness = (1 - w) * raw_fitness + w * novelty_score.

    This keeps diversity alive even in late generations.
    The 0.2 weight means novelty matters but doesn't override quality.
    """
    raw = genome.fitness
    novelty = novelty_score(genome, population)
    genome.details["novelty_score"] = round(novelty, 4)
    return (1 - novelty_weight) * raw + novelty_weight * novelty
```

### 3D. Island Model with Migration (ALREADY IN v2 — upgrade)

Current: 4 islands, ring migration every 10 generations.
**Upgrade: heterogeneous islands with different objectives.**

```python
# Island 0: Maximize OOS Sharpe (quality)
# Island 1: Maximize trade count (exploitation frequency)
# Island 2: Maximize novelty (diversity)
# Island 3: Minimize drawdown (risk management)

ISLAND_OBJECTIVES = {
    0: lambda g: g.details.get("wf_sharpe", 0),
    1: lambda g: min(g.details.get("total_oos_trades", 0) / 200, 1.0) * max(0, g.details.get("wf_sharpe", 0)),
    2: lambda g: g.details.get("novelty_score", 0) * max(0.1, g.fitness),
    3: lambda g: g.details.get("noise_score", 0),  # Robustness-focused
}
```

### 3E. Inverse Strategy Detection (ALREADY IN v2 — upgrade)

Current: Swap TP/SL and invert channel_mult for consistent losers.
**Upgrade: full signal inversion + fresh optimization of TP/SL.**

```python
def full_inverse(genome, all_candles, all_folds):
    """True signal inversion: reverse every BUY to SELL and vice versa.

    Instead of hacking gene values, run the same strategy but
    record the OPPOSITE direction. Then re-optimize TP/SL for
    the inverted signals using a small local search.
    """
    inv_genes = copy.deepcopy(genome.genes)

    # Swap trend filter direction
    inv_genes["trend_strength_min"] = -inv_genes["trend_strength_min"]

    # Swap channel breakout direction: invert min_edge sign convention
    # (long when price < lower, short when price > upper)
    inv_genes["channel_mult"] = GENE_RANGES["channel_mult"][1] - inv_genes["channel_mult"] + GENE_RANGES["channel_mult"][0]

    # Local search on TP/SL for inverted signals
    best_inv = None
    best_fitness = -999

    for tp_mult in np.arange(1.0, 4.0, 0.5):
        for sl_mult in np.arange(0.5, 2.5, 0.5):
            trial = copy.deepcopy(inv_genes)
            trial["tp_atr_mult"] = tp_mult
            trial["sl_atr_mult"] = sl_mult

            g = Genome(genes=trial)
            f = calculate_fitness_v2(g, all_candles, all_folds)
            if f > best_fitness:
                best_fitness = f
                best_inv = g

    return best_inv
```

---

## 4. Practical Execution Plan

### Phase 1: Vectorize the Backtest Engine (Week 1)

**Goal:** Replace pure-Python backtest with numpy. 100x speedup on indicator calculation.

**Files to modify:**
- `alpha_engine/genome_evolution_v2.py`: Replace `calc_ema`, `calc_atr`, `calc_hma`, `calc_sma` with numpy versions
- New file: `alpha_engine/vectorized_backtest.py` containing the numpy backtest engine
- Keep the old pure-Python versions as fallback (no numpy dependency in CI? use conditional import)

**Steps:**
1. Create `vectorized_backtest.py` with `backtest_genome_vectorized()`
2. Add `numpy` to requirements (already imported in super_strategies.py)
3. Benchmark: old vs new on 1000 BTC candles, assert identical trade results
4. Replace the inner loop in `calculate_fitness_v2` with vectorized version

**Validation:** Both engines must produce identical trade signals on the same data. Write a test that runs 100 random genomes through both and asserts matching output.

### Phase 2: Multi-Fidelity Funnel (Week 2)

**Goal:** Screen 1M genomes through the 4-tier funnel.

**Files to create:**
- `alpha_engine/massive_mutation_engine.py`: Main orchestrator
- `alpha_engine/surrogate_model.py`: kNN/RF fitness predictor

**Steps:**
1. Implement Tier 1 cheap screen (100 candles, 1 symbol, 0.5ms/genome)
2. Implement Tier 2 medium screen (500 candles, 2 symbols, 2-fold WF)
3. Integrate surrogate model after 10K real evaluations
4. Wire Tier 3 = existing `calculate_fitness_v2`
5. Implement Tier 4 deep validation (2000 candles, 6 symbols, bootstrap)
6. Add Deflated Sharpe Ratio as final gate

**Validation:** Run 100K mutations first. Check that Tier 4 survivors have positive PnL on held-out data not used in any tier.

### Phase 3: GitHub Actions Overnight Job (Week 3)

**Goal:** Run 1M mutations as a scheduled GitHub Actions job (6-hour limit).

**New workflow:** `.github/workflows/massive-mutation.yml`

```yaml
name: Massive Mutation Engine
on:
  schedule:
    - cron: '0 2 * * 0'  # Sunday 2am UTC (overnight)
  workflow_dispatch:
    inputs:
      total_mutations:
        description: 'Number of mutations to test'
        default: '1000000'

jobs:
  evolve:
    runs-on: ubuntu-latest
    timeout-minutes: 350  # 5h50m (under 6h limit)

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install numpy scipy scikit-learn

      - name: Fetch historical data
        run: python alpha_engine/fetch_historical.py --symbols BTC,ETH,SOL,BNB,DOGE,XRP --candles 2000

      - name: Run massive mutation
        run: |
          python alpha_engine/massive_mutation_engine.py \
            --mutations ${{ inputs.total_mutations || '1000000' }} \
            --output alpha_engine/data/massive_mutation_results.json
        timeout-minutes: 340

      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add alpha_engine/data/massive_mutation_results.json
          git commit -m "Massive mutation: top survivors from ${{ inputs.total_mutations || '1M' }} tests" || true
          git push

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: mutation-results
          path: alpha_engine/data/massive_mutation_results.json
```

**Time budget (1M mutations):**

| Phase | Time | Notes |
|---|---|---|
| Fetch 2000 candles x 6 symbols | 5 min | Binance API with rate limiting |
| Tier 1: 1M x 0.5ms | 8 min | Vectorized, single symbol |
| Tier 2: 50K x 10ms | 8 min | 2 symbols, 2-fold WF |
| Tier 3: 1K x 160ms | 3 min | Full v2 pipeline |
| Tier 4: 50 x 2s | 2 min | Deep validation + bootstrap |
| DSR correction | 1 min | Statistical test |
| Surrogate training/prediction | 5 min | Throughout Tier 1-2 |
| **Total** | **~32 min** | Well under 6h limit |

This means we could actually run **10M mutations** in ~5 hours if needed.

### Phase 4: Forward-Test Top 20 Survivors (Ongoing)

The 20 genomes surviving Tier 4 + DSR get added to the live alpha engine for paper trading.

**Integration with existing system:**

```python
# In alpha_engine/live_scanner.py or a new forward_test.py:

def load_evolved_genomes():
    """Load top genomes from massive mutation results."""
    with open("alpha_engine/data/massive_mutation_results.json") as f:
        results = json.load(f)
    return results["tier4_survivors"]

def forward_test_genome(genome_genes, symbol="BTCUSDT"):
    """Generate live signals from an evolved genome.

    This hooks into the existing signal_tracker.py
    to validate TP/SL hits against real Binance prices.
    """
    candles = fetch_latest_candles(symbol, limit=200)
    # Run backtest on recent data to check for current signal
    trades = backtest_genome_vectorized(candles, genome_genes)

    if trades and trades[-1].bar_index >= len(candles) - 3:
        # Recent signal — emit as live pick
        return {
            "strategy": f"evolved_{genome_genes.get('genome_id', 'unknown')}",
            "symbol": symbol,
            "direction": trades[-1].direction,
            # ... standard signal format
        }
    return None
```

**Forward-test rules:**
- Run for minimum 30 days before any capital allocation
- Require 20+ trades with WR > 50% and PF > 1.2 in forward test
- Compare against DSR prediction: if forward Sharpe is within 1 std of backtest Sharpe, genome is validated
- Kill any genome whose forward drawdown exceeds 2x backtest max drawdown

---

## 5. Concrete Parameter Ranges to Explore

### 5A. Original 14 Keltner Genes (from genome_evolution.py)

| Gene | Range | Step | Hot zone (from v2 winners) | Notes |
|---|---|---|---|---|
| ema_period | 10-60 | 1 | 25-35 | EMA center of channel |
| atr_period | 8-40 | 1 | 14-25 | ATR lookback |
| channel_mult | 1.0-3.5 | 0.1 | 1.5-2.2 | Channel width; >2.5 = too few signals |
| comp_window | 30-150 | 5 | 60-100 | Compression lookback |
| tp_atr_mult | 0.5-4.0 | 0.1 | **1.5-3.0** | v1 bug: 0.5 = scalper death. Floor at 1.0 |
| sl_atr_mult | 0.3-2.5 | 0.1 | **1.0-2.0** | v1 bug: 2.1 = too wide SL. Cap at 2.0 |
| max_hold | 4-24 | 1 | 8-16 | Bars before forced exit |
| hma_period | 10-50 | 1 | 21-43 | Hull MA trend filter |
| min_edge | 0.0-0.5 | 0.05 | 0.0-0.15 | Minimum breakout strength |
| vol_gate_high | 1.5-3.0 | 0.1 | 1.8-2.5 | Half-size threshold |
| vol_gate_extreme | 2.5-5.0 | 0.25 | 3.0-4.0 | Skip threshold |
| trend_strength_min | 0.0-0.01 | 0.001 | 0.0-0.005 | HMA slope floor |
| reentry_cooldown | 0-6 | 1 | 1-3 | Bars between signals |
| volume_confirm | 0.5-3.0 | 0.1 | 0.8-1.5 | Volume ratio gate |

**Safety constraints (hardcoded, not evolvable):**
- `tp_atr_mult >= 1.0` always (prevent the scalper death trap from v1)
- `sl_atr_mult <= 2.0` always (prevent the wide-SL trap)
- `tp_atr_mult / sl_atr_mult >= 1.0` (risk/reward >= 1:1)

### 5B. New Genes from Super Strategies (MUTATION_GENES in super_strategies.py)

These are the evolvable parameters for the 10 super strategies. Each should be added as a separate genome type.

**Strategy Type 1: Trend-Following (super_keltner_ema_momentum)**

| Gene | Range | Step | Notes |
|---|---|---|---|
| ema_fast | 8-12 | 1 | Fast EMA in stack |
| ema_slow | 20-26 | 1 | Slow EMA in stack |
| kc_ema | 18-24 | 1 | Keltner center period |
| kc_atr_mult | 1.0-2.0 | 0.1 | Channel width |
| rsi_ob | 65-80 | 1 | RSI overbought filter |
| tp_atr_mult | 2.0-4.0 | 0.25 | Take profit |
| sl_atr_mult | 1.5-2.5 | 0.25 | Stop loss |

**Strategy Type 2: Mean-Reversion (super_rsi_bollinger_revert)**

| Gene | Range | Step | Notes |
|---|---|---|---|
| rsi_period | 2-7 | 1 | Connors-style short RSI |
| bb_period | 18-25 | 1 | Bollinger period |
| bb_std | 1.8-2.5 | 0.1 | Bollinger width |
| hurst_threshold | 0.40-0.50 | 0.02 | H < 0.5 = mean-reverting |

**Strategy Type 3: On-Chain/Sentiment (super_whale_fear_accumulate)**

| Gene | Range | Step | Notes |
|---|---|---|---|
| fg_threshold | 15-25 | 1 | Fear & Greed extreme |
| whale_vol_mult | 3.0-7.0 | 0.5 | Volume spike detection |
| wyckoff_score_min | 0.45-0.65 | 0.05 | Accumulation phase |

**Strategy Type 4: Inverse (super_inverse_seasonal_obi)**

| Gene | Range | Step | Notes |
|---|---|---|---|
| lookback | 14-30 | 1 | Inverse signal lookback |
| confidence_floor | 0.60-0.75 | 0.05 | Minimum confidence to flip |

### 5C. NEW Genes to Add (not in current codebase)

| Gene | Range | Type | Rationale |
|---|---|---|---|
| timeframe_hours | {1, 2, 4, 8} | discrete | Multi-timeframe optimization |
| entry_type | {0=market, 1=limit_at_ema, 2=limit_at_lower} | discrete | Entry execution |
| trail_stop_pct | 0.0-2.0 | float | Trailing stop (0 = disabled) |
| profit_lock_pct | 0.0-1.5 | float | Lock profits at X ATR in profit |
| partial_exit_pct | 0.0-0.5 | float | Take partial at 1st TP target |
| session_filter | {0=all, 1=asia, 2=london, 3=nyc} | discrete | Session-based filter |
| regime_filter_period | 0-100 | int | 0 = disabled, else use ADX/Hurst for regime |
| max_correlated_positions | 1-5 | int | Portfolio-level risk gene |

These 8 new genes bring total genome size to 22 (Keltner) or 15-22 (super strategies), expanding the search space significantly.

### 5D. Total Search Space Calculation

For the 14 Keltner genes with their step sizes:

```
ema_period: 51 values (10-60)
atr_period: 33 values
channel_mult: 26 values (1.0-3.5 by 0.1)
comp_window: 25 values (30-150 by 5)
tp_atr_mult: 36 values (0.5-4.0 by 0.1)
sl_atr_mult: 23 values (0.3-2.5 by 0.1)
max_hold: 21 values
hma_period: 41 values
min_edge: 11 values (0.0-0.5 by 0.05)
vol_gate_high: 16 values
vol_gate_extreme: 11 values
trend_strength_min: 11 values
reentry_cooldown: 7 values
volume_confirm: 26 values

Total grid: 51 * 33 * 26 * 25 * 36 * 23 * 21 * 41 * 11 * 16 * 11 * 11 * 7 * 26
         ≈ 1.7 × 10^17 combinations
```

Even 1M mutations only explores 0.000000000059% of the space. This is why smart search (DE, CMA-ES, surrogate models) matters more than brute force.

---

## Summary: What to Build

| Priority | Component | Speedup | Effort |
|---|---|---|---|
| 1 | Vectorized backtest (numpy) | 100x | 2 days |
| 2 | Multi-fidelity 4-tier funnel | 20x | 2 days |
| 3 | Differential Evolution mutation | Better convergence | 1 day |
| 4 | Deflated Sharpe Ratio gate | Kills false positives | 0.5 day |
| 5 | Cross-symbol validation (6 symbols) | Anti-overfit | 0.5 day |
| 6 | Surrogate model (RF) | 3x | 1 day |
| 7 | CMA-ES covariance learning | Better mutations | 1 day |
| 8 | GitHub Actions overnight workflow | Automation | 0.5 day |
| 9 | Bootstrap CI (Tier 4) | Statistical rigor | 0.5 day |
| 10 | Novelty search | Diversity | 0.5 day |

**Total estimated effort:** 9.5 dev days to go from 6K backtests to 1M+ with statistical rigor.

**The single most important thing:** Deflated Sharpe Ratio. Without it, the best genome out of 1M trials is almost certainly a false positive. With it, you can trust what survives.
