# SQL Extract Edge Analysis - ejaguiar1_stocks (2026-04-06)

**Source:** `ejaguiar1_stocks` MySQL dump, 65,154 at_raw_picks, 7,119 consensus picks, 121 signal outcomes.
**Closed trades analyzed:** 3,823 (at_raw_picks) + 4,871 (consensus).

## EDGE #1: Battleground + Alpha Engine Are the Only Profitable Sources

| Source | n | WR | Avg PnL | PF |
|--------|---|----|---------|----|
| battleground | 726 | 60.9% | +2.13% | 1.22 |
| alpha_engine | 493 | 52.7% | +0.45% | 1.15 |
| alpha_engine_db | 238 | 58.0% | +2.51% | 1.52 |
| genome_darwin | 10 | 60.0% | +27.96% | 2.03 |
| audit_trail_local | 1,775 | 40.5% | -5.98% | 0.32 |
| sandbox_opposite | 244 | 1.6% | -6.11% | 0.01 |

**Action:** Route capital only through battleground/alpha_engine sources. Kill sandbox_opposite and audit_trail_local signal feeds.

## EDGE #2: 5 Strategies With Proven Live Edge (n>=20, PF>2)

| Strategy | n | WR | Avg PnL | PF |
|----------|---|----|---------|----|
| justin_breakout_volume_v2 | 350 | 73.7% | +2.02% | 2.31 |
| crypto_keltner_compression_expansion_v1 | 66 | 75.8% | +14.82% | 2.79 |
| crypto_rsi_whaleconfirmed_v1 | 100 | 64.0% | +6.62% | 4.18 |
| crypto_drawdown_convexity_recovery_v1 | 22 | 68.2% | +15.20% | 14.54 |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 37 | 89.2% | +4.89% | 58.79 |

**Action:** Increase allocation to these 5. They produced +2,860% cumulative PnL on 575 trades.

## EDGE #3: SHORTs Outperform LONGs in Live Data

- **LONG:** n=2,269, WR=40.3%, avg PnL=-1.81%
- **SHORT:** n=1,554, WR=50.3%, avg PnL=-0.80%

SHORTs have 10pp higher WR. In bearish crypto markets, SHORT signals carry more edge. The system's LONG bias is destroying capital.

**Action:** Shift signal mix toward SHORT when BTC 4h regime is bearish. Target 50/50 LONG/SHORT balance.

## EDGE #4: Consensus agreement=3 Is the Sweet Spot

| Agreement | n | WR |
|-----------|---|----|
| 2 | 2,745 | 39.8% |
| **3** | **879** | **50.6%** |
| 4 | 582 | 39.5% |
| 5 | 277 | 24.9% |
| 6+ | 334 | 27.5% |

Only agreement=3 breaks 50% WR. Higher agreement (4-6) actually DECREASES WR -- likely herding/crowding effect.

**Action:** Filter consensus picks to agreement=3 only. Reject agreement>=5 picks entirely.

## EDGE #5: FETUSDT + RENDERUSDT Are Alpha Symbols

| Symbol | n | WR | Avg PnL | PF |
|--------|---|----|---------|----|
| FETUSDT | 143 | 60.1% | +10.32% | 14.22 |
| RENDERUSDT | 54 | 64.8% | +6.61% | 3.96 |
| BTCUSDT | 725 | 49.1% | +1.93% | 1.18 |
| BNBUSD | 10 | 80.0% | +14.76% | 50.23 |

Meanwhile: DOGEUSDT (-2,090% total), XRPUSDT (-1,602%), ALGOUSDT (-1,035%), SOLUSDT (-1,031%) are capital destroyers.

**Action:** Overweight FETUSDT/RENDERUSDT. Blacklist DOGEUSDT, ALGOUSDT, APEUSDT. Reduce XRPUSDT/SOLUSDT size by 50%.

## EDGE #6: Confidence 0.7-0.8 Is the Only Reliable Band

| Confidence | n | WR | Avg PnL |
|------------|---|----|---------|
| 0.5-0.7 | 1,014 | 51.8% | +3.60% |
| **0.7-0.8** | **244** | **70.1%** | **+15.64%** |
| 0.8-1.0 | 418 | 6.7% | -5.17% |

Confidence >0.8 is a SELL signal (6.7% WR!). The system's highest-confidence picks are the worst. This is likely overfitting.

**Action:** Hard-reject any pick with confidence >= 0.8. Size up picks in 0.7-0.8 band.

## EDGE #7: Forex Is Quietly Profitable

- FOREX: n=84, WR=58.3%, avg PnL=+2.16%
- forex_rsi2_mean_reversion: n=55, WR=61.8%, PF=13.56
- Top forex pairs: GBPJPY (+86%), AUDUSD (+68%), USDCAD (+6%)

**Action:** Increase forex allocation. forex_rsi2_mean_reversion has PF=13.56, the highest reliable PF in the system.

## Kill List (Strategies to Remove)

| Strategy | n | WR | Total PnL | PF |
|----------|---|----|-----------|----|
| justin_ema9_pullback_v2 | 563 | 33.4% | -6,344% | 0.16 |
| justin_rsi_divergence_v2 | 383 | 31.1% | -4,165% | 0.17 |
| sandbox_opposite | 244 | 1.6% | -1,490% | 0.01 |
| opposite_day | 130 | 3.1% | -765% | 0.03 |
| justin_trend_follow_v2 | 217 | 34.6% | -625% | 0.36 |

These 5 strategies lost -13,389% combined. Removing them immediately improves system PnL by ~60%.
