# Sportsbet DB Audit Follow-Up — 2026-05-09

**Original audit:** `reports/SPORTSBET_DB_AUDIT_2026_04_25.md`
**Follow-up date:** 2026-05-09
**Reviewer:** Claude (auto-audit)
**Scope:** Verify §A1 ungraded-picks fix has taken effect; check current ungraded count.

---

## What Was Checked

### 1. SQL migration — `reports/sql_migrations/2026_04_25_sportsbet_fixes.sql` §A1

The §A1 block in the migration file is a **read-only diagnostic SELECT** only:

```sql
SELECT id, pick_date, sport, event_id, home_team, away_team,
       commence_time, market, outcome_name, best_book_key
FROM lm_sports_daily_picks
WHERE result IS NULL
  AND commence_time < NOW() - INTERVAL 1 DAY
ORDER BY commence_time DESC;
```

It flags rows for manual CSV export; it **does not write any settlement or result values**.
The §A1 "fix" was never the settlement mechanism itself — only a diagnostic probe.

### 2. PHP code — `live-monitor/api/sports_picks.php` `settle_picks` action

The settlement-sweep adjustment **did land** in the live file. Lines 1403-1409 show:

```php
// How far back to scan the DB for pending daily picks. Previously this wrongly reused
// daysFrom=3, so any game older than 3 days never entered settlement and stayed pending forever.
$lookbackDays = isset($_GET['lookback_days']) ? intval($_GET['lookback_days']) : 30;
if ($lookbackDays < 1) { $lookbackDays = 1; }
if ($lookbackDays > 120) { $lookbackDays = 120; }
```

This fixes the root cause of the silent-skip bug: pending picks are now scanned up to 30 days
back by default (max 120). Before this fix, `daysFrom=3` (the Odds API window) was also used
as the DB lookback, so any pick >3 days old was never attempted.

**Residual limitation:** The Odds API `/scores` endpoint only returns completed-game data for
up to 3 days back (`daysFrom` 1–3). For picks from 2026-02-12 (≈85 days ago — audit ids 17
and 19), the automatic settler still cannot resolve them via the scores API.
Those rows require the `grade_manual` endpoint (key-authenticated POST with home/away scores).

### 3. Live endpoint — `?action=ungraded_audit`

This action **does not exist** in `sports_picks.php`. The dispatcher handles:
`today`, `edge_policy_audit`, `tier_breakdown`, `performance`, `pick_history`,
`analyze`, `daily_picks`, `settle_picks`, `grade_manual` — no `ungraded_audit`.

### 4. Live endpoint accessibility

All three probe URLs returned **HTTP 403 Forbidden** (server-level restriction, not PHP-level):

| URL | Result |
|---|---|
| `…sports_picks.php?action=ungraded_audit` | 403 |
| `…sports_picks.php?action=today` | 403 |
| `…sports_bets.php?action=summary` | 403 |

The API directory appears to be restricted at the web-server / .htaccess level on 50webs.
No public read endpoint currently exposes a settlement-health metric.

---

## Current Ungraded Count

**Unmeasurable from public endpoints.**

- No `ungraded_audit` action exists in the PHP file.
- All public API endpoints return 403 from the 50webs server.
- Direct DB access (phpMyAdmin) would be required to run the §A1 diagnostic SELECT.

Baseline from 2026-04-25 audit: **≥ 2 confirmed ungraded rows** (ids 17 and 19,
both `2026-02-12` games, `result IS NULL`).

---

## Delta vs Baseline

| Metric | Baseline (2026-04-25) | Today (2026-05-09) |
|---|---|---|
| Confirmed ungraded (spot-checked) | ≥ 2 (ids 17, 19) | Unmeasurable |
| `settle_picks` lookback bug fixed | No | **Yes** (lookback_days param, default 30) |
| `ungraded_audit` endpoint exists | No | **No** |
| Public API accessible | Unknown | No (403) |

The root-cause code fix (lookback_days) is present and improves the system going forward.
However, the specific 2026-02-12 rows cannot be auto-settled (Odds API 3-day limit);
the current count is not verifiable without DB access.

---

## Recommendations

### R1 — Add `ungraded_audit` endpoint (immediate, low-risk)
Add a read-only `action=ungraded_audit` to `live-monitor/api/sports_picks.php` returning:
```json
{"ungraded_count": N, "oldest_commence_time": "...", "sample": [...]}
```
This closes the observability gap. A PR for this is attached to this follow-up.
See `live-monitor/api/sports_picks.php` dispatcher section for insertion point.

### R2 — Manually grade ids 17 and 19 via `grade_manual` (one-time)
The two known 2026-02-12 picks can be resolved by POSTing to
`sports_picks.php?action=grade_manual&key=<ADMIN_API_KEY>` with the final scores for:
- `Santa Clara Broncos vs Seattle Redhawks` (2026-02-12)
- `Washington Huskies vs Penn State` (2026-02-12)

Source: ESPN or sports-reference.com for NCAAB results on that date.

### R3 — Raise `lookback_days` default to 60 (or add a cron job)
The default `lookback_days=30` still won't catch picks in the 31–120 day window unless
explicitly called. A nightly cron calling `settle_picks?lookback_days=90` (key-authed)
would close this gap systematically.

### R4 — Investigate 403 on API endpoints
If the 403 is intentional (IP allowlist), document it. If it's misconfiguration,
restore access to the public `today`/`tier_breakdown`/`performance` actions —
the sports tab depends on these for the live UI.

---

## Reproducer Commands (post-PR merge)

```bash
# Check ungraded count after the new endpoint is deployed:
curl "https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=ungraded_audit"

# Manually settle the two known old picks (requires ADMIN_API_KEY):
# 1. Look up final scores for Santa Clara vs Seattle (NCAAB, 2026-02-12)
# 2. POST to grade_manual
curl -X POST \
  "https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=grade_manual&key=<KEY>" \
  -H "Content-Type: application/json" \
  -d '{"rows":[{"sport":"basketball_ncaab","event_id":"","home_team":"Santa Clara Broncos","away_team":"Seattle Redhawks","commence_time":"2026-02-12 03:00:00","home_score":0,"away_score":0}]}'
```

*(Fill in actual scores and event_id before running.)*
