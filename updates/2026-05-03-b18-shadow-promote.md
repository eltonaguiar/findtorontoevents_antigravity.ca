# B18 — Shadow-Mode Auto-Promotion (2026-05-03)

## What shipped

Adds a default-OFF mechanism to break the chicken-and-egg trap for strategies that
have never had a pick close (and therefore can never accumulate the forward-WR
signal the HC gate requires to promote them).

**Default state: identical to production.** No behavior change when
`SHADOW_MODE_AUTO_PROMOTE_ENABLED=0` (the default).

## The problem it solves

Four strategies identified on 2026-04-30 had currently-emitting active_raw picks but
ZERO closed history:
- `enhanced_ml_A_xgboost` (27 raw), `regime_terminal` (10 raw, EQUITY),
- `smart_money_consensus` (4 raw, EQUITY), `super signal (strong) via ml_crypto_pred` (12 raw)

These strategies are permanently blocked because:
- HC gate requires `strat_fwd_wr` → needs closed picks → needs picks through gate
- Gate blocks picks → no closed picks → no `strat_fwd_wr` → HC blocks

The shadow-mode path breaks the trap:
1. For any strategy with zero closed history and ≥10 active_raw emits, promote ONE
   pick per cycle as "shadow active" (tagged `shadow_mode=True`).
2. Shadow picks are labeled with `shadow_size_multiplier: 0.1` (10% sizing hint).
3. After ≥10 closed shadow picks, recompute WR. Graduate if positive + Wilson lb ≥ 50%
   (this graduation step is a manual operator action, queued for B18-follow-up).
4. Global cap: max 5 concurrent shadow picks system-wide.

## Files changed

| File | Change |
|---|---|
| `audit_trail/quality_gates.py` | New `should_shadow_promote()` + constants |
| `audit_trail/dashboard_generator.py` | New `_apply_shadow_promotion()` + call in `generate()` |
| `tools/dashboard_hc_rules.py` | `passes_high_conviction_pick()`: shadow_mode=True → HC fail |
| `tests/test_shadow_promote.py` | 15 new tests (all pass) |

## Environment flags

```
SHADOW_MODE_AUTO_PROMOTE_ENABLED=0  # default → no behavior change
SHADOW_MODE_AUTO_PROMOTE_ENABLED=1  # activate shadow promotion
```

## Payload additions

When `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1`, the payload gains:

```json
{
  "shadow_probation": {
    "enabled": true,
    "shadow_picks": [{"strategy": "...", "symbol": "...", "direction": "LONG"}],
    "candidate_strategies": [{"strategy": "...", "raw_emit_count": 12, "closed_count": 0}]
  }
}
```

Each shadow-promoted pick carries:
- `shadow_mode: true`
- `shadow_size_multiplier: 0.1`
- `shadow_strategy_raw_emit_count: N`
- `_gate_passed: true`

## Wire-Up Rule

Opt-in sidecar. No production caller when flag is OFF. Flag flip is the wiring step.

**Wiring plan**: Flip `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1` in
`.github/workflows/alpha-engine-live.yml` after 14-day shadow observation shows
≥1 shadow strategy accumulating ≥10 closed picks. Graduate or demote each strategy
based on after-cost WR + Wilson lb (per B16/B17 tooling already on main).

## Pre-requisites

- B16 ✅ (`tools/forward_edge_audit.py` on main — provides after-cost stats used for
  graduation decisions)

## References

- `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §6.5 — B18 item definition
- `reports/feedback/B18-claude-sonnet-self-review-2026-05-03.md`
- `reports/feedback/B18-codebuff-proxy-self-review-2026-05-03.md`
