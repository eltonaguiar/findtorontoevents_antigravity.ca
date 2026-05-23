# DBMF / CTA Commodity-Momentum Replication Research

## Context

You are a quantitative researcher for findtorontoevents.ca/audit.

Goal: create `tools/research/dbmf_replication.py` — a CTA commodity-momentum replication strategy
inspired by iMGP DBi Managed Futures Strategy ETF (DBMF) and SG CTA Index methodology.

This would give the system a rules-based COMMODITY signal independent of source-system quality issues.

## Your Task

1. **Research the DBMF replication methodology:**
   - DBMF replicates top-20 CTA funds using multiple regression on 8 liquid futures
   - The regression is re-estimated monthly
   - Core signals: 12m - 1m momentum (trend-following) on commodities, bonds, FX, equity index futures

2. **Read** the existing project files:
   - `alpha_engine/config.py` — available strategy families, data sources
   - `tools/research/` — check if any forex_carry.py or related research exists
   - `audit_trail/quality_gates.py` — search for "COMMODITY" to understand current commodity gates
   - `alpha_engine/strategies/` — check for existing momentum strategies

3. **Design `tools/research/dbmf_replication.py`**:
   - Inputs: OHLCV for 8 commodity futures (GC=F, CL=F, HG=F, ZC=F, ZS=F, ZW=F, NG=F, SI=F) via yfinance
   - Signal: 12-month rolling return minus 1-month return (trend strength)
   - Output: ranked list of LONG/SHORT signals with conviction scores
   - Regime filter: only emit LONG signals when trend_strength > 0 (same as CTA funds)
   - Output format: compatible with `audit_trail/quality_gates.py` pick schema

4. **Wire-up plan** (Wire-Up Rule compliance):
   - Name the function in quality_gates.py or alpha_engine that would call this module
   - Provide the exact integration point
   - Provide a `## Wiring Plan` section if full wire-up is deferred

5. **Produce the complete implementation** in JSON output:

## Output Format (JSON)

```json
{
  "module_path": "tools/research/dbmf_replication.py",
  "strategy_name": "dbmf_momentum",
  "signals": ["GC=F", "CL=F", "HG=F", "ZC=F", "ZS=F"],
  "lookback_months": 12,
  "implementation": "full Python code as a string",
  "wiring_plan": {
    "caller_file": "...",
    "caller_function": "...",
    "integration_pr_target": "next sprint"
  },
  "backtest_expectation": {"wr": 0.0, "pf": 0.0, "sharpe": 0.0},
  "data_source": "yfinance | FRED | other",
  "dependencies": ["yfinance", "pandas", "numpy"]
}
```
