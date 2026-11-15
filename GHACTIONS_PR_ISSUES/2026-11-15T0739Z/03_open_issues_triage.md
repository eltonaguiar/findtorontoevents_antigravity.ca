# 03 — Open Issues Triage (49 open)

| Bucket | Count |
|---|---|
| `[backup-verify]` spam | 42 |
| Secret-rotation reminders | 5 |
| Real product bugs | 2 |

## A. backup-verify spam (42 issues) — the dominant problem

Titles: `[backup-verify] Restore check FAILED — <date>` (Jun 15 → Nov 15 2026). Every one is the same failure:
```
dashboard_data.json NOT FOUND
Critical file missing: audit_dashboard/data/dashboard_data.json
```
- **Cause:** `backup-verify.yml` checks a gitignored generated file (see `01_github_actions_audit.md` §2.1) and opens a new issue on every failure with no dedup.
- **Resolution:** merge PR #713, then **close all 42 in one pass** (they are identical). Keep one canonical tracking issue if a *real* backup-restore verification is re-introduced.

## B. Secret-rotation reminders (5 issues) — security debt

`[Security] Monthly Secret Rotation Reminder — {Aug, Sep, Oct, Nov} 2026` (and one for July). Auto-created by `secret-rotation-reminder.yml`, **never acted on**. Checklist covers `DB_PASS_STOCKS`, `DB_PASS_BACKTESTS`, `DB_PASS_ANALYTICS`, `BINANCE_API_KEY/SECRET`, `COINGECKO_API_KEY`, `DISCORD_WEBHOOK_URL`, `SENDGRID_API_KEY`.
- **Action:** actually rotate these (runbook: `docs/DB_ROTATION_RUNBOOK_2026-05-13.md`), verify via `cross-db-audit.yml` + `alpha-engine-daily-picks.yml`, then close the reminder issues. 5 months of unrotated credentials is a real exposure.

## C. Real product bugs (2 issues)

| Issue | Title | Note |
|---|---|---|
| **#748** | Production resolver predates `_priceless_close` → `exit_price=0.0` flat closes in `recent_closed` | Real resolver bug. Related open PRs: #749, #756. Prioritize together. |
| **#654** | Weekly event gap scan DEGRADED (scrapers blocked, 56/10,614 events) | Data-quality, not trading. Low priority but the event feed is a product surface. |

## D. Recommendation

1. **Close 42 spam issues** after merging #713.
2. **Rotate secrets** and close 5 reminders (do it, don't just close the issue).
3. **Fix #748** via the resolver PRs (#749/#756), coordinating to avoid conflicts.
4. **Adopt a dedup rule** for any future auto-opening workflow (backup-verify is the template of what NOT to do).
