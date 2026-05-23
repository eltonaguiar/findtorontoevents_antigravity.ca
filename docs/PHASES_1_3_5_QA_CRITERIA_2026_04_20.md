# QA / pass criteria for Phases 1, 3, 5 (uncommitted)

**Status:** built by subagents, not yet committed. This doc enumerates the pass criteria against which 4 peer reviewers will evaluate before any commit lands.

**Cross-ref:** [docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md](REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md)

## What was built (uncommitted)

### Phase 1 — at-issue feed-membership stamping
**Files:**
- `audit_trail/feed_membership.py` (new, ~125 lines) — `VERIFIED_ALPHA_SOURCES`, `is_smart_pick_per_pick`, `is_verified_alpha_per_pick`, `evaluate_hc_tier`
- `audit_trail/stamp_pick_quality.py` (modified, +~40 lines) — adds stamping block in `stamp_picks()` loop after trust_tier, and `_CLOSED_STATUSES_FOR_AT_ISSUE` constant
- `tests/test_stamp_feed_membership.py` (new, ~140 lines, 11 tests)

**Notable choices:**
- `VERIFIED_ALPHA_SOURCES = frozenset({"claude_gainer_st", "claws_of_doom"})` — deliberately conservative; derived from current `TIER_PROVEN` entries in `cross_aggregation/system_trust_registry.py`
- HC tier evaluator inlined (not reusing `tools/hc_gates_python.py` — Phase 3 parity-tests that separately). Rule: `score >= 60 AND trust_tier in {PROVEN, RELIABLE} AND confidence >= 0.70`; `grade-a` requires `score >= 70 AND PROVEN AND conf >= 0.80`.
- `at_issue_*` twins snapshotted only when status in `_CLOSED_STATUSES_FOR_AT_ISSUE` AND twin not already present — frozen thereafter.

### Phase 3 — HC evaluator parity test
**Files:**
- `tools/hc_parity_test.js` (new, 106 lines) — Node CLI, reuses `audit_dashboard/hc_filter.js` via `require()`
- `tools/hc_parity_test.py` (new, 113 lines) — pipes 3,500 recent_closed picks through Node, compares to Python mirror, exits non-zero on any divergence
- `.github/workflows/hc-parity.yml` (new, 46 lines) — Mon 15:00 UTC cron + manual dispatch; validation-only, no auto-commit

**Local run result:** 3,500 picks, **0 divergences**; JS 0.22s, Python 0.02s.
**Browser stubs required:** None — `hc_filter.js` is already Node-aware via `typeof window !== 'undefined'` guards.

### Phase 5 — Wilson LB gate + hysteresis
**Files:**
- `audit_trail/guide_band_activation.py` (new) — `wilson_lower_bound(wins, n, z)` + `should_activate_guide_band(wins, n, currently_active, min_n=50, activate_at=0.52, deactivate_below=0.47, alpha=0.05, k=1)`
- `audit_trail/dashboard_generator.py` (modified) — call site ~line 13413; reads/writes `audit_dashboard/data/guide_band_state.json` for hysteresis persistence
- `audit_dashboard/template.html` (modified) — inline script conditionally rewrites the "under re-validation" block with live Wilson LB when `active === true`
- `tests/test_guide_band_activation.py` (new, 10 tests)

**Notable choices:**
- `wins > n` raises `ValueError` (upstream counting bug surfaces; silent clipping rejected)
- Bonferroni: `k` scales confidence via `1 - alpha/k`; `deactivate_below` stays on 95% scale (preserves hysteresis semantics)
- Current `recent_closed` has n=0 matching PROVEN+conf 0.8-0.9, so `active` resolves False today; gate flips on automatically when cohort repopulates past n=50 with Wilson LB ≥ 0.52

## Aggregate test result
**59/59 unit tests pass** across Phase A + B + feed-hygiene + stamp-feed-membership + guide-band-activation.
**Syntax clean** on all 4 modified Python files.

---

## Pass criteria each reviewer should check

### Correctness
1. Phase 1: does the at_issue_* snapshot fire **exactly once** on ACTIVE→CLOSED and **never rewrite** thereafter? (Idempotency test exists; read it and confirm logic.)
2. Phase 1: is `is_smart_pick_per_pick` respecting the `classify_pick_quality_v2` convention (clone `status="ACTIVE"` before gate call)? If not, closed picks would silently return None.
3. Phase 3: is the JS-vs-Python parity test reading the SAME `correlation_pair_registry` on both sides? (Cursor mirror must match JS source.)
4. Phase 5: hysteresis state survives dashboard regens via `guide_band_state.json`. What happens on fresh install when the file doesn't exist yet?
5. Phase 5: `wins > n` raises ValueError. Does it raise in a way that halts the pipeline, or is it caught defensively?

### Gate/methodology alignment with v3 doc
1. VERIFIED_ALPHA_SOURCES has only 2 entries. Is that too narrow? Does it leak past validation (e.g., a source_system that was historically treated as PROVEN but is missing here — resulting in the user seeing a PROVEN pick NOT flagged is_verified_alpha)?
2. Phase 5 `activate_at=0.52` / `deactivate_below=0.47` — is the hysteresis gap of 5pp appropriate? Too narrow = flicker; too wide = latency in deactivating a genuinely decayed filter.
3. Phase 1 HC tier evaluator uses score/trust_tier/confidence thresholds — where did those numbers come from? Are they just "vibes" or derived from the repo's existing hc_filter.js?
4. Phase 3 CI workflow is weekly. Given the frequency of closed-pick turnover, is weekly too slow for parity drift detection?

### Safety / blast radius
1. Phase 1 modifies `stamp_pick_quality.py` hot path. If `feed_membership` import fails (missing dep, circular), does the existing trust-tier stamping still work? (Defensive try/except needed?)
2. Phase 5 modifies `dashboard_generator.py` — new code path writes `guide_band_state.json`. If that write fails (disk full, permissions), does it crash dashboard regen or warn-and-continue?
3. Phase 3 workflow `continue-on-error: false` by default — if the parity test fails, does it block anything downstream? Is this the right rigor level?
4. Phase 5's inline script in `template.html` — does it degrade gracefully if `summary.guide_band_proven_conf_80_90` is absent (old payload schema)?

### v1.1 governance
1. Phase 1 stamps `is_verified_alpha` using a hard-coded source list. Should this be revision-controlled via `docs/` rather than buried in a `frozenset` at module top?
2. Phase 3 parity failure behavior: on divergence, what's the operator's runbook? Rebuild the JS? Revert Phase 1 stamping?
3. Phase 5 band re-enablement is automated via Wilson LB. Should this require human review (like `_FORCE_DEMOTED_STRATEGIES` does), or is the Wilson gate sufficient governance?

---

## What reviewers should NOT flag as blockers

- Docstring verbosity or style — cosmetic
- Minor variable naming preferences
- "Could be refactored to share code with X" — unless the refactor is safety-critical
- Test fixture style — if coverage is adequate, leave it

## Reviewer output format

Each reviewer should return (under 400 words each):
- **Blockers** (must fix before commit) — file:line citations
- **Should reconsider** — with rationale
- **Verdict**: commit as-is / commit after minor fixes / hold

Blockers will be fixed before commit; "should reconsider" items will be logged as follow-ups.
