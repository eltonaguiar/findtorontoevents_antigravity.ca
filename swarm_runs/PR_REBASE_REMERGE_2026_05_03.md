# PR #723 + #724 — Rebase + Re-merge Attempt

**Date:** 2026-05-03 (post-19:11Z race)
**Operator authorization:** confirmed
**Working dir:** `e:\findtorontoevents_antigravity.ca`
**Cost:** $0 (no swarm calls)

---

## Summary

| PR | Pre-action | Action | Post-action | Final verdict |
|----|------------|--------|-------------|---------------|
| #723 | DIRTY / CONFLICTING | API rebase failed → local rebase → SEMANTIC CONFLICT | rebase aborted, branch unchanged | **BLOCKED — operator decision required** |
| #724 | DIRTY / CONFLICTING | API rebase failed → local rebase → SEMANTIC CONFLICT | rebase aborted, branch unchanged | **BLOCKED — operator decision required** |

**Merges executed: 0**
**PR final states: both still OPEN with mergeStateStatus=DIRTY**

Both PRs hit **real semantic conflicts** (not mechanical), per task instructions both were aborted rather than blindly resolved. Both branches are restored to their original origin tips (no force pushes, no destructive ops).

---

## PR #723 — B18 Shadow-Mode Auto-Promotion

### Pre-action state
- `mergeable`: CONFLICTING
- `mergeStateStatus`: DIRTY
- `headRefName`: `feat/b18-shadow-promote-v2-2026-05-03`
- `additions`: 456, `changedFiles`: 8
- `statusCheckRollup`: empty (no CI runs queued — may need re-trigger)
- 2 commits ahead of `origin/main`:
  - `a223e720fe4` chore(loop): mark V3-V7 re-verified; B17/B2/B11/B14 merged; add B18 ready
  - `2853dd10031` feat(B18): shadow-mode auto-promotion for zero-closed-history strategies

### Action taken
1. `gh pr update-branch 723 --rebase` → **failed**: "Cannot update PR branch due to conflicts"
2. Fell through to local rebase:
   - `git checkout -B feat/b18-shadow-promote-v2-2026-05-03 origin/feat/b18-shadow-promote-v2-2026-05-03`
   - `git rebase origin/main`
3. First commit (`a223e720fe4`) rebased cleanly.
4. Second commit (`2853dd10031`) hit 4 conflicts:
   - `reports/feedback/B18-claude-sonnet-self-review-2026-05-03.md` — add/add
   - `reports/feedback/B18-codebuff-proxy-self-review-2026-05-03.md` — add/add
   - `tools/dashboard_hc_rules.py` — content
   - `updates/2026-05-03-b18-shadow-promote.md` — add/add
5. **`git rebase --abort`** invoked.

### Why aborted (semantic, not mechanical)
PR #719 (`66c97f96936` — "feat(gates+audit): B18 — shadow-mode auto-promotion for zero-history strategies (default-OFF)") **already merged the same B18 feature on 2026-05-03 03:19Z** with a **different function signature**:

```python
# Already on main (PR #719):
def should_shadow_promote(strategy, raw_emit_count, closed_count) -> bool:  # 3 positional

# PR #723 wants to add:
def should_shadow_promote(
    source_key, strat_closed_n, strat_raw_n, current_shadow_count,
    *, min_raw=10, max_shadow=5,
) -> bool:  # 4 positional + 2 kwargs
```

