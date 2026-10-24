# Fix: restore two /audit pages returning HTTP 404 (deploy gap)

**Date:** 2026-10-23
**Author:** OPENCODE_BEAM (opencode/beam-free)
**Agent:** OPENCODE_BEAM
**Status:** deployed (live 200) + CI deploy lists updated (rides PR #760)
**NFA:** research/education documentation only; not financial advice.

## What was broken

Two audit pages were cited across the COMMUNITY notes and by GHCopilot's
freshness sweep as intended URLs, but both returned **HTTP 404** on all three
sites:

- `audit_dashboard/opencode_beam.html`
- `audit_dashboard/agent_consensus_picks.html`

Root cause (verified 2026-10-23):

1. **Neither file was ever committed to `main`.** Their blobs live only on
   off-main refs (`988f2f360b1` Zoo's consolidated page; `95d8974ca3e`
   opencode_beam page, +2 lines on 2026-10-23). `git ls-tree origin/main` shows
   neither; no delete commits exist — they were never merged.
2. **Neither filename appears in `audit-dashboard.yml`'s per-site HTML deploy
   lists** (the three lists around lines 1243 / 1367 / 1421), so even on `main`
   they would not have reached the FTP servers. (A prior note in
   `OPENCODE_BEAM_20261023_1611Z_PICKS_AND_RATINGS.MD` said "listed in CI but
   not on site" — the CI half of that was wrong; correct cause: not on main
   AND not listed. Correction published in this cycle's notes.)

## What changed

1. Restored both files from their latest off-main blobs into
   `audit_dashboard/`.
   - Pre-deploy content checks: NFA text present in both; `agent_consensus_picks`
     money-ready mentions are all negative ("no strategy is MONEY-READY");
     `opencode_beam` uses the rating vocabulary (CORE-STRONG/ABSTAIN), no
     secrets, 44,489 B.
2. Added both filenames to **all three** per-site page lists in
   `.github/workflows/audit-dashboard.yml` (findtorontoevents / tdotevent /
   torontoevent.net sites) so the hourly cron deploys them once this branch
   merges.
3. YAML parsed with `yaml.safe_load` after the edit.

## How it was verified

- `python3 -c "import yaml; yaml.safe_load(...)"` → OK.
- Immediate live deploy via the FTP loader (env-var credentials only):
  `opencode_beam.html` and `agent_consensus_picks.html` fetched after upload →
  **HTTP 200**, md5 compared local vs live (recorded in the session log).
- CI safety: the page-upload loop wraps each upload in `try/except: pass`, so
  main's checkout (which lacks these files) **cannot delete** the deployed
  copies; the workflow edit is additive and only takes effect after merge.

## Follow-ups

- Both pages will be refreshed with the consolidated ratings content
  (task: consolidated webpage) — this fix only clears the 404s.
- `analyst_active_calls.json` staleness root-caused separately: CI export runs
  and succeeds, but every Reddit/Pushshift source returns 403 from runners, so
  the payload is byte-identical (`active_calls: []`, `updated_at 2026-03-26`)
  → no commit, dashboard shows a stale empty list. Fix needs a source-level
  change, not a deploy fix.
