# FUTURES research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the FUTURES research run at run_2026-08-08T06-17-45Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `futures_momentum_v1` (cerebras)
  - entry: At market close, compute 60-day total return for each ETF in ['DBC','GSG','DBA','USO','UNG','PDBC']; rank them descending. Open long positions in the top 2 ETFs and short positions in the bottom 2 ETFs. Positions are entered at the next day open.
  - exit: Close each position at the next day open when either (a) the ETF drops out of its respective top-2/bottom-2 rank, or (b) 30 calendar days have elapsed since entry, whichever comes first.
  - sizing: Allocate equal dollar amount to each leg; then scale the entire portfolio to target 8% annualized volatility using the 30-day rolling realized volatility of the portfolio (risk-parity scaling).
  - universe: ['DBC', 'GSG', 'DBA', 'USO', 'UNG', 'PDBC']
  - regime: Skip all trades on days when the CBOE Volatility Index (VIX) > 25 or when the NBER recession flag is active (US recession).
  - P3: PF=1.32 WR=30.0% MDD=33.5% Sharpe=0.11 n=10
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBC (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_carry_v1` (cerebras)
  - entry: For each ETF, compute the 30-day simple moving average (SMA30). Go long an ETF when its price is at least 1% below SMA30 (indicating potential positive roll-yield carry) and go short when its price is at least 1% above SMA30. Enter positions at next day open.
  - exit: Close the position at next day open when the price crosses back within ±0.5% of SMA30 or after 45 calendar days, whichever occurs first.
  - sizing: Equal dollar allocation per leg; apply risk-parity scaling to achieve a portfolio-wide target volatility of 10% annualized, using a 30-day rolling realized volatility estimate.
  - universe: ['DBC', 'GSG', 'DBA', 'USO', 'UNG', 'PDBC']
  - regime: Only trade during periods identified as economic expansions (NBER recession flag = false). Skip all days in recessions.
  - P3: PF=1.32 WR=30.0% MDD=33.5% Sharpe=0.11 n=10
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBC (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_regime_switch_v1` (cerebras)
  - entry: Determine macro regime daily: if NBER recession flag = false (expansion) use the momentum rule from futures_momentum_v1; if recession flag = true use the carry rule from futures_carry_v1. Enter positions at next day open accordingly.
  - exit: Apply the respective exit rule of the active sub-strategy (30-day rank change or 45-day SMA cross).
  - sizing: Risk-parity across all active legs targeting 9% annualized volatility, using a 30-day rolling realized volatility estimate.
  - universe: ['DBC', 'GSG', 'DBA', 'USO', 'UNG', 'PDBC']
  - regime: None beyond the regime definition; the strategy is inactive only when both expansion and recession flags are ambiguous (e.g., transition days).
  - P3: PF=1.02 WR=18.9% MDD=42.6% Sharpe=0.02 n=37
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBC (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_vol_target_momentum_v1` (cerebras)
  - entry: Compute 60-day total return for each ETF; go long the top 2 and short the bottom 2 ETFs. Positions are entered at next day open.
  - exit: Close each leg at next day open when the ETF exits its top-2/bottom-2 rank or after 20 calendar days, whichever occurs first.
  - sizing: Scale each leg so that the portfolio's 30-day rolling realized volatility equals a target of 10% annualized (volatility-targeting as in Harvey et al.).
  - universe: ['DBC', 'GSG', 'DBA', 'USO', 'UNG', 'PDBC']
  - regime: Skip trading on days when VIX > 30.
  - P3: PF=1.32 WR=30.0% MDD=33.5% Sharpe=0.11 n=10
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBC (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_pair_trend_v1` (cerebras)
  - entry: Form two pairs: (USO vs UNG) and (DBC vs GSG). For each pair, compute 30-day momentum for both ETFs; go long the ETF with higher momentum and short the other. Enter at next day open.
  - exit: Close the pair when the momentum difference reverses sign or after 40 calendar days, whichever occurs first.
  - sizing: Allocate equal risk to each pair; within each pair, size long and short legs equally. Apply portfolio-wide risk-parity scaling to target 9% annualized volatility (30-day rolling vol).
  - universe: ['DBC', 'GSG', 'USO', 'UNG']
  - regime: Skip trading on days when weekly change in US crude oil inventories exceeds 5 million barrels (proxy for market noise) or when VIX > 25.
  - P3: PF=1.02 WR=18.9% MDD=42.6% Sharpe=0.02 n=37
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBC (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_carry_vol_dbc_v1` (xai)
  - entry: long DBC when 60d carry signal (implied yield from futures curve) > 0 AND 30d realized volatility < 15%
  - exit: exit when carry signal flips negative OR after 60d hold period
  - sizing: fixed position size targeting 10% annualized volatility based on 30d historical vol
  - universe: ['DBC']
  - regime: skip when VIX > 25 OR 90d DBC volatility > 20%
  - P3: PF=1.02 WR=18.9% MDD=42.6% Sharpe=0.02 n=37
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBC (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_momentum_pdbc_v1` (xai)
  - entry: long PDBC when 120d momentum > 0 AND 60d momentum > 0
  - exit: exit when 60d momentum < 0 OR after 90d hold period
  - sizing: fixed position size targeting 10% annualized volatility based on 60d historical vol
  - universe: ['PDBC']
  - regime: skip when VIX > 30 OR 90d PDBC volatility > 25%
  - P3: PF=1.09 WR=33.3% MDD=42.0% Sharpe=0.07 n=48
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for PDBC (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_regime_dba_v1` (xai)
  - entry: long DBA when 60d momentum > 0 during economic expansion (based on 6m moving average of ISM PMI > 50)
  - exit: exit when momentum < 0 OR economic regime shifts to recession (ISM PMI < 50)
  - sizing: risk-parity allocation targeting 8% annualized volatility based on 60d historical vol
  - universe: ['DBA']
  - regime: skip during recession regime (ISM PMI < 50) OR when VIX > 30
  - P3: PF=1.52 WR=38.1% MDD=19.0% Sharpe=0.37 n=42
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBA (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_vol_target_uso_v1` (xai)
  - entry: long USO when 90d momentum > 0 AND adjust position to target 10% annualized volatility
  - exit: exit when momentum < 0 OR after 120d hold period
  - sizing: dynamic sizing to maintain constant 10% annualized volatility based on 30d historical vol
  - universe: ['USO']
  - regime: skip when VIX > 35 OR 90d USO volatility > 30%
  - P3: PF=1.07 WR=30.8% MDD=59.9% Sharpe=0.05 n=39
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for USO (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `futures_diagnostic_noedge_gsg_v1` (xai)
  - entry: long GSG when 60d momentum > 0 AND 30d volatility < 15%
  - exit: exit when momentum < 0 OR after 90d hold period
  - sizing: fixed position size targeting 10% annualized volatility based on 30d historical vol
  - universe: ['GSG']
  - regime: skip when VIX > 30 OR 90d GSG volatility > 25%
  - P3: PF=1.36 WR=40.0% MDD=34.4% Sharpe=0.24 n=40
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GSG (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


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
  "asset_class": "FUTURES",
  "run_id": "run_2026-08-08T06-17-45Z",
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
