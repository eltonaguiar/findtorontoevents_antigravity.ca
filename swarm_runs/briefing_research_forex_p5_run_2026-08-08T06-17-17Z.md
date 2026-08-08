# FOREX research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the FOREX research run at run_2026-08-08T06-17-17Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `forex_momentum_uup_v1` (cerebras)
  - entry: long UUP when 60d momentum > 0 AND 90d realized volatility of UUP < 8%
  - exit: exit when 60d momentum flips sign OR after 30 calendar days, whichever comes first
  - sizing: allocate full capital (100%) to the position; risk-adjusted size = 1 / rolling 60d volatility of UUP to target 8% annualized vol
  - universe: ['UUP']
  - regime: skip trade on any day where 90d realized volatility of UUP > 12% (high-vol regime)
  - P3: PF=1.33 WR=41.5% MDD=14.4% Sharpe=0.36 n=53
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for UUP (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `forex_value_momentum_combo_fxA_v1` (cerebras)
  - entry: compute value = log(price / 200d SMA) and momentum = 20d return of FXA; combined_signal = 0.5*value + 0.5*momentum; go long FXA when combined_signal > 0
  - exit: exit when combined_signal ≤ 0 OR after 60 calendar days, whichever occurs first
  - sizing: risk-parity: position size = 1 / rolling 60d volatility of FXA to target 8% annualized vol
  - universe: ['FXA']
  - regime: skip when 30d realized volatility of UUP (proxy for global risk) > 10%
  - P3: PF=0.54 WR=25.7% MDD=21.6% Sharpe=-0.41 n=35
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for FXA (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `forex_regime_conditional_hybrid_fxA_v1` (cerebras)
  - entry: if UUP 30d return > 0 (expansion regime) AND FXA 30d momentum > 0 then go long FXA; otherwise stay in cash
  - exit: exit when either condition fails or after 45 calendar days, whichever comes first
  - sizing: risk-parity: position size = 1 / rolling 60d volatility of FXA to target 8% annualized vol
  - universe: ['FXA']
  - regime: skip when 90d realized volatility of UUP > 12% (high-vol regime)
  - P3: PF=0.54 WR=25.7% MDD=21.6% Sharpe=-0.41 n=35
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for FXA (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `forex_dollar_carry_uup_v1` (cerebras)
  - entry: compute spread = UUP 30d return - FXE 30d return; if spread > 0 AND UUP 30d momentum > 0 then go long UUP; else stay in cash
  - exit: exit when spread ≤ 0 OR after 30 calendar days, whichever occurs first
  - sizing: risk-parity: position size = 1 / rolling 60d volatility of UUP to target 8% annualized vol
  - universe: ['UUP', 'FXE']
  - regime: skip when spread < 0.5% over the past 30 days (compressed yield differential) OR when 90d realized volatility of UUP > 12%
  - P3: PF=1.33 WR=41.5% MDD=14.4% Sharpe=0.36 n=53
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for UUP (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `forex_risk_parity_multi_etf_v1` (cerebras)
  - entry: daily compute 60d covariance of returns of [UUP, FXE, FXA, FXB, FXF]; solve for weights that equalize risk contributions to achieve 8% annualized portfolio volatility; rebalance on the first trading day of each month
  - exit: no explicit exit; positions are held until next monthly rebalance; if regime filter triggers, set all weights to zero for that month
  - sizing: risk-parity weights as described in entry; target portfolio volatility = 8% annualized
  - universe: ['UUP', 'FXE', 'FXA', 'FXB', 'FXF']
  - regime: skip (set all weights to zero) on any month where the portfolio's 60d realized volatility exceeds 15% (high-risk regime)
  - P3: PF=1.33 WR=41.5% MDD=14.4% Sharpe=0.36 n=53
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for UUP (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


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
  "asset_class": "FOREX",
  "run_id": "run_2026-08-08T06-17-17Z",
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
