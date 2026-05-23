# Baby Strat AI Prompt
## Use This Prompt to Generate Trading Strategies

---

## 🎯 YOUR MISSION

Create a **Baby Strat** - a new trading strategy that:
1. Is genuinely different from existing strategies
2. Follows the template format exactly
3. Can be validated through backtesting
4. Adds value to the existing ecosystem

---

## 📋 STEP-BY-STEP PROCESS

### STEP 1: Research What's Already Built

**READ THESE FILES FIRST:**
```
1. EXISTING_STRATEGIES_INVENTORY.md  ← START HERE
2. BABY_STRAT_GUIDE.MD
3. incubator/templates/hello_baby_strat.py  ← USE THIS TEMPLATE
```

**Ask yourself:**
- Does a similar strategy already exist? (Check inventory)
- What makes my approach different?
- Which "white space" category does this fit?

---

### STEP 2: Choose Your Strategy Type

**Select ONE primary category:**

| Category | Description | Example Idea |
|----------|-------------|--------------|
| **Mean Reversion** | Price returns to average | RSI + funding rate filter |
| **Momentum** | Trend continuation | Momentum + whale accumulation |
| **Breakout** | Escape from range | Volume profile + VWAP |
| **Arbitrage** | Price discrepancies | Cross-exchange funding |
| **ML-Based** | Pattern recognition | LSTM + on-chain features |
| **Alternative Data** | Non-price signals | Social sentiment + price |

**Your twist:** Add a UNIQUE filter or confirmation that existing strategies don't have.

---

### STEP 3: Define Core Logic

**Fill out this template:**

```markdown
Strategy Name: _______________
Primary Asset: [BTC/ETH/Crypto/Forex/Stocks]
Timeframe: [1h/4h/1d]

ENTRY CONDITIONS:
1. Primary indicator: _______________
2. Confirmation filter: _______________
3. Risk filter: _______________

EXIT CONDITIONS:
- Take Profit: _____ (ATR multiple / Fixed %)
- Stop Loss: _____ (ATR multiple / Fixed %)
- Time Exit: _____ (hours/days)

POSITION SIZING:
- Risk per trade: _____%
- Max concurrent: _____ positions

UNIQUE VALUE:
What makes this different from existing strategies?
→ _______________
```

---

### STEP 4: Write the Code

**Use this EXACT template structure:**

```python
"""
{STRATEGY_NAME} - Baby Strat
==========================

Created by: {AI_AGENT_NAME}
Date: {DATE}

Strategy Logic:
- Entry when: {DESCRIBE}
- Exit when: {DESCRIBE}
- Risk management: {DESCRIBE}

Unique Value Proposition:
{WHY THIS IS DIFFERENT}
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    """Required: Do not modify this class."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class {STRATEGY_NAME}Strategy:
    """
    Your strategy implementation.
    
    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Define all tunable parameters here.
        
        Args:
            params: Dictionary of parameters
        """
        self.params = params or {}
        
        # Example parameters - modify for your strategy
        self.lookback = self.params.get('lookback', 20)
        self.threshold = self.params.get('threshold', 30)
        self.tp_atr_mult = self.params.get('tp_atr_mult', 2.0)
        self.sl_atr_mult = self.params.get('sl_atr_mult', 1.5)
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.
        
        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair
            
        Returns:
            List of Signal objects (empty if no signal)
        """
        # Validate data
        if len(data) < self.lookback + 10:
            return []
        
        # YOUR LOGIC HERE
        # 1. Calculate indicators
        # 2. Check entry conditions
        # 3. Calculate TP/SL
        # 4. Return signal
        
        signals = []
        
        # Example structure:
        # if entry_condition_met:
        #     signals.append(Signal(
        #         symbol=symbol,
        #         direction="BUY",
        #         confidence=0.75,
        #         entry_price=current_price,
        #         take_profit=tp_price,
        #         stop_loss=sl_price,
        #         reason="Your logic here"
        #     ))
        
        return signals
    
    # Add any helper methods here
    # def _calculate_indicator(self, data):
    #     pass


# ==============================================================================
# TESTING - Required: Verify your strategy works
# ==============================================================================

if __name__ == "__main__":
    """Quick test with synthetic data."""
    
    # Create synthetic OHLCV data
    np.random.seed(42)
    n = 200
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, n)),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n)
    })
    
    # Test strategy
    strategy = {STRATEGY_NAME}Strategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")
    
    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
```

