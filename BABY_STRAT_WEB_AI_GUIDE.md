# Baby Strat Guide for Web-Only AIs
## Copy-Paste Strategy Creation (Character Limit Optimized)

**For:** AIs without filesystem access (ChatGPT web, Claude web, etc.)  
**Method:** Human copy-pastes your code, IDE agent verifies  
**Character Limit:** Optimized for ~4000 token outputs

---

## 🎯 How This Works (Web AI → Human → IDE Agent)

```
WEB AI (You)
    │
    ├── Generate strategy in chunks
    ├── Use short format below
    └── Output fits in character limit
            │
            ▼
    HUMAN (Copy-Pastes)
            │
            ├── Copies your code
            ├── Pastes into project
            └── Runs IDE agent (Kimi/Cursor)
                    │
                    ▼
    IDE AGENT (Verifies)
            │
            ├── Checks for duplicates
            ├── Fixes syntax errors
            ├── Adds missing imports
            └── Validates logic
                    │
                    ▼
    INCUBATOR (Tests)
            │
            ├── Backtest validation
            ├── Paper trading
            └── Graduation
```

---

## 📏 OUTPUT FORMAT (Use This Template)

**CRITICAL:** Stay under 3000-4000 tokens. Use CONCISE code.

```markdown
## STRATEGY: {NAME}

### CONCEPT (1-2 sentences)
{What does this do? What's unique?}

### LOGIC
- Entry: {condition}
- Exit: {TP/SL method}
- Filter: {what avoids bad trades}

### WHY UNIQUE
{How is this different from RSI/Bollinger/MACD strategies?}

### CODE
```python
{MINIMAL working code - see template below}
```

### PARAMETERS
- {param1}: {value} ({why})
- {param2}: {value} ({why})

### EXPECTED REGIME
{trending/ranging/volatile}
```

---

## 📝 CODE TEMPLATE (Ultra-Concise)

**Target:** Under 150 lines, under 3000 tokens

```python
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class {STRATEGY_NAME}Strategy:
    """{ONE_LINE_DESCRIPTION}"""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        # MAX 6 PARAMETERS - keep it simple
        self.lookback = self.p.get('lookback', 20)
        self.threshold = self.p.get('threshold', 30)
        self.tp = self.p.get('tp_atr', 2.0)
        self.sl = self.p.get('sl_atr', 1.5)
    
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.lookback + 5:
            return []
        
        # Calculate 1-2 indicators max
        indicator = self._calc_indicator(data)
        price = data['close'].iloc[-1]
        
        # Entry logic (keep it simple)
        if self._entry_condition(indicator, price):
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=0.7,
                entry_price=price,
                take_profit=price * 1.02,
                stop_loss=price * 0.98,
                reason="{YOUR_LOGIC}"
            )]
        return []
    
    def _calc_indicator(self, data: pd.DataFrame):
        # ONE indicator calculation
        pass
    
    def _entry_condition(self, indicator, price):
        # ONE condition
        pass

# Test
if __name__ == "__main__":
    # Minimal test
    data = pd.DataFrame({
        'close': np.random.randn(100).cumsum() + 50000,
        'high': np.random.randn(100).cumsum() + 50100,
        'low': np.random.randn(100).cumsum() + 49900,
    })
    s = {STRATEGY_NAME}Strategy()
    print(s.generate_signals(data))
```

---

## ❌ STRATEGIES TO AVOID (Already Exist)

**DO NOT create these (high duplicate risk):**

| Strategy Type | Why Not | Existing Location |
|---------------|---------|-------------------|
| RSI < 30 buy, > 70 sell | 5+ exist | Various files |
| MACD crossover | 3+ exist | ml_battleground/ |
| Bollinger Band bounce | 4+ exist | alpha_engine/ |
| MA crossovers | 6+ exist | Multiple locations |
| Simple momentum (past returns) | Competition has it | STOCKS/competition/ |
| Basic breakout | Breakout Arena exists | breakout_arena/ |
| Funding rate arbitrage | Tier 1 strategy | KIMI_CLAW_RESEARCH/ |
| XGBoost ensemble for crypto | Mercury 2 already | crypto_signal_engine/ |

---

## ✅ WHITE SPACE (Safe to Explore)

**These areas have FEWER existing strategies:**

### 1. On-Chain + Price Combinations
- Whale wallet movements + RSI
- Exchange inflows + momentum
- Network activity + trend

### 2. Cross-Asset Correlations
- BTC-SPX correlation breakdowns
- DXY impact on crypto
- Gold-BTC flight to quality

### 3. Order Book / Microstructure
- Bid-ask imbalance signals
- Order book depth changes
- Liquidation cluster detection

