# audit3 review — second pass (2026-11-19)

**Reviewer:** Kilo (vanilla-handsaw worktree)
**Subject:** `/audit3` — `alpha_engine/audit3_tribunal.py`, the ledger, and the
publish path.
**Method:** read `audit3_tribunal.py` end-to-end, the plan
`docs/plans/2026-11-19-audit3-v2-evidence-and-success-metric-plan.md`, the two
prior reviews (`AUDIT_SURFACE_REVIEW_2026-11-19.md`,
`AUDIT3_FEEDBACK_RESPONSE_2026-11-19.md`), and the edge backlog
`docs/EDGE_IDEAS_BACKLOG_2026-11-19.md`. The three sibling worktrees
(`universal-pisces`, `witty-fight`, `lapis-chronometer`) contain no distinct
work — clean checkouts at `origin/main` — so nothing new was harvested there.

---

## What the peers already closed (do not re-propose)

Merged to main via PR #904 and #905:

| Item | Status |
|---|---|
| Canonical denominator (`resolved_closed_view.py`) — A2 | ✅ merged |
| Measured cost in audit3 (per-class + per-strategy) — A3/F4 | ✅ merged |
| One smart-picks definition — A5 | ✅ merged |
| Dead tiles out, gates on by default — A6 | ✅ merged |
| Concentration gate blocks `PROVEN_T2` (`top_sym_share <= 0.60`) — F3 | ✅ already in code |

My earlier draft flagged the concentration gate as "report-only"; that was wrong —
line 773 already fail-closes `PROVEN_T2`. Dropped.

---

## Still open (this review's contribution)

Priority = probability of changing a decision × certainty of correctness.

### F1 — Bootstrap CIs assume i.i.d. trades (the biggest open item)

`bootstrap_mean_ci` (`audit3_tribunal.py:189`) resamples individual trades
independently. Picks overlap in calendar time and share symbols, so the G2 net‑
expectancy CI is too tight: some of the "positive" cells pass the edge gate more
often than the true FDR allows (i.e. it inflates both `PROVEN_T2` and
`CANDIDATE`).

**Fix:** block bootstrap over overlapping calendar windows using each row's
open/close timestamps (rows are already sorted chronologically in `load_rows`).
Keep the same seed, same `n_boot`, same percentile CI; only the resampling unit
changes from a trade to a block. Backward-compatible signature:
`bootstrap_mean_ci(values, *, times=None, block='auto', ...)` — when `times` is
absent, current i.i.d. behaviour is preserved, so an unvalidated change cannot
silently alter verdicts.

**Test to write:** overlap-injection — a cell whose wins are all inside one
week must show a *wider* CI than the same PnLs spread uniformly over a year.
Without that test, the fix is unverified.

### F2 — Split-half stability only checks `mean > 0`

`split_half_ok` (line 308) requires each half's raw mean to be positive. A half
with a microscopic +0.001% mean passes. Change to require each half's **CI lower
bound** (or a materiality floor, e.g. `PROVEN_MIN_NET_CI_LO_PCT`) to be
positive. Rerun to confirm no cell silently flips.

### N1 — Repeated-looks correction across runs

BH FDR (G3) is applied per run, but `audit3-ledger.yml` re-scores every ~6h.
The same cell is re-tested over time, so a cell that crosses q≤0.10 once will
eventually do so by chance. Enforce an always-valid / alpha-spending rule, or
require a verdict to persist across K consecutive runs before `CANDIDATE`/`PROVEN_T2`
and record `first_pass_at`. This is the largest blind spot the existing docs do
not cover.

### N2 — Verdict-churn monitor

Nothing tracks a cell flipping verdicts between runs. Add a `verdict_churn`
ledger + alert: high churn means the judge is noisy, not that the edge is real.

### N3 — Evidence recency / regime gate on promotion

