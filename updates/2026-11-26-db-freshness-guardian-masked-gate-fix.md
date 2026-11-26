# DB Freshness Guardian — unmask the gate (2026-11-26)

## What was broken

`.github/workflows/db-freshness-guardian.yml` runs hourly and is the only thing
watching whether the trading databases are still moving. Its check step read:

```yaml
        run: python tools/db_freshness_check.py
        # Exit 0=GREEN, 1=YELLOW (warning, not failure), 2=RED (failure)
        # continue-on-error: DB secrets may be absent in CI environment;
        # report is still written + uploaded regardless of exit code.
        continue-on-error: true
```

`tools/db_freshness_check.py` returns a tri-state exit code that encodes real
health — `0=GREEN`, `1=YELLOW`, `2=RED`, documented in its own module docstring
and again in the workflow header ("RED = CI failure"). `continue-on-error: true`
discarded all three. **The step could only ever report success**, so a genuinely
stale `live_picks` / `resolver_outputs` / `signal_outcomes` / `backtests` table
produced a passing green checkmark on an hourly schedule.

This is the exact failure mode the guard's own inline comment says it was added
to catch — `tools/db_freshness_check.py:51-53` records that one lane silently
froze 2026-06-12..06-18 (six days) while a neighbouring check stayed green. The
guard was built to surface that class of stall, then wired so it could not.

The reason `continue-on-error` existed is legitimate and worth preserving:
when the CI environment has no DB credentials the script cannot connect and
exits 2. Failing the job on "no secrets configured" would make the workflow red
for an infrastructure reason that is not a data problem. The bug was the
implementation, not the intent — a sledgehammer used where a discriminator was
needed.

## Secondary bug found in the same file

`DB_FRESHNESS_OUTPUT` was:

- documented in the module docstring (line 17: `DB_FRESHNESS_OUTPUT (default: audit_dashboard/data/db_freshness.json)`),
- **explicitly set** by the workflow
  (`DB_FRESHNESS_OUTPUT: audit_dashboard/data/db_freshness.json`),
- and **never read** by `run_freshness_check()`, which hardcoded the path at
  line 451.

So the variable was dead configuration that looked live. Anyone overriding it to
move the report would have silently still written to the default location and
broken the artifact upload. Same defect family as the `concurrency: { queue: max }`
keys removed earlier the same day: a key that parses, looks authoritative, and
does nothing.

## What changed

### 1. New `tools/db_freshness_verdict.py`

Re-derives the pass/fail decision from the report the check **always writes**
(it writes at line 514, *before* the exit code at 526, so the report is available
even when the run is RED). Policy:

| Report state | Job verdict |
|---|---|
| `GREEN` | pass |
| `YELLOW` | pass, annotated as degraded (matches the documented "warning, not failure" contract) |
| `RED`, **every** RED check is a connectivity failure | pass, annotated as unverified |
| `RED`, **any** RED check carries real staleness data | **FAIL** |
| report missing/corrupt (`--strict`) | **FAIL** — a silently broken guard must not pass |

**Discriminator.** `db_freshness_check.py` writes two structurally different
kinds of RED:

```python
# connectivity failure (lines 471-487) — has an `error` key
{"check": "live_picks", "status": "RED", "error": "No stocks DB password ..."}

# genuine staleness (lines 181-211-248-304-385) — has data, no `error` key
{"check": "live_picks", "status": "RED", "minutes_stale": 7431.0,
 "last_pick_at": "2026-11-21T05:00:00Z", "n_active": 0}
```

Presence of `error` marks an environment failure; a RED **without** `error` is a
real finding and fails the job. A RED with **no** per-check detail at all is not
attributed and does not fail (cannot judge, annotates a warning instead).

`classify()` is a pure function (no I/O) so it is unit-testable.

### 2. Workflow: verdict step owns the gate

`continue-on-error: true` is **kept** on the check step — deliberately — so the
report is always written and always uploaded. A new step immediately after it
makes the decision:

