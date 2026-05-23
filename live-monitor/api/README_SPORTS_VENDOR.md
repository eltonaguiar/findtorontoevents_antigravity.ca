# Sports betting API — vendoring

## Already in this repo (baseline)

| Asset | Source |
|--------|--------|
| [../sports-betting.html](../sports-betting.html) | Pulled from `https://findtorontoevents.ca/live-monitor/sports-betting.html` |
| [../sports-betting.js](../sports-betting.js) | Pulled from `https://findtorontoevents.ca/live-monitor/sports-betting.js` |
| [.github/workflows/sports-betting-refresh.yml](../../.github/workflows/sports-betting-refresh.yml) | Already tracked |

## Must copy via FTP (PHP is not published as source)

Download from production (see [ftp-credentials.mdc](.cursor/rules/ftp-credentials.mdc) — typical remote path `/findtorontoevents.ca/live-monitor/api/`):

- `sports_odds.php`
- `sports_picks.php`
- `sports_bets.php`

Place them in this directory: `live-monitor/api/`.

Commit **as-is** first, then wire in:

- `require_once dirname(__FILE__) . '/sports_metrics_lib.php';`
- Replace any duplicate win-rate logic with `sports_compute_settled_metrics($rows)`.

## Schema checklist

Run on MySQL:

```sql
DESCRIBE lm_sports_bets;
```

Confirm or add:

- `closing_odds` (DECIMAL) for CLV — backfill optional script TBD
- Column names for `market` vs `bet_type`, `book` vs `bookmaker` — update [../sql/v_sports_forensics.sql](../sql/v_sports_forensics.sql) accordingly before applying the view.

## Forensics view

Apply after column names match:

```bash
# mysql ... < live-monitor/sql/v_sports_forensics.sql
```

On older MySQL, replace `CREATE OR REPLACE` with `DROP VIEW IF EXISTS` + `CREATE VIEW`.
