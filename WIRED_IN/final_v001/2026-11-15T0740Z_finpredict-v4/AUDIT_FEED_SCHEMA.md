# AUDIT_FEED_SCHEMA — dashboard verdict panel

**Folder**: `WIRED_IN/final_v001/2026-11-15T0740Z_finpredict-v4/`
**Purpose**: define the JSON schema the audit dashboard (`findtorontoevents.ca/audit`) consumes so per-asset-class verdicts are honest, reproducible, and machine-readable.

## Source of truth
`reports/sma200_wealth_gate_backtest.json` (the clean, cost-adjusted, OOS, benchmark-relative backtest) plus per-candidate protocol outputs.

## Recommended verdict panel JSON

```json
{
  "generated_at": "2026-11-15T07:40Z",
  "benchmark_policy": "buy-and-hold of same asset, net of costs",
  "asset_classes": {
    "crypto": {
      "candidate": "BTC sma200",
      "verdict": "WEALTH_BEAT",
      "protocol_status": "0/10 gates complete",
      "sizing_allowed": false,
      "metrics": { "sharpe_strat": 0.567, "sharpe_bh": 0.463, "final_strat": 1.936, "final_bh": 1.676 }
    },
    "commodity": {
      "candidate": "GLD sma200",
      "verdict": "WEALTH_BEAT",
      "protocol_status": "0/10 gates complete; 1% wealth-margin gate applied",
      "sizing_allowed": false,
      "metrics": { "sharpe_strat": 1.139, "sharpe_bh": 0.927, "final_strat": 2.118, "final_bh": 2.007 }
    },
    "equities": {
      "candidate": "tactical-beta sleeve (SPY/QQQ/VTI>200dMA else SGOV)",
      "verdict": "DD_OVERLAY",
      "protocol_status": "benchmark sleeve; no alpha claim",
      "sizing_allowed": false,
      "metrics": { "sharpe_strat": 1.123, "sharpe_bh": 0.878, "final_strat": 1.856, "final_bh": 1.851 },
      "forward_alpha": {
        "candidate": "vwap-reversion-scout",
        "clock": { "n": 28, "target_n": 155, "t_stat": 1.99, "bar": 3.54, "status": "OPEN" }
      }
    },
    "bonds": {
      "verdict": "REJECT",
      "reason": "negative/weak Sharpe; loses wealth vs B&H",
      "sizing_allowed": false
    },
    "forex": {
      "verdict": "BLOCKED",
      "reason": "insufficient validated data (^DXY n=0)",
      "sizing_allowed": false
    },
    "prediction_markets": {
      "verdict": "REJECT",
      "reason": "structural: zero-sum, adverse selection, fees, size mismatch, PBO=0.603",
      "sizing_allowed": false
    }
  }
}
```

## Rules for the dashboard
1. **Never show a strategy as profitable unless `protocol_status` == "10/10 gates complete" and `verdict` == "PROVEN".**
2. Display `sizing_allowed:false` prominently for every non-PROVEN class.
3. Always show the benchmark comparison (strategy vs B&H of same asset) — no benchmark, no claim.
4. The forward-alpha clock is informational only; `OPEN` means no sizing.
5. Keep the empty-template `AUDIT_REPORT.md` fields populated per candidate as proof evidence.

## Wiring
Add a reader for this schema in `benchmark_proof.html` (or the audit dashboard) that renders the per-class verdict table. The data file can be generated from `reports/sma200_wealth_gate_backtest.json` + protocol outputs.
