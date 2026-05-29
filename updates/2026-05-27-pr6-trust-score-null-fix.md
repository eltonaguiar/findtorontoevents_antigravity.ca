# PR6: Fix trust_score NULL + HC Overlay Fallback

**Date:** 2026-05-27
**Branch:** `fix/pr6-trust-score-null-fix`
**Severity:** P0 (trust_score NULL on 99.99% of closed picks)

## Problem

`trading_picks.trust_score` is NULL on 38,884 of 38,889 closed picks. The High Conviction overlay (`hc_filter.js`) requires `trust_score >= 6` — so with trust=0, **every single pick fails the HC gate**. The cited "CRYPTO 60.3% N=562 and EQUITY 68.1% N=72" HC stats are unreproducible.

## Changes

### File: `audit_dashboard/hc_filter.js`
- **Added trust_tier → trust_score fallback:** When trust_score is 0/null, derive from trust_tier:
  - PROVEN=9, ELITE=8, TRUSTED=7, DEVELOPING=5, WATCH=3, SANDBOX/UNPROVEN/PROBATION/DEMOTED=1
- HC overlay now works even when trust_score is NULL, as long as trust_tier is populated

### File: `tools/backfill_trust_score.py`
- **Added `--mysql` flag:** Backfills trust_score directly in MySQL `trading_picks` table
- Derives numeric score from trust_tier via CASE statement
- Dry-run by default, `--apply` to execute
- Preserves existing JSON backfill mode

## Impact Analysis

- **HC overlay:** Immediately functional — picks with trust_tier=TRUSTED or higher now pass the trust gate
- **HC stats:** Should become reproducible within 24h of dashboard regeneration
- **MySQL backfill:** `python tools/backfill_trust_score.py --mysql --apply` updates all 38,884 NULL rows
- **Risk:** LOW — tier-to-score mapping is conservative (TRUSTED=7, just above the floor of 6)

## Verification
1. Run `python tools/backfill_trust_score.py --mysql` (dry-run) to see affected rows
2. Run with `--apply` to backfill
3. Check `/audit/` HC overlay — should show non-empty pick list
4. Verify CRYPTO HC stats match claimed 60.3% ± 5pp
