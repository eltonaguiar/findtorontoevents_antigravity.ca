# B17 — HC Button Audit + After-Cost Gating
## Multi-AI Review: Codebuff Proxy (Claude simulated, per §5 protocol)
**Date:** 2026-05-02

---

## A. Confirmed Assumptions

1. **B16 tool produces usable JSON.** Running `python3 tools/forward_edge_audit.py --date 2026-05-02` produced `reports/forward_edge_audit_2026-05-02.json` with `strategies` array of 248 items and `survivors` array of 5. The `both_survive` field (bool) is the correct `is_ac_survivor` flag.

2. **`_normalize_pick()` is the correct injection point.** All picks flow through it regardless of source. Adding field stamping there ensures 100% coverage (confirmed: V6 shows 18/18 active picks carry `concept_family` — same pattern).

3. **`transaction_costs.json` already exists.** `tools/data/transaction_costs.json` is on main (confirmed `ls`). B17 can reference it for documentation but the `forward_edge_audit.py` tool already uses it internally — no new config file needed.

4. **HC gate files correctly identified.** `tools/hc_gates_python.py` ends with `filter_high_conviction_ordered()` and `passes_high_conviction_pick()`. Appending `passes_hc_after_cost()` at the end does not disrupt existing exports.

---

## B. Surfaced Contradictions / Blockers

1. **PR #601 was closed without merge.** Root cause unknown. The new PR should clearly mark itself as a re-implementation (not a squash/fixup) so CI has a clean history. Add a note in PR body that this supersedes closed PR #601.

2. **test_hc_gate_audit.py snapshot test.** The original B17 PR (#601) mentioned a snapshot test that would fail on future gate changes. This is good practice but the snapshot depends on the current dashboard payload, which changes hourly. Use a synthetic fixture snapshot instead of the live payload to avoid flakiness.

3. **`is_ac_survivor: None` vs `False`** is semantically different. `None` = unknown (strategy not in index); `False` = known non-survivor. The HC shadow gate should treat `None` as "don't filter" (pass-through) and only block when `is_ac_survivor = False` with both fields populated. Confirmed delta in Claude review above.

4. **Loading B16 artifact path.** The artifact filename includes a date (`forward_edge_audit_2026-05-02.json`). The loader must find the latest one by `sorted(glob(...))[-1]` rather than hardcoding the date. This ensures the function works without daily reconfiguration.

---

## C. Recommended Deltas

1. Artifact discovery: `sorted(glob("reports/forward_edge_audit_*.json"))[-1]` with fallback to `None` if empty.
2. Build index as `{(strat, class): row, strat: row_for_fallback}` — two-layer lookup.
3. `passes_hc_after_cost()` signature: `(pick: dict) -> bool` with `os.environ` check inside (no need to pass flag as param — keeps call site clean and consistent with existing HC gates).
4. Export `passes_hc_after_cost` from `tools/hc_gates_python.py` only (authoritative); `dashboard_hc_rules.py` imports from it.
5. Add `"after_cost_net_per_trade": None, "wilson_lb_wr": None, "is_ac_survivor": None` to the `PICK_SCHEMA_KEYS` constant in `dashboard_generator.py` (line ~208) to keep schema documentation current.

---

## D. Net Verdict

**Ready to ship.** Low risk, additive only, default-OFF gate. Consensus delta with Claude primary review: lazy artifact load, staleness guard, null passthrough, synthetic snapshot test. No template changes. Two feedback docs provided per §5.
