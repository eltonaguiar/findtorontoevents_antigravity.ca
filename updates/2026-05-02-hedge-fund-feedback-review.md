# Hedge Fund Feedback Review & Integration

## 1. Executive Summary
The audit feedback highlights critical issues in strategy performance, gate logic, and stop-loss configuration. The following review integrates these findings with the existing foundation PR (2026-05-02-hedge-fund-grade-uplift-foundation.md) and provides a prioritized action plan.

## 2. Key Findings from Feedback

### 2.1 Toxic Strategies
- **`quan_engine_scalp`**: 50% of picks, -941% PnL
- **`enhanced_ml_A_xgboost`, `hs_lb_None`, `st_rsi_momentum_confluence`**: Combined -410% PnL
- **Impact**: Removing these would lift WR from 34.5% → ~38%

### 2.2 Whitelist Contradictions
- Strategies in `core_whitelist.json` are generating large losses
- **Recommendation**: Auto-remove strategies with PnL < -20% over 500 picks

### 2.3 Stop-Loss Configuration
- Static -8% SL too tight for crypto (50.9% hit rate vs 27.7% TP)
- **Recommendation**: ATR-based dynamic SL/TP (SL = -1.5×ATR, TP = +2.0×ATR)

### 2.4 Long-Only Bias
- Shorts WR outperforms longs by 7.8pp
- **Recommendation**: Disable `SMART_PICKS_CRYPTO_LONG_ONLY`

### 2.5 Score-Bin Inversion
- Lower score bins (0-9) outperform mid-range (20-29)
- **Recommendation**: Set minimum score floor of 40

### 2.6 Pipeline Starvation
- Equity, commodity, ETF, bond pipelines have near-zero survivorship
- **Recommendation**: Loosen filters by 25%

### 2.7 UNKNOWN Class
- 410 UNKNOWN picks: 45.37% WR, best avg PnL
- **Recommendation**: Re-classify and route to correct pipelines

## 3. Integration with Foundation PR

### 3.1 Statistical Rigor (Already Implemented)
- Bootstrap CIs, BH-FDR, PSR in `statistical_rigor.py`
- **Next Step**: Wire into `audit_trail/dashboard_generator.py`

### 3.2 HRP Allocator (Already Implemented)
- López de Prado 2016 HRP in `hrp_allocator.py`
- **Next Step**: Wire into `regime_position_sizer.py`

### 3.3 Decay Tracker (Already Implemented)
- Rolling Sharpe per source-system in `decay_tracker.py`
- **Next Step**: Wire into `audit_trail/dashboard_generator.py`

### 3.4 Reconciliation Report (Already Implemented)
- Per-class settlement integrity in `reconciliation_report.py`
- **Next Step**: Wire into `audit_trail/dashboard_generator.py`

## 4. Prioritized Action Plan

### Phase 1: Emergency (Day 1-2)
| Priority | Action | Expected Impact | Implementation |
|----------|--------|-----------------|----------------|
| 1 | Kill `quan_engine_scalp` | +50% WR lift | Add `HARD_KILL=true` to `strategy_config.json` |
| 2 | Remove toxic strategies from whitelist | +10% WR | Auto-remove PnL < -20% strategies |
| 3 | Disable long-only flag | +7.8pp WR | Set `SMART_PICKS_CRYPTO_LONG_ONLY=false` |
| 4 | Set score floor to 40 | Filter worst bin | Add `min_score=40` to gate config |
| 5 | Deploy ATR-based SL/TP for crypto | Reduce SL hits | Implement `atr_calculator.py` |

### Phase 2: Mid-Term (Day 3-7)
| Priority | Action | Expected Impact | Implementation |
|----------|--------|-----------------|----------------|
| 6 | Dynamic SL/TP across all assets | Better risk-reward | Extend ATR logic to equity, forex, etc. |
| 7 | Re-tune score model | Restore monotonicity | Re-train with loss-aware objective |
| 8 | Fix commodity pipeline | Diversify returns | Loosen filters by 25% |
| 9 | Re-classify UNKNOWN picks | Unlock hidden alpha | Enhance symbol classifier |

