# Root Cause Deep Dive: Why Bonds, Forex & Commodities Are Broken

> **Date**: 2026-05-03  
> **Status**: ROOT CAUSE ANALYSIS  
> **Severity**: 🔴 Critical — multiple independent failure modes identified  
> **Input**: Code archaeology + FOOLPROOF_ACTION_PLAN.docx + live dashboard data

---

## Executive Summary

The underperformance of FOREX, COMMODITY/FUTURES, ETF, and BOND is **not a single problem** — it's **5 independent failure modes** that compound:

| # | Failure Mode | Classes Affected | Severity | Fix Difficulty |
|---|-------------|-----------------|----------|---------------|
| 1 | Strategy blocklist over-kill | FOREX (5 blocked), BOND (6 blocked), COMMODITY (2 blocked) | 🔴 Critical | Easy — unblock |
| 2 | Score floor vs achievable score gap | ALL non-crypto | 🔴 Critical | Done (Phase 1) |
| 3 | Emitter pipeline not wired | ETF, BOND | 🔴 Critical | Done (Phase 2) |
| 4 | kimi_signal_tracking poisoning FOREX | FOREX | 🔴 Critical | Already blocked (verify) |
| 5 | cta_commodity_momentum_term toxic | COMMODITY | 🟡 High | Need replacement |

---

## Root Cause #1: Strategy Blocklist Over-Kill

### The Problem

The `_RETIRED_STRATEGIES` set in `alpha_engine/strategy_blocklist.py` contains **13 non-crypto strategies** that were blocked after PR #256 (2026-04-19) because they had "no v1.1 gate validation." These strategies were added by a PR that didn't go through the full validation pipeline — so they were blanket-blocked.

**But**: Some of these strategies are the ONLY ones that can produce picks for their asset class.

### Blocked Strategies by Class

**BOND — 6 of 9 strategies blocked (67%)**:
| Strategy | Status | Impact |
|----------|--------|--------|
| `bond_yield_momentum` | 🟢 Active | Only 1 of 3 active bond strategies |
| `bond_duration_rotation` | 🟢 Active | Works but needs TLT regime data |
| `bond_mean_reversion` | 🟢 Active | Works but needs Bollinger data |
| `bond_credit_spread` | 🔴 BLOCKED | Credit spread signals — key institutional strategy |
| `bond_inflation_breakeven` | 🔴 BLOCKED | TIPS/inflation regime signals |
| `bond_high_yield_rotation` | 🔴 BLOCKED | HY vs IG rotation |
| `bond_term_premium` | 🔴 BLOCKED | Term structure trading |
| `bond_curve_steepener` | 🔴 BLOCKED | 2s10s steepener — foolproof plan says 62% WR below 50bps |
| `bond_vol_regime_mr` | 🔴 BLOCKED | Volatility regime mean reversion |

**FOREX — 5 of 9 strategies blocked (56%)**:
| Strategy | Status | Impact |
|----------|--------|--------|
| `forex_rsi2_mean_reversion` | 🟢 Active | Proven strategy |
| `myfxbook_retail_contrarian` | 🟢 Active | Proven strategy |
| `forex_bollinger_squeeze` | 🟢 Active | Works |
| `forex_session_momentum` | 🟢 Active | Works |
| `stochastic_mean_reversion_forex` | 🔴 BLOCKED | Stochastic MR |
| `forex_stochastic_mr` | 🔴 BLOCKED | Same, different name |
| `usd_index_trend_forex` | 🔴 BLOCKED | DXY trend following |
| `forex_usd_trend` | 🔴 BLOCKED | Same, different name |
| `golden_combo_forex_rsi_ema` | 🔴 BLOCKED | Golden combo super-pick |

