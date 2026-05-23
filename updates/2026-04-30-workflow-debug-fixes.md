# 2026-04-30 — Workflow Debug & Fixes

Five GitHub Actions workflows were failing on the latest scheduled run for
`main`. This doc captures the methodology I followed to triage each failure,
the root cause for each, and the surgical fix applied.

## Methodology

1. **Inventory.** Pulled the most recent ~300 completed runs for `main` via
   the GitHub Actions API and grouped them by workflow → conclusion. The five
   in-flight failures called out in the task description were:

   | Run ID | Workflow |
   |---|---|
   | 25173508113 | Forward Test Daily |
   | 25173437821 | [torontoevent.net] Forward Test Daily |
   | 25172633679 | ALPHA ENGINE — Dynamic Runner (Cloud or Local) |
   | 25172223911 | ALPHA ENGINE — Live Autonomous Scanner |
   | 25172093096 | Daily Stock Data Refresh |
   | 25174261899 | CI Tests (latest in-progress run failing on the same assertion) |

2. **Pulled the failed-job logs** for each run via
   `get_job_logs?failed_only=true` and read the last 60–100 lines to find the
   actual exception / non-zero exit trigger.

3. **Mapped each error back to the source line** (`grep -n` + `view`) and
   classified it:
   - real defect (code change required), vs.
   - environmental (external HTTP 404 / 50webs host outage) where the
     workflow itself was over-eager about `set -e`.

4. **Applied the smallest possible fix** for each defect, keeping behavior on
   the happy path identical. No new dependencies, no test/lint additions.

5. **Verified locally** with `py_compile` for the touched Python files,
   `python3 -m pytest tests/test_trust_tier_non_crypto_default_on.py` for the
   CI-Tests regression, and `yaml.safe_load(...)` for the workflow YAML.

## Findings & fixes

### 1. Forward Test Daily / [torontoevent.net] Forward Test Daily
**Both runs failed identically** at `STOCKS/competition/forward_test.py:592`:

```
KeyError: 'pnl_pct'
  File ".../forward_test.py", line 535, in cmd_resolve
    _update_summary(data)
  File ".../forward_test.py", line 592, in _update_summary
    pnls = [p['pnl_pct'] for p in picks if p['pnl_pct'] is not None]
```

**Root cause.** `_update_summary` (and the `cmd_status` print loop above it)
hard-indexed `p['pnl_pct']`, but newly-imported OPEN picks don't have a
`pnl_pct` key until the first resolve cycle adds one. The first run after a
new pick lands therefore raises `KeyError` before `_update_summary` can
compute totals.

**Fix.** Three call sites (`forward_test.py:563`, `:578`, `:592`) now use
`p.get('pnl_pct')` so missing keys behave the same as `None` — which is the
sentinel the rest of the code already expects.

### 2. ALPHA ENGINE — Dynamic Runner / Live Autonomous Scanner
Both runs failed at `alpha_engine/production_scanner.py:1246` in
`close_stale_picks`:

```
TypeError: can't subtract offset-naive and offset-aware datetimes
    entry_dt and (now - entry_dt).total_seconds() > STALE_HOURS_THRESHOLD * 3600
```

**Root cause.** `now = datetime.now(timezone.utc)` is tz-aware. The entry-date
parser at `:1232` uses `datetime.fromisoformat(entry_date_str.replace("Z",
"+00:00"))`, which preserves tz only when the source string has an offset.
Some upstream sources persist naive ISO strings (e.g. `"2026-04-30T15:00:00"`
with no offset). When such a pick reached `close_stale_picks`, `entry_dt` was
naive and the subtraction blew up.

**Fix.** After the parse block, treat any tz-naive `entry_dt` as UTC by
attaching `tzinfo=timezone.utc`. This matches the behavior of the
`%Y-%m-%d`-only branch immediately above and is consistent with how the rest
of `production_scanner.py` defaults missing offsets.

### 3. CI Tests — `test_commodity_banned_passes_by_default`
Latest CI run (25174261899) failed only on:

```
FAILED tests/test_trust_tier_non_crypto_default_on.py::test_commodity_banned_passes_by_default
  AssertionError: assert False is True
   +  where False = passes_active_gate({'asset_class': 'COMMODITY', ...})
```

**Root cause.** The test fixture (`_build_pick`) used `CL=F` as the COMMODITY
representative symbol. `CL=F` is in `COMMODITY_BLACKLIST`
(`audit_trail/quality_gates.py:914`), added by the Phase 2-D commodity
sub-class kill on 2026-04-29. `passes_active_gate` therefore correctly returns
`False` regardless of the trust-tier bypass the test was actually trying to
exercise. Other classes in the same test file (EQUITY/FOREX/ETF/BOND/FUTURES)
use whitelisted symbols, which is why only the COMMODITY case failed.

**Fix.** Switch the COMMODITY representative to `HG=F` (copper) — one of the
two symbols `COMMODITY_BLACKLIST` explicitly leaves alive (`HG=F`, `PL=F`).
The test now exercises the trust-tier bypass it was written to verify, and
`pytest tests/test_trust_tier_non_crypto_default_on.py` is green
(18 passed). The blacklist itself behaves correctly and is left untouched.

### 4. Daily Stock Data Refresh
Run 25172093096 failed at the **"Verify cached report data"** step with
`Process completed with exit code 28`. Exit 28 is curl's "operation timeout"
code; under the default `set -e` shell, the timeout aborted the whole step
even though the verification is purely informational and `Step 3` already
sets `continue-on-error: true` for the actual refresh call.

**Root cause.** Steps 4 and 5 (verify report page / verify cached data) ran
without `continue-on-error` and without `|| true` on the curl invocation, so
a transient 50webs timeout — which is also why upstream `import_picks.php`
returned HTTP 404 in the same run — surfaced as a workflow failure even
though no productive step had failed.

**Fix.** Added `continue-on-error: true` to Steps 4 and 5 and an `|| echo`
fallback on each `curl --max-time 15` so timeouts produce an actionable
warning rather than aborting the job. Behavior on the happy path is
unchanged (200 OK still prints the cached stats; non-200 still emits a
`::warning::`).

## Verification

- `python3 -m py_compile STOCKS/competition/forward_test.py
  alpha_engine/production_scanner.py` → OK
- `python3 -m pytest tests/test_trust_tier_non_crypto_default_on.py` → **18
  passed, 0 failed**
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/daily-stock-refresh.yml'))"`
  → OK

## Out-of-scope / not changed

- The HTTP 404 from `findtorontoevents.ca/findstocks/api/import_picks.php` is
  a 50webs deploy / endpoint health issue and is not actionable from this
  repo. The workflow change makes the verify steps non-fatal so a transient
  upstream outage no longer marks the run as failed. The actual refresh step
  was already `continue-on-error: true`.
- Stale "Not run in awhile" workflows listed in the original scan
  (`pages-build-deployment`, `Taste Profile Scanner`, etc.) are scheduling
  questions, not bugs — they need a human decision on whether to re-enable
  rather than a code fix.
- "Sports Prediction Market Sync" / "Pick Monitor & Price Validator (30min)"
  showing `cancelled` are likely concurrency-group cancellations
  (newer-run-supersedes-older), not failures, and don't have a defect
  signature in the logs.
