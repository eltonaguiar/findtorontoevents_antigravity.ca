# DB Rotation Runbook — 2026-05-13

User rotated passwords for `ejaguiar1_stocks` + `ejaguiar1_backtests`
MySQL DBs. New local env vars:

```
DB_PASS_STOCKS / DB_NAME_STOCKS
DB_PASS_BACKTESTS / DB_NAME_BACKTESTS
```

## What's affected

**Code paths (already handled by `tools/db_env.py`):**

`tools/db_env.py::get_stocks_creds()` and `get_backtests_creds()` resolve
the password through a priority chain:

```
stocks priority:    DB_PASS_STOCKS -> MYSQL_PASSWORD -> DB_STOCKS_PASSWORD -> DB_PASSWORD -> AUDIT_DB_PASS
backtests priority: DB_PASS_BACKTESTS -> DB_BACKTESTS_PASSWORD -> BACKTESTS_DB_PASS -> MYSQL_PASSWORD -> DB_STOCKS_PASSWORD
```

So any Python caller that switched to `db_env.get_stocks_creds()` works
with EITHER old or new env-var names. Migration is best-effort.

**Workflows (20 reference `secrets.MYSQL_PASSWORD`):**

```
ab_analysis.yml                  alpha-engine-live.yml           audit-dashboard.yml
breakout-arena.yml               claude-gainer-short-term.yml    consensus-outcome-tracker.yml
deploy-fc-api-env-godaddy.yml    deploy-fc-api-hotfix.yml        dna_strategy_pipeline.yml
hierarchical-bayes.yml           hoffman-tracker.yml             incubator-pipeline.yml
mega-mutation-tracker.yml        mirror-site.yml                 mutation-lab.yml
mysql-trading-sync.yml           now-scanner.yml                 paper-trading.yml
strategy-health-monitor.yml      strategy-health-report.yml
```

All 20 workflows pull the secret as `${{ secrets.MYSQL_PASSWORD }}` and
pass it through as one of these env-var names to the subprocess:
`MYSQL_PASSWORD`, `DB_STOCKS_PASSWORD`, `AUDIT_DB_PASS`, `DB_PASSWORD`.

## The fix — operator action required

### Option A (recommended) — single GH secret update

Update the canonical `MYSQL_PASSWORD` GitHub secret to the new password.
All 20 workflows immediately use the new password on their next run.
Zero code changes needed.

```bash
gh secret set MYSQL_PASSWORD -R eltonaguiar/findtorontoevents_antigravity.ca
# paste new password at stdin prompt
```

This is the minimum-risk path. The backtests DB is rarely written to
from CI; if it has a different password, see Option B.

### Option B — separate stocks/backtests secrets

If `ejaguiar1_stocks` and `ejaguiar1_backtests` now have DIFFERENT
passwords (vs the legacy "same pass for both"), add both new secrets:

```bash
gh secret set DB_PASS_STOCKS    -R eltonaguiar/findtorontoevents_antigravity.ca
gh secret set DB_PASS_BACKTESTS -R eltonaguiar/findtorontoevents_antigravity.ca
gh secret set MYSQL_PASSWORD    -R eltonaguiar/findtorontoevents_antigravity.ca
# paste the new STOCKS pass into MYSQL_PASSWORD too (canonical fallback)
```

Two of the 20 workflows (`audit-dashboard.yml` + `ab_analysis.yml`) now
also pass `DB_PASS_STOCKS` / `DB_NAME_STOCKS` env vars sourced from the
new secret with `secrets.MYSQL_PASSWORD` fallback. The other 18 still
use `MYSQL_PASSWORD` only — they will use the same value as
`DB_PASS_STOCKS` per the canonical fallback above.

## Verification

After update, dispatch one DB-touching workflow + check for auth errors:

```bash
gh workflow run ab_analysis.yml -R eltonaguiar/findtorontoevents_antigravity.ca
# wait ~3 min
gh run list --workflow ab_analysis.yml --limit 1
gh run view <id> --log | grep -iE "Access denied|auth|password|connect"
```

Expected: zero `Access denied` lines. Resolver output: real `# Found N
zero-PnL resolver-bug candidates`.

## What I shipped this session

- `tools/db_env.py` — unified resolver (commit `040cf144a59`)
- `audit-dashboard.yml` — passes `DB_PASS_STOCKS` + `DB_NAME_STOCKS` env
  with `secrets.MYSQL_PASSWORD` fallback on 5 steps (this commit)
- `ab_analysis.yml` — same pattern on 3 steps (this commit)

## What user still needs to do

Only one CLI command (Option A path):

```bash
gh secret set MYSQL_PASSWORD -R eltonaguiar/findtorontoevents_antigravity.ca
```

If user already did this when rotating — verify timestamp updated:

```bash
gh secret list -R eltonaguiar/findtorontoevents_antigravity.ca | grep MYSQL_PASSWORD
# 'updatedAt' should be after the rotation, not 2026-03-05
```

## Risk if unfixed

Every DB-touching workflow auth-fails silently:
- `audit-dashboard.yml` produces stale `dashboard_data.json`
- `ab_analysis.yml` produces stale `system_pf_verification.json`,
  `ab_summary.json`, `cot_step7_friction_adjusted_mc.json`
- `alpha-engine-live.yml` cannot read `trading_picks` for ingest
- `paper-trading.yml` cannot write to `at_raw_picks`

Result: dashboard appears live but underlying data goes stale 24h+
without surfacing the failure (most workflows use `|| echo non-fatal`
to swallow errors).

## NFA

Documentation only. No live trades affected by either path.
