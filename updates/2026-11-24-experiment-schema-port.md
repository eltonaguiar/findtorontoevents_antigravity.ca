# 2026-11-24 — `docs/experiment_schema.sql` shipped to main, tracker de-duplicated

## What was broken

Three separate defects, found by measuring rather than assuming:

1. **The file was absent from `main`.** `docs/experiment_schema.sql` existed only
   in the `vanilla-handsaw` worktree on branch `feat/profitability-scorecard-2026-11-24`.
   The verification command therefore raised `FileNotFoundError`, not a count mismatch.

2. **The only copy was Postgres-flavoured.** `UUID`, `BIGSERIAL`, `JSONB`,
   `TIMESTAMPTZ`, and `DEFAULT now()` at line 131. `executescript` parses the whole
   script, and SQLite rejects `DEFAULT now()`. Copying the file verbatim would have
   converted a `FileNotFoundError` into an `OperationalError` — still no table count.

3. **The tracker had silently drifted from the contract.** `tools/experiment_tracker.py`
   declared its own five-table `SCHEMA` literal (`runs`, `run_params`, `metrics`,
   `artifacts`, `mc_runs`) while the schema file specifies twelve. `docs/evaluation_harness.md:18`
   asserted the two were the same thing. Nothing failed, because nothing compared them.
   The seven missing tables (`market_events`, `signals`, `orders`, `fills`, `positions`,
   `portfolio_snapshots`, `risk_events`) are exactly the audit trail that makes
   "same code path in every mode" checkable.

## What changed

- `docs/experiment_schema.sql` (new) — SQLite port of the twelve-table DDL. Mechanical
  substitutions only: `UUID`→`TEXT`, `BIGSERIAL`→`INTEGER PRIMARY KEY`,
  `TIMESTAMPTZ`→`TEXT`, `JSONB`→`TEXT`, `DOUBLE PRECISION`→`REAL`, `BIGINT`→`INTEGER`,
  `DEFAULT now()`→`DEFAULT CURRENT_TIMESTAMP`. All `CHECK` constraints kept verbatim.
  Two deliberate deviations: `IF NOT EXISTS` (so `init_db()` stays idempotent) and
  **no `AUTOINCREMENT`** (it creates an implicit `sqlite_sequence` table, which would
  make the count 13).
- `docs/experiment_schema.pg.sql` (new) — the Postgres original, preserved. It is the
  dialect that can actually enforce `JSONB`/`TIMESTAMPTZ`, so deleting it to make a
  test pass would be destroying evidence.
- `tools/experiment_tracker.py` (new on main) — the branch version, with its
  `SCHEMA` literal replaced by `load_schema()` reading the file. `init_db()` unchanged
  otherwise.
- `tests/test_experiment_schema.py` (new) — 14 tests, including the drift guard
  (`test_tracker_does_not_declare_its_own_ddl`), the contract-order assertion, the
  idempotency check, and the tracker round-trip / append-only-API assertions.

## Verification

```
python3 -m pytest tests/test_experiment_schema.py -q
14 passed in 0.13s

python3 -c "import sqlite3,pathlib;db=sqlite3.connect(':memory:');db.executescript(pathlib.Path('docs/experiment_schema.sql').read_text());print(len([r for r in db.execute(\"select name from sqlite_master where type='table'\")]))"
12
```

Note: this machine has no `python` on `PATH`, only `python3`; the command was run with
`python3`. The invoked code is identical.

The drift guard was verified to actually fail: the first run of the test suite failed
`test_tracker_does_not_declare_its_own_ddl` because my own comment contained the words
"CREATE TABLE". The test now strips comment lines before searching, so prose about the
rule does not satisfy it while a real statement would.

## Scope

No verdict, tally, metric, or dashboard payload was touched. The settled
`0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` tally is unchanged by this work.

## Provenance

Ported from `feat/profitability-scorecard-2026-11-24` in the `vanilla-handsaw` worktree.
Not invented here; the DDL content is the peer branch's, the dialect port and the
de-duplication are this change.
