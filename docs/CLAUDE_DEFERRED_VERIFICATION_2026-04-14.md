# Claude deferred items #1–4 — verification (2026-04-14)

Automated checks run in-repo. Repeat anytime:

```powershell
python tools/_verify_claude_deferred_items.py
```

## #1 Scanner calibration JSON

| Path | Status (this workspace) |
|------|-------------------------|
| `.tmp-validation-mcp/scanner_calibration_config.json` | **Missing** (not in git; MCP folder has other artifacts only) |
| `alpha_engine/data/scanner_calibration_config.json` | **Missing** — add when exporting from validation MCP |

**Assist shipped:** Optional hook **`alpha_engine/scanner_score_calibration.py`** + example **`alpha_engine/data/scanner_calibration_config.example.json`**. `alpha_engine/scanner.py` applies bucket deltas **after** short-gate ML mutations and **before** regime ML filtering, only if a real `scanner_calibration_config.json` exists with `"enabled": true`.

**Existing related code:** `alpha_engine/model_calibration.py` + `production_scanner.apply_calibration_to_picks` (Platt/isotonic on closed picks). The new hook is **scanner-local** bucket tweaks; keep schemas separate to avoid double-applying.

## #2 Luxalgo alts (`vt_csv_edge_luxalgo_alts.py`)

**Status:** File **not present** under `baby_strategies/`. No LuxAlgo string matches in `baby_strategies/*.py`. This item is **still a stub / not landed** — needs implementation + a hook in `incubator/backtest_team/forward_signal_scanner.py` (and/or `alpha_engine` scanner) once the module exists.

## #3 `closed_picks.json` quarantine

| Metric | Value |
|--------|--------|
| Rows in `alpha_engine/data/closed_picks.json` | 4,270 |
| Ghost heuristic (same entry/exit ~0, or ~0 PnL + no exit_reason) | **800** (18.7%) |
| Duplicate keys (symbol + strategy + direction + entry minute) | **407** (9.5%) |

**`alpha_engine/quarantine_closed_picks.py` (default dry run):** Phase 1 ghosts **800**, Phase 2 duplicates among non-ghosts **402**, **1,202** total quarantined (**28.1%** clean reduction). Does **not** overwrite `closed_picks.json` unless run with `--apply`.

Claude’s **1,609 / 38.7%** figures likely used **`data_quality_gate.py`** or a different dedup definition — that filename **was not found** in the repo root; **`quarantine_closed_picks.py`** is the operational equivalent documented here.

**Policy:** Do not run `--apply` without backup + explicit approval; script already writes only to `closed_picks_quarantine.json` / `closed_picks_clean.json` on apply.

## #4 Orphan `vt_*` strategies

| Count | Description |
|-------|-------------|
| 45 | `baby_strategies/vt_*.py` files |
| 6 | `VT*Strategy` entries in `incubator/backtest_team/forward_signal_scanner.py` `TIER1_STRATEGIES` |
| **39** | `vt_*.py` primary `*Strategy` class **not** in that TIER1 VT set |

So “~37 orphans” is **directionally correct**; off by two depending on how classes are counted (first `*Strategy` in file vs. multiple classes).

Full orphan list is printed by `tools/_verify_claude_deferred_items.py`.

## Summary

| # | Item | Verified | Next step |
|---|------|----------|-----------|
| 1 | Isotonic / bucket JSON | Not in tree | Paste MCP export → `alpha_engine/data/scanner_calibration_config.json`, set `enabled: true` |
| 2 | Luxalgo alts | **Missing file** | Add `vt_csv_edge_luxalgo_alts.py` + scanner registration |
| 3 | Ghost / dup closed picks | **1,202** quarantine candidate (28.1%) | Dry-run OK; `--apply` only with approval |
| 4 | VT orphans | **39** vs TIER1 | Register selectively; avoid bulk register without validation |
