# 2026-06-22 — CLI tightenings: exit-code-2 path, derive `display`, `known_marker_bearers` slice

## What this doc is

Three small ratchet improvements to `tools/sync_dark_audit_sidecar_scan.py`
applied on 2026-06-22 (same day as initial release in
`updates/2026-06-22-sync-dark-audit-sidecar-scan-cli.md`).

Each tightening is ~5-15 min and isolated; verification was run end-to-end
after all 3 were applied.

## The 3 tightenings

### 1. Exit-code-2 path properly wired

**Before:** `main()` returned 1 for any FAIL or any scanner-self-error
state (UNPARSEABLE sidecar JSON, TIMEOUT pytest subprocess, OS_ERROR on
subprocess). The docstring claimed exit 2 for "scan itself errored" but the
code never returned 2.

**After:** Hoisted `n_scan_error` counter in `main()` BEFORE the
n_fail/n_cron_hard_fail resolution. Counts roll up directly from Section A
(`state == "UNPARSEABLE"`) + Section C (`state in ("TIMEOUT", "OS_ERROR")`)
— bypassing `cross_ref` so a SCAN_ERROR is never silently obscured as a
FAIL. Resolution order is now explicit:

```
  2  scanner self-broken (UNPARSEABLE / TIMEOUT / OS_ERROR)
  1  contract discipline violation (FAIL) OR cron-sidecar MISSING_CRON_HARD_FAIL
  0  all green
```

### 2. `display` key derived from `name` (single source of truth)

**Before:** Each of the 7 contract entries in `_build_contracts()` had BOTH
a `name` (snake_case: `operator_review_today`, `winner_hunt_replay`, ...)
AND a hand-typed `display` (kebab-case: `operator-review-today`,
`winner-hunt-replay`, ...). Every display was the kebab-case
transformation of the name — pure duplication.

**After:** Dropped the `display` key from all 7 manifest entries. `_cross_ref`
derives display via `contract["name"].replace("_", "-")` — one source of
truth. Verified that the resulting display equals the previous hand-typed
value for ALL 7 contracts, including `btc_scalping_investigation` which had
no alt-kebab complication.

Net change: -7 manifest lines, +1 derivation in `_cross_ref`.

### 3. `known_marker_bearers` slice in JSON envelope

**Before:** `--json` output sections A/B/C/D + global_summary. No way for
CI to enumerate the WHITELIST (files that DO carry the allow-marker for a
contract) — only the BLACKLIST (unguarded readers) was surfaced.

**After:** New function `_marker_bearers_for(contract)` mirrors
`_reader_scan_for` but produces the whitelist. Walks the same SCAN_ROOTS +
exempt rules, but does NOT require sidecar-filename match — this is
intentional, since a refactor that moves the load site should NOT silently
delete the marker comment.

Threaded into `main()` via the existing ThreadPoolExecutor (alongside
A/B/C). New optional kwarg `_render_json(..., known_marker_bearers=None)`
adds three new keys to the envelope:

- `known_marker_bearers: [{"contract": "...", "marker_bearers": [...], "bearer_count": N}, ...]`
- `global_summary.scan_errors: N`              (Section A UNPARSEABLE + Section C TIMEOUT/OS_ERROR)
- `global_summary.marker_bearer_total: N`      (sum of `bearer_count` across contracts)

Note: `marker_bearers` is broader than "consumers with markers" — it captures
ANY file in `tools/ + audit_trail/ + alpha_engine/` whose source matches
the allow-marker regex, regardless of whether it currently consumes the
sidecar. This is a "review-time discovery" signal, not a "consumer floor"
assertion. See Cleanup #1 in the reviewer notes below for a future
sharpening if a CI consumer needs a tighter semantic.

## Verification (run after all 3 edits applied)

```
=== A. py_compile ===
  sync_dark_audit_sidecar_scan.py: OK

=== C. default text-mode run ===
... 7 contracts [ OK ] / 0 unguarded readers / 0 fail ...
EXIT_DEFAULT=0

=== D. JSON mode (verifies new keys) ===
known_marker_bearers count: 7
global_summary: {"fail": 0, "marker_bearer_total": 12, "missing": 0,
                  "ok": 7, "scan_errors": 0, "total": 7}
  operator_review_today:      0 bearers
  winner_hunt_replay:         2 bearers
  audit_surface_truth:        1 bearers
  anti_overfit_audit:         2 bearers
  blacklist_reconciliation:   2 bearers
  blocked_registry:           1 bearers
  btc_scalping_investigation: 4 bearers

=== E. --contract winner_hunt_replay - scope retains shape ===
contracts in D: 1
known_marker_bearers: [{'contract': 'winner_hunt_replay',
                        'marker_bearers': ['audit_trail/winner_hunt_replay.py',
                                            'tools/winner_hunt_replay_dashboard.py'],
                        'bearer_count': 2}]

=== F. --contract bogus - still exit 2 ===
Unknown contract: this_does_not_exist. Available: [...7 names...]
EXIT_BOGUS=2

=== G. display fields render correctly (derived from name) ===
audit-surface-truth     /  anti-overfit-audit     /  winner-hunt-replay ...
```

## Reviewer verdict (`code-reviewer-minimax-m3`)

**Shippable.** Five minor cleanups, none blocker:

1. `_marker_bearers_for` doesn't require sidecar-filename match → potential
   false positives in `marker_bearers` (file with marker in docstring but
   no consumer role). Rename envelope key from `known_marker_bearers` to
   `marker_mentions` (or `marker_bearer_files`) to reflect actual semantics.
2. `_render_json`'s `Optional[list] = None` default for
   `known_marker_bearers` is dead-code defensive. Drop `Optional` + default;
   make required positional.
3. Exit-2 docstring says "scan itself errored" but UNPARSEABLE is currently
   routed through it — UNPARSEABLE is data-side corruption, not strictly
   scanner-self-broken. Either split into `SCAN_READ_ERROR` vs UNPARSEABLE
   (behavior change) or add 1-paragraph docstring clarification. Recommend
   doc-only clarification for scope reasons.
4. `name.replace("_", "-")` slightly opaque — add `_display_for(name)` helper
   for explicitness + future assertion anchor. Marginal; leave as-is unless
   a non-snake_case contract name is added later.
5. `global_summary.marker_bearer_total` sums across all contracts unconditionally.
   Consider also exposing `global_summary.bearers_by_contract` for one-line
   floor-check assertions. Low priority.

## Files touched

- `tools/sync_dark_audit_sidecar_scan.py`: +30 / -10 (net +20 lines).
  - `_build_contracts()`: removed 7 `display` keys.
  - `_cross_ref()`: derives display via `.replace`.
  - new `_marker_bearers_for()` function after `_reader_scan_for()`.
  - `main()`: hoist `n_scan_error` counter; wired `_marker_bearers_for`
    into parallel pool; pass sorted `marker_bearers` into `_render_json`.
  - `_render_json()`: new optional `known_marker_bearers` kwarg; envelope
    gets 3 new keys.

No new files dropped under `tools/` (the script is self-contained).

## Re-run trigger

All previously-documented exit-code-0 / exit-1 behavior unchanged.
`tools/sync_dark_audit_sidecar_scan.py` exits 2 only when:

- a sidecar on disk fails `json.JSONDecodeError` (Section A), OR
- a pytest subprocess times out (Section C, `--timeout` exceeded), OR
- a pytest subprocess raises `OSError` (Section C, e.g., `python3` not on PATH).

If none of those conditions fire, exit code stays at 0/1 per the prior
behavior.
