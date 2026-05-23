# Automation / Cron / Monitoring Proposals — 2026-05-08

Author: investigation pass (read-only). Audited 319 workflows in `.github/workflows/`, dashboard data in `audit_dashboard/data/`, and `tools/`. Discord webhook channel = `DISCORD_WEBHOOK_PAPERTRADE` consumed by `coinglass_strategies/discord_notify.py` + `utils/discord_heartbeat.py`. PR-comment side channel = `tools/swarm/comment_poster.ps1` (NOT a Discord poster despite the prompt suggesting so — kept here for the record).

## Existing automation that already covers parts of the asked set

Before proposing, three of the user's ten candidates are already (partially) shipped:

| Asked candidate | Existing workflow | Verdict |
|---|---|---|
| #4 Workflow failure backstop | `.github/workflows/actions-failure-guardian.yml` (every 30 min, calls `scripts/actions_failure_guardian.py`) | Already auto-reruns. Gap = no "3+ consecutive" gate; reruns first failure. Worth a **tightening PR**, not a new workflow. |
| #6 STOCKSUNIFY daily pull | `.github/workflows/stocks-daily-stocksunify.yml` (40 21 * * 1-5) | Already pulls. Gap = no freshness/staleness alert if the workflow itself silently no-ops. Roll into proposal A2. |
| #7 Cross-PC heartbeat | None on GH (cross-PC gateway is local-host only) | Genuinely missing; a GH-side heartbeat would just check that the local agent posted to the bus — feasible but low value. **Drop**, ROI poor. |

The eight proposals below are NEW or genuine upgrades.

---

## A1 — WON-with-negative-PnL contradiction monitor

- **Schedule:** daily, 14:00 UTC (after audit-dashboard 13:00 UTC tick)
- **Source data:** `audit_dashboard/data/db_health.json::checks.won_pnl_contradiction`. Confirmed shape today: `contradiction_detected: true`, `negative_pnl_count: 3064` per status. Field already populated.
- **Logic:** read JSON, alert if `contradiction_detected == true` AND total `negative_pnl_count` across statuses ≥ 100 (small drift = noise; mass mislabel = bug like the 2026-04-27 `_daily_loss` regression).
- **Alert channel:** Discord via `DISCORD_WEBHOOK_PAPERTRADE`, plus opens a GH issue tagged `data-quality` if the same alert fires 3 days running.
- **LoC estimate:** ~80 (workflow YAML 30 + python check 50)
- **Why needed:** the canonical "WON pick with negative PnL" bug class has caused at least two production incidents (`feedback_phantom_halt_alert_bug.md`, `feedback_noncrypto_resolver_live_close_bug.md`). 3064 negative-PnL WON rows live in prod RIGHT NOW per today's snapshot — and no one is paged.
- **Avoided-outage value:** HIGH. Catches mislabel storms before they propagate into live HALT decisions / kill claims.

## A2 — Stale data-file watchdog (multi-source)

- **Schedule:** every 6h
- **Source data:** `os.stat()` mtime on every `*.json` in `audit_dashboard/data/` (84 files today) + `STOCKSUNIFY/data/daily-stocks.json`.
- **Logic:** group by **source workflow** (mapped via a small static manifest file). For each, expected refresh cadence is hourly/daily/weekly. Emit a Discord alert listing files where `now - mtime > 2 × expected_cadence`.
- **Alert channel:** Discord — single rolled-up message ("17 files stale, top offenders: …"). Avoid 84-line spam.
- **LoC estimate:** ~150 (manifest 60 + check 60 + workflow 30)
- **Why needed:** subsumes user's #3 AND fixes the silent-no-op gap on #6 STOCKSUNIFY. Today's recurring failure mode (`hyro-bridge-regen` 3+ days red, `penny-skyrocket` 5+ days red) is invisible from the audit dashboard because the JSON files just stop refreshing — no error tile.
- **Avoided-outage value:** HIGH. One job replaces three half-built ones.

## A3 — Phantom-EXPIRED weekly chart

