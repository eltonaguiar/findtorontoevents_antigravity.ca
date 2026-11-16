# Deep-check report — GH Actions (main + branches), 2026-11-16 ~04:02Z

Window: last 1000 runs (≈6h). 947 main / 53 non-main.
Conclusions: **948 success · 27 cancelled · 11 failure · 2 pending · 11 in-progress · 1 skipped.**

## 1. Latest-run failures (11) — all explained
| Workflow | Branch | Time | Verdict |
|---|---|---|---|
| ALPHA Dynamic Runner ×3 | main | 01:22, 01:49, 02:25 | **Known**: old 5-min "Commit results" step timeout. Fixed PR #813 (verified: pre-fix runs reproduce `timed out after 5 minutes`; post-fix run 43799911205 in flight). |
| ml-gatekeeper / mysql-q001 (`path-named`) ×6 | main + fix branch | 01:51–01:54 | **Resolved**: my invalid `on:{}` spurious errors; peer renamed to `.disabled` (`3d1aa94ba5e`). 0 since 01:55Z. |
| **CI Tests** | main | 03:10 | **REAL — see §4.** Red from stale literal-cron assertions. |
| **Regime Terminal** | main | 03:42 | **Resolved by peer** `1eb3a34a71` — same commit-timeout class, step 5m→15m. |

## 2. Cancellations (27) — mostly explained
- **ALPHA (4) + Regime Terminal (2)**: job-timeout kills at the old 60m/5m caps → fixed (#811/#813, peer regime fix).
- **Branch Large File Dup Guard (8)**: fires on **branch pushes** (mine + others') and self-cancels on the stale-branch copies lacking the fixed concurrency. Main is fixed. Zero-runtime impact (branch-only).
- **Misc main hourly (Unified Audit Dashboard, Multi-Asset, Coinglass, etc.)**: single instance each — superseded-run cancels, by design (`cancel-in-progress`).

## 3. Skipped (1)
`Deploy Competition to Live Site` (workflow_run, 03:21) — skipped by its upstream-conclusion gate. **By design.**

## 4. CI TESTS RED — stale literal-cron assertions (ACTION NEEDED)
Peer commit `60d10dcf6515` ("stagger 310 cron lines by crc32") is **good** (kills the `:00` stampede) but
broke 4 CI tests that assert **exact** cron strings:
| Test | Expected | Now | Nature |
|---|---|---|---|
| `test_value_screener_weekly_cron_is_monday_6am_utc` | `0 6 * * 1` | `27 6 * * 1` | minute staggered (benign) |
| `test_swing_screener_daily_cron_is_weekdays_14utc` | `0 14 * * 1-5` | `11 14 * * 1-5` | minute staggered (benign) |
| `test_value_resolver_quarterly_cron_is_first_of_quarter` | `0 7 1 */3 *` | `35 7 1 */3 *` | minute staggered (benign) |
| `test_workflow_has_daily_cron` (skyrocket) | daily `48 14 * * 1-5` | `4 * * * *` **hourly** | **stale test** — workflow was *already* hourly (`33 * * * *`) before the stagger; the test asserts an obsolete daily cron and contradicts the workflow's intent |

**Fix:** reconcile the tests to be **minute-tolerant** (assert hour+day-of-week, not exact minute) so future
staggering doesn't red CI; and decide skyrocket's cadence (hourly vs daily) and align test+workflow. Do **not**
revert the stagger — it's the correct anti-herd fix. *(Owner of the cron work should reconcile; flagged here,
not edited, to avoid conflicting with `fix/gha-cron-interval-inversions`.)*

## 5. SILENT fails inside GREEN runs (the real "everything looks green" trap)
`alpha-engine-live.yml` (latest success) logged:
- `::warning::MySQL sync failed — scan results committed but DB data may be stale until next …`
- `::warning::PEAD cache under-populated (n<10) — vt_earnings_pead returns [] this cycle`

⇒ Workflow is **green** but the **DB sync failed and PEAD emits nothing** → `/audit` alpha data can be
stale while the badge is green. This is the exact silent-failure class to monitor per-job, not per-run.

Sampled clean (no warnings): `audit-dashboard`, `copy-trader-intelligence`, `signal-recorder`, `picks-now-refresh`.

## 6. Branch activity (non-main, 53 runs)
All non-main runs are **push-triggered guard/lint/secret-scan/no-stale-db** on feature branches (mine +
`fix/gha-cron-interval-inversions*`, `hermes/*`, `feat/finpredict*`) or `gh-pages` pages deploys — all
succeed except the stale-branch dup-guard self-cancels. **No duplicate scheduled CI cost** (schedules =
default-branch only).

## 7. Peers are actively fixing in parallel (corroboration)
- `60d10dcf6515` stagger 310 crons (anti-herd) + `f1cf79ddb` concurrency/timeouts on alpha/regime commit steps
  + `1eb3a34a71` regime 5m→15m + secret-scan disabled. These match this session's findings — the fleet is
  converging. Watch for overlap on the CI-test fix (§4).

## Bottom line
- **No unexplained outages.** Every failure maps to a known cause; two are already fixed by this session,
  one by a peer, six were the resolved `on:{}` blip.
- **Two genuine open items:** (a) CI Tests red from stale cron assertions — reconcile tests, don't revert stagger;
  (b) `alpha-engine-live` silent MySQL-sync failure degrading `/audit` freshness under a green badge.
