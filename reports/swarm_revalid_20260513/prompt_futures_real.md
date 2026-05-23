# Re-validate FUTURES asset-class edge against REAL backtest data

## Context

Prior swarm round (2026-05-11) returned `NO_EDGE` for every FUTURES strategy variant tested. That round ran on synthetic n=10 trade stubs with simplified signal translation.

This re-validation grounds the same question in REAL data from `tools/backtest_futures_ts_momentum.py` against 14 liquid yfinance continuous-contract futures (CT/GC/SI/HG/ZC/ZW/ZS/NG/ES/NQ/ZN/ZB/6E/6J — CL=F excluded per memory). Moskowitz-Ooi-Pedersen 2012 time-series momentum, 12m signal × inverse-vol weights, monthly rebalance.

## Real backtest results

**LONG-SHORT variant** (long > 0 / short < 0 per instrument):
- n = 160 periods (~13.3 years)
- WR = 58.13%
- Profit Factor = 1.7083
- Sharpe (annualized) = 0.6564
- Max Drawdown = 13.61%
- Total return = +55.05% over backtest

**LONG-ONLY variant** (clip negatives to zero):
- n = 145 periods (~12 years)
- WR = 61.38%
- Sharpe = 0.8551
- Max Drawdown = **6.57%** (passes TIER-1 MDD≤10% threshold)
- Total return = +54.3%

## Tier classification (per `docs/PERFORMANCE_CHARTER.md`)

- TIER-1: PF≥2 AND WR≥55 AND MDD≤10 AND n≥200
- TIER-2: PF≥1.5 AND WR≥50 AND MDD≤20 AND n≥100
- TIER-3: PF≥1.2 AND WR≥45 AND MDD≤25 AND n≥100

LONG-SHORT verdict: TIER-2 confirmed (PF 1.71, WR 58.1, MDD 13.6, n=160). Fails TIER-1 only on PF<2.
LONG-ONLY verdict: NEAR-TIER-1 (MDD 6.57 passes; WR 61.4 passes; PF unmeasured in long-only since no losses fully cancel wins).

## Question to engines

You are a quant researcher reviewing FUTURES asset class. Live `/audit` shows FUTURES sub-floor: WR 5.9%, PF 0.00 (essentially silent-dead per `project_futures_kill_without_replacement.md`). But the offline academic backtest above shows real edge.

**Your job:** propose 3-5 concrete, implementable strategy variants OR signal-emission paths that translate the academic edge into live `/audit` picks. For each, return strict JSON ONLY:

```json
{
  "strategies": [
    {
      "name": "<short_identifier>",
      "thesis": "<1-sentence why this should work>",
      "signal_construction": "<exact rule: lookback + entry + exit>",
      "universe": ["<futures symbols>"],
      "expected_pf": <number>,
      "expected_sharpe": <number>,
      "expected_mdd_pct": <number>,
      "differentiation_from_existing": "<how is this different from the live FUTURES emitters that are dead>",
      "implementation_hours": <integer>,
      "wire_target": "<which file in alpha_engine/ or audit_trail/ would emit this signal>",
      "data_source": "<yfinance / CFTC COT / FRED / etc.>",
      "fail_mode": "<the most likely way this strategy could overfit or fail in live>"
    }
  ],
  "killers": [
    "<existing live FUTURES strategy that should be retired (with reason)>"
  ],
  "tier1_attainability_pct": <0-100, your confidence the class can reach TIER-1 in 60 days>,
  "single_most_important_finding": "<one sentence>"
}
```

## Constraints

- NO speculation about strategies that need data we don't have (e.g., no order-book microstructure, no satellite imagery)
- All proposed signals must be reproducible with: yfinance, CFTC COT (already wired via `tools/cot_fetcher_socrata.py`), FRED (key available), or basic price-derived features
- Must explain why the academic edge (MDD 6.57% long-only) hasn't materialized in live emitters
- Reject any strategy that requires holding > 30 days (we're scoring on monthly rebalance)
- Reject any strategy whose `expected_pf` is below 1.5 (TIER-2 floor)
