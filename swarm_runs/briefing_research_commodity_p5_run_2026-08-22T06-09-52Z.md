# COMMODITY research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the COMMODITY research run at run_2026-08-22T06-09-52Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `commodity_ts_momentum_gold_v1` (cerebras)
  - entry: long GLD when 30d return > 0 AND 60d SMA of GLD is rising
  - exit: close position when 30d return <= 0 OR after 90 days
  - sizing: allocate 2% of portfolio equity to each GLD trade (fixed fractional)
  - universe: ['GLD']
  - regime: skip when 30d rolling volatility of GLD > 2.0%
  - P3: PF=9.12 WR=62.5% MDD=18.5% Sharpe=1.08 n=16
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_cross_sectional_momentum_v1` (cerebras)
  - entry: at month start compute 60d total return for each ETF in ['GLD','SLV','PPLT','PALL','CPER','DBA']; go long top 2 and short bottom 2
  - exit: rebalance monthly, closing all positions at month end
  - sizing: equal risk weight to each leg targeting 10% annualized portfolio volatility
  - universe: ['GLD', 'SLV', 'PPLT', 'PALL', 'CPER', 'DBA']
  - regime: skip month when 30d rolling volatility of SPY > 1.5%
  - P3: PF=9.12 WR=62.5% MDD=18.5% Sharpe=1.08 n=16
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_carry_value_gold_silver_v1` (cerebras)
  - entry: long GLD when price < 0.95 * 200d SMA AND short GLD when price > 1.05 * 200d SMA; same rule for SLV
  - exit: close when price crosses its 200d SMA
  - sizing: fixed 1% of portfolio equity per leg (long or short)
  - universe: ['GLD', 'SLV']
  - regime: skip when 30d rolling volatility of GLD or SLV > 2.5%
  - P3: PF=10.16 WR=25.0% MDD=26.2% Sharpe=0.79 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_energy_momentum_carry_v1` (cerebras)
  - entry: long CPER when 30d return > 0 AND CPER price > 12-month SMA (proxy for backwardation)
  - exit: close when 30d return <= 0 OR CPER price falls below 12-month SMA
  - sizing: scale to target 8% annualized portfolio volatility
  - universe: ['CPER']
  - regime: skip when VIX (proxied by 30d SPY volatility) > 25
  - P3: PF=2.43 WR=54.5% MDD=24.8% Sharpe=0.38 n=11
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for CPER (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_agri_momentum_value_v1` (cerebras)
  - entry: long DBA when 60d return > 0 AND DBA price < 0.97 * 200d SMA
  - exit: close when 60d return <= 0 OR price crosses above 200d SMA
  - sizing: fixed 2% of portfolio equity per trade
  - universe: ['DBA']
  - regime: skip when 30d rolling volatility of DBA > 2.0% OR when 30d SPY volatility > 1.5%
  - P3: PF=1.49 WR=37.2% MDD=19.0% Sharpe=0.34 n=43
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBA (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_ts_momentum_v1` (deepseek)
  - entry: long GLD when 12-month (252d) return > 0 AND 1-month (21d) return > 0; short GLD when 12-month return < 0 AND 1-month return < 0
  - exit: exit on 12-month momentum sign flip or 60 trading day hold (whichever first)
  - sizing: fixed 100% of capital per signal (long or short), no leverage
  - universe: ['GLD']
  - regime: skip when GLD 90-day realized volatility > 25% annualized (avoid extreme vol regimes)
  - P3: PF=10.16 WR=25.0% MDD=26.2% Sharpe=0.79 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_carry_gold_v1` (deepseek)
  - entry: long GLD when 3-month futures curve slope (proxied by GLD price vs 3-month forward price from ETF structure) is backwardated (slope > 0); short when contango (slope < 0)
  - exit: exit on carry sign flip or 30 trading day hold
  - sizing: fixed 100% of capital per signal
  - universe: ['GLD']
  - regime: skip when GLD 60-day average daily volume < 5 million shares (low liquidity regime)
  - P3: PF=10.16 WR=25.0% MDD=26.2% Sharpe=0.79 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_value_agriculture_v1` (deepseek)
  - entry: long DBA when 5-year price relative to 200-day moving average < 0.8 (cheap); short DBA when 5-year price relative to 200-day moving average > 1.2 (expensive)
  - exit: exit when price reverts to 0.95-1.05 of 200-day MA or 90 trading day hold
  - sizing: fixed 100% of capital per signal
  - universe: ['DBA']
  - regime: skip when DBA 200-day volatility > 30% annualized (avoid extreme agricultural shocks)
  - P3: PF=2.51 WR=72.2% MDD=13.0% Sharpe=0.56 n=18
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for DBA (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_momentum_cross_sectional_v1` (deepseek)
  - entry: long top 2 commodities by 12-month momentum (GLD, SLV, PPLT, PALL, CPER, DBA); short bottom 2 by 12-month momentum; equal-weight long/short
  - exit: rebalance monthly; exit all positions on rebalance day
  - sizing: equal-weight long/short, each leg 50% of capital (net zero beta)
  - universe: ['GLD', 'SLV', 'PPLT', 'PALL', 'CPER', 'DBA']
  - regime: skip when average cross-sectional dispersion of 12-month returns across universe < 5% (low momentum dispersion regime)
  - P3: PF=9.12 WR=62.5% MDD=18.5% Sharpe=1.08 n=16
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `commodity_carry_momentum_combined_v1` (deepseek)
  - entry: long GLD when both 12-month momentum > 0 AND carry (proxied by 3-month forward curve slope) > 0; short when both < 0; else flat
  - exit: exit on either momentum or carry sign flip, or 45 trading day hold
  - sizing: fixed 100% of capital per signal
  - universe: ['GLD']
  - regime: skip when GLD 30-day correlation to SPY > 0.7 (high equity beta regime reduces commodity-specific edge)
  - P3: PF=9.12 WR=62.5% MDD=18.5% Sharpe=1.08 n=16
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for GLD (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


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
  "run_id": "run_2026-08-22T06-09-52Z",
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
