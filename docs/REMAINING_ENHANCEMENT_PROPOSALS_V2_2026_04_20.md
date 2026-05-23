# Proposed approach v2 — remaining /audit enhancement items (2026-04-20)

**Supersedes:** [`REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md`](REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md) (v1).

**Status:** revised after peer review. Two independent reviewers (engineer-lens + product-lens) identified substantive flaws in v1. This document incorporates their feedback.

## Summary of v1 flaws

1. **Wrong layer for stamping.** v1 wired `stamp_feed_membership` into `feed_hygiene.sanitize_active_picks`, a filter/normalizer whose job is rejecting bad rows. That conflates concerns, risks circular imports (feed_hygiene → audit_trail), and fires at N concurrent scanner ingests rather than a single serialized choke point.
2. **`setdefault` propagates stale stamps.** Upstream scanners can hand-set `is_smart_pick=true` on a pick that fails the current gate; `setdefault` preserves the lie forever. Opposite of the overwriting semantics `stamp_pick_quality.py` already uses for `trust_tier`.
3. **Ordering bug.** `is_smart_pick` depends on `trust_tier`, which is stamped *after* feed_hygiene in the pipeline. Ingest-time stamping would evaluate against the previous cycle's trust_tier — silently wrong.
4. **Concurrency.** Multiple scanners evaluating rolling-WR gates microseconds apart against different in-memory snapshots will stamp the same symbol inconsistently.
5. **v1 sequencing optimizes infrastructure over user experience.** Item 1 is internal tooling with zero user-facing benefit; users are being misled *right now* by the n=0 Guide band and the absence of "trust HC first" framing.
6. **n<10 cliff** for Guide band activation is arbitrary; should be a Wilson lower bound on the WR.
7. **hc_gates_python provenance** (Cursor-authored mirror of the JS filter) deserves a parity-test against the live JS evaluator before being wired into any hot path.

---

## Revised approach

### Phase 0 — Ship the user-facing banner TODAY (~30 min)

Before any stamping infrastructure. Addresses the "no one is telling users the real story" product gap.

Add three pieces to `audit_dashboard/template.html`:

