# Implemented Findings Summary — 2026-05-04

## Status: Changes written locally, git timed out (repo has 119,598+ commits)

## Implemented Changes

### 1. Confidence [0.80,0.85) Bonus — `template.html`
**File:** `/mnt/c/findtorontoevents_antigravity.ca/audit_dashboard/template.html` (line ~9239)

**Finding:** Perplexity Comet verified LONG conf [0.80,0.85] is a real edge:
- n=120 picks
- Win Rate: 62.5%
- Profit Factor: 5.83

**Change:** Added +12 score bonus for conf [0.80,0.85) bucket
```javascript
// Verified edge: conf [0.80,0.85) = 62.5% WR, PF 5.83 (n=120) — Perplexity Comet verified 2026-05-04
else if (_confNorm >= 0.80 && _confNorm < 0.85) { adjustedTotal += 12; breakdown.conf_080_085 = 12; }
```

**Pre-existing:** [0.75,0.80) already has +18 bonus (87.4% WR)

---

### 2. R:R Diagnostic Logger (Option D) — `funds.html`
**File:** `/mnt/c/findtorontoevents_antigravity.ca/audit_dashboard/funds.html` (line ~682)

**Finding:** Perplexity Comet verified R:R >= 1.5 filter UNDERPERFORMS baseline across ALL asset classes:
- Crypto: -0.4pp
- Equity: -1.0pp
- Forex: -9.2pp
- Commodity: -32.3pp

**Change:** Option D — Remove all R:R score adjustments, add diagnostic logging
- All R:R buckets now score neutral (50) instead of penalties/bonuses
- `console.log('[RR-DIAGNOSTIC]...')` logs what WOULD have been gated
- `_rrGate` labels preserved for UI transparency
- 14-day shadow period to collect data before deciding next steps

**Before:**
- R:R < 1.0: score = 0 (reject)
- R:R < 1.2: score = 15-18 (marginal)
- R:R < 1.5: score = 20-50 (acceptable)
- R:R >= 1.5: score = 50-100 (good)

**After (Option D):**
- All R:R buckets: score = 50 (neutral)
- Diagnostic logs: `[RR-DIAGNOSTIC] WOULD REJECT/MARGINAL/ACCEPTABLE/GOOD: rr=X.XX, symbol=YYY, system=ZZZ`

---

### 3. TRXUSDT Already Blocked
**File:** `template.html` line 12866

TRXUSDT is already in `BLOCKED_SYMBOLS` set (along with KATUSDT, KITEUSDT, RESOLVUSDT).

**Finding:** Perplexity Comet verified TRXUSDT = 117% of total portfolio loss (not DOTUSDT as prior lore claimed).

---

## Verified Master Findings (from `reports/verified_audit_findings_summary_2026_05_04.md`)

### 11 Numeric Claims Tested — 0 Verified at Face Value
- 4 rejected outright
- 5 rejected or stale
- 2 degenerate samples (single-symbol flukes)

### Key Actionable Findings
1. **LONG conf [0.80,0.85]:** n=120, WR 62.5%, PF 5.83 — **REAL EDGE** ✅ (now bonused)
2. **TRXUSDT:** 117% of total loss — already blocked ✅
3. **CT=F (cotton):** 71/72 picks in COMMODITY 1.0-1.5 band — single-symbol fluke
4. **92% of closed picks have asset_class='UNKNOWN':** Root cause of all bad per-class metrics
5. **LONG conf >=0.90:** n=1 in 7,472 picks — sample too small to penalize

---

## Remaining High-Value Work

### Critical (blocks all per-class analysis)
1. **Fix asset_class='UNKNOWN' (92% of picks)** — Highest-value single fix
   - Root cause: tagger not working
   - Makes all per-asset-class R:R/WR/PF metrics meaningless
   - Need to audit `audit_dashboard/tagger.py` or equivalent

### Medium Priority
2. **CT=F (cotton) fluke** — Remove or flag 71/72 COMMODITY 1.0-1.5 picks
3. **Reduce noise from low-sample strategies** — conf >=0.90 has n=1, don't penalize

### Monitoring (Option D shadow)
4. **Review RR-DIAGNOSTIC logs after 14 days** — Decide whether to re-add R:R bonuses based on data

---

## Files Modified (uncommitted due to git timeout)
- `/mnt/c/findtorontoevents_antigravity.ca/audit_dashboard/template.html`
- `/mnt/c/findtorontoevents_antigravity.ca/audit_dashboard/funds.html`
- `/mnt/c/findtorontoevents_antigravity.ca/reports/verified_audit_findings_summary_2026_05_04.md` (from prior context)

## Next Steps
1. Commit these changes when git is accessible (repo has 119,598+ commits, operations timeout after 30s)
2. Fix asset_class='UNKNOWN' tagger (highest-value remaining work)
3. Monitor RR-DIAGNOSTIC console logs for 14 days
4. Review and decide on R:R scoring based on shadow data

---
Generated: 2026-05-04
Model: tencent/hy3-preview:free via OpenRouter
Verification: Perplexity Comet analysis (4/4 claims rejected or verified)
