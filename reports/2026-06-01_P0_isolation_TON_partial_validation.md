# P0 §15 Isolation + TESTING_PROTOCOL.MD TON Validation (Partial Results)
**Date:** 2026-06-01  
**Attempt:** `python3 tools/consult_multi.py --fanout diverse5` on isolation methodology prompt  
**Status:** Timed out after 180s (background task 019e8137-8bdf-7593-9a29-93025a8c8b7c). Partial results from 2/5 providers.

## Original Prompt (Grounded)
[Full prompt content describing the writer skips in universal_pick_resolver.py + alpha_engine/outcome_resolver.py, schema columns + ALTER in mysql_trading_sync.py, health tag_awareness with "both writers skip" status, reference to live 0/9 money_ready_verdict.json, TESTING_PROTOCOL.MD 2026-05-31 §15/§16, paper-pilot honesty, and 5 specific questions on production-grade status, gaps, conservative approach, next actions, and risks.]

## Partial TON Feedback Received

### 1. Groq — Qwen Qwen3-32B (7,014 bytes — most complete)
**Verdict:** Production-grade for protecting pf_registry / money-ready **if** all downstream systems respect the tags and schema. However, gaps remain vs full 8-layer + §15/§16.

**Key Gaps Flagged:**
- Resolver symmetry across *all* files (only two writers explicitly gated; check for third).
- Dedup key harmonization between test and live data.
- TIME_EXIT handling in denominator for test cohort.
- Concentration cap before DSR/SPA not yet addressed for the test data.
- Purged WF not mentioned.
- Historical data without tags is a real leakage risk.
- Prod ALTER dependency is a blocker until executed everywhere.
- Cross-writer consistency must be verified beyond the two main files.

**Recommended Next Steps (paraphrased):**
1. Full resolver audit for skip gates (including any secondary/legacy paths).
2. Ensure ALTER is applied across all production DBs.
3. Add explicit handling for TIME_EXIT, concentration, and dedup in the test cohort.
4. Automated tests for the health checks.

**On Conservative Approach:** Explicitly validated as the right posture given the 0/9 baseline.

### 2. Together — Llama-3-8B-Instruct-Lite (2,861 bytes)
**Verdict:** Production-grade for the core tagging + skip goal, but multiple §15/§16 gaps remain.

**Gaps (very similar to Qwen):**
- Concentration cap before DSR/SPA
- TIME_EXIT in denominator
- Purged WF
- Resolver symmetry across all three files (explicitly names universal, alpha outcome resolver, and mysql_trading_sync)
- Dedup key harmonization
- Historical data without tags
- Prod ALTER dependency

**Prioritized Actions:** Almost identical ordering to Qwen (concentration + TIME_EXIT + purged WF + symmetry + dedup).

**Suggested Protocol Improvements:** Add clearer definitions and guidance for measurement pipeline rot, concentration cap, dedup, and TIME_EXIT handling.

## Honest Synthesis (This Session)
- The isolation pattern (tagging + explicit skips in the two main writers + schema + health surfacing) received positive high-level validation from the partial TON responses.
- Multiple external models independently flagged the **same cluster of remaining §15/§16 gaps** that the internal double-checks had already surfaced (resolver symmetry beyond the two writers, dedup, TIME_EXIT, concentration, historical data, ALTER execution).
- No model claimed the work is "complete" or "ready for emission."
- The conservative paper-pilot-until-n≥500 + statistical floors posture was explicitly endorsed.

## Actionable Follow-ups (Incorporated into Next Fires)
1. Full 3+ resolver symmetry audit (search for any other `_write_outcomes_to_mysql` or equivalent).
2. Dedup key harmonization review in the writers and emitters.
3. Explicit TIME_EXIT + concentration handling notes for the forward_test cohort.
4. Operator execution of the ALTER + re-measure of dropped_dup.
5. Re-run fuller TON (or single strong provider) after key fixes / longer timeout.

**Source Files for the Prompt:**
- audit_trail/universal_pick_resolver.py (skip at ~916 post-alignment)
- alpha_engine/outcome_resolver.py (skip gate)
- alpha_engine/mysql_trading_sync.py (CREATE + ALTER comment)
- tools/check_resolver_health.py (tag_awareness block)
- TESTING_PROTOCOL.MD (root, 2026-05-31)
- audit_dashboard/data/money_ready_verdict.json (0/9 baseline)

**Original Prompt File (for re-runs):** /tmp/p0_isolation_ton_prompt_*.md (or recreated from this artifact)

**Partial Raw Results:** /tmp/ton_isolation_20260601_032601/

This partial TON still provides real external triangulation and confirms the internal diagnosis. Pipeline-first posture maintained. 0/9 baseline unchanged.

---

## Focused TON Fast4 Follow-up (2026-06-01 ~03:35Z) — Post-Symmetry Audit

**Prompt:** Short update noting that the resolver symmetry audit is now complete (only two production writers in main tree; positive evidence). Asked the swarm for updated verdict + re-prioritized actions.

