# Proposed approach — remaining /audit enhancement items (2026-04-20)

**Status:** proposal for peer review. Not yet implemented.

**Author:** Claude Opus 4.7 (1M context)

**Context:** after today's v1.1 enforcement round (commits `cb54fee16` → `fda3398ce`), two product/UX-level items remain from the effectiveness audit and additional-fixes survey. This document proposes concrete approaches for each and solicits peer-review feedback.

---

## Item 1 — At-issue feed-membership stamping

### What's left

The closed-pick schema now allows `is_smart_pick`, `is_verified_alpha`, `hc_tier`, `ml_score`, `hf_conviction_tier`, `va_cohort_id`, `sym_track_wr`, and `paper_trade` fields (commit `faba0b66a`), but **upstream writers don't populate them**. Every field is currently 0% populated on closed picks.

Without populated flags, Smart Picks / High Conviction / Verified Alpha feeds are retroactively unauditable — we can't run counterfactuals like "what did the Smart Picks tab return on the user on 2026-04-19?".

### Proposed approach: hybrid stamping at two life-cycle events

**(a) At ingest** — `alpha_engine/feed_hygiene.sanitize_active_picks` is already the canonical choke point. Add a helper `stamp_feed_membership(pick)` that computes all flags against current gate state:

```python
# In a new module: audit_trail/feed_membership.py
def stamp_feed_membership(pick: dict) -> dict:
    """Stamp at-issue feed flags on an active pick. Idempotent."""
    out = dict(pick)
    out.setdefault("is_smart_pick", bool(passes_smart_gate(pick)))
    out.setdefault("is_verified_alpha",
                   pick.get("trust_tier") == "PROVEN"
                   and pick.get("source_system") in VERIFIED_ALPHA_SOURCES)
    out.setdefault("hc_tier", evaluate_hc_tier(pick))  # from hc_gates_python
    return out
```

Wire into `sanitize_active_picks` immediately after `ensure_entry_time` + `normalize_forex_pnl`. Idempotent via `setdefault`, so picks re-ingested later preserve original stamps.

**(b) At status transition** — when a pick flips ACTIVE → CLOSED (outcome resolver), snapshot the three booleans into `at_issue_*` twins the same way `at_issue_strat_fwd_wr` already works. This preserves "what the user actually saw" even if the gate logic changes weeks later.

### Why not single-point stamping?

- **Stamp only at ingest:** historical picks in existing `active_picks.json` files never get stamped. Would need a one-time backfill script.
- **Stamp only at close:** active picks don't carry the flag, so the dashboard would have to recompute it on every render (inefficient and fragile vs code drift).

Hybrid gets both: new picks stamped immediately, closed picks preserve the at-issue snapshot, all without backfill.

### Edge cases / risks

