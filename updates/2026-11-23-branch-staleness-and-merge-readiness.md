# Branch staleness diagnosis + merge-readiness (vanilla-handsaw)

**Date:** 2026-11-23T06:59Z · **Author:** Kilo.

## What I found running the broader regression set
Running 118 tests across `audit3_*`, `selection_alpha`, `pod_emission`, `assert_surface_parity`, `resolved_closed_view`
and `verification_tools`: **114 passed, 4 failed**. The 4 failures are in
`test_selection_alpha_coverage.py` (by_class/by_slice/bar_coverage) and `test_audit3_falsifiers.py`.

**Cause: this branch is stale, not my edits.**
- `git rev-list --left-right --count origin/main...HEAD` → **7,133 behind / 87 ahead**.
- `origin/main`'s `ALPHA_PASSTHROUGH_KEYS` includes `by_class, by_slice, by_strategy, bar_coverage` (and a `pf_basis`
  import); **this branch's copy predates all of them**. So the 4 tests assert features that exist only on main.
- My only edit to `audit3_tribunal.py` is the additive `compounded_max_drawdown` helper + one return-dict key.

## Merge-readiness of my drawdown change
Cherry-picked `ca011dbc182` onto a throwaway worktree at **origin/main**:
- **auto-merged, zero conflicts**;
- **`pytest tests/test_audit3_tribunal.py` → 38 passed on main**;
- `compounded_max_drawdown([50,-50]) == 50.0` (correct);
- temp worktree removed, nothing pushed.

## Recommendation
My additive changes are merge-safe onto current main. The 4 local failures will disappear once the branch is rebased
onto main (they are main-only features). **Do not chase those 4 as bugs** — they are a staleness artifact. The clean path
to land my work: fresh branch from `origin/main`, cherry-pick the additive commits (drawdown, tools, reports, docs);
the stale-base merge is the only thing that carries risk, and it is avoidable.

*Paper only. Not investment advice.*
