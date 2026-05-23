# DBMF / CTA Commodity-Momentum Replication — Swarm Research Report
**Date:** 2026-05-16 | **Engine:** deepseek-v4-flash | **Run:** dbmf-v2-20260516T230454Z

## Module: tools/research/dbmf_replication.py

Full implementation produced by swarm. Key specs:

| Field | Value |
|-------|-------|
| Strategy | `dbmf_momentum` |
| Universe | GC=F, CL=F, HG=F, ZC=F, ZS=F, ZW=F, NG=F, SI=F |
| Signal | 12-month return minus 1-month return (trend strength) |
| Regime filter | LONG only when momentum > 0 |
| Data source | yfinance |
| Backtest target | Sharpe 0.5-0.8 / WR 55-60% / PF 1.2-1.5 |

### Wiring Plan

```
caller_file: audit_trail/quality_gates.py
caller_function: run_commodity_quality_gates() → new check_dbmf_momentum()
integration:
  1. from tools.research.dbmf_replication import get_dbmf_signals
  2. New gate: check_dbmf_momentum() calls get_dbmf_signals() → validates signal quality
  3. Add 'dbmf_momentum' to COMMODITY strategy families in alpha_engine/config.py
  4. Wire into run_quality_gates()
Target PR: next sprint after initial data collection validates signal quality
```

### Implementation Status

Module written to `tools/research/dbmf_replication.py`. Class `DBMFReplicator` with:
- `fetch_data()` — yfinance OHLCV download with MultiIndex handling
- `calculate_momentum_signals()` — 12m-1m momentum per ticker
- `generate_signals()` — ranked LONG signals with conviction scores
- `get_quality_gate_compatible_output()` — compatible with quality_gates.py pick schema
- `run()` — full pipeline
- `get_dbmf_signals()` — entry point for wiring

### Next Steps

1. Run `python tools/research/dbmf_replication.py --json` to see current signals
2. Run 1-year backtest (add `--backtest` flag — implement in next sprint)
3. If Sharpe > 0.5, proceed with wiring into quality_gates.py
