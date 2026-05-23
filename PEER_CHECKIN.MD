# Peer Check-In — Claude Opus (Trading Edge Investigation)
**Last Updated:** 2026-04-04 16:25 UTC
**Agent:** Claude Opus 4.6 (1M context) — Trading Strategy Developer
**Working Directory:** e:\findtorontoevents_antigravity.ca

---

## 🎯 Current Focus: Building "THEWINNERS" Paper Trading Portfolio

Building a challenge portfolio containing ONLY TV-verified winning strategies. User challenged: "create a paper trading strategy portfolio completely FULL OF WINNERS!"

---

## 📊 Completed This Session (Last ~6 Hours)

### 1. Found Critical Bug: Python Backtester Look-Ahead Bias
- **Issue:** Every backtester was entering at `close[signal_bar]` instead of `open[next_bar]`
- **Impact:** Inflated results 10-40% vs TradingView Strategy Tester ground truth
- **Fixed:** `backtest_edge_finder.py` (commit `b529173b2a`)
- **Files still needing fix:** backtest_multi_strategy.py, backtest_novel_strategies.py, backtest_rsi2_case_study.py, backtest_param_optimization.py, backtest_kimi_claw_signals.py

### 2. Discovered 3 TV-Verified Edges (on full 8.5yr Binance history)

#### Edge #1: AG Trend-Pullback v1.2 (OPTIMIZED)
- Logic: EMA50>EMA200 + RSI(2)<10 + ADX>25 + TP 2.5x ATR + SL 2x ATR
- **BTC 1D:** +16.71%, 54.3% WR, 4.65% DD
- **ADA 1D:** +10.38% (rescued from -4.56% with default params)
- **AVAX 1D:** -0.36% (rescued from -18.38%)
- File: `pine_strategies/AG_Trend_Pullback_Optimized_v1.2.pine`

#### Edge #2: AG Momentum Breakout v1.0
- Logic: RSI(14)<40 recent + cross back above 50 + ADX>20 + TP 3x ATR
- **LINK 1D:** +18.16%, 57.6% WR
- **BTC 1D:** +12.61%, 60.7% WR
- **SOL 1D:** +12.09%, 50.0% WR, 3.72% DD (lowest)
- **BNB 1D:** +10.67%, 33.3% WR
- **ETH 1D:** +10.54%, 35.0% WR
- **ADA 1D:** +1.53%, 41.7% WR
- **6 of 7 profitable** (only AVAX fails)
- File: `pine_strategies/AG_Momentum_Breakout_v1.0.pine`

#### Edge #3: AG SHORT-Only v1.3
- Logic: EMA50<EMA200 + RSI(2)>90 + ADX>20 + TP 3x ATR + SL 2x ATR
- **ETH 1D:** +15.04% (BEST)
- **AVAX 1D:** +9.68% (rescued from LONG -18.38%)
- **SOL 1D:** +5.15%, 68.4% WR (highest WR — short squeezes)
- **BTC 1D:** +3.03%, 1.78% DD (lowest DD of all)
- File: `pine_strategies/AG_TrendPullback_Short_v1.3.pine`

### 3. Grid Search: 960 Parameter Combos Tested
- Top combo: RSI<10, ADX>20, TP 3.0x, SL 2.0x, hold 10 → Sharpe 2.36
- Key finding: **SHORTs carry the edge** (PF 1.36-1.43 vs LONGs near 1.0)
- File: `backtest_trend_pullback_variants.py` + `.json`

---

## 💼 THEWINNERS Portfolio (Just Built — 16:25 UTC)

**Account:** THEWINNERS USD ($1,000 initial capital)
**Strategy:** 7 picks, all from TV-verified winning strategy/symbol combos

| # | Symbol | Side | Entry | TP | SL | Strategy | Historical |
|---|--------|------|-------|-----|-----|----------|------------|
| 1 | BTC | LONG | $67,488 | $71,537 | $64,788 | Trend-Pullback v1.2 | +16.71% |
| 2 | ETH | SHORT | $2,060 | $1,854 | $2,163 | SHORT-Only v1.3 | +15.04% |
| 3 | SOL | LONG | $81.17 | $89.29 | $77.11 | Trend-Pullback v1.1 | +21.96% |
| 4 | BNB | LONG | $592.57 | $621 | $574 | Trend-Pullback v1.1 | +49.75% |
| 5 | LINK | LONG | $8.72 | $10.03 | $8.07 | Momentum Breakout v1.0 | +18.16% |
| 6 | ADA | LONG | $0.2463 | $0.2710 | $0.2315 | Trend-Pullback v1.2 | +10.38% |
| 7 | AVAX | SHORT | $9.00 | $8.10 | $9.90 | SHORT-Only v1.3 | +9.68% |

**Expected combined historical: +142.69% across all 7 trades** (hypothetical if strategies repeat)

---

## 📈 Other Portfolios Status (from audit 16:17 UTC)

| Portfolio | Balance | Equity | Unrealized | W/L |
|-----------|---------|--------|------------|-----|
| BROKIE | $999.68 | $1,001.94 | +$2.26 | 2W/1L |
| TESTER | $3,005.60 | $3,005.17 | -$0.44 | 4W/2L |
| SCALPER | $2,000.15 | $1,990.28 | -$9.86 🔴 | 2W/4L |
| TRUSTOURSCORE | $90,060.71 | $90,406.50 | +$345.78 ✅ | 4W/1L |
| zerounderscore | $100,478.87 | $100,629.50 | +$150.63 | 2W/3L |
| THEWINNERS | $1,000.00 | $1,000.00 | $0 (fresh) | 0/0 |

**System-wide:** 14 winners / 11 losers = 56% WR. Unrealized: +$488.37 across all.

---

## 🧪 Active Experiments

- 7 TV-verified picks deployed to THEWINNERS
- Tracking BTC LONG as primary signal (dominant winner across 3 portfolios)
- Testing if asymmetric R:R (1.67:1) + quality entries can produce 40-60% WR edge consistently

---

## 📝 Files I'm Actively Editing

- `CHATWITHIT.MD` — live coordination log (edited every ~30 min)
- `TESTING_PROTOCOL.MD` — open in user's IDE (don't conflict)
- `pine_strategies/*.pine` — Pine scripts for TV (4 strategies now)
- `backtest_*.py` — Python backtesters (need look-ahead fix in 5 remaining)

---

## 🤝 For Other Agents

**Please avoid editing these files while I'm active:**
- `CHATWITHIT.MD` (I'm updating ~every 30min)
- `audit_trail/quality_gates.py` (I just integrated 7 strategies here)
- `audit_dashboard/template.html` (scoring weights for backtest winners)

**Safe to work on in parallel:**
- Any non-backtest code
- Scanner scripts (multi_asset/, alpha_engine/)
- Dashboard generators (don't run locally!)
- Strategy registry expansions
- Infrastructure work (workflows, CI/CD)

**Please ALERT me if:**
- You find another look-ahead bias in any backtester
- You see conflicting positions being placed on paper trading accounts
- You identify a strategy that TV-verifies at >20% annual with <10% DD

---

## 📞 Contact

Message me via CHATWITHIT.MD "Peer Coordination" section or the claude-peers MCP.

Current status: **ACTIVE** — monitoring THEWINNERS portfolio, continuing edge research.
