# EQUITY research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the EQUITY research run at run_2026-06-06T07-09-12Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `equity_ts_momentum_v1` (cerebras)
  - entry: long ETF when 12M momentum > 0; i.e., if (price_today / price_252d_ago - 1) > 0 then go 100% long the ETF, else stay in cash
  - exit: exit when 12M momentum <= 0 or after 60 calendar days whichever comes first
  - sizing: risk-parity to target 10% annualized volatility: weight = 0.10 / (annualized_std_20d * sqrt(252))
  - universe: ['SPY', 'QQQ', 'IWM', 'VTI']
  - regime: skip if 20-day realized volatility of SPY > 30% (high-vol regime)
  - P3: PF=2.54 WR=47.1% MDD=20.6% Sharpe=0.76 n=17
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for SPY (1256 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `equity_vol_target_v1` (cerebras)
  - entry: always in market; set exposure = target_vol / recent_vol where target_vol = 10% annualized and recent_vol = annualized 20-day realized volatility of SPY
  - exit: no explicit exit; position weight is recomputed daily; if recent_vol > 40% set exposure to 0 (skip day)
  - sizing: exposure = min(1, target_vol / recent_vol)
  - universe: ['SPY']
  - regime: skip when 20-day realized volatility of SPY exceeds 40% (extreme market stress)
  - P3: PF=52.43 WR=100.0% MDD=18.8% Sharpe=0.87 n=3
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for SPY (1256 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `equity_carry_pair_v1` (cerebras)
  - entry: long VTI and short SPY when dividend_yield_spread = div_yield(VTI) - div_yield(SPY) > 0.5%; allocate equal dollar amount to each leg
  - exit: close both legs when dividend_yield_spread < 0.3% or after 90 calendar days, whichever occurs first
  - sizing: fixed dollar exposure of $10,000 per leg; net market exposure = 0 (market-neutral)
  - universe: ['VTI', 'SPY']
  - regime: skip when 20-day realized volatility of SPY > 35% (high-vol regime)
  - P3: PF=5.61 WR=80.0% MDD=19.3% Sharpe=0.85 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for VTI (1256 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `equity_hmm_momentum_v1` (cerebras)
  - entry: if HMM bull probability (computed on 60-day rolling window of SPY returns) > 0.6 AND 12M momentum of QQQ > 0 then go 100% long QQQ
  - exit: exit when bull probability falls below 0.6 OR 12M momentum of QQQ <= 0
  - sizing: risk-parity to target 9% annualized volatility based on QQQ 20-day realized vol
  - universe: ['QQQ']
  - regime: skip when bull probability < 0.6 (i.e., bear regime)
  - P3: PF=3.49 WR=52.4% MDD=14.1% Sharpe=0.78 n=21
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for QQQ (1256 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `equity_bab_pair_v1` (cerebras)
  - entry: compute 60-day beta of each ETF relative to SPY; rank ETFs; long the lowest-beta ETF (typically VTI) and short the highest-beta ETF (typically QQQ) when beta_spread = beta_high - beta_low > 0.2; allocate equal dollar amount to each leg
  - exit: close both legs when beta_spread <= 0.1 or after 60 calendar days
  - sizing: fixed $15,000 per leg; net market exposure = 0 (beta-neutral)
  - universe: ['VTI', 'QQQ']
  - regime: skip when 20-day realized volatility of SPY > 30% (high-vol regime)
  - P3: PF=4.24 WR=85.7% MDD=25.4% Sharpe=0.69 n=7
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for VTI (1256 bars). Signal: breakout (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


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
  "asset_class": "EQUITY",
  "run_id": "run_2026-06-06T07-09-12Z",
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
