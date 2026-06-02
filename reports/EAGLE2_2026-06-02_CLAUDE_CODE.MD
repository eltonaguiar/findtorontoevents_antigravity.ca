# EAGLE2 Enhancement Plan — Claude Code
## Date: 2026-06-02

---

## 1. Root Cause Analysis: Why No Profitable Strategies Per Asset Class

### The Core Problem

**Research edge ≠ deployed edge.** The /audit production book is weak because we promote from the wrong evidence, run too many weak emitters, tolerate concentration artifacts, and use inconsistent validation standards.

### Per-Asset-Class Diagnosis

| Class | Live PF | WR | Root Cause | Action |
|-------|---------|-----|------------|--------|
| CRYPTO | 0.98 | 39.7% | Selection/gating mismatch. Edge exists in sub-cohorts (VWAP, Bollinger) but deployed aggregate loses. Smart/HC inflated by mislabeled `claude_gainer_st`. | Promote lab sleeves, depromote aggregate |
| EQUITY | 0.76 | 37.4% | Honest failure. Bad deployed strategies, weak emitter quality. Only `stocks_rsi2_pullback` works (n=70, WR=62.9%). | Stop trading. Rebuild. |
| ETF | 0.34 | — | Best candidate edge (dual momentum), but sample too small (n=13). Backtests orphaned. | Wait for forward n |
| FOREX | 0.27 | 46.1% | Data/resolver + weak edge. High WR + terrible PF = red flag. Mislabels/TIME_EXIT artifacts. | Fix resolver. Don't trade. |
| COMMODITY | 0.475 | 9.1% | Too little clean sample (n=3). CT=F DSR=1.0 was falsified. | Keep collecting |
| BOND | — | 55.6% | Data gap. No meaningful live sample. Backtests PF 1.29-1.62 but orphaned. | Wire FRED API |
| FUTURES | — | — | Concentration/artifact risk. Stats too dependent on narrow sources. | Don't trust yet |

### What We're Doing Wrong

1. **Different standards for research vs production** — lab sleeves look decent, main scanner emits from noisier universe
2. **Too much breadth, not enough promotion discipline** — 100+ strategies, 8 gates, 0 promoted to A-tier
3. **Confusing "interesting cell" with "capital-ready strategy"** — tournament edge ≠ funnel edge ≠ money-ready edge
4. **Concentration masquerading as edge** — one source dominating looks amazing but is fragile
5. **Resolver/label issues polluting trust** — disputed cohorts, mislabeled entries inflating stats

---

## 2. The 10-Step Admissibility Pipeline (Code Snippets)

Every strategy must pass ALL 10 steps before it can affect capital.

### Step 1: Pre-Register Hypothesis

```python
# reports/hypothesis_registry.json
{
    "H-051": {
        "strategy": "VWAPReversion_4h_CRYPTO",
        "registered_utc": "2026-06-02T07:00:00Z",
        "params": {"vwap_period": 50, "band_mult": 1.0, "tp_pct": 0.05, "sl_pct": 0.03},
        "universe": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
        "expected_edge": "VWAP mean reversion — institutional rebalancing creates predictable reversion to VWAP",
        "success_criteria": {"min_oos_pf": 1.05, "min_oos_sharpe": 0.5, "min_trades": 50},
        "status": "PRE_REGISTERED"
    }
}
```

### Step 2: Purged + Embargoed Walk-Forward

