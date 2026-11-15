# 2026-11-15 — making the forward clock fill itself: costs, daily sync, second candidate

Three changes that all attack the same problem: a pre-registered forward test is worthless if the clock
never fills. vwap-reversion-scout fires ~48×/yr and its promotion sample is ~155 trades — roughly three
years of waiting, with no cost model and no automation.

## 1. Fee model — verdicts now read net PnL

`tools/forward_tracker.py sync` previously stored `fees: 0.0` with `cost_model: none`, because the
dashboard payload has no fee field. A forward PF measured gross is a weaker claim than a backtest that
included costs, and the gap would have been invisible in the verdict.

Now the registered cost assumption is applied explicitly: **6 bps per side, on both legs** (12 bps of
notional round-trip), resolved from `plan.json → cost_model.fee_bps_per_side` with per-strategy override
and a `--fee-bps-per-side` run override.

| Field | Meaning |
|---|---|
| `pnl_gross` | raw price move × qty |
| `fees` | `notional × bps/10000 × 2` |
| `pnl` | **net** — this is what the verdict rules consume |
| `fee_bps_per_side` | the basis that was actually applied to that row |

Measured: at the default $10,000 notional, fees are exactly **$12.00** per round trip, and every
guard-lifted preview row satisfies `net = gross − 12.00` (checked programmatically, all rows, zero
mismatches).

## 2. Daily workflow — `.github/workflows/forward-ledger-sync.yml`

Runs 05:37 UTC (after the hourly audit build refreshes the live payload) plus `workflow_dispatch`.

| Step | What it does |
|---|---|
| Fetch payload | `curl` the live `dashboard_data.json` to **`/tmp`**, refusing a payload with 0 closed rows; warns if `generated_at` is >48h old |
| Sync | `forward_tracker.py sync --fee-bps-per-side 6` |
| Status | prints the per-strategy verdict to the run log |
| Commit | adds **only** `state/forward_test/ledger.jsonl`, runs the conflict-marker guard, asserts exactly one staged path and that it *is* the ledger, commits with `[skip ci]`, pushes via `safe_push.sh` |

Deliberate choices:

- **Separate workflow, not a step in audit-dashboard.** That job runs hourly and has a documented
  cancel-cascade history; committing there would mean ~24 ledger commits/day and would couple an
  append-only data file to a 35-minute job.
- **Fetched to `/tmp`, never over the tracked payload.** Overwriting `audit_dashboard/data/dashboard_data.json`
  would put a 25MB file in the commit and fight audit-dashboard for the same path.
- **The guard is not in the workflow.** The pre-registration date check lives in the tool, so a workflow
  edit cannot lift it.
- **Fails loudly** on a broken payload or an unexpected staged path instead of committing nothing quietly.

## 3. Second candidate — `rs-breakout-scout` (EQUITY), with a measurement design

Screened 127 strategy/class pairs on `reports/pick_excess_returns.json`; took the best remaining
clustered t after excluding the already-registered strategies.

| | Value |
|---|---:|
| Windows / picks | 44 / 45 |
| Mean excess vs SPY | +1.08pp (window-mean) |
| Window sd | 4.12pp |
| Clustered t | **+1.74** |
| Excess win rate | 53.3% |
| Observed rate | 74/yr over 216d |

**It fails multiplicity and the registration says so.** With 127 pairs screened, the Bonferroni bar is
|t| ≥ 3.54. +1.74 is far below it. Registering it is not a claim that it works — it is a claim that a
forward clock is the only instrument that can settle it.

Measurement design (in `plan.json`, so the rules precede the data):

- **Primary:** one-sided mean `excess_pp` per `(entry_day, exit_day)` window, clustered so batch closes
  count once.
- **Power:** `n = ((1.96 + 0.84)·4.12/1.08)² = 152` windows at 80% power, α 0.05 — ~2.0 years at the
  observed rate. The number is derived, not asserted.
- **Interim looks at 25/50/100/152** with O'Brien-Fleming alpha spending: an early large effect can
  promote, but no promotion is allowed off an interim look, and no KILL before n ≥ 20 windows.
- **KILL:** n ≥ 20 and mean excess < 0 with boot5(PF) < 1.00; or n ≥ 50 and mean excess < +0.25pp.

`strict_class: true` on this entry (its prior is EQUITY-only), while vwap-reversion-scout keeps both
classes because its prior was measured across EQUITY+ETF. Class-skipped rows are counted in the output.

### The uncomfortable finding

The clock-fill problem **cannot be solved by picking a busier strategy**. The highest-frequency strategy
in the book is `luxalgo_confluence` (1,173 picks) at −0.03pp, t −1.89 — a cost sink. Frequency and edge
are anti-correlated here. So the honest answer is more weak candidates plus sequential monitoring, which
is what this commit does, not a fast clock.

## Verification

| Check | Result |
|---|---|
| `py_compile` | clean |
| Fee arithmetic, all preview rows | fees = $12.00, `net = gross − 12.00`, 0 mismatches |
| `sync --dry-run` | still `would append 0`, 29 closed before registration — the guard survived the refactor |
| Workflow YAML | parses; cron/permissions/concurrency verified; all required guards present in the parsed tree |
| `plan.json` | parses; 4 strategies; `cost_model` + per-strategy `fee_bps_per_side` present |
| `selftest` | 8/8 |

## Limits

- **Nothing has been admitted yet.** The ledger is still empty and the guard reports 29 pre-registration
  picks excluded. Until real picks close after 2026-11-15, every verdict is `CONTINUE`, 0 trades.
- **Fees are a flat assumption**, not measured slippage. 6 bps/side is the backtest's assumption, so
  forward and prior share a cost basis — but a strategy trading illiquid names will do worse than 6 bps.
- **The interim looks are a design, not yet a functioning sequential test** — the alpha-spending
  boundaries are recorded in the plan, and implementing them is a follow-up.
- `rs-breakout-scout`'s median hold is **not measured** in this change; `FORWARD_TEST.md` says so rather
  than guessing.