- **Schedule:** weekly, Sunday 02:00 UTC
- **Source data:** universal pick ledger / `dashboard_data.json::by_asset_class.{class}.statuses.EXPIRED` divided by total picks per class.
- **Logic:** compute phantom% = `EXPIRED / total` for each asset class. Append a row to `reports/phantom_expired_history.csv`. Render a 30-day sparkline into `audit_dashboard/data/phantom_trend.json` for the dashboard.
- **Alert channel:** Discord on phantom% > 25% week-over-week jump per class. CSV is the persistent record.
- **LoC estimate:** ~120
- **Why needed:** matches user candidate #2. Phantom EXPIRED is the canary for resolver bugs (live-close at yfinance spot, ghost rows like `feedback_quan_engine_matic_positive_artifact`). Weekly trend > daily snapshot for catching slow drift.
- **Avoided-outage value:** MEDIUM-HIGH. Slow-drift resolver bugs took 4–12 weeks to detect last time. This compresses MTTD to ≤7 days.

## A4 — Concept-family coverage daily report

- **Schedule:** daily, 23:00 UTC
- **Source data:** `dashboard_data.json::picks.active` aggregated by `concept_family`.
- **Logic:** count picks per concept_family. Alert on (a) any family with 0 picks for 3 days running, (b) any family whose share dropped >50% week-over-week. Output CSV + Discord summary.
- **Alert channel:** Discord
- **LoC estimate:** ~90
- **Why needed:** matches user candidate #5. Diversification is part of charter ("phenomenal across ALL asset classes"). When a strategy silently dies (e.g. `futures_kill_without_replacement` per memory), concept_family count zeros days before WR/PF metrics would catch it.
- **Avoided-outage value:** MEDIUM-HIGH. Catches silent kills. Cheap.

## A5 — Hyro backtest scheduled runner

- **Schedule:** weekly, Saturday 18:00 UTC
- **Source data:** runs `tools/hyro_backtest.py`, `tools/hyro_backtest_extended.py`, `tools/hyro_backtest_new_strategies.py` — currently MANUAL only.
- **Logic:** run all three, commit `hyro_backtest_*.json` outputs in `audit_dashboard/data/`, diff vs prior week's results, alert on PF/WR drift > 0.3 / 5pp.
- **Alert channel:** Discord + commit log
- **LoC estimate:** ~70
- **Why needed:** matches user candidate from "scheduling manual things." Three hyro_backtest result files exist, but they're stale because nothing reruns them. Without a baseline, hyro strategy drift is invisible.
- **Avoided-outage value:** MEDIUM. Direct CRON-cost is moderate (3 backtests = ~30 min/run). Justified if hyro is on the live path (it is — see `tools/hyro_quan_bridge.py`).

## A6 — OOS Sharpe overfit canary

- **Schedule:** daily, 04:00 UTC
- **Source data:** any backtest output writing `oos_sharpe` OR `walk_forward_sharpe` (regex sweep of `audit_dashboard/data/*.json` + `backtests/`).
- **Logic:** alert if any class/strategy reports OOS Sharpe > 5 OR `total_pnl_pct_compounded_ew` > 10000% OR Sortino > 10. These are math-implausible; almost always a unit-mismatch (fractional vs %) or compounding bug. Direct nod to `feedback_cycle10_unit_mismatch_bug`.
- **Alert channel:** Discord + auto-open GH issue
- **LoC estimate:** ~110
- **Why needed:** combines user candidates #9 and #10. Already burned by exactly this class of bug (Cycle10). Cheap insurance.
- **Avoided-outage value:** HIGH. One catch = saved kill claim against an innocent strategy.

## A7 — Resolver-vs-ledger daily reconciliation

