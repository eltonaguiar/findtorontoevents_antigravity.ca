# Live Trade Monitoring — Lessons Learned
## 2026-03-16 | 10 snapshots over 2 hours | 8 positions at 20x leverage

### Portfolio Summary
| Symbol | Score | Type | Low Point | Final PnL (spot) | Final PnL (20x est) | Outcome |
|--------|-------|------|-----------|-------------------|----------------------|---------|
| DOTUSDT | 35 | Audit pick | -0.37% | **+1.80%** | ~+36% | WIN |
| SOLUSDT | 72 | Audit pick | +0.02% | **+1.20%** | ~+24% | WIN (never red) |
| ETHUSDT | 95 | Audit pick | -0.31% | **+1.11%** | ~+22% | WIN (recovered from -6.11% at 20x) |
| AVAXUSDT | 72 | Audit pick | -0.26% | **+0.99%** | ~+20% | WIN |
| BTCUSDT | 79 | Audit pick | -0.41% | **+0.26%** | ~+5% | WIN (barely) |
| DOGEUSDT | 65 | Audit pick | -0.90% | **-0.10%** | ~-2% | FLAT |
| XRPUSDT | 45 | Audit pick | -0.61% | **-0.22%** | ~-4.4% | LOSING (recovering) |
| ATOMUSDT | 0 | Manual add | -0.65% | **-0.25%** | ~-5% | LOSING (gave back gains) |

### Key Findings

#### 1. Score-Performance Correlation is Phase-Dependent
- **During selloffs**: High-score picks dip LESS (positive correlation) — score = drawdown protection
- **During early recovery**: Low-score mid-caps bounce FIRST (negative correlation) — score = slower recovery
- **During broad recovery**: High-score picks catch up (correlation returns positive)
- **Net result**: Over 2 hours, high-score picks outperformed. Score works on SWING timeframe.

#### 2. 20x Leverage Amplifies Everything Dangerously
- A normal -0.4% BTC spot move became -8.25% at 20x
- ETH went from +0.13% to -6.11% to +22% at 20x in 2 hours — wild swings
- SOL was the ONLY position that never went red — it had independent momentum
- Lesson: At 20x, you need picks with LOW CORRELATION to BTC, not just high scores

#### 3. Manual Picks Underperform System Picks
- ATOMUSDT (manual, score 0): Volatile, peaked at +3.42% then gave it ALL back, ending -5%
- System-scored picks (avg score 65+): 5 of 7 ended green
- The scoring system outperformed human intuition over a 2-hour window

#### 4. Correlation is the Hidden Killer at High Leverage
- 7 of 8 positions were LONG crypto — maximum correlation
- When BTC dumped, everything dumped together (except SOL)
- Portfolio P&L swung from -$6 to -$20 to +$15 — all from BTC moves
- Lesson: Max 2-3 correlated positions at 20x. Diversify across uncorrelated assets.

#### 5. Meme Coins (DOGE) Don't Follow the Rules
- DOGE (score 65) was the worst system-picked performer
- Recovered slower than everything else despite mid-range score
- Meme coins have their own momentum independent of fundamentals
- Lesson: The scoring system doesn't capture meme coin dynamics. Consider a "meme penalty" factor.

#### 6. SOL Was the Perfect 20x Pick — Why?
- Multi-system consensus (score 72) but not overcrowded like BTC/ETH
- Independent catalyst — decoupled from BTC during the dump
- Never went red across 10 snapshots — the ONLY position to achieve this
- Moderate volatility — enough to profit but not enough to liquidate
- Lesson: The ideal 20x pick is mid-score, mid-cap, with independent momentum

### Recommendations for Scoring System

1. **Leverage Safety Gate** (SHIPPED today) — Tags each pick with max safe leverage based on:
   - Volatility, correlation, entry quality, regime, R:R, beta score

2. **Correlation Penalty** (TO BUILD) — Reduce score when >3 positions share same direction/sector

3. **Recovery Speed Factor** (TO BUILD) — Track how fast a pick recovers from drawdowns. Fast recovery = safer for leverage.

4. **Meme Coin Penalty** (TO BUILD) — Flag DOGE, SHIB, PEPE, BONK etc. with higher leverage requirements

5. **Independent Momentum Bonus** (TO BUILD) — Bonus points for picks showing price movement AGAINST BTC trend (like SOL today)

6. **Bear Market Long Suppression** (SHIPPED today) — Require higher agreement threshold for longs in bear regime

### Raw Data
See `live_trade_journal.json` for all 10 snapshots with exact prices and PnL at each interval.
