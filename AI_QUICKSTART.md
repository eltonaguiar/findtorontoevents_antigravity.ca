# AI Quickstart Guide
## Create Your First Baby Strat in 5 Minutes

---

## 🚀 5-STEP QUICKSTART

### Step 1: Read (2 minutes)
```bash
# Read these THREE files in order:
1. EXISTING_STRATEGIES_INVENTORY.md     # What's already built
2. BABY_STRAT_GUIDE.MD                  # How the system works  
3. incubator/templates/hello_baby_strat.py  # Copy this template
```

### Step 2: Check (1 minute)
```bash
# Ask yourself:
- Does my idea already exist in the inventory?
- What's my unique angle?
- Which "white space" category?

# If unsure, check:
grep -i "your_idea" EXISTING_STRATEGIES_INVENTORY.md
```

### Step 3: Create (5 minutes)
```bash
# Copy template
cp incubator/templates/hello_baby_strat.py incubator/agents/YOUR_NAME/my_strategy_v1.py

# Edit the file:
# - Change class name
# - Modify generate_signals() logic
# - Add your unique twist
# - Test: python my_strategy_v1.py
```

### Step 4: Validate (2 minutes)
```python
from incubator.shared_infra.sandbox import AgentSandbox
from incubator.validation.pipeline import ValidationPipeline

# Create sandbox
sandbox = AgentSandbox("YOUR_NAME")

# Write strategy
with open("my_strategy_v1.py") as f:
    code = f.read()
sandbox.write_strategy("my_strategy_v1.py", code)

# Run backtest (you implement this)
results = run_backtest(code)  # Returns metrics dict

# Submit for validation
pipeline = ValidationPipeline()
report = pipeline.run_full_pipeline(
    agent_id="YOUR_NAME",
    strategy_name="my_strategy_v1",
    strategy_code=code,
    backtest_results=results
)

print(f"Result: {report.result}")  # PASS / FAIL / HOLD
```

### Step 5: Iterate (ongoing)
```bash
# If PASS → Paper trading for 30 days
# If FAIL → Read report.reason, fix, resubmit
# If HOLD → Gather more backtest data
```

---

## 📁 FILE REFERENCE

| File | Purpose | When to Read |
|------|---------|--------------|
| `EXISTING_STRATEGIES_INVENTORY.md` | What's already built | **BEFORE creating anything** |
| `BABY_STRAT_GUIDE.MD` | System architecture | Before coding |
| `BABY_STRAT_AI_PROMPT.md` | Detailed creation guide | While coding |
| `incubator/templates/hello_baby_strat.py` | Copy-paste template | Starting point |
| `AI_QUICKSTART.md` | This file | Quick reference |

---

## ✅ CHECKLIST BEFORE CODING

```markdown
- [ ] Read EXISTING_STRATEGIES_INVENTORY.md
- [ ] Identified unique angle not in inventory
- [ ] Checked similar strategies don't exist
- [ ] Have clear entry/exit logic
- [ ] Know how to calculate indicators
- [ ] Understand risk management (TP/SL)
```

---

## 🎯 DECISION TREE

```
START
  │
  ▼
Read EXISTING_STRATEGIES_INVENTORY.md
  │
  ├─► Similar strategy exists? ──► STOP, find new angle
  │
  └─► Idea is unique? ──► Continue
            │
            ▼
    Does it fit white space?
            │
    ├─► Yes (alternative data, cross-asset, etc.)
    │       │
    │       ▼
    │   Write code using template
    │       │
    │       ▼
    │   Test locally
    │       │
    │       ▼
    │   Submit to validation
    │       │
    │       ▼
    │   PASS → Paper trading
    │   FAIL → Iterate
    │
    └─► No (another RSI strategy?)
            │
            ▼
        Add UNIQUE filter
        (RSI + funding rate?
         RSI + whale movement?)
            │
            ▼
        Continue to write code
```

---

## 🆘 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| "Idea already exists" | Add a unique filter or different asset class |
| "Code won't run" | Check `hello_baby_strat.py` template, compare line-by-line |
| "Validation failed" | Read `report.reason`, likely Sharpe < 1.0 or overfit |
| "Too similar to existing" | Use fingerprinter, modify logic significantly |
| "Don't know what to build" | Check "White Space" section in inventory |

---

## 💬 EXAMPLE WORKFLOW

**AI Agent: kimi_01**

```
1. Reads EXISTING_STRATEGIES_INVENTORY.md
   → Sees RSI strategies exist but most are basic
   
2. Finds "White Space" section
   → "On-chain metrics underexplored"
   
3. Idea: RSI + Whale Movement Confirmation
   → Buy when RSI < 30 AND whale inflows spike
   
4. Checks inventory again
   → No strategy combines RSI + on-chain
   
5. Creates strategy using template
   → Implements RSI calculation
   → Adds mock whale data reader
   → Combines signals
   
6. Tests locally
   → python my_strategy.py → 3 signals generated ✓
   
7. Submits to validation
   → Backtest shows Sharpe 1.2, WR 52% ✓
   → Passes uniqueness check ✓
   
8. Result: PASS → Paper trading for 30 days
```

---

## 📊 EXPECTED TIMELINE

| Phase | Duration | Your Action |
|-------|----------|-------------|
| Research | 10 min | Read inventory, find white space |
| Coding | 20 min | Write strategy using template |
| Testing | 10 min | Run local tests, fix bugs |
| Validation | 5 min | Submit, wait for result |
| **Total to first result** | **~45 min** | |
| Paper Trading | 30 days | Automated, you wait |
| Promotion | 1 day | If paper trading succeeds |

---

## 🎓 LEARNING PATH

**Beginner:**
1. Copy `hello_baby_strat.py` exactly
2. Modify just the thresholds (RSI 30→25)
3. Submit and see results
4. Learn from feedback

**Intermediate:**
1. Add ONE unique filter to existing concept
2. (Example: Bollinger Bands + volume confirmation)
3. Validate uniqueness carefully
4. Iterate based on backtest metrics

**Advanced:**
1. Explore white space categories
2. Create truly novel combinations
3. Multi-timeframe or cross-asset strategies
4. ML-enhanced signal generation

---

## 🔗 KEY CONCEPTS

**Baby Strat:** New unproven strategy in sandbox
**Validation Gates:** Backtest → Paper → Production (3 stages)
**Fingerprinter:** Detects duplicate/similar strategies
**White Space:** Strategy categories with few existing implementations

---

## 📝 REMEMBER

> **"Don't reinvent the wheel. Reinvent the engine."**

- ✅ DO: Add unique filters, combine concepts creatively
- ❌ DON'T: Copy existing strategies with different parameters
- ✅ DO: Focus on white space areas
- ❌ DON'T: Create another basic RSI/MACD strategy
- ✅ DO: Make it backtestable and interpretable
- ❌ DON'T: Overfit with 20 parameters

---

**Ready? Start here:**
```bash
cat EXISTING_STRATEGIES_INVENTORY.md
```
