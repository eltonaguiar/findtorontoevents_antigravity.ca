# 2026-11-15 — forward-test clock panel on the audit dashboard

Progress toward a forward-test verdict existed only inside `forward_tracker.py status`. Anyone reading
the dashboard could see that a strategy was registered, but not how far it was from a verdict, which
look the next decision comes at, or what the boundary is at that look.

## What shipped

| File | Role |
|---|---|
| `tools/build_forward_clock.py` | Builds `audit_dashboard/data/forward_clock.json` |
| `audit_dashboard/forward_clock.js` | Renders the panel into `#forward-clock-body` |
| `audit_dashboard/template.html`, `index.html` | Panel section + script tag (source of truth is the template; the generator rebuilds index from it) |
| `tools/deploy_audit_files.py` | `audit_js` row + `audit_data` row |
| `.github/workflows/forward-ledger-sync.yml` | Rebuilds the JSON after each sync; may commit only the ledger + this file |

The panel shows, per pre-registered strategy: trades admitted, windows against the registered sample
target with a progress bar, the next scheduled look, observed z against that look's O'Brien-Fleming
boundary, the mean hold, the verdict from `decide()`, and the prior **labelled in-sample**.

## The design decision that matters

**The panel contains no verdict logic.** `build_forward_clock.py` imports `decide()` and
`interim_verdict()` from `forward_tracker.py` and serialises their output. It computes nothing itself.

The alternative — reimplementing the thresholds in JavaScript — is how a dashboard starts disagreeing
with its own tool. The person reading the page trusts the page; the tool would be right and silent. One
source of truth, or none.

Zero progress is rendered as an **explanation**, not an empty bar:

> Nothing has been admitted yet. That is the pre-registration guard working, not a failure: picks that
> closed before a strategy was registered are excluded by construction.

An empty progress bar reads as "failing". A sentence reads as what it is. Same reasoning as the excess
column rendering `—` instead of a fabricated `0.00`.

Failure to load the JSON says so (`Forward clock unavailable: …`) rather than showing an empty clock,
because an empty clock would also read as "0 progress".

## Two bugs caught during the build

1. **The panel would have fabricated zeros.** The first `interim_verdict()` test rows carried no
   notional, so `_endpoint()` divided by zero and returned `0.0pp` for every row — which made a strong
   synthetic series score `z = 0.00` instead of promoting. Fixed in the selftest fixture (rows now carry
   `notional_usd`); the production path was already guarded by `if notional else 0.0`, but the *test*
   would have passed a broken implementation.
2. **Achieved alpha jittered** (0.0494 vs 0.0507 for the same solved C) because the crossing tail used a
   step mask, so moving the bisection boundary across a grid node changed the sum. `_tail()` interpolates
   inside the crossing cell; the result is now stable at **0.05000** with **C = 1.7077** and boundaries
   **4.21 / 2.98 / 2.11 / 1.71**.

## Verification

| Check | Result |
|---|---|
| `build_forward_clock.py` on the real plan | 4 strategies, 0 ledger rows, 0/152 windows |
| Payload assertions | `rs-breakout-scout`: target 152, next look 25, endpoint `excess_pp`, prior flagged in-sample |
| `node --check forward_clock.js` | syntax OK (working copy and committed blob) |
| Template / index wiring | exactly 1 script tag, exactly 1 section each; excess column intact |
| Deploy list | both rows present (2 sources + 2 URLs) |
| Workflow | parses; clock-build step present; old single-path assertion **removed**; allow-list present |
| Panel section placement | precedes the footer nav in the committed template |
| Diff guards | template +7/−0, index +7/−0, deploy +2/−0, AGENTS.md +1/−0 |

## Limits

- **Not visually verified.** No browser was opened: the checks are JS syntax, payload assertions, DOM-id
  presence, and script/ordering wiring. How the panel actually paints is unconfirmed.
- **Not deployed.** The panel appears on `/audit` only after this merges and `audit-dashboard.yml`
  uploads the new HTML/JS/JSON. Until then the section renders its "Loading…" placeholder on the old
  uploaded copy — which does not have the section at all, so nothing breaks, nothing shows.
- **The ledger is empty**, so every bar is honestly at 0 and the panel shows the explanation banner.
  That is the correct state, not a bug.
- The workflow that refreshes the JSON only runs on the default branch; it has never executed.
