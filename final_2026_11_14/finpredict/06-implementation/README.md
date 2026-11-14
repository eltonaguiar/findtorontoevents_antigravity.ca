# 06 — Implementation delivered

Branch `fix/audit-p0-truth` (pushed to `origin`, based on `origin/main`). Three self-contained, low-risk P0 fixes from the master plan, all `py_compile`-clean and functionally smoke-tested.

| # | Fix | File | Change |
|---|---|---|---|
| P0-1 | FX direction `KeyError: 'LONG'` (93 failed runs/24h) | `alpha_engine/scanner.py:2937` | normalize `LONG→BUY`, `SHORT→SELL` before bucketing |
| P0-2 | `summary_picks` WR > 100% (7 classes) | `tools/sync_summary_picks_json.py:63-65,165` | wins/losses strict subset of `resolved` + `min(wins,resolved)` clamp |
| P0-5 | `None → 0.0` entry coercion (phantom `entry=0.0`) | `alpha_engine/prediction_market_consensus.py:589-591` | removed `or 0`; `entry_price` stays `None`, status degrades to `SIGNAL` |

Documentation: `updates/2026-11-14-p0-truth-fixes.md`.

### Not yet implemented (recommended next, in order)

1. P0-3/P0-4 — workflow YAML (Python 3.14 `update-environment:false` in 197 files; audit-dashboard cron vs 97-min runtime).
2. P0-6+P0-7 — quote-provenance contract + render (must ship together).
3. P0-8 — honesty metrics (n + Wilson CI + excluded counts).
4. The PnL-unit mix bug (`dashboard_generator.py:8065-8072` heuristic).

Also on `origin/main` (by peers, needs coordinator review): `fix/audit-js-syntax-and-deploy-guard` (JS parse fix + pre-FTP `node --check` guard — correct, urgent), `d8c8dd25581` (ML leakage masking ON-by-default — unreviewed production change).
