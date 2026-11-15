# Open Issues Analysis

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
**Generated:** 2026-11-15T08:00Z UTC
**Total Open Issues:** ~50+

---

## Critical Issues

### #787 — [backup-verify] Restore check FAILED — 2026-11-15
- **Author:** app/github-actions
- **Created:** 2026-11-15T07:34:27Z
- **Labels:** backup-verify, automated
- **URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/issues/787

### #783 — [backup-verify] Restore check FAILED — 2026-11-15
- **Author:** app/github-actions
- **Created:** 2026-11-15T07:07:20Z
- **Labels:** backup-verify, automated

### #782 — [backup-verify] Restore check FAILED — 2026-11-15
- **Author:** app/github-actions
- **Created:** 2026-11-15T06:37:53Z
- **Labels:** backup-verify, automated

### #781 — [backup-verify] Restore check FAILED — 2026-11-15
- **Author:** app/github-actions
- **Created:** 2026-11-15T06:10:54Z
- **Labels:** backup-verify, automated

### #780 — [backup-verify] Restore check FAILED — 2026-11-15
- **Author:** app/github-actions
- **Created:** 2026-11-15T06:03:22Z
- **Labels:** backup-verify, automated

---

## Recurring Issue Patterns

### 1. Backup Verify Failures (Chronic)

This is the most recurring issue, with failures recorded monthly since at least August 2026:

| Month | Issue Count | Issue Numbers |
|-------|-------------|---------------|
| November 2026 | 5+ | #787, #783, #782, #781, #780 |
| October 2026 | 8+ | #728-721 |
| September 2026 | 8+ | #694-680 |
| August 2026 | 8+ | #686-676 |
| July 2026 | 6+ | #674-668 |
| June 2026 | 6+ | #674-668 (some overlap) |

**Root cause:** The backup-verify workflow checks:
1. `dashboard_data.json` — trading_picks count via dashboard_data.json proxy
2. `recent_exits.json` — at_pick_outcomes count
3. Critical file existence: `alpha_engine/data/recent_exits.json`, `alpha_engine/data/ml_health_status.json`, `audit_dashboard/data/pcg5_log.json`
4. Python syntax smoke test on key engine files

The recurring failures suggest either:
- Critical files are missing or empty
- Python syntax errors in key engine files
- Dashboard data fetch failures

### 2. Security Rotation Reminders (Recurring)

| # | Title | Created |
|---|-------|---------|
| #764 | [Security] Monthly Secret Rotation Reminder — November 2026 | 2026-11-01 |
| #695 | [Security] Monthly Secret Rotation Reminder — October 2026 | 2026-10-01 |
| #685 | [Security] Monthly Secret Rotation Reminder — September 2026 | 2026-09-01 |
| #675 | [Security] Monthly Secret Rotation Reminder — August 2026 | 2026-08-01 |
| #668 | [Security] Monthly Secret Rotation Reminder — July 2026 | 2026-07-01 |

These are automated monthly reminders for secret rotation, which is related to the QA Market Validation failure (missing API keys).

### 3. Production Resolver Issue

**#748 — Production resolver predates _priceless_close -> exit_price=0.0 flat closes in recent_closed**
- **Author:** eltonaguiar
- **Created:** 2026-10-20T02:56:09Z
- **Issue:** Production resolver uses `_priceless_close` which results in `exit_price=0.0` flat closes in `recent_closed`. This means many picks have zero exit price, making PnL calculations incorrect.

---

## Related Issues to QA Market Validation Failure

The QA Market Validation workflow failure is related to the secret rotation issues:
- #764: Monthly Secret Rotation Reminder — November 2026
- #695: Monthly Secret Rotation Reminder — October 2026
- #685: Monthly Secret Rotation Reminder — September 2026
- #675: Monthly Secret Rotation Reminder — August 2026
- #668: [Security] Monthly Secret Rotation Reminder — July 2026

These reminders suggest that API keys/secrets need regular rotation, and the QA Market Validation failure may be related to expired or missing secrets.

---

## Recommended Actions for Issues

### P0 — Critical

| # | Action | Related Issues |
|---|--------|---------------|
| 1 | Add 5 missing API secrets to GitHub repo Settings | #764, #695, #685, #675, #668 (secret rotation reminders) |
| 2 | Investigate and fix backup-verify failures | #787, #783, #782, #781, #780, #728-721, #694-668, #686-676 |
| 3 | Fix production resolver exit_price=0.0 issue | #748 |

### P1 — Do This Week

| # | Action | Related Issues |
|---|--------|---------------|
| 4 | Merge PR #786 (fixes QA price validation) | Related to #764, #695, #685 |
| 5 | Merge PR #785 (restores audit page script tags) | Related to general audit stability |
| 6 | Review and close resolved backup-verify issues | #787-780, #728-721, #694-668, #686-676 |

### P2 — Do This Month

| # | Action |
|---|--------|
| 9 | Review remaining open issues |
| 10 | Set up issue templates for backup-verify failures |
| 11 | Add automated labeling for backup-verify failures |
