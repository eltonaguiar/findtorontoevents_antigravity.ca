# Institutional Readiness P0 — Strategy Kill Blocks (2026-05-24)

## Summary

Following the industry benchmark analysis (`reports/audit_benchmark_analysis_2026-05-24.md`), 3 asset classes were identified as catastrophically below professional trading desk standards:

| Asset | WR% | PF | Benchmark WR | Benchmark PF | Verdict |
|-------|-----|----|-------------|-------------|---------|
| BOND | 0.0% | 0.00 | 48% | 1.20 |  CRITICAL |
| COMMODITY | 11.9% | 0.29 | 50% | 1.40 |  CRITICAL |
| FOREX | 32.8% | 0.92 | 48% | 1.30 | ❌ FAIL |

This commit adds P0 kill blocks for the worst-performing strategies in each class, aligned with Claude's institutional readiness plan (`plan/institutional-readiness-2026-05-24`).

## Changes to `audit_trail/quality_gates.py`

### BLOCKED_SOURCE_SYSTEMS — Added `bond_scanner`
```python
"bond_scanner",  # n=9 closed, 0% WR across all 3 strategies. No active edge.
```

### PERMANENTLY_KILLED_STRATEGIES — Added BOND strategies
```python
"bond_mean_reversion",       # n=5, 0% WR, all losses
"bond_yield_momentum",       # n=3, 0% WR, all losses
"bond_yield_curve_slope",    # n=1, 0% WR
```

### EXTRA_KILLED_FOREX_STRATEGIES — Added FOREX losers
```python
"fx_smart_carry_trade_momentum",       # n=15, 0% WR, -0.08% sum PnL
"fx_smart_forex_rsi2_mean_reversion",  # n=5, 0% WR, -0.03% sum PnL
```

### BLOCKED_STRATEGIES — Added FOREX pairs
```python
("fx_smart_carry_trade_momentum", "FOREX"),       # n=15, 0% WR
("fx_smart_forex_rsi2_mean_reversion", "FOREX"),  # n=5, 0% WR
```

## What Was Already Blocked (No Action Needed)

### COMMODITY
All major COMMODITY losers were already blocked in prior sessions:
- `cot_positioning` — BLOCKED_SOURCE_SYSTEMS (COT look-ahead leakage)
- `cftc_cot_commercial_signal` — PERMANENTLY_KILLED_STRATEGIES
- `futures_momentum` — BLOCKED_SOURCE_SYSTEMS + PERMANENTLY_KILLED_STRATEGIES
- `cta_cross_asset_tsmom` — BLOCKED_DIRECTION_TRIPLES (COMMODITY LONG+SHORT)
- `cta_commodity_momentum_term` — PERMANENTLY_KILLED_STRATEGIES
- `combined_confidence` — PERMANENTLY_KILLED_STRATEGIES

The 11.9% COMMODITY WR is a historical artifact from before these blocks were added. No new COMMODITY picks should be emitted from blocked strategies.

### FOREX (already blocked)
- `forex_rsi2_mean_reversion` — BLOCKED_STRATEGIES (7.1% WR post-resolver-v2)
- `forex_carry_momentum` — BLOCKED_ASSET_STRATEGY_PAIRS
- `myfxbook_retail_contrarian` — BLOCKED_ASSET_STRATEGY_PAIRS + BLOCKED_DIRECTION_TRIPLES (LONG)
- `ig_contrarian_sentiment` — BLOCKED_DIRECTION_TRIPLES (LONG only; SHORT is T1-grade at 61.4% WR)

The 32.8% FOREX WR is dragged down by historical `ig_contrarian_sentiment` LONG picks and the newly blocked `fx_smart_*` variants.

## Expected Impact

| Metric | Before | After (projected) |
|--------|--------|-------------------|
| BOND closed WR | 0.0% | N/A (no new picks) |
| FOREX closed WR | 32.8% | ~40%+ (removes 20 zero-WR picks) |
| COMMODITY closed WR | 11.9% | N/A (blocks already in place) |

## Alignment with Institutional Readiness Plan

This implements **Workstream A5** (honest stat surface — kill losers so metrics reflect real edge) and partially addresses the **Stage 1 gate** targets (PF>1.3, WR>48%) for FOREX. BOND and COMMODITY are effectively retired pending new strategy development (Workstream F1).

## Files Changed
- `audit_trail/quality_gates.py` — +12 lines (3 blocks added)
