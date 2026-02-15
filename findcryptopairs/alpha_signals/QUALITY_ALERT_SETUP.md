# Discord Quality Alert Bot - Setup Guide
## "Are We Sure?" - Quality-Gated Alerts

---

## 🎯 Core Principle

**Only send Discord alerts when we have statistical evidence.**

| Tier | Trades | Win Rate | Status | Discord Alert |
|------|--------|----------|--------|---------------|
| 🏆 Institutional | 500+ | 70%+ | **SEND** | @everyone ping |
| 🎯 Certain | 250+ | 65%+ | **SEND** | @here ping |
| ✅ Proven | 100+ | 60%+ | **SEND** | Normal alert |
| ⚠️ Validated | 50+ | 55%+ | **SEND** | With caution note |
| 🔍 Emerging | 30-50 | Any | **SUPPRESS** | Monitor only |
| ❌ Early Guess | <30 | Any | **SUPPRESS** | RSVE accumulating |

---

## 🚀 Quick Start

### 1. Set Environment Variable

```bash
# Windows PowerShell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"

# Or in .env file
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

### 2. Replace Your Current Alert Call

**OLD WAY (sends everything):**
```python
# Your old code
send_discord_alert(symbol="BTC", confidence=85, ...)  # Always sends
```

**NEW WAY (quality-gated):**
```python
from discord_alerts_quality import send_quality_alert

# Only sends if strategy is validated
sent, message = send_quality_alert(
    symbol="BTCUSDT",
    signal_type="buy",
    entry=50000,
    stop=49000,
    target=52000,
    strategy_id="BTC_CME_GAP_V2",  # Must have 50+ trades
    base_confidence=85,
    timeframe="1h"
)

if not sent:
    print(f"Alert suppressed: {message}")
```

---

## 📊 How It Works

### The Quality Gates

Every alert must pass these checks:

1. **RSVE Pipeline Check** (<30 trades)
   - ❌ SUPPRESSED: "Strategy in Week 1 - early guess"
   - Logs to console but NO Discord alert

2. **Minimum Trade Count** (<50 trades)
   - ❌ SUPPRESSED: "Only X trades, need 50+"
   - Strategy still validating

3. **Win Rate Threshold** (<55%)
   - ❌ SUPPRESSED: "Win rate below threshold"
   - Strategy underperforming

4. **Consecutive Losses** (5+)
   - ❌ SUPPRESSED: "Possible broken strategy"
   - Regime change detected

5. **Sharpe Ratio** (<0.5, after 100 trades)
   - ❌ SUPPRESSED: "Poor risk-adjusted returns"
   - Too much volatility for edge

### If All Gates Pass

```
✅ ALERT SENT with:
   - Adjusted confidence (tier multiplier applied)
   - "How sure" statement
   - Position sizing guidance
   - Strategy statistics
```

---

## 🎨 Discord Alert Format

### 🏆 Institutional Alert (500+ trades, 70%+ WR)

```
🏆 BTCUSDT BUY SIGNAL

📊 Confidence Assessment
   Base: 88/100 → Adjusted: 106/100 (capped at 100)
   🏆 INSTITUTIONAL

💰 Trade Setup
   Entry: $50,000.00
   Stop: $49,000.00 (-2.0%)
   Target: $52,000.00 (+4.0%)
   R:R = 1:2.0

📈 Strategy Stats
   ID: BTC_CME_GAP_V2
   Trades: 500
   Win Rate: 70.0%
   Sharpe: 1.85

🛡️ Position Sizing
   🏆 FULL SIZE (2-3% risk)
   Institutional-grade signal. Standard position sizing.

🔍 How Sure Are We?
   ✅ CERTAIN: 500+ trades, 70.0% WR, Sharpe 1.85. 
   Institutional-grade signal with extensive validation. 
   This is as sure as we get in trading.
```

### ⚠️ Validated Alert (50+ trades, 55%+ WR)

```
⚠️ DOGEUSDT BUY SIGNAL

📊 Confidence Assessment
   Base: 75/100 → Adjusted: 60/100
   ⚠️ VALIDATED

... (position sizing shows TEST SIZE with warnings)

⚠️ CAUTION
   This strategy meets minimum thresholds but is still 
   building track record. Use smaller size.
```

---

## 🔧 Configuration

### Minimum Thresholds (Configurable)

```python
from alert_system_v2_quality_gates import QualityGateConfig