- **Schedule:** daily, 03:00 UTC (after end-of-day resolver runs)
- **Source data:** `outcome_resolver.py` outputs vs `forward_validator.py` outputs vs `dashboard_data.json::picks.active`.
- **Logic:** for each closed pick today, verify (a) status enum is one of {WIN, LOSS, BREAKEVEN, EXPIRED, STOPPED}, (b) sign(pnl_pct) matches status (per `PNL_WIN_THRESHOLD_BY_CLASS`), (c) symbol/direction unchanged from open. Output count of mismatches by source_system.
- **Alert channel:** Discord on >5 mismatches; CSV log always.
- **LoC estimate:** ~180
- **Why needed:** the resolver-v2 bug bundle (CRYPTO 0.1bp, others 5bp from `outcome_resolver.py:115-126`) shipped 2026-05-02. Today A1's `won_pnl_contradiction` flag is RED with 3064 rows — meaning v2 didn't fully clean the backlog. We need ongoing reconciliation, not a one-shot cleanup.
- **Avoided-outage value:** HIGH. Direct hedge against the entire `feedback_noncrypto_resolver_live_close_bug` class.

## A8 — Active-gate execution-time audit

- **Schedule:** every 4h
- **Source data:** sample of paper-trade exec logs from TV accounts (HIGHFWWRABV55_SCOREABOVE50_V4, BANNED_TIER_*, etc.) cross-referenced with the active-gate filter currently configured for that account.
- **Logic:** for the last 50 fills per account, verify that each pick passed the account's stated gate AT THE TIME OF FILL — not just at generation. Flag any fill that should have been blocked (per `feedback_gate_at_execution_not_generation.md`).
- **Alert channel:** Discord on any flagged fill. Hard block: the workflow can write a `tools/exec_blocklist.json` consumed by the next exec cycle.
- **LoC estimate:** ~200
- **Why needed:** the gate-bypass bug pattern is a recurring memory-tracked finding (memory file: `feedback_gate_at_execution_not_generation.md`). The recent BANNED-tier "verified clean" finding (`project_banned_tier_gate_bypass_2026_04_28.md`) shows we need ongoing verification, not just one investigation.
- **Avoided-outage value:** VERY HIGH for live money — directly protects capital allocation rules. CRON cost moderate (4h is the right cadence; hourly = noisy).

---

## Top-5 ranking by (avoided_outage_value / cron_cost)

| Rank | ID | Title | Outage value | CRON cost | Ratio | Why |
|------|----|-------|--------------|-----------|-------|-----|
| 1 | **A2** | Stale data-file watchdog | HIGH | LOW (6h, ~5s/run) | best | One job covers 3 user candidates; catches silent-no-op deaths that audit dashboard misses. |
| 2 | **A1** | WON/PnL contradiction monitor | HIGH | TINY (daily, 1s) | excellent | Field already populated and currently RED with 3064 rows; trivial to ship; high direct outage hedge. |
| 3 | **A6** | OOS Sharpe / compound-PnL overfit canary | HIGH | TINY (daily, regex sweep) | excellent | Already burned by Cycle10 unit-mismatch; this is the regression test in production. |
| 4 | **A8** | Active-gate execution-time audit | VERY HIGH | MEDIUM (4h, ~30s) | great | Directly protects live capital. The single proposal where one catch pays back years of cron cost. |
| 5 | **A7** | Resolver-vs-ledger daily reconciliation | HIGH | MEDIUM (daily, ~60s) | good | A1 catches the symptom; A7 catches the cause. Together they bracket the resolver class of bugs. |

A3, A4, A5 are still worth shipping but are second-wave: they are slow-drift detectors, not P0 outage hedges.

## Implementation order suggested

1. **A1 + A6 first** — both are <2h to ship and use already-populated fields. Immediate green-tier coverage.
2. **A2** — replaces 3 half-baked file-watchdog proposals.
3. **A8** — touches live-money path; deserves its own PR with a rollout plan.
4. **A7** — extends A1 from symptom to cause.
5. **A3 + A4 + A5** — ship as a batch in week 2 once the P0 trio above is steady.

## Notes

- All proposals reuse `DISCORD_WEBHOOK_PAPERTRADE` and the `utils/discord_heartbeat.py` helper. No new webhook secrets needed.
- All proposals are read-only against prod data files; only writes are alert posts and `reports/*.csv` history files.
- None require WSL or Windows paths; pure Linux runners.
- The `actions-failure-guardian.yml` improvement (3+ consecutive gate) is a one-line PR and not listed here as a separate proposal — file as a follow-up issue against that workflow.