### 4. Alternative Timeframes
- Multi-timeframe confluence (4h + 1h alignment)
- Session-based (London/NY open)
- Weekend vs weekday patterns

### 5. Risk-Adjusted Signals
- Volatility regime detection first
- Position sizing based on Kelly
- Drawdown recovery systems

---

## 🔧 IF CODE IS TOO LONG (Character Limit Hit)

**Option A: Output Strategy Concept Only**

```markdown
## STRATEGY CONCEPT: {NAME}

### LOGIC
{Describe in pseudocode - bullet points}

### KEY INNOVATION
{What's unique - 2 sentences}

### INDICATORS NEEDED
- {indicator1}: {purpose}
- {indicator2}: {purpose}

### ENTRY CONDITIONS
1. {condition}
2. {condition}
3. {condition}

### EXIT CONDITIONS
- TP: {logic}
- SL: {logic}

### PARAMETERS
- {param1}: {suggested value}
- {param2}: {suggested value}

### EXPECTED PERFORMANCE
- Best in: {market regime}
- Win rate estimate: {X%}
- Sharpe estimate: {X.X}
```

**Then human says to IDE agent:**
> "Implement this strategy concept: [paste concept above]"

---

## 📋 HUMAN COPY-PASTE WORKFLOW

### Step 1: You (Web AI) Generate
Use format above, stay under 3000 tokens

### Step 2: Human Copies
```bash
# Create file
touch incubator/agents/web_ai/strategy_v1.py

# Paste your code
```

### Step 3: IDE Agent Verifies
Human prompts IDE agent:
```
Check this strategy for:
1. Duplicates against EXISTING_STRATEGIES_INVENTORY.md
2. Syntax errors
3. Missing imports
4. Logic flaws
5. Backtest readiness

File: incubator/agents/web_ai/strategy_v1.py
```

### Step 4: IDE Agent Fixes
IDE agent will:
- Add proper imports
- Fix indentation
- Add error handling
- Verify against inventory
- Create proper test

### Step 5: Multi-Pair Testing (NEW)

All strategies are tested on **BTC, ETH, and SOL**:

```bash
# Multi-pair validation
python run_multi_pair_testing.py \
  --strategy your_strategy \
  --pairs BTC,ETH,SOL
```

**Requirements:**
- Must pass on at least 1 pair (Sharpe≥1.0, WR≥45%, DD≤25%)
- Best pair/direction is tracked
- Strategies failing all pairs are eliminated

### Step 6: Submit to Validation
```bash
python -m incubator.validation.run_pipeline \
  --agent web_ai \
  --strategy strategy_v1
```

---

## 🎯 EXAMPLE: Complete Short Output

**Example Strategy (Under 200 lines, ~2500 tokens):**

```markdown
## STRATEGY: WhaleRSI_Confirmation

### CONCEPT
RSI mean reversion ONLY when whale wallets are accumulating (on-chain confirmation).

### LOGIC
- Entry: RSI < 35 AND whale inflow > 2x average
- Exit: TP 2x ATR, SL 1.5x ATR
- Filter: Only trade when funding rate negative (shorts overleveraged)

### WHY UNIQUE
Basic RSI strategies get chopped. Adding whale confirmation filters out false signals during genuine sell-offs.

### CODE
```python
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class WhaleRSIConfirmationStrategy:
    """RSI + whale accumulation confirmation."""
    
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.rsi_period = self.p.get('rsi_period', 14)
        self.rsi_threshold = self.p.get('rsi_threshold', 35)
        self.whale_mult = self.p.get('whale_mult', 2.0)
        self.tp_atr = self.p.get('tp_atr', 2.0)
        self.sl_atr = self.p.get('sl_atr', 1.5)
    
    def generate_signals(self, data: pd.DataFrame, whale_data: pd.Series = None, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < self.rsi_period + 10 or whale_data is None:
            return []
        
        rsi = self._rsi(data['close'], self.rsi_period)
        atr = self._atr(data)
        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Whale confirmation
        whale_avg = whale_data.rolling(24).mean().iloc[-1]
        whale_current = whale_data.iloc[-1]
        whale_confirmed = whale_current > whale_avg * self.whale_mult
        
        if current_rsi < self.rsi_threshold and whale_confirmed:
            confidence = min((self.rsi_threshold - current_rsi) / self.rsi_threshold * 0.8 + 0.2, 0.95)
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"RSI {current_rsi:.1f} + Whale {whale_current:.0f} > {whale_avg:.0f}"
            )]
        return []
    
    def _rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        return tr.rolling(period).mean()

