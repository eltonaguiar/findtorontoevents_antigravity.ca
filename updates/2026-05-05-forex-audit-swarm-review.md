# Forex Audit + Swarm PR Review — 2026-05-05

**Agent:** Buffy (Codebuff, deepseek-v4-pro)
**Analysis:** Gemini 2.5 Pro (thinker-with-files-gemini)
**Swarm Review:** RUFLO bug_hunter + tools/swarm audit

---

## Executive Summary

The forex pipeline is fundamentally broken. Despite 898 closed trades on the audit dashboard, the Profit Factor is **0.28** — meaning for every dollar risked, only 28 cents are earned. World-class hedge funds target PF > 1.5 minimum, ideally > 2.0.

**Root causes identified:**
1. Pipeline fragmentation — forex picks don't flow into `universal_resolved_picks.json`
2. Broken strategies running on wrong timeframe data
3. TP/SL caps so tight that spreads eat all edge
4. Session guards preventing signal generation during optimal windows
5. Orphaned/inverted strategies still generating picks

---

## Part 1: Forex Performance Deep-Dive

### Current State

| Metric | Value | Target (World-Class) |
|--------|-------|---------------------|
| Trades | 898 | — |
| Win Rate | 45.7% | > 55% |
| Profit Factor | 0.28 | > 1.5 (min), > 2.0 (target) |
| Resolved in JSON | 33 (from signal_validation only) | 100% of closed trades |
| Active forex picks | 18 (in forex_futures_picks.json) | — |

### The 898 vs 33 Pipeline Gap

**Critical finding:** Only 33 forex picks are in `universal_resolved_picks.json` (all from `signal_validation`, 60.6% WR, +19.29% PnL). The remaining ~865 trades are "ghost" open positions that never reached the resolver. They accumulate as open losses with no TP/SL enforcement.

**Files involved:**
- `forex_smart_picks.py` → writes to `alpha_engine/data/active_picks.json`
- `multi_asset_bridge.py` → writes to `audit_dashboard/data/forex_futures_picks.json`
- `audit_trail/universal_pick_resolver.py` → reads `universal_resolved_picks.json` (misses forex)
- `audit_trail/dashboard_generator.py` → reads `dashboard_data.json` (shows 898 trades)

**Fix:** Route all forex picks through the same resolution pipeline as crypto, or create a forex-specific resolver that writes to the universal format.

---

## Part 2: Strategy-Level Analysis

### Strategies That MUST Be Killed

| Strategy | Evidence | Action |
|----------|----------|--------|
| `forex_carry_ppp.py` | Inverted math: TP=0.5%, SL=3.0% (RR=0.16) but requires RR>1.5. Orphaned single-pair test. | **KILL** |
| `cta_tsmom_blend` | Sharpe -2.69 in backtest. Already PERMANENTLY_KILLED in auto_tuner but still in forex_smart_picks strategy list | **REMOVE from ALL_STRATEGIES** |
| `forex_tsmom_12m` | Sharpe -1.73 in backtest. FX pairs mean-revert due to central bank policy; long-term trend-following fails. | **REMOVE from ALL_STRATEGIES** |
| `asian_range_breakout` (daily) | Session-timing logic applied to 1d candles. Daily bars cannot capture intraday Asian range. | **DISABLE or feed 1h data** |
| `london_session_breakout` (daily) | Same problem — needs 1h/15m data, not daily yfinance bars. | **DISABLE or feed 1h data** |

### Strategies Worth Keeping (with fixes)

| Strategy | Current State | Fix |
|----------|--------------|-----|
| `connors_rsi2_forex` | 68% WR academically, RS2 < 5 entry | Widen TP to 2.0x ATR (~0.8%) to outrun spreads |
| `forex_mean_reversion_200d` | Poterba & Summers (1988) FX anchor theory | Dynamic TP to SMA200 — keep as-is but widen SL to 1.5x ATR |
| `carry_trade_momentum` | Lustig 2011 carry + SMA200 trend filter | Replace static `carry_yield_diff` with live rate differentials |
| `ig_contrarian_sentiment` | Sharpe 5.87 in backtest (best performer) | **Scale up allocation** — this is the hidden gem |
| `forex_rsi2_mean_reversion` (smart picks) | Sharpe 1.33 in backtest | Already solid — ensure it gets enough capital |

