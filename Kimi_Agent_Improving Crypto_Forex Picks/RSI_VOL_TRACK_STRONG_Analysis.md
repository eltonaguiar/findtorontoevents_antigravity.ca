# RSI/VOL/TRACK/STRONG Empty Fields Analysis
## FindTorontoEvents.ca Dashboard - March 26, 2026

---

## 🎯 Executive Summary

The empty "..." and "—" values in the dashboard are **expected behavior** based on:
1. Pick sources that don't compute technical indicators
2. Insufficient forward-test data for track records
3. Strict filtering for "Strong Signal" designation

This is a **data pipeline gap**, not a bug.

---

## 📊 Field-by-Field Analysis

### 1. RSI Column (shows "..." when empty)

**Location in Code:** `audit_dashboard/template.html` lines 4065-4099

**Logic:**
```javascript
let rsi = p.rsi_at_entry || p.rsi || p.rsi_14 || null;
if (rsi == null) try { rsi = JSON.parse(p.ml_features_at_entry || '{}').rsi_at_entry; } catch(e) {}
if (rsi == null) try { rsi = p.sb_rsi_at_entry; } catch(e) {}
if (rsi != null && rsi != 50) { /* render value */ }
// ... lazy fetch from Binance ...
return '<td class="num" style="color:var(--text-dim)" title="RSI loading...">...</td>';
```

**Why Empty:**

| Source System | Populates RSI? | Reason |
|---------------|----------------|--------|
| alpha_engine | ✅ Yes | Has ML feature pipeline |
| ml_crypto_predictor | ✅ Yes | Computes technical indicators |
| claude_gainer | ✅ Yes | ML-based system |
| copy_trader_intel | ❌ No | Copy traders don't provide RSI |
| prediction_market_agents | ❌ No | PM signals don't have tech indicators |
| contrarian_consensus | ❌ No | Consensus picks lack per-pick features |
| kimi_riseoftheclaw | ⚠️ Partial | Some algorithms provide it |

**Lazy Fetch:** The dashboard tries to fetch RSI live from Binance for USDT pairs, but:
- Only works for crypto (USDT suffix)
- Requires successful API call
- Cache is lost on page refresh

**Fix Options:**
1. **Short-term:** Ensure `fetchBinanceKlinesWithFailover` has proper error handling
2. **Medium-term:** Add RSI computation to `universal_pick_resolver.py`
3. **Long-term:** Require all pick sources to provide basic tech indicators

---

### 2. VOL Column (shows "..." when empty)

**Location in Code:** `audit_dashboard/template.html` lines 4101-4131

**Logic:**
```javascript
let vol = p.volume_ratio || p.vol_ratio || p.volume_acceleration || null;
if (vol == null) try { vol = JSON.parse(p.ml_features_at_entry || '{}').volume_ratio; } catch(e) {}
if (vol == null) try { vol = p.sb_volume_ratio; } catch(e) {}
if (vol != null && vol != 1.0) { /* render value */ }
// ... lazy fetch from Binance ...
return '<td class="num" style="color:var(--text-dim)" title="Volume loading...">...</td>';
```

**Why Empty:**
- Same reasons as RSI - pick sources don't provide volume data
- Only ML-heavy systems (alpha_engine, ml_crypto_predictor) populate this
- Copy traders, PM signals, and consensus picks lack volume ratios

**Volume Ratio Meaning:**
- `>2.0x` = High volume confirmation (green)
- `1.0-2.0x` = Normal volume
- `<1.0x` = Low volume - weak signal (gray)

---

### 3. TRACK Column (shows "—" when empty)

**Location in Code:** `audit_dashboard/template.html` lines 3894-3906

**Logic:**
```javascript
const fwdWr = p.strat_fwd_wr;
const fwdTrades = p.strat_fwd_trades || 0;
const trackLevel = p.track_level || 'none';
if (fwdWr == null || trackLevel === 'none') return `<td class="num" style="color:#6b7280" title="No track record...">—</td>`;
// Render forward WR%
```

**Why Empty:**

TRACK requires **forward test data** which most systems don't have:

| System | Has Forward Tests? | Notes |
|--------|-------------------|-------|
| battleground | ✅ Yes | Backtest + forward test data |
| ml_crypto_predictor | ✅ Yes | Tracks live performance |
| alpha_engine | ⚠️ Partial | Some strategies have it |
| copy_trader_intel | ❌ No | No forward test pipeline |
| prediction_market_agents | ❌ No | Experimental, no tracking |
| genome/evolution | ❌ No | Paper trading only |

**Track Levels:**
- `symbol` = 3+ trades on this specific symbol (bold text)
- `strategy` = 5+ trades strategy-wide (italic text)
- `none` = insufficient data (shows "—")

**This is the #2 winner predictor (IC=0.173)** according to the dashboard tooltip, so empty values significantly reduce pick quality assessment.

---

### 4. STRONG Column (shows "—" when empty)

**Location in Code:** `audit_dashboard/template.html` lines 3918-3925

