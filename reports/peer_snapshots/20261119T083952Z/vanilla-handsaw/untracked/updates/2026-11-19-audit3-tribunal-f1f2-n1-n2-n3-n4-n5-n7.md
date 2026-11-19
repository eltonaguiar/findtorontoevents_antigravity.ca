# audit3 tribunal — statistical-gate hardening (2026-11-19)

**Branch:** `add-strategy-variable-tracking` (vanilla-handsaw worktree)
**Module:** `alpha_engine/audit3_tribunal.py`, `alpha_engine/audit3_selection_alpha.py`
**Review:** `docs/AUDIT3_REVIEW_2026-11-19.md`

## What was broken

The audit3 judge had five blind spots that could grant a `PROVEN_T2` / `CANDIDATE`
verdict on an edge that was not real, plus one rule that existed only as prose:

1. **F1 — i.i.d. bootstrap.** `bootstrap_mean_ci` resampled trades independently.
   Picks overlap in calendar time and share symbols, so the G2 net-expectancy CI
   was too tight and inflated both promotion verdicts.
2. **F2 — split-half only checked `mean > 0`.** A half with a +0.001% mean counted
   as stable.
3. **N1 — no repeated-looks correction.** BH FDR is per run, but the ledger is
   re-scored every ~6h; a cell that crosses q ≤ 0.10 once eventually does so by
   chance.
4. **N2 — no verdict-churn monitor.** Nothing tracked a cell flipping verdicts
   between runs.
5. **N3 — no recency/regime gate.** `PROVEN_T2` had no requirement that the edge
   still be present in the recent window.
6. **N4 — flat materiality floor.** `PROVEN_MIN_NET_CI_LO_PCT = 0.05` is meaningful
   for FOREX (5bp cost) and inside the noise for CRYPTO (15bp cost).
7. **N5 — selection alpha ignored hold time.** A 1-hour pick and a 30-day pick
   were equated in the M1b headline.
8. **N7 — the freeze rule was not enforced.** "No new strategy while a P0 item is
   open" existed only in `docs/EDGE_IDEAS_BACKLOG_2026-11-19.md`.

## What changed

### F1 block bootstrap
- `_circular_blocks(rng, n, block_len)`; `bootstrap_mean_ci(..., block=False)` with
  `block_len = max(1, int(sqrt(n)))`, same seed / `n_boot` / percentile CI.
- `evaluate_cell` passes `block=True` for the G2 net CI and the 2× cost stress.
- Default stays i.i.d., so callers that do not opt in cannot silently change.

### F2 split-half materiality
- `split_half_ok(values, min_mean=0.0)`; `evaluate_cell` passes the per-cell floor.

### N1 repeated-looks (G8)
- `PERSISTENCE_RUNS = 2`; `cell_key`, `load_history`, `save_history`,
  `apply_persistence_gate`.
- A `CANDIDATE`/`PROVEN_T2` raw verdict must persist across 2 consecutive runs;
  `first_pass_at` records the run that began the streak.
- CLI `--history`, `--history-write`, `--persistence-runs`; report `persistence`.
- `audit3-ledger.yml` persists `audit_dashboard/data/audit3_verdict_history.json`.

### N2 verdict churn
- `apply_persistence_gate` stamps `raw_verdict` per cell.
- `load_prev_verdicts`, `compute_verdict_churn` (alert when tracked ≥ 20 and rate
  > 30%); report `verdict_churn`.
- CLI `--prev-ledger`, `--max-churn` (exit 3, fail-closed before the ledger and
  history sidecar are written); workflow passes `--prev-ledger` + `--max-churn 0.30`.

### N3 recency gate
- `recency_ok` — trailing `max(5, round(25%·n))` closes must have non-negative net
  mean; rows ordered by `closed_at`/`timestamp`.
- `PROVEN_T2` capped at `CANDIDATE` on a stale regime; per-cell `recency`/`recent_ok`.

### N4 cost-scaled materiality floor
- `materiality_floor(mean_cost_pct) = max(0.05, 0.5 · mean round-trip cost)`.
- Used for both the split-half floor and the `PROVEN_T2` CI lower bound; per-cell
  `mean_cost_pct` / `materiality_floor_pct`.

### N5 hold-time-normalised selection alpha
- `audit3_selection_alpha.py` now reports `hold_days_mean`, `hold_days_median`,
  `alpha_per_day_pct`, `alpha_annualized_pct`, `min_hold_days`, `n_min_hold`,
  `min_hold_participation`, `alpha_pct_min_hold`. `alpha_pct` is unchanged.

### N7 freeze gate
- `reports/strategy_freeze.json` (P0 = E11/E13/E14, with unfreeze conditions).
- `tools/strategy_freeze_gate.py` (exit 1 frozen / 0 clear / 2 manifest error).
- Enforced as the first step of `.github/workflows/forward-test-new-strategies.yml`.

## How it was verified

- `tests/test_audit3_tribunal.py` — 34 passed (F1, F2, N1, N2, N3, N4).
- `tests/test_audit3_selection_alpha.py` — 11 passed (N5).
- `tests/test_strategy_freeze_gate.py` — 4 passed (N7).
- Full audit3 + freeze set — **86 passed**.
- Two-run N1 smoke: run 1 demoted 7 cells (`n_candidate` 0, `n_weak` 1); run 2
  promoted 7 with `first_pass_at` = first-run timestamp; a no-history run left the
  gate off (`available: False`).
- N2 CLI smoke: `--max-churn 0.0` exits 3 and writes nothing.
- End-to-end smoke on the synthetic 150-row payload: exit 0, verdicts unchanged,
  `recency` / `materiality_floor_pct` populated.

## Not done (still open)

- N6 — excluded-cohort bias audit (46% integrity-excluded, 9,100 auto-expired).
- E11 (FX backfill + symbol mapping), E13 (PIT stamping), E14 (exit redesign).
- E12 — 90-day hold-benchmark pilot.
- Fund-manager beta-core sleeve config (Conservative) — see
  `docs/FUND_MANAGER_QUICK_VIABLE_PLAN_2026-11-19.md`.

## Doctrine note

None of these delete or demote anything under "innocent until proven guilty";
they tighten when a claim is granted. `KILL`/`WEAK` behaviour is unchanged, and
all new gates are backward-compatible (defaults preserve the old path).