```python
def purged_walk_forward(strategy, ohlcv, train_pct=0.7, purge_days=30, embargo_days=10):
    """
    Proper purged walk-forward — NOT the broken version in walk_forward_backtester.py.
    Key differences from current code:
    - Actual IS optimization → locked params → OOS signal generation
    - Purge gap between train/test (prevents autocorrelation leakage)
    - Embargo period after test (prevents look-ahead)
    """
    n = len(ohlcv)
    split = int(n * train_pct)
    
    train_end = split - purge_days  # Purge: remove last 30 days from training
    test_start = split + embargo_days  # Embargo: skip first 10 days of test
    
    train_data = ohlcv.iloc[:train_end]
    test_data = ohlcv.iloc[test_start:]
    
    # Phase 1: Optimize on training data
    best_params = grid_search_optimize(
        strategy, train_data,
        param_ranges=strategy.default_param_ranges(),
        metric='sharpe',  # Optimize for Sharpe, NOT win rate
        min_trades=20
    )
    
    # Phase 2: LOCK parameters, generate signals on test data
    locked_strategy = strategy.clone(best_params)
    oos_equity, oos_trades = locked_strategy.run(test_data, capital=100_000)
    
    # Phase 3: Validate
    return WalkForwardResult(
        is_sharpe=compute_sharpe(train_equity),
        oos_sharpe=compute_sharpe(oos_equity),
        oos_pf=compute_pf(oos_trades),
        oos_wr=compute_wr(oos_trades),
        oos_n_trades=len(oos_trades),
        params=best_params,
        verdict="PASS" if compute_pf(oos_trades) >= 1.05 and len(oos_trades) >= 20 else "FAIL"
    )
```

### Step 3: Apply Costs/Slippage by Asset Class

```python
# Use the EXISTING cost models (they're good, just not wired to backtests)
from alpha_engine.transaction_costs import TransactionCostModel
from alpha_engine.slippage_model import SlippageModel

ASSET_COSTS = {
    'CRYPTO': {'commission_bps': 10, 'slippage_bps': 5, 'market_impact_model': 'crypto'},
    'EQUITY': {'commission_bps': 5, 'slippage_bps': 3, 'market_impact_model': 'equity'},
    'ETF':    {'commission_bps': 3, 'slippage_bps': 2, 'market_impact_model': 'etf'},
    'FOREX':  {'commission_bps': 3, 'slippage_bps': 2, 'market_impact_model': 'forex'},
    'BOND':   {'commission_bps': 2, 'slippage_bps': 1, 'market_impact_model': 'bond'},
}

def apply_costs(trades, asset_class):
    """Apply realistic costs to every trade — the MISSING piece in all 5 backtest modules."""
    costs = ASSET_COSTS[asset_class]
    cost_model = TransactionCostModel(costs['market_impact_model'])
    slippage_model = SlippageModel(costs['market_impact_model'])
    
    costed_trades = []
    for t in trades:
        commission = t['entry_price'] * costs['commission_bps'] / 10000
        slippage = slippage_model.estimate(
            t['entry_price'], t.get('quantity', 1), t.get('hold_bars', 1)
        )
        # Apply to both entry and exit
        total_cost = (commission + slippage) * 2
        t['pnl'] = t['pnl'] - total_cost
        t['pnl_pct'] = t['pnl'] / (t['entry_price'] * t.get('quantity', 1))
        costed_trades.append(t)
    return costed_trades
```

### Step 4: Deflated Sharpe Ratio (DSR)

```python
import numpy as np
from scipy.stats import norm

def deflated_sharpe_ratio(observed_sharpe, n_trials, n_observations, skew=0, kurtosis=3):
    """
    Correct DSR implementation (Lopez de Prado 2014, eq. 7).
    Uses Euler-Mascheroni constant + skew/kurtosis corrections.
    """
    euler_mascheroni = 0.5772
    
    # Expected maximum Sharpe under null (with multiple testing correction)
    e_max_sharpe = (
        (1 - euler_mascheroni) * norm.ppf(1 - 1/n_trials) +
        euler_mascheroni * norm.ppf(1 - 1/(n_trials * np.e))
    )
    
    # Sharpe standard error with skew/kurtosis correction
    sharpe_std = np.sqrt(
        (1 + 0.5 * observed_sharpe**2 - skew * observed_sharpe +
         (kurtosis - 3) / 4 * observed_sharpe**2) / (n_observations - 1)
    )
    
    # DSR = probability that true Sharpe > 0 after correcting for multiple testing
    dsr = norm.cdf((observed_sharpe - e_max_sharpe) / sharpe_std)
    
    return dsr

# Usage: track cumulative strategy count
N_TRIALS_TESTED = 100  # Total strategies ever tested in development
dsr = deflated_sharpe_ratio(
    observed_sharpe=2.5,
    n_trials=N_TRIALS_TESTED,
    n_observations=516,
    skew=-0.3,
    kurtosis=4.2
)
# dsr > 0.95 required for promotion
```