if __name__ == "__main__":
    data = pd.DataFrame({
        'close': np.random.randn(100).cumsum() * 1000 + 50000,
        'high': np.random.randn(100).cumsum() * 1000 + 50100,
        'low': np.random.randn(100).cumsum() * 1000 + 49900,
    })
    whale = pd.Series(np.random.randn(100) * 100 + 1000)
    s = WhaleRSIConfirmationStrategy()
    signals = s.generate_signals(data, whale)
    print(f"Signals: {len(signals)}")
    for sig in signals:
        print(f"{sig.direction} {sig.symbol} @ {sig.entry_price} - {sig.reason}")
```

### PARAMETERS
- rsi_period: 14 (standard)
- rsi_threshold: 35 (more extreme than 30 for better confirmation)
- whale_mult: 2.0 (whale flow must be 2x average)
- tp_atr: 2.0 (2x ATR take profit)
- sl_atr: 1.5 (1.5x ATR stop loss)

### EXPECTED REGIME
Best in: Ranging markets with smart money accumulation (not trending).
```

**Token count:** ~2200 tokens ✅

---

## ⚠️ COMMON MISTAKES (Web AI)

| Mistake | Fix |
|---------|-----|
| Outputting 500+ lines | Keep under 200 lines max |
| Including long docstrings | One-liner docstrings only |
| Printing debug info | Remove print statements |
| Complex nested classes | Single class only |
| Multiple strategies in one | One strategy per output |
| No test code | Always include `if __name__ == "__main__"` |

---

## ✅ CHECKLIST FOR WEB AI OUTPUT

```markdown
- [ ] Under 3000 tokens
- [ ] Under 200 lines of code
- [ ] Includes Signal dataclass
- [ ] Has __init__ with parameters
- [ ] Has generate_signals method
- [ ] Includes minimal test
- [ ] Explains what's unique
- [ ] Avoids duplicate strategies (checked inventory)
- [ ] Clear entry/exit logic
- [ ] 6 or fewer parameters
```

---

## 🚀 QUICK START FOR WEB AIs

