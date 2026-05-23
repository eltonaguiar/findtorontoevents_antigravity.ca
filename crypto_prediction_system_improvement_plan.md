# Crypto Prediction System Improvement Plan

**Date:** 2026-03-02  
**Systems:** Hub Dashboard (25 systems)  
**Current Status:** Mixed performance with several critical failures  
**Priority:** High - Immediate action required for 5+ underperforming systems

---

## Executive Summary

The crypto prediction ecosystem at [https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/hub/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/hub/) shows promising cross‑system consensus but suffers from significant weaknesses:
- **3 systems with 0% win‑rate** (Mercury 2, Battleground A, Battleground C)
- **Alpha Engine losing $5,751** despite 141 closed trades
- **JavaScript errors** degrading user experience
- **Missing timestamps** in fresh‑picks display
- **Redundant/dormant systems** cluttering the hub

This plan outlines a 30‑day transformation to boost overall win‑rate from ~45% to ≥60%, eliminate console errors, and create a leaner, higher‑conviction signal pipeline.

---

## 1. Current System Performance Analysis

### 1.1 High‑Performing Systems (Keep & Scale)
| System | Win‑Rate | Sharpe | Status | Action |
|--------|----------|--------|--------|--------|
| **KIMI Rise of the Claw** | 66% | High | Solid | Expand algorithm count |
| **ML: Claws of Doom** | ~60% | Positive | Active | Maintain current config |
| **Super Signal Engine** | N/A | N/A | New | Use as high‑conviction filter |
| **ML: Claude Gainer Tracker** | ~55% | Positive | Active | Continue forward testing |

### 1.2 Underperforming Systems (Critical Fix Required)
| System | Win‑Rate | Sharpe | Status | Root Cause |
|--------|----------|--------|--------|------------|
| **ML: Mercury 2** | 0% (0/10) | Negative | Retrain | Over‑engineering; excessive guards filter out good signals |
| **ML: Battleground A** | 0% (0/15) | Negative | Paused | PANIC_SELL logic exits too early in fear regimes |
| **ML: Battleground C** | 0% (0/?) | Negative | Paused | GRU‑Attention net overfitted; doesn't generalize |
| **ML: Alpha Engine** | 34.8% | -3.85 | Active | Stop‑hunting losses (79/89); needs SL adjustment |
| **ML: Crypto ML Edge** | ~45% | Neutral | Active | DSR gate too restrictive; TP/SL distances suboptimal |
| **QuantumFusion** | N/A | N/A | Broken | Endpoint 404; system non‑functional |

### 1.3 Dormant/Redundant Systems
- Signal Engine (dormant)
- Breakout Arena A/B/C (dormant)
- ML: Breakout Arena C (dormant)
- FC‑CRYPTO PRO (new but untested)
- Incubator Forward Test (experimental)

### 1.4 Hub Infrastructure Issues
1. **JavaScript Console Errors:**
   - `updateAggregatorPanels is not defined` at hub/:1421
   - `favicon.ico 404` (missing favicon)
   - `Failed to fetch quantum_fusion: undefined` in consensus_engine.js

2. **Fresh‑Picks Display:**
   - "No timestamp" for Predictions Engine picks
   - Missing date‑field detection for certain systems

3. **Data Quality:**
   - Mercury 2 lacks `closed_picks.json` (dead link)
   - Multiple systems missing closed‑trade history

---

## 2. Key Improvement Areas

### 2.1 Model Performance & Overfitting
- **Problem:** Mercury 2's win‑rate dropped from 77.8% (v1.0) to 0% (v1.3) due to added guards.
- **Solution:** Revert to v1.0 guard levels while keeping beneficial features.

### 2.2 Fear‑Regime Logic
- **Problem:** Battleground systems block BUYs in extreme fear (F&G=11) despite contrarian bias.
- **Solution:** Implement regime‑aware entry logic with dynamic thresholds.

### 2.3 Stop‑Loss Optimization
- **Problem:** Alpha Engine's 79/89 losses were stop‑hunted at 1.5× ATR.
- **Solution:** Widen SL to 2.25× ATR + add volatility‑adjusted positioning.

