# Edge Stability Refresh Implementation & Fix

## Status
- **Last Updated:** 2026-05-31
- **Status:** FIXED & AUTOMATED

## Problem
The `findtorontoevents.ca/audit/edge_stability.html` page was showing stale data (last updated May 12, 2026) despite a daily refresh workflow (`edge-stability-refresh.yml`) running successfully in the repository.

## Root Cause
The main deployment pipeline `audit-dashboard.yml` was configured to upload `edge_stability.html`, but it did not include the `audit_dashboard/data/edge_stability/*.json` data files in its FTP upload steps. As a result, the live site never received the daily updates committed to the repository.

## Solution
1.  **Fixed Deployment Pipeline:** Modified `.github/workflows/audit-dashboard.yml` to explicitly upload the `data/edge_stability/` directory to all three production targets:
    - `findtorontoevents.ca`
    - `torontoevent.net`
    - `tdotevent.ca`
2.  **Verified Automation:** Confirmed that `.github/workflows/edge-stability-refresh.yml` correctly runs daily at 00:30 UTC, fetches the production `dashboard_payload.json`, regenerates per-class stability JSONs, and commits them with `[skip ci]`.
3.  **Timestamping:** Verified that `edge_stability.html` correctly displays the `as_of` timestamp in EST for transparency.

## Verification
- Validated `audit-dashboard.yml` syntax.
- Local run of `tools/edge/edge_stability.py --all` confirmed to produce valid JSON schema v1.
- Deployment loop now globs `audit_dashboard/data/edge_stability/*.json` and ensures the remote directory exists before upload.

## Files Modified
- `.github/workflows/audit-dashboard.yml`: Added `data/edge_stability` upload logic to 3 deploy functions.
- `updates/2026-05-31-edge-stability-deploy-fix.md`: This documentation.