**If you have 5 minutes:**
1. Read EXISTING_STRATEGIES_INVENTORY.md (check what's already built)
2. Pick a "white space" area
3. Use template above
4. Output concise code (< 3000 tokens)
5. Human will handle the rest

**If you hit character limit:**
1. Output STRATEGY CONCEPT format instead
2. IDE agent will implement
3. You still get credit as originator

---

**Your goal:** Create unique, backtestable strategies that fit in a chat window.

**Human's job:** Copy, verify with IDE agent, submit to incubator.

**Result:** Worldwide deployment if it works! 🚀
---

## 🌐 WEB AI PROMPT - Copy This to Get Strategies

**Use this prompt with ChatGPT, Claude, or any web AI to generate baby strategies:**

---

### 📋 COPY-PASTE PROMPT (Start Here)

```markdown
You are an expert quantitative trading strategist. Create baby trading strategies for cryptocurrency markets (BTC, ETH, SOL).

## CONTEXT

We are building a portfolio of "baby strategies" - small, focused algorithms that:
- Target Sharpe Ratio >= 1.0
- Win Rate >= 45%
- Max Drawdown <= 25%
- Trade on 1h, 4h, or 1d timeframes
- Use only price/volume data (no external APIs)

## REFERENCE FILES (View these for context)

Current Bundle Registry (what we track):
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_REGISTRY.md

Current Baby Strategies (existing code to avoid duplication):
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/baby_strategies

Cursor AI Strategies (advanced examples):
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/incubator/agents/cursor_ai

Strategy Inventory (avoid duplicates):
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/incubator/EXISTING_STRATEGIES_INVENTORY.md

## WHAT WE WANT

Create 1-3 NEW baby strategies that are:

1. **UNIQUE** - Not basic RSI/MACD/Bollinger (we have those)
2. **FOCUSED** - One clear edge, not 10 conditions
3. **BACKTESTABLE** - Uses only OHLCV data
4. **SIMPLE** - Under 200 lines of Python

## SIGNAL TYPES WE NEED

**Priority 1: Multi-Timeframe Confluence**
- Strategies that align 2+ timeframes (e.g., 4h trend + 1h entry)
- Higher timeframe filter + lower timeframe trigger

**Priority 2: Volume-Confirmed Patterns**
- Breakouts with volume surge confirmation
- Reversals with volume divergence

**Priority 3: Microstructure Edge**
- Bid-ask imbalance proxies
- Liquidation wick patterns
- Funding rate regime filters

**Priority 4: Cross-Asset Signals**
- BTC leading ETH/SOL
- DXY inverse correlation
- SPX correlation breakdowns

## STRATEGY REQUIREMENTS

```python
# Required structure:
from dataclasses import dataclass
from typing import List
import pandas as pd
import numpy as np

@dataclass
class Signal:
    symbol: str
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0-1.0
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str

class YourStrategyName:
    def __init__(self, params=None):
        self.p = params or {}
        # MAX 6 parameters
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        # Returns list of Signal objects
        pass
```

## OUTPUT FORMAT

For each strategy, provide:

### STRATEGY: {Name}

**Concept:** 1-2 sentence description

**Why Unique:** How is this different from standard indicators?

**Logic:**
- Entry condition:
- Exit condition (TP/SL):
- Filter (what to avoid):

**Parameters:** (max 6)
- param1: default_value (purpose)

**Code:**
```python
[Your code here - under 200 lines]
```

**Expected Regime:** trending/ranging/volatile

---

## AVOID THESE (Already Exist)

- Basic RSI overbought/oversold
- MACD crossovers
- Simple MA crossovers
- Bollinger Band bounces without confirmation

## EXAMPLES OF GOOD UNIQUE CONCEPTS

✓ "ADX trend strength + volume confirmation for breakout entries"
✓ "Multi-timeframe RSI alignment (4h oversold + 1h turning up)"
✓ "Volatility expansion after contraction (squeeze breakout)"
✓ "Session-based momentum (London/NY open continuation)"
✓ "Liquidation wick + volume spike exhaustion pattern"

Create your strategies now. Focus on SIGNAL QUALITY over complexity.
```

---

### 📎 DIRECT FILE LINKS FOR REFERENCE

| File | Purpose | GitHub Link |
|------|---------|-------------|
| **Bundle Registry** | See all active bundles | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_REGISTRY.md |
| **Baby Strategies** | Existing baby strategies | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/baby_strategies |
| **Cursor AI Agents** | Advanced strategy examples | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/incubator/agents/cursor_ai |
| **Strategy Inventory** | List of all strategies (avoid duplicates) | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/incubator/EXISTING_STRATEGIES_INVENTORY.md |
| **Baby Bundle Guide** | Full documentation | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_GUIDE.md |
| **Bundle Database** | Live SQLite DB with trades | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/battleground/data/bundle_babies.db |

---

### 🎯 BUNDLE CREATION PROMPT (Advanced)

```markdown
## BUNDLE CREATION PROMPT

Create a baby bundle from 2-4 strategies that share:
- Same SYMBOL SCOPE (single vs multi vs broad)
- Same TIMEFRAME SCOPE (single vs partial vs multi)
- Same DIRECTION BIAS (long vs short vs both)

Check BABY_BUNDLE_REGISTRY.md first to avoid duplicate classifications.

**Bundle Requirements:**
1. Each strategy must pass Tier 1 on at least 1 pair (BTC/ETH/SOL)
2. Combined Sharpe should be >= 2.0
3. Max drawdown per strategy <= 25%
4. At least 12+ trades per strategy

**Output Format:**
```yaml
Bundle Name: {Symbol}_{Timeframe}_{Direction}
Classification:
  Symbol Scope: {single/multi/broad}
  Timeframe Scope: {single/partial/multi}
  Direction Bias: {long/short/both}

Strategies:
  1. {strategy_name}
     - Best Pair: {pair}
     - Best Timeframe: {tf}
     - Sharpe: {X.XX}
     - Win Rate: {XX}%
     - Max DD: {X}%

Aggregated Metrics:
  Avg Sharpe: {X.XX}
  Avg Win Rate: {XX}%
  Max Drawdown: {X}%
```
```

---

## ✅ AFTER WEB AI GENERATES STRATEGY

**Human workflow:**

1. **Copy the code** from web AI
2. **Create file:** `incubator/agents/web_ai/{strategy_name}.py`
3. **Paste and save**
4. **Run IDE agent:** "Check this strategy for duplicates, syntax, logic"
5. **Run backtest:** `python run_multi_pair_testing.py --strategy {name}`
6. **Add to bundle:** If it passes, add to BABY_BUNDLE_REGISTRY.md

---

*Last Updated: 2026-02-27*


---

## 🔗 Quick Links

- [Bundle Registry](BABY_BUNDLE_REGISTRY.md) - All active bundles
- [Ideas & Feedback](BABY_IDEAS.md) - Community contributions
- [Baby Bundle Guide](BABY_BUNDLE_GUIDE.md) - System documentation
- [Strategy Inventory](incubator/EXISTING_STRATEGIES_INVENTORY.md) - Avoid duplicates

---

*Last Updated: 2026-02-27*