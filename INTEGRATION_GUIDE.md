# Edge Finder v2 Integration Guide

**Complete integration of PHP Edge Finder v2 API with Python HF Statistical Validation**

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PICK GENERATION SOURCES                           │
│  (Your existing strategies: LSR, OBB, VDR, VRM, SMC, etc.)          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHP EDGE FINDER V2 API                                             │
│  File: live-monitor/api/edge_finder_v2.php                          │
│                                                                     │
│  ?action=scan → Returns:                                            │
│    • bucket: ACTIVE / SMART / HIGH_CONVICTION                       │
│    • final_score: alpha_score - risk_penalty                        │
│    • score_breakdown: detailed components                           │
│    • reasons: explainability tags                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PYTHON HF VALIDATION LAYER (NEW)                                   │
│  File: audit_trail/edge_finder_bridge.py                            │
│                                                                     │
│  Validates:                                                         │
│    • DSR (Deflated Sharpe Ratio) > 0.5                              │
│    • Harvey-Liu p-value < 0.05                                      │
│    • Regime robustness (3+ of 4 regimes)                            │
│    • Kill switch status (4-tier)                                    │
│    • CVaR position sizing                                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FINAL PRODUCTION PICKS                                             │
│  Approved picks with full validation metadata                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Test Your PHP API

Visit these endpoints to verify your PHP API is working:

```bash
# Main scan endpoint
https://yourdomain.com/live-monitor/api/edge_finder_v2.php?action=scan

# Check methodology
https://yourdomain.com/live-monitor/api/edge_finder_v2.php?action=methodology

# Market status
https://yourdomain.com/live-monitor/api/edge_finder_v2.php?action=market
```

**Expected Response:**
```json
{
  "ticker": "NVDA",
  "bucket": "HIGH_CONVICTION",
  "final_score": 78.4,
  "alpha_score": 65.2,
  "risk_penalty": 6.8,
  "reasons": ["fresh_pick", "tight_entry_cluster"]
}
```

### 2. Use the Python Bridge

```python
from audit_trail.edge_finder_bridge import EdgeFinderBridge

# Initialize bridge
bridge = EdgeFinderBridge(
    api_base_url="https://yourdomain.com",
    min_dsr=0.5,  # Minimum Deflated Sharpe Ratio
    min_p_value=0.05  # Maximum Harvey-Liu p-value
)

# Validate a single pick
pick = bridge.validate_pick(
    ticker="NVDA",
    historical_returns=pd.Series([...]),  # Strategy returns
    current_regimes=pd.Series([...]),     # Regime labels
    portfolio_value=100000,
    position_sizes={"BTCUSDT": 0.1}
)

print(f"PHP Bucket: {pick.php_bucket}")          # From PHP API
print(f"Final Bucket: {pick.final_bucket}")      # After HF validation
print(f"DSR: {pick.dsr}")                        # Deflated Sharpe
print(f"Approved: {pick.approved_for_trading}")  # Final decision
print(f"Position Size: {pick.position_size:.2%}")
```

### 3. Batch Validation

```python
# Validate multiple picks
tickers = ["NVDA", "AAPL", "BTCUSDT", "ETHUSDT"]

results = bridge.batch_validate(
    tickers=tickers,
    returns_data={
        "NVDA": nvda_returns,
        "AAPL": aapl_returns,
        ...
    },
    portfolio_value=100000
)

# Filter approved picks
approved = [r for r in results if r.approved_for_trading]
```

### 4. Portfolio Risk Snapshot

```python
# Get complete portfolio risk status
snapshot = bridge.get_portfolio_snapshot(
    portfolio_value=100000,
    all_returns=returns_df,  # DataFrame of all strategy returns
    position_sizes={"NVDA": 0.1, "BTCUSDT": 0.05}
)

print(f"Current DD: {snapshot['current_drawdown']:.1%}")
print(f"CVaR 95%: {snapshot['cvar_95']:.2%}")
print(f"Kill Switch: {snapshot['kill_switch_level']}")
print(f"Can Trade: {snapshot['can_trade']}")
```

## Integration with smart_picks_engine.py

Replace your existing validation with the bridge:

