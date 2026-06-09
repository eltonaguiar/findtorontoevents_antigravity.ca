---
tags: [incident, summary, audit]
created: 2026-06-09
status: active
---

# Incidents & Enhancements — Live Summary

> Live page: **findtorontoevents.ca/audit/incidents.html** (auto-regenerated nightly from `INCIDENT_*` + `ENHANCEMENT_*` tables in `ejaguiar1_stocks`). This note is a vault-side index/snapshot.

## Current counts (2026-06-09, all class tables)

| INCIDENTS | count | | ENHANCEMENTS | count |
|-----------|------:|-|--------------|------:|
| OPEN | 86 | | BACKLOG | 139 |
| IN_PROGRESS | 6 | | ACCEPTED | 8 |
| TRIAGED | 5 | | VALIDATED | 14 |
| RESOLVED | 70 | | IMPLEMENTED | 33 |
| | | | REJECTED | 2 |

## Key incidents logged this session (2026-06-09)
- **P0** Resolver-version selection bias — same data yields 4–6× PF spread (no defensible edge until intrabar).
- **P0** 70–95% TIME_EXPIRED invalidates resolved dataset.
- **P0** Backfill contamination — forward_test_only=0 on all crypto+equity rows.
- **P1** GHA: Unified Audit Dashboard None-sort (~60 fails, RESOLVED), MySQL Sync import (~66 fails, RESOLVED), CI Tests 28 stale-assertion fails (OPEN triage).
- **P1** FOREX bleeder family emitting ~3,600 garbage picks (RESOLVED — banned at intake).
- **P1** Peer in-place intrabar `--apply` overwrote 2000 canonical rows (RESOLVED — 1921 restored from snapshot).
- **P1** Clean-cohort money-ready screen: 0 confirmed survivors.

## Key enhancements (SAVE-1..5 rescue plan → ENHANCEMENT_OVERALL)
- SAVE-1 OHLCV deep backfill ✅ run · SAVE-2 intrabar resolver 🟡 dry-run+parallel-apply done, production write-path pending · SAVE-3 re-baseline+paper-pilot ⬜ · SAVE-4 TSMOM sleeve ✅ wired · SAVE-5 ROI dashboard+kill-switch ⬜.

## Deploy note
The live incidents.html is rebuilt by the **Incidents + Enhancements — Nightly Page Render** workflow from the DB tables, then FTP-deployed. Rows logged to `INCIDENT_*`/`ENHANCEMENT_*` appear after the next render. To force: `gh workflow run "incidents-enhancements-nightly.yml"`.

## Related
- [[sessions/2026-06-09-rescue-fixes-and-benefits]]
- [[reference/edge-rescue-roadmap]]
- [[incidents/resolver-intrabar-blocker]]
