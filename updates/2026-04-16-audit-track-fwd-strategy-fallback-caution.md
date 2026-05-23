# Audit dashboard: Track / FWD WR / FWD N strategy-fallback caution

**Date:** 2026-04-16  
**Area:** `audit_dashboard/template.html` (source; `index.html` is CI-regenerated)

## What was missing

- **Track** used italic + strategy-wide WR when symbol-specific history had fewer than three resolved closes, but there was no **warning icon** and tooltips did not consistently show **both** symbol-specific and strategy-wide forward stats.
- **FWD WR** and **FWD N** are always strategy-wide (correct for HC gating), but when symbol track was still “thin” there was no **visual caution** and tooltips did not combine **strategy + symbol** context.

## What changed

- Added helpers: `_symTrackUseable`, `_normStratWrPctPick`, `_symTrackSummaryForTooltip`, `_stratWideSummaryLine`, `_stratFallbackCautionSpan`.
- **`_ic_track`:** bold path (n≥3 symbol): tooltip includes symbol line + strategy line. Italic path: warning glyph (U+26A0 U+FE0F) + dual tooltip on icon and percentage.
- **`strat_fwd_wr` / `strat_fwd_trades`:** same warning when symbol track is not useable for Track (`!_symTrackUseable`); tooltips include strategy-wide and symbol-specific lines.
- **`_ic_regime`** inner tooltip uses `_symTrackUseable` instead of duplicating the n≥3 condition.
- Updated `colTips._ic_track` and `allActiveCols` tips for Track / FWD WR / FWD N.

## Verification

- `python audit_dashboard/check_template_sync.py` — exit 0.

## Deploy note

After merge to `main`, the audit-dashboard workflow should regenerate `audit_dashboard/index.html` from `template.html`.