---

### STEP 5: Self-Validation Checklist

**Before submitting, verify:**

```markdown
## ✅ Code Quality
- [ ] Code runs without errors (`python strategy_name.py`)
- [ ] Returns correct Signal dataclass
- [ ] Handles edge cases (insufficient data, etc.)
- [ ] Has clear comments explaining logic

## ✅ Uniqueness
- [ ] Checked EXISTING_STRATEGIES_INVENTORY.md
- [ ] Can explain what's different
- [ ] Not just RSI/MACD/MA with different parameters
- [ ] Adds genuinely new logic

## ✅ Risk Management
- [ ] Has stop loss calculation
- [ ] Has take profit calculation
- [ ] Position sizing is reasonable
- [ ] Won't blow up account on bad streak

## ✅ Backtestable
- [ ] Uses only OHLCV data
- [ ] No future peeking
- [ ] Calculation uses proper window/sliding
- [ ] Can run on 1000+ bars
```

---

### STEP 6: Submit for Validation

**Package your strategy:**

```python
# Create submission
from incubator.shared_infra.sandbox import AgentSandbox

sandbox = AgentSandbox("your_agent_name")

# Write strategy code
with open("your_strategy.py") as f:
    code = f.read()

sandbox.write_strategy(
    filename="your_strategy_v1.py",
    code=code,
    metadata={
        "author": "your_name",
        "strategy_type": "momentum/mean_rev/breakout/etc",
        "unique_value": "what makes this different",
        "expected_regime": "trending/ranging/volatile"
    }
)

# Run validation pipeline
from incubator.validation.pipeline import ValidationPipeline

pipeline = ValidationPipeline()
report = pipeline.run_full_pipeline(
    agent_id="your_agent_name",
    strategy_name="your_strategy_v1",
    strategy_code=code,
    backtest_results=your_backtest_results
)

print(f"Validation Result: {report.result}")
print(f"Next Stage: {report.next_stage}")
```

---

## 🎨 EXAMPLE: GOOD vs BAD Strategies

### ❌ BAD: High Duplicate Risk

```python
# RSI Mean Reversion - TOO COMMON
if rsi < 30:
    buy()
elif rsi > 70:
    sell()

# Why bad: 5+ strategies already do exactly this
```

### ✅ GOOD: Unique Angle

```python
# RSI Mean Reversion with Funding Rate Filter
if rsi < 30 and funding_rate < -0.01:  # Extra filter
    buy()  # Only when oversold AND shorts are overleveraged

# Why good: Adds funding rate confirmation, different from basic RSI
```

### ❌ BAD: Too Complex

```python
# 47 indicators, 12 nested if statements
if ind1 and ind2 and ind3 and ind4 and ind5...:
    if ind6 or ind7 or ind8:
        if not ind9 and ind10 > threshold:
            buy()

# Why bad: Overfit, won't generalize
```

### ✅ GOOD: Simple but Unique

```python
# VWAP Deviation with Volume Confirmation
if price < vwap * 0.98 and volume > volume_ma * 2:
    buy()  # Price below VWAP on high volume = potential reversal

# Why good: Simple, interpretable, unique combination
```

---

## 🔴 COMMON MISTAKES TO AVOID

| Mistake | Why It's Bad | Fix |
|---------|--------------|-----|
| **Duplicate existing strategy** | Wastes resources, rejected by fingerprinter | Check inventory first |
| **Too many parameters** | Overfitting, poor generalization | Max 5-6 key parameters |
| **No stop loss** | Risk of ruin | Always include SL calculation |
| **Future peeking** | Cheating in backtest | Only use past data |
| **Too complex** | Hard to debug, overfit | Keep it simple |
| **No comments** | Others can't understand | Explain the logic |
| **Hardcoded values** | Not adaptable | Use params dict |

---

## 🎯 SUCCESS CRITERIA

Your strategy will PASS validation if:
- ✅ Sharpe ratio ≥ 1.0
- ✅ Win rate ≥ 45%
- ✅ Max drawdown ≤ 20%
- ✅ DSR probability ≥ 75% (not overfit)
- ✅ Uniqueness score < 90% similar to existing
- ✅ **Multi-pair verified** (passes on at least 1 of: BTC, ETH, SOL)

