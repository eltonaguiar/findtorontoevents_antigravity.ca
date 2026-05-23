# UEPS Wiring Report — 2026-04-28

## Summary

Wires the **US Equity Prediction System (UEPS)** modules (built in commit
`1c95eec9f0`, dashboard tab added in `8a9e7e8a2b`) into a recurring runner that
emits a dashboard-scoped JSON artifact, plus client-side fetch/render in
`audit_dashboard/template.html` so the live `/audit` page populates the
`#ueps-section-mount` div.

Aligns with CLAUDE.md MAJOR GOAL #1 (phenomenal performance across all asset
classes on `findtorontoevents.ca/audit`) and the CLAUDE.md Wire-Up Rule —
adds the missing recurring caller for the dashboard surface.

## Files Touched

| File | Action | Lines | Purpose |
|---|---|---|---|
| `tools/run_ueps_pickers.py` | NEW | 181 | Production caller. Loads universe, runs `ValueScreener` + `ShortSideScreener`, writes `audit_dashboard/data/ueps_picks.json`. |
| `.github/workflows/ueps-pick-runner.yml` | NEW | 104 | Cron `15 */4 * * *` runner that invokes the script + commits + pushes via `safe_push.sh`. Mirrors `audit-dashboard.yml` patterns (`fetch-depth: 0`, split concurrency by event_name, `if: always()` on artifact upload). |
| `audit_dashboard/template.html` | EDIT | +118 | Adds client-side fetch of `data/ueps_picks.json` + lightweight DOM-safe card renderer that populates `#ueps-section-mount`. Uses `data-pick-type` attribute so the existing sub-tab filter (long-term/swing/closed) keeps working. Loads on first UEPS-tab click (lazy). |
| `reports/ueps_wiring_2026_04_28.md` | NEW | this file | This report. |

## Wiring Map

| UEPS module | Caller now in production |
|---|---|
| `alpha_engine/value_screener.py` | `tools/run_ueps_pickers.py::run_screeners` (also `alpha_engine/value_screener_runner.py`) |
| `alpha_engine/short_side_screener.py` | `tools/run_ueps_pickers.py::run_screeners` |
| `alpha_engine/fundamentals_fetcher.py` | `tools/run_ueps_pickers.py` (via `build_screener_inputs`) |
| `alpha_engine/earnings_calendar_fetcher.py` | `tools/run_ueps_pickers.py` (via `build_screener_inputs`) |
| `alpha_engine/dividend_history_fetcher.py` | `tools/run_ueps_pickers.py` (via `build_screener_inputs`) |
| `alpha_engine/long_term_pick_contract.py` | `value_screener.py` / `swing_screener.py` (factories used inside screeners; called transitively by runner) |
| `audit_dashboard/ueps_section_renderer.py` | Indirectly: client-side JS in `template.html` mirrors the same card structure (`data-pick-type`, `data-symbol`). Server-side renderer remains opt-in for `dashboard_generator.py` integration in a future PR. |

Modules NOT wired in this PR (deferred):

* `alpha_engine/swing_screener.py` — needs OHLCV-window plumbing from the production
  scanner. The runner emits `swing_picks: []` for now; swing tab shows the
  empty-state placeholder until follow-up PR.
* `alpha_engine/thesis_resolver.py` / `alpha_engine/swing_resolver.py` — owned by
  `value_resolver_quarterly.yml` (already exists; resolver runner wiring is a
  separate PR per the SYNTHESIS phase plan).
* `alpha_engine/value_backtest.py` — backtest harness, not a live runner.

## Test Status

```
PYTHONPATH=. python -m pytest tests/test_ueps_*.py tests/test_long_term_*.py \
  tests/test_swing_*.py tests/test_thesis_*.py tests/test_fundamentals_*.py \
  tests/test_value_*.py -q
→ 209 passed in 5.98s
```

```
PYTHONPATH=. python -m pytest tests/test_ueps_workflow_yaml.py -v
→ 37 passed in 0.34s
```

`python -m py_compile` on every changed/new Python file: clean.
`yaml.safe_load` on the new workflow file: clean.
`grep -c "^<<<<<<<|^=======|^>>>>>>>"` on every changed file: 0 conflict markers.

## Smoke-Deploy Steps (post-merge)

After this PR merges into `main`:

```bash
# 1. (Optional) Manually trigger the runner once to seed the JSON:
gh workflow run ueps-pick-runner.yml

# 2. Wait for the run to finish, confirm the picks JSON committed back:
gh run list --workflow=ueps-pick-runner.yml -L 3
ls -la audit_dashboard/data/ueps_picks.json

# 3. The next hourly audit-dashboard.yml run will regenerate index.html with
#    the new template.html. Or trigger it directly:
gh workflow run audit-dashboard.yml

# 4. FTP-deploy (only after audit-dashboard.yml regenerates index.html):
python tools/deploy_to_ftp.py --audit-only
# (Or wait for the audit-dashboard.yml to FTP-upload via its own deploy step.)

# 5. Verify on production:
curl -sI https://findtorontoevents.ca/audit/ | head -3
# Open https://findtorontoevents.ca/audit/ → click "📈 US Equity Picks" tab.
```

Per CLAUDE.md "Never run dashboard generators locally": the runner script
writes ONLY a JSON artifact. The dashboard generator (`audit-dashboard.yml`)
remains the sole owner of `index.html` regeneration.

## Cross-References

* UEPS sidecar build: commit `1c95eec9f0` — *feat(ueps): add US Equity
  Prediction System (UEPS) — 15 phases, 244/244 tests*
* UEPS dashboard tab + first runner: commit `8a9e7e8a2b` — *feat(ueps):
  wire UEPS into /audit + recreate Performance Charter*
* Project context: `updates/long_term_value_project_2026-04-27/PROJECT.md`
* Synthesis lock: `updates/long_term_value_project_2026-04-27/findings/SYNTHESIS.md`
* Performance charter: `docs/PERFORMANCE_CHARTER.md`
* CLAUDE.md Wire-Up Rule: addressed — production caller exists for every
  UEPS module that has a runtime data path. Modules without a live caller
  in this PR (swing_screener, resolvers, backtest) carry an explicit
  Wiring Plan above.

## Gaps / Follow-Up

1. **Swing screener wiring** — needs OHLCV windows. Will follow once the
   scanner exposes its OHLCV cache to UEPS.
2. **Server-side renderer integration** — `audit_dashboard/ueps_section_renderer.py`
   is not yet called by `dashboard_generator.py`. The client-side fetch
   approach used in this PR was chosen specifically to avoid tangling with
   the dashboard generator while Copilot's parallel `quality_gates.py` work
   is in flight.
3. **n=N/100 counter** is wired client-side from the live picks count, not
   from a closed-track-record count. Once `value_resolver_quarterly.yml`
   resolves picks into `closed_picks.jsonl`, the counter will tick up via
   the same JSON fetch.
4. **Universe expansion** — currently uses the 50-ticker S&P 100 baseline
   from `alpha_engine.value_screener_runner.DEFAULT_UNIVERSE`. PHASE 13
   replaces with the EDGAR companyfacts.zip universe.
