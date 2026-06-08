# GHA Hourly Health Monitor — 2026-06-08

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Note:** Last CI Tests run on main was 2026-06-06T21:41Z (run #27074654009) — ~39h ago with no new push since. All 30 runs in the scanned window (2026-06-05T14:36Z → 2026-06-06T21:41Z) are failures. 31 tests failed / 6125 passed in the most recent run.

**Failure clusters (AUTHOR_FIX required):**

| Cluster | Tests | Root symptom |
|---|---|---|
| FOREX hard-disable gate | 4 | `FOREX_HARD_DISABLE` defaults OFF (passes) instead of ON (blocks); `passes_active_gate` returns True for FOREX |
| mysql_sync category case | 8 | Category inference returns `'CRYPTO'` (uppercase) instead of `'crypto'` (lowercase) — test contract violated |
| M096 CTF concentration cap | 4 | Gate returns `False` in fail-open and skip cases — should be `True` (pass-through) |
| Money ready verdict | 7 | Returns `NOT_READY` in cases expecting `WATCH` or `MONEY_READY` — likely stricter gate added |
| PEAD signal generation | 2 | Zero signals generated where 1–3 expected |
| ETF tight gate | 3 | Gate blocks scores ≥55 that should pass (standard or tight floor=60) |
| EQUITY dragger blocks | 1 | `('EQUITY','multi_asset_copytrader')` not found in `BLOCKED_ASSET_STRATEGY_PAIRS` despite PR #552 claiming to add it |
| M001 COT stale gate | 1 | `test_multi_asset_cot_source_stamped` assertion fails |
| PF registry tournament DB | 1 | `test_tournament_loader_transforms_db_rows` returns 0 instead of 2 rows |

**Most recently merged PR:** #552 "feat(ops): PEAD shadow cron + EQUITY dragger blocks" merged 2026-06-05T14:42Z (correlated with CI failure onset). Failures span multiple unrelated modules — breadth suggests either shared dependency regression or accumulation of pre-existing failures surfaced by the same push.

**Chronic workflows:** none detected

- `Sports endpoint smoke + Playwright`: 15/15 success (2026-06-07T15:45Z → 2026-06-08T11:55Z) — GREEN
- `Claude Gainer ML Live Scanner`: 15/15 success — GREEN
- All 29 other scanned workflows in 30-run snapshot: success or skipped — GREEN

**Open PRs RED:**

| PR | Title | CI Status | Classification | Recommended action |
|---|---|---|---|---|
| #553 | feat(picks-now): multi-factor quant screener | Unknown (no CI run since creation 2026-06-06T04:37Z) | N/A — CI Tests is RED on main; any PR CI would inherit same failures | Author must wait for main CI to go green |

**Action required:**
- **Operator/author should fix the 31 failing tests listed above on main.** Highest-priority clusters: FOREX gate regression (production quality gate degraded), M096 CTF fail-open broken (live gate blocks valid picks), money ready verdict over-blocking.
- PR #552 is the closest causal candidate — review `alpha_engine/quality_gates.py`, `audit_trail/quality_gates.py`, and `tools/mysql_sync.py` (or equivalent) for case-normalization change.
- `alpha_engine/backtest_quant_algorithms.py` has invalid Python syntax at line 1 (surfaced by coverage parser) — may be a separate issue.
- Run link: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27074654009
