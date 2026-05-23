# Review: Plan — Improve Struggling Asset Class Performance

**Reviewer notes (2026-04-14)** — Feedback on the draft plan *Infrastructure for Non-Crypto Asset Class Recovery*. Line references in the plan may drift; verify against current files before implementation.

---

## Executive summary

The plan is **coherent, phased, and reversible**, and it respects repo rules (investigation before broad strategy kills, no placeholder data). The highest-value adjustment is **Phase 2**: the repo already implements sophisticated exit normalization in `audit_trail/quality_gates.py` (`normalize_exit_reason()`). The draft should **wire that helper into ingestion/dashboard** rather than adding a second, simpler mapping that could **re-introduce** the issue #186 bias (treating ambiguous closes as SL hits).

---

## Strengths

1. **Clear triage ordering** — Hard blocks and gate fixes before pipeline mutations (CRYPTO TP/SL) matches risk management: stop bleeding first, measure, then change generation.
2. **Governance hooks** — COMMODITY freeze doc + mutation protocol for CRYPTO SL/TP aligns with `CLAUDE.md` / `STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
3. **Separation of concerns** — FOREX “fix labels, not block” vs COMMODITY “investigate then demote” is logically sound given different failure modes.
4. **Verification section** — Measurable outcomes (counts, ratios, parity) make rollback and review possible.

---

## Phase 1 — Triage & hard blocks

| Item | Feedback |
|------|------------|
| **Block ETF** | Low risk if volume is truly tiny; confirm `BLOCKED_ASSET_CLASSES` is the single source used everywhere picks are admitted (including any batch importers). One-line change is fine if grep shows no parallel allowlists. |
| **EQUITY bypass + `strat_fwd_wr ≥ 55%`** | Matches the intent of stale Bayes WR. **Implementation detail:** picks may expose forward WR under multiple keys; `quality_gates.py` already consolidates via `_effective_forward_wr_ratio()` / `strat_fwd_wr` / `strategy_fwd_wr` — reuse that normalization so the gate behaves consistently. |
| **COMMODITY soft freeze** | Good. Explicit doc path avoids silent policy drift. |

**Risk:** Tightening bypass may drop visibility for a **small set of genuinely good** low-score names; worth a one-time before/after list of affected `(strategy, symbol)` for manual spot-check.

---

## Phase 2 — Exit label normalization

**Critical alignment with existing code**

- `quality_gates.py` already documents issue **#186** and implements `normalize_exit_reason(pick)`, which:
  - Refines `WON`/`LOST`/`WIN`/`LOSS` using **exit vs TP/SL distance** when prices exist.
  - Maps ambiguous cases to **`FORCE_CLOSED`**, not to `SL_HIT`, because many legacy “LOST” rows are **not** stop-loss events.
- The draft suggests mapping to `TP_HIT`/`SL_HIT` with fallback to **`TIME_EXIT`**. That **differs** from the implemented policy (`FORCE_CLOSED` for unresolvable binary labels). Blind `LOST → SL_HIT` would **worsen** FOREX discipline metrics relative to the current design.

**Recommendation**

1. **Primary action:** Call `normalize_exit_reason()` (or share its logic via one module) in `dashboard_generator.py` at the agreed boundary — *post-resolution, single pipeline* — and add `exit_label_quality` there if still needed.
2. **Do not** duplicate a naive WON/LOST → TP/SL map alongside the existing helper unless tests prove the helper is unsuitable.
3. If product/UI requires a “legacy binary” flag, base it on **raw** `exit_reason` ∈ {WON, LOST, …} **before** normalization, or on `normalized == FORCE_CLOSED` with binary raw input — not on TP_HIT/SL_HIT alone.

**Tests:** Add golden cases: binary label + exit near entry → `FORCE_CLOSED`; binary + exit near TP → `TP_HIT`; parity + dashboard stats sanity.

---

## Phase 3 — COMMODITY investigation & decay gate

| Item | Feedback |
|------|------------|
| **Scorecard script** | Good. Pin output filename to the date of the run; keep under `docs/` as proposed. |
| **`_hf_threshold_a` in `passes_active_gate()`** | Accurate gap: today `_hf_threshold_a` excludes **Smart** picks (`passes_smart_gate`) but not necessarily **all** active display. Extending to active for non-crypto **increases severity** — intentional per plan; document expected drop in COMMODITY active count. |
| **Demotion PR** | Matches `STRATEGY_INVESTIGATION_BEFORE_KILL.md`; keep mutation CSV / analysis artifacts in the PR for auditability. |

**Edge case:** When `bt_wr` / `fwd_wr` are missing, `decay_hard_gate_triggers()` returns `False` (no gate). Confirm picks with partial stats do not **hide** decay; optional follow-up: surface “insufficient data” in health (Phase 4).

---

## Phase 4 — Asset class health on dashboard

- Half-split PF by asset class is valuable; define **minimum closed N** per class before showing STABLE/DECAYING (avoid noisy badges on thin samples).
- **Thresholds:** Document cutoffs for DECAYING vs DEAD (e.g. delta PF, absolute new PF) so the UI is not purely subjective.
- **Template rule:** Project convention is to edit `audit_dashboard/template.html` (not generated `index.html` if applicable) — the plan already points at the template; keep generator + template in sync for JSON keys.

---

## Phase 5 — EQUITY HC filter extension

- **Motivation** is clear (surface score+trust edge).
- **Constraints:** `classify_hf_conviction_tier()` already requires `min_forward_trades` and other gates — new EQUITY paths should **respect the same forward-trade and trust-tier rules** to avoid promoting picks that fail other HC invariants.
- **Parity:** Running `tools/validate_dashboard_parity.py` after changing `conviction_stack.py` + `dashboard_hc_rules.py` + `hc_filter.js` is mandatory; list all three in the PR checklist.
- **≤10 picks increase:** Treat as a **soft guardrail**, not a hard revert trigger — if the data supports more promotions, revisit the cap after measuring PF impact.

---

## Phase 6 — CRYPTO SL:TP ratio

- Correctly flagged as a **mutation** requiring `MUTATION_THREE_AXIS_PROTOCOL.md` analysis.
- **Correlation vs causation:** High SL:TP ratio may reflect **regime** (trend vs chop) as much as ATR caps. Phase 6 should include a short **baseline window** and control for direction (LONG-only policy already touched in smart gate comments).
- **Interaction:** Earlier `TRAIL_ACTIVATE_PCT` changes affect live behavior; ship behind a flag or narrow symbol cohort if possible.

---

## Cross-cutting items

1. **Order of operations:** Phases 1–2 improve **measurement**; Phase 3–4 improve **visibility**; Phase 5–6 change **promotion and risk**. Avoid running Phase 6 before Phase 2 metrics are trustworthy, or mutation analysis will be noisy.
2. **Documentation:** Per user preference, avoid expanding markdown beyond what the team needs; the COMMODITY freeze + investigation docs are justified; optional short “Phase 2 wired normalize_exit_reason” note in an existing ops doc may suffice instead of a new long design doc.
3. **No synthetic data:** Plan complies with workspace rules.

---

## Suggested edits to the draft plan (summary)

| Section | Suggestion |
|---------|------------|
| Phase 2 | Replace bespoke WON/LOST mapping with **adoption of `normalize_exit_reason()`**; use **`FORCE_CLOSED`** (or document explicit deviation) instead of defaulting to `TIME_EXIT`. |
| Phase 1 | Use **`_effective_forward_wr_ratio()`** or the same field precedence as gates for the new recency condition. |
| Phase 4 | Add **min sample size** and **numeric thresholds** for health badges. |
| Verification | Add **unit/integration tests** for exit normalization and a **before/after** export for Phase 1 EQUITY bypass changes. |

---

## Verdict

**Approve with revisions:** Implement Phase 2 by **integrating existing normalization** rather than duplicating weaker rules; align fallback labels with `normalize_exit_reason()` semantics. The rest of the plan is execution-ready with the usual caution on line-number references and cross-file parity (HC filter + dashboard).
