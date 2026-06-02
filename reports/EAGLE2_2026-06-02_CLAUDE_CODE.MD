# EAGLE2 Enhancement Plan — Claude Code (gx10-c9b9)
## Date: 2026-06-02

---

## 1. Root Cause Analysis: Why No Profitable Strategies Per Asset Class

### The Core Problem

**Research edge ≠ deployed edge.** The /audit production book is weak because we promote strategies from the wrong evidence, run too many weak emitters, tolerate concentration artifacts, and use inconsistent validation standards.

### Per-Asset-Class Root Causes

| Class | Live PF | Live WR | Root Cause | Verdict |
|-------|---------|---------|------------|---------|
| **CRYPTO** | 0.98 | 39.7% | Selection/gating/concentration mismatch. Proven cells exist (VWAP, Bollinger) but deployed aggregate book still loses. Smart/HC/ELITE surfaces inflated by mislabeled `claude_gainer_st`. | Edge exists in sub-cohorts, not in aggregate |
| **EQUITY** | 0.76 | 37.4% | Honest failure. Bad deployed strategies, failed holdout, weak emitter quality. Only `stocks_rsi2_pullback` works (n=70, WR=62.9%). | Hemorrhaging. Stop trading. |
| **ETF** | 0.34 | — | Best candidate edge (dual momentum), but sample too small (n=13). Backtests orphaned — no production wire-up. | Wait for forward n |
| **FOREX** | 0.27 | 46.1% | Data/resolver problem + weak edge. High WR with terrible PF = red flag. Mislabels/TIME_EXIT artifacts distorting picture. Hard-gated via PR #6. | Dead until resolver fixed |
| **COMMODITY** | 0.475 | 9.1% | Too little clean sample (n=3 policy-clean). CT=F DSR=1.0 was falsified (6.33x over-emission). | Stability/sample problem |
| **FUTURES** | — | — | Concentration/artifact risk. Stats too dependent on narrow sources/cohorts. | Don't trust yet |
| **BOND** | — | 55.6% | Mostly data gap. No meaningful live sample. Backtests PF 1.29-1.62 but orphaned. | Accumulating (78 raw picks) |

### The 5 Things We're Doing Wrong

1. **Different standards for research vs production** — lab sleeves look decent, but the main scanner emits from a much noisier universe
2. **Too much breadth, not enough promotion discipline** — 100+ strategies, 8 gates, 0 promoted to A-tier
3. **Confusing "interesting cell" with "capital-ready strategy"** — tournament edge ≠ funnel edge ≠ money-ready edge
4. **Concentration masquerading as edge** — one source/system dominating looks amazing but is fragile
5. **Resolver/label/duplicate issues polluting trust** — disputed cohorts, mislabeled `claude_gainer_st` inflating CRYPTO stats

### The MA Trend Finding (Critical)

The AI Leaderboard's Monte Carlo verdict (2026-05-29): **"these high Profit Factors are trend-following shape, not edge."**

- 200-day MA **underperforms buy-and-hold risk-adjusted in all 7 asset classes**
- It **fails the timing test** — being long on above-MA days is no better than random (null p = 0.28–0.67)
- The only genuine benefit: **lower max-drawdown**
- Conclusion: treat MA-trend as **a defensive / regime overlay, NOT an alpha source**

---

## 2. Where the Real Edge Is

### Confirmed (Multiple Validations)

| Strategy | Asset | Evidence | Action |
|----------|-------|----------|--------|
| **VWAPReversion** | CRYPTO | DSR=21.4, PBO=0.18 on 4h, 516 OOS trades, walk-forward PASS | **Enable: CRYPTO_VERIFIED_VWAP_ENABLED=1** |
| **BollingerMR** | CRYPTO | Walk-forward PASS, OOS PF=1.673, WR=52.6% | **Enable: CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED=1** |
| **OBV Divergence** | CRYPTO | 115 trades, WR=75.7%, PF=8.15, 15 WF folds, 100% consistency | Already in scanner |
| **stocks_rsi2_pullback** | EQUITY | n=70, WR=62.9%, only proven equity sleeve | Already active |

### Promising (Needs Forward Sample)

| Strategy | Asset | Evidence | What's Missing |
|----------|-------|----------|----------------|
| ETF Dual Momentum | ETF | Walk-forward PASS, OOS PF=1.21 | Forward sample (n too small) |
| CryptoDonchianBreakout | CRYPTO | Walk-forward PASS all 3, DSR=7.24 | PBO=0.676 (needs 4h test) |
| deepseek_v4 tournament | CRYPTO | Highest tournament PF | Same admissibility pipeline |
| Bond backtests | BOND | PF 1.29-1.62 | Production wire-up |

### Dead (Confirmed)