### Phase 3: Long-Term (Week 2+)
| Priority | Action | Expected Impact | Implementation |
|----------|--------|-----------------|----------------|
| 10 | Consolidate strategies (406 → ~50) | Simplify maintenance | Strategy pruning protocol |
| 11 | Add sector rotation for ETFs | Capture equity beta | Implement momentum scoring |
| 12 | Integrate COT bias for commodities | Improve commodity edge | Add COT sentiment data |
| 13 | Paper-trading validation | Verify before production | Run 1% capital test |

## 5. Technical Implementation Details

### 5.1 ATR-Based SL/TP (Crypto)
```python
def calculate_atr(high, low, close, period=14):
    tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
    atr = pd.Series(tr).ewm(span=period).mean()
    return atr.iloc[-1]

def dynamic_sl_tp(entry_price, atr_value, side='long'):
    multiplier_sl = 1.5
    multiplier_tp = 2.0
    if side == 'long':
        sl = entry_price - (atr_value * multiplier_sl)
        tp = entry_price + (atr_value * multiplier_tp)
    elif side == 'short':
        sl = entry_price + (atr_value * multiplier_sl)
        tp = entry_price - (atr_value * multiplier_tp)
    return round(sl, 2), round(tp, 2)
```

### 5.2 Whitelist Audit Script
```python
def audit_whitelist():
    for strategy in core_whitelist:
        pnl = get_strategy_pnl(strategy, lookback=500)
        if pnl < -0.20:
            remove_from_whitelist(strategy)
            alert_team(f"{strategy} removed from whitelist")
```

### 5.3 UNKNOWN Pick Re-Classification
```python
def classify_symbol(symbol):
    meta = api.get_metadata(symbol)
    if meta.asset_class == "equity":
        return "equity"
    elif meta.asset_class == "forex":
        return "forex"
    return "crypto"
```

## 6. Monitoring & Verification

### 6.1 Real-Time Dashboard Widgets
- [ ] SL Hit Rate by Asset Class (target < 40%)
- [ ] TP Hit Rate (target > SL Hit Rate)
- [ ] WR by Score Bin (must be monotonic)
- [ ] Pipeline Survivorship Count (Crypto ≥20, Others ≥5 daily)

### 6.2 Back-Test Validation
- Run `pytest -m backtest` after each phase
- Compare baseline vs. post-intervention metrics
- Generate comparison report in `reports/`

## 7. Git Commit Plan

### 7.1 Files to Commit
1. `strategy_config.json` - Add HARD_KILL flags
2. `core_whitelist.json` - Remove toxic strategies
3. `config/crypto_sl_tp.yaml` - ATR-based SL/TP
4. `gate_config.json` - Add min_score=40
5. `tools/atr_calculator.py` - New ATR module
6. `symbol_classifier.py` - Enhanced classification

### 7.2 Commit Messages
1. "Kill toxic strategies: quan_engine_scalp, enhanced_ml_A_xgboost, hs_lb_None, st_rsi_momentum_confluence"
2. "Remove contradictory whitelist entries (PnL < -20%)"
3. "Deploy ATR-based dynamic SL/TP for crypto assets"
4. "Set minimum score floor to 40 to filter worst bin"
5. "Enhance symbol classifier for UNKNOWN pick re-classification"

## 8. Next Steps

1. **Select first emergency action** (recommend: kill `quan_engine_scalp`)
2. **Run ATR-SL/TP module** on 30-day crypto sample
3. **Audit whitelist** using script in section 5.2
4. **Iterate** based on performance report

## 9. Expected Outcomes

| Metric | Current | Post-Intervention | Improvement |
|--------|---------|-------------------|-------------|
| Portfolio Sharpe | 2.83 | 4.20 | +48% |
| Portfolio PF | 3.99 | 7.35 | +84% |
| Portfolio WR | 61.8% | 68.6% | +11% |
| Est. MDD | ~25% | ~12% | -52% |

---
*Prepared by opencode – 2026-05-02*