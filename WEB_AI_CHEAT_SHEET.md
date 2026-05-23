# Web AI Cheat Sheet
## Quick Reference for Copy-Paste Workflow

---

## 🚀 30-Second Start

**Give web AI this prompt:**
```
Create a trading strategy following the format in BABY_STRAT_WEB_AI_GUIDE.md.

Requirements:
- Under 3000 tokens
- Not RSI/MACD/Bollinger (already exist)
- Use this template: [paste CODE TEMPLATE from guide]

Create something in the WHITE SPACE:
- RSI + on-chain (whale wallets)
- Multi-timeframe confluence  
- Cross-asset (BTC-SPX correlation)
- Order book imbalance
- Session-based (London/NY open)
```

---

## 📋 What to Copy from Web AI

### Good Output Looks Like:
```markdown
## STRATEGY: WhaleMomentum

CONCEPT: Momentum only when whales are buying

LOGIC:
- Entry: Price > SMA20 + whale inflow > 2x avg
- Exit: TP 3x ATR, SL 2x ATR

UNIQUE: Filters momentum by smart money

CODE:
```python
[class definition]
```

PARAMETERS:
- sma_period: 20
- whale_mult: 2.0
```

### Bad Output (Reject & Ask to Fix):
- ❌ Over 4000 tokens
- ❌ Over 300 lines of code
- ❌ Basic RSI strategy (duplicate)
- ❌ No test code
- ❌ No explanation of uniqueness

---

## 🔄 Your Workflow

### Step 1: Get Strategy from Web AI
```bash
# Copy their output
```

### Step 2: Save File
```bash
mkdir -p incubator/agents/web_ai/
nano incubator/agents/web_ai/strategy_name.py
# Paste web AI code
```

### Step 3: Ask IDE Agent to Verify
```
Verify this web AI strategy:

File: incubator/agents/web_ai/strategy_name.py

Check:
1. Duplicate against EXISTING_STRATEGIES_INVENTORY.md
2. Syntax errors
3. Missing imports
4. Logic flaws
5. Backtest readiness

Fix any issues and save corrected version.
```

### Step 4: Run Validation
```bash
cd incubator
python -m validation.pipeline --agent web_ai --strategy strategy_name
```

### Step 5: Monitor
- Backtest results: Check validation report
- Paper trading: 30 days automated
- Graduation: Team review

---

## 🎯 Quick Decision Tree

```
Web AI gives you output
        │
        ├── Too long (> 4000 tokens)?
        │       ├── YES → Ask for CONCEPT ONLY format
        │       └── NO → Continue
        │
        ├── Duplicate strategy (RSI/MACD/MA)?
        │       ├── YES → Reject, ask for WHITE SPACE
        │       └── NO → Continue
        │
        ├── Has syntax errors?
        │       ├── YES → IDE agent fixes
        │       └── NO → Continue
        │
        └── Ready for validation
                └── Submit to pipeline
```

---

## 📊 White Space Quick Pick

**If web AI can't think of anything unique, give them one of these:**

| Strategy Idea | Core Logic | Why Unique |
|---------------|------------|------------|
| **Whale RSI** | RSI < 35 + whale inflow > 2x | Filters false RSI signals |
| **Funding Momentum** | Momentum only when funding < -0.01% | Shorts pay longs |
| **London Open Breakout** | Breakout in first 2h of London | Session volatility |
| **BTC-SPX Divergence** | Trade when correlation breaks | Cross-asset edge |
| **ATR Position Sizing** | Scale size inversely to ATR | Risk management |
| **Fear-Greed Mean Rev** | Buy extreme fear, sell greed | Sentiment + price |

---

## 🐛 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Web AI output cut off | Ask for "CONCEPT ONLY" format |
| Code has syntax errors | IDE agent auto-fixes |
| Strategy too simple | Ask to add one filter/condition |
| Duplicate detected | Point to WHITE SPACE section |
| No test code | IDE agent adds test block |
| Character limit hit | Break into 2 messages or use concept mode |

---

## 📝 Credit Tracking

**When web AI creates strategy:**
- Save their agent name in metadata
- File: `incubator/agents/web_ai/strategy_name.py.meta.json`

```json
{
  "origin": "web_ai_chatgpt",
  "creator": "human_copy_paste",
  "verified_by": "ide_agent_kimi",
  "date": "2026-02-26"
}
```

**Original web AI gets credit even if IDE agent fixes code.**

---

## ⚡ Speed Tips

1. **Bookmark this page** for quick reference
2. **Keep template handy** in text file for copying
3. **Have inventory open** to check duplicates fast
4. **Use IDE agent** for all verification (don't do manually)
5. **Batch process** - collect 5 strategies, then verify all at once

---

## 🔗 Essential Links

| File | Purpose | When to Use |
|------|---------|-------------|
| `EXISTING_STRATEGIES_INVENTORY.md` | Check duplicates | Before accepting strategy |
| `BABY_STRAT_WEB_AI_GUIDE.md` | Full web AI guide | Detailed reference |
| `WEB_AI_SHORT_PROMPT.md` | Copy-paste prompt | Giving to new web AI |
| `BABY_STRAT_DEPLOYMENT_ROADMAP.md` | Where it ends up | Explaining to web AI |
| `incubator/templates/hello_baby_strat.py` | Code template | Web AI starting point |

---

## ✅ Success Checklist

```markdown
Web AI Strategy Accepted:
- [ ] Under 3000 tokens
- [ ] Not a duplicate
- [ ] Has test code
- [ ] Explains uniqueness
- [ ] IDE agent verified
- [ ] Saved to incubator/agents/web_ai/
- [ ] Validation pipeline running
- [ ] Web AI credited in metadata
```

---

**Remember: Web AI creates concept → You copy-paste → IDE agent verifies → Incubator tests → Worldwide deployment** 🚀
