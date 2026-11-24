# Enhancement Plan — bestiejobharvest (2026-11-18)

## Scope
Consolidate job-signal matcher + pipeline + GitHub Pages delivery for ServiceNow/Salesforce/ITSM-ITAM roles (Toronto/GTA + Canada-remote).

## Tracks
1. Matcher calibration (done): explicit non-build roles cleared; residual FPs 0 at scored_geo_eligible@2.
2. Pipeline integration: wire matcher into scan_boards -> normalize_lead -> verify_leads -> inbox merge.
3. GitHub Pages: publish verified feed as static site (docs/index.html + data/*.json) via Pages workflow.
4. QA: eval_matcher 49/49, verify_leads offline gate, py_compile, board invariants.

## GitHub Pages plan
- Add `docs/` directory with index.html listing verified leads (client-side fetch of data/verified_leads.json).
- Add `.github/workflows/pages.yml` to deploy docs/ on push to main.
- Data contract: data/verified_leads.json (array of normalized+verified leads) with url, role, company, location, tracks, geo_bucket.
- Rights gate: only verified + rights-cleared leads published.

## QA gate
- py_compile all prototype scripts
- eval_matcher 49/49
- verify_leads offline (0 pass/46 review/3 reject baseline; target 0 reject after rights gate)
- no PII/secrets in published data

## Deletion safety
- v2 commits cherry-picked into bestiejobharvest (8 commits).
- v4 untracked docs/config/scripts copied into updates/.
- v3 had only WIRED_IN artifacts already present in main; no unique bestiejob work.
- v2/v3/v4 safe to delete after this plan is committed.
EOF