# Proposal — super_signals "strong consensus" sub-label penalty

**For peer (`0f7ecsyk`) — DO NOT execute. Flag-only proposal.**

**Source:** Hidden-edge swarm (cycle 2, `reports/hidden_edge_scan_2026-05-13.md`):
> "super_signals strategy label `strong consensus (alpha_engine, ml_crypto_pred)` accounts for **47/49** noise picks from super_signals (whole system is +1.07% — the top-score slice is uniquely toxic)."

## Current state (verified)

- `audit_trail/quality_gates.py:4168` — `"super_signals": 8, # 55.7% WR, +0.72% avg PnL, n=122`
- The aggregate gets +8 score. Sub-label-aware penalty does not exist.
- One specific sub-strategy (`"strong consensus (alpha_engine, ml_crypto_pred)"`) supplies 96% (47/49) of the noise cohort. Other super_signals strategy variants likely net-positive.

## Proposed change

Add a per-(source_system, strategy_label) override map. Apply -15pt to super_signals when strategy contains "strong consensus":

```python
# audit_trail/quality_gates.py (NEW)
# Source-system × strategy-label overrides applied AFTER base SOURCE_SYSTEM_SCORES.
# Reason: hidden_edge_scan_2026-05-13.md found one toxic sub-label dragging the
# whole source-system score.
_STRATEGY_LABEL_OVERRIDES: dict[tuple[str, str], int] = {
    # super_signals "strong consensus" — 47/49 noise picks at top score band.
    # Base score 8 - 15 = -7 effective.
    ("super_signals", "strong consensus (alpha_engine, ml_crypto_pred)"): -15,
}

def apply_strategy_label_override(base_score: int, source_system: str, strategy: str) -> int:
    """Apply per-strategy-label override if present. Else return base."""
    for (sys_pattern, strat_pattern), delta in _STRATEGY_LABEL_OVERRIDES.items():
        if sys_pattern == source_system and strat_pattern in strategy:
            return base_score + delta
    return base_score
```

Wire-up: caller computing pick score after `SOURCE_SYSTEM_SCORES[source_system]` lookup runs the override. Find caller(s) — grep for `SOURCE_SYSTEM_SCORES[` returns expected sites.

## Acceptance gate

Per CLAUDE.md tier targets + per the swarm finding:
- Shadow-mode 14 days (log effective scores to `audit_dashboard/data/strategy_label_override_log.json`)
- Confirm noise cohort drops from 47/49 → <10/49 for super_signals
- If confirmed, promote to live scoring

## Effort

- Code: 1h (5 LOC + 1 unit test)
- Shadow log: 30min
- Acceptance gate check at +14d: 30min

## Risk

- LOW. Score change is additive penalty. If override fires on wrong pick, worst case is -7 vs +8 = 15pt reduction in pick score → pick demoted, not blocked.
- The strategy_label string match is a soft contains-check. Brittle if peer changes naming. Worth pinning the literal in a constant.

## Cross-link

Tied to:
- `feedback_disclosure_is_not_enforcement.md` candidate (PCG-5 spec): pattern of "we measured the noise but didn't penalize it"
- `feedback_confidence_is_not_edge.md`: same root cause — high-score band ≠ high-PnL band
- `feedback_use_claude_peers_not_redis_bus.md`: this proposal is being routed via reports/ + claude-peers, not Redis bus (CLAUDE.md preference)

## Decision needed

1. **Approve** the override pattern AS-IS (1-pair example) → I write the code + test in a follow-up PR, peer reviews
2. **Approve with tweak** — different score delta, different label match → tell me the values
3. **Reject** — keep base SOURCE_SYSTEM_SCORES flat; address via a different mechanism
