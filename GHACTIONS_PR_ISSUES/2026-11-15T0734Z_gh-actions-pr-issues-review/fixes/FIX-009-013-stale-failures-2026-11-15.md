# FIX-009…013 — Stale-failure triage (past 3 days, no subsequent success)

**Date:** 2026-11-15 · **Method:** enumerated all 367 workflows, fetched each one's latest completed run since 2026-11-12, flagged those whose latest run = `failure` (no later success).

Result: **10 stale failures**. 5 actionable on `main` (below); the rest are environmental/branch/known (see table).

| Workflow | Root cause | Fix |
|---|---|---|
| `daily-prices-yf-refresh` (FIX-009) | `ModuleNotFoundError: No module named 'tools'` — `tools/refresh_daily_prices_yf.py` had a **hardcoded** `sys.path.insert(0, "/home/eaguiar2015/...")` (operator's local box). On GHA the repo path differs. | Replaced with portable `Path(__file__).resolve().parent.parent` repo-root insert. |
| `edge-stability-daily` (FIX-010) | Raw `git push` → `! [rejected] main -> main (fetch first)` push race. | Use `bash .github/scripts/safe_push.sh` (+ `TOKEN_FOR_PUSH`). |
| `pead-shadow-collector` (FIX-011) | Hand-rolled 10-attempt push loop still exhausted under concurrent main pushes. | Replaced loop with `safe_push.sh`. |
| `daily-price-refresh` (FIX-012) | Calls **dead** `fetch_prices.php` (HTTP 404); superseded by daily-prices-yf-refresh. | Retired → `daily-price-refresh.yml.disabled`. |
| `robust-edge-miner` (FIX-013) | `sys.exit(1)` whenever a NEW robust candidate appears ("fail-LOUD = good news") → permanently red. | Now `::warning` + step summary + artifact, **exit 0**. A new candidate is good news, not a CI error. Unreadable-JSON still fails. |

## Not changed (out of scope / environmental / known)
| Workflow | Why |
|---|---|
| `mirror-site` | FTP flakiness + cert verification disabled (infra). |
| `qa-market-validation` | Correctly red — real data quality (see FIX-006). |
| `verified-pilot-daily` | Real sub-step failure; now diagnosable via `failed_steps` (FIX-003b). |
| `hc-parity` | Runs only on `pull_request` for branch `feat/stop-fill-cost-gate-final-v3` — belongs to a PR, not main. |
| `mermaid-test-deploy` | Runs only on `push` to branch `wiring` — not main. |

## Verification
- All edited workflows parse with `yaml.safe_load` ✅
- `tools/refresh_daily_prices_yf.py` compiles and `import tools.db_env` resolves via the new path ✅
- robust-edge-miner snippet simulated with a synthetic candidate → prints `::warning`, exits 0 ✅

## Testing note
`edge-stability-daily` and `pead-shadow-collector` **push data to `main`**; triggering them from the feature branch would run `safe_push.sh HEAD:main` on branch code, so they are validated by YAML/compile + next scheduled run after merge — not manually dispatched from the branch.