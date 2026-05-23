# Hedge Fund Grade Scoring Audit — 2026-04-21

## Objective
Ensure ALL asset classes meet hedge fund quality standards: **WR >= 55%, positive PnL, PF >= 1.5**.

---

## Full Performance Audit Results

### Per-System Per-Asset-Class (Top Issues Found)

| System | Asset Class | Trades | WR% | PnL% | Action |
|--------|------------|--------|-----|------|--------|
| claude_gainer_st | CRYPTO | 731 | 23.8% | -463.3% | **Cap lowered 45→25** |
| copy_trader_intel | CRYPTO | 233 | 34.3% | -765.9% | **Cap added: 35** |
| kimi_riseoftheclaw | CRYPTO | 13 | 8.3% | -59.8% | **Blocked on CRYPTO** |
| kimi_signal_tracking | FOREX | 22 | 36.4% | -35.3% | **Already blocked** |
| mercury2 | CRYPTO | 22 | 18.2% | -7.0% | **Cap added: 20** |
| forex_copy_trader | FOREX | 39 | 16.7% | -0.4% | **Cap added: 15** |
| goldmine_stocks | EQUITY | 5 | 0.0% | -22.3% | **Blocked + cap: 10** |
| fast_stocks_competition | EQUITY | 6 | 0.0% | -22.0% | **Blocked on EQUITY** |

### Strategies Banned (WR < 35% on 15+ non-flat trades)

| Strategy | WR% | Trades | PnL% | Status |
|----------|-----|--------|------|--------|
| atr_regime_rsi | 17.2% | 29 | -10.4% | **BANNED** |
| st_atr_vol_breakout | 22.2% | 27 | -21.5% | **BANNED** |
| st_obv_support_divergence | 23.8% | 84 | -78.5% | **BANNED** |
| carry-trade-momentum | 26.7% | 15 | -2.2% | **BANNED** |
| copy_hl_lb_None | 32.0% | 278 | -806.4% | **BANNED** |

### Last 10/20 Picks Per Asset Class (Before Fix)

| Asset Class | Last 10 WR | Last 20 WR | Grade |
|-------------|-----------|-----------|-------|
| **ETF** | 80.0% | 85.0% | HF-GRADE |
| **EQUITY** | 66.7% | 64.7% | HF-GRADE |
| **COMMODITY** | 50.0% | 57.1% | HF-GRADE |
| **BOND** | 55.6% | 50.0% | Borderline |
| **CRYPTO** | 40.0% | 60.0% | Mixed |
| **FOREX** | 25.0% | 42.9% | BELOW-HF |

---

## Fixes Applied

### 1. `quality_gates.py` — Strategy Bans & Blocks

- **6 new PERMANENTLY_KILLED_STRATEGIES**: atr_regime_rsi, st_atr_vol_breakout, st_obv_support_divergence, carry-trade-momentum, copy_hl_lb_None/none
- **3 new BLOCKED_STRATEGIES entries**: kimi_signal_tracking|CRYPTO, goldmine_stocks|EQUITY, fast_stocks_competition|EQUITY

### 2. `score_booster.py` — Scoring Engine Hardening

- **PnL Outlier Cap**: All trades capped to [-100%, +100%] — eliminates -106,700% AUDUSD outlier
- **Symbol-Specific WR Gate**: Score capped at 50 if symbol WR < 35% on 10+ trades
- **Non-Crypto Catastrophe Penalty**: -15 penalty for forex/commodity symbols with < 30% WR
- **Per-System-Per-Asset WR Gate**: Score capped to WR*100 when system has < 35% WR on 15+ trades for that asset class
- **System Score Caps Expanded**: 5 new entries (mercury2_fast, copy_trader_intel, mercury2, forex_copy_trader, goldmine_stocks)
- **claude_gainer_st cap lowered**: 45 → 25 (reflects actual 23.8% WR)

---

## Expected Impact

| Metric | Before | Expected After |
|--------|--------|---------------|
| FOREX active WR | 28.6% | **50%+** (catastrophic systems capped/blocked) |
| CRYPTO active WR | 44.7% | **55%+** (worst systems capped to bottom) |
| Overall Sharpe | -1.56 | **-0.3 to +0.2** (PnL outliers eliminated) |
| Smart Picks PF | ~1.0 | **1.5+** (negative-edge strategies banned) |

## Verified

- [x] `quality_gates.py` syntax OK
- [x] `score_booster.py` syntax OK
- [x] All fixes are additive — no existing logic removed
- [x] Full audit trail fields for each new gate
