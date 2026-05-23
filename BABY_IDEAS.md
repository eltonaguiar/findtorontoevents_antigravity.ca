# Baby Strategy Ideas & Feedback Log
## Community Contributions for Strategy Improvement

**Purpose:** A living document where AIs and humans can contribute ideas, feedback, and improvements to the baby strategy system.

---

## 📝 How to Contribute

When adding an entry, include:

```markdown
### YYYY-MM-DD HH:MM - [AI Model/Name]

**Category:** [IDEA | FEEDBACK | BUG | IMPROVEMENT | STRATEGY_CONCEPT]

**Summary:** One-line summary

**Details:**
Detailed explanation of the idea, feedback, or issue.

**Proposed Solution:** (if applicable)
How to address this.

**Files Affected:** (if applicable)
- `file_path.py` - what needs changing

**Priority:** [LOW | MEDIUM | HIGH | CRITICAL]
```

---

## 🎯 Active Ideas & Feedback

---

### 2026-02-27 23:30 - Kimi Code

**Category:** IMPROVEMENT

**Summary:** Create standardized web AI prompt for strategy generation

**Details:**
Developed comprehensive prompt for web AIs (ChatGPT, Claude) to generate baby strategies. Includes:
- Direct GitHub links to all reference files
- Clear requirements (Sharpe >= 1.0, WR >= 45%, DD <= 25%)
- Priority signal types (multi-timeframe, volume-confirmed, microstructure)
- What to avoid (basic RSI/MACD duplicates)
- Bundle creation guidelines

**Proposed Solution:**
Prompt added to BABY_STRAT_WEB_AI_GUIDE.md. Web AIs can now generate strategies without filesystem access.

**Files Affected:**
- `BABY_STRAT_WEB_AI_GUIDE.md` - Added "WEB AI PROMPT" section

**Priority:** MEDIUM

---

### 2026-02-27 23:25 - Cursor Agent

**Category:** IMPROVEMENT

**Summary:** Database normalization for bundle enum values

**Details:**
Fixed enum drift in bundle_babies.db where old values like 'partial_multi_timeframe' and 'both' were blocking `bundle_baby_system.py --update-battleground` from running cleanly.

**Proposed Solution:**
Normalized enum values to current standard values:
- `partial_multi_timeframe` → `partial_timeframe`
- `both` → `long_only` (for bundles that were actually long-only)

**Files Affected:**
- `battleground/data/bundle_babies.db` - Enum value updates

**Priority:** HIGH

---

### 2026-02-27 23:15 - Kimi Code

**Category:** BUG

**Summary:** Bundle documentation duplication between files

**Details:**
Discovered that bundle details were being duplicated between BABY_BUNDLE_GUIDE.md and BUNDLE_REGISTRY.md. This creates maintenance overhead and potential for inconsistencies.

**Proposed Solution:**
1. BABY_BUNDLE_GUIDE.md = System guide (how it works)
2. BUNDLE_REGISTRY.md = Canonical bundle list (what exists)
3. Added AI notes at top of both files explaining the separation
4. Updated all cross-references

**Files Affected:**
- `BABY_BUNDLE_GUIDE.md` - Refactored to be guide-only
- `BUNDLE_REGISTRY.md` - Made canonical registry

**Priority:** MEDIUM

---

### 2026-02-27 23:00 - Kimi Code

**Category:** STRATEGY_CONCEPT

**Summary:** MIRACLE Bundle concept - multi-symbol multi-timeframe

**Details:**
Proposed creating a "MIRACLE" bundle classification for strategies that pass on multiple symbols AND multiple timeframes. These would be the highest-quality bundles with:
- Multi-symbol robustness (BTC/ETH/SOL)
- Multi-timeframe robustness (1h/4h/1d)
- Both direction capability

Target metrics: Sharpe > 3.0, WR > 60%, DD < 5%

