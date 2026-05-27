# EAGLE: Range-Bound Analysis — Symbols Oscillating Between Two Prices
**Date:** 2026-05-27 02:26 EST | **Model:** Claude Opus 4.7 (via CommandCode)
**Branch:** `feat/EAGLE-2026-05-27-end-to-end-review`

---

## Executive Summary

**Finding:** 3 symbols/asset-class pairs exhibit persistent oscillation between identifiable price bands, driven by structural factors (interest rate differential, yield curve, VWAP reversion). The most actionable is FOREX AUDUSD=X (carry-driven mean-reversion). CRYPTO BTC/ETH also oscillate around VWAP during range-bound DXY regimes but break during trends. ETF TLT/IEF has yield-curve-driven oscillation with documented TSMOM edge.

**Risk:** No oscillation is a "sure thing." All three break during regime shifts. Position sizing + regime gate are mandatory.

---

## 1. FOREX AUDUSD=X — Carry-Driven Oscillation (Most Actionable)

### Mechanics
AUDUSD oscillates because:
- **Interest rate differential** between RBA (AUD) and Fed (USD) creates persistent mean-reversion
- When AUD rate > USD rate → carry trade inflows → AUDUSD rises
- When USD strengthens (DXY up) or risk-off → AUDUSD falls
- The 1.5-2% rate differential band creates a natural ceiling/floor

### Evidence from Mutation Autopsy
- AUDUSD SHORT: PF=3.55, n=11 (exploiting overbought/oversold extremes)
- AUDJPY SHORT: PF=2.45 (carry unwind on JPY crosses)
- MeanReversionBB: PF=2.09, n=44 (bollinger band reversion across FX)

### Entry/Exit Framework
| Parameter | Value |
|---|---|
| Entry (SHORT) | RSI(14)<30 on 4H + DXY 1D EMA20 < EMA50 (USD weak → AUD strong → SHORT the overbought) |
| Entry (LONG) | RSI(14)>70 on 4H + DXY 1D EMA20 > EMA50 (USD strong → AUD weak → LONG the oversold) |
| TP | 0.8% (~0.0050 on typical 0.6200-0.6800 range) |
| SL | 0.5% |
| Max hold | 3 days |
| Session | London/NY overlap (08-16 UTC) |
| NOT during | NFP, FOMC, RBA rate decision ±2h |

### Expected Performance
- WR estimated: 52-58% (mean-reversion with structural driver)
- PF estimated: 1.3-1.5 (small wins, tight risk)
- n/year: 40-60 trades (oscillation frequency ~weekly)
- Regime risk: BREAKS when DXY in strong trend (breakout, not oscillation)

### Status
- FOREX HARD_DISABLE currently blocks ALL FOREX
- Requires exemption: SHORT-only sleeve + DXY confluence gate
- Paper first (30d, n≥30) before any sizing

---

## 2. CRYPTO BTCUSDT/ETHUSDT — VWAP Oscillation During Range-Bound DXY

### Mechanics
BTC/ETH oscillate ±3-5% around VWAP during range-bound DXY regimes. The pattern:
- Weekday range: typically ±3-5% of opening price
- Support/resistance at round numbers ($87k, $88k, $89k for BTC)
- Funding rate flips signal exhaustion: high positive funding → mean-revert down; negative funding → mean-revert up
- The oscillation BREAKS during DXY trend moves (BTC follows DXY inversely)

### Evidence
- Connors RSI2 on BTC: documented 75%+ WR on SPY/QQQ pattern (transfers to BTC as most liquid)
- On-chain MVRV-Z: LONG when <-0.5 (undervalued), SHORT when >2.0 (overvalued) — but synthetic backtest PF only 1.28
- UTC-hour filter (M-001): rejects 08-09 UTC (death zone), boosts 22 UTC — supports intraday oscillation thesis

### Entry/Exit Framework
| Parameter | Value |
|---|---|
| Entry (LONG) | Connors RSI(2)<5 + BTC above 200 SMA + DXY 4H neutral (±0.5% range) |
| Entry (SHORT) | Connors RSI(2)>95 + funding rate >0.05% + DXY 4H neutral |
| TP | 2% |
| SL | 1.5% |
| Max hold | 48 hours |
| Session | Skip 06-09 UTC, boost 22 UTC |
| Hard stop | VIX>30 → don't trade (vol regime break) |

### Expected Performance
- WR estimated: 55-60% (connors pattern + funding exhaustion)
- PF estimated: 1.3-1.5 (modest edge)
- n/year: 80-120 (frequent oscillation)
- Regime risk: BREAKS during DXY trend (>2% 4H move), crypto-specific events

