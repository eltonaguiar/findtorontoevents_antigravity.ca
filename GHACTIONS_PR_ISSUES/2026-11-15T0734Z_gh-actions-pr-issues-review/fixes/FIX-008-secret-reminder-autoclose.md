# FIX-008 — Monthly security reminders accumulate forever

**File:** `.github/workflows/secret-rotation-reminder.yml`
**Severity:** P2
**Status:** Applied (PR #790)

## What was broken
`secret-rotation-reminder.yml` creates a "[Security] Monthly Secret Rotation Reminder — <Month>" issue on the 1st of each month, but never closes the previous month's. As a result Jul/Aug/Sep/Oct/Nov 2026 reminders were **all open simultaneously** (#668, #675, #685, #695, #764).

## What changed
- Added a **"Close prior-month reminders"** step before creating the new issue. It lists open issues matching the reminder title prefix and closes any whose title is **not** the current month, with a "superseded" comment.
- Also closed the 4 stale reminders (#668, #675, #685, #695) immediately; kept #764 (November, current).

## How to verify
- `yaml.safe_load` parses the workflow ✅
- Next 1st-of-month run should close October's reminder and keep only the new one open.
- Current open set is now just #764.

## Note
The step uses the same `GH_TOKEN`/`gh issue` pattern already used by the create step, so no new permission is required (`issues: write` already granted).