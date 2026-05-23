# RSI/VOL/TRACK/STRONG Fixes Deployed
## March 26, 2026

---

## ✅ Fixes Implemented

### 1. Feature Enricher Module (NEW)
**File:** `audit_trail/feature_enricher.py` (NEW - 180 lines)

**What it does:**
- Computes RSI-14 for picks that don't have it
- Computes volume ratio for picks that don't have it
- Fetches Binance kline data with failover
- Caches results to avoid redundant API calls
- Integrates into universal pick resolver

**Functions:**
```python
enrich_pick_with_features(pick)     # Enrich single pick
enrich_picks_batch(picks)           # Enrich batch of picks
_compute_rsi(closes, period=14)     # RSI calculation
_compute_volume_ratio(volumes)      # Volume ratio calculation
```

**Integration:** Added to `universal_pick_resolver.py` - every pick is now enriched before resolution.

---

### 2. Dashboard Template Improved
**File:** `audit_dashboard/template.html`

**Changes:**
- Added retry counter for RSI lazy-fetch (max 2 attempts)
- Added retry counter for volume lazy-fetch (max 2 attempts)
- After 2 failed attempts, shows "—" instead of "..."
- Prevents infinite "..." state when data is unavailable

**Before:**
```javascript
return '<td class="num" style="color:var(--text-dim)" title="RSI loading...">...</td>';
```

**After:**
```javascript
if (window._rsiFetchAttempts[sym] <= 2) {
    return '<td class="num" style="color:var(--text-dim)" title="RSI loading...">...</td>';
}
return '<td class="num" style="color:#6b7280" title="RSI unavailable">—</td>';
```

---

## 📊 Impact Analysis

### Before Fixes
| Column | Empty State | Cause |
|--------|-------------|-------|
| RSI | "..." forever | No source data + lazy fetch fail |
| VOL | "..." forever | No source data + lazy fetch fail |
| TRACK | "—" | No forward test data |
| STRONG | "—" | Doesn't meet 5-filter criteria |

### After Fixes
| Column | Empty State | Improvement |
|--------|-------------|-------------|
| RSI | Value or "—" | Universal resolver computes it |
| VOL | Value or "—" | Universal resolver computes it |
| TRACK | "—" | (No change - requires forward tests) |
| STRONG | "—" | (No change - requires strict criteria) |

---

## 🔍 Why TRACK and STRONG Still Show "—"

### TRACK Column
**Requirement:** Forward test data (`strat_fwd_wr`)

**Why empty:**
- Most systems don't track forward performance
- Only battleground, ml_crypto_predictor have this data
- Requires 5+ closed trades strategy-wide OR 3+ on specific symbol

**Fix:** Would need to backfill from closed picks (separate effort)

### STRONG Column
**Requirement:** Pass 5-filter gate:
1. Confidence >= 75%
2. HTF aligned
3. Trust >= MEDIUM
4. Forward WR >= 50%
5. R:R >= 1.5

**Why empty:**
- Copy trader picks capped at 0.60 confidence (can't reach 0.75)
- Most picks lack forward WR data
- Strict criteria intentionally limits "strong" signals

**Fix:** Lower confidence threshold OR create "MODERATE" tier

---

## 📈 Expected Improvements

### Immediate (Next Hour)
- Universal resolver runs and computes RSI/VOL for active picks
- Dashboard shows actual values instead of "..."

### Short-term (24h)
- ~60% of picks should show RSI values
- ~60% of picks should show VOL values
- Remaining 40% are non-crypto or failed fetches (show "—")

---

## 🧪 Testing

### Test Feature Enricher
```bash
cd E:\findtorontoevents_antigravity.ca
python -c "
from audit_trail.feature_enricher import enrich_pick_with_features
test = {'symbol': 'BTCUSDT', 'direction': 'LONG'}
enriched = enrich_pick_with_features(test)
print(f'RSI: {enriched.get(\"rsi_at_entry\", \"N/A\")}')
print(f'VOL: {enriched.get(\"volume_ratio\", \"N/A\")}')
"
```

### Verify Integration
```bash
python -c "
import json
from pathlib import Path
# Check resolver now imports feature_enricher
resolver = Path('audit_trail/universal_pick_resolver.py').read_text()
print('Feature enricher integrated:', 'feature_enricher' in resolver)
"
```

---

## 📝 Files Modified

1. **audit_trail/feature_enricher.py** (NEW)
   - RSI/volume computation module
   - Binance kline fetching with failover
   - Caching system

2. **audit_trail/universal_pick_resolver.py**
   - Added import and call to `enrich_pick_with_features()`
   - Every pick now enriched before resolution

3. **audit_dashboard/template.html**
   - Added retry counters for lazy fetch
   - Shows "—" after 2 failed attempts instead of "..."

---

## 🎯 Success Criteria

- [x] Feature enricher module created
- [x] Integrated into universal resolver
- [x] Dashboard template improved
- [ ] RSI values appear for >50% of picks (check in 1h)
- [ ] VOL values appear for >50% of picks (check in 1h)
- [ ] No more permanent "..." states

---

*Fixes deployed: March 26, 2026*
