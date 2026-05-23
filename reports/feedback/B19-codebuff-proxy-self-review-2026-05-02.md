# B19 Multi-AI Feedback — Codebuff proxy self-review (2026-05-02)

Item: **B19 — Pair-level exception carve-out for proven (strategy, symbol) pairs**

## A. Confirmed assumptions

1. **`alpha_engine/pair_exceptions.py` is the right new module location.**
   Mirrors the pattern of `alpha_engine/concept_registry.py` (B4, PR #566).
   Using `alpha_engine/` for pure-registry modules keeps `audit_trail/`
   clean for pipeline-critical code.

2. **`tools/derive_pair_exceptions.py` analysis tool is additive.** No new
   production caller needed — it's a weekly CLI tool, not an emitter.
   Wire-Up Rule doesn't apply to offline analysis tools (same exemption as
   `tools/forward_edge_audit.py`).

3. **Wilson 95% lower bound formula verified.** The B19 thresholds
   (Wilson lb ≥ 60%, n ≥ 20) are appropriate. For n=20 at 60% WR, the
   Wilson lb is ~38% — aggressive. B19 sets the bar at lb ≥ 60%, meaning
   the point estimate at n=20 needs to be ~84%+ before the lb clears 60%.
   This is correctly restrictive.

## B. Surfaced contradictions / blockers

1. **`tests/test_quality_gates.py` is the right existing test file** — it
   already covers `passes_active_gate` and `passes_smart_gate`. No need for
   a separate `tests/test_pair_exceptions.py`. The new tests should be in
   `test_quality_gates.py` to keep coverage co-located with the gate logic.
   **Delta**: consolidate into existing test file as B19 test class.

2. **`PAIR_EXCEPTION_CARVE_OUT_ENABLED` in CI**: workflow tests run with
   default env (flag OFF). Ensure the tests explicitly set the flag ON for
   carve-out tests, OFF for anti-regression. No workflow YAML change needed.

3. **Carve-out should NOT bypass catastrophic blocks.** Even with the flag
   ON, the carve-out must NOT bypass: BANNED trust tier (direct fraud risk),
   `is_strategy_blocked` (deliberately killed strategies), `BLOCKED_SYMBOLS`.
   The carve-out should only skip the R:R and strategy-level WR checks.

## C. Recommended deltas to the action-item doc

1. **Scope the carve-out carefully**: Only skip score-floor + R:R + forward-WR
   checks. Never skip trust-tier-BANNED, blocked-symbols, SCALP-mode (24.8% WR
   empirical kill).

2. **Add `exception_carve_out: True` field for dashboard visibility.** The
   /audit table should show these picks with a visual badge.

## D. Net verdict: **ready-to-ship**

Minor refinements to scope (don't bypass catastrophic blocks, don't skip SCALP
gate). Otherwise solid. Implement now with the stated constraints.
