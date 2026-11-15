# 03 — Open Issues

49 open issues total. **43 of them are duplicate `backup-verify` bot issues** —
that single bug is 88% of the open-issue queue and hides the real work.

## The flood: 43 × `[backup-verify] Restore check FAILED`

All opened by `github-actions[bot]`, all the same body:

```
dashboard_data.json NOT FOUND
Critical file missing: audit_dashboard/data/dashboard_data.json
```

Open issues: **#787 #783 #782 #781 #780 #728 #727 #726 #725 #724 #723 #722 #721
#694 #693 #692 #691 #690 #689 #688 #687 #686 #684 #683 #682 #681 #680 #679 #678
#677 #676 #674 #673 #672 #671 #670 #669 #606 #605 #604 #603 #602**

Opened monthly since June, but **5 opened today alone** (#780 06:03, #781 06:10,
#782 06:37, #783 07:07, #787 07:34) — all citing the same run `43683666944`.

### Root cause (proven)
1. `backup-verify.yml` checks `audit_dashboard/data/dashboard_data.json`, which is
   **gitignored** (`.gitignore:218`) and therefore **never present** at
   `actions/checkout`. The check can never pass.
2. The "Open failure issue" step calls `issues.create(...)` **unconditionally** —
   no lookup for an existing open issue.
3. `actions-failure-guardian.yml` runs every 30 min and re-runs the failure. A
   re-run keeps the same run id, so each retry files another issue.
4. → self-sustaining loop: fail → guardian retries → new issue → repeat.

### Fix
Merge **PR #713** (ready, CLEAN) which:
- fetches the live copy from `https://findtorontoevents.ca/audit/data/dashboard_data.json`;
- warns+skips the proxy when absent instead of failing;
- removes the gitignored path from `critical_files`;
- makes issue creation idempotent (comments on the existing open issue).
Then bulk-close the 43 stale issues:

```bash
gh issue list --state open --label backup-verify --limit 200 \
  --json number --jq '.[].number' \
  | xargs -n1 gh issue close --reason "not planned"
```
(Do this **after** #713 is merged, or they will re-open on the next run.)

## Real issues (non-backup)

| # | Title | Assessment |
|---|-------|------------|
| **#748** | Production resolver predates `_priceless_close` → `exit_price=0.0` flat closes in `recent_closed` | **Real, high-impact data-integrity bug.** This is the FLAT_CLOSE pollution that corrupts every reported PF/WR. Fix before trusting any performance number. (Related unmerged PRs: #749 batch-close root cause, #666 backfill price guard, #756 resolver flat-exit.) |
| #764 | [Security] Secret rotation reminder — Nov 2026 | Legitimate checklist, but it is the **5th** unclosed monthly reminder. |
| #695 / #685 / #675 / #668 | Secret rotation reminders — Oct/Sep/Aug/Jul | Stale duplicates. The reminder workflow should reuse one tracking issue (same idempotency pattern as #713) instead of filing a new one each month. |
| #654 | Weekly event gap scan DEGRADED (scrapers blocked) | Event-scraper health, unrelated to trading; low priority but real. |

## Issue-hygiene recommendations

1. **Idempotent bot issues everywhere.** Both `backup-verify.yml` and
   `secret-rotation-reminder.yml` create a fresh issue every run/month. Adopt the
   `listForRepo` + comment-if-open pattern (already written in PR #713).
2. **Auto-close on recovery.** Add a success step that finds the open
   `backup-verify` issue and closes it when checks pass.
3. **Label + pin one tracking issue per concern** (backup-verify, secret
   rotation) and have bots comment there.
4. After merging #713, close all 43 `backup-verify` issues so the queue reflects
   real work only.
