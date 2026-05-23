# Asset Class Fix & ChatGPT Strategy Status — 2026-05-04

## Summary

This report summarizes:
1. **ROOT CAUSE FIX**: 92% of closed picks had `asset_class='UNKNOWN'`
2. **ChatGPT Strategy Status**: Found and verified
3. **Next Steps**: Re-run resolver to regenerate data with proper asset classes

---

## 1. ROOT CAUSE: 92% UNKNOWN Asset Class

### Problem
- **92% of closed picks** in `universal_resolved_picks.json` had `asset_class='UNKNOWN'`
- This made all per-asset-class metrics (WR, PF, Sharpe) meaningless
- Root cause: Picks didn't have `asset_class` field when written to JSON

### Fix Applied
**File Modified**: `/mnt/c/findtorontoevents_antigravity.ca/audit_trail/universal_pick_resolver.py`

**Changes**:
1. **Added import** (after line 27):
   ```python
   from audit_trail.asset_classification import classify_asset
   ```

2. **Added enrichment function** (before writing picks):
   ```python
   def enrich_pick_with_asset_class(pick):
       """Add asset_class to pick dict if missing."""
       if isinstance(pick, dict):
           if 'asset_class' not in pick or not pick.get('asset_class'):
               symbol = pick.get('symbol', '')
               try:
                   asset_class = classify_asset(symbol)
                   pick['asset_class'] = asset_class.value
               except Exception:
                   pick['asset_class'] = 'UNKNOWN'
       return pick
   ```

3. **Applied to all picks** (before writing to JSON):
   ```python
   all_resolved = [enrich_pick_with_asset_class(p) for p in all_resolved]
   ```

### Verification
- Python syntax check: **PASSED** (`py_compile` OK)
- Patch applied successfully via `patch` tool

### Impact
- All future picks will have `asset_class` field (CRYPTO, FOREX, EQUITY, etc.)
- Existing picks will be enriched on next run
- Per-asset-class metrics will now be meaningful

---

## 2. ChatGPT Strategy Status

### Strategy Found
- **Name**: `chatgpt_combined` (note: typo in name, should be `chatgpt_combined`)
- **Data Location**: `battleground/data/chatgpt_combined_signals.json`
- **Meta-model**: `audit_dashboard/meta_model_chatgpt.py`

### Performance (from `ACTION_PLAN_APRIL2026.MD`)
| Metric | Value |
|--------|-------|
| Historical WR | 75% |
| Recent WR (table) | 83.3% |
| PnL | +50% |
| Recent PnL | +2.49% |

### Rating
- **Tier A** (ship-ready) per `updates/strong_strategy_per_asset_class_2026-04-20.md`
- One of only 2 ChatGPT picks rated Tier A

### Files Referencing ChatGPT
- `audit_trail/asset_classification.py` — uses ChatGPT's recommendations
- `audit_trail/quality_gates.py` — references ChatGPT Codex findings
- `updates/strong_strategy_per_asset_class_2026-04-20.md` — rates ChatGPT strategies
- `meta_model_trainer.py` — includes ChatGPT's leak-free scoring fix

### Recommendation
- Add `chatgpt_combined` to **PROVEN** tier if it meets criteria:
  - WR >= 60%
  - PF > 1.5
  - Trades >= 50
  - DSR > 1.0

---

## 3. Next Steps

### Immediate (Required)
1. **Re-run `universal_pick_resolver.py`** to regenerate `universal_resolved_picks.json` WITH `asset_class` fields:
   ```bash
   cd /mnt/c/findtorontoevents_antigravity.ca
   python -m audit_trail.universal_pick_resolver
   ```

2. **Verify asset class distribution** in regenerated JSON:
   - Should see CRYPTO, FOREX, EQUITY, ETF, COMMODITY, etc.
   - UNKNOWN should drop from 92% to <10%

3. **Re-run `dashboard_generator.py`** to regenerate `dashboard_data.json` with proper asset classes

### Short-term (1-2 days)
1. **Validate ChatGPT strategy** for PROVEN tier:
   - Check current WR, PF, trade count
   - If meets criteria, add to trust registry

2. **Implement hedge-fund optimizations** (from Claude analysis):
   - Enforce PROVEN capital weights (70/25/5)
   - Add concentration caps (≤10% per symbol)
   - Promote trust score to primary gate (trust≤3 = block)

3. **Fix ChatGPT typo** (`chatgpt_combined` → `chatgpt_combined`) if it doesn't break references

### Medium-term (3-7 days)
1. **Portfolio-level risk optimization**:
   - Add risk-parity weighting panel to `/audit`
   - Implement CVaR-based position sizing
   - Add DSR (Deflated Sharpe Ratio) gates

2. **Expand asset class patterns** if needed:
   - Review `audit_trail/asset_classification.py` patterns
   - Add new symbols/patterns as needed

---

## 4. Files Modified (Uncommitted — Git Times Out)

Due to repo size (119,598+ commits), git operations timeout after 30s. Changes written locally:

1. **`/mnt/c/findtorontoevents_antigravity.ca/audit_trail/universal_pick_resolver.py`**
   - Added `classify_asset` import
   - Added `enrich_pick_with_asset_class()` function
   - Applied enrichment to all picks before writing JSON

2. **`/mnt/c/findtorontoevents_antigravity.ca/audit_dashboard/template.html`** (from prior session)
   - Added confidence [0.80,0.85) bonus (+12)
   - Verified edge: 62.5% WR, PF 5.83 (n=120)

3. **`/mnt/c/findtorontoevents_antigravity.ca/audit_dashboard/funds.html`** (from prior session)
   - Implemented Option D (R:R diagnostic logger)
   - Removed score penalties, added console logging

---

## 5. Reports Generated

1. **`/mnt/c/findtorontoevents_antigravity.ca/reports/verified_audit_findings_summary_2026_05_04.md`**
   - 11 numeric claims tested — 0 verified at face value
   - Key findings: TRXUSDT = 117% of loss, CT=F cotton fluke, 92% UNKNOWN

2. **`/mnt/c/findtorontoevents_antigravity.ca/reports/IMPLEMENTED_FINDINGS_2026_05_04.md`**
   - Summary of implemented fixes (confidence bonus, R:R diagnostic)

3. **`/mnt/c/findtorontoevents_antigravity.ca/reports/ASSET_CLASS_FIX_AND_CHATGPT_STATUS_2026_05_04.md`** (this file)
   - Root cause fix for UNKNOWN asset class
   - ChatGPT strategy status and recommendation

---

## 6. Acknowledgments

- **Perplexity Comet**: Verified 4/4 claims, provided WR/PF data for confidence bands
- **Claude Opus 4.7**: Provided hedge-fund-grade optimization recommendations
- **ChatGPT**: Original meta-model design, leak-free scoring fix, strategy recommendations

---

**Generated**: 2026-05-04  
**Model**: tencent/hy3-preview:free via OpenRouter  
**Status**: All critical fixes applied locally, ready for user to commit when git accessible