### Step 5: Probability of Backtest Overfitting (PBO)

```python
def probability_of_backtest_overfitting(strategy, ohlcv, n_configs=100):
    """
    Correct PBO implementation (Bailey et al. 2015).
    Uses ACTUAL strategy permutations, NOT random sign flips.
    """
    # Generate strategy matrix: different parameter configurations
    configs = generate_param_grid(strategy, n_configs)
    
    # Run each config on full data
    pnl_matrix = []
    for config in configs:
        s = strategy.clone(config)
        _, trades = s.run(ohlcv, capital=100_000)
        pnl_matrix.append([t['pnl_pct'] for t in trades])
    
    pnl_matrix = np.array(pnl_matrix)
    
    # Split into IS/OOS (combinatorial symmetric cross-entropy)
    n = pnl_matrix.shape[1]
    half = n // 2
    
    is_sharpes = []
    oos_sharpes = []
    for i in range(n_configs):
        is_returns = pnl_matrix[i, :half]
        oos_returns = pnl_matrix[i, half:]
        is_sharpes.append(compute_sharpe(is_returns))
        oos_sharpes.append(compute_sharpe(oos_returns))
    
    # PBO = probability that the IS-best config is NOT the OOS-best
    is_best = np.argmax(is_sharpes)
    oos_rank = np.argsort(oos_sharpes).tolist().index(is_best)
    pbo = oos_rank / n_configs  # Higher rank = worse OOS performance
    
    return pbo  # < 0.5 required for promotion
```

### Step 6: Block Bootstrap (Not i.i.d. Shuffle)

```python
def block_bootstrap(pnl_series, block_size=20, n_iterations=1000, confidence=0.95):
    """
    Block bootstrap preserving autocorrelation structure.
    Current monte_carlo_validator.py uses i.i.d. shuffle — this is WRONG.
    """
    n = len(pnl_series)
    n_blocks = int(np.ceil(n / block_size))
    
    bootstrap_sharpes = []
    bootstrap_pfs = []
    
    for _ in range(n_iterations):
        # Sample blocks with replacement
        block_starts = np.random.randint(0, n - block_size + 1, size=n_blocks)
        resampled = np.concatenate([
            pnl_series[start:start + block_size] for start in block_starts
        ])[:n]  # Trim to original length
        
        bootstrap_sharpes.append(compute_sharpe(resampled))
        bootstrap_pfs.append(compute_pf_from_pnl(resampled))
    
    alpha = 1 - confidence
    ci_sharpe = (
        np.percentile(bootstrap_sharpes, 100 * alpha / 2),
        np.percentile(bootstrap_sharpes, 100 * (1 - alpha / 2))
    )
    ci_pf = (
        np.percentile(bootstrap_pfs, 100 * alpha / 2),
        np.percentile(bootstrap_pfs, 100 * (1 - alpha / 2))
    )
    
    return BootstrapResult(
        sharpe_ci=ci_sharpe,
        pf_ci=ci_pf,
        sharpe_median=np.median(bootstrap_sharpes),
        pf_median=np.median(bootstrap_pfs),
        # FAIL if CI includes zero
        verdict="PASS" if ci_sharpe[0] > 0 else "FAIL"
    )
```

### Step 7: Regime Robustness

```python
def regime_robustness_test(strategy, ohlcv, capital=100_000):
    """
    Test edge across market regimes.
    Strategy must work in ≥3 of 4 regimes.
    """
    regimes = {
        'trending_up': ohlcv[ohlcv['close'].pct_change(20) > 0.05],
        'trending_down': ohlcv[ohlcv['close'].pct_change(20) < -0.05],
        'ranging': ohlcv[(ohlcv['close'].pct_change(20).abs() < 0.05)],
        'volatile': ohlcv[ohlcv['close'].pct_change().rolling(20).std() > 
                          ohlcv['close'].pct_change().std() * 1.5],
    }
    
    results = {}
    for regime_name, regime_data in regimes.items():
        if len(regime_data) < 100:
            continue
        _, trades = strategy.run(regime_data, capital)
        results[regime_name] = {
            'pf': compute_pf(trades),
            'wr': compute_wr(trades),
            'n': len(trades),
            'profitable': compute_pf(trades) >= 1.0
        }
    
    profitable_regimes = sum(1 for r in results.values() if r['profitable'])
    total_regimes = len(results)
    
    return RegimeResult(
        results=results,
        profitable_count=profitable_regimes,
        total_count=total_regimes,
        verdict="PASS" if profitable_regimes >= max(3, total_regimes * 0.75) else "FAIL"
    )
```

