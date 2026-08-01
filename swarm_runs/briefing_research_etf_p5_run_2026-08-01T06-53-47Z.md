# ETF research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the ETF research run at run_2026-08-01T06-53-47Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `etf_carry_yield_v1` (cerebras)
  - entry: At month-end, compute trailing 12-month dividend yield for each ETF in the universe; rank them. Go long the top 3 yield ETFs and short the bottom 3 yield ETFs. Enter positions at the next day open.
  - exit: Close all positions at the next month-end (i.e., hold for ~1 month).
  - sizing: Allocate equal dollar amount to each long and short leg; target portfolio volatility of 8% annualized using a rolling 60-day volatility estimate of the long-short spread.
  - universe: ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
  - regime: Skip the month if the 30-day realized volatility of SPY (proxy for market risk) exceeds 20% or if the 60-day SPY momentum is negative.
  - P3: PF=73.85 WR=75.0% MDD=17.0% Sharpe=0.92 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for XLK (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `etf_spread_arbitrage_v1` (cerebras)
  - entry: Compute the daily spread S = XLF_price - XLE_price. Calculate its 60-day rolling mean μ and standard deviation σ. When S < μ - 2σ, go long XLF and short XLE; when S > μ + 2σ, go long XLE and short XLF. Enter at next day open.
  - exit: Close the pair when the spread reverts to within 0.5σ of μ or after a maximum holding period of 20 trading days, whichever comes first.
  - sizing: Risk-scale each trade to target 1% of portfolio equity per pair, using the 20-day rolling volatility of the spread to set position size.
  - universe: ['XLF', 'XLE']
  - regime: Skip trading on days when the VIX (proxy from ^VIX) exceeds 30 or when the 10-day average volume of either ETF falls below its 30-day median (liquidity filter).
  - P3: PF=2.17 WR=66.7% MDD=19.7% Sharpe=0.49 n=12
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for XLF (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `etf_cross_asset_momentum_v1` (cerebras)
  - entry: At month-end, compute 60-day total return for each ETF in the universe. Rank them and go long the top 4 performers, short the bottom 4 performers. Enter at next day open.
  - exit: Rebalance monthly; close all positions at month-end and re-enter based on updated rankings.
  - sizing: Allocate equal capital to each long and short leg; apply a portfolio-level volatility target of 10% annualized using a 60-day rolling volatility of the long-short basket.
  - universe: ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
  - regime: Skip the month if the 30-day realized volatility of the MSCI World Index (proxy via VTI) exceeds 18% or if the 60-day momentum of the S&P 500 is negative.
  - P3: PF=73.85 WR=75.0% MDD=17.0% Sharpe=0.92 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for XLK (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `etf_value_momentum_combo_v1` (cerebras)
  - entry: For each ETF, compute (a) trailing 12-month dividend yield and (b) 60-day total return. Standardize both metrics across the universe and sum to obtain a combined score. Go long the top 3 scoring ETFs and short the bottom 3. Enter at next day open after month-end ranking.
  - exit: Hold positions for 30 calendar days or until the combined score rank changes by more than 2 positions, whichever occurs first.
  - sizing: Equal dollar allocation per leg; scale to a target portfolio volatility of 9% annualized using a 30-day rolling volatility of the long-short spread.
  - universe: ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
  - regime: Skip the month if the 20-day average VIX exceeds 28 or if the 30-day realized volatility of the Bloomberg US Aggregate Bond Index (proxy via BND) exceeds 10%.
  - P3: PF=73.85 WR=75.0% MDD=17.0% Sharpe=0.92 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for XLK (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `etf_diagnostic_momentum_v1` (cerebras)
  - entry: Go long any ETF whose 60-day total return is positive at month-end; otherwise stay in cash.
  - exit: Reassess monthly; exit any position whose 60-day return turns negative.
  - sizing: Allocate up to 100% of capital to the single longest-positive-momentum ETF; if none, stay fully in cash.
  - universe: ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
  - regime: Skip the month if the 30-day realized volatility of SPY exceeds 22% (high-vol regime) to avoid noisy signals.
  - P3: PF=73.85 WR=75.0% MDD=17.0% Sharpe=0.92 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for XLK (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


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
  "asset_class": "ETF",
  "run_id": "run_2026-08-01T06-53-47Z",
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