```yaml
      - name: Freshness verdict (RED fails, absent DB secrets do not)
        if: always()
        run: python tools/db_freshness_verdict.py audit_dashboard/data/db_freshness.json --strict
```

`if: always()` so the verdict runs even if an earlier step fails. The upload step
is unchanged and still runs on `always()`, so the report survives a failing job.

### 3. `tools/db_freshness_check.py`: honour `DB_FRESHNESS_OUTPUT`

Relative values now resolve against the repo root, so the workflow's declared
value and the artifact upload path agree regardless of cwd. Behaviour is
byte-identical when the variable is unset.

## How it was verified

**Unit tests** — `tools/test_db_freshness_verdict.py`, 20 assertions, all pass:

```
ok   green -> no fail          ok   e2e green exit
ok   yellow -> no fail         ok   e2e yellow exit / warns
ok   data-red -> fail          ok   e2e data-red exit=1 / errors / names check
ok   env-red only -> no fail   ok   e2e env-red exit=0 / warns
ok   mixed -> fail             ok   e2e missing report exit=0 (default) / exit=2 (--strict)
ok   mixed -> 1 data red / 1 env red
ok   bare red -> no fail
ok   empty green -> no fail
ok   unknown overall -> no fail
all verdict tests passed
```

**Real-script end-to-end**, no DB credentials present (the case `continue-on-error`
was protecting):

```
$ python3 tools/db_freshness_check.py          # exit 2
ERROR Stocks DB connect failed: No stocks DB password — set DB_PASS_STOCKS ...
INFO  Overall DB freshness: RED

report: overall=RED
  live_picks        RED  error=YES
  resolver_outputs  RED  error=YES
  signal_outcomes   RED  error=YES
  backtests         RED  error=YES

$ python tools/db_freshness_verdict.py <report> --strict
::warning::DB freshness RED ignored -- every RED is a DB connectivity failure,
           not staleness (secrets likely absent in this environment)
exit 0                                          # <-- still passes, as before
```

**Genuine staleness must fail** — synthetic report shaped from the real
`check_live_picks()` output, `live_picks` 7,431 minutes (5.2 days) stale:

```
::error::DB freshness RED -- genuine staleness in: live_picks.
          live_picks: minutes_stale=7431.0 (last=2026-11-21T05:00:00Z)
exit 1                                          # <-- now fails, previously passed
```

Mixed (one stale + one connect-error) also exits 1 — a real finding is never
hidden by an unrelated connectivity failure.

**Lint** — `actionlint -oneline .github/workflows/db-freshness-guardian.yml` →
exit 0, clean. YAML parses; 6 steps in the expected order with
`continue-on-error: true` only on the check step and `if: always()` on the
verdict + upload steps.

**Env-var fix** — override honoured (`DB_FRESHNESS_OUTPUT=/tmp/override_report.json`
→ written there); default preserved when unset (→ `<repo>/audit_dashboard/data/db_freshness.json`).

## Blast radius / risk

- **Cannot break green builds silently.** If the guard is healthy the verdict
  exits 0. If DB secrets are absent it exits 0 with a warning, exactly as today.
- **Can newly fail** in one case only: a real staleness RED, or a missing/corrupt
  report under `--strict`. Both are intended — that is the whole point.
- **First-run consideration:** if the trading DBs are stale *right now*, this
  workflow will go red on its next hourly run. That would be a true finding, not
  a regression — but expect the possibility.
- No other workflow reads this file's exit code. `concurrency: { queue: max }`
  was already removed on main; nothing here reintroduces it.

## Not done / follow-ups

- Did not tune any threshold in `db_freshness_check.py`. The `THRESHOLDS` values
  (live 2h/6h, resolver 4h/12h, backtests 48h/168h) are untouched.
- The remaining failure-mode question is whether the DB credentials *are* present
  in CI. If they are absent, this guard has been reporting "unverified" for a
  long time and the new warning annotation will finally say so on every run —
  worth checking the first dispatch.
