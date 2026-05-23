# Rise of the Claw — Strategy Research Notes
## World-Class Institutional Strategies (Feb 17, 2026)

### Strategies Already Implemented (v3)
| ID | Strategy | Tier | Academic Basis |
|----|----------|------|----------------|
| funding-rate-arb | Funding Rate Arbitrage (VWMA z-score) | TIER_1 | Polynomial/Drift Protocol |
| pairs-trading | Cointegration Z-score | TIER_1 | Engle-Granger |
| betting-against-beta | Beta<0.8 + above 200d SMA | TIER_1 | Frazzini & Pedersen 2014 |
| flash-crash-reversal | DD + RSI(6) + vol capitulation | TIER_1 | Broad academic |
| quality-minus-junk | Composite quality z-score | TIER_1 | Novy-Marx/Asness 2019 |
| meme-bollinger-mean-rev | BB lower band + RSI<30 + vol spike | TIER_1 | Technical |
| macd-momentum | MACD histogram crossover | TIER_1 | Classic technical |
| golden-cross-stocks | 50/200 SMA golden cross | TIER_1 | Classic technical |
| momentum-factor | 12-1 month momentum | TIER_1 | Jegadeesh & Titman 1993 |
| + 11 SCOUT strategies | StochRSI, CCI, Williams%R, Donchian, Supertrend, Keltner, RSI, Volume, MA crossover | SCOUT | Supplementary TA |

### High-Priority Future Strategies (Research Identified)

#### 1. Carry Trade (Forex) — Sharpe 0.5-0.8, Win Rate 70-80%
- Borrow low-yield (JPY), invest high-yield (AUD/NZD) 
- Signal: Interest rate differential > 1.5% AND above 50d SMA
- Pairs: AUD/JPY, NZD/JPY, ZAR/JPY
- Stop loss: 5% below entry
- **Requires yfinance forex data + external interest rate API**

#### 2. ML Regime Detection — Sharpe 1.3-1.8
- Detect Bull/Bear/Sideways regime using Random Forest on 50+ indicators
- Apply different strategy per regime
- Accuracy: 65-75% for regime identification
- **Requires sklearn — add to backtest_engine.py as meta-layer**

#### 3. Adaptive Entropy-Based Thresholds — Sharpe 1.2-1.5
- Calculate Shannon entropy of returns window
- High entropy (>0.7) = loosen RSI thresholds (less responsive)
- Low entropy (<0.3) = tighten RSI thresholds (more selective)
- Better than static drought adaptation
- **Potential v4 upgrade for all SCOUT strategies**

#### 4. Sector Rotation — Sharpe 0.8-1.2
- Rotate into top-performing sectors quarterly
- Market regime filter: Only rotate when SPY > 200d SMA
- Sectors: XLK, XLF, XLE, XLV, XLI, XLB, XLY, XLP, XLU

#### 5. Short Squeeze Detection — Sharpe 0.9-1.2, Win Rate 45-55%
- Price breaks above 20d high + Volume > 5x + Consecutive green candles
- **Requires external short interest data (Fintel API)**
- High reward when squeeze catches (20-100%+ moves)

### Benchmark Sharpe Ratios (Research-Validated)
| Strategy Class | Sharpe | Win Rate | Max DD |
|---------------|--------|----------|--------|
| Momentum | 0.9-1.3 | 52-58% | -20% to -30% |
| Mean Reversion | 0.9-1.2 | 60-70% | -15% to -20% |
| Pairs Trading | 1.2-1.6 | 65-75% | -10% to -15% |
| Funding Rate Arb | 0.8-1.2 | 85-95% | -5% to -10% |
| MA Crossover | 0.7-1.1 | 45-52% | -15% to -25% |
| Volume Breakout | 0.8-1.1 | 40-50% | -20% to -30% |
| Sector Rotation | 0.8-1.2 | 55-65% | -18% to -25% |

### Tournament Thresholds (Research-Aligned)
- Promotion: 50+ trades + 55%+ win rate ✅ (matches our current threshold)
- Phase 1 Goal: Sharpe > 0.8 + Max DD < 20%
- Phase 2 Goal: Sharpe > 1.0 + Max DD < 15%
- Production Goal: Combined Sharpe > 1.5 across remaining strategies

### World-Class Benchmarks
- Retail traders: Sharpe 1.0-1.5 = "Good" 
- Institutional: 1.5-2.0 = "Excellent"
- Top Hedge Funds (Citadel, D.E. Shaw): 2.0-2.5
- Renaissance Medallion (best ever): 3.0+ Sharpe, 65% annual returns

---

## Architecture Planning Agent Findings (Feb 17, 2026)

### CRITICAL: Overfitting Warning
The STOCKS competition system has **bt_fwd_correlation = 0.34** (only 34% correlation between backtest and forward test). Only 5 of 23 strategies survived live forward testing. **Our backtest alone is NOT reliable for ranking.**

This is why the three-layer pipeline (live forward → MySQL ingest → weekly backtest) was the right call. Real forward outcomes must drive rankings.

### Better Composite Scoring Formula (from architecture agent)
Current tournament.js uses: return 40% + win rate 25% + activity 20% + consistency 15%

**Recommended upgrade:**
```
Sharpe ratio (normalised 0-3)  = 30%
Win rate                        = 25%
Max drawdown (inverted)         = 20%
Profit factor (normalised)      = 15%
Consistency (monthly ret std)   = 10%
```
This is more aligned with how top funds evaluate strategies.

### Tournament Leagues (future upgrade)
Instead of a flat leaderboard, a 4-league bracket:
- Champions League (top 5): composite > 0.65
- Premier Division (6-12)
- Challenger Division (13-20)
- Qualification (new entrants)
- Eliminated: must pass rapid backtest (Sharpe > 0.8) to re-enter

### ML Ranker Feature Priorities (once we have forward data)
Most predictive features (in order):
1. `bt_fwd_correlation` — the single most important anti-overfitting signal
2. `bear_sharpe` — does the strategy work in bear markets (most strategies fail here)
3. `max_drawdown` — strategies with deep drawdowns rarely survive
4. `win_rate` — must be above 50% consistently
5. `total_trades` — strategies with <50 trades in 5yr have insufficient evidence

### Key Files in STOCKS system (for future KIMI integration)
- `STOCKS/competition/run_competition.py` — `compute_indicators()` pattern to reuse
- `STOCKS/competition/forward_test.py` — forward pick resolution logic
- `FORWARD_TEST_EXECUTIVE_SUMMARY.md` — documents the overfitting problem
