# TradingView Paper Portfolio — PM Decisions Log (April 2026)

**Portfolio Manager**: Claude Opus 4.6 (1M context)
**Mandate**: Manage 6 paper trading books on TradingView as hedge-fund PM. Make unilateral risk-management decisions, document every action with reasoning.
**Reporting format**: Each decision has (1) what, (2) why, (3) expected outcome, (4) what would invalidate it.

---

## 📊 Opening State (2026-04-05 ~03:30 UTC)

| Portfolio | Balance | Realized | Unrealized | Equity | Net | Positions |
|-----------|---------|----------|------------|--------|-----|-----------|
| zerounderscore | $99,856 | -$144 | +$283 | $100,139 | **+$139** | 8→10 |
| TRUSTOURSCORE | $90,181 | -$9,819 | -$3 | $90,177 | **-$9,822** | 12 |
| TESTER | $3,005 | +$4.72 | -$0.62 | $3,004 | **+$4.10** | 6 |
| THEWINNERS | $999 | -$1.48 | -$0.38 | $998 | **-$1.86** | 12 |
| BROKIE | $1,002 | +$1.61 | +$0.92 | $1,003 | **+$2.53** | 7 |
| SCALPER | $1,993 | -$7.30 | -$3.22 | $1,989 | **-$10.52** | 5 |

**Aggregate**: ~-$9,680 (dominated by TRUSTOURSCORE legacy WARUSDT error of -$9.8K)

---

## 🎯 PM Strategy (April 2026)

### Thesis
1. **CHOP/BEAR regime favors SHORTS** — dashboard data shows 56% SHORT WR vs 49% LONG in bear regime. BERA-SHORT on zerounderscore is concrete proof (+1.73%).
2. **Alpha is concentrated in A-bucket** — trust≥6 alpha_engine picks (not the ml_crypto_pred flood of 120-score impostors).
3. **Size follows conviction** — meaningful position sizing on A-bucket, minimal on experimental.
4. **Cut losers, let winners run** — don't hold losing picks past their SL. Current 12-position THEWINNERS is too fragmented.

### Portfolio roles (revised)
- **zerounderscore** ($100K): Primary alpha book, add meaningful SHORTS + BTC-LONG when direction works
- **TRUSTOURSCORE** ($90K): Recovery book. Concentrate on 4-6 high-quality A-bucket picks at 3% each. Stop diluting
- **TESTER** ($3K): Experimental SHORTS at 2% each. Theme: tsmom_strategy
- **SCALPER** ($2K): Tight-stop momentum. Currently misaligned (counter-trend BTC short)
- **THEWINNERS** ($1K): Consolidation target. Close losers, keep A-bucket winners
- **BROKIE** ($1K): Low-risk proven, 5% per position, don't over-trade

---

## 📋 Decisions Log (reverse chronological)

### 2026-04-05 03:30 UTC — Portfolio Rebalance Session

#### DECISION #1: Close APTUSDT LONG on THEWINNERS
- **What**: Close 91.34 APT long (entry 0.851, current 0.846, PnL -$0.46, -0.53%)
- **Why**: Consolidation. THEWINNERS has 12 positions on $1K — fragmented. APT is the biggest % loser and showing persistent weakness. Better to redeploy margin into fewer, higher-quality positions.
- **Expected outcome**: Frees ~$77 margin. Slight realized loss (-$0.46).
- **Invalidator**: N/A — already SL-ing a losing pick.

#### DECISION #2: Add KITEUSDT SHORT to zerounderscore (2%)
- **What**: Open KITEUSDT SHORT 2% ($2000 notional) on zerounderscore
- **Why**: Doubling down on the tsmom_strategy SHORT thesis that BERA-SHORT proved (+1.73%). KITE is the paired pick from the same strategy (conf=0.72 sweet spot). Adds SHORT to rebalance L/S ratio (currently 62/38 long-biased).
- **Expected outcome**: If tsmom momentum-shorts keep working, $2K at 50% target TP = $100 gain. SL around 17% adverse = -$340 risk.
- **Invalidator**: If KITE rallies back to entry+1%, I review at 4h mark.

#### DECISION #3: Skip JTOUSDT LONG add to zerounderscore
- **What**: Not opening JTO LONG on zerounderscore
- **Why**: Already holding JTO LONG on THEWINNERS ($20), TRUSTOURSCORE ($1800), BROKIE ($50). Cross-portfolio exposure sufficient; adding another $2K would create concentration risk.
- **Expected outcome**: Prevents correlated drawdown if JTO reverses.
- **Invalidator**: JTO rallies >3% before I close one of the existing positions.

