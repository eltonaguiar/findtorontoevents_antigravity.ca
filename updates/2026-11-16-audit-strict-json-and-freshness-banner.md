# /audit panels: strict-JSON publish guard + honest freshness banner

**Date:** 2026-11-16
**Scope:** `audit_dashboard/dashboard_freshness.js`, `tools/audit_pick_funnel/build_ic_analysis.py`,
`tools/deploy_audit_files.py`, two committed `/audit/data/*.json` artifacts, one new test file.
**Evidence:** `updates/2026-11-16-audit-dashboard-live-truth-check.md` (live probes, 2026-11-16 ~03:00Z).

## What was broken

Two panels on https://findtorontoevents.ca/audit read "no data" while their payloads returned
HTTP 200 with fresh timestamps:

| Payload | Problem token | Panel symptom |
|---|---|---|
| `strategy_ic_analysis.json` | bare `"pf": Infinity` | "Failed to load IC analysis data… endpoint may be unreachable" |
| `money_ready_verdict.json` | bare `"dsr_score": NaN` (2x) | Money Ready tile: "No data available / unknown" |

Python's `json` module accepts **and emits** `NaN` / `Infinity` by default, so every server-side
check called these files valid. The browser's `JSON.parse` rejects the **entire document** on the
first such token — a 42 KB file fails over one value.

Three separate defects kept this alive:

1. **The IC builder manufactured the bad value.** `build_ic_analysis.py` computed
   `pf = gross_win / gross_loss if gross_loss > 0 else inf` and then wrote
   `round(pf,4) if pf != inf else "Infinity"`. The pre-2026-05 build emitted a bare `Infinity`
   token (unparseable); the current one emits the *string* `"Infinity"` (parseable, but a type
   landmine for anything doing numeric math on `pf`).
2. **The deploy list had dropped the IC file.** `strategy_ic_analysis.json` was removed from
   `tools/deploy_audit_files.py:UPLOADS`, so the live copy was frozen at the 2026-05-29 build —
   i.e. the permanently broken one. Nothing could ever repair the panel.
3. **The committed data artifacts themselves were invalid.** `audit_dashboard/data/
   money_ready_verdict.json` carried 2 bare `NaN` and `strategy_ic_analysis.json` carried the
   string sentinel; the deploy ships exactly these bytes, so fixing the generators alone would
   not have changed what the site serves.
4. **The freshness banner could not see a dead source.** `buildFreshnessPanel()` computed
   `hasStale` only from `freshness.level === 'red'`. A source that failed to load has
   `timestamp: null` → level `unknown`, which is neither red nor counted — so the panel printed
   **"DATA FRESHNESS — ALL SOURCES CURRENT"** directly above a tile reading "No data available".

## What changed

- **`tools/audit_pick_funnel/build_ic_analysis.py`** — a non-finite PF is now `None` (JSON `null`)
  instead of `inf` / `"Infinity"`, per the repo measurement contract ("null plus reason, not
  999/infinity"), and the writer uses `allow_nan=False` so any other non-finite value fails at
  build time instead of publishing.
- **`tools/deploy_audit_files.py`** — new `_strict_json_problem()` / `_sanitize_json_bytes()`
  applied to every `.json` target. A payload the browser cannot parse is uploaded as a sanitized
  copy (non-finite → `null`) with `SANITIZED (non-strict token …)` in the deploy log, so the repo
  artifact stays exactly what the builder wrote. `strategy_ic_analysis.json` is re-added to
  `UPLOADS` so the panel can finally refresh.
- **`audit_dashboard/data/money_ready_verdict.json`, `strategy_ic_analysis.json`** — regenerated
  in place with non-finite values / string sentinels replaced by `null` (46,243 → 46,245 B;
  41,205 → 41,188 B).
- **`audit_dashboard/dashboard_freshness.js`** — `hasMissing` joins `hasStale` in the verdict;
  the header downgrades to amber `SOURCE NOT LOADING`, and the affected tile carries
  "No timestamp — file missing, unreachable, or not valid JSON. Treated as unverified, not current."
- **`tests/test_deploy_audit_files_strict_json.py`** — 6 offline tests covering bare `NaN`,
  `±Infinity`, non-UTF-8, the quoted-sentinel case, sanitizer round-trip, and preservation of
  finite values.

## Verification

```
python3 -m py_compile tools/audit_pick_funnel/build_ic_analysis.py tools/deploy_audit_files.py   # OK
node --check audit_dashboard/dashboard_freshness.js                                              # OK
python3 -m pytest -q tests/test_deploy_audit_files_strict_json.py                                 # 6 passed
```
Both repaired artifacts re-parse under `json.loads(..., parse_constant=raise)` — the exact
strictness the browser applies — with 0 `NaN`/`Infinity` tokens remaining.

## Not verified here

- No deploy was run (needs `FTP_USER`/`FTP_PASS`); the live files keep their current bytes until
  the next `audit-dashboard.yml` deploy step or a manual `tools/deploy_audit_files.py` run.
- The repaired money-ready artifact will be overwritten by the next
  `money_ready_snapshot.py` run; that writer is already sanitizing (see
  `tests/test_money_ready_verdict_strict_json.py`), so the regeneration should stay strict.
- The builder needs `audit_dashboard/data/dashboard_data.json` to run, so `build_ic_analysis.py`
  was compile-checked, not executed end-to-end.
