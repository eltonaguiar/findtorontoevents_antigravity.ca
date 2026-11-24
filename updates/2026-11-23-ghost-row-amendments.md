# Block 55 — ghost-row provenance: closing three exposures

**Date:** 2026-11-23 · **Base:** `origin/main` @ `8f296213f06ea533d9c70951eb59e21851708816` (non-shallow clone; `is-shallow-repository` = `false`)

Amends [`CONTEST/ROUND_01_2026-11-23/GHOST_ROW_PROVENANCE.md`](../CONTEST/ROUND_01_2026-11-23/GHOST_ROW_PROVENANCE.md) (Block 54, PR #1106). Documentation only: no code, ledger, result, or label changed. The programme tally is not restated.

## What was open, and what was found

| Exposure | Block 54 | Block 55 result |
|---|---|---|
| `reports/edge_per_class.json` "consumed by nothing that gates" | assertion | **Proved.** Untracked (`cat-file -e` → 128, not gitignored), no workflow runs its producers, and no code reads the JSON. Two writers, zero readers, zero gating consumers |
| Is a ghost cohort in the `cot_lag_corrector` strategy? | `UNMEASURED` | **Empty by static set comparison.** Ghosts = `meta_strategy` / MEMECOIN; corrector = `multi_asset_cot` / COMMODITY-scoped gate. A DB-verified `source_table` cross-check remains outstanding |
| Live ghost recount | impossible (creds fail) | **Stated as a limitation.** 22,947 is `db_health.json` snapshot 2026-11-23T18:43:46Z; error direction unquantified |

## Why the verdict is unchanged

The `edge_extractor` path cannot move a verdict, promotion, `money_ready` state, CI check, or allocation: its output is untracked, unscheduled, and read by nothing. It does scan `bt_backtest_trades` raw with no ghost filter (`tools/edge_extractor.py:46`) and writes a human-facing Markdown of per-class WR/PF/Sharpe (`tools/edge_extractor.py:177`) that over ghost-inflated rows is not a performance estimate — a presentation hazard, not a gate.

The `cot_lag_corrector` path *is* a gate (`audit_trail/quality_gates.py:8425-8434`, COMMODITY-only, `shadow` by default), but its strategy/source (`multi_asset_cot`) is disjoint from every ghost cohort's (`meta_strategy`), and its asset-class scope (COMMODITY) is disjoint from the cohorts' (MEMECOIN).

## Evidence index (each path verified to exist on `origin/main`)

- [`tools/edge_extractor.py:46`](../tools/edge_extractor.py) raw query · `:175` JSON writer · `:177` Markdown writer
- [`tools/edge_scanner.py:76`](../tools/edge_scanner.py) second JSON writer (different table: `backtest_results`)
- [`tools/hc_health_monitor.py:49`](../tools/hc_health_monitor.py) / [`tools/_hc_noncrypto_diagnostic.py:33`](../tools/_hc_noncrypto_diagnostic.py) same-named helper, reads dashboard picks not the JSON
- [`tools/cot_lag_corrector.py:124`](../tools/cot_lag_corrector.py) primary query · `:80` `MULTI_ASSET_COT_SOURCE`
- [`audit_trail/quality_gates.py:8422`](../audit_trail/quality_gates.py) mode · `:8425` COMMODITY scope · `:8429-8434` reject
- [`audit_dashboard/data/db_health.json:2`](../audit_dashboard/data/db_health.json) `generated_at` · `:84` `total_ghost_rows: 22947`
- [`.github/workflows/audit-dashboard.yml:264`](../.github/workflows/audit-dashboard.yml) hourly refresh of `db_health.json`

## Working tree

The shared tree (`push/phase2-round-2026-11-22`) was measured read-only: `CONTEST/` clean and absent on disk, branch unchanged. All writes were made inside the `/tmp` clone.