**(a) Top-of-page status banner.** Auto-populated from `dashboard_data.json` aggregates:
> Aggregate PF *0.76* reflects legacy strategies now blocked. Active logic (post-block) PF ~*1.10*. **High Conviction tier** PF *1.61* (n=*62*) — most reliable feed. [Learn more](#guide).

The three numbers should re-compute at dashboard-generator time via a small helper in `audit_trail/dashboard_generator.py`. Banner hides if any of the three is unavailable.

**(b) Tier-trust legend** near the feed tabs:
> - 🟢 **High Conviction** — strongest realized edge (~PF 1.6)
> - 🔵 **Smart Picks** — passes strict per-asset gates
> - 🟡 **Verified Alpha** — mixed — check sub-cohort
> - ⚪ **Active / Open** — all live picks

**(c) Hide the n=0 Guide band** (`PROVEN + confidence 0.8-0.9`) until it populates. Simpler than "insufficient sample" copy — user doesn't have to reason about statistical power to trade the dashboard.

Ship as a single PR, `audit_dashboard/template.html` only. No schema work, no new modules.

### Phase 1 — At-issue stamping (v2, internal tooling, 1-week track)

**Move stamping to `stamp_pick_quality.py`**, which is:
- Already a sibling pipeline step (not concurrent with ingest)
- Already runs *after* `trust_tier` is stamped (correct ordering for `is_smart_pick` which depends on trust)
- Already uses overwriting semantics (not `setdefault` — fixes stale-stamp bug)
- Already the precedent for `at_issue_*` twin fields

Add one function: `stamp_feed_membership(pick, at_issue: bool)`:
```python
def stamp_feed_membership(pick: dict, at_issue: bool = False) -> None:
    """Stamp is_smart_pick, is_verified_alpha, hc_tier on a pick.
    
    If at_issue=True, also writes at_issue_is_smart_pick, at_issue_hc_tier
    for closed-pick historical preservation.
    """
    is_sp = bool(passes_smart_gate(pick))
    pick["is_smart_pick"] = is_sp
    pick["is_verified_alpha"] = (
        pick.get("trust_tier") == "PROVEN"
        and pick.get("source_system") in VERIFIED_ALPHA_SOURCES
    )
    pick["hc_tier"] = evaluate_hc_tier(pick)
    if at_issue:
        pick["at_issue_is_smart_pick"] = pick["is_smart_pick"]
        pick["at_issue_is_verified_alpha"] = pick["is_verified_alpha"]
        pick["at_issue_hc_tier"] = pick["hc_tier"]
```

Call from two places inside `stamp_picks()`:
1. On every pass — updates live flags to match current gate state (overwriting).
2. When a pick transitions ACTIVE → CLOSED (detected via `status` + absence of `at_issue_*`) — snapshots the `at_issue_*` twins exactly once.

### Phase 2 — Backfill + live n-indicator (1-week track, scoped)

**Backfill script** `tools/backfill_feed_membership.py` runs once against the 3500-row `recent_closed`. Evaluates each pick against gate state at time of close (approximated using `at_issue_trust_tier` / `at_issue_strat_fwd_wr` if present, else current state). Writes `is_*` + `at_issue_is_*` fields. Without this, Phase 0 banner's n=62 stat for HC is correct but retrospective counterfactuals on Smart Picks / Verified Alpha cohorts remain impossible.

**Live n-indicator** for the Guide overlay (if we don't hide the band entirely):
- Compute `wilson_lb(wins, n, 0.95)` on matching closes.
- Display band only if `wilson_lb >= 0.45` AND `n >= 20`. Otherwise hide.
- No amber/green cluttery icons (per product reviewer).

### Phase 3 — Parity-test hc_gates_python (0.5 day, gating Phase 1-2)

Before wiring `tools/hc_gates_python.py` into production stamping, run a parity test:
- Feed last 500 closed picks through the Python evaluator
- Compare to the JS `hc_filter.js` result via headless browser or a Node runner
- Fail gate if any pick classified differently

If parity breaks, stamp directly from `passes_smart_gate` + server-side HC predicate rather than reusing the Cursor mirror.

---

## Sequencing (revised)

| Phase | Effort | User visible? | Ship order |
|---|---|---|---|
| 0 — Banner + legend + hide n=0 band | ~30 min | **YES (today)** | 1 |
| 3 — HC evaluator parity test | 0.5 day | No (gating) | 2 |
| 1 — Stamping in stamp_pick_quality | ~3 hours | No | 3 |
| 2 — Backfill + Wilson-LB live indicator | ~1 day | Partial | 4 |

Phase 0 alone closes the "users are being misled today" gap. The remaining three enable retroactive analytics, which is valuable but not user-visible.

---

## Decision needed

Both reviews converge on: **ship Phase 0 today; treat Phases 1-3 as internal tooling with no urgency**. The v1 proposal had it backwards.

Questions I still want feedback on:
1. Is the three-number banner framing honest, or does it over-promise? ("PF 1.61 on n=62" is a real edge, but a naive user might mistake it for a guarantee.)
2. Should the Guide band be **hidden** or **shown with Wilson-LB gate**? Hidden is simpler; shown with a gate is more transparent. Product reviewer preferred hidden.
3. If we hide the n=0 band, do we need a `audit_dashboard/GUIDE_ARCHIVE.md` entry so the spec isn't lost?

---

## Reviewer attribution

- **Engineer-lens reviewer** caught: wrong layer, `setdefault` stale propagation, ordering bug, concurrency, Wilson-LB vs cliff, hc_gates_python provenance, plus 5 additional missed questions (paper_trade writer, backfill policy, ordering vs stamp_pick_quality, test fixture breakage, rollback feature flag).
- **Product-lens reviewer** caught: wrong sequencing, item 1 has no user-facing win, cleaner MVP exists in 30 min, amber/green icons are clutter, users want signal not epistemics.

Both reviews are incorporated. v2 is the merge.

---

## Cross-references

- v1 proposal: `docs/REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md`
- `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md` — HC PF 1.61, aggregate PF 0.76
- `docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md` — blocklist-leakage flip
- `audit_trail/stamp_pick_quality.py` — target pipeline step for Phase 1
- `audit_dashboard/template.html` — target for Phase 0
- `tools/hc_gates_python.py` — to be parity-tested in Phase 3