#### DECISION #4: Hold all existing zerounderscore positions
- **What**: No changes to BERA-S, BTC-L, ADA-L, LINK-S, ETH-S, POL-L, FIL-L, AVAX-L
- **Why**: Winners (BERA, BTC, ADA) earning their keep. Losers within ATR tolerance. AVAXUSDT LONG -0.44% on $10K notional looks scary but is only -0.44%, well within 1x ATR. Not cutting.
- **Invalidator**: Any position reaching -1.5% triggers re-review.

#### DECISION #5: Hold TRUSTOURSCORE positions, add 2 SHORTS next cycle
- **What**: No closes on TRUSTOURSCORE right now. Plan 2 new SHORT adds next cycle (SHORT tsmom picks)
- **Why**: Already added SUI/OP/JTO this session. Current positions all within SL tolerance. To recover the -$9.8K legacy hole, need BOTH consistent small wins AND 1-2 concentrated bets. SHORT bias follows regime edge.
- **Expected outcome**: Gradual drawdown recovery over 50-100 trades.
- **Invalidator**: Any TRUSTOURSCORE position hits -5%.

#### DECISION #6: Close SCALPER BTCUSDT SHORT
- **What**: Close 0.0149 BTC SHORT (entry 66,901, current 67,155, PnL -$3.77, -0.38%)
- **Why**: SCALPER's theme is cut-losers-fast (0.5x ATR SL). BTC SHORT counter to the trend at -0.38% on $1K notional is hurting scalper discipline. Book is underwater -$10.52. Close and free $99 margin for trend-aligned trades.
- **Expected outcome**: Realizes -$3.77. Account margin released.
- **Invalidator**: N/A — SCALPER SL discipline demands the close.

#### DECISION #7: Add BTCUSDT LONG to SCALPER (replacement trade)
- **What**: After closing BTC-S, add BTCUSDT LONG at current price, 8% ($160) with tight SCALPER R:R
- **Why**: If BTC is trending up (current 67,160 vs scalper's short entry 66,901 = +0.4% up), align with trend instead of fighting it. SCALPER can use larger position size because of tight 0.5x ATR SL (1.25% risk = $2 per trade).
- **Expected outcome**: If BTC continues to $68,200 (1.5x ATR = 1.5%), profit = $2.40 per $160 = 1.5%. Still tiny but trend-aligned.
- **Invalidator**: BTC fails $67,000 within 2h = close.

#### DECISION #8: Size-down THEWINNERS remaining adds
- **What**: After APT close, don't add more to THEWINNERS. Keep at 11 positions.
- **Why**: $1K can't support more concentrated bets. Let the existing 5 SUPER cohort picks (SUI/DOGE/DYDX/STRK/JTO) and the 6 legacy positions play out.
- **Expected outcome**: Focus beats fragmentation.
- **Invalidator**: A pick underperforms by >1% → cut and redeploy.

---

## 📅 Monitoring Cadence (PM decision)

**Primary check-in**: every 45 minutes during active US market hours.
**Rationale**:
- TP/SL rules use 1-2x daily ATR (slow-moving), so sub-30min checks are noise
- BUT intraday price action on crypto can move 2-3% in an hour during volatility spikes
- 45min is middle-ground: fast enough to cut losers before they blow through SL, slow enough to avoid overtrading

**What happens at each check-in**:
1. Pull every portfolio's positions + balance + realized/unrealized P&L
2. Flag any position at -2% or worse → decide cut vs hold
3. Flag any position at +TP target (within 5%) → move SL to breakeven
4. If regime has shifted (check dashboard regime indicator), re-evaluate L/S mix
5. Append outcomes + decisions to this log

**Off-hours** (user timezone night / low-vol hours):
- Extend to 2h intervals
- Widen stops slightly (don't cut losers on overnight noise)

**Emergency triggers** (override interval):
- Any single position loses >$100 → immediate review
- Aggregate unrealized drawdown > -$500 → immediate review
- BTC moves >3% in 30min → review all BTC-correlated positions

## Risk Limits (PM self-imposed)

- Max position size per portfolio: 15% (book concentration cap)
- Max per-pick loss before review: -5% (pick-level stop)
- Max book drawdown before full review: -10% of opening equity
- Cross-portfolio correlation: limit to 3 portfolios per symbol
- Counter-trend: max 1 per portfolio at any time

---

## Metrics to track (review at each cycle)

- Realized P&L per portfolio (daily)
- Unrealized P&L per portfolio (hourly)
- Win rate by bucket (A/B/C/D/E-SHORT)
- Win rate by source (alpha_engine vs ml_crypto_pred vs tsmom_strategy)
- L/S ratio per portfolio (target balanced for zerounderscore)
- Cross-portfolio correlation (via symbol overlap)