**Proposed Solution:**
Created initial MIRACLE bundle in database with:
- `crypto_multiframe_breakout_pulse_v1` (5m/15m focus)
- `crypto_liquidation_flow_exhaustion_v1` (15m/1h focus)
- `crypto_multiframe_regime_router_v1` (multi-timeframe)

**Files Affected:**
- `bundle_baby_system.py` - Bundle creation logic
- `battleground/data/bundle_babies.db` - Added MIRACLE bundle

**Priority:** HIGH

---

### 2026-02-27 22:45 - Cursor Agent

**Category:** IDEA

**Summary:** Tier 2 standardized testing for all strategies

**Details:**
All strategies should go through standardized multi-timeframe testing:
- Tier 1: Multi-pair validation (BTC, ETH, SOL)
- Tier 2: Multi-timeframe validation (1h, 4h, 1d)

Only strategies passing both tiers should be eligible for bundles.

**Proposed Solution:**
Implemented tiered testing system:
- `tiered_backtest_system.py` - Main testing framework
- `incubator/testing/backtest_utils.py` - Shared utilities
- Results stored in `battleground/data/tiered_backtest_results_*.json`

**Files Affected:**
- `tiered_backtest_system.py` - Created
- `incubator/testing/backtest_utils.py` - Created

**Priority:** HIGH

---

## 💡 Strategy Concepts (Awaiting Implementation)

---

### 2026-02-27 22:30 - Kimi Code

**Category:** STRATEGY_CONCEPT

**Summary:** On-Chain Volume Confirmation Strategy

**Details:**
Use exchange inflow/outflow data to confirm price-based signals:
- Entry: RSI oversold + exchange outflows (accumulation)
- Exit: RSI overbought + exchange inflows (distribution)
- Filter: Only trade when whale movements align with signal

**Data Requirements:**
- On-chain exchange flow data (Glassnode, CryptoQuant APIs)
- Requires API key and rate limit management

**Expected Performance:**
- Should filter out 30-40% of false RSI signals
- Target: Sharpe 1.5+, WR 55%+

**Priority:** MEDIUM
**Status:** Awaiting data source integration

---

### 2026-02-27 22:15 - Cursor Agent

**Category:** STRATEGY_CONCEPT

**Summary:** Cross-Asset Momentum Divergence

**Details:**
Trade BTC/ETH/SOL based on momentum divergences:
- When BTC momentum > ETH momentum, long ETH (catch-up trade)
- When SOL momentum > BTC momentum, long BTC (rotation trade)
- Use relative strength index between pairs

**Logic:**
```
rsi_btc = calculate_rsi(btc_data)
rsi_eth = calculate_rsi(eth_data)

if rsi_btc > 60 and rsi_eth < 40:
    signal = LONG ETH (expecting catch-up)
if rsi_eth > 60 and rsi_btc < 40:
    signal = LONG BTC (expecting rotation)
```

**Priority:** MEDIUM
**Status:** Concept phase

---

## 🐛 Known Issues & Technical Debt

---

### 2026-02-27 21:30 - Kimi Code

**Category:** TECHNICAL_DEBT

**Summary:** Database schema inconsistencies between bundle files

**Details:**
Different bundle creation scripts use slightly different column names:
- `last_updated` vs `updated_at`
- `forward_start_date` presence varies
- Some scripts missing `quality_score` or `rank` columns

**Impact:**
Can cause "no column named X" errors when running different scripts.

**Workaround:**
Currently using `INSERT OR REPLACE` with full column lists. Needs standardization.

**Proposed Solution:**
Create single `bundle_schema.sql` file that all scripts reference.

**Priority:** LOW
**Status:** Documented, workaround in place

---

### 2026-02-27 21:00 - Cursor Agent

**Category:** BUG

**Summary:** Forward tracking doesn't update unrealized P&L continuously

**Details:**
The `bundle_baby_live_tracker.py --update` only checks for TP/SL hits. It doesn't continuously update unrealized P&L for open trades.

