# PR4: Signal Outcomes Pipeline Restoration Verification

**Date:** 2026-05-31
**Branch:** `fix/pr4-signal-outcomes-pipeline-verification`
**Severity:** P0 — historical signal outcomes staleness made forward-WR claims unverifiable
**Incident addressed:** `signal_outcomes table 82 days stale`

## What Was Broken

The incidents inventory reported that `at_signal_outcomes` / `signal_outcomes` was stale by 82 days, with the last resolved outcome around 2026-03-04. That meant the dashboard could not trust forward win-rate / outcome coverage claims because the resolver pipeline appeared dead.

## Current Finding

The incident is now stale / already repaired. The live MySQL `at_signal_outcomes` table is populated and current.

Verified live database state on 2026-05-31 UTC:

```text
at_signal_outcomes: count=107777, latest_created_at=2026-05-30 23:44:47
```

Current source-system coverage:

```text
kimi_riseoftheclaw: 68628
alpha_engine: 20460
ml_battleground_system_f_clawsofdoom: 10602
battleground: 7380
mercury2: 469
crypto_signal_engine: 60
multi_asset_copytrader: 36
kimi_signal_tracker: 23
ml_battleground_system_b_regime: 19
ml_battleground_system_a_filter: 19
opposite_day: 15
paper_trading: 10
breakout_approach_c_spike_reverse: 9
ml_battleground_ensemble: 8
bundle_babies: 6
```

Current asset-class coverage:

```text
CRYPTO: 53480
FOREX: 35978
UNKNOWN: 14596
MEMECOIN: 3554
EQUITY: 169
```

## What Was Checked

1. Inspected `.github/workflows/outcome-resolver.yml`.
2. Confirmed the workflow runs hourly via cron:

```yaml
- cron: '15 */1 * * *'
```

3. Confirmed the workflow now runs `alpha_engine/active_picks_sync.py` before the resolver for:
   - CRYPTO
   - EQUITY
   - FOREX
   - COMMODITY
   - ETF
   - BOND
4. Confirmed `alpha_engine/active_picks_sync.py` has the live-writer path:
   - explicit `--apply` flag
   - environment gate `ACTIVE_PICKS_SYNC_APPLY=1`
   - MySQL `UPDATE at_raw_picks`
   - append to `alpha_engine/data/closed_picks.json`
5. Confirmed the workflow mirrors resolved outcomes to MySQL with `audit_trail/backfill_local_sources.py`.
6. Queried the live `at_signal_outcomes` schema and freshness.
7. Queried current `at_raw_picks` status distribution:

```text
CLOSED: 50465
OPEN: 45726
EXPIRED: 31146
WON: 14546
LOST: 8650
```

## What Changed

No code change was required in this session. The restoration work had already landed before this verification:

- `.github/workflows/outcome-resolver.yml` contains the hourly resolver workflow.
- `alpha_engine/active_picks_sync.py` exists and includes guarded live-write logic.
- `audit_trail/backfill_local_sources.py` populates `at_signal_outcomes` from local closed/outcome sources.

This document records the verification and closes PR #4 as **resolved / stale incident verified fixed**.

## Verification Commands

Live table freshness was verified with a read-only MySQL query using the local stocks DB password:

```bash
DB_STOCKS_PASSWORD='[redacted]' python3 -c "... SELECT COUNT(*), MAX(created_at) FROM at_signal_outcomes ..."
```

Result:

```text
(107777, 2026-05-30 23:44:47)
```

## Follow-Up Recommendation

Update the incident tracker row from `OPEN` to `RESOLVED` or `STALE_VERIFIED_FIXED`.

Recommended extra dashboard hardening for a later PR:

- Add a freshness badge that uses `MAX(created_at)` from `at_signal_outcomes`.
- Alert if `MAX(created_at)` is older than 24 hours.
- Alert if outcome coverage drops below an agreed threshold.
- Break out `UNKNOWN` asset-class outcomes so they can be normalized or assigned upstream.