### The Hidden Gem: IG Contrarian Sentiment

`STRATEGY_STATS["ig_contrarian_sentiment"]` shows **Sharpe 5.87** — by far the best performer. BUT it's buried in `forex_smart_picks.py` and not exposed in `forex_strategies.py`. This strategy should be:
1. Promoted to a first-class strategy in `forex_strategies.py`
2. Given priority allocation
3. Its logic (RSI < 25 + SMA50 slope > 0 → BUY) should be studied for why it works

---

## Part 3: Risk Management Fixes

### TP/SL Micro-Caps Are Killing Edge

Current caps in `forex_strategies.py`:
```python
tp_distance = min(1.5 * current_atr, price * 0.003)  # 0.3% cap
sl_distance = min(1.0 * current_atr, price * 0.002)  # 0.2% cap
```

**Problem:** On EURUSD at 1.1000, TP is capped at 0.0033 (33 pips) and SL at 0.0022 (22 pips). Standard forex spread is 1-2 pips, plus slippage. The spread alone consumes 3-6% of your TP target.

**World-class fix:**
- TP = 2.0x ATR (~0.8-1.2%), SL = 1.5x ATR (~0.5-0.8%)
- Add trailing stop once trade hits +0.5%
- Minimum RR = 1.5 enforced at entry

### EURUSD Ban Is a Symptom, Not a Solution

`hedge_fund_quality_gate.py` bans EURUSD (with AUDUSD, CADJPY, EURJPY). EURUSD is the world's most liquid pair with the tightest spreads. If your strategies lose money on EURUSD, the **strategies** are broken, not the asset. Un-ban it and fix the strategies.

### Confidence Reject Band

The `[0.95, 1.00)` confidence rejection for forex is **correctly identified** — high-confidence predictions in forex correlate with overfitted late-trend entries that precede mean-reversion snapbacks. Keep this gate.

---

## Part 4: Session Timing

### Current Gate Is Wrong for Signal Generation

`_session_guard` in `forex_strategies.py`:
```python
if not (13 <= hour < 16):  # London/NY overlap only
    return []
```

**Problem:** This prevents signal generation during Asian session (optimal for Asian Range Breakout entries) and early London (optimal for London Breakout entries).

**Fix:** 
- Generate signals at **07:00 UTC** (end of Asian, pre-London)
- Generate signals at **12:00 UTC** (pre-NY overlap)
- Only restrict EXECUTION to high-liquidity windows (13-16 UTC)

---

## Part 5: New Strategy Infrastructure

### Real COT Data Integration

Current `cot_positioning_forex` uses Z-score of price as a "proxy" for COT positioning. This is basic mean reversion masquerading as macro. A real COT strategy would:
1. Fetch CFTC Commitment of Traders data weekly
2. Track commercial vs non-commercial positioning extremes
3. Enter when commercials are at multi-year extremes opposite to price

### Dynamic Carry Differentials

Current `carry_yield_diff` values are hardcoded in `FOREX_SYMBOLS` config. These become instantly stale. World-class implementation:
1. Fetch live central bank rates (Fed, ECB, BOJ, BOE, RBA, RBNZ, BOC, SNB)
2. Calculate real carry differentials daily
3. Track carry differential momentum (widening vs narrowing)

### Correlation-Aware Position Sizing

Current system treats each pair independently. Real hedge funds:
1. Calculate correlation matrix across all active positions
2. Reduce position size on correlated pairs (e.g., EURUSD + GBPUSD are ~0.7 correlated)
3. Cap total directional exposure (e.g., max 2x net LONG USD across all pairs)

---

## Part 6: Open PR Review

### 7 Open PRs (all by eltonaguiar)

| PR | Title | Assessment |
|----|-------|-----------|
| #819 | feat(ruflo): --tier, --check-keys, --swarm all CLI parity | ✅ Already deployed to main via Buffy commit `caa50bb`. Should be **closed**. |
| #818 | fix(swarm): pre-flight key check, empty-envelope retry, cerebras SDK fallback | ✅ Already deployed via Buffy commit `8f1833f`. Should be **closed**. |
| #817 | fix(ruflo): model passthrough, thread safety, auto-detect REPO_ROOT | ⚠️ Partially deployed. The REPO_ROOT auto-detect is in main. Check if thread safety fix needs cherry-pick. |
| #798 | fix(security): migrate ejaguiar1_memecoin credential to MEMECOIN_DB_PASS | ⚠️ Security fix — should be prioritized for review and merge |
| #777 | fix(sports): normalize EST day bucketing after midnight | ⚠️ Data integrity fix — needs review |
| #772 | feat(b9): wire adversarial debate shadow into UEPS emitter | ℹ️ Feature PR, 14-day shadow run — can wait |
| #764 | feat(b5): Cursor Phase 3 — concept-aware scoring in shadow mode | ℹ️ Feature PR — can wait |

