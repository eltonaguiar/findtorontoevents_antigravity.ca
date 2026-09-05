# COMMODITY research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the COMMODITY research run at run_2026-09-05T06-17-52Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `commodity_ts_momentum_gold_v1` (cerebras)
  - entry: long GLD when 30d return > 0 AND 60d SMA of GLD is rising
  - exit: close position when 30d return <= 0 OR after 90 days
  - sizing: allocate 2% of portfolio equity to each GLD trade (fixed fractional)
  - universe: ['GLD']
  - regime: skip when 30d rolling volatility of GLD > 2.0%
  - P3: PF=11.66 WR=66.7% MDD=18.5% Sharpe=1.09 n=15
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_cross_sectional_momentum_v1` (cerebras)
  - entry: at month start compute 60d total return for each ETF in ['GLD','SLV','PPLT','PALL','CPER','DBA']; go long top 2 and short bottom 2
  - exit: rebalance monthly, closing all positions at month end
  - sizing: equal risk weight to each leg targeting 10% annualized portfolio volatility
  - universe: ['GLD', 'SLV', 'PPLT', 'PALL', 'CPER', 'DBA']
  - regime: skip month when 30d rolling volatility of SPY > 1.5%
  - P3: PF=11.66 WR=66.7% MDD=18.5% Sharpe=1.09 n=15
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_carry_value_gold_silver_v1` (cerebras)
  - entry: long GLD when price < 0.95 * 200d SMA AND short GLD when price > 1.05 * 200d SMA; same rule for SLV
  - exit: close when price crosses its 200d SMA
  - sizing: fixed 1% of portfolio equity per leg (long or short)
  - universe: ['GLD', 'SLV']
  - regime: skip when 30d rolling volatility of GLD or SLV > 2.5%
  - P3: PF=11.22 WR=25.0% MDD=26.2% Sharpe=0.8 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_energy_momentum_carry_v1` (cerebras)
  - entry: long CPER when 30d return > 0 AND CPER price > 12-month SMA (proxy for backwardation)
  - exit: close when 30d return <= 0 OR CPER price falls below 12-month SMA
  - sizing: scale to target 8% annualized portfolio volatility
  - universe: ['CPER']
  - regime: skip when VIX (proxied by 30d SPY volatility) > 25
  - P3: PF=2.68 WR=60.0% MDD=24.8% Sharpe=0.4 n=10
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for CPER (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_agri_momentum_value_v1` (cerebras)
  - entry: long DBA when 60d return > 0 AND DBA price < 0.97 * 200d SMA
  - exit: close when 60d return <= 0 OR price crosses above 200d SMA
  - sizing: fixed 2% of portfolio equity per trade
  - universe: ['DBA']
  - regime: skip when 30d rolling volatility of DBA > 2.0% OR when 30d SPY volatility > 1.5%
  - P3: PF=1.61 WR=39.5% MDD=19.0% Sharpe=0.43 n=43
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBA (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


## Tier-2 floor (CLAUDE.md MAJOR GOAL)

PF ≥ 1.5, WR ≥ 50%, MDD < 20%, n ≥ 100 trades.

## Your mandate

Vote GO / MIXED / NO_EDGE per candidate. For GO verdicts, draft a Wiring Plan (per CLAUDE.md Wire-Up Rule) — what file gets the caller, what trust_score to seed, what feature flag gates it.

If most candidates fail T2 floor (esp. n<100), the run-level verdict should be MIXED or NO_EDGE — DO NOT fabricate GO just because backtest PF is high. n<30 is too small for any reliable verdict; flag as "needs longer history" rather than GO.

## Output schema (JSON-strict)

```json
{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "COMMODITY",
  "run_id": "run_2026-09-05T06-17-52Z",
  "synthesis": [
    {
      "spec_id": "<from list above>",
      "verdict": "GO|MIXED|NO_EDGE",
      "rationale": "1-3 sentences citing PF/WR/MDD/n + cross-test + simplified-signal caveat",
      "wiring_plan": "if GO: paste-ready 1-paragraph wiring plan. else empty string."
    }
  ],
  "run_verdict": "GO|MIXED|NO_EDGE",
  "run_rationale": "1-paragraph overall — what edge surfaced (if any), what's blocked on n / faithful-signal, retry conditions"
}
```

Return ONLY the JSON object. No prose preamble, no markdown fence.
