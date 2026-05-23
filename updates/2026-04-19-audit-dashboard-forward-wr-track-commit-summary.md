# Commit summary: audit dashboard data clarity (forward WR + Track tooltip)

## Why these changes

1. **`forward_wr` vs `strat_fwd_wr` mismatches**  
   Some pick rows carried `forward_wr` as a **fraction** (e.g. `0.8182` meaning ~81.8%) when upstream had already set `forward_trades`. The generator only backfills `forward_wr` from `_get_fwd_stats` when `forward_trades` is missing or zero, so the fractional value was never converted to **percent (0–100)**. That made spot-checks against the strategy leaderboard look like the pipeline was wrong when it was often a **unit encoding bug**.

2. **Track column threshold was hard to interpret**  
   The UI gates **symbol-specific** Track display on **n ≥ 3** closes for that **strategy + symbol** (`sym_track_total`). Operators could see italic/strategy-wide cells but had to guess how many symbol closes existed. The tooltip now states **explicit progress** (`k/3`, “need m more”) so it is obvious where each symbol stands relative to the gate.

## What changed (files)

| File | Change |
|------|--------|
| `audit_trail/dashboard_generator.py` | After agreement enrichment, normalize `forward_wr`: if it is a **float** in `(0, 1]`, multiply by 100 and round to one decimal. **Integer `1` is left unchanged** (treated as 1% in percent units, not 100%). |
| `audit_dashboard/template.html` | Introduce `_SYM_TRACK_MIN_N = 3`; use it in `_symTrackUseable` and `_symTrackSummaryForTooltip`. Tooltip copy always includes **progress toward symbol-specific Track** and handles **no closes / thin n / no classified W/L** more explicitly. Track column header tip mentions **n/3** on hover. |

## Granular notes (also in repo)

- `updates/2026-04-15-dashboard-forward-wr-fraction-normalize.md` — forward_wr normalization detail.
- `updates/2026-04-15-audit-track-tooltip-n-progress.md` — Track tooltip n/3 behavior.

## How verified

- `python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"` exits 0.
- **Playwright / live dashboard:** after CI regenerates `audit_dashboard/index.html` from `template.html`, re-run audit E2E or manually hover Track to confirm progress text.

## Scope of this commit

This commit is intentionally limited to **generator normalization** and **dashboard template** UX for forward/track clarity. Other modified files in the working tree (caches, unrelated engines, auto-generated `index.html`) were **not** included.
