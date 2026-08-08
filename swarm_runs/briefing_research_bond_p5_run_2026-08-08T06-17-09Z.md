# BOND research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the BOND research run at run_2026-08-08T06-17-09Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `bond_momentum_longshort_v1` (cerebras)
  - entry: if (pct_change(TLT, 60) > 0) and (pct_change(TLT, 60) > pct_change(SHY, 60)) then go long TLT and short SHY
  - exit: close both legs after 30 calendar days or when pct_change(TLT, 60) < 0
  - sizing: scale the long and short legs to achieve an annualized portfolio volatility of 8% (risk-parity scaling)
  - universe: ['TLT', 'SHY']
  - regime: skip when VIX > 25
  - P3: PF=0.0 WR=0.0% MDD=12.6% Sharpe=-0.3 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TLT (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_term_premium_slope_v1` (cerebras)
  - entry: if (yield(TLT) - yield(SHY) > median(yield(TLT)-yield(SHY)) + 1*std(yield(TLT)-yield(SHY))) then go long TLT
  - exit: close when the spread falls below its median or after 60 days, whichever comes first
  - sizing: target 6% annualized volatility; position size = target_vol / recent_60d_vol(TLT)
  - universe: ['TLT', 'SHY']
  - regime: skip when US recession indicator (e.g., NBER recession flag) is true
  - P3: PF=0.0 WR=0.0% MDD=12.6% Sharpe=-0.3 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TLT (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_liquidity_spread_v1` (cerebras)
  - entry: if (yield(TLT) - yield(BND) > median_spread + 0.5*std_spread) then go long TLT and short BND
  - exit: close when spread reverts to median or after 45 days
  - sizing: risk-parity to 7% annualized volatility across the two legs
  - universe: ['TLT', 'BND']
  - regime: skip when VIX > 30 or when 30-day Treasury liquidity index (proxy: ADV of TLT) falls below its 20-day moving average
  - P3: PF=0.0 WR=0.0% MDD=12.6% Sharpe=-0.3 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TLT (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_regime_duration_v1` (cerebras)
  - entry: if (rolling_std(TLT, 60) < low_vol_threshold) then allocate 100% to TLT else allocate 30% to TLT and 70% to SHY
  - exit: re-balance monthly; switch allocations whenever the volatility regime flips
  - sizing: scale total exposure to target 8% annualized portfolio volatility
  - universe: ['TLT', 'SHY']
  - regime: skip when VIX > 25
  - P3: PF=0.0 WR=0.0% MDD=12.6% Sharpe=-0.3 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TLT (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_credit_spread_term_v1` (cerebras)
  - entry: if (yield(HYG) - yield(LQD) > median_spread + 1*std_spread) then go long LQD and short HYG
  - exit: close when spread narrows to median or after 40 days
  - sizing: risk-parity to 7% annualized volatility across the long and short legs
  - universe: ['LQD', 'HYG']
  - regime: skip when US corporate credit default swap index (proxy: CBOE IG CDS) exceeds its 30-day moving average
  - P3: PF=1.05 WR=36.4% MDD=7.9% Sharpe=0.03 n=11
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for LQD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_inflation_rotation_v1` (cerebras)
  - entry: if (yield(TIP) - yield(TLT) > median_spread + 0.75*std_spread) then go long TIP and short TLT
  - exit: close when the spread falls below median or after 35 days
  - sizing: target 6% annualized volatility; scale positions using recent 60-day vol of TIP
  - universe: ['TIP', 'TLT']
  - regime: skip when CPI YoY growth > 4% (high-inflation regime) or when VIX > 30
  - P3: PF=1.69 WR=42.9% MDD=5.5% Sharpe=0.33 n=14
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TIP (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_momentum_cross_country_v1` (deepseek)
  - entry: long IEF when 12-month total return > 0 AND 12-month total return > median of all bond ETFs in universe; short TLT when 12-month total return < 0 AND 12-month total return < median of all bond ETFs in universe
  - exit: exit long when 12-month total return drops below 0; exit short when 12-month total return rises above 0; or after 60 trading days, whichever comes first
  - sizing: equal risk-weight: target 10% annualized vol per position, cap at 20% of portfolio per position
  - universe: ['IEF', 'TLT', 'SHY', 'IEI', 'TIP', 'LQD', 'VCIT', 'VCSH', 'HYG', 'BND', 'TIPS', 'MBB', 'AGG']
  - regime: skip when 10-year US Treasury yield < 1.0% (zero-lower-bound distortion) OR when VIX > 30 (flight-to-quality regime)
  - P3: PF=0.84 WR=37.5% MDD=8.5% Sharpe=-0.05 n=8
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for IEF (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_liquidity_premium_on_off_v1` (deepseek)
  - entry: long LQD (liquid corporate) when spread between LQD yield and VCIT yield > 0.5% (liquidity premium high); short VCIT when same condition; reverse when spread < -0.2%
  - exit: exit long when spread drops below 0.2%; exit short when spread rises above -0.1%; or after 30 trading days
  - sizing: equal dollar notional long/short, target 8% annualized vol for the pair
  - universe: ['LQD', 'VCIT']
  - regime: skip when VIX > 28 (liquidity dry-up distorts on/off spreads) OR when corporate bond market stress indicator (e.g., CDX IG spread > 150bp)
  - P3: PF=1.05 WR=36.4% MDD=7.9% Sharpe=0.03 n=11
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for LQD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_macro_factor_duration_v1` (deepseek)
  - entry: long IEF when macro factor composite (z-score of industrial production growth + inflation + financial conditions index) > 0.5 (expansion); short IEF when composite < -0.5 (contraction)
  - exit: exit long when composite drops below 0; exit short when composite rises above 0; or after 90 trading days
  - sizing: linear: position size = composite_zscore * 0.3 of portfolio, capped at 40% per side
  - universe: ['IEF', 'SHY', 'TLT']
  - regime: skip when macro data release is within 3 trading days (avoid look-ahead bias) OR when any macro component is missing (use last available)
  - P3: PF=0.9 WR=73.3% MDD=12.2% Sharpe=-0.04 n=15
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for IEF (1255 bars). Signal: mean_reversion_zscore (keyword-routed from spec.entry). LLM-driven signal translation queued f

### `bond_regime_switching_duration_v1` (deepseek)
  - entry: long TLT when Markov-switching model signals low-volatility regime (probability > 0.7); long SHY when high-volatility regime (probability > 0.7); hold cash when probabilities are ambiguous (0.3-0.7)
  - exit: exit when regime probability crosses below 0.5 for current position; re-evaluate weekly
  - sizing: full allocation to signaled regime: 100% TLT in low-vol, 100% SHY in high-vol, 0% in ambiguous
  - universe: ['TLT', 'SHY']
  - regime: skip when 10-year yield < 0.5% (ZLB distorts volatility regimes) OR when regime probability is stuck >0.9 for >60 days (model overfitting)
  - P3: PF=0.0 WR=0.0% MDD=12.6% Sharpe=-0.3 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TLT (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_momentum_cross_v1` (xai)
  - entry: long the top 2 ETFs from [IEF, TLT, IEI] based on 60-day price momentum when momentum > 0
  - exit: exit when momentum falls below 0 or after 30-day hold period
  - sizing: equal weight across selected ETFs, targeting 10% annualized volatility
  - universe: ['IEF', 'TLT', 'IEI']
  - regime: skip when VIX > 20
  - P3: PF=0.42 WR=18.5% MDD=14.4% Sharpe=-0.58 n=27
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for IEF (1255 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_term_premium_v1` (xai)
  - entry: long TLT when estimated 10-year term premium (based on yield curve slope 10y-2y) is in top 20% of historical values over past 5 years
  - exit: exit when term premium drops below 50th percentile or after 60-day hold
  - sizing: fixed 100% allocation to TLT, scaled to 8% annualized volatility
  - universe: ['TLT']
  - regime: skip during NBER recession periods
  - P3: PF=0.0 WR=0.0% MDD=12.6% Sharpe=-0.3 n=5
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for TLT (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_liquidity_premium_v1` (xai)
  - entry: long IEF and short SHY when the yield spread between intermediate and short-term Treasuries widens by more than 1 standard deviation over past 120 days
  - exit: exit when spread narrows to mean or after 45-day hold
  - sizing: dollar-neutral long-short position, targeting 6% annualized volatility
  - universe: ['IEF', 'SHY']
  - regime: skip when 3-month Treasury yield > 2%
  - P3: PF=0.84 WR=37.5% MDD=8.5% Sharpe=-0.05 n=8
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for IEF (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `bond_credit_spread_v1` (xai)
  - entry: long LQD when corporate credit spread (LQD yield minus IEF yield) is in top 25% of historical range over past 3 years
  - exit: exit when spread falls below 50th percentile or after 60-day hold
  - sizing: fixed 100% allocation to LQD, targeting 7% annualized volatility
  - universe: ['LQD', 'IEF']
  - regime: skip when default risk premium (HYG yield minus LQD yield) > 5%
  - P3: PF=1.05 WR=36.4% MDD=7.9% Sharpe=0.03 n=11
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for LQD (1255 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


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
  "asset_class": "BOND",
  "run_id": "run_2026-08-08T06-17-09Z",
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
