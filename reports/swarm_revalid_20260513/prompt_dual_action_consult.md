# Swarm consult: 2 in-flight action items

## Background

This session shipped 6 production exec-gate PRs (NS-C/FX1/NS-D/NS-F/VIX-gate/VIX-ETF) + EQUITY VIX+YC combined regime SUPER-BREAKTHROUGH backtest (PF 5.87 / Sharpe 2.29 / MDD 7.2%). 2 in-flight items need design review before action.

## Item 1: Wire YC overlay into vix_regime_gate.py

**Current state** (post PR #958 + #959):
- `audit_trail/vix_regime_gate.py` covers EQUITY + ETF with VIX threshold gate
- `VIX_REGIME_GATE_ENABLED=0` default OFF
- Cached fetch of ^VIX via yfinance (4h TTL)
- `should_reject_equity_pick()` reads pick['asset_class'] + checks VIX > threshold

**Proposed extension** (per breakthrough report):
- Add `_fetch_yc_now()` returning (^TNX - ^FVX) spread
- Add `get_cached_yc()` with same 4h TTL
- Add `is_yc_below_threshold()` env-configurable threshold (default 0.0)
- Modify `should_reject_equity_pick()`: when env `YC_REGIME_GATE_ENABLED=1`, also check YC; reject if EITHER VIX bad OR YC inverted
- Backtest evidence: VIX<22 AND YC>0 combined = PF 4.98 / Sharpe 2.08 / MDD 16.8% (vs VIX<22-only PF 4.55 / Sharpe 1.98 / MDD 16.8%). Combined adds PF/Sharpe headroom without changing MDD.

**Risks:**
- Two yfinance fetches now in hot path (cached, but still)
- New env adds operator complexity
- 4h cache may be stale if YC inverts intraday
- Function still named `should_reject_equity_pick` — adding YC adds responsibility scope

## Item 2: NS-A multi_asset_cot DB-verify

**Background:** `multi_asset_cot` shows system PF 21.86 / WR 94.1% on 102 closed (per dashboard payload). AA-4 blend backtest used dashboard numbers + flagged as fabrication-risk-pattern (similar to kimi_signal_tracking PF reversal earlier session). NS-A workflow `ab_analysis.yml` keeps cancelling on concurrency lock. Operator-deferred for direct DB query against `ejaguiar1_stocks.picks` joined to outcomes.

**Current options:**
A. Manual SQL via Bash with `--password "$DB_PASS_STOCKS"` env (one-time verify)
B. Fix `ab_analysis.yml` concurrency lock — unblock cron
C. New standalone verifier script `tools/verify_multi_asset_cot_db.py` that ignores existing cron
D. Wait for operator NS-A cycle completion

Goal: verify PF 21.86 against raw DB before any real-money sizing on this strategy.

## Question to engines

For EACH of the 2 items, return strict JSON ONLY:

```json
{
  "item_1_vix_yc_wire_up": {
    "verdict": "PROCEED | HOLD | REVISE_DESIGN",
    "merge_safety": "<safe | risky | needs_shadow_first>",
    "function_name_concern": "<rename_required | keep_with_docstring | add_new_function>",
    "default_state": "OFF | ON_AT_LOW_THRESHOLD",
    "biggest_risk": "<one sentence>",
    "concrete_changes_recommended": ["<list of file/line/change>"]
  },
  "item_2_ns_a_db_verify": {
    "recommended_option": "A | B | C | D",
    "rationale": "<1-2 sentences>",
    "expected_outcome": "<verifies edge | falsifies edge | hits stale data>",
    "blocking_for_real_money_sizing": "<yes | no | partial>"
  },
  "priority_order": ["item_1_first | item_2_first | parallel"],
  "single_most_important_consideration_across_both": "<one sentence>"
}
```

## Constraints

- Per CLAUDE.md Wire-Up Rule, must have production caller OR explicit opt-in sidecar
- Item 1 builds on PR #958/#959 pattern (well-established)
- Item 2 blocks real-money sizing on multi_asset_cot ($PF 21.86 too good to trust without DB verify)
- Reversibility: prefer env-flag flips over architectural changes
