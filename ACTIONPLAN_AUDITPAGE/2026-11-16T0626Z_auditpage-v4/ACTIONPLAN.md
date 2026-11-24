# Audit-page action plan — auditpage-v4

- **Author:** kilo worktree `.kilo/worktrees/auditpage-v4`
- **Written:** 2026-11-16T06:26Z
- **Scope:** https://findtorontoevents.ca/audit/ — page text, DB health, PnL sanity, per-class profitability, Polymarket/Kalshi, WIRED_IN, GH Actions.
- **Status:** findings + ranked suggestions. No production code changed.
- **Peers read (already on main):**
  - `ACTIONPLAN_AUDITPAGE/2026-11-16T0625Z_kilo_auditpage/00_KILO_AUDIT_ACTIONPLAN_2026-11-16.md` (commit `3ff92974407`)
  - `ACTIONPLAN_AUDITPAGE_2026-11-16T06-23-31Z/ACTIONPLAN_AUDITPAGE.md` (commit `6fa66ddb5b1`)
- **Discarded:** three background subagents in this session. Their tables were not evidence (one returned a generic refusal; one restated the same broken string as the fix; one labelled successful GH runs as BROKEN). Do not merge those outputs.

---

## 1. What all three passes agree on

| Claim | v4 check |
|---|---|
| 0 asset classes money-ready | Confirmed. `audit_surface_truth.json` `money_ready_count=0`, `money_ready_classes=[]`. Headline "0/6" understates it: it is **0/9**. |
| Nothing to size | Confirmed. Policy-clean PF is &lt;1.5 everywhere with n≥100. Best honest lead remains shadow `crypto_rsi5070_us` (net PF ~1.11, CI-LB 0.92, bar 1.15). |
| Ghost rows still 22,947 | Confirmed in `audit_dashboard/data/db_health.json` (`generated_at` 2026-11-16T01:29:16Z). 10 cohorts, all MEMECOIN `meta_strategy`, constant `pnl_pct`, `distinct_entries` 1–4. Top: DOGEUSDT LONG n=3569 @ 1.3226%, DOGEUSDT LONG n=3160 @ 5.0%, WIFUSDT SHORT n=2763 @ -3.0%. |
| Page says ghost rows are gone | Confirmed false. Hard-coded at `audit_dashboard/template.html:857` and `audit_dashboard/index.html:857`: "Ghost rows: 0 (was 22,947)". Live DB health still has 22,947. |
| WON vs PnL sign | No contradiction. `won_pnl_contradiction.contradiction_detected=false`. Non-canonical statuses: 0. |
| IC panel dead | `audit_dashboard/data/strategy_ic_analysis.json` does not exist. Remove the panel or generate the file. |
| Prediction markets stay shadow | Recorded decision (PBO 0.603; copy-trading rejected). No code pin found by peer A. Do not promote. |

**Profitability verdict (do not soften):** no class is profitable at the money-ready bar. COMMODITY is the only class with a slightly positive raw PF (1.03, n=229) and it fails WR and the policy-clean cut (policy_clean n=14, PF 0.17). ETF raw PF 0.022 is a broken emitter, not a strategy. EQUITY WR 59.2% with PF 0.94 is the textbook "WR is not edge" case.

---

## 2. Corrections the finalizer must apply

These are places the two peer plans disagree, or where a peer claim does not survive a direct check.

### 2.1 "PnL integrity 99.5%" overclaims

`db_health.json` `pnl_integrity` metric is **sign consistency**, not magnitude.

- sampled 24,158; sign mismatch &gt;1pp: **130 (0.54%)** — this is the number the page prints as 99.5%.
- naive magnitude mismatch: **6,535 (27.05%)**.

The page label "PnL Integrity (sampled) 99.5%" hides the 27% magnitude gap. Rename the tile to "sign consistency" and show both numbers. Do not treat 99.5% as proof that reported PnL matches entry/exit.

### 2.2 Ghost-row check is green while 22,947 rows exist

`checks.ghost_rows.ok=true`, `threshold_pass=true`, `tier=yellow`. `overall.checks_failed=0`, `banner_should_show=false`, `harness_healthy=true`.

That is why the health strip can look fine next to a truth-layer sentence that is also wrong. Yellow must not count as pass, and `banner_should_show` must be true while `total_ghost_rows>0`. Fix in `tools/db_health_check.py` (the ghost_rows scorer), then delete the hard-coded sentence at `template.html:857`.

