# Audit dashboard: strategy tooltip descriptions for all active strategies

## What we did

Cross-checked **44 unique** `strategy` values from `audit_dashboard/data/dashboard_data.json` active picks against `_STRATEGY_DESCRIPTIONS` in `audit_dashboard/template.html` (same block in `index.html`).

**Tool:** `python tools/audit_strategy_desc_coverage.py` — classifies each strategy as `map` (static description), `super_narrative`, or `missing`.

## Additions

Seventeen entries (plus fuzzy keys `ml_enhanced`, `enhanced_ml`, `pm_whale`) so every current active strategy either:

- Matches a **specific** description, or
- **Fuzzy-matches** a family key (e.g. all `ml_enhanced_*` via key `ml_enhanced`), or
- Uses existing **super-signal** narrative in `_strategyTooltipNarrative`.

Blurbs were aligned to **real** module/registry context (`prediction_market_consensus.py`, `non_crypto_consensus.py`, `contrarian_consensus.py`, `tsmom_strategy.py`, `kalshi_signals.py`, `genome/dna_*.py`, `regime_terminal`, KIMI strategy names, etc.) — not invented performance numbers.

## Playwright

- **`tests/audit_remote_warn_and_desc.spec.ts`** — opens live `https://findtorontoevents.ca/audit/`, activates **Active Picks**, counts **`.track-strat-warn-icon`**, logs sample tooltip titles, asserts no critical JS errors.
- Registered in **`playwright.config.ts`** `testMatch`.
- Run: `npx playwright test "tests/audit_remote_warn_and_desc.spec.ts" --project="Desktop Chrome"` (use **forward slashes** on Windows so the config `testMatch` resolves).

**Live run (2026-04-16):** ~**147** TRACK warning icons on the table (strategy-wide vs symbol-specific — expected when `sym_track_total < 3`). Many tooltips still showed **n=0** symbol ledger lines until the **dashboard generator** redeploys **`00e419f4d4`** super-signal `source_system` ledger fix into `dashboard_data.json`.

## Strategy column tooltip (leaderboard hit)

When a leaderboard row exists, the tooltip previously showed only BT/FWD metrics. It now appends the same **description blurb** as the empty branch (via `_strategyTooltipNarrative`, skipped when the text would only repeat the humanized strategy name).

## Deploy

`python tools/deploy_to_ftp.py --audit-only` after `acorn` parse check on edited HTML.
