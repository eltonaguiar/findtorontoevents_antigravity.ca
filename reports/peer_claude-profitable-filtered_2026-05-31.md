# Peer Review — INCIDENT_OVERALL #24: Profitable-but-Filtered Observability Lane

**Date:** 2026-05-31
**Reviewer:** Claude (Opus 4.7) subagent
**Task:** Decide whether the uncommitted file `audit_trail/profitable_filtered_observer.py` should ship for INCIDENT_OVERALL #24.

## Approach

1. Inspected `git status` in main working dir — confirmed `audit_trail/profitable_filtered_observer.py` and `updates/2026-05-31-profitable-but-filtered-observability-lane.md` are both untracked WIP from cursor.
2. Read the module (106 lines) and the design doc.
3. Validated the contract against the P0 incident: "Profitable-but-filtered picks are not surfaced anywhere."
4. py_compile passed.
5. Created clean branch `incident/24-profitable-filtered-observer-2026-05-31` off `origin/main` (did NOT base on the cursor `fix/incidents-batch-resolve-2026-05-31` branch — per directive, do not step on cursor's in-flight `tools/db_env.py` work).
6. Copied the two files onto the clean branch, committed, pushed, opened PR for human review (no auto-merge).

## Evidence

- File location: `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/profitable_filtered_observer.py` (3549 bytes, mtime 2026-05-31 02:26)
- Companion doc: `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-05-31-profitable-but-filtered-observability-lane.md`
- Module is purely observational:
  - Writes one append-only JSONL line per later-profitable rejected pick to `audit_dashboard/data/profitable_but_filtered_YYYY-MM-DD.jsonl`.
  - Threshold: `min_pnl_pct=0.5` (default).
  - Captures `first_failed_gate`, `strategy`, `symbol`, `direction`, `gate_score_at_reject`, `later_pnl_pct`, `later_exit_reason`, `observed_at`.
  - Stable join key: `signal_id` if present, else `symbol|strategy|direction`.
- No mutation of scoring, gates, or active/smart feeds. No DB writes (so the DB-backup hard rule does not trigger).
- Wire-Up Rule: doc explicitly documents the planned caller in `audit_trail/dashboard_generator.py` post the existing `_filter_active_picks_with_gate(...)` call. This PR ships the module + doc; wiring is a deliberate follow-up PR (smallest reviewable diff first), which matches the Wire-Up Rule's "opt-in sidecar with wiring plan" branch.

## Verdict

**SHIP.** The file matches the incident contract exactly: it produces the first durable false-negative signal for gate calibration without any production-behavior risk. The companion `updates/` doc satisfies documentation + Wire-Up Plan requirements.

## Proposed Diff

Two new files only:

- `audit_trail/profitable_filtered_observer.py` (+106 lines, new module)
- `updates/2026-05-31-profitable-but-filtered-observability-lane.md` (+63 lines, new doc)

No edits to existing files. No DB writes. No FTP touches.

## Test Plan

1. `python3 -c "import py_compile; py_compile.compile('audit_trail/profitable_filtered_observer.py', doraise=True)"` — passed locally.
2. Smoke import: `python3 -c "from audit_trail.profitable_filtered_observer import record_if_later_profitable, record_batch_if_later_profitable; print('OK')"`.
3. Manual functional smoke (follow-up): synthesize one rejected pick + one closed_lookup entry with `pnl_pct=1.2` → confirm a JSONL line is appended to `audit_dashboard/data/profitable_but_filtered_<today>.jsonl` with `first_failed_gate` populated.
4. Wire-up PR (follow-up, separate): call `record_batch_if_later_profitable(filtered_out, closed_by_key)` in `dashboard_generator.py` and confirm the JSONL grows on the next dashboard regen.

## Rollback Plan

- Revert the PR. The two files are net-new; no callers exist yet (no wire-up), so removal is byte-for-byte safe.
- The JSONL artifact (if any was written post-wire-up) is observational and can be left in place or deleted from `audit_dashboard/data/` with no production impact.

## Coordination Notes

- Branched off `origin/main` (commit `fedf7d656`), NOT off `fix/incidents-batch-resolve-2026-05-31`. This avoids colliding with cursor's in-flight edits to `tools/db_env.py`, `tools/backfill_trust_score.py`, `tools/safe_db_archive.py`, and the dashboard template.
- PR opened for human review only — no auto-merge.
- No DB writes performed; the ejaguiar1_backups hard rule did not need to fire.