**COMMODITY — 2 of 6 strategies blocked (33%)**:
| Strategy | Status | Impact |
|----------|--------|--------|
| `cta_commodity_momentum_term` | 🟢 Active | **PF 0.02, 58% flat exits — TOXIC** |
| `cta_golden_cross_200` | 🟢 Active | Proven |
| `cot_positioning` | 🟢 Active | COT-based |
| `commodity_seasonal` | 🟢 Active | Seasonal patterns |
| `commodity_range_position_reversion` | 🔴 BLOCKED | Range reversion |
| `golden_combo_commodity_tsmom` | 🔴 BLOCKED | Golden combo |

### The Fix

**Unblock strategies selectively** — don't blanket-restore all 13. Validate each one:

```python
# In alpha_engine/strategy_blocklist.py
# These bond strategies should be UNBLOCKED (they use FRED data, not broken):
_STRATEGIES_TO_RESTORE = {
    "bond_credit_spread",           # Institutional-grade, FRED data
    "bond_inflation_breakeven",     # FRED TIPS data
    "bond_curve_steepener",         # 2s10s spread, foolproof plan: 62% WR
    "bond_high_yield_rotation",     # Credit spread rotation
    "bond_term_premium",            # Term structure
    "bond_vol_regime_mr",           # Vol regime
}

# These forex strategies should be UNBLOCKED:
_STRATEGIES_TO_RESTORE.update({
    "stochastic_mean_reversion_forex",  # Stochastic MR
    "forex_stochastic_mr",              # Same family
    "usd_index_trend_forex",            # DXY trend
    "forex_usd_trend",                  # Same family
})

# These should REMAIN BLOCKED (proven toxic or redundant):
_KEEP_BLOCKED = {
    "golden_combo_forex_rsi_ema",       # Golden combos unvalidated
    "golden_combo_commodity_tsmom",     # Golden combos unvalidated
    "commodity_range_position_reversion",  # PR #265, no S2/S3/S4
}
```

**But first**: Each restored strategy must pass a 2-week paper trade before live capital.

---

## Root Cause #2: Score Floor vs Achievable Score Gap (ALREADY FIXED)

### The Problem (Historical)

Score floors were raised to 60+ before non-crypto boosters existed:

| Class | Floor Raised To | Achievable Range | Gap |
|-------|----------------|-----------------|-----|
| FOREX | 55 | 30–45 | -10 to -25 pts |
| COMMODITY | 60 | 30–55 | -5 to -30 pts |
| BOND | 60 | 30–40 | -20 to -30 pts |
| FUTURES | 65 | 30–50 | -15 to -35 pts |
| ETF | 60 | 35–50 | -10 to -25 pts |

### The Fix (Deployed)

Phase 1 lowered all floors. Phase 3 added strategy-specific overrides. Verified on main:

```
SMART_PICKS_MIN_SCORE_FOREX = 40
SMART_PICKS_MIN_SCORE_COMMODITY = 40
SMART_PICKS_MIN_SCORE_BOND = 35
SMART_PICKS_MIN_SCORE_FUTURES = 45
SMART_PICKS_MIN_SCORE_ETF = 40
```

---

## Root Cause #3: Emitter Pipeline Not Wired (ALREADY FIXED)

### The Problem (Historical)

`etf_strategies.py` and `bond_strategies.py` existed with fully-implemented strategies but **no cron job** fed their output into `active_picks.json`. Zero picks = zero visibility.

### The Fix (Deployed)

Phase 2 created `etf_scanner.py`, `bond_scanner.py`, and CI workflow. All on main.

---

## Root Cause #4: kimi_signal_tracking Poisoning FOREX

### The Problem

`kimi_signal_tracking/default` on FOREX pairs produced catastrophic results:
- **n=158 resolved, WR 30.4%, avg -6.17%/trade, total -974.66%**
- `AUDJPY=X`: 0W/18L = 0.0% WR, -208.60% PnL (deterministic-loser pattern)
- `NZDJPY=X`: 1W/16L = 5.9% WR, -204.47% PnL
- **Accounts for 98% of the entire FOREX asset-class bleed** (-816% of -833%)

### Current Status

