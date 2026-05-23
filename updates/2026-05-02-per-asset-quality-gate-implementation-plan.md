# Per-Asset-Class Audit Quality Gate Plan (Evidence-Backed)

## Why this document exists
This repo needs a production-ready implementation plan for per-asset-class quality gating on `findtorontoevents.ca/audit`, with CI enforcement and UI compatibility.  
This document is the PR artifact that captures:

1. what will change,
2. why it should change,
3. evidence from current payload data,
4. rollout and rollback safety.

## Scope
Planned implementation targets:

- `audit_trail/quality_gates.py`
- `audit_trail/dashboard_generator.py`
- `audit_dashboard/template.html`
- `audit_trail/quality_monitor.py`
- `.github/workflows/audit-dashboard.yml`

Asset classes in scope:

- `CRYPTO`, `EQUITY`, `FOREX`, `COMMODITY`, `FUTURES`, `BOND`, `ETF`

## Baseline evidence (captured from current payload)
Data source used:

- `audit_dashboard/data/dashboard_data.json`

Metrics extracted from current `picks.active` / `picks.smart`:

| Asset Class | Active | Smart | Score P50 | Score P75 | FWR P50 | FWR P75 | Corrupted |
|---|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 10 | 0 | 68.000 | 96.500 | 0.642 | 0.708 | 0 |
| EQUITY | 5 | 0 | 40.000 | 40.000 | 0.551 | 0.551 | 0 |
| FOREX | 3 | 0 | 40.000 | 50.000 | 0.459 | 0.502 | 0 |
| COMMODITY | 0 | 0 | NA | NA | NA | NA | 0 |
| FUTURES | 0 | 0 | NA | NA | NA | NA | 0 |
| BOND | 0 | 0 | NA | NA | NA | NA | 0 |
| ETF | 0 | 0 | NA | NA | NA | NA | 0 |

Interpretation:

- Current smart pick coverage is zero across all classes in this snapshot.
- Only three classes currently have active-volume evidence (`CRYPTO`, `EQUITY`, `FOREX`).
- Four classes are sparse/empty and must be handled with non-starving policy (`warn` mode first, hard gating later).

## What changes are proposed (and why)

### 1) Backend class-specific smart gate
Add class-aware thresholds in `passes_smart_gate()`.

Why:

- A single global floor causes either over-rejection (starvation) or under-filtering (quality leakage).
- Current per-class distributions differ materially.

### 2) Keep active gate permissive with hard safety blocks
`passes_active_gate()` remains conservative only for true safety failures:

- missing core fields,
- corrupted rows,
- impossible trade geometry,
- blocked symbol/strategy hard rules.

Why:

- Active feed should not be silently starved by smart-level quality logic.

### 3) Reduce over-stacking penalties
Move from additive correlated penalties to capped bucket logic.

Why:

- Correlated penalties can collapse viable rows to near-zero scores and erase class diversity.

### 4) Payload segmentation for UI and CI
Add:

- `assetClassSummary`
- `smartPicksByAsset`

Why:

- UI needs class-level badges/tooltips.
- CI needs explicit class-level regression checks.

### 5) CI quality gate with staged strictness
Add `warn` then `hard` mode enforcement in `audit-dashboard.yml`.

Why:

- Prevent accidental production regressions.
- Avoid blocking deployments during threshold tuning for low-volume classes.

## Initial threshold policy (data-grounded and starvation-aware)
These are rollout starting points from current observed distributions, not final fixed values:

| Class | Min score (smart) | Min forward WR | Notes |
|---|---:|---:|---|
| CRYPTO | 65 | 0.62 | based near current score P50 and WR lower-middle band |
| EQUITY | 40 | 0.50 | near observed center to avoid starvation |
| FOREX | 40 | 0.46 | aligned to current observed median/min envelope |
| COMMODITY | 40 (warn) | 0.50 (warn) | sparse class; promote to hard mode only after volume |
| FUTURES | 45 (warn) | 0.50 (warn) | sparse class |
| BOND | 35 (warn) | 0.50 (warn) | sparse class |
| ETF | 40 (warn) | 0.50 (warn) | sparse class |

## CI enforcement policy
Explicit, auditable checks:

- if `activeCount >= N` (recommended `N=10`) and `smartCount == 0` => violation
- if class `avgScore` or `forwardWR` falls below floor => violation
- `QUALITY_GATE_MODE=warn` => annotate warnings and pass
- `QUALITY_GATE_MODE=hard` => fail workflow

## UI compatibility guarantee
Planned UI behavior in `template.html`:

- render class quality badges from `assetClassSummary`
- keep existing filters functional (`f-asset`, score filters, date filters)
- degrade gracefully for missing classes (no JS crashes)

## Rollout plan
1. Add baseline extractor and snapshot report.
2. Implement class-aware gate logic and penalty-bucket cap.
3. Emit payload class summary and segmented smart picks.
4. Add UI badges/tooltips from payload summary.
5. Turn CI gate on in `warn` mode, monitor, then switch to `hard`.

## Rollback plan
Fast rollback knobs:

- revert floor constants in one config map,
- set `QUALITY_GATE_MODE=warn` (or temporary off),
- keep payload schema backward compatible so UI does not break if checks are relaxed.

## Acceptance checklist
- [ ] All 7 classes emitted in payload summary (even when zero-volume)
- [ ] Smart picks segmented by class and filterable in UI
- [ ] No corrupted rows in active/smart outputs
- [ ] CI catches class-level regressions at configured floor
- [ ] Existing dashboard filters continue to work

