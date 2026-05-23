# B17 — HC Button Audit + After-Cost Gating
## Multi-AI Review: Claude Sonnet 4.6 (self-review via §5 protocol)
**Date:** 2026-05-02

---

## A. Confirmed Assumptions

1. **File paths are correct.** `tools/dashboard_hc_rules.py` (lines 1-end) and `tools/hc_gates_python.py` (lines 1-end) both contain `passes_high_conviction_pick()` as the main HC predicate. The hook point in `dashboard_generator.py` is `_normalize_pick()` around line 6808 (after `assign_concept_fields()`). Confirmed by reading the source.

2. **B16 artifact schema confirmed.** `tools/forward_edge_audit.py` produces `reports/forward_edge_audit_YYYY-MM-DD.json` with keys: `['generated_at', 'date', 'caveat', 'wiring_status', 'version', 'survivors', 'strategies', 'summary']`. Each entry in `strategies` has: `strategy`, `asset_class`, `after_cost_mean_pnl_pct`, `wilson_lb_wr_pct`, `both_survive`, and 15 other fields. The stamping fields `after_cost_net_per_trade` (= `after_cost_mean_pnl_pct`), `wilson_lb_wr` (= `wilson_lb_wr_pct`), `is_ac_survivor` (= `both_survive`) are directly available.

3. **Wire-Up Rule satisfied.** `stamp_after_cost_fields()` is called from `_normalize_pick()` in the production path. `passes_hc_after_cost()` is an opt-in shadow gate behind `HC_AFTER_COST_GATE_ENABLED=1` — satisfies CLAUDE.md sidecar pattern.

4. **B16 prereq is met.** `tools/forward_edge_audit.py` exists on main and produces valid output (verified: 5 survivors identified, 248 strategies in index, artifact at `reports/forward_edge_audit_2026-05-02.json`).

5. **HC gate parity note.** PR #648 (merged 2026-05-02) already fixed Gate 7b parity. `passes_hc_after_cost()` is an ADDITIVE shadow gate, not a replacement, so parity is preserved.

---

## B. Surfaced Contradictions / Blockers

1. **Staleness guard essential.** `forward_edge_audit_*.json` is dated. If the artifact is >25 hours old, null-stamp rather than use stale rates. The `generated_at` field in the JSON must be checked. Implementation must not stamp fields from a 30-day-old artifact.

2. **Index key collision.** Multiple strategies may have the same name across different asset classes (e.g. `rs-breakout-scout` appears in EQUITY with WR 77.8% and potentially in CRYPTO with different stats). The index must key by `(strategy_lower, asset_class_upper)` with fallback to `strategy_lower` only.

3. **Null tolerance.** Some active picks have `strategy=None` or blank. The stamp function must never raise; null strategy → null fields (no filtering).

4. **Shadow gate passthrough.** When `HC_AFTER_COST_GATE_ENABLED=0` (default), `passes_hc_after_cost()` must return `True` for all picks — do not accidentally block picks when the flag is off.

5. **Avoid breaking closed-pick normalization.** `_normalize_pick()` is called for BOTH active AND closed picks. Stamping after-cost fields on closed picks is harmless (they already have real PnL) but the index lookup must not slow down the generator meaningfully (49 strategies × 3500 picks = 171,500 dict lookups — fine with a pre-built dict).

---

## C. Recommended Deltas

1. Load the B16 artifact **lazily and once** per `generate()` call, not per-pick. Pass the index into `stamp_after_cost_fields(pick, index)` rather than loading it inside the function.
2. Staleness threshold: 25h (one dashboard rebuild cycle + margin).
3. Key strategy: `(strategy.lower(), asset_class.upper())` → row; fallback: `strategy.lower()` → first matching row.
4. The "Honest Read" panel in `template.html` is deferred to a follow-up PR (B17b) to keep this PR small and reviewable.
5. Tests should cover: null-strategy pick → null fields; matching strategy → correct fields; stale artifact → null fields; shadow gate ON with survivor → passes; shadow gate ON without survivor → fails; shadow gate OFF → always passes.

---

## D. Net Verdict

**Ready to ship** with the deltas above. The stamp function is pure-read from a pre-built dict, making it zero-risk to the existing normalization path. The shadow gate is additive and default-OFF. Scope is well-defined: field stamping + shadow gate + tests. No template changes needed in this PR.
