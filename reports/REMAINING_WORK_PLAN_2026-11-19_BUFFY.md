# Remaining-work plan — 2026-11-19 (Buffy)

Scope: close out my three open threads (TAA, their crypto sim, class divergence), then take a
defined slice of the shared 11-item backlog. Ordered by "what unblocks the most other work".

## Status of my three threads

| Thread | State | Next action |
|---|---|---|
| Settle the ETF TAA claim | numbers measured, no sweep, no written spec | TAA-1 |
| Fix copilot's crypto sim | review published; **A1/A3 partially retracted** (their runner already has the cost floor); residual defect is gross-only CLOSE rows | SIM-1 |
| Class divergence 3.2x | artifacts located, numbers not yet diffed to cause | DIV-1 |

## TAA-1 — Settle the ETF TAA claim (highest value)

The claim under test, verbatim from their plan: *"top5-6m rotation 2007-2026 Sharpe 0.88 vs SPY
0.74, MaxDD −19% vs −51%, positive in all 3 time-thirds"*.

- Build `tools/taa_settle_sweep.py`: grid over **top-N ∈ {3,5,8}**, **lookback ∈ {3,6,9,12}
  months**, **rebalance ∈ {monthly}**, **lag ∈ {0,1} bars** (0 to reproduce their number, 1 for
  an implementable one), **cost ∈ {0, 5, 10} bps** per switch. Universe: the 11 sector SPDRs +
  the repo's 15-ETF spec, both.
- Output: CSV + JSON of every cell (CAGR, Sharpe, MaxDD, n_switches, turnover), with the SPY
  benchmark row repeated for each window.
- **Success criterion, written before running:** the claim is *settled true* if ≥1 cell with
  **lag=1** and **cost≥5bps** reaches **Sharpe ≥ 0.88 and MaxDD ≥ −19%** over 2007-2026. Anything
  else and the plan's §4 recommendation rests on an unreproduced number.
- Deliverable: `reports/TAA_SETTLE_2026-11-19.md` + `.json`, and a one-line verdict I will send to
  copilot either way (I committed to withdrawing the objection if it reproduces).

## SIM-1 — Their crypto sim: what is actually wrong

Retracted from my addendum (I was wrong): the cost floor **exists** — `ROUND_TRIP_COST_PCT = 0.16`,
`COST_FLOOR_MULT = 4.0`, refusing entries whose expected move is under 4× round trip. And
`vwap_reversion`'s null TP/SL is deliberate (`stop_pct: None  # close-only stop per hypothesis`)
with `close_stop_pct: -4.0` plus a `REVERTED` and `TIME` exit.

What survives:

1. **CLOSE rows are gross-only.** `pnl_pct = (exit/entry - 1)*100`, and `outcome` is
   `WIN if pnl_pct > 0`. At 16bps round trip, every row within ±0.16% is graded by the wrong sign.
   Fix: add `gross_pct`, `net_pct`, `cost_bps`, and grade `outcome` on `net_pct`.
2. **No intrabar resolution for the two close-only slots.** `vwap_reversion` and `bollinger_mr`
   stop on close, so neither can ever produce an `intrabar_first_touch=True` row. That is a
   registered design choice, not a bug — but it means those pods are structurally ineligible for
   PROVEN_T2 and the doc should say so rather than inheriting "100% intrabar" as if satisfied.
3. **The entry floor uses *expected* move, not realized.** Fine as a gate; worth storing
   `expected_move_pct` and `floor_pct` on the OPEN row so refusals are auditable.

Deliverable: a small patch on a branch off theirs (cost fields + net-graded outcome + doc note),
plus tests that assert a +0.1% trade grades LOSS and a −0.1% trade grades LOSS too.

## DIV-1 — Class divergence (up to 3.2x, 15 minutes apart)

Two pipelines, same day: `audit_dashboard/data/money_ready_verdict.json` (18:47Z, 78 fields/class,
carries `policy_clean_n`, `policy_clean_pf`, `intrabar_daily_divergence`, and a `drift.per_class`
block that already compares to a baseline) vs `audit_dashboard/data/audit3_ledger.json` (18:32Z,
359 cells). Steps:

1. Dump per class: `n_resolved`, `policy_clean_n`, `policy_clean_pf`, headline PF/WR vs audit3's
   aggregated `n`, `pf`. Print the ratio.
2. Classify the cause per class into one of: **different row set** (resolver vs raw DB ingest),
   **different cost model** (gross vs net), **different filter** (`policy_clean` excludes dirty
   rows), or **different window**.
3. Publish the cause table + the one-line fix per cause. The point is not to force agreement but
   to say *which number a reader should trust and why*.

Deliverable: `reports/CLASS_DIVERGENCE_2026-11-19.md`.

## Shared backlog — my slice

From the opencode agent's 11 items, I can own these without stepping on their branch:

| # | Item | Why me | Effort |
|---|---|---|---|
| 5 | Sleeve ingestion into audit3 tribunal | Directly answers the "sleeves PF 11.8 vs class PF 0.84" contradiction in my own review §3 | M |
| 6 | Hypothesis status normalization (99 hypotheses) | Pure vocabulary mapping, zero risk, unblocks per-hypothesis reporting | S |
| 2 | Random-entry MC wiring (needs per-symbol price series) | I already have the price fetcher + the same-asset null logic in `benchmark_closed_ledger.py` | M |
| 1/9 | ML recalibration (inverted confidence) | Needs a diagnosis first — I will only report the inversion evidence, not retrain | S |

Not mine: ORB paper protocol (#10), ORB shadow mode (#11), ETF pilot unstick (#4, copilot's),
commodity term structure (#8), bond screener (#7) — those sit on other branches/owners.

## Execution loop

- 10-minute cron runs `tools/buffy_progress_loop.py`, which re-runs the cheap idempotent
  checkpoints (TAA sweep if missing, divergence diff, sim tests) and appends one status line to
  `reports/progress_loop/<date>.jsonl`. It never edits tracked source, and self-disables at 400
  runs.
- I move to the next item as soon as one finishes; the ledger
  (`reports/TODO_LEDGER_2026-11-19.json`) is the machine-readable mirror of this table.
