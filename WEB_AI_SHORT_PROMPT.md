# Web AI Short Prompt (Copy-Paste Ready)
## Fits in ChatGPT/Claude Character Limits

**Give this to any web AI:**

---

```
You are creating a trading strategy for the Baby Strat Incubator.

CONSTRAINTS:
- Output MUST be under 3000 tokens
- Code MUST be under 200 lines
- Strategy MUST be unique (not basic RSI/MACD/MA)

AVAILABLE STRATEGIES (DO NOT DUPLICATE):
- RSI mean reversion (5+ exist)
- MACD crossover (3+ exist)  
- Bollinger Bands (4+ exist)
- Simple momentum (exists)
- XGBoost ensemble (Mercury 2)
- Funding arbitrage (Tier 1)

WHITE SPACE (CREATE THESE):
- RSI + on-chain data (whale wallets)
- Multi-timeframe confluence
- Cross-asset correlations (BTC-SPX)
- Order book imbalance
- Session-based strategies

OUTPUT FORMAT:
```
## STRATEGY: [NAME]

CONCEPT: [1 sentence]

LOGIC:
- Entry: [condition]
- Exit: [TP/SL logic]
- Filter: [avoid bad trades]

UNIQUE: [How is this different from existing?]

CODE:
```python
[paste template below, fill in your logic]
```

PARAMETERS:
- [param]: [value] ([why])
```

CODE TEMPLATE (fill in):
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

class {YOUR_STRATEGY_NAME}Strategy:
    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.param1 = self.p.get('param1', default_value)
        # MAX 6 parameters
    
    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        if len(data) < 50:
            return []
        
        # YOUR INDICATOR CALCULATION
        indicator = self._calc(data)
        price = data['close'].iloc[-1]
        
        # YOUR ENTRY LOGIC
        if self._should_enter(indicator, price):
            return [Signal(
                symbol=symbol,
                direction="BUY",
                confidence=0.7,
                entry_price=price,
                take_profit=price * 1.02,
                stop_loss=price * 0.98,
                reason="your logic here"
            )]
        return []
    
    def _calc(self, data):
        # YOUR indicator
        pass
    
    def _should_enter(self, indicator, price):
        # YOUR condition
        pass

if __name__ == "__main__":
    data = pd.DataFrame({'close': np.random.randn(100).cumsum() + 50000,
                        'high': np.random.randn(100).cumsum() + 50100,
                        'low': np.random.randn(100).cumsum() + 49900})
    s = {YOUR_STRATEGY_NAME}Strategy()
    print(s.generate_signals(data))
```

RULES:
1. Code must run without errors
2. Max 6 parameters in __init__
3. Must include test in __main__
4. Strategy name must be descriptive
5. Explain WHY this is unique

YOUR TURN: Create a strategy following this format.
```

---

## After Web AI Responds

**Human copies the output, then asks IDE agent:**

```
I've received a strategy from a web AI. Please:

1. Save to: incubator/agents/web_ai/{strategy_name}.py
2. Check against EXISTING_STRATEGIES_INVENTORY.md for duplicates
3. Fix any syntax errors
4. Add missing imports
5. Verify the test runs
6. Create proper backtest wrapper

Strategy code:
[PASTE WEB AI OUTPUT HERE]
```

---

## Alternative: Concept-Only Mode

**If web AI hits character limit, use this:**

```
You are creating a trading strategy CONCEPT (code will be written later).

Output this format ONLY:

## STRATEGY CONCEPT: [NAME]

CORE IDEA: [1-2 sentences]

ENTRY LOGIC:
1. [Condition 1]
2. [Condition 2]
3. [Condition 3]

EXIT LOGIC:
- Take Profit: [how]
- Stop Loss: [how]

INDICATORS NEEDED:
- [Indicator 1]: [purpose]
- [Indicator 2]: [purpose]

WHY UNIQUE: [How is this different from RSI/MACD/Bollinger?]

BEST REGIME: [trending/ranging/volatile]

ESTIMATED PERFORMANCE:
- Win rate: [X%]
- Sharpe: [X.X]
- Max DD: [X%]

PARAMETERS:
- [param1]: [value]
- [param2]: [value]
```

**Then human asks IDE agent:**
```
Implement this strategy concept as working Python code:
[PASTE CONCEPT]
```

---

## Copy-Paste Checklist for Human

```markdown
- [ ] Web AI output received
- [ ] Saved to incubator/agents/web_ai/
- [ ] IDE agent verification requested
- [ ] IDE agent fixed any issues
- [ ] Backtest validation running
- [ ] Strategy submitted to pipeline
```