```python
# OLD CODE (existing)
def filter_picks(picks):
    smart_picks = []
    for pick in picks:
        if pick['score'] > 60:  # Simple threshold
            smart_picks.append(pick)
    return smart_picks

# NEW CODE (with HF validation)
from audit_trail.edge_finder_bridge import integrate_with_smart_picks_engine

def filter_picks(picks, portfolio_value, returns_data):
    bridge = integrate_with_smart_picks_engine()
    
    smart_picks = []
    for pick in picks:
        ticker = pick['symbol']
        returns = returns_data.get(ticker)
        
        validated = bridge.validate_pick(
            ticker=ticker,
            historical_returns=returns,
            portfolio_value=portfolio_value
        )
        
        if validated.approved_for_trading:
            # Add HF metadata to pick
            pick['hf_validated'] = True
            pick['dsr'] = validated.dsr
            pick['cvar_95'] = validated.cvar_95
            pick['position_size'] = validated.position_size
            pick['final_bucket'] = validated.final_bucket
            smart_picks.append(pick)
    
    return smart_picks
```

## Validation Criteria

### PHP API Buckets
| Bucket | Score Range | Description |
|--------|-------------|-------------|
| HIGH_CONVICTION | 75-100 | Strong signal, multiple confirmations |
| SMART | 55-74 | Good signal, some concerns |
| ACTIVE | 35-54 | Weak signal, monitor closely |
| REJECTED | <35 | Does not meet criteria |

### HF Validation Gates
| Gate | Threshold | Purpose |
|------|-----------|---------|
| DSR | >0.5 | Ensure skill (not luck) |
| Harvey-Liu p | <0.05 | Multiple testing correction |
| Regimes | 3+ of 4 | Robust across market conditions |
| Kill Switch | <20% DD | Risk management |
| CVaR | <5% | Tail risk control |

### Position Sizing Formula
```
base_size = {HIGH_CONVICTION: 10%, SMART: 5%, ACTIVE: 2.5%}
hf_multiplier = 1.0 if validated else 0.5
kill_multiplier = {WARNING: 0.75, CAUTION: 0.50, ALERT: 0.25, KILL: 0.0}
cvar_multiplier = min(0.05 / cvar_95, 1.0) if cvar_95 > 0.05 else 1.0

final_size = base_size * hf_multiplier * kill_multiplier * cvar_multiplier
final_size = min(final_size, 15%)  # Max 15% per position
```

## Migration Path

### Phase 1: Parallel Logging (Week 1)
```python
# Log both old and new scores without using new gates
validated = bridge.validate_pick(...)
log.info(f"Old score: {pick['score']}, New HF score: {validated.dsr}")
# Still use old filtering for production
```

### Phase 2: Soft Warnings (Week 2)
```python
# Flag discrepancies but don't block
if pick['bucket'] == 'HIGH_CONVICTION' and not validated.hf_validated:
    log.warning(f"{ticker}: PHP says HIGH, HF says REJECT")
    # Still allow but flag for review
```

### Phase 3: Hard Gates (Week 3+)
```python
# Require HF validation for production
if not validated.approved_for_trading:
    continue  # Skip this pick
```

## Files in This Enhancement

| File | Lines | Purpose |
|------|-------|---------|
| `audit_trail/hf_statistical_rigor.py` | 388 | Multiple testing, DSR, regime metrics |
| `audit_trail/hf_risk_management.py` | 797 | Kill switches, CVaR, correlation, scenarios |
| `audit_trail/edge_finder_bridge.py` | 433 | PHP ↔ Python integration layer |
| `HF_SCORING_ENHANCEMENT_SUMMARY.md` | 224 | Technical documentation |
| `INTEGRATION_GUIDE.md` | This file | Usage guide |

## Troubleshooting

### PHP API Not Responding
```python
# Bridge automatically falls back to basic scoring
pick = bridge.validate_pick(ticker="NVDA")  # No historical_returns
# Returns: bucket=ACTIVE, hf_validated=True (pass by default)
```

### Insufficient Historical Data
```python
# Need at least 100 observations for HF validation
if len(returns) < 100:
    # Bridge passes pick but notes insufficient data
    pick = bridge.validate_pick(ticker="NVDA", historical_returns=returns)
    # pick.hf_validated = True (pass by default)
    # pick.rejection_reasons = ['insufficient_data']
```

### Kill Switch Active
```python
portfolio_value = 82000  # 18% DD from 100k peak
pick = bridge.validate_pick(..., portfolio_value=portfolio_value)
# pick.kill_switch_level = "CAUTION"
# pick.position_size *= 0.5  # Reduced by 50%
```

## Next Steps

1. **Test PHP API endpoints** on your domain
2. **Run bridge validation** on historical picks
3. **Compare old vs new scores** (should see fewer false positives)
4. **Deploy gradually** following Phase 1-3 migration
5. **Monitor DSR vs actual performance** (expect correlation > 0.30)

## Support

For questions or issues:
- Review `HF_SCORING_ENHANCEMENT_SUMMARY.md` for technical details
- Check module docstrings for API reference
- Run `python audit_trail/edge_finder_bridge.py` for example usage
