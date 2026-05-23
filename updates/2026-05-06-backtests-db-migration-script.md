# Backtests DB migration helper added

## What was needed

We need to move bulk backtesting data out of `ejaguiar1_stocks` into the empty
`ejaguiar1_backtests` database, while keeping credentials out of source code and
using only environment variables / secrets.

## What changed

- Added `tools/migrate_backtests_to_backtests_db.py`.
- The script copies backtest-heavy tables from source DB to target DB using MySQL
  SQL (`CREATE TABLE ... LIKE` + `INSERT INTO target SELECT * FROM source`).
- Default source/target:
  - `SOURCE_DB_NAME=ejaguiar1_stocks`
  - `TARGET_DB_NAME=ejaguiar1_backtests`
- Default tables:
  - `bt_backtest_trades`
  - `bt_backtest_runs`
  - `backtest_trades`
  - `backtest_results`
  - `at_large_backtest_results`
  - `at_incubator_backtest_results`
- Supports:
  - `--dry-run` (count/visibility checks only)
  - `--truncate-target` (re-run clean copy)
  - `--tables ...` (custom subset)
  - `--stop-on-error`

## Credential handling

No passwords are hardcoded in the new script. It reads from env variables
compatible with GitHub Secrets / FTP-side `.env` conventions:

- Host/port: `MYSQL_HOST`, `MYSQL_PORT`
- Source DB creds: `SOURCE_DB_USER`/`SOURCE_DB_PASS` (fallback to `AUDIT_DB_*`)
- Target DB creds: `TARGET_DB_USER`/`TARGET_DB_PASS` (fallback to `BACKTESTS_DB_*`)

## Verification done

- Python syntax validation:
  - `python -c "import py_compile; py_compile.compile('tools/migrate_backtests_to_backtests_db.py', doraise=True)"`
- Repository scan confirmed these SQL dumps map as expected:
  - `(9).sql` => `ejaguiar1_backtests` (empty skeleton)
  - `(8).sql` => `ejaguiar1_stocks` (contains `bt_backtest_trades`, `bt_backtest_runs`, and other backtest tables)

