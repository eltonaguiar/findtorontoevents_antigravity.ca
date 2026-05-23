# 2026-04-30 — UEPS active_picks.json sync wired into runner workflow

## The bug

`tools/run_ueps_pickers.py` was designed (per its docstring) to write to
both:

1. `audit_dashboard/data/ueps_picks.json` — client-side dashboard feed.
2. `alpha_engine/data/active_picks.json` — shared execution ledger via
   `sync_to_active_picks()`.

But `.github/workflows/ueps-pick-runner.yml` only ran
`git add audit_dashboard/data/ueps_picks.json`. The second mutation was
silently discarded with the ephemeral runner FS at job end.

The workflow header comment even claimed: *"Does NOT mutate
alpha_engine/data/active_picks.json — separate dashboard feed."* That
comment contradicted the script's actual behavior — the sync ran in
memory, then the runner shut down without committing.

## Empirical baseline (2026-04-30, pre-fix)

```
audit_dashboard/data/ueps_picks.json: 30 fresh long_picks (generated 17:02 UTC)
alpha_engine/data/active_picks.json: 157 entries
  - ueps_-prefixed rows: 0
  - long_term_value pick_type: 0
```

Result: UEPS long-term equity picks never reached /audit's main active
table. They only appeared in the dedicated UEPS sidecar tab.

## The fix (one diff)

```diff
-      - name: Commit ueps_picks.json
+      - name: Commit ueps_picks.json + active_picks.json
         id: commit
         if: steps.run_pickers.outcome == 'success'
         continue-on-error: true
         env:
           TOKEN_FOR_PUSH: ${{ secrets.GH_PAT || github.token }}
         run: |
           git config user.name "github-actions[bot]"
           git config user.email "github-actions[bot]@users.noreply.github.com"
-          git add audit_dashboard/data/ueps_picks.json
+          git add audit_dashboard/data/ueps_picks.json \
+                  alpha_engine/data/active_picks.json
           if git diff --cached --quiet; then
             echo "No changes to commit"
           else
             TS=$(date -u +"%Y-%m-%d %H:%M UTC")
             N_LONG=$(...)
             N_SHORT=$(...)
-            git commit -m "data: ueps picks refresh - long=${N_LONG} short=${N_SHORT} (${TS}) [skip ci]"
+            git commit -m "data: ueps picks refresh + active_picks sync - long=${N_LONG} short=${N_SHORT} (${TS}) [skip ci]"
             bash .github/scripts/safe_push.sh
           fi
```

Plus the inverted header comment is rewritten to match reality.

## Concurrency safety

`active_picks.json` is also written by other crons (alpha-engine-live.yml,
etc.). With a naïve `git push` two concurrent commits would hit
non-fast-forward rejection. The workflow already uses
`bash .github/scripts/safe_push.sh` which retries with rebase — the same
mechanism every other auto-commit workflow uses to coexist. The
`sync_to_active_picks()` function in `tools/run_ueps_pickers.py` is
**insert-only** at the row level (existing entries with matching
`(symbol, source_system)` are preserved), so even when the rebase
re-runs, the merged state is convergent.

## Verification

After merge + first cron (next 4h-aligned slot 23:15 UTC etc):

1. `alpha_engine/data/active_picks.json` gains ~30 rows tagged
   `id` prefix `ueps_value_screener_*`, `pick_type=long_term_value`,
   `holding_horizon=3y+`.
2. `/audit` main active table shows EQUITY rows with these tags.
3. After PR #545's TF classifier patch already merged: those rows
   classify as POSITION via the `value_screener` system default →
   user's "TF=LONG term" complaint is resolved.

## Why this PR is independent of PR #545 / PR #546

- PR #545 added `value_screener` → POSITION as a system default in
  `cross_aggregation/timeframe_classifier.py`. That classifier mapping
  fires the moment any pick with `source_system="value_screener"`
  reaches `/audit` — but UEPS picks never reached `/audit` because of
  the workflow bug fixed by THIS PR.
- PR #546 wired the penny skyrocket detector (independent producer).
- PR #547 (this) finally puts UEPS picks on /audit's main table.

The three together close the gap the user originally flagged ("EQUITY
active picks have no LONG_TERM TF").

## Files

- `.github/workflows/ueps-pick-runner.yml` — header comment fix +
  `git add` extension (10 line delta net).
- `tests/test_ueps_active_sync_workflow.py` — new (6 tests).
- `updates/2026-04-30-ueps-active-sync-fix.md` — this doc.

## Risk: LOW

- Single-file workflow change.
- `sync_to_active_picks()` is insert-only — existing `active_picks.json`
  rows (157 from other emitters) are preserved.
- `safe_push.sh` retry-with-rebase already handles concurrent writes
  from `alpha-engine-live.yml` to the same file.
- If something does go wrong, rolling back is one-line removal of the
  second path from `git add`.

## Out of scope (deferred)

- Adding a `ueps` source to `JSON_PICK_SOURCES`. Not needed:
  `active_picks.json` is already loaded under the `alpha_engine`
  system at `JSON_PICK_SOURCES[0]`. UEPS rows ride on that path with
  their own `source_system="value_screener"` tag for attribution.
- Adding a new TF dropdown alias "LONG-TERM" — separate UI PR.
- Concept taxonomy for `pick_type=long_term_value` — Cursor Phase 1.