### Multi-Pair Testing Requirements

All strategies must be tested on **BTC, ETH, and SOL** to verify robustness:

| Pair | Test Direction | Criteria |
|------|----------------|----------|
| BTC | LONG / SHORT / BOTH | Sharpe ≥1.0, WR ≥45%, DD ≤25% |
| ETH | LONG / SHORT / BOTH | Sharpe ≥1.0, WR ≥45%, DD ≤25% |
| SOL | LONG / SHORT / BOTH | Sharpe ≥1.0, WR ≥45%, DD ≤25% |

**Multi-Pair Verification Status:**
- 🟢 **VERIFIED** - Strategy passes on at least one pair
- 🔴 **FAILED** - Strategy fails on all pairs (will be eliminated)

Strategies that fail multi-pair testing on BTC, ETH, and SOL are **eliminated** from the incubator.

Your strategy will FAIL if:
- ❌ Any of the above thresholds not met
- ❌ Code has errors
- ❌ Too similar to existing strategy
- ❌ No risk management
- ❌ **Fails multi-pair testing** (no passing config on BTC/ETH/SOL)

---

## 📚 RESOURCES

**Required Reading:**
1. `EXISTING_STRATEGIES_INVENTORY.md` - What already exists
2. `BABY_STRAT_GUIDE.MD` - How the incubator works
3. `incubator/templates/hello_baby_strat.py` - Template code

**Optional Reading:**
- `100_ALGORITHMS_MASTER_CATALOG.md` - For inspiration
- `strategy_catalog.md` - Detailed descriptions
- `docs/blueprints/2026-02-25_0818EST_DETAILED_BLUEPRINT.md` - System architecture

---

## 💡 FINAL TIP

> **"The best strategies solve a specific problem in a specific market condition."**

Instead of "make money in crypto", think:
- "Make money when BTC is range-bound and funding is negative"
- "Make money during high volatility with smart money confirmation"
- "Make money on DeFi tokens when governance activity spikes"

**Be specific. Be unique. Be backtestable.**

---

**Ready? Start with STEP 1: Read the inventory.**


---

## 🌐 WHERE YOUR STRATEGY ENDS UP

### The Full Journey

```
YOU create strategy
        │
        ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ STAGE 0: Sandbox │ ──► │ STAGE 1-2: Test  │ ──► │ STAGE 3: Graduate│
│ Private          │     │ Backtest + Paper │     │ Archive          │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────┐
                                               │ STAGE 4: LIVE    │
                                               │ Discord + Web    │
                                               │ 🌍 WORLDWIDE     │
                                               └──────────────────┘
```

### Timeline & Visibility

| Stage | Duration | Who Can See |
|-------|----------|-------------|
| **Sandbox** | Hours/days | 🔒 Only you |
| **Validation** | Minutes | 🔒 Automated system |
| **Paper Trading** | 30 days | 🔒 Automated system |
| **Graduated** | 1-7 days | 👁️ Team review |
| **Production** | Ongoing | 🌍 **WORLDWIDE** |

### What "Worldwide" Means:

**Discord Channel:**
- Real-time alerts for every pick
- Daily performance summaries
- Your agent name credited: "🎓 Strategy by kimi_01"

**Website Dashboard:**
- URL: `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/f/`
- Your strategy name in the UI
- Live pick tracking
- Performance charts

**GitHub Actions:**
- Runs every 30 minutes
- Auto-commits results
- Public commit history

### Requirements to Go Live:

**Automatic (You Control):**
- Write working strategy ✓
- Pass backtest validation (Sharpe ≥ 1.0, WR ≥ 45%) ✓
- Complete 30-day paper trading ✓

**Human Review (We Control):**
- Strategy selected for deployment
- GitHub Action configured
- Discord webhook added
- Dashboard page generated

**Timeline:** ~31 days from creation to worldwide deployment

---

## 💡 INCENTIVE

> **Create a great strategy → Get credited on a live trading system → Worldwide visibility**

Your name appears on:
- Every Discord alert
- Website dashboard
- GitHub commits
- Strategy metadata

**Read full details:** `BABY_STRAT_DEPLOYMENT_ROADMAP.md`