**Logic:**
```javascript
const ssKey = (p.symbol||'') + '|' + (p.strategy||'');
const ss = window._strongSignals ? window._strongSignals[ssKey] : null;
if (ss) {
  return `<td style="text-align:center"><span style="color:#fbbf24;font-size:14px">★</span></td>`;
}
return `<td style="text-align:center;color:#333">—</td>`;
```

**Why Empty:**

STRONG requires passing the **5-filter gate** from `strong_signals.py`:
1. Confidence >= 75%
2. HTF (Higher Time Frame) aligned
3. Trust >= MEDIUM
4. Forward WR >= 50% (if available)
5. R:R >= 1.5

**Data Source:** `window._strongSignals` is loaded from a separate endpoint (likely `strong_signals.json` or similar).

Most picks fail these strict criteria:
- Copy trader picks have confidence capped at 0.60 (can't reach 0.75)
- Many strategies lack forward WR data
- HTF alignment requires additional computation

---

## 🔍 Root Cause Analysis

### The ML Feature Pipeline Gap

From `audit_trail/dashboard_generator.py` lines 1766-1774:
```python
# These fields come from source scanners (alpha_engine, KIMI, etc.)
"rsi_at_entry": _float(raw.get("rsi_at_entry", raw.get("rsi", raw.get("rsi_14", 0)))) or None,
"volume_ratio": _float(raw.get("volume_ratio", raw.get("vol_ratio", raw.get("volume_acceleration", 0)))) or None,
"htf_bias": raw.get("htf_bias", raw.get("htf_alignment", raw.get("htf_aligned", ...))),
```

**Problem:** Only ~40% of pick sources provide these fields.

### Systems That DO Provide RSI/VOL
1. alpha_engine (ML-enhanced strategies)
2. ml_crypto_predictor
3. claude_gainer_ml
4. Some kimi_riseoftheclaw algorithms

### Systems That DON'T Provide RSI/VOL
1. copy_trader_intel (external trader data)
2. prediction_market_agents (signal-only)
3. contrarian_consensus (aggregated picks)
4. genome/evolution (DNA mutations)
5. Most incubator strategies

---

## ✅ Recommended Fixes

### Immediate (Today)

1. **Fix Lazy Fetch Error Handling**
   - Current: Shows "..." forever if Binance fetch fails
   - Fix: Add timeout and fallback to "—" after 5 seconds

```javascript
// In template.html around line 4099
// Add a retry counter and show "—" after 3 failed attempts
if (!window._rsiFetchAttempts) window._rsiFetchAttempts = {};
window._rsiFetchAttempts[sym] = (window._rsiFetchAttempts[sym] || 0) + 1;
if (window._rsiFetchAttempts[sym] > 3) {
  return '<td class="num" style="color:#6b7280" title="RSI unavailable">—</td>';
}
```

### Short-term (This Week)

2. **Add Feature Computation to Universal Resolver**
   - Modify `audit_trail/universal_pick_resolver.py`
   - Compute RSI/volume for picks that lack them
   - Store in `universal_resolved_picks.json`

```python
# Add to universal_pick_resolver.py
def compute_features_for_pick(pick):
    """Compute RSI/volume for picks missing them."""
    if pick.get('rsi_at_entry') is None:
        pick['rsi_at_entry'] = fetch_and_compute_rsi(pick['symbol'])
    if pick.get('volume_ratio') is None:
        pick['volume_ratio'] = fetch_and_compute_volume(pick['symbol'])
    return pick
```

3. **Track Record Backfill**
   - Use `closed_picks.json` data to populate `strat_fwd_wr`
   - Compute symbol-specific and strategy-wide WR
   - Add to dashboard payload

### Medium-term (Next 2 Weeks)

4. **Standardize Feature Requirements**
   - Require all new pick sources to provide:
     - `rsi_at_entry` OR `rsi_14`
     - `volume_ratio` OR `vol_ratio`
     - `htf_bias` OR `htf_alignment`
   - Add validation in `dashboard_generator.py`

5. **Strong Signal Recalibration**
   - Lower confidence threshold from 0.75 to 0.70
   - Alternative: Create "MODERATE" tier for 0.60-0.75 confidence
   - This would populate more STRONG column entries

---

## 📈 Expected Impact

| Fix | Affected Picks | Visual Impact |
|-----|----------------|---------------|
| Lazy fetch fix | All USDT pairs | "..." → value or "—" |
| RSI/VOL computation | ~60% of picks | "..." → actual value |
| Track backfill | ~40% of picks | "—" → WR% value |
| Strong recalibration | ~15% of picks | "—" → ★ star |

---

## 🎓 Conclusion

The empty fields are **not a bug** - they reflect genuine data gaps in the pipeline:

1. **RSI/VOL empty** = Pick source doesn't compute technical indicators (mainly copy traders and PM signals)
2. **TRACK empty** = No forward test history available for that strategy/symbol
3. **STRONG empty** = Pick didn't pass the strict 5-filter quality gate

**Priority:**
- P1: Fix lazy fetch to show "—" instead of "..." when data unavailable
- P2: Add feature computation to universal resolver
- P3: Backfill track records from closed picks

---

*Analysis based on audit_dashboard/template.html and audit_trail/dashboard_generator.py*