### Step 8: Forward Paper Evidence

```python
def forward_paper_validation(strategy_name, min_trades=30, min_pf=1.05, min_wr=0.45):
    """
    Require forward paper evidence before promotion.
    This is the MISSING step — we promote from backtests alone.
    """
    # Query forward test results from database
    forward_picks = query_forward_picks(strategy_name)
    
    if len(forward_picks) < min_trades:
        return ForwardResult(verdict="INSUFFICIENT", n=len(forward_picks), needed=min_trades)
    
    pf = compute_pf(forward_picks)
    wr = compute_wr(forward_picks)
    
    return ForwardResult(
        n=len(forward_picks),
        pf=pf,
        wr=wr,
        verdict="PASS" if pf >= min_pf and wr >= min_wr else "FAIL"
    )
```

### Step 9: Promotion Gate (Forward ≈ OOS)

```python
def promotion_gate(strategy_name, oos_pf, oos_wr, forward_pf, forward_wr):
    """
    Promote only if forward performance stays close to OOS lab performance.
    This prevents the "backtest great, live terrible" problem.
    """
    pf_decay = abs(forward_pf - oos_pf) / oos_pf
    wr_decay = abs(forward_wr - oos_wr) / oos_wr
    
    return PromotionResult(
        oos_pf=oos_pf,
        forward_pf=forward_pf,
        pf_decay=pf_decay,
        oos_wr=oos_wr,
        forward_wr=forward_wr,
        wr_decay=wr_decay,
        verdict="PROMOTE" if pf_decay < 0.20 and wr_decay < 0.15 else "HOLD"
    )
```

### Step 10: Gradual Capital Scaling

```python
def gradual_scale(strategy_name, live_pf, live_n_weeks, live_n_trades):
    """
    Shadow → tiny → small → full sizing.
    Only scale after sustained live proof.
    """
    if live_n_weeks < 2 or live_n_trades < 10:
        return {'allocation_pct': 0.5, 'stage': 'SHADOW'}
    elif live_n_weeks < 4 or live_pf < 1.0:
        return {'allocation_pct': 1.0, 'stage': 'TINY'}
    elif live_n_weeks < 8 or live_pf < 1.1:
        return {'allocation_pct': 5.0, 'stage': 'SMALL'}
    elif live_pf >= 1.1 and live_n_weeks >= 8:
        return {'allocation_pct': 15.0, 'stage': 'FULL'}
    else:
        return {'allocation_pct': 0.5, 'stage': 'SHADOW'}
```

---

## 3. Monitoring Dashboard — Metrics & Thresholds

### Real-Time Metrics (Grafana)

| Metric | Frequency | Source | Alert Threshold | Query |
|--------|-----------|--------|-----------------|-------|
| Live PF (per class) | Daily | `trading_picks` table | < 0.4 for > 5 days | `SELECT asset_class, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as wr FROM trading_picks WHERE status = 'CLOSED' AND closed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY asset_class` |
| WR (per class) | Daily | `trading_picks` table | > 0.7 with PF < 0.4 (suspicious) | Same as above |
| Concentration HHI | Weekly | `trading_picks` table | > 0.25 | `SELECT 1.0 * SUM(cnt*cnt) / (SUM(cnt)*SUM(cnt)) as hhi FROM (SELECT strategy, COUNT(*) as cnt FROM trading_picks WHERE status = 'CLOSED' GROUP BY strategy) t` |
| Resolver dispute rate | Weekly | `trading_picks` table | > 2% | `SELECT SUM(CASE WHEN resolver_status = 'DISPUTED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) FROM trading_picks WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)` |
| DSR (rolling 30d) | Weekly | Walk-forward engine | < 0.5 | Run `deflated_sharpe_ratio()` on last 30 days of closed trades |
| PBO (rolling 30d) | Weekly | Walk-forward engine | > 0.6 | Run `probability_of_backtest_overfitting()` on last 30 days |
| Regime drift | Monthly | Regime classifier | Edge shift > 15% | Compare current month's regime performance vs prior 3 months |
| Forward/OOS decay | Per promotion | Promotion gate | > 20% | `abs(forward_pf - oos_pf) / oos_pf` |

