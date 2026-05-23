# Master-Picks Data Quality Checklist & Checks and Balances

## Overview
This document outlines the comprehensive checks and balances to ensure only high-quality, accurate signals are sent to #master-picks.

---

## 1. Signal Vetting Process (5-Layer Validation)

### Layer 1: Quality Score Check (25 points)
- **Minimum Threshold**: 75.0 (B+ grade)
- **Sources**: DNA/Genome system backtest scores
- **Metrics**:
  - Sharpe Ratio >= 1.5
  - Win Rate >= 55%
  - Profit Factor >= 1.6
  - Max Drawdown <= 20%
  - Total Trades >= 50

### Layer 2: Price Validation (25 points)
- **Real-Time Price Sources** (in order):
  1. CoinGecko API (free, primary)
  2. CoinMarketCap API (if API key available)
  3. Binance Public API
  4. Scrapling web scraper (fallback)
- **Maximum Deviation**: 25% from current market price
- **Example Failures**:
  - SOL at $143 vs current $87 = 63% deviation → REJECTED
  - ETH at $3175 vs current $2035 = 56% deviation → REJECTED
  - BTC at $83646 vs current $69020 = 21% deviation → ACCEPTED

### Layer 3: Multi-System Consensus (20 points)
- **Minimum Systems**: 2+ independent systems must agree
- **Tracked Systems**:
  - alpha_engine
  - mercury2
  - dna_genome
  - crypto_ml_edge
- **Consensus Scoring**:
  - 4+ systems: +20 points
  - 3 systems: +15 points
  - 2 systems: +10 points
  - 1 system: 0 points (rejected)

### Layer 4: Confidence Threshold (15 points)
- **High Confidence (≥85%)**: +15 points
- **Good Confidence (80-84%)**: +10 points
- **Low Confidence (<80%)**: 0 points

### Layer 5: Forward Test Performance (15 points)
- **Win Rate ≥55%**: +15 points
- **Win Rate 50-54%**: +5 points
- **No forward test data**: 0 points

### Vetting Score Threshold
- **Minimum to Pass**: 70/100
- **Price Validity**: Must pass price validation (mandatory)

---

## 2. Duplicate Detection

### Symbol + Direction Deduplication
- Only one pick per symbol/direction combination
- Keep highest quality score when duplicates found
- Example: If 2 BTC LONG signals, keep the one with:
  - Higher quality_score
  - More agreeing systems
  - Better backtest metrics

---

## 3. Tracker Persistence

### Data Files Committed to Repo
- `signal_aggregator/data/master_picks_tracker.json` - Active picks
- `signal_aggregator/data/master_picks_history.json` - Closed picks

### Commit Schedule
- Every hourly run commits tracker updates
- Ensures data persists between GitHub Actions runs
- Enables performance tracking over time

---

## 4. Genome/DNA System Integration

### Quality Thresholds in Genome System
```python
quality_threshold = 70.0  # Only picks with score >= 70
min_backtest_trades = 50
min_sharpe_ratio = 1.5
max_drawdown = 0.20
```

### Validation Checks (9-Point Checklist)
1. ✅ Sufficient backtest data
2. ✅ No recent similar signal (avoid duplicates)
3. ✅ Market hours OK
4. ✅ Liquidity sufficient
5. ✅ Correlation within limits
6. ✅ Daily loss limit OK
7. ✅ Spread acceptable
8. ✅ Volatility normal
9. ✅ Not blacklisted

---

## 5. Current Data Quality Issues

### Known Issues (March 2, 2026)

| Symbol | Genome Entry | Current Price | Deviation | Status |
|--------|--------------|---------------|-----------|--------|
| ETHUSDT | $3,253 | $2,035 | 59% | ❌ REJECTED |
| ETHUSDT | $3,175 | $2,035 | 56% | ❌ REJECTED |
| SOLUSDT | $142.25 | $87.26 | 63% | ❌ REJECTED |
| SOLUSDT | $143.46 | $87.26 | 63% | ❌ REJECTED |
| BTCUSDT | $83,646 | $69,020 | 21% | ✅ ACCEPTED |

