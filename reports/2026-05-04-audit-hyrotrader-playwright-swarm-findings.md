# Audit + Hyrotrader Playwright Swarm Findings

Date: 2026-05-04  
Scope:
- `https://findtorontoevents.ca/audit`
- `https://findtorontoevents.ca/audit/hyrotrader`

## Objective

Create a thorough test and gap-analysis gameplan for audit surfaces, with per-asset-class quant checks and console/runtime validation.

## Swarm Conclusions

- The audit surfaces need both UI regression coverage and strict metric-contract checks.
- Important potential drift signals were identified in current payload interpretation:
  - class health badge and metric inconsistencies,
  - low/zero recent-closed activity that weakens confidence in near-term PF/WR claims.
- A quant-aware test layer is required beyond visual checks.

## Recommended Playwright Suite

- `tests/audit/audit.smoke.spec.ts`
- `tests/audit/audit.metric-contract.spec.ts`
- `tests/audit/audit.asset-class-integrity.spec.ts`
- `tests/audit/audit.hyrotrader.challenge-flow.spec.ts`
- `tests/audit/audit.console-errors.spec.ts`

## Required Assertions

- Zero critical runtime errors:
  - `pageerror`,
  - `console.error`,
  - failed key payload requests.
- Tab and section rendering:
  - no silent empty panes,
  - no broken drilldowns.
- Metric contract integrity:
  - displayed values match payload values,
  - no inconsistent status badges vs underlying metrics.

## Per-Asset-Class Quant Checklist

Apply to equity, commodity, bond, crypto, forex, ETF:

- PF floor validation
- WR floor validation
- MDD sanity checks
- minimum sample size gates
- walk-forward and forward-test consistency
- stale payload detection/freshness markers

## Missed Improvement Candidates (High-Level)

- Add explicit freshness timestamps on audit cards.
- Add payload-version hash to UI footer for debugging.
- Add stale-state visual warning when data age exceeds threshold.
- Add consistency tests for class status labels.
- Add strict "insufficient sample size" presentation policy.
- Add cross-check report for closed-pick vs active-pick metric leakage.
- Add guardrails for contradictory metric combinations.
- Add deterministic sorting and pagination checks for large tables.
- Add no-data fallback UX tests for each tab.
- Add periodic remote synthetic monitor coverage for `/audit` and `/audit/hyrotrader`.

## Kimi Artifact Cross-Reference Note

The swarm plan was generated as an executable framework and should be mapped section-by-section against your Kimi quant audit docs (`sec01`-`sec10`, structure, final markdown/docx artifacts).  
Where Kimi imposes stricter thresholds, those should override defaults in this plan.

## Risks and Mitigation

- Metric ambiguity from stale or partial payloads: enforce freshness + warning UX.
- Overconfidence from low sample sizes: hard display gating and test assertions.
- Contract drift over time: add CI contract tests directly against production payload schema.

## Outcome

The audit/hyrotrader testing strategy is ready for implementation with quant-specific pass/fail gates, not just UI snapshots.

