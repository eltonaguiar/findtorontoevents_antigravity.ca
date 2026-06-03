## What was broken

The live sports endpoints under `https://findtorontoevents.ca/live-monitor/api/` are currently returning:

- `{"ok":false,"error":"Sports DB connection failed"}`

This is not a generic network outage. The code path in `live-monitor/api/sports_db.php` reads `DB_SPORTS_PASSWORD` from `live-monitor/api/.env`, and the live diagnostics showed 50webs returning an access-denied error for MySQL credentials. That points to server-side credential drift or a stale/missing `.env`.

## What I changed

I added an explicit credential-refresh path to `tools/deploy_sports_files.sh`:

- new flag: `--include-env`
- it uploads `live-monitor/api/.env` alongside the normal sports files
- source of truth:
  - prefer a local `live-monitor/api/.env` if present
  - otherwise synthesize a temporary `.env` from exported `DB_STOCKS_PASSWORD` and `DB_SPORTS_PASSWORD`

This keeps secrets out of git while giving operators a repeatable way to repair production credential drift.

## Why this matters

Before this change, the sports deploy helper could sync PHP files but had no sanctioned way to refresh the hidden `live-monitor/api/.env` credential file. That made outages like this one operationally awkward: the code could be correct while production stayed broken because the secret file on 50webs had drifted.

## Safe repair path

When you have explicit approval to update production, run:

```bash
DB_STOCKS_PASSWORD=... \
DB_SPORTS_PASSWORD=... \
FTP_USER=... FTP_PASS=... \
tools/deploy_sports_files.sh --include-env --force
```

Use `--force` here because the pre-deploy smoke is already red while production is broken; the post-deploy smoke is the real confirmation step.

## How it was verified

- Traced the live sports failure path through `live-monitor/api/sports_db.php` and `live-monitor/api/db_config.php`.
- Confirmed the live production endpoints currently fail on the same DB-connection error.
- Confirmed locally that working 50webs credentials exist for both `ejaguiar1_stocks` and `ejaguiar1_sportsbet`, so the likely issue is production-side secret drift rather than database unavailability.
- Syntax-checked the updated deploy helper with `bash -n`.