config = QualityGateConfig(
    min_total_trades=50,           # Require 50+ trades
    min_win_rate=0.55,             # Require 55%+ win rate
    min_sharpe_ratio=0.5,          # Require Sharpe >0.5
    max_consecutive_losses=5,      # Max 5 losses in a row
)
```

### Discord-Specific Config

```python
from discord_alerts_quality import DiscordAlertConfig

config = DiscordAlertConfig(
    webhook_url="your-webhook-url",
    min_adjusted_confidence=60,    # After quality gates
    
    # Who to ping by tier
    role_mentions={
        ConfidenceTier.INSTITUTIONAL: "@everyone",
        ConfidenceTier.CERTAIN: "@here",
    },
    
    # Suppression settings
    suppress_early_guess=True,     # Always true
    suppress_emerging=True,        # Always true
    suppress_validated=False,      # Allow with warning
)
```

---

## 📈 Strategy Lifecycle

```
Week 1 (RSVE):        0-30 trades    → 🚫 SUPPRESSED (RSVE accumulating)
Week 2 (RSVE):        30-50 trades   → 🚫 SUPPRESSED (paper trading)
Week 3 (RSVE):        50+ trades     → ⚠️ CAUTION (live test)
Month 2-3:            100+ trades    → ✅ PROVEN (normal alerts)
Month 6+:             250+ trades    → 🎯 CERTAIN (boosted confidence)
Year 1+:              500+ trades    → 🏆 INSTITUTIONAL (@everyone)
```

---

## 🔄 Migration from Old System

### Step 1: Audit Current Strategies

```bash
cd findcryptopairs/alpha_signals
python alert_system_v2_quality_gates.py
```

This will show you which strategies pass/fail quality gates.

### Step 2: Import Trade History

```python
from alert_system_v2_quality_gates import QualityGatedAlertSystem

alerts = QualityGatedAlertSystem()

# Import your historical trades
for trade in historical_trades:
    alerts.update_strategy_metrics(
        strategy_id=trade['strategy'],
        won=trade['profit'] > 0,
        profit=trade['profit']
    )

# Check quality summary
print(alerts.get_quality_summary())
```

### Step 3: Update Alert Code

Find all places where you send Discord alerts and wrap with quality gates:

```python
# BEFORE
discord_webhook.send(embed=alert)

# AFTER
sent, msg = await bot.send_alert(...)
if not sent:
    logger.info(f"Suppressed: {msg}")
```

---

## 📊 Monitoring & Stats

### View Suppression Stats

```python
print(f"Alerts sent: {bot.stats['sent']}")
print(f"Suppressed: {bot.stats['suppressed']}")
print(f"Quality rate: {bot.stats['sent']/(bot.stats['sent']+bot.stats['suppressed'])*100:.1f}%")
```

### Daily Report

```python
# Send daily stats to Discord
await bot.send_stats_report()
```

---

## 🛡️ Risk Management Integration

Each alert includes position sizing based on validation:

| Tier | Position Size | Stop | Target |
|------|--------------|------|--------|
| 🏆 Institutional | 2-3% risk | Standard | Full |
| 🎯 Certain | 1.5-2% | Standard | Full |
| ✅ Proven | 1-1.5% | Standard | 75% |
| ⚠️ Validated | 0.5-1% | Tighter | 50% scale |

---

## 🧪 Testing

Run the test suite:

```bash
cd findcryptopairs/alpha_signals

# Test quality gates
python alert_system_v2_quality_gates.py

# Test Discord integration (without sending)
python discord_alerts_quality.py
```

---

## ⚠️ Important Notes

1. **Strategy ID is Critical**: Always use consistent strategy IDs
   - Good: `BTC_CME_GAP_V2`, `ETH_LONDON_BREAKOUT_5M`
   - Bad: `strategy_1`, `test_signal`

2. **Trade History Persistence**: Metrics saved to `strategy_metrics.json`
   - Back up this file
   - It tracks the validation state of all strategies

3. **RSVE Integration**: Works with your RSVE pipeline
   - Week 1 strategies auto-suppressed
   - Week 3+ strategies eligible for alerts

4. **Discord Rate Limits**: Quality gates help prevent spam
   - Fewer, higher-quality alerts
   - Better user experience

---

## 📞 Support

**Files:**
- `alert_system_v2_quality_gates.py` - Core quality logic
- `discord_alerts_quality.py` - Discord integration
- `QUALITY_ALERT_SETUP.md` - This guide

**Integration:** See `example_integration.py` for complete example.