`PROVEN_T2` has no recency requirement. Add a trailing-window sanity check (last
~25% of a cell's history must be non-negative net), else cap at `CANDIDATE`.

### N4 — Promotion materiality floor should scale with cost-model error

`PROVEN_MIN_NET_CI_LO_PCT = 0.05` is a fixed 5bp. That is meaningful for FOREX
(2bp cost) but inside the noise for CRYPTO (15bp). Tie the floor to the applied
cost model's error per class.

### N5 — Selection alpha should be hold-time-normalised

M1b equates a 1-hour pick with a 30-day hold. Report annualised / per-hold-time
selection alpha plus a minimum hold-time participation so the headline isn't
dominated by short-timing trades.

### N6 — Bias-direction audit of the excluded 78.6%

The coverage panel now publishes counts, but nobody samples the excluded cohorts
(46% integrity-excluded, 9,100 auto-expired) to learn whether they are random or
systematic. Periodic random-sample audit of excluded rows, estimating sign and
magnitude of selection bias on the retained 21.4% slice.

### N7 — "No new strategy while P0 open" is a sentence, not a gate

The backlog states the freeze rule; nothing in the CI/publish path enforces it.
Wire it as a gate (block new scan emission while E11/E13/E14 are open).

---

## Suggested order

1. F1 (block bootstrap + overlap test) — fixes the most likely false-positive source.
2. N1 (repeated-looks) — closes the multi-run FDR hole.
3. N2 (verdict churn) — monitoring, cheap.
4. F2, N3, N4 — tighten promotion without changing the doctrine.
5. N5, N6 — measurement honesty.
6. N7 — enforcement.

Doctrine note: none of the above deletes or demotes anything under
"innocent until proven guilty"; they tighten when a claim is *granted*.

---

## Shipped (2026-11-19, `add-strategy-variable-tracking`)

| Item | Implementation | Verification |
|---|---|---|
| F1 block bootstrap | `bootstrap_mean_ci(..., block=)` + `_circular_blocks`; `evaluate_cell` passes `block=True` for the G2 net CI and the 2× cost stress | `test_block_bootstrap_widens_clustered_ci` |
| F2 split-half materiality | `split_half_ok(..., min_mean=PROVEN_MIN_NET_CI_LO_PCT)` wired in `evaluate_cell` (default keeps old behaviour) | `test_split_half_requires_material_mean` |
| N1 repeated-looks | `PERSISTENCE_RUNS=2`; `cell_key`/`load_history`/`save_history`/`apply_persistence_gate`; report `persistence` block; CLI `--history`/`--history-write`/`--persistence-runs`; `audit3-ledger.yml` sidecar | 6 tests + two-run smoke (7 demoted → 7 promoted) |
| N2 verdict churn | `raw_verdict` stamped per cell; `load_prev_verdicts`/`compute_verdict_churn`; report `verdict_churn`; CLI `--prev-ledger`/`--max-churn` (exit 3); `audit3-ledger.yml` passes `--prev-ledger` + `--max-churn 0.30` | 4 tests incl. CLI exit-3 |
| N3 recency gate | `recency_ok` trailing 25% (min 5) net-mean check; `PROVEN_T2` capped at `CANDIDATE` on a stale regime; per-cell `recency`/`recent_ok` | 3 tests |
| N4 cost-scaled floor | `materiality_floor(mean_cost)` = max(5bp, 50% of mean round-trip cost); used for both the split-half floor and the `PROVEN_T2` CI lower bound; per-cell `mean_cost_pct`/`materiality_floor_pct` | 2 tests |
| N5 hold-time-normalised alpha | `alpha_per_day_pct`, `alpha_annualized_pct`, `hold_days_mean/median`, `min_hold_participation`, `alpha_pct_min_hold` in `audit3_selection_alpha.py` | 2 tests |
| N7 freeze gate | `reports/strategy_freeze.json` + `tools/strategy_freeze_gate.py`; enforced at the top of `forward-test-new-strategies.yml` | `tests/test_strategy_freeze_gate.py` (4 tests) |

Still open: N6 (excluded-cohort bias audit), plus E11/E13/E14 and the E12
hold-benchmark pilot.

Suite: `tests/test_audit3_tribunal.py` 34 passed; `test_audit3_edge_hunt.py`
15 passed; `test_audit3_selection_alpha.py` 11 passed; full audit3 + freeze set
86 passed. End-to-end smoke on the synthetic 150-row payload: exit 0, verdicts
unchanged, `recency`/`materiality_floor_pct` populated.