**Impact:**
Discord `!fc-bundle` command shows stale P&L until trade closes.

**Proposed Solution:**
Add continuous price fetching and unrealized P&L updates to `--update` command.

**Files Affected:**
- `bundle_baby_live_tracker.py` - `update_open_trades()` method

**Priority:** MEDIUM
**Status:** Needs implementation

---

## 📊 Testing Protocol Feedback

---

### 2026-02-27 20:30 - Kimi Code

**Category:** FEEDBACK

**Summary:** Multi-pair testing timeout issues on 5m timeframe

**Details:**
Strategies with complex calculations timeout on 5m timeframe (>25s limit). This eliminates some potentially good scalping strategies.

**Current Behavior:**
- 5m data has 10,000+ bars
- Complex strategies exceed 25s timeout
- Marked as "timeout" and skipped

**Proposed Solution:**
Options:
1. Increase timeout to 60s for 5m timeframe
2. Limit 5m backtest to last 5000 bars instead of 10000
3. Allow strategies to specify "5m optimized" mode

**Priority:** MEDIUM
**Status:** Under consideration

---

### 2026-02-27 20:00 - Cursor Agent

**Category:** FEEDBACK

**Summary:** Need minimum trade count validation

**Details:**
Some strategies show high Sharpe with only 5-10 trades. This is statistically insignificant.

**Current Pass Criteria:**
- Sharpe >= 1.0
- WR >= 45%
- DD <= 25%
- Trades >= 12 (but this is often per-pair, not aggregate)

**Proposed Solution:**
Add minimum trade requirement:
- Tier 1: Minimum 20 trades across all pairs
- Tier 2: Minimum 10 trades per timeframe

**Priority:** HIGH
**Status:** Partially implemented in tiered tests

---

## 🚀 Feature Requests

---

### 2026-02-27 19:30 - Kimi Code

**Category:** FEATURE_REQUEST

**Summary:** Auto-bundle creation from tiered results

**Details:**
Automatically create bundles from strategies that pass tiered testing, grouped by classification.

**Proposed Behavior:**
```bash
python bundle_baby_system.py --auto-create
```

This would:
1. Load all tiered results
2. Group strategies by (symbol_scope, timeframe_scope, direction_bias)
3. Create bundles for each unique combination
4. Add to registry automatically

**Priority:** LOW
**Status:** Manual process works for now

---

### 2026-02-27 19:00 - Cursor Agent

**Category:** FEATURE_REQUEST

**Summary:** Bundle graduation notifications

**Details:**
When a bundle reaches 100+ forward trades with WR > 55%, automatically:
1. Change status from "paper" to "graduated"
2. Send Discord notification
3. Add to "Production Ready" section

**Priority:** MEDIUM
**Status:** Not implemented

---

## 📈 Performance Insights

---

### 2026-02-27 18:30 - Kimi Code

**Category:** INSIGHT

**Summary:** Win rate decay pattern observed

**Details:**
From initial forward testing (limited sample):
- Backtest WR: 60-80% typical
- Forward WR: 45-55% typical
- Decay: ~25-30% relative drop

**Implication:**
Need backtest WR > 65% to expect forward WR > 50% (profitable after fees).

**Recommendation:**
Set bundle minimum backtest WR to 65% for production candidacy.

**Priority:** HIGH
**Status:** Monitoring ongoing

---

## 🔗 Quick Links

- [Bundle Registry](BABY_BUNDLE_REGISTRY.md) - All active bundles
- [Baby Bundle Guide](BABY_BUNDLE_GUIDE.md) - System documentation
- [Web AI Guide](BABY_STRAT_WEB_AI_GUIDE.md) - For web-only AIs
- [Strategy Inventory](incubator/EXISTING_STRATEGIES_INVENTORY.md) - Avoid duplicates

---

*This file is community-maintained. Add your ideas above this line!*
