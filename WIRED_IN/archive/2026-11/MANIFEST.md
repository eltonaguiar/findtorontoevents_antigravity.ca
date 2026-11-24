# WIRED_IN Archive Manifest — 2026-11

**Purpose:** index of `WIRED_IN/` research folders with their runtime status, so future cleanup
never breaks a live consumer. Created 2026-11-16 (CF5 follow-up, `11_INTEGRATION_RECORD.md` §4).

## Rule
- **LIVE-REFERENCED** = a generator/resolver/panel reads this folder's outputs at runtime. NEVER move/delete.
- **ARCHIVE-CANDIDATE** = research artifact with no runtime consumer; safe to move under
  `archive/2026-11/` in a later deliberate pass (moves deferred: too many cross-references to
  move blindly — this index is the safe first step).

## Index (as of 2026-11-16)

| Folder | Status | Notes |
|---|---|---|
| `2026-11-15T0150Z_childlike-airport` | **LIVE-REFERENCED** | source of `audit_dashboard/data/wired_in_childlike_active_picks.json`; consumers: `audit_trail/dashboard_generator.py` (JSON_PICK_SOURCES + `_PAPER_ONLY_SYSTEMS`), `audit_trail/universal_pick_resolver.py` (SYSTEM_SOURCES) |
| `2026-11-15T0230Z_childlike-airport`, `2026-11-15T0653Z_childlike-airport`, `2026-11-15T0700Z_childlike-airport` | LIVE-REFERENCED (variants) | sibling card-emission snapshots; keep until childlike emitter consolidation |
| `2026-11-15_0708…` (HERMES proof/), `2026-11-15_0711_buffy/experiments/` (repo_mine, build_tracker), `2026-11-15_0725_inspect-wt/tracker/` | ARCHIVE-CANDIDATE | research tools + CSV/HTML outputs, zero runtime consumers (verified 2026-11-16 feed-trace) |
| `2026-11-15T0130Z_scratch-hippodraco`, `2026-11-15T0657Z_scratch-hippodraco` | ARCHIVE-CANDIDATE | audit scratch docs |
| `2026-11-15T065338Z_hilarious-seer`, `2026-11-15T0700Z_finpredict-summary` | ARCHIVE-CANDIDATE | delivery summaries (also covered by `final_v001` docs) |

## Later-pass checklist (when moving)
1. `git grep` each folder name across the repo (generator/resolver/panel refs).
2. Move ARCHIVE-CANDIDATE rows here under `archive/2026-11/<folder>/`.
3. Update this table's paths; run the theory/childlike feed checks (`tests/` + one audit cycle).