| Strategy | Asset | Evidence |
|----------|-------|----------|
| ConnorsRSI2 | CRYPTO | Sharpe -2.6, bleeds 89-97% despite 60% WR |
| ML confidence | ALL | Anti-predictive (conf ≥ 0.90 → 14.4% WR) |
| EQUITY aggregate | EQUITY | PF=0.76, hemorrhaging |
| FOREX aggregate | FOREX | PF=0.27, hard-gated |
| COMMODITY DSR=1.0 | COMMODITY | Falsified (6.33x over-emission) |

---

## 3. Enhancement Blueprint

### Phase 1: Stop the Bleeding (Week 1-2)

#### 3.1 Enable VWAPReversion + BollingerMR
```bash
# In production scanner environment:
CRYPTO_VERIFIED_VWAP_ENABLED=1
CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED=1
```
Gate: WALKFORWARD_REPORT.json → "vwap_reversion" = PASS, "bollinger_mr" = PASS

#### 3.2 Depromote Weak Live Classes
- **EQUITY**: Desize to 0 until `stocks_rsi2_pullback` is the only emitter
- **FOREX**: Keep hard-gated (PR #6). Don't lift until PF > 1.0
- **CRYPTO aggregate**: Desize. Promote individual sleeves (VWAP, Bollinger) instead

#### 3.3 Fix Portfolio Pipeline
- Verify `pf_portfolio_deepseek_v4__aggressive.json` exists and is being served
- Debug the daily cron that generates portfolio data
- Confirm 81 portfolios / 66 with positions are accessible

### Phase 2: Admissibility Pipeline (Week 3-4)

Every strategy must pass this 10-step pipeline before it can affect capital:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ADMISSIBILITY PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│ Step 1: Pre-register hypothesis (before backtest)                   │
│   - Lock parameters, symbol universe, entry/exit rules              │
│   - Document expected edge source                                   │
│   - Use reports/hypothesis_registry.json                            │
│                                                                     │
│ Step 2: Real data only                                              │
│   - No synthetic data, explicit source provenance                   │
│   - FRED API key for carry rates                                    │
│   - fetch_crypto_ohlcv_paginated() for deep history                 │
│                                                                     │
│ Step 3: Purged + embargoed walk-forward                             │
│   - 70/30 IS/OOS chronological split                                │
│   - ≥30 day purge gap, 10 day embargo                               │
│   - Rolling windows (train=504d, test=126d)                         │
│                                                                     │
│ Step 4: Costs/slippage by asset class                               │
│   - Crypto: 10bps commission + 5bps slippage                        │
│   - Equity: 5bps + 3bps                                             │
│   - Forex: 3bps + 2bps                                              │
│                                                                     │
│ Step 5: DSR + PBO + SPA correction                                  │
│   - DSR > 1.0 required                                              │
│   - PBO < 0.5 required                                              │
│   - SPA p-value < 0.10                                              │
│                                                                     │
│ Step 6: Block bootstrap (not i.i.d. shuffle)                        │
│   - Preserve autocorrelation structure                              │
│   - 1000 iterations minimum                                         │
│                                                                     │
│ Step 7: Regime robustness                                           │
│   - Must work in trending AND ranging markets                       │
│   - Edge persists in ≥ 3 of 4 regimes                               │
│                                                                     │
│ Step 8: Forward paper evidence                                      │
│   - Minimum 30 resolved picks                                       │
│   - Forward PF within 20% of OOS PF                                 │
│                                                                     │
│ Step 9: Promotion gate                                              │
│   - Only if forward PF/WR stays close to OOS lab PF/WR              │
│   - Live PF ≥ 0.5, WR ≤ 0.6                                        │
│                                                                     │
│ Step 10: Gradual capital scaling                                    │
│   - Shadow → tiny (0.5%) → small (5%) → full                       │
│   - Scale only after live proof (8 weeks)                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Phase 3: DNA Mutation (Week 5-6)

#### Mutation Framework
For every strategy that fails but has plausible signal:

```python
# Pseudo-code for mutation pipeline
def mutate_strategy(base_strategy, param_ranges):
    """Generate parameter variants and test each."""
    variants = []
    for params in grid_search(param_ranges):
        variant = base_strategy.clone(params)
        # Run through admissibility pipeline
        result = run_admissibility_pipeline(variant)
        if result.oos_pf >= 1.05 and result.oos_wr > 0:
            variants.append(result)
    return sorted(variants, key=lambda x: x.oos_sharpe, reverse=True)

# Example: ConnorsRSI2 mutation
param_ranges = {
    'rsi_oversold': [5, 10, 15, 20],
    'rsi_overbought': [65, 70, 75, 80],
    'tp_atr_mult': [1.5, 2.0, 2.5, 3.0],
    'sl_atr_mult': [1.0, 1.5, 2.0],
    'max_hold': [5, 10, 15, 20],
}
```

#### Inversion Testing
For every strategy with WR > 60% but negative Sharpe:
```python
def test_inversion(strategy, data):
    """Test if fading the signal is profitable."""
    eq_normal, trades_normal = strategy.run(data, capital)
    eq_inverse, trades_inverse = run_inverse(strategy, data, capital)
    
    if trades_inverse and compute_pf(trades_inverse) > 1.0:
        return InversionResult(
            original_pf=compute_pf(trades_normal),
            inverse_pf=compute_pf(trades_inverse),
            recommendation="FADE"
        )
```

**Example**: ConnorsRSI2 (WR 60%, PF 0.95) → inverse would have WR 40%, PF ~1.05

### Phase 4: Monitoring & Governance (Week 7-8)

#### Real-Time Metrics Dashboard

| Metric | Frequency | Alert Threshold | Tool |
|--------|-----------|-----------------|------|
| Live PF | Daily | < 0.4 for > 5 days | Grafana |
| WR | Daily | > 0.7 with PF < 0.4 | Grafana |
| Concentration (HHI) | Weekly | > 0.25 | Custom script |
| Resolver dispute rate | Weekly | > 2% | SQL query |
| Regime drift | Monthly | Edge shift > 15% | Regime classifier |
| DSR (rolling 30d) | Weekly | < 0.5 | Rigorous harness |
| PBO (rolling 30d) | Weekly | > 0.6 | Rigorous harness |

#### Concentration Detection
```python
def compute_concentration(picks):
    """Herfindahl-Hirschman Index for strategy concentration."""
    strategy_counts = Counter(p.strategy for p in picks)
    total = sum(strategy_counts.values())
    hhi = sum((count / total) ** 2 for count in strategy_counts.values())
    return hhi  # Alert if > 0.25

def compute_source_concentration(picks):
    """Check if edge comes from one source/system."""
    source_counts = Counter(p.source for p in picks)
    dominant_pct = max(source_counts.values()) / sum(source_counts.values())
    return dominant_pct  # Alert if > 0.50
```

#### Resolver Health Check
```sql
-- Weekly resolver dispute audit
SELECT 
    asset_class,
    COUNT(*) as total_picks,
    SUM(CASE WHEN status = 'DISPUTED' THEN 1 ELSE 0 END) as disputed,
    ROUND(SUM(CASE WHEN status = 'DISPUTED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as dispute_pct
FROM trading_picks
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY asset_class
HAVING dispute_pct > 2.0;
```

---

## 4. Code Snippets: Standardized Validation Pipeline

### 4.1 Pre-Registration
```python
# reports/hypothesis_registry.json
{
    "H-050": {
        "name": "VWAPReversion_4h_CRYPTO",
        "registered_utc": "2026-06-02T07:00:00Z",
        "strategy_class": "VWAPReversionStrategy",
        "params": {"vwap_period": 50, "band_mult": 1.0, "tp_pct": 0.05, "sl_pct": 0.03},
        "universe": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
        "timeframe": "4h",
        "expected_edge": "VWAP mean reversion with institutional rebalancing",
        "success_criteria": {"min_oos_pf": 1.05, "min_oos_sharpe": 0.5, "min_trades": 50}
    }
}
```

### 4.2 Purged Walk-Forward
```python
def purged_walk_forward(strategy, data, train_pct=0.7, purge_days=30, embargo_days=10):
    """Proper purged walk-forward with gap between train/test."""
    split = int(len(data) * train_pct)
    train_end = split - purge_days
    test_start = split + embargo_days
    
    train_data = data.iloc[:train_end]
    test_data = data.iloc[test_start:]
    
    # Train: optimize parameters
    best_params = optimize_parameters(strategy, train_data)
    
    # Test: generate signals with LOCKED parameters
    strategy_locked = strategy.clone(best_params)
    equity, trades = strategy_locked.run(test_data, capital)
    
    return WalkForwardResult(
        is_sharpe=compute_sharpe(train_equity),
        oos_sharpe=compute_sharpe(equity),
        oos_pf=compute_pf(trades),
        oos_wr=compute_wr(trades),
    )
```

### 4.3 DSR + PBO
```python
def compute_dsr(sharpe, n_trials, n_observations):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)."""
    euler_mascheroni = 0.5772
    expected_max_sharpe = (1 - euler_mascheroni) * norm.ppf(1 - 1/n_trials) + euler_mascheroni * norm.ppf(1 - 1/(n_trials * math.e))
    
    sharpe_std = math.sqrt((1 + 0.5 * sharpe**2) / n_observations)
    dsr = norm.cdf((sharpe - expected_max_sharpe) / sharpe_std)
    return dsr

def compute_pbo(strategy, data, n_configs=100):
    """Probability of Backtest Overfitting (Bailey et al. 2015)."""
    # Generate strategy matrix: different parameter configurations
    configs = generate_param_grid(strategy, n_configs)
    pnl_matrix = np.array([run_strategy(c, data) for c in configs])
    
    # Find best IS config
    is_sharpes = [compute_sharpe(pnl) for pnl in pnl_matrix]
    best_is_idx = np.argmax(is_sharpes)
    
    # Check if best IS is also best OOS
    oos_sharpes = [compute_sharpe_oos(pnl) for pnl in pnl_matrix]
    best_oos_idx = np.argmax(oos_sharpes)
    
    pbo = 1.0 if best_is_idx != best_oos_idx else 0.0
    return pbo  # Simplified; real implementation uses combinatorial symmetric cross-entropy
```

### 4.4 Block Bootstrap
```python
def block_bootstrap(pnl_series, block_size=20, n_iterations=1000):
    """Block bootstrap preserving autocorrelation structure."""
    n = len(pnl_series)
    n_blocks = n // block_size
    
    bootstrap_sharpes = []
    for _ in range(n_iterations):
        # Sample blocks with replacement
        block_indices = np.random.choice(n - block_size + 1, size=n_blocks, replace=True)
        resampled = np.concatenate([pnl_series[i:i+block_size] for i in block_indices])
        bootstrap_sharpes.append(compute_sharpe(resampled))
    
    ci_lower = np.percentile(bootstrap_sharpes, 2.5)
    ci_upper = np.percentile(bootstrap_sharpes, 97.5)
    return ci_lower, ci_upper
```

### 4.5 Regime Robustness
```python
def test_regime_robustness(strategy, data):
    """Test edge across market regimes."""
    regimes = classify_regimes(data)  # trending_up, trending_down, ranging, volatile
    
    results = {}
    for regime_name, regime_data in regimes.items():
        equity, trades = strategy.run(regime_data, capital)
        results[regime_name] = {
            'pf': compute_pf(trades),
            'wr': compute_wr(trades),
            'sharpe': compute_sharpe(equity),
            'n_trades': len(trades),
        }
    
    # Edge must persist in >= 3 of 4 regimes
    profitable_regimes = sum(1 for r in results.values() if r['pf'] >= 1.0)
    robust = profitable_regimes >= 3
    
    return RegimeRobustnessResult(results=results, robust=robust)
```

---

## 5. Timeline (12-Week Horizon)

| Week | Milestone |
|------|-----------|
| 1-2 | Enable VWAPReversion + BollingerMR. Depromote EQUITY/FOREX. Data/resolver audit. |
| 3-4 | Deploy standardized admissibility pipeline. Pre-register all hypotheses. |
| 5-6 | Run purged-embargoed walk-forward on ETF dual momentum + crypto VWAP/Bollinger on 4h. |
| 7 | Shadow-size approved sleeves (ETF 0.2%, Crypto VWAP 0.5%). |
| 8-9 | Mutation testing on failed lab sleeves. Evaluate inversion candidates. |
| 10 | Promote any sleeve meeting live PF/WR gate (≥ 0.5 PF, ≤ 0.6 WR). |
| 11-12 | Full-size rollout for successful sleeves. Deploy Quant Ops Dashboard. |

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
| Unexpected resolver drift | Medium | High | Continuous resolver health checks; fallback to backup source |
| Over-fitting during mutation | Low | Medium | Strict OOS holdout; block-bootstrap verification |
| Regulatory policy change | Low | High | Maintain policy-clean flagging; rapid re-validation pipeline |
| Capital allocation lag | Medium | Low | Pre-approved shadow-size budget; automated scaling scripts |
| ML confidence remains anti-predictive | High | Medium | Disable ML gate for CRYPTO until recalibrated |

---

## 8. The Bottom Line

**We don't need more strategies. We need fewer, better-validated strategies with proper forward proof.**

The 100+ strategy funnel is noise. Most are curve-fit. The ones that survive are:
- VWAPReversion (crypto, 4h) — DSR=21.4, PBO=0.18
- BollingerMR (crypto, daily) — walk-forward PASS
- OBV Divergence (crypto) — WR=75.7%, PF=8.15
- stocks_rsi2_pullback (equity) — WR=62.9%

**The path forward:**
1. Enable VWAPReversion (stop the bleeding)
2. Depromote losing classes (EQUITY, FOREX)
3. Build the admissibility pipeline (prevent future failures)
4. Mutate failed strategies (find hidden edges)
5. Wait for forward sample on ETF/COMMODITY

---

*Generated: 2026-06-02T07:10Z*
*Agent: Claude Code (gx10-c9b9)*
*Based on: 3 parallel agent audits + live dashboard data + verification reports + AI Leaderboard MC verdict*
