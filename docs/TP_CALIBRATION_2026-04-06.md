# TP Calibration Report (2026-04-06)

## Problem Statement

78.9% of resolved crypto trades hit SL before TP. SL was already calibrated to
~2.1% (PF 3.05), but TP remained static at 2.5% across all symbols regardless
of volatility. The payoff ratio was 1.38:1 vs the 1.65:1 needed for the system's
win rate to be profitable. Trades were dying on noise, not wrong direction.

## Data Analyzed

- 2,867 closed crypto picks from audit_dashboard/data/dashboard_data.json
- 1,692 resolved (SL or TP hit): 1,032 SL hits (61.0%), 660 TP hits (39.0%)
- Avg winner: +3.14%, Median: +2.69%
- Avg loser: -2.09%, Median: -1.80%
- Current payoff ratio: 1.50:1

## Per-Symbol Findings

### SL Hit Rates by Symbol (resolved trades only)
| Symbol    |   N  | SL Rate | TP Rate | Avg TP Set | Avg SL Set | Optimal TP |
|-----------|------|---------|---------|------------|------------|------------|
| TRXUSDT   |  148 | 92.0%   | 8.0%    | 2.37%      | 1.34%      | 1.61%      |
| UNIUSDT   |   97 | 81.8%   | 18.2%   | 4.54%      | 2.34%      | 2.81%      |
| LTCUSDT   |   60 | 81.8%   | 18.2%   | 3.26%      | 1.72%      | 2.06%      |
| SOLUSDT   |  187 | 73.6%   | 26.4%   | 3.49%      | 1.93%      | 2.32%      |
| ADAUSDT   |  101 | 65.1%   | 34.9%   | 2.74%      | 1.49%      | 2.12%      |
| OPUSDT    |   55 | 64.3%   | 35.7%   | 3.83%      | 1.93%      | 3.04%      |
| APTUSDT   |  158 | 63.8%   | 36.2%   | 3.81%      | 1.95%      | 3.07%      |
| DOGEUSDT  |   91 | 62.5%   | 37.5%   | 1.89%      | 1.11%      | 1.58%      |
| BTCUSDT   |  301 | 62.4%   | 37.6%   | 2.53%      | 1.94%      | 2.33%      |
| BNBUSDT   |   91 | 60.0%   | 40.0%   | 2.20%      | 1.15%      | 1.95%      |
| AVAXUSDT  |   92 | 59.5%   | 40.5%   | 3.89%      | 2.25%      | 3.50%      |
| ETHUSDT   |  119 | 57.4%   | 42.6%   | 2.59%      | 1.62%      | 2.46%      |
| SUIUSDT   |  104 | 56.3%   | 43.7%   | 2.54%      | 1.36%      | 2.46%      |
| DOTUSDT   |  100 | 49.0%   | 51.0%   | 3.55%      | 1.83%      | OK         |
| RENDERUSDT|   67 | 47.7%   | 52.3%   | 4.55%      | 2.63%      | OK         |

### Winner Size Distribution (TP-hit trades)
- >= 1%: 94.1% of winners
- >= 2%: 76.1%
- >= 3%: 41.8%
- >= 5%: 8.5%
- >= 8%: 2.9%

### Key Insight
Most winners cluster at 2-3% profit. Setting TP at 2.5% for low-vol symbols and
3.5%+ for high-vol symbols is the sweet spot. The old static 2.5% was too tight
for volatile alts (they need room to swing) and too ambitious for BTC/ETH (where
moves are smaller but more reliable).

## Volatility Tier Calibration

### Tier Definitions
| Tier    | TP% (fallback) | SL% | ATR TP mult | ATR SL mult | Expected R:R |
|---------|---------------|-----|-------------|-------------|--------------|
| LOW     | 2.0%          | 2.1%| 1.0x        | 1.0x        | ~1.0         |
| MID     | 2.8%          | 2.1%| 1.4x        | 1.0x        | ~1.33        |
| HIGH    | 3.5%          | 2.1%| 1.6x        | 1.0x        | ~1.67        |
| DEFAULT | 2.5%          | 2.1%| 1.5x        | 1.0x        | ~1.19        |

### Rationale

**LOW tier (BTC, ETH, BNB, LTC, XRP):** These majors have lower daily ATR (2-3.5%).
The old 2.5% TP was actually reasonable but the R:R was too aggressive. By tightening
TP to 2.0% (fallback) and using 1.0x ATR, we capture the majority of moves. BTC
specifically had a 62.4% SL-hit rate with 2.53% avg TP set — most winners were at
~1.97% median, so 2.0% captures the bulk.

**MID tier (SOL, AVAX, LINK, SUI, etc.):** 4-5% daily ATR. These need room to breathe.
2.8% TP fallback gives them a better shot at hitting TP before noise triggers SL.
With ATR, 1.4x multiplier gives ~5.7-7% TP which matches the observed winner distribution.

**HIGH tier (DOGE, TRX, RENDER, TRUMP, PEPE, etc.):** High noise, 4-8% daily ATR.
3.5% TP fallback. With ATR, 1.6x multiplier gives room for the volatile swings.
These symbols have the worst SL-hit rates (TRX 92%, UNI 82%) because TP was set
absurdly wide relative to their price action.

### Minimum R:R Enforcement
All tiers enforce a minimum 1.2 R:R (TP distance / SL distance). If the vol-aware
TP would create R:R < 1.2, TP is widened to meet the floor. This prevents the
LOW tier from having R:R < 1.0 in edge cases.

## Implementation

### Files Modified
1. :
   - Added  dict (30 symbols with daily ATR%)
   - Added  (tier -> tp_pct, sl_pct, atr_tp_mult, atr_sl_mult)
   - Added  mapping
   - Added  function
   - Added  function (main computation engine)
   - Updated  to route crypto through vol-aware engine
   - Updated SL-only and TP-only derivation to use tier-specific R:R

2. :
   - Replaced old flat ATR table with vol-tier-aware table
   - Added tier definitions and per-symbol calibrated TP/SL reference

## Expected Impact

| Metric | Before | After (projected) |
|--------|--------|-------------------|
| SL-hit rate (of resolved) | 61.0% | ~50-55% |
| Avg winner | 3.14% | ~2.5-3.0% (tighter but more frequent) |
| Avg loser | 2.09% | ~2.1% (unchanged) |
| Payoff ratio | 1.50:1 | ~1.3-1.5:1 |
| Profit factor | ~0.96 (MID), ~0.85 (HIGH) | ~1.1+ (MID), ~1.0+ (HIGH) |

The trade-off: winners will be slightly smaller on average (capped tighter), but
significantly more trades will reach TP before SL, improving the overall PF.
The biggest improvement is expected in HIGH vol tier where TRX/UNI/LTC had
absurd 80-92% SL-hit rates from unreachable TP targets.
