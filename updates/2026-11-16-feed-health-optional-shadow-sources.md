# Feed Health: registered-but-empty shadow PM sources no longer fail the gate

**Date:** 2026-11-16 ~05:35Z
**Scope:** `.github/workflows/feed-health.yml` dependency chain (`audit_trail/dashboard_payload_health.py`)

## What was broken

`Feed Health Check` was the **only workflow failing on `main`** in a fresh 360-workflow
sweep (run #3816 / 43806313904, 04:48:47Z, attempt 2):

```
MISSING system rows (2): ['pm_kalshi_re_signals', 'pm_polymarket_re_signals']
• `pm_kalshi_re_signals` — missing_from_payload
• `pm_polymarket_re_signals` — missing_from_payload
##[error]Process completed with exit code 1.
```

Root cause is a wiring/ownership mismatch introduced by the 2026-11-16 prediction-market
registration:

- `audit_trail/dashboard_generator.py` (line ~4304) appends both systems to
  `JSON_PICK_SOURCES`, so `dashboard_payload_health.py` treats them as **required**
  payload rows.
- Their producers (`alpha_engine/polymarket_signals.py`, `alpha_engine/kalshi_signals.py`)
  run in `audit-dashboard.yml` lines 126–127 **non-fatally**
  (`|| echo "::warning::… non-fatal"`), because they depend on live venue APIs.
- Neither has produced `alpha_engine/data/polymarket_signals.json` /
  `kalshi_signals.json` data that reaches the published payload: the live
  `audit/data/dashboard_payload.json` (generated 04:09Z) contains neither name.

So a best-effort, paper-only shadow feed made an hourly CI gate permanently red — the
gate asserted "every registered source must have rows", which is not true of a source
that has never emitted rows.

## What changed

`audit_trail/dashboard_payload_health.py`:

- New `_OPTIONAL_SYSTEMS = {"pm_kalshi_re_signals", "pm_polymarket_re_signals"}` with a
  comment stating the rule: optional = producers are best-effort and have not yet
  produced rows; a healthy source must never be listed here; review after 7 consecutive
  days of rows.
- Missing-source accounting now splits into:
  - `missing_systems` → appended to `problems` → **still fails** the gate (real wiring
    regressions keep failing).
  - `optional_missing` → new dataclass field + `OPTIONAL sources with no rows yet
    (warning, not failure): [...]` line in `summary_lines()` → surfaces in the CI log and
    Slack message, but does not set `ok=False`.

Nothing else changes: `_HIDDEN_SYSTEMS` / `_GHOST_SYSTEMS` exclusions, payload staleness,
`invalid_numeric_fields`, and the `ok = not problems` semantics are untouched.

## How it was verified

- `tests/test_dashboard_payload_health_optional.py` (4 tests): optional-missing → `ok=True`
  + warning line + empty `missing_systems`; required-missing → `ok=False`; optional-present
  → no warning; hidden/ghost still excluded.
- Existing `tests/test_audit_truth_claims.py` and `tests/test_deploy_audit_files_strict_json.py`
  (11 tests, strict-JSON / wording guards from earlier today) still pass.
- The next scheduled Feed Health run (`35 */1 * * *`) is the live confirmation; the log
  should show the OPTIONAL warning and a green conclusion.

## Not changed (owner decisions)

- The two PM producers still run non-fatally in `audit-dashboard.yml`. If the shadow
  feeds should be live, the fix is a dedicated failing job with credentials — a scope
  decision, not a health-gate bug.
- `stocks1234560` hardcoded-password failures come from a June PR branch
  (`fix/md-action-items-2026-06-05`); `git grep` on `main` finds **0** files, so `main`
  is clean. The stale PR should be closed rather than "fixed".

See `GHACTIONS_2026-11-16/2026-11-16_05-35Z_stale-jobs-and-db-quality/GHACTIONS_STALE_JOBS_AND_DB_QUALITY.MD`
for the full stale-job census and the SQL data-quality findings.