The two implementations also differ in:
- Constants location (`_SHADOW_*` module-level vs. function defaults)
- Caller wiring (PR #723 adds an explicit shadow_mode bypass at the top of `passes_active_gate`; main has the bypass in different form)
- Field names in `picks.shadow_probation` payload

The conflict files also diverge: both PRs ship `B18-claude-sonnet-self-review-2026-05-03.md` and `B18-codebuff-proxy-self-review-2026-05-03.md` with **completely different content** (different reviewers, different verdicts, different prose).

**This is functional duplication, not a mechanical merge.** PR #723's "v2" suffix in the branch name suggests the author knew #719 was the v1; v2 may have intentional refinements that need a human to reconcile.

### Post-action state
- Local branch deleted then re-checked-out fresh from origin tip → no local divergence.
- Remote branch unchanged (no force-push performed).
- `mergeStateStatus` will remain DIRTY until operator decides:
  1. **Close #723 as superseded by #719** (if v2's signature change is not desired), OR
  2. **Manually rebase v2 conflicts** keeping v2's signature + accept review-doc divergence (operator chooses which review doc set wins), OR
  3. **Open follow-up PR** that lands only the *delta* from #723 vs the already-merged #719.

### Final verdict
**BLOCKED — operator decision required.** Recommend closing #723 as superseded unless v2's expanded signature (`current_shadow_count` cap, kwargs) is the intended forward path.

---

## PR #724 — FOREX/Crypto Deep-Dive Reports

### Pre-action state
- `mergeable`: CONFLICTING
- `mergeStateStatus`: DIRTY
- `headRefName`: `investigation/forex-crypto-deep-dives-2026-05-03`
- `additions`: 1390, `changedFiles`: 6
- `statusCheckRollup`: 1 success (Conflict Marker Check at 03:52Z, pre-race)
- 3 commits ahead of `origin/main`:
  - `4345d6d1c9a` investigation(forex+crypto): deep-dive reports per CLAUDE.md Goal #1
  - `7d3ce505c38` investigation(forex): consolidated rescue plan + corruption-filter root cause + 5 new strategies
  - `e4cb5b4f043` Add asset-class recovery analysis plan

### Action taken
1. `gh pr update-branch 724 --rebase` → **failed**: "Cannot update PR branch due to conflicts"
2. Fell through to local rebase:
   - `git checkout -B investigation/forex-crypto-deep-dives-2026-05-03 origin/investigation/forex-crypto-deep-dives-2026-05-03`
   - `git rebase origin/main`
3. First two commits (`4345d6d1c9a`, `7d3ce505c38`) rebased cleanly — they only add new report files in `reports/` that don't conflict.
4. Third commit (`e4cb5b4f043`) hit 1 conflict on `FOREX_COMMODITIES_BONDS.MD` (add/add).
5. **`git rebase --abort`** invoked.

### Why aborted (semantic, not mechanical)
`FOREX_COMMODITIES_BONDS.MD` has a chaotic recent history — multiple authors writing competing rescue plans:

```
e6f9536aa5b Update remediation status: Phase 1-3 complete, Phase 4 pending
42c8b77cfaf Enhance FOREX_COMMODITIES_BONDS.MD: add KPI tables, owner/reviewer, model-risk framework, ...
a05a54d85a6 Add FOREX_COMMODITIES_BONDS.MD — asset class underperformance analysis and remediation plan
e4cb5b4f043 Add asset-class recovery analysis plan          ← PR #724
327b86e3bbc FOREX/COMMODITIES/BONDS recovery plan: comprehensive analysis and fix strategy
37b0ad72f2c Add FOREX_COMMODITIES_BONDS.MD: poor-performance autopsy + 30/60/90 fix plan
3cfce875519 Update forex commodities bonds recovery memo
26c35204493 docs(plan): add forex commodity bond recovery roadmap
f146c141e96 docs(plan): add forex commodity bond recovery roadmap
```

The version on `origin/main` is **1609 lines** (with KPI tables, model-risk SR 11-7 framework, governance, CI/CD checklist — looks like the most polished iteration). PR #724's version is **651 lines** (different structure — sections numbered 1–17 with table of contents, but skinnier content per section).

Both files are entirely different documents covering the same topic. Auto-resolution with `--theirs` or `--ours` would either **discard the polished governance doc on main** or **discard the structured PR #724 plan** — both are wrong without operator review.

### Important nuance
The first 2 commits of PR #724 are clean adds — only `e4cb5b4f043` (the 3rd) is the problem. This means the **valuable content of PR #724** (`reports/deep_dive_FOREX_2026_05_03.md`, `reports/deep_dive_CRYPTO_quan_unknown_drag_2026_05_03.md`, `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md`, `reports/forex_corrupt_filter_analysis_2026_05_03.md`, `reports/forex_new_strategies_2026_05_03.md`) **could be landed independently** by dropping `e4cb5b4f043` from the PR.

### Post-action state
- Local branch reset to fresh origin tip; no force-push.
- Remote branch unchanged.
- `mergeStateStatus` will remain DIRTY.

### Final verdict
**BLOCKED — operator decision required.** Recommendations (in preference order):
1. **Drop `e4cb5b4f043` from PR #724** (`git rebase -i origin/main` and delete that commit) — this lands the 5 high-value `reports/*.md` deep-dive files cleanly without the duplicate `FOREX_COMMODITIES_BONDS.MD`. Then `gh pr update-branch 724 --rebase` should succeed.
2. **Close #724 and open a smaller PR** with just the `reports/*.md` files.
3. **Manually merge** PR #724's `FOREX_COMMODITIES_BONDS.MD` into the polished main version (heavy human-author-decision work).

---

## Open queue

| PR | Status | Next step |
|----|--------|-----------|
| #723 | BLOCKED — semantic dup of #719 | Operator: close as superseded, OR cherry-pick the v2 signature delta into a follow-up PR |
| #724 | BLOCKED — competing FOREX_COMMODITIES_BONDS.MD authorship | Operator: rebase-drop `e4cb5b4f043` to land the clean 5 reports/, OR open a smaller PR |

Neither was force-pushed. Neither was closed. Both branches are bit-identical to their pre-action origin state.

---

## Notes

- Local working tree had `cherry-pick/max-hold-hours-by-class` checked out with WIP changes (`audit_trail/universal_pick_resolver.py`, `tests/test_universal_pick_resolver.py`, plus untracked `TV_PICKS_2026-05-03_17-05.md` and a few data-file modifications). All stashed and restored after the rebase attempts. Original WIP intact.
- API-rebase (`gh pr update-branch --rebase`) failed for both PRs immediately — GitHub's mechanical-only resolver cannot handle these conflict surfaces.
- No CI was triggered; no merges performed; no destructive ops executed.
