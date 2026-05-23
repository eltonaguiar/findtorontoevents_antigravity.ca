# Session BZ Review — 2026-05-17

## Context
Continuation of PATH_TO_PROVEN_EDGE. This session built M-107 (hypothesis pre-registration gate),
investigated the futures_momentum anti-signal hypothesis, fixed stale MASTER_ACTION_PLAN checkboxes,
and performed a dropchat-multipc handoff (gateway unreachable, fallback to events.jsonl + CHATBIBLE_FAILURE.MD).

## Session deliverables

### 1. reports/hypothesis_registry.json (M-107)
Pre-registration gate. 5 hypotheses registered before testing:
- H-001: COT positioning (LIVE_TESTING) — WR=78.4% 2 windows, needs 3rd window
- H-002: EQUITY PEAD (PENDING_IMPLEMENTATION)
- H-003: ETF 12-1 momentum (PENDING_IMPLEMENTATION)
- H-004: COMMODITY inventory-surprise roll yield (PENDING_IMPLEMENTATION)
- H-005: futures_momentum inversion — TESTED, REFUTED, ARCHIVED

### 2. futures_momentum anti-signal investigation (H-005 REFUTED)
DeepSeek suggested 2% WR might be an inverted signal. Investigation result:
- LONG picks: avg_pnl=-0.0274, WR=2.0% (n=148)
- SHORT picks: avg_pnl=-0.0276, WR=1.9% (n=54)
- Conclusion: BOTH directions fail equally. Not an inversion bug. Symmetrically broken.
- Action required: operator must approve BLOCKED_ASSET_STRATEGY_PAIRS entry
- H-005 archived to archived_failures — not re-testable on same sample

### 3. MASTER_ACTION_PLAN stale checkbox fixes
- PR #1027: [ ] → [x] (CLOSED — no review needed)
- P2 PR #1187: [ ] → [x] (OPEN as of 2026-05-17)

### 4. dropchat-multipc
Gateway 192.168.2.32:8788 unreachable. CHATBIBLE_FAILURE.MD appended, events.jsonl fallback written.

## Review questions

1. Is the hypothesis_registry.json structure correct for the M-107 pre-registration requirement?
2. Is the futures_momentum symmetry analysis (LONG WR=2.0% ≈ SHORT WR=1.9%) sufficient to reject the inversion hypothesis?
3. Any concerns about the H-001 COT edge (2 windows, needs 3rd) — should it stay LIVE_TESTING or be downgraded to WATCH?
4. Is the dropchat-multipc fallback (events.jsonl + CHATBIBLE_FAILURE.MD) handled correctly?

## Pending operator decisions (CANNOT implement without user approval)
- Block futures_momentum (WR=2%, n=202) — now confirmed NOT an anti-signal, truly broken
- Reduce quan_engine_scalp volume share (n=5293, WR=29.9%)
- Block cta_replicator COMMODITY (WR=12%, n=83)

## Commits this session
- ff2ed9dac1: feat(edge): M-107 hypothesis pre-registration registry + futures_momentum inversion REFUTED
