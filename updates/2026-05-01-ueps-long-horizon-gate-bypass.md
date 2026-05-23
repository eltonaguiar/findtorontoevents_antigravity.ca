# 2026-05-01 — UEPS long-horizon active-gate bypass (default-OFF)

## Summary

30 UEPS picks (long-horizon EQUITY value, magic_formula × piotroski × acquirers,
TF=POSITION) sit in `picks.active_raw` but 0 reach `picks.active`. Empirical
gate-instrumentation showed three short-term-calibrated filters reject them:

| Cause | Count | % |
|---|---|---|
| `non-crypto raw score below active-display floor` (score < 55) | 19 | 63% |
| `BLOCKED_SYMBOLS` (data-feed blacklist for short-term) | 6 | 20% |
| `elite_grade=D hard-blocked` | 4 | 13% |
| `closed status=SL_HIT` (stale leak — separate bug) | 1 | 3% |

Trust-score (3) and forward-WR floor were NOT rejecters — both correctly pass.

## Fix

Add helper `_ueps_long_horizon_bypass_active(pick)` in
`audit_trail/quality_gates.py`. When `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=1`
AND `source_system=ueps` AND `trade_timeframe=POSITION`, four
short-term-calibrated rejecters are skipped:

1. `BLOCKED_SYMBOLS` — short-term data-feed issues don't apply at 3y horizon
2. `elite_grade=D` — calibrated for short-term momentum (grade F still blocks)
3. Non-crypto raw-score 55 floor
4. Universal raw-score 40 floor

All real-safety gates remain active: trust_score, status (SL_HIT/closed),
wf_verdict, forward_wr floor, EXEMPT_FROM_SAFETY_GATES, jpy_cross_buy_kill,
healthcare_long_momentum_blacklist, entry_price sanity, mutation filter.

**Default-OFF**. Operator flips on after 14-day shadow review per CLAUDE.md.

## Empirical verification

```
Flag OFF:  0/30 UEPS pass; non-UEPS control 55/177
Flag ON : 29/30 UEPS pass; non-UEPS control 55/177  (GOOGL correctly blocked
                                                     for status=SL_HIT)
```

Non-UEPS counts identical across both flag states → no leak.

## Tests

`tests/test_ueps_long_horizon_gate_bypass.py` — 11 tests, all passing:

1. Default-OFF safety (current behavior preserved)
2. Flag ON bypasses raw-score floor for UEPS POSITION
3. Flag ON bypasses BLOCKED_SYMBOLS for UEPS only (non-UEPS NVDA still blocked)
4. Flag ON bypasses elite_grade D (grade F still blocks)
5. Non-UEPS sources unaffected by the flag
6. Status-closed real-safety gate still blocks UEPS under bypass
7. **Forward-WR floor still enforced under bypass** (final-reviewer addition)
8. Bypass only applies to `trade_timeframe=POSITION` (intraday UEPS still gated)
9-11. Helper-function invariants (flag unset, all-conditions-met, non-ueps)

## Risk: LOW (default-OFF)

No production behavior change on merge. Code path is exercised only when
operator explicitly sets the env flag after monitoring 14d shadow.

## Rollback

```
unset UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED  # or set to 0
```

No PR revert needed.

## References

- `reports/UEPS_GATE_FIX_PLAN_2026_05_01.md` — full plan + 3-AI consensus
- `reports/feedback/deepseek-ueps.md` — recommended B
- `reports/feedback/cerebras-qwen-ueps.md` — recommended B
- `reports/feedback/xai-grok-ueps.md` — recommended B
- `reports/feedback/deepseek-ueps-plan-FINAL.md` — SHIP-WITH-MINOR-EDITS verdict
- `audit_trail/quality_gates.py:1523-1545` — `_ueps_long_horizon_bypass_active`
- `audit_trail/quality_gates.py:3905-3909` — BLOCKED_SYMBOLS guard
- `audit_trail/quality_gates.py:4090-4099` — elite_grade D guard
- `audit_trail/quality_gates.py:4413-4426` — non-crypto raw-score floor guard
- `audit_trail/quality_gates.py:4582-4587` — universal score-40 floor guard
