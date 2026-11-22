# Plan — take H-150 from validated signal to a forward-tested, promotable strategy

**Date:** 2026-11-22 · worktree `/tmp/w45` @ `fix/dsr-baselines-h146-key-scrub-2026-11-21`
**Decision this plan implements:** `/audit3` is the proof surface (see
`reports/2026-11-22-audit2-vs-audit3-forward-test-decision.md`).

## Where we are

| Item | State |
|---|---|
| H-149 annual GP/A, 711 names | **REJECTED** (4 strong + / 11 strong −), factor alpha t=0.04, 0 of 10,230 records delisted mid-window |
| H-149 bottom-left tail | entry-truncated: 759 names with facts → 711 with prices → **48 never priceable** (warrants/units/delisted) |
| H-150 signal (quarterly TTM GP/A) | validated **91.11%** within 1% of audited 10-K on 225 pairs / 30 companies |
| H-150 backtest | tool written (`tools/h150_gpa_backtest.py`), run launched 2026-11-22 |
| FMP delisted-ticker route | **dead credential** (401 on `stable/`, 403 on `v3/`); Finnhub free has no delisted history |

## Workstream A — full-sample TTM validation (running)

`python3 tools/h150_ttm_gpa.py --sample-n 2600 --out reports/h150_ttm_validation_full.json`

Accept: `pct_within_1pct >= 90`, `comparable_pairs >= 500`, `companies_with_ttm >= 100`.
If it fails, the TTM signal is not trustworthy at scale and Workstream B's result is void —
say so rather than reporting the backtest alone.

## Workstream B — H-150 backtest (running)

`python3 tools/h150_gpa_backtest.py --sample-n 2600`

Frozen spec (do not touch after the first run): SEC filers seed 149, cap $2B–$10B, top quintile
z ≥ 0.8416, next-session-open entry, first month-end ≥ 20 and ≤ 60 calendar days, 20 bp
round-trip, 2× stress, unmodified `edge_stability_harness`, FF4 alpha t ≥ 2.0.

Outputs: `harness` verdict (whole in-band cross-section), `book` (the held portfolio, net mean,
WR, per-formation series), `factor_regression` (overlapping + every-2nd, IR on FF4 residuals),
`cost_stress_2x`, and a single `verdict` with five explicit gates.
Accept: all five gates → `PROVEN_CANDIDATE`; anything less → `NOT_PROVEN`, written to the
registry as such with the failing gate named.

## Workstream C — delisted-ticker prices (blocked on a working vendor key)

The 48 never-priceable names and the (currently empty) delisting tail need historical bars for
delisted tickers. `FMP_API_KEY` in `~/dbpasses.txt` is invalid. Viable routes, in order:
1. **Polygon.io** — reference endpoint returns `active=false` tickers *and* aggregates, which is
   the whole requirement in one API. Needs a key.
2. **Tiingo** — daily EOD incl. delisted symbols on paid plan.
3. **CRSP via WRDS** — the academic gold standard; needs institutional access.

Until one exists, H-149/H-150 reports keep the declared −30% Shumway/Warther haircut and the
`names_never_priceable` block. Do not silently drop the names; do not claim the tail is measured.

## Workstream D — forward-test wiring (build now, promote later)

1. Emit the H-150 paper book as forward rows in `reports/forward_observations.jsonl`
   (`hypothesis_id: "H-150"`, `opened_at`/`closed_at` real timestamps, `entry_px` at the next
   open, `exit_px` at the closed fire, `benchmark_leg_ret` from SPY over the identical window,
   `fees`, `funding: 0`).
2. Register a pod in `audit_dashboard/data/audit2_pods.json` with `status: "pre_registered"`,
   `hypothesis_id: "H-150"`, and `registered_at` set **before** the first emitted row.
3. Let `alpha_engine/audit3_tribunal.py::forward_gate_block` decide. Promotion needs
   n ≥ 100, net PF CI-LB > 1.0 **or** IR ≥ 0.5, 100% honest intrabar first-touch, benchmark
   coverage ≥ 90%.
4. `/audit2` displays that clock; it never promotes.

## Sequence and gates

A and B run in parallel today. B's number is only reportable if A clears its bar. C is blocked
on procurement (ask the user for a Polygon or Tiingo key; do not scrape). D's emitter can be
written now and will stay dark until B yields a candidate.

## Definition of done

- A: artifact committed with its metrics, or the negative result documented.
- B: `reports/h150_gpa_backtest_2026-11-22.json` + a `reports/*.md` narrative + registry update.
- C: a documented vendor decision (key present or explicitly declined).
- D: one dry-run row through `forward_gate_block` proving the schema is accepted (eligible or a
  named blocking reason), not merely that the file parses.

## Non-goals

No new strategies, no parameter sweeps on H-150, no promotion from any dashboard, no changes to
`tools/edge_stability_harness.py`.