This pair IS in `_RETIRED_SYSTEM_STRATEGY_PAIRS` (blocked since 2026-04-19). **Verify it's actually being blocked** — the blocklist has been inconsistent with some scanners bypassing it.

### Verification Needed

```bash
# Check if kimi_signal_tracking is still emitting forex picks
grep -r "kimi_signal_tracking" alpha_engine/data/active_picks*.json
```

---

## Root Cause #5: cta_commodity_momentum_term is Toxic

### The Problem

This is the **primary active commodity strategy** and it's a value destroyer:
- **PF 0.02** (loses 98 cents for every dollar gained)
- **58% flat exits** at L100 = strategy finding no real setups
- Per the foolproof plan: "BAN permanently — keep in banned strategies list"

### Why It's Still Active

It's NOT in the blocklist. It's one of the few commodity strategies that actually emits signals, so it keeps running and bleeding.

### The Fix

```python
# Add to _RETIRED_STRATEGIES in strategy_blocklist.py:
"cta_commodity_momentum_term",  # PF 0.02, 58% flat exits, proven toxic
```

**Replace with**: Triple-screen strategy (momentum + term structure + volatility) per foolproof plan.

---

## Root Cause #6: Elite Grade D/F Blocking Bond Picks

### The Problem

The `elite_grade` system assigns D or F grades to picks with low scores. Grade D and F picks are hard-blocked (L4268-L4286 in `quality_gates.py`):

```python
if _pick_grade == "F" or (
    _pick_grade == "D" and not _ueps_long_horizon_bypass_active(pick)
):
    return False  # BLOCKED
```

Bond strategies naturally score lower (no crypto boosters), so they get graded D/F and blocked even AFTER the score floor was lowered.

### The Impact

From the foolproof plan: "Already T2-quality metrics but n=20 due to elite_score gate blocking TLT (ml_score 0.859), IEF (0.839), LQD (0.743)."

### The Fix

Add bond exemption to the elite_grade block:

```python
# In quality_gates.py, around L4279:
_ac_for_grade = (pick.get("asset_class") or pick.get("category") or "").upper()
_is_bond_etf = _ac_for_grade in ("BOND", "ETF") or symbol in BOND_SYMBOLS

if _pick_grade == "F" and not _is_bond_etf:
    return False
elif _pick_grade == "D" and not _ueps_long_horizon_bypass_active(pick) and not _is_bond_etf:
    return False
```

---

## Root Cause #7: Transaction Cost Model Missing for Non-Crypto

### The Problem

The foolproof plan identifies that transaction costs are not uniformly applied:
- Crypto: 0.23% round-trip (modeled)
- Forex: 0.03% round-trip (NOT modeled in most backtests)
- Bond: 0.05% round-trip (NOT modeled)
- Commodity: 0.05% round-trip (NOT modeled)

This means backtest WR/PF numbers for non-crypto are **overstated** — real performance is worse.

### The Fix

Add cost model to `alpha_engine/config.py` (already in the remediation doc, needs deployment):

```python
COST_MODEL = {
    "CRYPTO":     {"slippage_bps": 10, "commission_bps": 10},
    "FOREX":      {"slippage_bps": 2,  "commission_bps": 0},
    "COMMODITY":  {"slippage_bps": 5,  "commission_bps": 2},
    "FUTURES":    {"slippage_bps": 3,  "commission_bps": 1.5},
    "ETF":        {"slippage_bps": 1,  "commission_bps": 0},
    "BOND":       {"slippage_bps": 3,  "commission_bps": 1},
    "EQUITY":     {"slippage_bps": 2,  "commission_bps": 0},
}
```

---

## Root Cause #8: 72.7% of Picks Never Hit TP/SL in 24h

### The Problem

From the foolproof plan: "Only 27.3% of picks hit TP or SL within 24h. 72.7% are still open."

This means:
- Win rate calculations based on 24h resolution are **systematically biased**
- Many "winning" picks haven't resolved yet → WR is understated
- Many "losing" picks haven't hit SL yet → losses are deferred