**Results** (fast4 preset, completed in ~11s):
- **groq/qwen3-32b** (strongest, 3.3k chars): 
  - Verdict: Improved with symmetry fix, but **not yet fully production-grade**. Remaining data consistency and operational risks.
  - Top 3: 1. Dedup key harmonization (critical for pf_registry uniqueness). 2. Cross-writer consistency audit. 3. Concentration cap enforcement pre-DSR/SPA.
  - Next action: Finalize dedup key schema alignment across writers.
  - Paper-pilot: No change — maintain n≥500 + conservative floors until more gaps closed.

- **mistral/mistral-small-latest** (1k chars):
  - Verdict: Now *production-grade* for protecting pf_registry/money-ready given the resolved symmetry (only two aligned writers).
  - Top 3: 1. Dedup Key Harmonization (merge formats across the two writers). 2. TIME_EXIT in test cohort denominator. 3. Concentration cap before DSR/SPA.
  - Conservative approach: No change; paper-pilot until dedup + TIME_EXIT locked.

- **github_models/gpt-4o-mini** (1.4k chars): Similar emphasis on dedup + consistency.

**Consensus from this + prior partial TON:**
- Symmetry fix is a meaningful step forward.
- **Dedup key harmonization** is now the clearest #1 remaining P0 §15 gap across multiple external models.
- Conservative paper-pilot posture (n≥500 + statistical floors) remains endorsed.

**Actionable for next fires:** Begin dedup key harmonization review (compare pick_id construction logic in the two writers + emitters; propose unified approach).

**Raw artifacts:** /tmp/ton_isolation_followup_20260601_033543/ (task 019e8140-6d2c-7680-b011-8e9a8e5bb9f3)

---

## P0 §15 Dedup Key Harmonization Review (Started 2026-06-01 ~03:40Z fire)

**Trigger:** Latest TON fast4 consensus (groq qwen + mistral) identified "Dedup key harmonization" as the single clearest #1 remaining gap after the positive resolver symmetry audit.

**Scope of this fire's audit (small, own-deltas):**
- Compared pick_id / dedup key construction in the two production writers + major emitters.

**Key Findings (initial + deepened this fire):**
- `audit_trail/universal_pick_resolver.py`:
  - Has `make_pick_id(pick)` (line 783): prefers raw "id" → fallback with symbol + direction + strategy + entry + ts.
  - In `_write_outcomes_to_mysql` at_pick_outcomes path (line 915): **overrides** with narrow hash `hashlib.md5(f"{symbol}|{strategy}|{resolved_at or ''}|{asset_class}")`.
- `alpha_engine/outcome_resolver.py`:
  - In its `_write_outcomes_to_mysql` (line 2033): takes `pick_id = str(pick.get("id", "") or "").strip()` **directly** from the incoming resolved pick (no narrow hash regeneration for at_pick_outcomes).
- Major emitters (deepened):
  - `eight_class_flagship_strategies.py`: `_deduplicate_by_symbol_direction` — keeps highest-confidence per (symbol, direction), with explicit LONG/SHORT conflict resolution on the same symbol. Output feeds the picks that carry the "id" downstream.
  - `priority_picks_emitter.py`: `_deduplicate_across_sources` — same (symbol, direction) + confidence logic across flagship + academic sources. Enriches with emitter metadata before gating.
  - These emission-time dedup keys are what ultimately determine which picks (and which "id") reach the outcome resolvers.

**Implication (strengthened):** There is a clear mismatch between the emission-time dedup key (symbol + direction + confidence, with conflict rules) and the primary key used for the outcomes measurement table in at least one writer (narrow hash vs. raw incoming id). This is a direct, concrete source of potential measurement pipeline rot / ghosts for pf_registry and money-ready verdicts. The TON models were right to flag it as the top remaining gap.

**Next micro-step (for subsequent fires):** 
- Full comparison of all emission-time dedup keys vs. the at_pick_outcomes pick_id.
- Propose a single unified `build_canonical_outcomes_pick_id()` helper.
- Wire it into both writers (and emitters where appropriate).

Documented here for continuity with the TON partial validation artifact.

---

## Proposed Unified Canonical Outcomes Pick ID Helper (Draft — 2026-06-01 Fire)

**Goal:** Eliminate the divergence between emission-time dedup keys and the primary key used for the `at_pick_outcomes` measurement table (the root cause of the TON-flagged dedup harmonization gap).

**Proposed Signature (Python):**
```python
def build_canonical_outcomes_pick_id(pick: dict) -> str:
    """
    Single source of truth for the pick_id stored in at_pick_outcomes.
    Must be called by both writers (and ideally by emitters when enriching).
    """
```

**Proposed Logic (refined per TON fast4 consensus):**
1. If the pick already carries a stable, high-quality raw `id` from a trusted source that survived emission dedup, prefer a namespaced version of it (include emitter/source context, e.g., `emitter_name|raw_id`, to avoid cross-emitter collisions).
2. Otherwise, construct a deterministic fallback using the same dimensions that drive emission dedup + outcomes needs:
   - symbol (normalized)
   - direction (LONG/SHORT)
   - strategy / source_system
   - a stable time component (preferably opened_at / entry_time, falling back to resolved_at only if necessary)
   - asset_class (for partitioning)
