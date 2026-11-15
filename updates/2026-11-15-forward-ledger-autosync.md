# 2026-11-15 — forward-test ledger auto-sync (`forward_tracker.py sync`)

Requested: auto-append closed `vwap-reversion-scout` picks from the dashboard into the forward-test
ledger so the clock fills itself.

## The constraint that shaped the implementation

The ledger is a **pre-registered** forward test. The 29 closed `vwap-reversion-scout` picks in the
dashboard are the sample that *produced* the prior (+1.96pp, clustered t 1.99) — the exact rows that
`FORWARD_TEST.md` promises not to backfill. An auto-sync that appended "all closed picks" would have
silently converted a forward test into another retrospective read of the same data, which is the one
thing that would make the whole exercise worthless.

So the guard is **structural**: a pick is admitted only if it **closed on or after that strategy's
registered `start` date** (`2026-11-15`). The motivating sample is excluded by construction, not by a
flag someone has to remember. `--since` exists for testing, and it is documented as a dry-run tool.

## Changes

| File | Change |
|---|---|
| `tools/forward_tracker.py` | New `sync` subcommand: reads a dashboard payload, admits only registered strategies with `auto_sync`, dedupes by pick id plus a composite fallback, and writes ledger rows through the same `_append` path as manual logging. `log` now records `pick_id`/`source` too. |
| `state/forward_test/plan.json` | `"auto_sync": true` on `vwap-reversion-scout` (and matching `DEFAULT_PLAN` entry). |

Behaviour:

```bash
python3 tools/forward_tracker.py sync --dry-run     # preview, writes nothing
python3 tools/forward_tracker.py sync               # append newly-closed picks
python3 tools/forward_tracker.py sync --dashboard /path/to/fresh_payload.json
```

Idempotency is by `pick_id` when the payload has one, **plus** a `strategy|symbol|side|opened|closed`
composite, so a second run — or a run after a payload loses its id column — cannot double-count.

Ledger rows carry `source: "dashboard_sync"`, `pick_id`, `asset_class`, `notional_usd` and an explicit
`cost_model`.

## Verification (measured, not asserted)

| Run | Result |
|---|---|
| `sync --dry-run` | `vwap-reversion-scout: would append **0** \| closed before registration **29** \| duplicate 0 \| incomplete 0` |
| `sync --dry-run --since 2026-01-01` | `would append **29**` — the mechanism fires when the guard is lifted, so the 0 above is the guard working, not a broken query |
| `sync` (real) | `appended 0` |
| `sync` again | `appended 0` — idempotent |
| `ls state/forward_test/` | **no `ledger.jsonl`** — nothing was admitted, so no backfill occurred |
| `forward_tracker.py status` | all 3 strategies `CONTINUE`, 0 trades, 0 days |
| `forward_tracker.py selftest` | **8/8** |
| `py_compile` | clean |

Note the count is **29**, not the 28 the excess report scored: one of the 29 was excluded there as a
`pnl_mismatch` (price-derived return disagreed with `pnl_pct` by >0.5pp). The sync does not apply that
filter — it stores the dashboard's own numbers — so its count is one higher.

## Limits — stated because they matter for reading the eventual verdict

- **`pnl` is now NET of costs.** This was `fees: 0.0` / `cost_model: none` for a few hours on 2026-11-15,
  then superseded the same day by the fee model — see
  [`2026-11-15-forward-clock-fill.md`](2026-11-15-forward-clock-fill.md). Synced rows carry
  `pnl_gross`, `fees` and `fee_bps_per_side`, and the verdict rules read the net `pnl`.
- **PnL is dollarised at a fixed $10,000 notional** so synced rows share a unit with manual `log` rows
  (which take dollar `pnl`). PF is a ratio and unit-independent, but expectancy is not, so mixing
  percent-PnL and dollar-PnL rows would corrupt the average. One notional per strategy keeps it clean.
- **Nothing schedules this.** It is a command, not a cron. If nobody runs it, the clock does not fill —
  and `status` will keep saying `0 trades` rather than pretending otherwise.
- The default payload path is the **checked-in** `audit_dashboard/data/dashboard_data.json`, which is a
  snapshot (currently `generated_at 2026-10-19`). A production run should point `--dashboard` at a
  freshly fetched payload, otherwise newly-closed picks are invisible.