### 2.4 Signal Redundancy
- **Problem:** 25+ systems create noise; many produce similar signals.
- **Solution:** Consolidate into 8‑10 high‑conviction systems with orthogonal methodologies.

### 2.5 Technical Debt
- **Problem:** JavaScript errors, broken endpoints, missing files.
- **Solution:** Systematic cleanup and validation pipeline.

---

## 3. 30‑Day Enhancement Plan

### Phase 1: Emergency Stabilization (Days 1‑7)
**Goal:** Fix critical errors, pause worst performers, stabilize hub.

1. **Day 1‑2: JavaScript Error Fixes**
   - Move `updateAggregatorPanels` function definition above `loadAll()` in [`hub/index.html`](hub/index.html)
   - Create `hub/favicon.ico` (16×16 purple gradient)
   - Remove QuantumFusion from `systems_manifest.json` and `SYSTEMS` array

2. **Day 3‑4: Fresh‑Picks Timestamp Fix**
   - Expand `ENTRY_DATE_KEYS` to include additional timestamp variants
   - Add Predictions Engine to hub's fresh‑picks feed
   - Implement fallback timestamp generation

3. **Day 5‑7: System Pausing & Data Cleanup**
   - Set Mercury 2, Battleground A/C to `dormant: true`
   - Create placeholder `closed_picks.json` for Mercury 2
   - Audit all GitHub data endpoints for 404s

### Phase 2: Model Retraining & Optimization (Days 8‑21)
**Goal:** Retrain underperforming models, optimize parameters.

4. **Day 8‑12: Mercury 2 Retrain**
   - Revert to v1.0 guard thresholds
   - Keep MTF trend filter and tiered TP exits
   - Forward test for 48h before reactivation

5. **Day 13‑16: Alpha Engine SL Adjustment**
   - Implement 2.25× ATR stop‑loss across all strategies
   - Add direction restrictions (BUY‑only/SELL‑only per strategy)
   - Prune 11 killed strategies, keep top‑5 performers

6. **Day 17‑21: Battleground System Overhaul**
   - Redesign extreme‑fear logic: allow BUYs with reduced position size
   - Add "neutral" regime path when confidence <70%
   - Implement ensemble weighting (System B weighted 2×)

### Phase 3: Signal Consolidation & Enhancement (Days 22‑30)
**Goal:** Reduce noise, increase conviction, improve UX.

7. **Day 22‑25: System Consolidation**
   - Merge similar ML systems (Battleground B/D/E into single ensemble)
   - Create "High Conviction" tier (≥60% WR, ≥3 months track record)
   - Archive dormant systems to separate "Legacy" view

8. **Day 26‑28: Super‑Signal Enhancement**
   - Lower consensus threshold from 60% to 55% for bear markets
   - Add volume confirmation to super‑signal detection
   - Implement real‑time WebSocket updates for live signals

9. **Day 29‑30: Monitoring & Automation**
   - Add automated health checks for all data endpoints
   - Implement daily performance reports via Discord
   - Create hub‑status dashboard with uptime metrics

---

## 4. Error Fixing Steps (Immediate)

### 4.1 `updateAggregatorPanels is not defined`
**Location:** `hub/index.html:1421` (in `loadAll()`)
**Fix:**
```javascript
// MOVE THIS FUNCTION ABOVE loadAll()
function updateAggregatorPanels(data) {
  // ... existing code ...
}

async function loadAll() {
  // ... existing code ...
  if (aggregatorData) {
    updateAggregatorPanels(aggregatorData); // Now defined
  }
}
```

### 4.2 `favicon.ico 404`
**Fix:** Generate simple favicon:
```bash
# Using ImageMagick
convert -size 16x16 xc:#a855f7 -fill '#06b6d4' -draw 'circle 8,8 8,4' favicon.ico
```
Place in `hub/favicon.ico` and update HTML `<link>` if necessary (currently uses data URI).

### 4.3 `Failed to fetch quantum_fusion: undefined`
**Fix:** Remove from systems:
1. Delete QuantumFusion entry from `hub/data/systems_manifest.json` (lines 384‑399)
2. Remove from `hub/index.html` `SYSTEMS` array (lines 2299‑2303)
3. Optionally create placeholder JSON at repo root if system should remain

