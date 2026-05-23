# Non-Crypto Asset Class Improvements

**Date:** 2026-04-14 1:10 AM EDT  
**Branch:** `cursor/non-crypto-improvements-407c`  
**Integration:** Changes to `audit_trail/quality_gates.py` — directly affects `findtorontoevents.ca/audit` Active Picks, Closed Picks, and Smart Picks views

---

## Changes by Asset Class

### EQUITY — Surgical Strategy Pruning

**Problem:** Equity is the worst-performing non-crypto asset at PF 0.75, -346% cumulative. But this is driven by specific losing sub-strategies, not the entire asset class. With Score≥50 + Trust≥3 filtering, equity reaches PF 2.62 on 119 picks.

**What we block (per-strategy, not per-system):**

| Strategy | N | WR | PF | Action | Investigation |
|----------|---|-----|-----|--------|--------------|
| `Value + Quality` | 48 | 6.2% | 0.14 | **BLOCK on EQUITY** | 3-axis autopsy: no rehab path |
| `Consecutive Beats` | 39 | 25.6% | 0.54 | **BLOCK on EQUITY** | Uniformly losing |
| `Earnings Drift` | 19 | 15.8% | 0.30 | **BLOCK on EQUITY** | Inverse confirmed PF 2.07 — use `inverse_wrapper.py` (PR #183) |
| `Dividend Aristocrats` | 8 | 0.0% | 0.00 | **BLOCK on EQUITY** | Zero wins |

**What we keep:**

| Strategy | N | WR | PF | Status |
|----------|---|-----|-----|--------|
| `Breakout Momentum` | 39 | 56.4% | 2.47 | ✅ Keep — best equity strategy |
| `Bollinger MR` | 65 | 50.8% | varies | ✅ Keep — borderline positive |
| `rs-breakout-scout` | 13 | 69.2% | 4.90 | ✅ Keep — strong but small n |
| `quality-minus-junk` | 22 | 63.6% | 1.64 | ✅ Keep — genuine edge |

**Projected benefit:** Removing the 4 blocked strategies eliminates ~154 losing picks (-334% cumulative). Remaining equity strategies have aggregate PF ~1.5-2.0.

**Dashboard impact:** Blocked strategies will no longer appear in Active Picks or Smart Picks on `findtorontoevents.ca/audit` when filtered to EQUITY.

### FOREX — Score Floor Lowered

**Problem:** `SMART_PICKS_MIN_SCORE_FOREX = 75` was too strict. No forex picks were qualifying for Smart Picks. The forex strategies that actually work (`forex_rsi2_mean_reversion` at 48.3% WR, `myfxbook_retail_contrarian` at 48.4% WR) score in the 30-45 range because of how the scoring system weights non-crypto strategies.

**Change:** SMART_PICKS_MIN_SCORE_FOREX lowered from 75 → 40

**Why 40 and not lower:** 
- Score < 30 on forex has 28.6% WR — losing
- Score 30-50 on forex has 43.3% WR, PF 2.34 — the actual edge zone
- The FwdWR≥50 gate (from PR #191) provides the real quality filtering
- Setting floor at 40 lets proven strategies through while still blocking junk

**Projected benefit:** Forex Smart Picks will now show ~400+ picks instead of ~0. The FwdWR gate ensures only validated strategies appear.

**Dashboard impact:** Forex asset class will now populate in the Smart Picks tab on `findtorontoevents.ca/audit`.

### CRYPTO — Strategy-Level Block

**Problem:** `enhanced_ml_A_xgboost` has 28% WR with 0% winning days across 8 trading days, 189 picks losing -113%. It persists because its source system (`ml_crypto_pred`) is not blocked — only the specific strategy is a consistent loser.

**Change:** Added `("enhanced_ml_A_xgboost", None)` to `BLOCKED_STRATEGIES` — blocks across all asset classes.

**Projected benefit:** Removes ~189 losing picks. These picks had the lowest per-day consistency in the entire system (0% winning days = every single day it trades, it loses on aggregate).

### ETF — Strategy-Level Blocks

**Problem:** ETF has 19 total picks at PF 0.28. The two dominant strategies (`extreme_oversold_bounce` at 0% WR, `vix_reversal` at 33% WR) have no demonstrated edge.

**Change:** Blocked both strategies on ETF asset class specifically.

**Note:** We do NOT block ETFs entirely. `proven_vwap_mean_reversion` (4 picks, 100% WR) and `sector_rotation` (1 pick, 100% WR) are left running for forward testing. If they accumulate n≥20 with PF≥1.3, they validate the ETF asset class.

### COMMODITY — No Changes

**Status:** PF 1.07, +6.3% cumulative. Essentially breakeven. No single strategy or filter reliably improves it beyond noise. The `futures_momentum` strategy (88% of commodity picks) is the system — it's not losing but not winning enough to justify changes.

**Monitoring:** Wait for n to grow. Trust≥3 gives a marginal lift (PF 1.28 on n=273) but the CI crosses 1.0. Need 200+ more picks to determine if there's real edge.

### BOND — No Changes

**Status:** n=8, too early. ZN=F via `futures_momentum` shows 50% WR, PF 25.9 — but that's 4 wins and 4 losses on tiny amounts. Need n≥50.

### FUTURES — Already Blocked

**Status:** Already in `BLOCKED_ASSET_CLASSES` per prior session. 6.3% WR on 17 picks. No changes needed.

---

## Implementation Details

### New: `BLOCKED_STRATEGIES` set + `is_strategy_blocked()` function

Added to `audit_trail/quality_gates.py`:

```python
BLOCKED_STRATEGIES = {
    ("Value + Quality", "EQUITY"),
    ("Consecutive Beats", "EQUITY"),
    ("Earnings Drift", "EQUITY"),
    ("Dividend Aristocrats", "EQUITY"),
    ("enhanced_ml_A_xgboost", None),  # Blocked across all asset classes
    ("extreme_oversold_bounce", "ETF"),
    ("vix_reversal", "ETF"),
}
```

The `is_strategy_blocked()` function uses substring matching on strategy names and exact matching on asset class. If `asset_class` is `None` in the tuple, the strategy is blocked everywhere.

This is wired into `passes_active_gate()` — the function that controls what appears in Active Picks and Smart Picks on the dashboard.

### How it integrates with the dashboard

The `passes_active_gate()` function in `quality_gates.py` is called by `audit_trail/dashboard_generator.py` for every pick before it's included in the dashboard payload. Picks that fail the gate are excluded from:
- Active Picks tab
- Smart Picks tab  
- Overview summary statistics
- Performance breakdowns

Closed picks are NOT affected — they remain visible in the Closed Picks tab for historical analysis. This is by design: we want to see the losing picks in historical view, but not recommend them as active positions.

---

## Summary

| Asset | Change | Before | After (projected) |
|-------|--------|--------|-------------------|
| **EQUITY** | Block 4 losing strategies | PF 0.75, -346% | PF ~1.5, ~-12% |
| **FOREX** | Lower score floor 75→40 | 0 smart picks | ~400 smart picks |
| **CRYPTO** | Block enhanced_ml_A_xgboost | 189 drag picks | Removes -113% drag |
| **ETF** | Block 2 losing strategies | PF 0.28, -15% | Remaining n=5 for forward test |
| **COMMODITY** | No change | PF 1.07 | Monitor |
| **BOND** | No change | n=8 | Monitor |
| **FUTURES** | Already blocked | — | — |

*Generated: 2026-04-14 1:10 AM EDT*
