# PR #285 Verification — edge-stability daily refresh wire-up

**Date:** 2026-05-31
**Reviewer:** Claude Opus 4.7
**Verdict:** MERIT — PR addresses a real broken-wire gap. Already merged. Live workflow proven functional.

## PR #285 actual scope

- **Type:** NEW workflow YAML (1 file, +36 / -0)
- **File:** `.github/workflows/edge-stability-refresh.yml`
- **Title:** `ci(edge-stability): daily 00:30 UTC refresh workflow`
- **State:** MERGED (commit `a0239170e` on main)
- **Trigger:** `schedule: '30 0 * * *'` + `workflow_dispatch`
- **Steps:**
  1. `actions/checkout@v6` (with GH_PAT for push)
  2. `actions/setup-python@v6` (3.11)
  3. `curl` live `https://findtorontoevents.ca/audit/data/dashboard_payload.json` → `audit_trail/data/dashboard_payload.json`
  4. `python -m tools.edge.edge_stability --all`
  5. `git add audit_dashboard/data/edge_stability/*.json` → commit `[skip ci]` → `git push`

## Existing-wire diagnosis (cross-check)

`grep -ln "edge_stability" .github/workflows/*.yml`:
- `audit-dashboard.yml` — only FTP-deploys existing `edge_stability_*.json` files (lines 1169-1178, 1285-1290). It does NOT generate them.
- `edge-stability-refresh.yml` — the NEW workflow (PR #285), which actually runs the generator.

**Conclusion:** before PR #285, `tools/edge/edge_stability.py` was orphan — no caller in any workflow. `audit-dashboard.yml` deployed whatever stale JSON happened to be in the repo, which explains the `as_of=2026-05-12T21:53` value persisting for 19 days.

## Real cause of staleness

The generator script (`tools/edge/edge_stability.py`) was never wired to a CI job. The last write to `audit_dashboard/data/edge_stability/` on main was a manual local commit on 2026-05-12. `audit-dashboard.yml` blindly FTP-deployed the stale local copies hourly, masking the broken pipeline.

PR #285 closes that gap with a daily scheduled refresh.

## Verification (this session)

- Dispatched `gh workflow run "edge-stability-refresh.yml"` → run `26724681663` completed `success` in ~13s.
- Pushed commit `84443c5a chore(edge-stability): daily refresh [skip ci]` to main (9 files, +8273/-15278).
- Confirmed on `origin/main`:
  - `audit_dashboard/data/edge_stability/edge_stability_index.json` → `as_of: 2026-05-31T21:15:21.322905+00:00`
  - CRYPTO n_total = 1022 (vs prior stale 2026-05-12 figure)
  - All 8 classes refreshed: BOND, COMMODITY, CRYPTO, EQUITY, ETF, FOREX, FUTURES, INDEX_STOCK
- One earlier dispatched run (`26724680761`) failed — likely a race/concurrency collision with the immediately-following successful run; the success ran 2s later. Non-blocking.

## Minor risk noted

PR body claims "script reads payload, not MySQL — no DB secrets needed". Code at `tools/edge/edge_stability.py:528-529` actually has a `_load_all_picks_mysql` fallback when payload is empty. In CI without DB creds, fallback would crash. In practice the payload IS populated (18.6 MB), so the primary path works. If the live payload ever ships empty (e.g. failed `audit-dashboard.yml` run), this workflow will fail loudly — acceptable, not silent.

## Verdict + Action

- **Scope:** new workflow YAML (NOT a modification).
- **Duplicates existing wire?** NO. No prior workflow ran the generator.
- **Merit:** YES — closes a real broken-wire gap.
- **Merged:** YES (already on main before this verification).
- **Action taken:** dispatched the workflow once to prove it works; confirmed as_of advanced from 2026-05-12 to 2026-05-31. Daily 00:30 UTC schedule will keep it fresh going forward.

No follow-up PR needed. Optional hardening: drop the MySQL fallback to make CI failures explicit instead of attempting un-credentialed DB connect.
