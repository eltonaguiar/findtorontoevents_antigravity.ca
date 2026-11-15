# 07 — Execution Roadmap (with exit criteria)

Owner column uses roles, not names: `CI` (workflow/config), `DATA` (ledger
integrity), `RESEARCH` (hypotheses), `DASH` (audit publish).

## Phase 0 — Unblock CI and fix the ledger (0–3 days)

| # | Task | Owner | Exit criterion |
|---|------|-------|----------------|
| 0.1 | Merge PR #713 (backup-verify live fetch + dedup) | CI | 0 open `backup-verify` issues after a scheduled run |
| 0.2 | Merge PR #786 (QA keys + rebase + smoke pin) | CI | `QA Market Validation` green |
| 0.3 | Pin `social-prediction-tracker.yml`, `sports-betting-refresh.yml` to `ubuntu-24.04` | CI | Playwright install succeeds in both |
| 0.4 | Guardian exclude-list + retry cap (`04` in GHA audit) | CI | no re-run storm; `run_attempt` capped at 3 |
| 0.5 | **#748** fix: no `exit_price=0.0` flat closes | DATA | `data_integrity_report.json` flat-close ratio ≤ 0.5% |
| 0.6 | Re-derive live stats from clean bars | DATA | PF 120 frozen artifacts gone from verdict payload |

**Gate to Phase 1:** QA green, backup-verify green, integrity report clean.

## Phase 1 — Make the clock run and publish it (1–3 weeks)

| # | Task | Owner | Exit criterion |
|---|------|-------|----------------|
| 1.1 | Merge PR #785 (clock, excess column, benchmark prices) | DASH | tags present in `origin/main` `template.html` |
| 1.2 | Add the two JS files to all FTP lists + `deploy_audit_files.py` | DASH | `curl` of both live JS = 200, not 404 |
| 1.3 | Add `forward-ledger-sync.yml` (daily, own concurrency group) | CI | `ledger.jsonl` grows daily |
| 1.4 | `pick_excess` net-of-cost | DATA | `net_pp` present; gross/net separated |
| 1.5 | `trial_count.json` + DSR/PBO with true count | RESEARCH | PBO computable (≥5 variants) |
| 1.6 | Populate `plan.json` with H-103 + scouts | RESEARCH | `forward_tracker selftest` loads all |

**Gate to Phase 2:** `/audit` shows live "vs Bench" + forward clock; `ledger_rows > 0`.

## Phase 2 — Run the one best hypothesis to significance (3–10 weeks)

| # | Task | Owner | Exit criterion |
|---|------|-------|----------------|
| 2.1 | H-103 ETF dual momentum: forward ledger to 152 windows | RESEARCH | `n_windows ≥ 152`, interim verdicts logged |
| 2.2 | H-201 BTC trend: ship reproducible backtest + forward | RESEARCH | backtest artifact exists; forward started |
| 2.3 | Interim verdicts on `/audit` every 20 windows | DASH | panel updates; no 404 |
| 2.4 | Kill anything breaching kill rules | RESEARCH | `08_ELIMINATION_REGISTER.md` updated |

**Gate to Phase 3:** at least one strategy `SHADOW` with n ≥ 100 (or ≥152
windows) and positive net excess.

## Phase 3 — Promote or kill (10–16 weeks)

| # | Task | Exit criterion |
|---|------|----------------|
| 3.1 | Run Gate 0–9 audit on the leading candidate | written pass/fail per gate |
| 3.2 | If all pass → `PROMOTED`, size live | `money_ready` non-empty for one class |
| 3.3 | If fail → `KILLED`, record reason | elimination register updated |
| 3.4 | Declare MF out of scope or build NAV ingest | manifest updated |

## Success = a falsifiable scorecard on `/audit`

Every class shows exactly one of `KILLED / TESTING(n) / SHADOW / PROMOTED` with
net-of-cost excess vs its benchmark and a CI. The absence of a promoted class is
an acceptable, honest outcome — and far better than the current state where
unverified "wealth beats" masquerade as edge.

## Anti-goals

- Do not add new strategies before the ledger runs.
- Do not count a backtest as proof.
- Do not ship numbers that cannot be re-run from a script in the repo.
