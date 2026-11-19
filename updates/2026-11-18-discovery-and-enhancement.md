# 2026-11-18 — Discovery + GitHub Pages Enhancements (bestiejobharvest)

## What was broken / missing
- Matcher leaked explicit non-build roles (`SF_declarative_admin_flows`, `SF_admin_Toronto_declarative_only`) at threshold @2.
- No live discovery/curation tool producing publishable, verified SN/SF developer leads.
- GitHub Pages scaffold existed but rendered raw JSON, not a usable table.
- No cross-check against vendor-direct ATS boards.

## What changed
1. `ideas/bestiejob/prototypes/job_signal_matcher.py` — explicit non-build roles
   (`non_build_explicit` with no build evidence) now clear the track entirely instead of a
   partial −4 penalty, so they cannot leak through at `scored_geo_eligible@2`.
2. `ideas/bestiejob/prototypes/fixtures_matcher_cases.labels.json` — removed `any_track`
   for the 3 cases the matcher now intentionally clears (`SF_declarative_admin_flows`,
   `SF_admin_Toronto_declarative_only`, `Dynamics365_admin_negative`).
3. `updates/scripts/discover_sn_sf_dev.py` (new) — loads the live BESTIEJOB feed
   (`eltonaguiar.github.io/BESTIEJOB/jobs.json`), filters SN/SF dev roles in Toronto/GTA +
   Canada-remote, runs the matcher, cleans malformed title/company fields, de-dupes agency
   reposts, checks URL liveness on a bounded shortlist, ranks, and emits
   `docs/data/verified_leads.json` + a markdown report.
4. `docs/index.html` — proper responsive table with track filter + text search, reading
   `data/verified_leads.json`.
5. `updates/2026-11-18-discovery-report.md` — 60 curated roles (31 SN / 29 SF, 60/60 reachable)
   plus direct-vendor cross-check.

## Verification (QA)
- `eval_matcher`: **49/49 passed (100%)**.
- `py_compile` on all prototype + discovery scripts: OK.
- `docs/data/verified_leads.json`: 60 leads, all `live=true`, 31 SN / 29 SF.
- Cross-check: ServiceNow (SmartRecruiters `country=ca`, 22) and Salesforce (Workday, 3) direct
  boards add no material dev-role gaps; SI partners dominate.

## Follow-ups
- Schedule `discover_sn_sf_dev.py --check-live` on a cron (e.g. hourly) and commit
  `docs/data/verified_leads.json`.
- Add rights-gate filtering (`updates/config/source-rights.yaml`) before publishing.
- Optional: expand to Montreal/Ottawa if scope widens.