### Concentration Detection (Python)

```python
def compute_concentration_metrics(picks):
    """Detect concentration masquerading as edge."""
    from collections import Counter
    
    # Strategy-level concentration (Herfindahl-Hirschman Index)
    strategy_counts = Counter(p['strategy'] for p in picks)
    total = sum(strategy_counts.values())
    hhi = sum((count / total) ** 2 for count in strategy_counts.values())
    
    # Source-level concentration
    source_counts = Counter(p.get('source', 'unknown') for p in picks)
    dominant_source_pct = max(source_counts.values()) / total
    
    # Symbol-level concentration
    symbol_counts = Counter(p['symbol'] for p in picks)
    dominant_symbol_pct = max(symbol_counts.values()) / total
    
    return {
        'strategy_hhi': hhi,
        'dominant_source_pct': dominant_source_pct,
        'dominant_symbol_pct': dominant_symbol_pct,
        'alerts': [
            'STRATEGY_CONCENTRATION' if hhi > 0.25 else None,
            'SOURCE_CONCENTRATION' if dominant_source_pct > 0.50 else None,
            'SYMBOL_CONCENTRATION' if dominant_symbol_pct > 0.30 else None,
        ]
    }
```

### Resolver Health Check (SQL)

```sql
-- Weekly resolver dispute audit
SELECT 
    asset_class,
    strategy,
    COUNT(*) as total_picks,
    SUM(CASE WHEN resolver_status = 'DISPUTED' THEN 1 ELSE 0 END) as disputed,
    ROUND(SUM(CASE WHEN resolver_status = 'DISPUTED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as dispute_pct,
    SUM(CASE WHEN status = 'TIME_EXIT' THEN 1 ELSE 0 END) as time_exits,
    ROUND(SUM(CASE WHEN status = 'TIME_EXIT' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as time_exit_pct
FROM trading_picks
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY asset_class, strategy
HAVING dispute_pct > 2.0 OR time_exit_pct > 30.0
ORDER BY dispute_pct DESC;
```

---

## 4. Mutation Testing Framework

### Overview

For every strategy that fails but has plausible signal (WR > 45%, PF > 0.8), run:
1. **Parameter mutation** — grid search ±20% on each parameter
2. **Symbol mutation** — test on different symbols in same asset class
3. **Timeframe mutation** — test on 1h, 4h, 1d
4. **Inversion** — fade the signal (only with OOS proof)

### Code: Parameter Mutation

```python
def mutate_parameters(strategy, ohlcv, capital=100_000, pct_range=0.20):
    """
    Generate parameter variants and test each through admissibility pipeline.
    Retain variants with PF improvement >= 0.05.
    """
    base_params = strategy.default_params()
    param_ranges = {}
    
    for param_name, base_value in base_params.items():
        if isinstance(base_value, (int, float)):
            low = base_value * (1 - pct_range)
            high = base_value * (1 + pct_range)
            param_ranges[param_name] = np.linspace(low, high, 5).tolist()
    
    results = []
    for combo in itertools.product(*param_ranges.values()):
        params = dict(zip(param_ranges.keys(), combo))
        variant = strategy.clone(params)
        
        # Run through purged walk-forward
        wf = purged_walk_forward(variant, ohlcv)
        
        if wf.verdict == "PASS":
            results.append(MutationResult(
                params=params,
                oos_pf=wf.oos_pf,
                oos_sharpe=wf.oos_sharpe,
                oos_trades=wf.oos_n_trades,
                improvement=wf.oos_pf - base_pf
            ))
    
    # Sort by OOS Sharpe
    results.sort(key=lambda x: x.oos_sharpe, reverse=True)
    
    # Retain only if improvement >= 0.05
    return [r for r in results if r.improvement >= 0.05]
```

### Code: Symbol Mutation

