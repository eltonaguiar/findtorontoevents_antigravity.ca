# Kalshi snapshot persistence — stale-cache fix + scheduled writer

**Date:** 2026-11-18 · **Author:** buffy (Freebuff)

## What was broken

`tools/verify_kalshi_picks.py` resolves sports picks against Kalshi markets. Its
loader `fetch_or_load_snapshot()` took the **newest `*.json` in
`data/kalshi_snapshots/` unconditionally** — no age check at all.

`data/kalshi_snapshots/` contained **exactly one file: `20260426T025427Z.json`,
mtime 2026-05-25** (measured age at fix time: **4,230 h ≈ 176 days**). So every
verification run resolved against a seven-month-old market book, while the
Kalshi signal agent was demonstrably alive (orchestrator 2026-11-17T23:07Z:
36 events → 4 signals, `error: null`).

Two independent defects:

1. **No writer on any schedule.** `tools/kalshi_sports_fetch.py` writes
   `data/kalshi_snapshots/<UTC>.json` by default, but `grep -rn
   kalshi_sports_fetch .github/workflows/` returned **nothing** — no workflow
   invokes it. The file we had was a one-off manual run.
2. **No staleness guard in the reader.** A dead cache was indistinguishable
   from a live one, so defect 1 was invisible.

## What changed

### 1. `tools/verify_kalshi_picks.py` — refuse stale snapshots

- New `MAX_SNAPSHOT_AGE_HOURS` (default **24**, override
  `KALSHI_MAX_SNAPSHOT_AGE_HOURS`; `0` disables the age check).
- `fetch_or_load_snapshot()` now stats the newest snapshot and, when it is older
  than the limit, **prints a warning and falls through to the live fetch**
  (the fallback that already existed) instead of returning April data.
- Added `os` / `time` imports.

### 2. `.github/workflows/kalshi-snapshot.yml` — new 6-hourly writer

- Cron `20 */6 * * *`, `workflow_dispatch`, own `concurrency` group.
- Runs `python tools/kalshi_sports_fetch.py --sport all` (the CLI's own `all`
  target — covers ufc/nba/tennis/golf/nfl/nhl/mlb/soccer).
- Commits only when the snapshot actually changed, message
  `chore(kalshi): refresh sports market snapshot [skip ci]`, with
  `pull --rebase --autostash` before push.
- Fail-open by design: if the workflow never runs, the new age guard makes the
  reader live-fetch, so correctness does not depend on the schedule.

## Verification (actually run)

```
$ python3 -c "...(mtime delta)..."
4230h old

$ KALSHI_MAX_SNAPSHOT_AGE_HOURS=24 python3 tools/verify_kalshi_picks.py
[verify] ignoring stale snapshot 20260426T025427Z.json (4230.4h old > 24h limit);
         falling back to a live Kalshi fetch
  matched=0  no_kalshi_match=0  skipped=1  picks=1
exit=0

$ python3 -c "import ast; ast.parse(open('tools/verify_kalshi_picks.py').read())"
verify_kalshi_picks.py parses OK
```

The guard fires on the exact file that caused the incident, the run completes
cleanly, and the live-fetch path is exercised rather than the stale cache.

## Not done (needs a decision / not authorised here)

- The workflow has **not been pushed or triggered** — it will first run on the
  next `:20 */6` slot after it lands.
- `data/kalshi_snapshots/20260426T025427Z.json` is **left in place** (it is
  harmless now that it is aged out, and it is the only historical sample). Delete
  it if you want the directory to start clean.
- Retention: nothing prunes old snapshots yet. At 4 files/day the directory grows
  slowly; add a `find -mmin` prune if it bothers you.
