# GHA actions audit — 2026-11-26 (with ports + prune)

Scope: the live Actions query `is:cancelled is:action_required is:failure is:neutral is:queued
is:skipped is:stale is:timed_out is:awaiting`, plus the off-main workflow inventory, plus a
branch-prune pass. Measured window: **2026-11-19T20:48Z → 2026-11-26T20:48Z (7d)**.
Rule applied: if a workflow's *latest* run succeeded, its earlier red runs are ignored.

## 1. Ports landed on main

Commit **`dbdf003d5417cb085592c7e5eb87046dcb9b42a9`** — 3 files, +889:

| file | why it was missing |
|---|---|
| `.github/workflows/forward-ledger-sync.yml` | existed only on `wired-in/buffy-2026-11-15`; every tool it calls was already on main |
| `.github/workflows/deploy-fte-integrations.yml` | existed only on 4 side branches |
| `TORONTOEVENTS_ANTIGRAVITY/integrations/index.html` | 49,784 B public page — **never on main**, so the path-filtered deploy could never fire |

Dependencies verified present on main: `tools/forward_tracker.py`, `tools/build_forward_clock.py`,
`tools/build_benchmark_prices.py`, `.github/scripts/assert_no_conflict_markers.sh`,
`.github/scripts/safe_push.sh`, `audit_dashboard/data/benchmark_prices.json`.

- **forward-ledger-sync**: cron `37 5 * * *`; no run yet (next 05:37Z). Manual dispatch recommended
  once with `dry_run=true` to confirm the payload fetch.
- **deploy-fte-integrations**: fired on the push and on dispatch. The validation step passes
  (49,784 B, no conflict markers, no credential-shaped literals). The **upload** fails:
  `ftplib.error_perm: 530 Login authentication failed` — at 20:58 and again at 21:00, with the same
  `FTP_HOST/FTP_USER/FTP_PASS` that `deploy-fte-index.yml` used successfully at 16:52 the same day.
  So the port is correct; the 50webs account rejects the new login.

**Suggested fix:** the four `deploy-fte-*` jobs share `concurrency: group: fte-ftp-deploy`, but
`audit-dashboard.yml`, `audit3-evidence.yml` and `audit3-ledger.yml` also log into the same 50webs
account without joining it, so two sessions can overlap. Put every 50webs FTP job in
`group: fte-ftp-deploy`, wrap `ftp.login` in a 3× retry with backoff, and confirm the account is not
locked. Until then the integrations page is on main but not published.

## 2. Run health — 7 days

- **1,344** non-success runs: **342 failure**, **934 cancelled**, **68 skipped**. Zero `timed_out`,
  `action_required`, `neutral`, `stale`.
- **261** workflow files were touched by those runs. **228** have a green latest main run → ignored.
- **33** have a non-success latest main run: **10 real red**, 2 skipped by `if:`, 15 in-flight at
  audit time, 6 whose workflow file is not on main (section 4).

## 3. The 10 still-red, with cause and suggested fix

| workflow | failing step | actual cause | suggested fix |
|---|---|---|---|
| `ci-tests.yml` | Run all tests (gating) | `test_audit_metric_invariants.py:50 dashboard_data.json missing`; 3.12 job "found no collectors" | those tests need a generated 25 MB payload that is not committed — `skipif(not path.exists())` on that module or ship a tiny fixture |
| `verification-tests.yml` | Run verification test suites | **25 failed / 7534 passed**: `test_etf_tight_gate_exactly_at_floor` expects score=60 to pass while the gate uses `score < 60`; `test_tournament_loader_transforms_db_rows` returns 0 rows, expected 2; ETF banned-by-default | spec conflicts, not drift — decide per test whether the gate or the assertion is authoritative |
| `deploy_bundle.yml` | Check validation results | `AttributeError: 'list' object has no attribute 'values'`, then `No strategy passed validation` | plain bug in the results-check code; no strategy clears win_rate/p_value/PF/OOS gates |
| `deploy-riseoftheclaw.yml` | Deploy to GitHub Pages | `400 ... in progress deployment. Please cancel <sha> first` | four workflows push Pages (`deploy-bestiejob-page`, `deploy-riseoftheclaw`, `fix-battleground`, `live_tracker`) with **no shared concurrency group** — give all four `group: github-pages` |
| `db-sync-to-mirror.yml` | Import into torontoevent.net | `ERROR 1044 (42000): Access denied for user ... to database '*_news'` and `'*_sportsbet'` | grant the mirror user on those 2 DBs, or drop them from the sync list |
| `sign-coherence-gate.yml` | Gate decision | “wrong-sign pnl count regressed: 1 > 0 baseline. The resolver corruption is growing.” | a new `source_system` emits wrong-sign `pnl_pct`; fix the sign convention in the resolver, then rebaseline |
| `gha-quality-framework.yml` | Commit report | `failed to push some refs` | it commits a report without `safe_push.sh`; use `.github/scripts/safe_push.sh` (rebase + backoff) like the ledger job |
| `clear-channel-command.yml` | Clear Channel | Discord: `lacks permission to delete messages in channel 1476311595977150779` | grant the bot Manage Messages (config, not code) |
| `2hour_challenge.yml` | execute-challenge | cancelled on `fapi.binance.com returned HTTP 451 (geo-blocked)` | US runners cannot reach Binance futures — route through a proxy or skip on 451; otherwise it can never pass |
| `forward-observations-ingest.yml` | Forward-growth watchdog (B3) | `FAIL POD-EQUITY-BREAKOUT has 0 forward rows 7.8d after pre-registration (grace 7.0d) — the emitter never landed` | register that POD's emitter, or mark the hypothesis not-emitted (4 sibling PODs are only WARN, inside grace) |