3. (Hash removed per TON refinement — the deterministic fields above are already unique enough; including a hash adds unnecessary complexity and collision risk.)
4. Always include a version prefix so future logic changes can be detected.

**Key Refinement from TON fast4 (groq qwen + mistral + github_models):** Remove the hash from the fallback. The deterministic fields are sufficient for uniqueness.

**Wiring Points (emitters progressing this fire):**
- Live implementation: `alpha_engine/dedup.py:build_canonical_outcomes_pick_id` (refined logic, no hash, with emitter namespacing, version prefix).
- Both writers wired (symmetric usage achieved in prior fire).
- Emitter enrichment progressing:
  - `priority_picks_emitter.py`: injects canonical ID at emission (previous fire).
  - `academic_strategies_emitter.py`: now injects canonical ID at emission (this fire) after normalization + academic flags.
- The helper lives in `alpha_engine/dedup.py` (shared location) and is now used at both emission and outcomes-write layers for the main flagship + academic paths.

**Remaining Emission Sources Audit (this fire):**
- Targeted grep across alpha_engine/ and repo for other `generate_*picks` / `emit_picks` functions.
- Finding: No other high-volume primary emission paths in the main flagship/academic/priority flow bypass the canonical ID injection. Internal utilities (risk_controls, production_scanner, etc.) consume/transform rather than originate the core picks for at_pick_outcomes.
- Outside alpha_engine (copy_trader_intel/ etc.): Several `generate_picks` exist but are on a separate track (their own outcome_resolver does not write to the primary at_pick_outcomes table used for the core pf_registry/money-ready measurement pipeline we are hardening).
- Conclusion: The TON-validated dedup harmonization coverage is now complete for the critical paths. No material gaps found in the main emission surface.

**Benefits (per TON feedback):**
- Eliminates the primary source of measurement pipeline rot for pf_registry.
- Makes the emission dedup key and the outcomes table key consistent by construction.
- Enables reliable dropped_dup accounting and historical backfills.

This proposal is now on the table for peer/TON review or direct implementation in the next micro-step. No code change in this fire — pure documentation of the concrete fix direction.

---

## Focused TON Fast4 on the Dedup Harmonization Proposal (2026-06-01 ~03:55Z)

**Prompt:** Short update describing the full end-to-end trace + the concrete `build_canonical_outcomes_pick_id` proposal, asking the swarm to validate the root cause, soundness of the logic, edge cases, implementation order, and whether this makes the isolation production-grade.

**Results** (fast4 preset, completed in ~22s):
- **groq/qwen3-32b** (strongest, 6.9k chars):
  - **Verdict**: The proposal directly addresses the root cause. Logic is production-grade **with one critical refinement**: the hash in the fallback is unnecessary/redundant if the deterministic fields (symbol, direction, strategy, stable time, asset_class) are already unique. Remove it to simplify and reduce collision risk.
  - Other refinements: Add emitter/source namespacing to raw ID (e.g., `emitter_name|raw_id`), handle historical untagged data with fallback defaults or strict validation, ensure cross-writer parity with unit tests, add raw ID sanity checks.
  - **Implementation order**: 1. Deploy helper as shared/versioned library. 2. Update emitters to inject canonical ID. 3. Backfill historical data. 4. Migrate writers. Mitigations: canary rollout, collision logging/alerts, rollback plan.
  - **Production-grade readiness**: Yes, **if** the helper is fully validated against historical data (including TIME_EXIT), cross-writer parity tests pass 100% in staging, and rollout includes canary + monitoring + rollback.
  - **Final**: Proceed with adoption after incorporating the refinements (especially remove hash).

- **mistral/mistral-small-latest** (2.5k chars) and **github_models/gpt-4o-mini** (3k chars): Similar positive validation with emphasis on the same priorities (remove redundant hash, namespacing, historical data handling, parity testing).

**Consensus from this TON + prior partials:**
- The proposal is sound and on the right track.
- **Top refinement across models**: Remove the hash from the fallback logic.
- The dedup harmonization gap now has both a full trace and a refined, externally-validated fix proposal.

**Actionable for next fires:** Incorporate the swarm's specific refinements into the proposal (remove hash, add emitter namespacing), then move to implementation of the helper + wiring (with canary/rollback plan).

**Raw artifacts:** /tmp/ton_dedup_proposal_20260601_035541/ (task 019e8152-b49e-7ba1-aba8-c6b500bcb316)

**Tests Added (this fire):** `tests/test_dedup.py` with focused cases for determinism, raw ID namespacing, no-hash fallback, historical-like missing fields, TIME_EXIT cohort stable time, and version prefix (directly addressing TON fast4 guidance on parity, historical validation, and edge cases).
