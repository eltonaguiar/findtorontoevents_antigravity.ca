# Fix — Dedup torontoevent backtest/deploy workflows (ROOCODE variant)

- Date: 2026-11-16T02:50Z
- Change: rename `torontoevent-backtest-and-deploy-ROOCODE.yml` → `.yml.disabled`
- Branch: `fix/dedup-roocode-backtest-2026-11-16`

## Problem
Two workflows were near-identical **true duplicates**, both firing every 15 min during
US market hours (`*/15 14-21 * * 1-5`) plus 4-hourly on weekends:
- `torontoevent-backtest-and-deploy.yml` (runs `generate_dashboard_data.py`, `live_scanner.py`, deploys via FTP to `FTPGODADDYHOST_TE_DOTNET`)
- `torontoevent-backtest-and-deploy-ROOCODE.yml` (byte-identical scripts + same FTP target; only whitespace/emoji/name differ — verified via `diff`)

Neither had a `concurrency` group. Effects:
1. **2× redundant load** every 15 min during market hours.
2. **Concurrent FTP write race** — two runs uploading the same dashboard files to the same
   torontoevent.net FTP root at the same time → possible partial/overwritten deploys.

## Change
Disabled the ROOCODE variant (`.yml.disabled`). The primary
`torontoevent-backtest-and-deploy.yml` continues to run and deploy, so the site still updates.

## Downstream impact
- **torontoevent.net**: unaffected — primary workflow still deploys. (This pair targets
  torontoevent.net, NOT findtorontoevents.ca/audit.)
- **findtorontoevents.ca/audit**: no direct dependency on this pair (audit is fed by
  `audit-dashboard.yml` + alpha engine, not these KIMI backtest deploys).

## Revert
```bash
git fetch origin && git checkout main && git pull --ff-only
git mv .github/workflows/torontoevent-backtest-and-deploy-ROOCODE.yml.disabled \
       .github/workflows/torontoevent-backtest-and-deploy-ROOCODE.yml
git commit -m "revert(ci): re-enable torontoevent backtest ROOCODE duplicate"
git push origin main
```

## Verification
After merge, confirm only the primary fires on the next market-hours `:15` tick:
`gh run list --workflow torontoevent-backtest-and-deploy.yml --limit 3` (success) and
`gh run list --workflow torontoevent-backtest-and-deploy-ROOCODE.yml` returns the last
pre-disable run only (no new ones).
