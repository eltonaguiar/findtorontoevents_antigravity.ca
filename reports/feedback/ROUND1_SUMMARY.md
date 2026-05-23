# AI Review Round 1 — 2026-05-01


## deepseek

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

---


## xai-grok

**A. Confirmed Strengths of the Plan (What Should Not Change)**  
The action plan demonstrates several robust elements that align with best practices for a multi-asset hedge fund alpha pipeline. The strict adherence to the Wire-Up Rule and Default-OFF policy for new gates or scoring changes, with a mandatory 14-day shadow period (e.g., B9, B5), ensures risk mitigation and aligns with production stability goals. The small PR scope (1-3 files) with tests and per-PR documentation fosters maintainability and reviewability. The use of `safe_push.sh` for concurrency in auto-commit workflows is a critical safeguard. Additionally, the detailed verification steps in Wave 1 (V1-V8) and the impact-ranked sequencing table provide clear prioritization and traceability, especially for urgent diagnostics like EQUITY-REGRESS (Item 2). The risk controls and acceptance criteria, targeting a PF lift from 0.98 to ≥1.05, are well-defined and measurable.

**B. Surfaced Contradictions, Blockers, Missing Prerequisites**  
A contradiction exists in the scheduling of B5 (Cursor Phase 3 scoring, Item 12) and B13 (per-class HMM, Item 13), both marked HIGH risk with shadow periods, yet their prerequisites (B4 48h soak and B12 7d soak) lack explicit verification steps in the plan beyond Wave 1’s V6. Without a confirmed checkpoint post-soak, there’s a risk of premature deployment. Additionally, B25 (TradingAgents identical-metrics, Item 16) is diagnostic-blocked but lacks a timeline or interim mitigation for unblocking, potentially stalling B26 downstream. Lastly, HYRO-FRESHNESS (Item 11) lacks clarity on whether revival or retirement is the default path if the workflow audit fails, risking scope creep in a tight 7-day window.

**C. Recommended Deltas to the Sequence (Move X Up, Add Y, Drop Z)**  
- Move B9 (TradingAgents wire-in shadow, Item 10) up to position 5, ahead of B19 (pair-level carve-out), as it activates a broader adversarial-debate sidecar with lower risk (LOW vs. MED) and leverages V1 verification expected imminently.  
- Add a new verification step post-Wave 1 for B4 and B12 soak periods, inserted before Items 12 and 13, to confirm prerequisite stability via a dashboard or audit log check. Label this as V9 (B4 soak) and V10 (B12 soak).  
- Drop B25 (Item 16) from the 7-day completion goal and reclassify it under Wave 6 as operator-decision-blocked until a diagnostic timeline is proposed, avoiding indefinite stalls.  

**D. Net Verdict: Needs-Rewrite**  
The plan is comprehensive but not ready-to-execute due to missing verification steps for HIGH-risk prerequisites (B5, B13) and unresolved blockers (B25). A rewrite incorporating the proposed deltas—reordering B9, adding V9/V10 checks, and deferring B25—will align it with risk controls and timeline feasibility. Revise and resubmit v2 for final review, ensuring soak-period confirmations and diagnostic clarity are addressed.

---


## cerebras-qwen-235b

**A. Confirmed strengths of the plan (what should not change)**  
The plan’s core structure is excellent: impact-ranked sequencing with strict prerequisite enforcement, clear risk labeling, and gating logic based on empirical accrual (e.g., B4/B12/B16 soaks) is correct and must be preserved. The separation of verification (Wave 1) from recreation (Wave 2) and empirically driven follow-ups (Wave 3) ensures stability post-merge. The 14-day shadow requirement for B9 is properly enforced, and the safe_push.sh mandate for auto-commits is essential. The acceptance criteria are measurable and tied to observable outputs (B16 readouts, PF ≥1.05), which aligns with production discipline.

