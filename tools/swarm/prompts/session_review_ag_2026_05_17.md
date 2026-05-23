# Session AG Review — 2026-05-17

## Context
Continuation of autonomous trading-edge improvement session. Follows Session AF (bond_connors_rsi2 backtest, COT dead-field discovery).

## Deliverables This Session

### 1. Equity Baby Strategies Backtest (M-077)

Created `tools/equity_baby_strategies_backtest.py`:
- Backtested `equity_vix_regime_momentum` and `equity_sector_rotation_momentum` from `baby_strategies` package
- Both use EXPIRED-excluded WR/PF methodology (aligned with shadow tracker)
- 30-bar max hold before marking EXPIRED; no overlapping positions per symbol (next_entry_bar tracking)

Results (2010-01-01 → 2026-05-17):

**equity_vix_regime_momentum** (SPY/QQQ/IWM, VIX term structure + SMA50 + 21d momentum, TP=6% SL=4%):
```
n_closed=448  n_expired=156  WR=40.6%  PF=1.03  MDD=0.23%  Sharpe=0.20
```
→ Sub-T2 (WR<50%, PF<1.5). Break-even. Do NOT promote to sizing.

**equity_sector_rotation_momentum** (11 sector ETFs, dual 1M+3M momentum, SPY SMA200 regime, TP=8% SL=5%):
```
n_closed=313  n_expired=403  WR=32.0%  PF=0.75  MDD=0.48%  Sharpe=-2.22
```
→ Losing strategy. WR=32% well below T2 floor. Do NOT deploy. Block from MONEY_READY.

Output: `audit_dashboard/data/equity_baby_strategies_backtest.json`

### 2. FOOLPROOF_ACTION_PLAN Audit — 5 Items Marked Done/Superseded

- **quan_engine 12% cap** → [x] superseded: fully BLOCKED in BLOCKED_SOURCE_SYSTEMS (quality_gates.py:1307)
- **confidence inversion 0.85+** → [~] partial: M-035 blocks CRYPTO confidence >0.90 (default ON); M-034 covers 0.85-0.90 but OFF by default; gap remains for 0.85-0.90 range
- **ml_crypto_predictor below 0.70** → [x] superseded: LONG fully BLOCKED; SHORT whitelisted to profitable pairs only
- **FOREX SHORT-only gate** → [x] superseded: ALL FOREX LONG picks hard-blocked (quality_gates.py:6461)
- **equity baby strategies backtest** → [x] done with results above

## Review Questions

1. **High expired rate in sector_rotation (403/716 = 56%)**: More than half of sector rotation
   picks expire without reaching TP or SL within 30 bars. This suggests the TP=8% target is
   too ambitious for the 30-bar holding window, or the sector rotation signals occur when
   markets are range-bound. Should the max_hold_bars be extended to 60+ to match rotation
   strategy timeframes?

2. **VIX regime WR=40.6% — below 50% despite published edge claims**: The baby_strategies
   implementation uses VIX contango as the entry trigger. The poor backtest result (below
   50% WR) may indicate the signal is too slow (daily bars) vs. the theoretical edge that
   works at hourly resolution. Should the strategy be retested on 4H bars?

3. **Sector rotation SHORT bias issue**: In bearish regime (SPY < SMA200), the strategy
   shorts the bottom sectors with negative momentum. This produced WR=32% — shorting
   sectors in a bear market may have worked briefly (2020 crash) but the bull market
   dominance (2010-2026) makes this branch rarely profitable. Should the bearish leg
   be disabled entirely?

4. **M-034 confidence inversion gate (0.85-0.90 range, OFF by default)**: The gap between
   M-035 (>0.90 blocked) and M-034 (0.85-0.90, OFF) means picks with confidence 0.85-0.90
   from super_signals/luxalgo can still pass. After 2 days of shadow (2026-05-15 deploy),
   has enough data accumulated to enable M-034? Or should the threshold be raised to 0.90
   to avoid a configuration toggle?

5. **backtest position blocking uses spy-timeline bar index for sector symbols**: In sector
   rotation, next_entry_bar_by_sym tracks position availability in the SPY timeline index (i),
   not the per-symbol dataframe index (idx). This can cause early re-entry if SPY dates and
   sector ETF dates diverge (e.g., SPY has 252 bars/year, XLK has 251). Is this a meaningful
   source of bias?

## Output Format Required
Provide a JSON assessment:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment
