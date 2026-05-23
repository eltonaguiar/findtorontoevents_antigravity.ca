# Swarm review v2: NS-C UTC filter — revised to ADD pattern (reject 6, 8, 9)

## Context

Following 4/4-engine swarm v1 review on the bare REPLACE patch (8,9 → 6 only):
- 1 MERGE (groq), 3 HOLD (xai, deepseek, cerebras)
- 2 REPLACE / 2 ADD split on scope
- Universal confounder: 6 UTC = Asia-open, possible weekend/liquidity effect

**Revised patch** keeps existing (8,9) blocks AND adds 6 UTC:
```python
# was: _hr in (8, 9)
# now: _hr in (6, 8, 9)
```

This addresses both:
1. New backtest evidence: 6 UTC = 23.1% WR / PF 0.06 on BTC
2. Original memory evidence: 8-9 UTC death zone for full CRYPTO universe (not falsified)

13/13 unit tests pass on revised branch.

## Question to engines

Re-review the conservative ADD patch. Should this MERGE now? Strict JSON:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_CAVEATS | REQUEST_CHANGES | REJECT",
  "merge_decision": "MERGE | HOLD | REJECT",
  "remaining_concerns": ["<list>"],
  "production_safety_assessment": "safe | risky | needs_shadow_mode_first",
  "estimated_pick_rejection_volume_pct_change": "<+/-N%>",
  "rollback_complexity": "<one_line_revert | multi_step | hard>"
}
```

## Constraints

- Bias toward shipping the conservative patch since 3 hours of rejection is strictly more conservative than 2 hours
- Net effect: same pre-existing 8,9 behavior PLUS new 6 UTC rejection
- Volume impact: from 8.3% of CRYPTO entries (2/24 hrs) → 12.5% (3/24)