```python
def mutate_symbols(strategy, symbols, interval='4h', capital=100_000):
    """
    Test strategy on different symbols in same asset class.
    Edge must work on >= 60% of symbols.
    """
    results = {}
    for sym in symbols:
        df, _ = fetch_crypto_ohlcv_paginated(sym, interval=interval, target_bars=1500)
        if df is None or len(df) < 500:
            continue
        
        wf = purged_walk_forward(strategy, df)
        results[sym] = {
            'oos_pf': wf.oos_pf,
            'oos_sharpe': wf.oos_sharpe,
            'oos_trades': wf.oos_n_trades,
            'passed': wf.verdict == "PASS"
        }
    
    pass_rate = sum(1 for r in results.values() if r['passed']) / len(results)
    
    return SymbolMutationResult(
        results=results,
        pass_rate=pass_rate,
        verdict="ROBUST" if pass_rate >= 0.60 else "FRAGILE"
    )
```

### Code: Inversion Testing

```python
def test_inversion(strategy, ohlcv, capital=100_000):
    """
    Test if fading the signal is profitable.
    Only invert with explicit OOS proof.
    """
    # Run original
    _, trades_original = strategy.run(ohlcv, capital)
    pf_original = compute_pf(trades_original)
    wr_original = compute_wr(trades_original)
    
    # Run inverse (flip BUY↔SELL signals)
    inverse_strategy = strategy.clone({'invert_signals': True})
    _, trades_inverse = inverse_strategy.run(ohlcv, capital)
    pf_inverse = compute_pf(trades_inverse)
    wr_inverse = compute_wr(trades_inverse)
    
    return InversionResult(
        original_pf=pf_original,
        original_wr=wr_original,
        inverse_pf=pf_inverse,
        inverse_wr=wr_inverse,
        recommendation="FADE" if pf_inverse > pf_original and pf_inverse > 1.0 else "KEEP",
        # Only fade if inverse is clearly better on OOS
        confidence="HIGH" if pf_inverse > 1.2 and pf_original < 0.9 else "LOW"
    )
```

---

## 5. Timeline (12-Week Horizon)

| Week | Milestone | Owner |
|------|-----------|-------|
| 1-2 | Enable VWAPReversion + BollingerMR. Depromote EQUITY/FOREX. Data/resolver audit. | Quant Ops |
| 3-4 | Deploy standardized admissibility pipeline. Pre-register all hypotheses. | Quant Research |
| 5-6 | Run purged walk-forward on ETF dual momentum + crypto VWAP/Bollinger on 4h. | Quant Research |
| 7 | Shadow-size approved sleeves (ETF 0.2%, Crypto VWAP 0.5%). | Portfolio Mgmt |
| 8-9 | Mutation testing on failed lab sleeves. Evaluate inversion candidates. | Quant Research |
| 10 | Promote any sleeve meeting live PF/WR gate (≥ 0.5 PF, ≤ 0.6 WR). | Portfolio Mgmt |
| 11-12 | Full-size rollout for successful sleeves. Deploy Grafana monitoring dashboard. | Ops |

---

## 6. Success Definition (Quarterly Review)

| Metric | Target |
|--------|--------|
| Deployable edge | ≥ 2 new capital-ready sleeves with live PF ≥ 0.5, WR ≤ 0.6 |
| Data cleanliness | Resolver dispute rate < 1% across all live feeds |
| Concentration | HHI for aggregate book < 0.20 |
| Pipeline latency | End-to-end validation ≤ 5 min per sleeve |
| Walk-forward pass rate | ≥ 10% of tested strategies pass |

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Resolver drift | Medium | High | Continuous health checks; fallback to backup source |
| Over-fitting during mutation | Low | Medium | Strict OOS holdout; block-bootstrap verification |
| Regulatory change | Low | High | Maintain policy-clean flagging; rapid re-validation |
| Capital allocation lag | Medium | Low | Pre-approved shadow-size budget; automated scaling |
| ML confidence remains anti-predictive | High | Medium | Disable ML gate for CRYPTO until recalibrated |

---

*Generated: 2026-06-02T07:15Z*
*Agent: Claude Code (gx10-c9b9)*
*Based on: 3 parallel agent audits + live dashboard data + AI Leaderboard MC verdict*
