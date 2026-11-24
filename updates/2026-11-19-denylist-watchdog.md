# audit3 denylist watchdog (2026-11-19)

**Scope:** `.github/workflows/audit3-denylist-watchdog.yml` (new).

## Why

`alpha_engine/audit3_denylist.py` fails **open**: if the ledger is missing or
stale, nothing is denied. That is the right choice for emission (a dead ledger
must not brick the pipeline), but it makes a dead `audit3-ledger` cron a *silent*
loss of enforcement. This watchdog is the independent alarm: it runs on its own
schedule and turns a stale committed ledger into a red build.

## What

- Hourly (`45 * * * *`), offset from `audit3-ledger` (`23 */6 * * *`), plus
  `workflow_dispatch` and a PR trigger on the health tool / denylist / itself.
- Runs `tools/audit3_denylist_health.py --ledger audit_dashboard/data/audit3_ledger.json
  --max-age-days 3 --min-strategy-kills 1`.
- Fails when the committed ledger is older than **3 days** (~12 missed 6-hourly
  runs) or contains no strategy kills — far inside the 14-day fail-open threshold.

## Why 3 days, not 2

`audit3-health.yml` already warns on a stale ledger at 2 days. The watchdog is a
harder gate: 3 days tolerates a weekend of failed runs without a false red, while
still catching a genuinely dead cron well before the 14-day fail-open horizon.

## Verification

- `python3 tools/audit3_denylist_health.py --ledger audit_dashboard/data/audit3_ledger.json
  --max-age-days 3 --min-strategy-kills 1` exits 0 against the current ledger.
- The workflow is additive: no existing workflow or deploy list is modified.
