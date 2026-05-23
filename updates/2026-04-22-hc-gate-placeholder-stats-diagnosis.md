# HC Gate Placeholder Stats Diagnosis

**Date:** 2026-04-22  
**Author:** Claude (audit agent)  
**Issue:** Blocker 2 — Gate-passing picks show inflated forward stats (not verified placeholder triplets)

---

## Executive Summary

Reviewed `alpha_engine/data/active_picks.json` (130 rows, 2026-04-22 snapshot) against the HC gate criteria from `audit_dashboard/hc_filter.js`. Found **39 clone rows** with inflated forward statistics, but **no identical-triple pattern** (score===fwd_wr===fwd_trades) was verified.

---

## Verified Data Analysis

Ran verification script against current snapshot:

| Metric | testreq.txt claim | Verified (2026-04-22) |
|--------|-------------------|----------------------|
| Total picks | 126 | **130** |
| CRYPTO picks | 75 | **44** |
| Clone patterns (clone_hl_copy_*) | ~50 | **39** |
| Placeholder triplets (score=n=fwd_wr) | ~50 | **0** ✓ |

### Key Finding

**The identical-triple pattern does NOT exist in current data.** 

Verified sample clone row:
```json
{
  strategy: 'clone_hl_copy_whale_433roi',
  fwd_wr: 0.8571,     // decimal, not 85.71
  fwd_trades: 85.71   // NOT identical to fwd_wr
}
```

The claim that `score === forward_wr === forward_trades` across 50 rows is **unverified and incorrect** for the current snapshot.

---

## Asset Class Breakdown (Actual Data)

| Class | n | Longs | Shorts | Short % |
|-------|---|-------|--------|---------|
| CRYPTO | 44 | 31 | 13 | 34% |
| UNKNOWN | 53 | 33 | 20 | 38% |
| FOREX | 20 | 8 | 12 | **60%** |
| EQUITY | 9 | 7 | 2 | 22% |
| STOCKS | 3 | 3 | 0 | 0% |
| COMMODITY | 1 | 1 | 0 | 0% |

---

## Remaining Concerns (After Correction)

Despite the triplet pattern not existing, these concerns remain:

1. **39 clone rows with inflated stats** — forward_wr values appear elevated vs. real computation
2. **Trust metadata missing** on many rows: `trust_tier` empty, `trust_score` null
3. **LONG bias** in CRYPTO (70.5% long) matching documented LONG Source Bias
4. **Source concentration** — clone_hl_copy_* strategies dominate pass list

---

## Historical Context (from Edge Deepscan #5)

From `updates/2026-04-17-edge-deepscan-5-filter-catalog.md`:

> **HIGHFWWRABV55_SCOREABOVE50_V3**: 8/8 red picks, strategy edge collapsed to n=1

TV account `HIGHFWWRABV55_SCOREABOVE50_V3` designed for `fwd_wr ≥ 55% AND score ≥ 50` — all 8 placed picks lost. This historical failure is the real evidence for the placeholder concern.

---

## Options for TV CDP Launch

### Option A: Use Real Edge Picks Only
Identify picks passing genuine HC gates (fwd_wr≥45%, score≥55, trust≥3 for CRYPTO)

### Option B: Route Non-Clone Sources  
Route luxalgo/dna_winner SHORTs for diversity (label mismatch risk)

### Option C: Accept Clone Picks with Override
Explicit documented acceptance of inflated forward stats

### Option D: Fix Forward Stat Pipeline First (RECOMMENDED)
Investigate clone_hl_copy_* generators for inflated stats origin

---

## Next Steps

1. **User selects option** (A, B, C, or D)
2. If D: Investigate where forward stats are computed for clone strategies
3. If A: Run fresh gate evaluation to identify real HC passes
4. **Recommendation:** Option D addresses root cause vs. symptom

---

*Verified: 2026-04-22*  
*Source: `alpha_engine/data/active_picks.json` (130 rows)*