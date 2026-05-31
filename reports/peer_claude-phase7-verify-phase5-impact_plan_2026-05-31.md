# Phase-7 — Verify Phase-5 Impact (PLAN)

Date: 2026-05-31. Goal: confirm PR #182 (RETIRE cta_golden_cross_200 + prediction_market_consensus) actually changed published `/audit/data/` numbers.

## Scope
1. Pull live `money_ready_verdict.json` + `pf_registry.json`.
2. Confirm whether the two suspect strategies still appear in `by_asset_class_strategy_policy_clean_net`.
3. Compare generated_utc vs PR #182 mergedAt (05:47Z).
4. Diff class-level CRYPTO + COMMODITY PF/WR vs Phase-2 baseline.
5. Check PR #183 follow-up (at_strategy_stats schema mismatch) — was a code fix landed?
6. Identify operator-actionable next steps.

## Method
- `curl https://findtorontoevents.ca/audit/data/<file>.json | jq …`
- `gh pr view 182,183` for merge timestamps + file lists.
- `gh run list --workflow=…` for refresh status.
- `grep` quality_gates.py / build_pf_registry.py / money_ready_verdict.py to confirm wiring.