## 4. Ignore these (verified)

- **934 cancelled** — `cancel-in-progress` superseding and rapid pushes; latest run green.
- **68 skipped** — job-level `if:` / `workflow_run` filters (`rl-agent-ppo`, `pine-generator`).
- **228 / 261 workflows** — later run succeeded; satisfies the ignore rule.
- `ops-laptop-ssh-setup.yml`, `ops-laptop-ssh-tunnel.yml` — exist only on `ops/laptop-ssh`, which no
  longer exists, and are absent from main. Dead history, not a port candidate.
- `pages-build-deployment` — GitHub-managed Pages workflow.
- `db-password-leak-guard.yml`, `masking-policy-lint.yml`, `quant-auditor-fast-pr.yml` — on main, and
  their latest runs are green (on side branches).

## 5. Off-main workflows: port or drop

16 workflow files existed only off-main. 2 are ported (section 1). Of the remaining 14:

**Not port-worthy (active job, but tool absent from main — verified absent):**

`winner-hunt-replay.yml` (`tools/build_winner_hunt_replay.py`), `fund-deep-dive.yml`
(`tools/fund_deep_dive.py` + 5 fund tools), `etf-spread-series.yml` (`tools/etf_spread_sampler.py`),
`class-verdict-gate.yml` (`tools/class_verdict_audit.py`), `artifact-detector.yml`
(`tools/verdict_drift_gate.py`), `audit-surface-gates.yml`
(`tools/check_walkforward_artifact_cells.py`), `gha-actions-health.yml`
(`tools/check_github_actions_health.py`), `sol-breakout-forward.yml`
(`tools/sol_breakout_forward.py`), `bond/commodity/mutual_fund_screener_weekly.yml`
(`tools/build_asset_class_rankings.py`).

None of them can run until its tool lands; porting the YAML alone would only add red runs.

**Do not port:** `runner-smoke-test.yml`, `runner-smoke-test-linux.yml` (self-labelled temporary),
`mermaid-test-deploy.yml` (pushes to the obsolete `wiring` branch).

Cheapest next port: `gha-actions-health.yml` — it is the missing watchdog for exactly this audit.

## 6. gh-pages

No `.github/workflows` on `gh-pages` (API 404). Nothing to port from it. Five main workflows publish
to it: `deploy-bestiejob-page`, `deploy-riseoftheclaw`, `fix-battleground`, `live_tracker`,
`stale-branch-cleanup`.

## 7. Branch prune

- 321 branches pre-run; **269** carry off-main workflow files; **186** add *only* the same 12 retired
  legacy workflow files.
- Only **12** of those 186 have zero unique commits (strict ancestors of main) — the only lossless
  deletions. **157** also add/modify real content (e.g. `buffy/batch-close-rootcause` carries 4 tools
  + 1 test + an `audit_trail` change); 17 are >5 commits ahead. **Do not bulk-delete these** — it
  would drop tools, tests and docs.
- Ran the repo's own policy (`stale-branch-cleanup.yml`: merged-only, ≥30d, no open PR). Dry run:
  7 candidates. Real run **`45895428027` deleted 7**:
  `feat/audit-dashboard-go-live-20261022`, `feat/micro-hold-fix-20261022`,
  `feat/systematic-entry-cell-miner`, `nemotron/audit-copy-trader-stale-check`,
  `nemotron-june-2026-audit`, `rescue/ddee81a6e9`, `rescue/ff726af5ae`.
  Branch count 321 → 315.
- 5 more strict ancestors are younger than the 30-day threshold and the weekly cron will age them
  out: `backup/gha-audit-2026-11-16`, `chore/scrape-events-11pm-toronto`,
  `feat/kimi-stop-record-b4-spy`, `feat/stop-fill-cost-gate-final-v3`,
  `fix/p0-safe-fixes-2026-11-14-main`.
