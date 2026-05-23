# Fix: /audit/research_index.html broken run links (2026-05-14)

## What Was Broken

The links on `/audit/research_index.html` pointed to `../research/asset_class/...`, which resolves outside `/audit/`.

Live checks showed the run links were failing (`404`) and research run artifacts were not being uploaded into the public `/audit/research/asset_class/` tree during dashboard FTP deploy.

## What Changed

1. Updated link generation in `tools/research/build_research_index.py`:
- From: `../research/asset_class/<class>/run_<ts>/index.html`
- To: `research/asset_class/<class>/run_<ts>/index.html`

2. Updated the currently committed static file `audit_dashboard/research_index.html` to match the new link format (`research/...`) so links are correct immediately.

3. Updated `.github/workflows/audit-dashboard.yml` FTP deploy script:
- Added `ensure_nested_dir(...)` helper to create nested remote folders safely.
- Added `upload_research_tree(...)` helper to upload all files from `research/asset_class/**`.
- Wired upload calls into all 3 site deploy functions:
  - `findtorontoevents.ca`
  - `torontoevent.net`
  - `tdotevent.ca`
- Target remote path: `/audit/research/asset_class/...`

## Verification

- Confirmed no stale `../research/asset_class` links remain in `audit_dashboard/research_index.html`.
- Confirmed 26 links now point to `research/asset_class/.../index.html`.
- Ran diagnostics on changed files; no syntax/lint errors reported for:
  - `.github/workflows/audit-dashboard.yml`
  - `tools/research/build_research_index.py`
  - `audit_dashboard/research_index.html`

## Expected Outcome After Deploy

- `/audit/research_index.html` links resolve to `/audit/research/asset_class/...`.
- FTP deploy now publishes the full research run artifact tree, so run pages should be reachable on the live sites.