### 2.3 Two different "DATA STALE" definitions

- Embedded payload banner: `audit_dashboard/template.html:17878` — `mins > 60` prints "DATA STALE! Check workflow status."
- Freshness panel: `audit_dashboard/dashboard_freshness.js` — red only after **72 hours**.

Both can be true at once. The 60-minute banner is mis-tuned: `audit-dashboard.yml` cron is `10 * * * *` and the job comment says 30–35 min, with `timeout-minutes: 115`. A healthy run routinely ages the embedded JSON past 60 minutes. Raise the banner to match the real cadence (suggest 150 min) **or** show "last success" instead of a false alarm. Do not treat the 60-minute string as a workflow outage by itself.

### 2.4 Dashboard publish is actually behind, for a different reason

Observed on `main`, workflow "Unified Audit Dashboard", 2026-11-16:

| created (UTC) | event | result | run |
|---|---|---|---|
| 03:21 | schedule | **success** | 43797722088 |
| 05:16 | workflow_dispatch | cancelled | 43809108656 |
| 06:04 | workflow_dispatch | cancelled | 43814272618 |
| 06:12 | workflow_dispatch | in_progress at audit time | 43815224263 |

No schedule run appears for 04:10 or 05:10. Concurrency is `group: dashboard-publish`, `cancel-in-progress: false` (`.github/workflows/audit-dashboard.yml:33-42`), so dispatches queue behind a long job and can starve the hourly cron. Last scheduled success was ~3h old at 06:26Z. That is the real freshness defect. Stop manual `workflow_dispatch` pile-ups; let the `:10` cron finish. Do not re-add the `push:` trigger.

### 2.5 Peer GHA "6 broken workflows" is already stale

`ACTIONPLAN_AUDITPAGE_2026-11-16T06-23-31Z` listed runs with no later success. Spot-checks at 06:26Z:

- `actions-failure-guardian` run 43812910225 — **success** (2026-11-16T05:51:13Z).
- `Deploy Rise of the Claw Dashboard` run 43812995439 — **success** (2026-11-16T05:52:02Z).

`db-freshness-guardian` last 10 main runs were all success (latest 2026-11-16T05:18:22Z, run 43809360293). `forward-validator.yml` does not exist (API 404). Do not open fix PRs from that list without a fresh per-workflow history. Canonical GHA work stays in `GHACTIONS_2026-11-16/` and `reports/gha_*_2026-11-16.*`. The "235 stale workflows" figure remains a sampling artifact (real stale/never-run ~20+12).

### 2.6 Prediction-market files: both peers are half right

- `alpha_engine/data/prediction_market_picks.json` **exists** (4.5 KB, `pick_count=2`, source `prediction_market_consensus`: BNBUSDT short, BTCUSDT long). Peer A's "file does not exist" is wrong for this path; peer B's "2 picks" is right.
- `audit_dashboard/data/prediction_market_picks.json` does **not** exist. The dashboard copy is missing.
- `alpha_engine/data/kalshi_signals.json` and `prediction_market_agents/data/kalshi_signals.json` are **both missing**. Peer A's path-split bug stands.
- `audit_dashboard/data/copytrade_pm_consensus.json` exists (43 KB).

`pm kalshi signals` showing SOLUSDT/ETHUSDT/BTCUSDT with `0t` and infinite PF is a display bug on top of the path split, not evidence of a live crypto book. Open trades with 0 closed must render PF as `n/a`, never `∞`. Peer A says the symbol mapping is intentional (`alpha_engine/kalshi_signals.py`); keep that, but label the row "Kalshi crypto series → spot proxy" so it is not read as a spot signal.

### 2.7 WIRED_IN

Agree with peer A: only `2026-11-15T0150Z_childlike-airport` is registered (`wired_in_childlike_active_picks.json`, paper_only, sizing 0). It is a frozen snapshot with no regenerating cron. Either add a rescan job or badge it "static snapshot".

Agree with the 06:23 plan: `WIRED_IN/2026-11-15_0700_scratch-hippodraco/STRATEGY_SHORTLIST.md` still sells 85–100% WR against PBO 0.603 and zero resolved forward trades. That contradicts `prediction_market_copy_trading_rejected`. Strip it from any promotion surface.

---

## 3. Ranked work for the finalizer

