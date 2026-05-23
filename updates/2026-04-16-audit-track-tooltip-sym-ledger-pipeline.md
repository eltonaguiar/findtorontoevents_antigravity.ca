# Audit Track: symbol ledger tooltip + resolved_closed track map

## What was wrong

- Live `audit_dashboard/index.html` still used a short Track tooltip (`strategy-wide … no X-specific WR`) with **no** warning glyph, no **n / W–L / pair WR** line, and no **“yet”** explanation when the ledger had unclassified exits.
- Per-(strategy, symbol) stats for the Track column were built from **`closed`** while forward truth uses **`resolved_closed`**, so symbol **n** could disagree with the deduped book.
- Symbol track lookup used only the display `strategy` string; when closed rows used a **canonical / id-prefix / alias** name, **`sym_track_total` stayed 0** even though NEARUSDT (etc.) had history.

## Changes

1. **`audit_trail/dashboard_generator.py`**
   - `_strategy_symbol_track_map = _build_strategy_symbol_track_stats(**resolved_closed**)` (was `closed`).
   - After existing `via` / `consensus` fallback, try **`_leaderboard_name_candidates_for_pick`** until a non-empty `(strategy, symbol)` bucket is found; set `track_sym_lookup_strategy` on the pick when this path hits.

2. **`audit_dashboard/template.html`** and **`audit_dashboard/index.html`**
   - Added **`_symPairLedgerLine(p)`**: one-line summary — symbol+strategy **n**, **W/L resolved**, **pair WR** or **n/a yet** (with reasons: no rows, key mismatch, or unclassified exits).
   - Track tooltips prefix with that line and **SHOWN IN CELL** for both bold (symbol) and italic (strategy-wide) modes.
   - Strategy-wide cells: **`_symTrackUseable`**, orange **\u26A0** via `_stratFallbackCautionSpan`, optional **`+N pair closes`** / **`sym WR pending`** sublabel (index aligned with template).

## Verification

- `python -m py_compile audit_trail/dashboard_generator.py` exits 0.
- After the next dashboard HTML generation / deploy, hover Track on a thin-symbol row: tooltip should show **resolved ledger n**, **W/L**, **pair WR or n/a yet**, then strategy-wide **SHOWN IN CELL** line.

## Note on differing percentages (e.g. 41% vs 43.6%)

Track (italic) uses **strategy-wide forward WR**; other badges/columns may use **symbol-specific** or **different** fields. The tooltip now states what the **cell** is showing vs the **pair ledger** line.
