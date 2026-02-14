# Algorithm Competition: 10 Strategies vs My Multi-Timeframe Momentum

## 🏆 The Competitors

### Academic/Scholarly Algorithms (5)

| # | Algorithm | Source | Core Edge |
|---|-----------|--------|-----------|
| **A1** | **Time-Series Momentum** | Hurst et al. (2017) - JPM | 12-month trend persistence |
| **A2** | **Pairs Trading** | Gatev et al. (2006) - RFS | Mean reversion on correlated pairs |
| **A3** | **CNN-LSTM Deep Learning** | Livieris et al. (2021) | Neural network pattern recognition |
| **A4** | **Opening Range Breakout** | Holmberg et al. (2013) | First 30-min volatility expansion |
| **A5** | **Dynamic VWAP** | Darolles & Le Fol (2007) | Volume profile execution |

### Social Media/Community Strategies (5)

| # | Algorithm | Source | Core Edge |
|---|-----------|--------|-----------|
| **S1** | **5-Minute Macro Scalping** | r/Daytrading (2024) | Opening range bias + retracement |
| **S2** | **RSI+MACD Divergence** | r/CryptoMarkets | Classic momentum divergence |
| **S3** | **Whale Shadow** | r/CryptoCurrency | On-chain smart money following |
| **S4** | **Narrative Velocity** | r/SatoshiStreetBets | Social sentiment + volume spikes |
| **S5** | **Portfolio Spray** | r/CryptoMarkets | VC-style diversification |

### My Algorithm

| Algorithm | Core Logic |
|-----------|------------|
| **KIMI-MTF** | Multi-timeframe momentum (1h/4h/24h) with composite scoring |

---

## 📊 Competition Rules

### Testing Framework
1. **Same universe**: 4 assets (POPCAT, PENGU, DOGE, BTC)
2. **Same timeframe**: 24-72 hour predictions
3. **Same evaluation**: Hit target = WIN, hit stop = LOSS, expired = NEUTRAL
4. **Scoring**:
   - WIN: +1 point
   - LOSS: -1 point  
   - EXPIRED: 0 points
   - Partial credit for progress milestones

### Progress Scoring
- 50% to target: +0.25 bonus
- 80% to target: +0.5 bonus
- Hit target: Full point

---

## 🎯 Algorithm Specifications

### A1: Time-Series Momentum (Academic)
```
Entry: 12-month positive return trend
Position: Long if momentum > 0, Short if < 0
Rebalance: Monthly
Crypto Adaptation: Use 7-day, 30-day, 90-day momentum
```
**Expected**: ~13.8% annual return, Sharpe 0.40-0.50

### A2: Pairs Trading (Academic)
```
Entry: Spread exceeds 2 std dev from mean
Exit: Spread converges to mean or 20 days
Pairs: DOGE/BTC correlation, POPCAT/SOL correlation
```
**Expected**: 11% annual return, 56-58% win rate, Sharpe 1.44

### A3: CNN-LSTM (Academic ML)
```
Entry: Model predicts >52% up probability
Exit: 24-hour hold or opposite signal
Input: 7-14 day price lags, volume
```
**Expected**: 52.9-54.1% accuracy, Sharpe 3.23

### A4: Opening Range Breakout (Academic)
```
Entry: Price breaks above/below first 30-min range
Time: 10:00-10:30 AM EST only
Exit: End of day or opposing signal
```
**Expected**: Significant alpha vs random walk

### A5: Dynamic VWAP (Academic)
```
Entry: Price crosses below VWAP (long), above VWAP (short)
Volume: Weight by predicted intraday volume
Timeframe: Intraday only
```
**Expected**: 50% of institutional volume uses this

### S1: 5-Minute Macro (Reddit)
```
Entry: Post-10:10 AM bias + retracement
Timeframe: 5-min chart, 1-min execution
Exit: Target #1 hit or trailing stop
```
**Claimed**: 80%+ win rate

### S2: RSI+MACD Divergence (Reddit)
```
Entry: RSI divergence + MACD crossover confirmation
Long: RSI higher low, price lower low
Short: RSI lower high, price higher high
Exit: 2% target or RSI extreme
```
**Claimed**: 60-65% win rate, 1.5:1 R:R

### S3: Whale Shadow (Reddit)
```
Entry: $1M+ whale wallet starts accumulating
Exit: Whale moves to exchange or tiered sells
Timeframe: Hours to weeks
```
**Claimed**: 40%+ monthly returns (with diversification)

### S4: Narrative Velocity (Reddit)
```
Entry: LunarCrush >80% + Volume >200% + Price >5%
Market Cap: $1M-$100M only
Exit: Sentiment <60% or volume -50%
```
**Claimed**: 12-18% per trade, 55-65% win rate

### S5: Portfolio Spray (Reddit)
```
Entry: 15-20 micro-caps (<$10M), 1-2% each
Criteria: Clean contract, locked liquidity, active community
Exit: Tiered (2x/5x/10x/20x+), time decay 2-4 weeks
```
**Claimed**: Portfolio-level 200% returns (18 zeros, 1 10x, 1 50x)

---

## 🥊 Current Standings

| Algorithm | Predictions Made | Wins | Losses | Score | Status |
|-----------|-----------------|------|--------|-------|--------|
| KIMI-MTF | 4 | 0 | 0 | 0 | ACTIVE |
| A1-A5 | 0 | 0 | 0 | 0 | PENDING |
| S1-S5 | 0 | 0 | 0 | 0 | PENDING |

### Current Market Prices (Baseline)
- POPCAT: $0.0515 (Target: $0.058)
- PENGU: $0.00670 (Target: $0.0075)
- DOGE: $0.0967 (Target: $0.105)
- BTC: $68,851 (Target: $72,000)

---

## 📈 Competition Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| Phase 1 | 0-24h | Initial predictions, algorithm deployment |
| Phase 2 | 24-48h | Mid-competition tracking |
| Phase 3 | 48-72h | Final results, winner declared |

**Winner Criteria**:
1. Highest win rate (minimum 10 predictions)
2. Best risk-adjusted returns
3. Most consistent performance across assets

---

## 📝 Implementation Notes

### Algorithms to Code
- [ ] A1: Time-Series Momentum (PHP/Python)
- [ ] A2: Pairs Trading correlation engine
- [ ] A3: Simplified ML model (or use pre-trained)
- [ ] A4: Opening Range Breakout detector
- [ ] A5: VWAP calculator
- [ ] S1: 5-min macro scanner
- [ ] S2: RSI+MACD divergence detector
- [ ] S3: Whale wallet tracker (on-chain)
- [ ] S4: Sentiment + volume screener
- [ ] S5: Micro-cap screener + position manager

### Data Requirements
- Price data: Coingecko/Kraken API
- On-chain: Arkham/DeBank API
- Sentiment: LunarCrush API
- Volume: DEX Screener/TradingView

---

*Competition start: 2026-02-13*
*Last updated: 2026-02-13 18:30 ET*