Do these in order. Each item names the file to change. None of this is a sizing change.

### P0 — stop the page from lying (small diffs)

1. Delete or data-bind the ghost-row sentence at `audit_dashboard/template.html:857` (and the generated `index.html` twin) so it reads `db_health.json` `total_ghost_rows`. Same pass: drop "TIER-2 PROVEN" treatment of `signal_validation` (PF 0.12, MDD 123%, 90d −118%).
2. In `tools/db_health_check.py`, yellow ghost-row tier must fail the check (`ok=false`, `banner_should_show=true`) while `total_ghost_rows>0`.
3. Split the PnL tile: sign-consistency 130/24158 **and** magnitude mismatch 6535/24158. Source field is already in `db_health.json`.
4. Stale banner at `template.html:17878`: change `mins > 60` to the real publish SLA, and print last scheduled success, not a generic "check workflow".
5. One-line banner: "0/9 classes money-ready. Research ledger, not a money book." Kill mixed headlines (CRYPTO PF 1.25 vs 0.92, EQUITY PF 2.13 vs 0.94, COMMODITY PF 1.77 vs 1.03) or label each with ledger + window.

### P1 — clean the ledger the page aggregates

6. Dry-run then execute ghost cleanup for the 10 MEMECOIN `meta_strategy` cohorts (`tools/cleanup_ghost_rows.py`). Re-run `tools/db_health_check.py`. Confirm `total_ghost_rows==0` before claiming it on the page.
7. Exclude those cohorts from `strategy_perf_by_class` before PF/WR. Drop any displayed PF&gt;10 at n&gt;30 until recomputed (peer 06:23 examples: GainerPredictor1h PF 120, ADX Trend PF 60).
8. Emit `zero_pnl_breakdown` (FLAT / missing exit / resolver fallback) per class. Resolver already zeroes PnL on purpose (`universal_pick_resolver.py` fallback + TIME_EXIT/FLAT). Make that visible so PnL=0% stops looking like a silent win.

### P2 — prediction markets and WIRED_IN (plumbing only, stay shadow)

9. One write path for Kalshi/Polymarket JSON. Today producers and `dashboard_generator.py` / `universal_pick_resolver.py` disagree, and `kalshi_signals.json` is absent on both cited paths. Generate in CI or unregister.
10. PF renderer: 0 closed trades → `n/a`, not `∞`.
11. Add an explicit shadow pin so `prediction_market_consensus` cannot leave the kill list (`alpha_engine/config.py`) or receive size. Do not rescind `prediction_market_copy_trading_rejected` without a new evidence pack.
12. Badge childlike-airport as a static paper snapshot, or schedule a rescan. Do not treat 3 picks (XLV/LLY/SHY) as live.

### P3 — publish pipeline, not a workflow massacre

13. Keep `audit-dashboard.yml` cron-only. Investigate why 04:10 and 05:10 schedule runs did not appear while dispatches queued on `dashboard-publish`. Do not mass-disable from a sampled run list.
14. Leave GHA fixes to `GHACTIONS_2026-11-16/ACTION_PLAN.md`. Re-verify any "failing, no later success" row before touching it.

### P4 — do not size; forward-track only

15. Compound −94% vs Σ per-trade +311% is a portfolio-construction question, not a strategy win. Investigate after P0/P1, not before.
16. Forward-track only: COMMODITY `futures_momentum`, FOREX `forex_rsi2`, shadow `crypto_rsi5070_us`. No class-level size until n≥100 and policy-clean PF≥1.5.

---

## 4. Verification the finalizer can re-run

- `python3 -c` against `audit_dashboard/data/db_health.json`: `ghost_rows.data.total_ghost_rows`, `pnl_integrity.data.gt1pct_mismatch`, `pnl_integrity.data.naive_magnitude_mismatch`.
- `rg -n -F "Ghost rows: 0" audit_dashboard/template.html` must be gone after P0.1.
- `gh run list -w "Unified Audit Dashboard" -b main -L 15` — expect a schedule success newer than 03:21Z once the queue drains.
- `test -f audit_dashboard/data/strategy_ic_analysis.json` or the IC panel is removed.
- `test -f alpha_engine/data/kalshi_signals.json` or the resolver registration for that path is removed.

## 5. Out of scope

No real-money sizing. No re-enabling of the audit-dashboard `push:` trigger. No mass workflow deletion. No edits to `dbpasses.txt`.
