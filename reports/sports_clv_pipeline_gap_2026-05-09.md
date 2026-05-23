# Sports CLV Pipeline Gap — 2026-05-09 forensic

## TL;DR

`lm_sports_clv` table on `ejaguiar1_sportsbet` has **NOT received a new row since 2026-02-12 04:59:52** — 86 days of dead pipeline (PR #862's "0 rows in 30d" finding understated the gap). All sports edge claims since mid-Feb are unverifiable. Goal #2 (sports betting) blocked at the validation layer.

## Verified state (2026-05-09T20:53Z)

```sql
SELECT COUNT(*), MIN(last_updated), MAX(last_updated) FROM lm_sports_clv;
-- n=10101  earliest=2026-02-11 02:36:17  latest=2026-02-12 04:59:52
```

Distribution by sport:
| sport | n |
|-------|---|
| basketball_ncaab | 7,450 |
| basketball_nba | 1,664 |
| soccer_usa_mls | 885 |
| americanfootball_ncaaf | 54 |
| icehockey_nhl | 48 |

All 10,101 rows ingested in a 24-hour window (Feb 11-12) — single one-shot backfill, no recurring writer.

## Root cause chain

1. **Workflow exists** — `.github/workflows/sports-betting-refresh.yml` schedules CLV backfill 5×/day at `0 15,18,21,0,3 * * *` UTC.

2. **Workflow calls** `python3 live-monitor/oddsharvester_clv_backfill.py --save-json --preferred-book-only --days-back 7 || echo "OddsHarvester skipped"` (line 437).

3. **Script bails early** — `oddsharvester` Python package is not installed in the workflow environment (not in any `requirements.txt`, not in the workflow's pip install steps). Lines 297-299 of `oddsharvester_clv_backfill.py`:
   ```python
   if not _HAS_ODDSHARVESTER:
       _log('oddsharvester not installed — nothing to do. Exit 0 for CI.')
       return 0
   ```
   Workflow shows green ✓ but produces zero data.

4. **`--save-json` mode would also be broken** — output dir is `live-monitor/backfill/clv/` on the GHA ephemeral runner. Files vanish at runner shutdown. No artifact upload, no DB push.

5. **`--inject-api` mode would also be broken** — relies on `findtorontoevents.ca/live-monitor/api/sports_clv.php?action=inject` endpoint that **does not exist**. Script docs (lines 25-26) explicitly note: *"The actual DB write endpoint (sports_clv.php?action=inject) is **not** assumed to exist yet."*

## Fix sequence (P1, queued for next session)

| Step | Effort | Effect |
|------|--------|--------|
| 1. Add `oddsharvester` to workflow pip install | 5 min | Unblocks script execution |
| 2. Verify scrape yields rows for at least 1 sport | 20 min | Proves OddsPortal still scrapeable |
| 3. Build `live-monitor/api/sports_clv.php?action=inject` endpoint OR a direct-MySQL writer Python script | 2-4 hr | Persists data |
| 4. Wire workflow to call `--inject-api` mode (replaces `--save-json`) | 5 min | Closes loop |
| 5. Backfill the 86-day gap by running `--days-back 90` once | 10 min | Restores history |
| 6. Add Q11b-style daily monitoring assertion (rows in last 24h > 0) to workflow | 15 min | Prevents future silent failures |

## Why this matters

- **Goal #2 (sports betting):** without CLV, we cannot validate whether picks beat the closing line — the gold-standard predictor of long-term EV.
- **Sports ML calibration (Q12 finding):** `lm_sports_ml_predictions.actual_outcome` is also NULL across all rows → no calibration signal AT ALL right now. CLV is the alternative truth signal until that's wired.
- **NBA STRONG TAKE +164% / NHL STRONG TAKE -100% (3-trade samples)** noted in earlier sessions — too small to be meaningful without CLV/closing-line truthing.

## Detection: prevent silent failure recurrence

Add to `sports-betting-refresh.yml` after the CLV step:

```bash
RECENT_CLV=$(mysql -h mysql.50webs.com -u ejaguiar1_sportsbet -p"$DB_SPORTS_PASS" ejaguiar1_sportsbet -se \
  "SELECT COUNT(*) FROM lm_sports_clv WHERE last_updated >= NOW() - INTERVAL 25 HOUR")
if [ "$RECENT_CLV" -lt 1 ]; then
  echo "::error::CLV pipeline silent failure — 0 rows in last 25h"
  exit 1
fi
```

Without this, "OddsHarvester skipped" stays green forever.

## Files

- This doc: `reports/sports_clv_pipeline_gap_2026-05-09.md`
- Backing: `reports/db_query_bank_2026-05-07/FINDINGS.md` Q11b
- Script: `live-monitor/oddsharvester_clv_backfill.py`
- Workflow: `.github/workflows/sports-betting-refresh.yml` line 437
- Schema: `lm_sports_clv` on `ejaguiar1_sportsbet`
