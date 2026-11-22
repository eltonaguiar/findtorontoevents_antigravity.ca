# Block 7 — GHA Monitoring Audit (2026-11-22)

**Question asked:** does scheduled CI already monitor picks so we can see when TP/SL
are met, and does it maintain paper-trading portfolios? The goal is to avoid adding an
eleventh overlapping workflow.

**Method:** read each workflow's `on:` block and every `run:` step, then follow the
invoked script. Paths are relative to the repo root; crons are copied verbatim from the
YAML (none are paraphrased).

## Capability key

- **(a) resolves picks against live prices** — an open pick is marked against a market price.
- **(b) checks TP/SL specifically** — take-profit / stop-loss is compared to price to close a pick.
- **(c) maintains a paper-trading portfolio with a committed ledger** — positions accumulate in a repo-tracked ledger file.

## The ten workflows

| Workflow | File | Cron (verbatim) | What it actually does | (a) | (b) | (c) |
|---|---|---|---|---|---|---|
| outcome-resolver | `.github/workflows/outcome-resolver.yml` | `47 */1 * * *` | `alpha_engine/active_picks_sync.py` per asset class against MySQL + live prices, writes `status/exit_price/exit_reason/pnl_pct` to `at_raw_picks` (code compares `tp`/`sl` to `live_price`, `active_picks_sync.py:158-167`); then `outcome_resolver.py --mysql`, mirror to `at_signal_outcomes`, commits `outcome_resolver_log.json` + `closed_picks.json` | **yes** | **yes** | partial — a real + paper books exist in MySQL, and closed picks are committed, but it is not a synthetic-portfolio equity curve |
| live_tracker | `.github/workflows/live_tracker.yml` | `24 * * * *` | `live_picks_tracker.py` (has `close_pick(...)`, `:154`), regenerates `dashboard/` and deploys Pages; `data/live_picks.db` is deliberately **not** tracked | yes | adjacent (closes picks; see note) | no committed ledger — the DB is untracked, only the HTML dashboard is committed |
| live-monitor-refresh | `.github/workflows/live-monitor-refresh.yml` | `42 * * * *`, `0 2 * * 0` | calls the **production PHP API** on findtorontoevents.ca: fetch prices, `live_trade.php?action=track` ("check SL/TP/max-hold auto-close", `:46-62`), scan signals, auto-execute strength ≥ 70, Kelly recalc, breakers; weekly hour-learning of best TP/SL/hold | yes | **yes** | yes in effect, but the ledger lives **server-side (MySQL), not in the repo** |
| portfolio-trackers | `.github/workflows/portfolio-trackers.yml` | `48 * * * *` | `alpha_engine.real_money_tracker`, `alpha_engine.portfolio_theories`, `tools/build_theory_tracker_sidecar.py`, then `safe_commit_push.sh` of `real_money_portfolio.json`, `real_money_history.json`, `theory_portfolios.json`, `theory_portfolios_history.json` | yes (marks books) | no — it marks/allocates, it does not close on TP/SL touch | **yes** — the cleanest (c) in the repo |
| forward-tracking-v2 | `.github/workflows/forward-tracking-v2.yml` | `28 * * * *` | imports picks into `forward_tracking.db`, `forward_trade_executor_v2.py --run-once` sets `status` to `tp_hit`/`sl_hit`/`expired` (`:96-103`), commits only `forward_stats.json` | yes | **yes** (tp_hit/sl_hit statuses) | partial — `forward_tracking.db` is uploaded as a 30-day artifact, **not** committed |
| ghcopilot-paper-monitor | `.github/workflows/ghcopilot-paper-monitor.yml` | `20 * * * *` | runs tests, `tools/ghcopilot_paper_monitor.py` (`resolve_leg`, `:236`) against `bars`, commits `audit_dashboard/data/ghcopilot_paper.json` (tracked), deploys via FTP | yes | yes (legs resolved with TP/SL, 16 TP/SL refs) | **yes** |
| dashboard-pick-trader | `.github/workflows/dashboard-pick-trader.yml` | `38 * * * *` | `alpha_engine/dashboard_pick_trader.py` (25 TP/SL refs), commits `portfolio_1x.json`, `portfolio_20x.json`, `dashboard_trader_log.json` when changed | yes | yes | **yes** (1x and 20x paper books, tracked) |
| crypto-intraday-sim | `.github/workflows/crypto-intraday-sim.yml` | `7,37 * * * *` | `verified_strategies/paper_pilot/crypto_intraday_sim.py --one-shot` on real 4h bars for 3 pre-registered slots, `tools/pilot_forward_bridge.py --apply` into `reports/forward_observations.jsonl`, commits sim state + log | yes | yes (guardrails, SL/TP exits) | **yes** |
| verified-pilot-daily | `.github/workflows/verified-pilot-daily.yml` | `53 6 * * *` | `tools/run_verified_pilots_daily.py` (ETF dual momentum, Faber TAA, crypto WF Hyro, forex carry G10), commits the small proof files (`faber_taa_paper_log.jsonl`, `etf_dual_momentum_state.json`, `forex_carry_g10_paper_log.jsonl`, stats JSONs) | yes | yes (pilot exit rules) | **yes** |
| tv-paper-tpsl-watchdog | `.github/workflows/tv-paper-tpsl-watchdog.yml` | `26,41,56,11 * * * *` (every 15 min) | `tools/tv_paper_tpsl_audit.py`, which reads `alpha_engine/data/tv_paper_positions_snapshot.json` and flags positions with **missing TP, missing SL, or TP/SL on the wrong side of entry** (`tools/tv_paper_tpsl_audit.py:86-115`), logging violators to `tv_paper_tpsl_violators.jsonl`; the workflow is `contents: read` and exits 0 if the snapshot is absent | **no** | **no** | **no** |

