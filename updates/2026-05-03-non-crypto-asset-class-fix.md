# Non-Crypto Asset Class Performance Fix — Futures/Bonds/Commodities/Forex

**Date:** 2026-05-03  
**Branch:** `non-crypto-asset-class-fixes-2026-05-03`

---

## Executive Summary

Four non-crypto asset classes are underperforming due to sample size inadequacy and strategy wiring gaps:

| Asset Class | Win Rate | Sample Size | Status |
|-------------|----------|-------------|--------|
| CRYPTO | 31.8% | 3,164 | ACCEPTABLE (WR floor met) |
| FOREX | 25.0% | 8 | CRITICAL — UNDERPERFORMING |
| FUTURES | 0.0% | 4 | CRITICAL — NO PICKS GENERATING |
| COMMODITY | N/A | 0 | CRITICAL — NOT IN DASHBOARD |
| EQUITY | 0.0% | 1 | CRITICAL — SAMPLE SIZE |

---

## Root Cause Analysis

### 1. Data Integrity Findings

```json
{
  "source_file": "alpha_engine/data/closed_picks.json",
  "issues": [
    "FOREX: 8 trades insufficient for statistical significance (need 20+)",
    "FUTURES: 4 trades, 0% WR - strategies blocked by quality gates",
    "COMMODITY: 0 picks in dashboard_payload.json",
    "EQUITY: 1 trade, cannot compute meaningful statistics"
  ]
}
```

### 2. Strategy Wiring Audit

**scanner.py line 152-161:** Forex removed from default scanning (THE GREAT PURGE 2026-03-11):
```python
# THE GREAT PURGE (2026-03-11): Forex and penny removed from default scanning.
# Forex: macd_divergence 0W/3L, bb_mean_reversion 0W/3L — no edge found.
```

**non_crypto_pick_audit.json:** COMMODITY symbols only appear in mirror but not in dashboard payload.

### 3. Quality Gate Blockers

From `multi_asset/scanner.py` lines 243-255:
- `NON_CRYPTO_MIN_CONFIDENCE = 0.50` — too restrictive for mean-reversion strategies
- `MIN_RR_GATE = 1.5` — reasonable, but many commodity strategies get rejected
- Forex strategies were purged without alternative replacement

### 4. Direction Bias Check

| Asset | LONG WR | SHORT WR | Bias |
|-------|---------|----------|------|
| FOREX | N/A | N/A | No data |
| FUTURES | 0% | 0% | None |
| COMMODITY | N/A | N/A | No picks |

---

## Top 3 Loss Drivers

1. **Systemic: No picks generated for FUTURES/COMMODITY** — Zero activity means 0% WR by definition
2. **Sample starvation: FOREX 8 trades, 2 wins** — Cannot establish statistical significance
3. **Quality gate rejection: Commodity picks blocked** — `non_crypto_pick_audit.json` shows 0 commodity picks passing filters

---

## 5 Fix Experiments

### Experiment 1: Reduce FOREX confidence threshold
- **Variable:** `NON_CRYPTO_MIN_CONFIDENCE`
- **Change:** 0.50 → 0.45
- **Hypothesis:** Lower threshold allows more forex mean-reversion signals through
- **Pass/Fail:** WR ≥ 35% on next 20 forex picks

### Experiment 2: Re-enable COMM freshness scan
- **Variable:** `ALL_SYMBOLS` dict in scanner.py
- **Change:** Add commodity futures from `COMMODITY_SYMBOLS` module
- **Hypothesis:** Commodity-specific strategies (seasonality, mean reversion) generate positive edge
- **Pass/Fail:** ≥5 commodity picks with WR ≥ 40% in 30-day window

### Experiment 3: Add FOREX-specific strategies
- **Variable:** `forex_strategies.py` enablement
- **Change:** Use `--forex-only` mode with new session-aware strategies
- **Hypothesis:** FX session filter + ATR reachability produces cleaner signals
- **Pass/Fail:** 55% WR on next 30 picks with proper session timing

### Experiment 4: Fix COMMODITY → DASHBOARD bridge
- **Variable:** Audit dashboard emitter
- **Change:** Ensure `asset_class` tag propagates from mirror to payload
- **Pass/Fail:** COMMODITY picks appear in `active_by_category_visible`

### Experiment 5: Tighten FUTURES stop logic
- **Variable:** `RISK_PARAMS["futures"]`
- **Change:** Use tighter stops (-3%, +6%) matched to ATR volatility
- **Hypothesis:** CL=F previously killed by wide stops; tighter stops capture mean reversion
- **Pass/Fail:** WR ≥ 45% on next 20 futures picks

---

## 30/60/90 Day Recovery Plan

### Days 0-30: Stabilization
1. Implement confidence threshold reduction for forex
2. Wire commodity symbols into default scan
3. Add session-aware forex strategies
4. Monitor: daily check of non-crypto active picks

### Days 31-60: Optimization
1. Run ablation studies on forex strategies
2. Tune commodity-specific parameters
3. Add volatility-adjusted stops for futures
4. Monitor: weekly performance reports

### Days 61-90: Scale
1. Increase allocation if WR ≥ 40% and profit factor ≥ 1.2
2. Demote if after 3 experiments no improvement
3. Document final state in MEMORY.md

---

## Acceptance Criteria for Re-promotion

- **Minimum sample:** 30 closed picks per asset class
- **Performance floor:** WR ≥ 40% OR profit factor ≥ 1.2
- **Consistency:** 3 consecutive weeks of positive PnL
- **Risk check:** Max drawdown ≤ -15% on any single pick type

---

## Files Modified

| File | Change |
|------|--------|
| `multi_asset/scanner.py` | Lowered `NON_CRYPTO_MIN_CONFIDENCE` to 0.45 |
| `multi_asset/scanner.py` | Added commodity symbols to `ALL_SYMBOLS` |
| `multi_asset/forex_strategies.py` | Session-aware strategies enabled |
| `audit_trail/universal_pick_resolver.py` | Fixed asset_class propagation for COMMODITY |
| `tools/asset_class_performance_checker.py` | New monitoring script |
| `tools/non_crypto_mutations.py` | Mutation experiment runner |

---

## Verification Commands

```bash
# Run forex-specific scan
python multi_asset/scanner.py --forex-only

# Check commodity picks
python -c "
import json
with open('audit_trail/data/dashboard_payload.json') as f:
    d = json.load(f)
    for p in d.get('picks', []):
        if p.get('asset_class') == 'COMMODITY':
            print(p)
"

# Run mutation experiments
python tools/non_crypto_mutations.py --experiment 1
python tools/non_crypto_mutations.py --experiment 2
```