### Root Cause
Genome system generating picks with stale prices. Need to:
1. Add real-time price feed to genome system
2. Regenerate picks with current market data
3. Increase price validation frequency

---

## 6. Automated Workflows

### Hourly Master-Picks (hourly-master-picks.yml)
- Runs every hour at :05
- Aggregates signals from all systems
- Applies price validation
- Sends top 5 to #master-picks
- Commits tracker data

### Vetted Picks Deploy (deploy-vetted-picks.yml)
- Runs every 4 hours at :15
- Uses 5-layer vetting process
- Only sends picks with score >= 70
- Manual trigger available

### Health Score Update (master-picks-health.yml)
- Runs every 4 hours
- Shows active picks with unrealized P/L
- Displays component scores
- EST timestamps

---

## 7. Manual Override & Commands

### Deploy Vetted Picks (Manual)
```bash
# Trigger via GitHub Actions
python signal_aggregator/deploy_vetted_picks.py
```

### View Closed Picks
```bash
python signal_aggregator/closed_picks_command.py 30
```

### Clear Channel (if needed)
```bash
# Requires DISCORD_BOT_TOKEN with MANAGE_MESSAGES
python signal_aggregator/clear_channel_command.py master_picks
```

---

## 8. Health Score Components

### Overall Score (0-100)
- **Win Rate Score (35%)**: 50%+ win rate = 100 points
- **Profit Factor Score (30%)**: 2.0+ = 100 points
- **Consistency Score (20%)**: Low std dev of returns
- **Sample Size Score (15%)**: 20+ trades = 100 points

### Grades
- A (Excellent): 80-100
- B (Good): 65-79
- C (Fair): 50-64
- D (Poor): 35-49
- F (Failing): 0-34

---

## 9. Required Secrets

| Secret | Purpose | Required For |
|--------|---------|--------------|
| DISCORD_MASTER_PICKS | Webhook for #master-picks | All workflows |
| DISCORD_FRESHPICKS | Webhook for #freshpicks | Hourly workflow |
| DISCORD_WEBHOOK_URL | Automation alerts | All workflows |
| DISCORD_BOT_TOKEN | Clear channel command | Channel clearing |
| COINMARKETCAP_API_KEY | Price validation (optional) | Price fetcher |

---

## 10. Monitoring & Alerts

### Positive Indicators ✅
- Multiple systems agreeing on direction
- High quality scores (B+ or better)
- Prices within 10% of market
- Strong backtest metrics
- Recent forward test wins

### Warning Signs ⚠️
- Single system signals
- Quality scores below 70
- Prices 15-25% off market
- Low consensus count
- Missing backtest data

### Critical Issues 🚨
- Prices >25% off market
- Quality scores below 65
- Failed validation checks
- Duplicate signals
- Stale data (>1 hour old)

---

## 11. Next Steps for Data Quality

1. **Fix Genome Price Staleness**
   - Add real-time price API to genome system
   - Regenerate picks hourly with fresh prices
   - Cache prices for max 5 minutes

2. **Add Forward Test Validation**
   - Track recent performance per strategy
   - Disable strategies with <50% win rate
   - Boost scores for strategies with >60% win rate

3. **Implement Signal Age Limit**
   - Reject signals older than 30 minutes
   - Force fresh data for each run
   - Add timestamp validation

4. **Create Quality Dashboard**
   - Real-time view of vetting results
   - Historical performance tracking
   - Alert on quality degradation

---

## 12. Success Metrics

Track these KPIs weekly:
- **Vetting Pass Rate**: % of signals that pass (target: 20-30%)
- **Price Validation Success**: % of prices within 10% (target: >95%)
- **Multi-System Consensus**: % with 2+ systems (target: >60%)
- **Average Quality Score**: Mean score of sent picks (target: >75)
- **Win Rate of Sent Picks**: Actual performance (target: >55%)

---

Last Updated: 2026-03-02
Version: 1.0
