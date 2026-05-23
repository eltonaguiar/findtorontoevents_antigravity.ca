### A. Confirmed strengths of the plan

1. **Verification-first discipline (Wave 1, Item 1):** Running V1-V8 before any new code is the correct priority—it prevents building on unconfirmed merges.
2. **Impact-ranked sequencing:** Placing EQUITY-REGRESS diagnostic (Item 2) at #2 aligns with the 1.43→1.29 PF degradation being the most urgent empirical problem.
3. **Risk controls alignment:** HIGH-risk items (B5, B13) behind shadow flags, `safe_push.sh` enforcement, and prerequisite verification on `main` all match the codebase constraints.
4. **Default-OFF compliance:** B9 (TradingAgents wire-in) correctly specified as 14-day shadow mode.
5. **Deferred scope discipline:** B22, B26, B10 are correctly parked—they lack prerequisites or operator decisions.

### B. Surfaced contradictions, blockers, missing prerequisites

1. **Contradiction: B6 (Item 3) before B2-redux (Item 6):** B6 (Cursor Phase 5 UI filters) is gated on `concept_family` field appearing on every pick (V6). But V6 verification is in Wave 1, which runs *before* Item 3. However, B2-redux (grid panel) also depends on V6 being clean. If V6 fails, both Items 3 and 6 are blocked. The sequence should group these together after V6 confirmation.
2. **Missing prerequisite: B19 (Item 5) needs V6 verification:** The `(atr_percentile_gate, BTCUSDT, LONG)` carve-out requires `concept_family` stamps to be present on all picks (V6). If V6 fails, the carve-out registry entry may reference a non-existent field.
3. **Blocked: B7 (Item 9) CFTC COT live-wire:** The plan notes V7 marked "non-fail diagnostic" on 2026-05-01 (0 BOND credit-spread picks). But B7 is a *new* integration—per the Wire-Up Rule, it needs a production caller OR explicit wiring plan. The plan doesn't specify which workflow will consume COT data. This is a missing prerequisite.
4. **Contradiction: B25 (Item 16) diagnostic-blocked but sequenced:** The plan correctly identifies B25 as "blocked behavior diagnosis, not code" but still places it at #16. This is misleading—it should be a diagnostic task, not a PR.

### C. Recommended deltas to the sequence

1. **Move B6 (Item 3) after V6 confirmation (after Item 1, before Item 2):** Group V6 verification + B6 UI filters + B2-redux grid panel into a single "concept_family surface" mini-wave. This avoids partial failure states.
2. **Add prerequisite check for B7 (Item 9):** Before scheduling, specify the production caller (e.g., `forex_resolver.py` or `commodity_resolver.py`). If none exists, B7 must be deferred or the plan must include a wiring PR.
3. **Drop B25 (Item 16) from sequence:** Replace with a diagnostic task: "Log raw LLM responses per ticker for 7 days; produce report." The fix PR should only be sequenced after diagnosis.
4. **Swap Items 8 and 9:** FOREX-RESOLVER-2 (Item 8) is lower risk and has a clear A/B replay path. B7 (Item 9) has the unresolved wiring issue. Move FOREX-RESOLVER-2 to #8, B7 to #9 only after wiring is confirmed.
5. **Add B23