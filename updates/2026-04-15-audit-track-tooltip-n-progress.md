# Audit dashboard: Track tooltip shows symbol n/X progress toward n≥3

## Change

In `audit_dashboard/template.html`, `_symTrackSummaryForTooltip` now always states **current close count vs threshold** for that **strategy + symbol** (e.g. `2/3 closes`, `need 1 more`), using the same gate as `_symTrackUseable` (`sym_track_total` vs minimum3).

Introduced `_SYM_TRACK_MIN_N = 3` once and reused it in `_symTrackUseable` so the cell rule and tooltip stay aligned.

## Edge cases

- **No closes:** progress `0/3`.
- **Closes but no classified W/L** (`sym_track_wr` null): explains missing outcomes while still showing close count progress.

## Verification

- Manual: open Active picks, hover Track — tooltip should include `Progress for symbol …: k/3 closes … need … more` until k≥3.
