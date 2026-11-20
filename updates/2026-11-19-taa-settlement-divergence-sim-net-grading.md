# 2026-11-19 — TAA settled, class divergence traced, crypto sim graded net of cost

Four changes landed together. Each is listed with what was wrong, what changed, and how it was
verified.

## 1. TAA claim settled: NOT REPRODUCED

**What was broken (as a claim):** copilot's money-maker plan asserts "top5-6m rotation 2007-2026
Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs −51%" and calls ETF tactical allocation "the ONE thing we've
proven", making it the basis of the $2k recommendation.

**What changed:** added `tools/taa_settle_sweep.py`, a pre-registered 576-cell grid (top-N ×
lookback × absolute-momentum × lag × cost, two universes, two windows) with the success criterion
fixed in source before the run. Wrote `reports/TAA_SETTLE_2026-11-19.md`.

**Result:** 0/576 cells met the bar. Best lagged cell over 2007-2026 is Sharpe **0.795** vs SPY
**0.735**, MaxDD **−41.7%** (or −23.8% on the broad universe) — the claimed 0.88/−19% lies outside
the entire grid. The claim does hold in 2018-2026 (1.045 vs 0.872), so the number is a window
artefact rather than a fabrication.

**Verified:** `python3 tools/taa_settle_sweep.py` exits 0, writes 576 rows to
`reports/taa_settle_2026-11-19.csv`; the sweep prints `verdict=NOT_REPRODUCED winners=0`. Price
cache committed alongside so the result is re-checkable offline.

## 2. Class divergence (up to 3.2x) traced to four causes; my own 3.2x withdrawn

**What was broken:** /audit's `money_ready_verdict.json` and /audit3's `audit3_ledger.json` disagree
by up to 3.2x on the same classes.

**What changed:** wrote `reports/CLASS_DIVERGENCE_2026-11-19.md` with a per-class cause table.
Four causes, only one a defect: (1) different resolved-row populations (CRYPTO 3,726 vs 6,675;
FOREX 628 vs 256 — not a subset either way); (2) `pf` is gross while `expectancy` is post-cost in
the same record, which flips the sign for EQUITY (+0.0075 with PF 0.64) and **ETF (PF 1.82 with net
expectancy −2.26%)** — the number the plan cites as ETF's strength is the gross one; (3) real bug:
`policy_clean_pf` is bit-identical to `pf` in all 11 classes while `policy_clean_n` differs, and for
CRYPTO a "clean subset" of 22,081 exceeds its 3,726-row parent; (4) `scored_share_of_valid_pct =
105.04` coverage arithmetic.

My earlier "3.2x" framing used a mean of per-cell profit factors, which is not a valid aggregate —
withdrawn and replaced with the row-weighted comparison.

**Verified:** every figure recomputed from the two committed JSON artifacts by the reproducer
embedded in the report; the 10-minute progress loop re-derives the ratio table each tick.

## 3. Crypto intraday sim: CLOSE rows graded gross, now graded net

**What was broken:** `verified_strategies/paper_pilot/crypto_intraday_sim.py` writes
`pnl_pct = (exit/entry − 1) × 100` (gross) and `outcome = WIN if pnl_pct > 0`, so at the runner's own
16 bps round-trip cost every trade finishing inside ±0.16% is graded with the wrong sign, and the
slot guardrails (trailing DD, daily pause, consistency) accumulate gross P&L. My earlier review
claim that the runner had **no** cost model was itself wrong — `ROUND_TRIP_COST_PCT = 0.16` with a
4× entry floor was already there; I mis-grepped case-sensitively. That correction is recorded in
`reports/PEER_REVIEW_copilot_money_maker_plan_2026-11-19.md`.

**What changed:** branch `fix/crypto-sim-net-grading-2026-11-19` off their branch adds
`gross_pct` / `net_pct` / `cost_pct` (with `pnl_pct` now net, so guardrails see net), grades
`outcome` on net, records `expected_move_pct` / `cost_floor_pct` / `assumed_round_trip_pct` on every
OPEN row so refusals are auditable, and stamps `intrabar_first_touch` on CLOSE rows so the two
close-only pods cannot be mistaken for intrabar-resolved ones.

**Verified:** `py_compile` clean; their own suite `pytest tests/test_crypto_intraday_sim.py` →
**17 passed**.

## 4. Peer review corrected on the record

Retracted addendum item A3 (runner has no cost model) entirely, downgraded A1 (null TP/SL) from
BLOCKER to a documented design consequence — `stop_pct: None` with `close_stop_pct: -4.0` is a
registered close-only expression. Push `01cee645bdd` on `review/buffy-money-maker-plan-2026-11-19`.

## Automation

`tools/buffy_progress_loop.py`, armed at `*/10` with `flock -n /tmp/buffy_progress.lock`, re-runs
the cheap idempotent checkpoints (TAA result present, divergence ratios, sim tests, ledger depth),
appends one JSON line per tick to `reports/progress_loop/<date>.jsonl`, never edits tracked source,
self-disables at 400 runs.