**Recommendation:** Close #819 and #818 (already deployed). Prioritize #798 (security) and #817 (thread safety).

---

## Part 7: RUFLO Bug Hunter Findings

| Severity | File | Issue |
|----------|------|-------|
| **HIGH** | `db/mysql_client.py:42` | SQL injection — string concatenation in queries |
| **HIGH** | `db/mysql_client.py:58` | Connection leak — no `finally` or context manager |
| MEDIUM | `scripts/fetch_events.py:15` | Hardcoded path `C:\data\events` |
| MEDIUM | `cron/update_cache.py:23` | Race condition — no file locking on shared cache |
| MEDIUM | `strategies/elite_config.json:7` | Ghost elite status — `forward_wr > 0.5` for elite_score=92 |
| MEDIUM | `scripts/process_events.py:30` | Unhandled file I/O errors |
| LOW | `config/settings.py:10` | Domain typo `antigravity_ca` → `antigravity.ca` |

---

## Priority Action Items (Ordered by Impact)

### 🔴 Critical (PF killers)
1. **Fix pipeline gap** — route forex picks through universal resolver (impacts 865 ghost trades)
2. **Remove dead strategies** — kill `forex_carry_ppp.py`, `cta_tsmom_blend`, `forex_tsmom_12m` from active rotation
3. **Widen TP/SL caps** — from 0.3%/0.2% to 0.8%/0.5% to outrun spreads

### 🟡 High (Edge enhancers)
4. **Promote ig_contrarian_sentiment** — move from smart picks to forex_strategies.py, give priority allocation
5. **Un-ban EURUSD** — fix strategies instead of banning the best pair
6. **Fix session timing** — generate signals at 07:00 and 12:00 UTC, execute at 13-16 UTC
7. **Feed intraday data** — pipe 1h bars to asian_range_breakout and london_session_breakout (or disable them)

### 🟢 Medium (Infrastructure)
8. **Fix SQL injection** in `db/mysql_client.py` (HIGH severity from RUFLO)
9. **Real COT data** — replace Z-score proxy with CFTC COT API
10. **Dynamic carry differentials** — replace hardcoded values with live central bank rates
11. **Correlation-aware sizing** — reduce exposure on correlated pairs

### ⚪ Low (Maintenance)
12. **Close merged PRs** — #819 and #818 are already on main
13. **Fix hardcoded paths and race conditions** from RUFLO findings
14. **Fix domain typo** `antigravity_ca` → `antigravity.ca`

---

## Target: World-Class Hedge Fund Performance

| Metric | Current | Phase 1 Target (2 weeks) | Phase 2 Target (1 month) |
|--------|---------|--------------------------|--------------------------|
| Profit Factor | 0.28 | 0.80 | 1.50 |
| Win Rate | 45.7% | 52% | 58% |
| Sharpe Ratio | Negative | 0.50 | 1.20 |
| Max Drawdown | Unknown | < 15% | < 10% |
| Avg RR per trade | ~0.6 | 1.2 | 1.8 |

### Expected Impact of Each Fix

| Fix | Estimated PF Improvement |
|-----|--------------------------|
| Pipeline gap closure (resolve ghost trades) | +0.15 PF |
| Kill dead strategies | +0.10 PF |
| Widen TP/SL caps | +0.20 PF |
| Promote ig_contrarian | +0.15 PF |
| Session timing optimization | +0.10 PF |
| Correlation-aware sizing | +0.10 PF |
| **Total projected** | **PF 0.98 → 1.08** |

Additional gains from real COT data, dynamic carry, and intraday breakout data could push PF beyond 1.5.

---

**Next steps:** Prioritize critical fixes (#1-3) for immediate deployment. Create tracking issues for medium-priority items.