1. **Drift between `is_smart_pick` and `passes_smart_gate`** — if the gate logic changes after stamping, closed-pick flags become stale. This is **intentional** (that's the at-issue point), but should be documented in the dashboard Guide.
2. **Verified Alpha source list** — needs a small config constant of sources that qualify. Today this is implicit in the dashboard logic; make it explicit in `audit_trail/feed_membership.py::VERIFIED_ALPHA_SOURCES`.
3. **HC tier** — already has a Python mirror (`tools/hc_gates_python.py`) from Cursor's data-health work. Reuse `filter_high_conviction_ordered`'s per-pick evaluator rather than re-implementing.

### Effort estimate

~2 hours implementation + ~1 hour tests + ~30min dashboard Guide update. Single PR touching 3 files.

---

## Item 2 — Guide copy for the `PROVEN + confidence 0.8-0.9` band

### What's left

Cursor's effectiveness audit found the Guide overlay documents a filter (`trust_tier=PROVEN AND confidence in [0.8, 0.9]`) that has **n=0 historical trades** on the 3500-row window. The Guide advertises an edge that cannot be validated empirically.

### Proposed approach: update copy + observability, not deletion

**(a) Update Guide copy.** Change the existing overlay text to something like:

> **Emerging filter — insufficient sample.** This band (PROVEN tier + confidence 0.8-0.9) currently has < 10 closed trades in the last 30 days. Performance claims are based on backtest only; will activate once n ≥ 50. See `/audit/data/edge_report.md` for live-sample status.

Rationale: deletion destroys the specification; widening the band (e.g., to `[0.7, 0.95]`) changes the advertised filter without notifying users. Copy update is the honest minimum.

**(b) Add sample-size live indicator.** In `audit_dashboard/template.html`, alongside the existing Guide ?-overlay, render the actual n of picks currently matching each cited filter. If n < 10, show an amber warning icon. If n ≥ 50, show a green check. This is empirical, updates every dashboard cycle, and prevents future stale-copy drift.

**(c) Re-evaluate after the PROVEN tier correction settles.** Today's `claude_gainer_st` force-demote (commit `534269141`) changes the PROVEN cohort distribution substantially. The 0.8-0.9 confidence band may populate naturally once the tier's definition is trustworthy again. Defer widening/deletion until 7 days of fresh closes under the new logic.

### Why not just delete the band?

The original rationale for `PROVEN + conf 0.8-0.9` was: high-trust strategies with moderate-but-not-suspicious confidence tend to outperform both extremes. That's a real hypothesis worth preserving even if the current sample is zero. Honest copy + live indicator beats silent deletion.

### Edge cases / risks

1. **If the band stays at n=0 for 30+ days post-correction**, widening or deletion becomes defensible. Set a calendar reminder.
2. **Live-indicator rendering cost** — trivial (single-pass filter on recent_closed during dashboard_generator).

### Effort estimate

~30min copy update + ~1 hour live indicator + amber/green icon CSS. Single PR in `audit_dashboard/template.html` + `audit_trail/dashboard_generator.py`.

---

## Sequencing recommendation

1. **Item 1 first.** Without populated feed-membership flags, we can't *measure* the effect of the Guide band (item 2) or anything else downstream. Stamping is load-bearing.
2. **Item 2 second.** Takes ~1-2 hours once item 1's data is flowing. Until then, just update the copy (minimum honest baseline) and defer the live indicator.
3. **Wait 7 days after item 1 ships** before deciding on band widening/deletion. Let the data speak.

---

## Open questions for peer review

The following are where I'm least confident in the approach. Please weigh in.

1. **Hybrid stamp vs single-point.** Is the complexity of "stamp at ingest + snapshot at close" justified, or is a one-time backfill + ingest-only stamp simpler for equivalent value?
2. **`at_issue_*` field naming.** Should the closed-pick snapshot use `at_issue_is_smart_pick` (verbose, parallel to `at_issue_trust_tier`) or a compact `as_issued` sub-object? The latter is cleaner but requires schema changes downstream.
3. **HC evaluator reuse.** `tools/hc_gates_python.py` was authored by Cursor as a Python mirror of the JS filter. Is it safe to call from the live sanitation path, or does it have performance characteristics (e.g. JSON reloads) that make it unsuitable?
4. **Guide band deletion threshold.** 7 days, 30 days, or some stat-based trigger (e.g., "delete if n < 10 after 30 days OR if widening to [0.7, 0.95] would still yield n < 20")?
5. **Live-indicator semantics.** Should the dashboard render a warning icon for *every* Guide-documented filter with insufficient sample, or only for the currently-promoted ones?

---

## Cross-references

- `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md` — finding that Guide band has n=0
- `docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md` — #2 schema field recommendation
- `docs/AUDIT_DATA_PIPELINE_GAP_CHECKS_2026_04_20.md` — feed audit methodology
- `tools/hc_gates_python.py` — Cursor's HC evaluator Python mirror
- `audit_trail/stamp_pick_quality.py` — existing at-issue stamping precedent (trust_tier, strat_fwd_wr)
- `alpha_engine/feed_hygiene.py` — current canonical sanitation choke point

Commits: `faba0b66a` (schema expansion), `534269141` (claude_gainer_st demote), `cb54fee16` (Phase A), `75e41adc4` (Phase B).
