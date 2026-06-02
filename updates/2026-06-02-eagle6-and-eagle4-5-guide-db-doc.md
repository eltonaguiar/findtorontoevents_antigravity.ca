# EAGLE-6 + EAGLE-4/5 Guide DB Doc Update (minimax-m3-free, 2026-06-02)

## Summary

Completed the live `ejaguiar1_stocks` DB documentation for the EAGLE-6 work and the EAGLE-4/5 guide doc recovery. Verified prior rows (#63, #83, #84, #85) are accurate, added 1 new ENHANCEMENT, 1 new INCIDENT, and updated 3 existing rows with proper timestamps and cross-references.

## What changed in the DB

### New ENHANCEMENT (1 row)

| ID | Class | Status | Impact | Effort | Title |
|----|-------|--------|--------|--------|-------|
| 107 | OVERALL | IMPLEMENTED | HIGH | S | EAGLE-4 + EAGLE-5 gates user-guide document (minimax-m3-free, 2026-06-02, PR #461) |

The 7-section HTML guide at `updates/eagle4-eagle5-gates-2026-06-02.html` (PR #461, branch `docs/eagle4-eagle5-gates-recovery-2026-06-02`). Categories: GATE. Linked to PRs #461 and the closed #447.

### New INCIDENT (1 row)

| ID | Class | Sev | Status | Title |
|----|-------|-----|--------|-------|
| 87 | OVERALL | P2 | RESOLVED | PR branch fast-forward corruption: docs/eagle4-eagle5-gates-2026-06-02 lost EAGLE-4/5 commits |

Component: `git-branch-state`. Documents the data-loss pattern where the doc-only branch was fast-forwarded past my EAGLE-4/5 commits by concurrent agent activity (PR #455 walkforward-lazy-imports merge). Fix recorded: "When a doc-only branch must coexist with concurrent auto-syncs, build on a clean new branch from current origin/main and add only the doc files. Cherry-picking old commits onto a fast-forwarded tip will produce index.html conflicts." Linked to PRs #447(closed), #461, #455.

### Updated rows (3)

| ID | Type | Change |
|----|------|--------|
| 63 (EAGLE-6 v1) | ENHANCEMENT_OVERALL | Set `implemented_at` to 2026-06-02 14:30:00 (was NULL) |
| 83 (EAGLE-4 gate) | ENHANCEMENT_OVERALL | Appended "guide-doc:PR #461" to `link_github_ref` |
| 84 (EAGLE-5 gate) | ENHANCEMENT_OVERALL | Appended "guide-doc:PR #461" to `link_github_ref` |

## Verification

- Re-rendered `audit_dashboard/incidents.html` and `audit_dashboard/data/incidents_enhancements_feed.json` via `tools/audit_pick_funnel/render_incidents_page.py`
- New totals: 114 incidents · 138 enhancements · 16 findings
- Both new entries visible at `https://findtorontoevents.ca/audit/incidents.html`:
  - #107 enhancement (EAGLE-4/5 guide doc)
  - #87 incident (branch fast-forward corruption, RESOLVED)
- The rendered files are normally committed by the nightly workflow `.github/workflows/incidents-enhancements-nightly.yml` — leaving them M for that workflow to pick up

## Existing EAGLE-6 DB state (already populated, no changes needed)

- **#63 EAGLE-6 statistical admissibility gate v1** — IMPLEMENTED. PR #456. link_github_ref `2b4d7ce36,036599997,456`. link_md_path `EAGLE6_2026-06-02_minimax-m3-free.MD`. enhancement_plan covers v1 (shipped) + v2 backlog.
- **#85 EAGLE-6 v2 statistical gates** — BACKLOG. PR #456. Step 1: generate `tools/cpcv_pbo_results.json` via `alpha_engine/anti_overfit_validator.py`.

## In-progress (not changed here)

- EAGLE-6 v2 PBO gate — blocked on `tools/cpcv_pbo_results.json` (not yet generated)
- EAGLE-6 v2 walk-forward OOS gate — blocked on per-strategy walk-forward payload
- EAGLE-6 v2 bootstrap CI gate — blocked on per-strategy PnL list
- EAGLE-6 v2 windowed-HHI to fix over-zealous small-population flagging

## Sources

- `tools/audit_pick_funnel/cli_track.py` — `enhancement` + `incident` UPSERT subcommands
- `tools/audit_pick_funnel/render_incidents_page.py` — page + feed JSON + updates/index.html injection
- `.github/workflows/incidents-enhancements-nightly.yml` — nightly cron
- `EAGLE6_2026-06-02_minimax-m3-free.MD` (EAGLE-6 plan, PR #456)
- `updates/eagle4-eagle5-gates-2026-06-02.html` (EAGLE-4/5 guide, PR #461)
- `EAGLE4_2026-06-02_minimax-m3-free.MD` (EAGLE-4 plan, PR #447 original / commit e9b2d73fd)

## Repro

```bash
# Verify row visibility
DB_PASS_STOCKS=stocks1234560 python3 tools/audit_pick_funnel/cli_track.py list --kind enhancement --limit 5 --class OVERALL
DB_PASS_STOCKS=stocks1234560 python3 tools/audit_pick_funnel/cli_track.py list --kind incident --limit 5 --class OVERALL --severity P2

# Re-render the page (also rewrites the feed JSON + updates/index.html injection)
DB_PASS_STOCKS=stocks1234560 python3 tools/audit_pick_funnel/render_incidents_page.py
```
