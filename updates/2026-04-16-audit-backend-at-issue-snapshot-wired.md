# Validation: `at_issue_*` backend wiring (generator)

## What another agent may have meant

The UI and **`_CLOSED_PICK_KEEP_FIELDS`** already allowed **`at_issue_*`** on slim closed rows, but **`audit_trail/dashboard_generator.py` never populated those keys** before the leaderboard merge and trust enrich — only the **allowlist** existed. The intended behavior was documented in **`updates/2026-04-15-audit-trust-edge-lev-tooltips-closed-snapshot.md`** § Generator.

Without snapshots, Closed Picks **Trust / FWD WR / FWD N** delta columns mostly fell back to post-merge values only (no “at signal” baseline).

## What is wired now

- **`_snapshot_at_issue_for_recent_closed(..., pre_leaderboard=True)`** runs **immediately before** the `for pick in active + recent_closed` leaderboard merge: copies **`strat_fwd_wr` / `forward_wr`**, **`strat_fwd_trades` / `forward_trades`**, and any existing **`trust_score` / `trust_tier`** into **`at_issue_*`** when those targets are still missing.
- **`_snapshot_at_issue_for_recent_closed(..., pre_leaderboard=False)`** runs **after** that loop and **before** **`enrich_picks_with_trust_score(recent_closed)`**: fills missing **`at_issue_trust_*`** from the merged row’s **`trust_tier` / `trust_score`** (pre-enrich).

## Already correct (no duplicate backend work)

- **`compute_non_crypto_performance`**: uses **`nc_asset_category_for_pick`**, **`net_pnl_pct`**, **`_outcome_bucket_from_pnl`** — server aggregate was already aligned; the earlier client-only fix addressed **Ex-killed** recomputes over **`recent_closed`**, not this Python path.

## Verification

- `python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"`
- Next **`dashboard_data.json`** build (CI or local **`generate()`**) will emit closed rows with **`at_issue_*`** where source data allows.
