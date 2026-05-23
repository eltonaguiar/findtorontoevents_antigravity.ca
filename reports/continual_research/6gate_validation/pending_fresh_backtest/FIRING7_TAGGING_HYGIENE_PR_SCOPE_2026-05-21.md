# PR Scope: EQUITY Tagging Hygiene Fix (P0)

**Date:** 2026-05-21 (Firing 7 of continual 6-gate research loop)  
**Priority:** P0 — Blocks clean EQUITY, ETF, and multiple high-conviction candidates (H-037, vix_regime, etc.)

## Problem Statement
90.8% of historically tagged "EQUITY" resolved picks in the audit pipeline are actually native cryptocurrency pairs (BTC-USD, ETH-USD, etc.). This is caused by:
- Emitters (signal_tracker.py and similar) not setting `asset_class`.
- `dashboard_generator.py` defaulting missing values to "EQUITY" (and "FOREX" in the CFTC branch).
- A scoring bonus in `quality_gates.py` that further cements the misclassification.

Result: Real clean EQUITY sample is ~20 trades. H-037 (ETF VIX carry) and other EQUITY-related work are untestable. Public /audit dashboard shows polluted data.

## Scope of Changes (Minimal & Safe)

1. **audit_trail/dashboard_generator.py**
   - Replace two hardcoded defaults (lines ~8254 and ~8282) with call to new `_infer_asset_class(symbol)` helper.
   - Add the helper method (fail-loud, symbol-based inference).

2. **KIMI_RISEOFTHECLAW/signal_tracker.py** (and main `signal_tracker.py` if used in prod path)
   - Ensure `asset_class` is set at emission time for crypto/forex symbols (use existing `classify_asset` or simple pattern match).

3. **audit_trail/quality_gates.py**
   - Remove or condition the erroneous +10 bonus for `("EQUITY", "signal_validation")`.

4. **One-time backfill** (script or SQL)
   - Re-classify the ~198 polluted rows in `universal_resolved_picks.json` and `at_raw_picks`.

5. **Optional but recommended**
   - Add validation in `universal_pick_resolver.py` to reject or flag crypto symbols tagged as EQUITY.

## Verification Steps (Post-Merge)
- Re-run `tools/validate_resolved_picks.py --by-asset-class --min-trades 10`
- Confirm `asset_class_breakdown` shows sharp drop in "EQUITY" crypto pollution and rise in clean CRYPTO count.
- Public /audit dashboard banner should start reflecting fresh, correctly classified data within the next hourly run.
- H-037 and EQUITY vix_regime candidates become testable in the 6/8-gate framework.

## Rollback Plan
- Revert the three code files.
- Re-run the resolver/backfill with previous logic if needed.

## Files Changed
- audit_trail/dashboard_generator.py (main change)
- KIMI_RISEOFTHECLAW/signal_tracker.py (or main signal_tracker.py)
- audit_trail/quality_gates.py
- New backfill script (one-time)

## Estimated Effort
- 1–2 hours for code changes + testing
- 30–60 min for backfill + verification

This fix unblocks the entire EQUITY and lighter-class 6-gate workstream and is a prerequisite for any credible claim of "institutional-grade" data quality.