**B. Surfaced contradictions, blockers, missing prerequisites**  
- **V8 verification is new but not gated in any Wave 5 item** — yet B17/B18 depend on B16’s daily artifact. If V8 fails, B17/B18 cannot proceed, but there's no explicit verification that the artifact is *parsable* or *complete*, only that it exists.  
- **B9 (TradingAgents wire-in) is gated on V1**, but V1 only confirms UEPS picks appear — not that the *contract shape* matches what `emit_long_term_picks` expects. Risk of schema mismatch is unaddressed.  
- **EQUITY-REGRESS (Item 2)** is correctly prioritized, but no dependency on fresh EQUITY data post-merge is stated. If the post-#582 emit cycle hasn’t run, the diagnostic may be stale.  
- **B5 and B13** are marked HIGH-risk and correctly shadow-gated, but the plan lacks a defined *flip-on* trigger beyond time (48h/7d soak) — should require PF lift or WR stability in the shadow.

**C. Recommended deltas to the sequence**  
- **Move B23 (Item 4) to Item 1.5**, immediately after V1-V8, since it’s a one-line verification that unblocks B26 and may reveal a critical resolver gap.  
- **Insert new Item 2.5: “Validate emit_long_term_picks output schema post-V1”** before B9 (Item 10) — this closes the B9-V1 gap.  
- **Move HYRO-FRESHNESS (Item 11) to Item 6**, ahead of B2-redux — it’s lower risk than slippage testing and unblocks telemetry needed for future diagnostics.  
- **Add prerequisite check for B17/B18: V8 must confirm artifact contains ≥7 days of non-null entries**, not just existence.  
- **Drop B6 (Item 3) ahead of B23** — correct as-is, since B6 depends only on V6 and is LOW risk.

**D. Net verdict: ready-to-execute**  
With the above deltas — particularly hardening the B9 schema check and tightening B17/B18 gating — the plan is **ready-to-execute**. It respects wire-up rules, defaults off, and small-PR discipline. No rewrite needed; proceed to v2 with these adjustments.

---


## cerebras-glm-4.7

A. Confirmed strengths of the plan
The prioritization of **Item 2 (EQUITY-REGRESS)** is the plan's strongest asset; addressing the 1.43 → 1.29 PF drop before adding new features is the correct quantitative discipline. The strict separation of **Item 1 (Verification)** from code changes prevents "fixing" transient propagation lag. Additionally, the explicit gating of **Items 12 & 13 (B5, B13)** behind shadow-mode soaks strictly adheres to the Default-OFF constraint, ensuring high-risk scoring changes do not destabilize the live book.

B. Surfaced contradictions, blockers, missing prerequisites
1.  **Item 10 (B9) Dependency Logic Error:** The plan states B9 is "gated on V1" (UEPS picks appearing). B9 is a TradingAgents integration, while V1 is specific to UEPS. Unless TradingAgents is a sub-component solely of UEPS, this dependency is a logic error. B9 likely depends on **Item 4 (B23)** verifying the resolver, not V1.
2.  **Missing Prerequisite for Item 16 (B25):** The sequence table lists Item 16 as the "fix" for B25, but the Wave 6 text explicitly states "Diagnostic needed first." The diagnostic task (logging raw LLM responses) is missing from the sequence. You cannot schedule the fix without the diagnostic preceding it.
3.  **Wire-Up Rule Violation Risk:** **Item 10 (B9)** proposes a "wire-in shadow" but does not explicitly identify the production caller in the sequence table. Per the Wire-Up Rule, this requires an explicit opt-in path or caller confirmation before the PR is drafted.

