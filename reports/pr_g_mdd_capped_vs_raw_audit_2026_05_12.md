# PR-G Audit — MDD Capped vs Raw PnL

**Date:** 2026-05-12
**Author:** mb2v7tau (this peer session)
**Status:** Investigation only — implementation deferred to peer `jdyl7t5f` (currently on /audit DB Health) per coordination

## Findings

5 MDD compute sites in `audit_trail/dashboard_generator.py`:

| File:line | Function | PnL source | Classification |
|---|---|---|---|
| `audit_trail/dashboard_generator.py:9336-9348` | System-level MDD | Clamped at read (`max(-100, min(200, float(p)))` at L9342) | **SAFE** |
| `audit_trail/dashboard_generator.py:10801-10809` | Strategy-level MDD (legacy) | RAW `pnl_pct` | **VULNERABLE** |
| `audit_trail/dashboard_generator.py:10816-10824` | (source_system, strategy) MDD | RAW `pnl_pct` | **VULNERABLE** |
| `audit_trail/dashboard_generator.py:11332-11340` | Forward validation MDD | RAW `pnl_pct` | **VULNERABLE** |
| `audit_trail/dashboard_generator.py:14241-14249` | `recent_max_dd` (last 10 trades) | RAW `pnl_pct` | **VULNERABLE** |

Workflow-side MDD calcs:
- `.github/workflows/alpha-engine-live.yml:594-599` — RAW pnl_pct cumsum
- `.github/workflows/claude-gainer-tracker.yml:266-271` — RAW pnl_pct cumsum
- `.github/workflows/cross-aggregator.yml:161` — stub only

## Critical contract gaps

- **`readiness.by_class` payload key DOES NOT EXIST** in current `dashboard_data.json` (verified at 2026-05-12T04:06Z). Codex master plan calls for it; not yet implemented.
- **`capped_vs_raw_pnl_gap` field DOES NOT EXIST** anywhere in codebase (grep returns 0 hits).
- `system_clean_metrics` already has per-strategy `total_pnl_raw` + `total_pnl_capped`, but **no class rollup**.

## Risk summary

- **System-level MDD is safe** (clamped at read). This is what gates Kimi's 680% anomaly claim — it CAN'T render that on /audit.
- **Strategy-level + forward-validation + recent MDDs are vulnerable** — ~1700 pre-resolver-v2 outlier rows may still inflate these.
- **Workflow engines use raw cumsum** — risk of bad position-sizing signals downstream.

## Recommended implementation (deferred to peer)

1. Extract the L9342 clamp into a helper `clamp_pnl_pct(p) -> float` in `audit_trail/dashboard_generator.py`.
2. Apply at all 4 vulnerable sites (10758-area reads).
3. Apply at workflow sites.
4. Add `capped_vs_raw_pnl_gap` per-class:
   - For each class, compute `sum(capped_pnl)` vs `sum(raw_pnl)`.
   - Surface gap in `readiness.by_class.<CLASS>.capped_vs_raw_pnl_gap`.
   - Threshold alert: gap > 5x flagged as "outlier-inflated" in payload.
5. New payload field surfaces in `audit_dashboard/template.html` MAJOR GOAL or DB Health panel.

## Coordination

Peer `jdyl7t5f` (per peer summary 2026-05-12T03:31Z) is "Fixing /audit DB Health red metrics: resolver dead-cycle + workflow cancellation root cause + 655k ghost row quarantine sweep." Their work touches the same MDD/PnL surface. Handing off this investigation rather than racing.

## References

- Kimi flag: 680% MDD anomaly (master plan EQUITY action #2)
- Codex payload contract: `readiness.by_class.<CLASS>.capped_vs_raw_pnl_gap` (master plan P1 cluster #1)
- Memory: `feedback_noncrypto_resolver_live_close_bug` — ~1700 pre-fix outliers
- Swarm consensus (5-model local panel): APPROVE 3/1/0, risk avg 4.5/10