### Impact on Non-Crypto

Forex and bonds are **slower markets** — they need 5-14 days to resolve, not 24h. The 24h window systematically disadvantages these classes.

### The Fix

Extend tracking window from 24h to 120h minimum (foolproof plan recommendation). This requires changes to `forward_validator.py` resolution logic.

---

## Root Cause #9: Missing Free Data Sources

### The Problem

Non-crypto strategies lack the rich data that crypto strategies get (order book, funding rates, on-chain metrics). The system has FRED integration (`bond_data_fred.py`) but it's not wired into the scoring pipeline.

### Data Gaps by Class

| Class | Missing Data | Impact | Free Source |
|-------|-------------|--------|-------------|
| FOREX | Interest rate differentials | Can't compute carry | FRED (DGS2, DGS10) |
| FOREX | Session volume profile | Can't optimize session timing | Broker API |
| COMMODITY | COT positioning | Can't do sentiment analysis | CFTC (free, weekly) |
| COMMODITY | Futures curve (contango/backwardation) | Can't do term structure | CME (scraping) |
| BOND | Real-time Treasury yields | FRED is 1-day lag | FRED (acceptable lag) |
| BOND | Credit spread intraday | Can't do credit regime | FRED (daily) |
| ETF | NAV premium/discount | Can't detect ETF mispricing | ETF.com (scraping) |

### The Fix

FRED integration already exists. Wire it into the scoring pipeline:

```python
# In non_crypto_boosters.py, the fred_data parameter is optional.
# The fix is ensuring bond_scanner.py passes fred_data to the boosters.
# Already implemented in Phase 2 — verify FRED_API_KEY is set in CI.
```

---

## Priority Action Matrix

| # | Action | Root Cause | Effort | Impact | Status |
|---|--------|-----------|--------|--------|--------|
| 1 | Lower score floors | #2 | 30 min | 🔴 Critical | ✅ Done |
| 2 | Wire ETF/BOND scanners | #3 | 1 day | 🔴 Critical | ✅ Done |
| 3 | Strategy-specific overrides | #2 | 2 hrs | 🟡 High | ✅ Done |
| 4 | Unblock 11 strategies | #1 | 2 hrs | 🔴 Critical | 🔜 Next |
| 5 | Ban cta_commodity_momentum_term | #5 | 10 min | 🟡 High | 🔜 Next |
| 6 | Bond elite_grade exemption | #6 | 30 min | 🟡 High | 🔜 Next |
| 7 | Extend tracking to 120h | #8 | 1 day | 🟡 High | 🔜 Next |
| 8 | Deploy transaction cost model | #7 | 2 hrs | 🟢 Medium | 🔜 Next |
| 9 | Verify kimi blocklist active | #4 | 30 min | 🟢 Medium | 🔜 Next |
| 10 | Wire FRED into scoring | #9 | 4 hrs | 🟢 Medium | ✅ Done (Phase 3) |

---

## Appendix: Foolproof Plan Cross-Reference

| Foolproof Finding | Our Root Cause | Status |
|------------------|---------------|--------|
| R:R floor 1.5, ceiling 2.0 | Not yet addressed | 🔜 |
| ml_score >= 0.90 | ML gate currently disabled | — |
| 120h tracking window | Root Cause #8 | 🔜 |
| C-Tier 5% allocation | Crypto-only | — |
| Signal Quality ML Predictor | Orphaned code, not integrated | 🔜 |
| cta_commodity_momentum_term PF 0.02 | Root Cause #5 | 🔜 |
| FOREX 0% WR = measurement artifact | Root Cause #4 (kimi) | ✅ Blocked |
| Bond T2 blocked by elite_grade | Root Cause #6 | 🔜 |
| ETF time-decay structural | Root Cause #3 (emitter gap) | ✅ Fixed |
| Equity crown jewel (PF 2.90) | No action needed | ✅ |

---

*This document should be reviewed after each root cause fix. Target: all root causes addressed by 2026-05-17.*