C. Recommended deltas to the sequence
1.  **Move Item 6 (B2-redux) to Position 3:** The Asset-Class × Timeframe grid panel is a critical diagnostic tool for the **Item 2** regression analysis. It should be built immediately after the regression is identified to visualize the degradation, rather than waiting until after UI filters (Item 3).
2.  **Move Item 4 (B23 verify) to Position 3 (concurrent with B2):** Verifying the `SYSTEM_SOURCES` entry is a prerequisite for **Item 10**. This infrastructure check must happen before planning the TradingAgents wire-in.
3.  **Insert "B25-Diag" before Item 16:** Add a new item: "Log raw LLM responses for TradingAgents per ticker." This must be completed before the fix in Item 16 can be attempted.
4.  **Clarify Item 10 Dependency:** Change the "Why now" for Item 10 to reflect dependency on Item 4 (B23) and explicit Wire-Up documentation, not V1.

D. Net verdict
needs-rewrite. The sequence contains a false dependency (B9 on V1) and omits a required diagnostic step for B25. Adjust the order to prioritize diagnostics (B2) over UI polish (B6) and fix the B9/B25 logic blocks.

---


## kimi-k2-6

The user wants me to review a draft action plan for a multi-asset hedge-fund-style alpha pipeline. I need to reply in 4 sections (A, B, C, D) with 300-500 words total. I need to be specific, cite item numbers from the sequence table, and not repeat the plan.

Key constraints from the system prompt:
- Wire-Up Rule: every new integration must have a production caller OR be opt-in with explicit wiring plan
- Default-OFF for any new gate or scoring change; 14-day shadow before flip-on
- Each PR ships small (1-3 files typical), with tests + per-PR doc
- safe_push.sh handles concurrency for auto-commit workflows

Let me analyze the plan:

Strengths:
- Verification-first approach (Wave 1 / Items 1) before writing new code
- Explicit risk ratings and gating (B5 gated on B4 soak, B13 on B12 soak)
- Small PRs with tests + docs
- Uses safe_push.sh
- Defers high-risk items (B5, B13) until soak complete
- Acknowledges degraded performance metrics and prioritizes EQUITY-REGRESS (Item 2)
- Separates blocked/operator-decision items (Wave 6)

Contradictions/Blockers/Missing Prerequisites:
- Wire-Up Rule violation: Item 10 (B9 TradingAgents wire-in) says "Ready to schedule for shadow-mode 14-day run in `long_term_pick_contract.py::emit_long_term_picks`" but does it have a production caller or explicit opt-in wiring plan? The plan mentions shadow mode but needs explicit wiring.
- Item 5 (B19 pair-level carve-out): This is a registry entry `(atr_percentile_gate, BTCUSDT, LONG)`. Is this a gate change? If so, Default-OFF requires 14-day shadow before flip-on. But the plan puts it at Order 5 without mentioning shadow/gating. The acceptance criteria wants PF 0.98→1.05 in 14 days, but B19 might need shadow time.
- Item 8 (FOREX-RESOLVER-2): This drops threshold 5.0 → 1.5. This is a scoring/gate change. It should be Default-OFF with 14-day shadow, but plan says "ship if Sharpe lift ≥ 0.5" without mentioning the mandatory 14-day shadow period.
- Item 12 (B5 Cursor Phase 3 scoring): HIGH risk. Plan says "gated on B4 soaking 48h post-merge". But the codebase constraints say "Default-OFF for any new gate or scoring change; 14-day shadow before flip-on". The plan mentions 48h soak for gating start, but B5 is a scoring change so it needs 14-day shadow, not just 48h. Also, B5 is HIGH risk but plan says "lands behind shadow flag for ≥48h" in risk controls — contradicts the 14-day shadow rule.
- Item 14/15 (B17/B18): Gated on B16 7d data, but B16 just merged. Plan says "can start once B16's daily artifact accrues 7+ days of data" — this is fine, but do these items respect the 14-day shadow for gating changes? B17 is "HC button after-cost gating" — that's a gate change, needs 14-day shadow.
- Item 3 (B6 Cursor Phase 5 UI filters): LOW risk UI. But it depends on concept_family field appearing on every pick (V6). If it's UI-only, maybe fine, but if it filters/scores picks, could affect production flow. Need to ensure it's read-only UI.
- Missing explicit Wire-Up plan for B9 (Item 10). Also B7 (

---
