# Stash integration commentary — 2026-04-22

**Purpose:** 18 stashes had accumulated locally over the past ~8 days (stash@{0}-{17}). This document records which changes were integrated, which were rejected, and why.

**Result:** 4 files integrated cleanly, 2 files rejected, stash@{0} kept for later surgical merge, stashes {1}-{17} left untouched (all predate significant main rewrites; re-applying would revert shipped fixes).

---

## Integrated into `main`

### 1. `docs/REHAB_AND_MUTATION_AUDIT_2026_04_22.md`
**Origin:** stash@{0} untracked file
**Action:** UTF-16 → UTF-8 conversion (the file arrived with a UTF-16 BOM + wide-char encoding from a Windows editor that's incompatible with the rest of the UTF-8 repo). Re-saved with `newline='\n'` for cross-platform cleanliness.
**Value:** Directly addresses the user's earlier request — "review the disabled symbol-strategy, and ensure they are still tracked so they have a chance to recover if they perform well... similarly checking for inverse strategies and using DNA mutations." The doc is a rehab-matrix tracking every retired/paper-flagged strategy against whether inverse + DNA-mutation tests were run per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
**Risk:** None — pure documentation.

### 2. `docs/WEEKLY_REVIEW_ACTIONABLE_2026_04_22.md`
**Origin:** stash@{0} untracked file
**Action:** None needed (clean UTF-8).
**Value:** Weekly review of candidate blocks across docs + updates + git history vs current `alpha_engine/strategy_blocklist.py`. Bridges the gap between `perf-review/` cycle PRs and actual blocklist additions.
**Risk:** None — pure documentation.

### 3. `updates/2026-04-21-eventbrite-dating-misclassification-fix.md`
**Origin:** stash@{0} untracked file
**Action:** None needed.
**Value:** User-facing record of a site-content classification fix (Eventbrite social-media-graphics course was showing under "Dating" category). Important for the `/updates` feed which is public.
**Risk:** None — pure content documentation.

### 4. `tools/block_bootstrap.py`
**Origin:** stash@{0} untracked file — **NEW tool** (distinct from existing `tools/block_bootstrap_ci.py`; this one uses `CircularBlockBootstrap` instead of `StationaryBootstrap`).
**Action:** **Portability fix applied** — replaced hardcoded `ROOT = r"c:\findtorontoevents_antigravity.ca"` with `ROOT = str(Path(__file__).resolve().parents[1])`. The hardcoded Windows path would have broken CI (Linux runners) and any non-Windows dev environment.
**Value:** Cross-strategy bootstrap CIs on HC / Smart Picks / Verified Alpha / per-asset-class slices using `arch.CircularBlockBootstrap` — complements the existing `StationaryBootstrap` tool and lets us cross-check block-method choice (Hansen-Politis-White theory predicts similar CIs when block size is well-chosen).
**Risk:** Low — additive tool, no hot-path writes.

---

## Rejected (dropped from integration)

### 5. `updates/2026-04-22-quant-libraries-integration.md` (rejected)
**Reason:** Redundant with `updates/2026-04-20-quant-libraries-integration.md` already on main (shipped in commit `2721ab565`). The 04-22 version is shorter (56 vs 158 lines), lower-detail, and carries no new empirical results. Dropping avoids two near-duplicate `/updates` entries misleading readers.

### 6. `updates/2026-04-22-deep-strategy-investigation-implementation.md` (rejected — **important**)
**Reason:** The doc claims three changes from the deep-strategy-investigation are now implemented:
1. TOD gate extended to `8,9,10,11,16,17,18,19,20`
2. Confidence ≥ 0.80 deprecated as HC gate
3. (Third change per its content)

**But none of these are on `main`.** Live code at `audit_trail/quality_gates.py:3658` still has `PHASE1_TOD_GATE_HOURS = "8,9,10,11"`. These changes live in PR #294, which I held per peer review (unvalidated — the PR's own blueprint explicitly lists "forward validate" as deferred work).

Shipping this update would create a **trust-leak** on `/updates` — users reading it would believe the gates were tightened when the code didn't change. Dropped. PR #294 remains the tracking artifact.

---

## Deferred — `stash@{0}` refactors of existing tools

stash@{0} also modifies three already-tracked files that cannot be cleanly merged:

| File | Change | Why deferred |
|---|---|---|
| `tools/deflated_sharpe.py` | stdlib-only (255 lines) → pandas + scipy + `feed_membership` import (123 lines) | Hardcoded `ROOT = r"c:\findtorontoevents_antigravity.ca"` same portability bug as `block_bootstrap.py`. Also loses the stdlib-only fallback elegance. Needs surgical merge: fix ROOT + verify no regression against the shipped per-feed DSR output. |
| `tools/walk_forward_validation.py` | pure-numpy (174 lines) → pandas + skfolio `WalkForward`/`CombinatorialPurgedCV` (132 lines) | Same portability issue + verification that CombinatorialPurgedCV output schema matches the existing `walk_forward_results_2026_04_20.json` consumers. |
| `audit_trail/quality_gates.py` | Adds `non_crypto_consensus` to `PERMANENTLY_KILLED_STRATEGIES` + clarifies `_SOURCE_SYSTEM_SCORES` / `_STRATEGY_SCORES` supersession | **This one is safe** — clean consolidation. But it would conflict against recent main edits in adjacent regions. Re-apply as a fresh focused commit rather than via stash pop. |

**Decision:** stash@{0} kept as-is. Surgical merge of the safe `quality_gates.py` portion (add `non_crypto_consensus` to `PERMANENTLY_KILLED_STRATEGIES`) will be a separate commit; the tool refactors defer to a focused PR with portability fixes + parity test against current outputs.

---

## Stashes {1}-{17} — audit & decision

| Stash | Base commit era | Verdict |
|---|---|---|
| {1} | `41a79c2c1` (blocklist syntax fix, 2026-04-20) | Obsolete — predates today's rewrites |
| {2} | `dc875fa80` (site health audit, 2026-04-20) | Obsolete — follow-up shipped |
| {3} | `97f511e53` (score calibration) | Obsolete — calibration doc shipped |
| {4} | `99f11db77` (feed_hygiene composite block) | Obsolete — composite block live via `0b2f5d01b` |
| {5} | `e435fc1bf` (Mercury enhancements) | Obsolete — Mercury enhancements live |
| {6} | `852c2b789` (loss-driver analyzer) | Obsolete — analyzer shipped |
| {7}-{8} | baby-strategies branches | Obsolete — PRs closed/merged |
| {9} | playbook split | Obsolete — playbook on main |
| {10} | `hotfix/esc-undefined-audit-crash` | Obsolete — crash fixed |
| {11}-{12} | Battle Test / forward-test cycles | Ephemeral automation state |
| {13}-{16} | hyrotrader pipeline fixes | Obsolete — pipeline fixes merged |
| {17} | `copilot/enhance-prediction-strategies` | Obsolete — Copilot PR closed/superseded |

**Not popped.** Every stash {1}-{17} is from a base commit that has since been heavily rewritten; popping any of them would risk silently reverting live fixes (blocklist entries, force-demotes, Phase A/B scoring, Phase 1 stamping). Safer to drop them after one more eyes-on pass.

---

## Summary

- **4 files** integrated into main via this session's cleanup
- **2 files** dropped (duplicate + trust-leak risk)
- **1 stash** ({0}) kept open for surgical merge of the `quality_gates.py` PERMANENTLY_KILLED addition + portability-fixed tool refactors
- **17 older stashes** {1}-{17} flagged as obsolete; recommend `git stash drop` after confirming no surprise holds

The key lesson from this integration pass: hardcoded Windows paths in `tools/` scripts are a recurring drift pattern. Every new `tools/*.py` should start with `ROOT = str(Path(__file__).resolve().parents[1])`. A `conftest.py` helper or pre-commit hook could enforce this.