### 4.4 Missing Timestamps in Fresh Picks
**Fix:** Update `ENTRY_DATE_KEYS` in `hub/index.html:2315‑2318`:
```javascript
const ENTRY_DATE_KEYS = [
  'entryDate', 'timestamp_est', 'timestamp', 'entry_time', 'created_at',
  'entry_date', 'signal_time', 'opened_at', 'open_time', 'date_opened',
  'created', 'time', 'opened', 'timestamp_utc', 'entry_timestamp',
  'signal_timestamp', 'generated_at', 'date'
];
```

---

## 5. Expected Outcomes & Metrics

### 5.1 Performance Targets (30‑Day Post‑Implementation)
| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Overall Win‑Rate | ~45% | ≥60% | +15pp |
| Active Systems Count | 25 | 10‑12 | -60% (quality over quantity) |
| Portfolio Realized P/L | +4.3% | +8‑10% | +5.7pp |
| JavaScript Console Errors | 3 | 0 | 100% reduction |
| Fresh‑Picks with Timestamps | ~85% | 100% | Complete |

### 5.2 Risk Mitigation
1. **Model Degradation Risk:** Keep v1.3 config as fallback; A/B test retrained models.
2. **Over‑Consolidation Risk:** Maintain at least 8 orthogonal methodologies.
3. **Data‑Pipeline Risk:** Implement endpoint health monitoring before consolidation.

### 5.3 Success Criteria
- **Technical:** Zero JavaScript console errors; all endpoints return valid JSON.
- **Performance:** Top‑5 systems maintain ≥60% WR for 30 consecutive days.
- **Usability:** Fresh‑picks banner shows actionable signals with complete metadata.
- **Operational:** Daily automated health reports delivered to Discord.

---

## 6. Implementation Roadmap

### Week 1 (Stabilization)
- Fix JavaScript errors (Day 1‑2)
- Update timestamp detection (Day 3‑4)
- Pause worst performers (Day 5‑7)
- **Deliverable:** Error‑free hub with accurate fresh‑picks display

### Week 2‑3 (Model Optimization)
- Retrain Mercury 2 (Day 8‑12)
- Adjust Alpha Engine SL (Day 13‑16)
- Overhaul Battleground systems (Day 17‑21)
- **Deliverable:** 3 retrained systems reactivated with improved metrics

### Week 4 (Consolidation & Automation)
- System consolidation (Day 22‑25)
- Super‑signal enhancement (Day 26‑28)
- Monitoring automation (Day 29‑30)
- **Deliverable:** Leaner hub with higher conviction signals and automated health checks

---

## 7. Resource Requirements

### 7.1 Technical Resources
- **GitHub Actions:** 3‑5 minutes daily for endpoint health checks
- **Compute:** Retraining Mercury 2 (∼2 GPU hours)
- **Storage:** Additional 100MB for historical backtest data

### 7.2 Human Resources
- **Data Scientist:** 10‑15 hours for model retraining (Days 8‑21)
- **Frontend Developer:** 4‑6 hours for JavaScript fixes (Days 1‑2)
- **DevOps Engineer:** 5‑8 hours for monitoring setup (Days 29‑30)

### 7.3 Timeline Summary
- **Total Duration:** 30 days
- **Critical Path:** Model retraining (14 days)
- **Parallel Tasks:** Error fixes + consolidation (can overlap)

---

## 8. Conclusion

The current crypto prediction ecosystem has strong foundations but requires surgical intervention to eliminate underperformers and technical debt. By executing this 30‑day plan, we can transform the hub from a noisy collection of 25 systems into a focused, high‑conviction signal generator with ≥60% win‑rate and zero console errors.

**Next Immediate Actions:**
1. Fix `updateAggregatorPanels` ordering (15‑minute task)
2. Generate favicon.ico (5‑minute task)
3. Remove QuantumFusion from systems list (10‑minute task)
4. Expand `ENTRY_DATE_KEYS` (5‑minute task)

These four quick fixes will immediately improve user experience and set the stage for the systematic model improvements outlined in this plan.