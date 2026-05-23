# penny_picks cron stoppage — root cause

## TL;DR

Not a bug. Workflow `Penny Stock Daily Picks` (id 233176023) was **deliberately disabled** on 2026-02-21, one day after its last successful run. Reason unclear. Same date saw mass-disable of ~14 other pick-generation workflows.

## Evidence

```
$ gh api repos/eltonaguiar/findtorontoevents.ca/actions/workflows/233176023
name: Penny Stock Daily Picks
state: disabled_manually
created_at: 2026-02-11T16:17:34
updated_at: 2026-02-21T03:17:38   ← disabled here
path: .github/workflows/penny-stock-picks.yml
```

## Other workflows disabled in the same window

```
$ gh api repos/.../actions/workflows -q '.workflows[] | select(.state == "disabled_manually") | .name'
Algorithm Competition Refresh
Alpha Engine — Daily Picks
Alpha Suite Daily Refresh
Check Streamer Live Status
Crypto Winner Scanner — Auto Scan
Daily Feed Summary
Daily Miracle DayTrades Scan
Daily Mutual Fund Refresh
Daily Picks Snapshot — Crypto, Forex & Stocks
Daily Stock Data Refresh
Daily Runs
Deals & Freebies — Verify & Refresh
Deploy Competition to Live Site
Deploy to GitHub Pages
Deploy & Refresh MOVIESHOWS3
```

## Hypothesis

Around 2026-02-21, the pick-generation pipeline was consolidated to `alpha-engine-live.yml` (which IS enabled and runs every 2h with a 90-min timeout — see `audit-dashboard.yml` companion). The standalone per-class daily-pick workflows became redundant.

**Verify**: does `alpha-engine-live.yml` produce penny-stock picks? If yes, the EQUITY pipeline was migrated, not killed. If no, EQUITY is genuinely uncovered.

## Re-enable command (DO NOT auto-fire — needs user approval)

```bash
gh workflow enable -R eltonaguiar/findtorontoevents.ca penny-stock-picks.yml
```

Or via UI: Settings → Actions → enabled the workflow.

## Why NOT to re-enable unilaterally

1. **Deliberate decommission**: someone took an action 1 day after last success. Could be cost, debt, migration.
2. **Output table populated 2026-04-27** per uncharted recon — meaning SOMETHING wrote to `penny_picks` 65 days after this workflow stopped. There's another writer (probably `alpha-engine-live.yml`).
3. **Mass-action pattern**: 14+ workflows disabled together = repo-wide policy decision, not a one-off bug.
4. **Output table now stale** since 2026-04-27, so even the alternate writer stopped → that's the real Goal #1 issue, not the disabled standalone workflow.

## Recommended next step

Find which workflow / process wrote to `penny_picks` between 2026-02-21 (penny-stock-picks.yml disabled) and 2026-04-27 (last actual write). That's the canonical EQUITY-pipeline writer.

```bash
git log --since="2026-02-21" --until="2026-04-30" --diff-filter=A --pretty=format:"%h %ad %s" --date=short -- 'tools/*penny*' 'tools/*equity*' 'alpha_engine/*equity*' 'audit_trail/*' 2>&1 | head -30
```

Plus: identify what exact workflow ran between those dates that touched the penny_picks table (search alpha-engine-live.yml + sub-scripts for `penny_picks` references).

## Files
- `.github/workflows/penny-stock-picks.yml` (disabled, schedule still in file)
- `reports/uncharted_tables_recon_2026-05-08.md` (flagged 2026-04-27 last write)