### `tv-paper-tpsl-watchdog` — precise verdict

Despite the name and the 15-minute cadence, it does **not** resolve TP/SL against
prices. It audits **TP/SL placement integrity**: are TP and SL present, numeric, and
on the correct side of entry for the position side. It never fetches a price, never
compares a price to TP/SL, and never closes a position. It is also **in standby
today**: `alpha_engine/data/tv_paper_positions_snapshot.json` does not exist on disk,
so the workflow hits its early `exit 0` ("watchdog in standby mode"). The closest
match to the user's TP/SL requirement by *name* is the weakest match by *function*.

## Conclusion: the GHA requirement is already SATISFIED

The user's stated requirement ("GHA monitoring to see if TP/SL are met" and "paper
trading portfolios") is covered by workflows that already exist. No eleventh workflow
is needed.

- **(a) resolves picks against live prices** — satisfied by `.github/workflows/outcome-resolver.yml` (via `alpha_engine/active_picks_sync.py`), with `live-monitor-refresh`, `forward-tracking-v2` and `crypto-intraday-sim` as additional resolvers.
- **(b) checks TP/SL specifically** — satisfied by `.github/workflows/outcome-resolver.yml` (`active_picks_sync.py:158-167`) and `.github/workflows/forward-tracking-v2.yml` (`tp_hit`/`sl_hit`), plus `live-monitor-refresh` (server-side PHP).
- **(c) paper-trading portfolio with a committed ledger** — satisfied by `.github/workflows/portfolio-trackers.yml` (real money + theory books committed), `ghcopilot-paper-monitor`, `dashboard-pick-trader`, `crypto-intraday-sim` and `verified-pilot-daily`.

Nothing is missing at the capability level. What is missing is **consolidation**: five
workflows each keep their own ledger format, and `forward-tracking-v2`'s ledger is an
artifact rather than a committed file. That is a tidy-up, not a gap worth a new
workflow.

## Minimum workflow that would add anything (description only, not created)

A new workflow would only add value if it unified reporting:

1. Read the already-committed ledgers (`theory_portfolios.json`, `portfolio_1x.json`, `ghcopilot_paper.json`, `crypto_intraday_sim_paper_log.jsonl`, pilot logs).
2. Normalise them to one schema (open/closed, TP/SL hit, net bp).
3. Emit one summary table for the audit dashboard.
4. Do not re-resolve prices (outcome-resolver already does that).
5. Do not commit new ledgers (the producers already do).

That is a reporting job, not a monitoring job, and it is not required by the stated
goal.