### Status
- On-chain momentum NOT live (CRYPTO_ONCHAIN_MOMENTUM_ENABLED=0)
- Connors RSI2 patterns exist in strategy registry but volume low
- Funding rate data available but not systematically used for oscillation
- ADV gate (PR-6) would ensure only liquid BTC/ETH signals survive

---

## 3. ETF TLT/IEF — Yield Curve Oscillation (Bond Duration Pair)

### Mechanics
TLT (20+ year Treasury) and IEF (7-10 year Treasury) oscillate based on yield curve shape:
- When curve steepens → TLT outperforms (long duration benefits from lower long rates)
- When curve flattens → IEF outperforms (short duration protected)
- Spread oscillates with 10Y-2Y spread
- MOVE index (bond vol) gates the oscillation: <20d MA → mean-revert, >20d MA → trend (break)

### Evidence
- TSMOM on TLT/IEF/SHY: academic (Moskowitz 2012), Cochrane-Piazzesi 2005 curve-carry
- Bond agent produces ~10 raw signals/day but 0 quality (elite_score floor 40 too high)
- M-024 BOND TSMOM pending

### Entry/Exit Framework
| Parameter | Value |
|---|---|
| Entry (LONG TLT) | Curve steepening: 10Y-2Y spread > 20d MA + TLT > SMA200 |
| Entry (LONG IEF) | Curve flattening: 10Y-2Y spread < 20d MA + IEF > SMA200 |
| TP | 1.5% |
| SL | 0.75% |
| Max hold | 21 days (monthly rebalance) |
| Regime gate | MOVE < 20d MA (bond vol low → mean-reversion works) |
| Hard block | FOMC ±2 days |

### Expected Performance
- WR estimated: 55-60% (curve-carry academic edge)
- PF estimated: 1.2-1.4 (low-vol asset, small edge)
- n/year: 12-24 (monthly frequency)
- Regime risk: BREAKS during rate shock, FOMC surprises

### Status
- BOND class: n=11, PF=0.66 — statistically meaningless
- 3 academic pilots unwired
- FHED data key needed for yield curve (M-032 pending)
- De-prioritized for 90 days

---

## 4. Comparison: Which Oscillation Is Most Actionable?

| Symbol | Structural Driver | Evidence Strength | Current Gate Blocker | Paper-Ready? |
|---|---|---|---|---|
| AUDUSD=X | Interest rate differential | PF 3.55 SHORT n=11 | FOREX HARD_DISABLE | After exemption framework |
| BTCUSDT | VWAP + funding rate | Connors RSI2 75%+ pattern | On-chain disabled | After ADV gate + on-chain enable |
| TLT/IEF | Yield curve shape | Academic 2005-2025 | BOND elite floor 40 | After floor lower + FRED key |

**Priority order:** AUDUSD (strongest evidence, smallest n) → BTCUSDT (most liquid, most volume) → TLT/IEF (lowest urgency, slowest oscillation).

---

## 5. Oscillation Detection Pipeline (Proposed)

Add to `alpha_engine/scanner.py` or new `alpha_engine/oscillation_detector.py`:

```
For each symbol with n≥30 closed picks:
  1. Compute Hurst exponent (H<0.5 = mean-reverting, H>0.5 = trending)
  2. Compute 30d rolling PF of Connors RSI2 signals
  3. Compute 30d range as % of price (tight range <5% = oscillation candidate)
  4. Check regime: DXY trend strength, VIX level, funding rate
  5. Flag: IS_OSCILLATING=True if H<0.4 AND range<5% AND regime=neutral
  6. Auto-exempt from trend-following gates when oscillating
  7. Auto-revoke when regime shifts (>2σ DXY/VIX move)
```

**Env:** `OSCILLATION_DETECTOR_ENABLED=1` (default OFF until backtest on 90d of data)

---

## 6. Risk Disclaimer

No oscillation is a "sure thing." All three patterns above BREAK during regime shifts:
- **AUDUSD**: Breaks during DXY super-trend (2022 rate hiking cycle)
- **BTCUSDT**: Breaks during trend breakouts (ETF approval, halving, macro events)
- **TLT/IEF**: Breaks during rate shocks (2022 bond crash, 2020 COVID liquidity crisis)

**Hard rules:**
- Never trade oscillation signals during macro event windows
- Never trade against DXY trend (for AUDUSD and BTCUSDT)
- Never exceed 0.5% risk per oscillation trade
- Always paper-validate 30d+ before any sizing