- Broader context: this was the cheapest of the cron failures. The billing
  export shows the 15 failing workflows cost **493 runner-minutes total (<0.1%)**
  of a 577,847-minute footprint; `db-freshness-guardian.yml` is not a cost
  problem. It is a correctness problem — a health check that could not report ill
  health.

---

# Follow-up: the masked RED was a query timeout, and the data really is 197 days stale

While validating the above fix on the self-hosted runner (run `45762821506`,
`laptop-zerou-wsl`), the run reported **success** but carried a
`[failure] Process completed with exit code 2` annotation. That is the masked
gate reproducing live, so I pulled the log:

```
WARNING backtests check error: (2013, 'Lost connection to MySQL server during query (timed out)')
INFO Freshness report written: ... (overall=RED)
INFO Overall DB freshness: RED
##[error]Process completed with exit code 2.
```

Same output on the three preceding cloud runs (`45760639241`, `45754479467`,
`45749836883`) — all `conclusion=success`, all hiding `exit code 2`. So this is
not a self-hosted network artifact; **every hourly run has been RED and reported
green.**

## Root cause

`check_backtests()` ran:

```sql
SELECT MAX(imported_at), COUNT(*) FROM bt_backtest_trades
```

Measured on the live DB: **34,619,493 rows**, and the only indexes are
`PRIMARY(id)`, `backtest_run_id`, `symbol`, `asset_class`, `strategy`, `status`.
There is **no index on `created_at` or `imported_at`**. So `MAX()` over that
column is a full table scan on top of a full `COUNT(*)` scan, against
`read_timeout=30` on the remote `mysql.50webs.com` host. Reproduced directly:

| Query | Result | Time |
|---|---|---|
| `SELECT MAX(imported_at), COUNT(*)` | `(2013, Lost connection … timed out)` | **30.0s** |
| `SELECT imported_at … ORDER BY id DESC LIMIT 5000` | `max=2026-05-13 00:03:45` | **0.1s** |
| `information_schema.TABLES.TABLE_ROWS` | `34619493` | 0.1s |

It could never succeed. The exception set `result["error"]`, which classified as
a connectivity RED — and `continue-on-error: true` turned that into a green job.

## Fix

`check_backtests()` now uses two index-friendly queries instead of one
full-scanning one:

- newest timestamps come from a **PRIMARY-key tail sample**
  (`ORDER BY id DESC LIMIT TAIL_SAMPLE_ROWS`, default 5000). Walking the PK
  backwards is O(n) regardless of table size; backtest rows are append-only so
  the newest timestamps are in the tail. The result records `sampled_rows` and
  `sample_truncated` so the approximation is visible in the report rather than
  implied.
- `n_total` comes from `information_schema.TABLES.TABLE_ROWS`, flagged
  `n_total_is_estimate: true`. It is reported only — never used to grade
  freshness.

`TAIL_SAMPLE_ROWS` is a module constant with a comment explaining when to raise
it (a table that backfills old rows with high ids would break the tail
assumption).

## End-to-end verification (live DB)

`python3 tools/db_freshness_check.py` → exit 2, and the report now contains:

```
check               backtests
table               bt_backtest_trades
status              RED
minutes_stale       284017.0
last_trade_at       2026-05-13 00:03:45
n_total             34619493
n_total_is_estimate True
sampled_rows        5000
sample_truncated    True
```

No `error` key, so this is a **real staleness** RED, not connectivity. Combined
with the verdict gate above, the job will now **fail** — which is correct.

## What this means

The backtests table is **197 days stale** (`bt_backtest_trades` last written
2026-05-13). The guardian has never been able to report it: first because the
query always timed out, then because the error was masked. After this branch,
the guard goes red and stays red until the backtests import is repaired. That is
the guard doing its job, not a regression.

Note `last_trade_at` is a tail *sample* max, not a proven global max. For an
append-only table the two agree unless rows were backfilled with high ids.
