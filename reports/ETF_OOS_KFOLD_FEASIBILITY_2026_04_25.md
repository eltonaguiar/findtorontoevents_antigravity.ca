# ETF OOS Purged K-Fold — Feasibility Note (2026-04-25)

## Question

Per synthesis #364 §9 / Copilot Cloud's PR #365 recommendation: rerun
`audit_trail/hc_edge_revalidation.py` with **purged K-Fold CV** on the current ETF
sample to decide whether to admit ETF to `passesValidatedEdgePerClass` in
`audit_dashboard/hc_filter.js`.

## Sample as of 2026-04-25 (dashboard_payload.json.recent_closed)

| Cohort | n | wins | losses | WR |
|---|---:|---:|---:|---:|
| ETF total | 84 | — | — | — |
| ETF decided (WON / LOST) | 81 | — | — | — |
| ETF passing proposed gate (`fwd_wr ≥ 50` AND `score ≥ 45`) | 30 | 19 | 11 | **63.3%** |

Spread across 18 unique close days.

## Why purged K-Fold isn't useful here yet

For a meaningful purged K-Fold the held-out fold needs to give a stable
WR estimate. With n=30 across 5 folds (`alpha_engine/validation/purged_cv.py`
default):

- Fold size ≈ 6 picks
- Expected fold wins ≈ 3.8 ± Wilson 95% CI ≈ ±0.46 (i.e. WR error ±~7-8 percentage points per fold)
- Combined across 5 folds with purge + embargo: effectively just splitting noise

K=3 is no better — fold size 10, single misclassified pick swings WR by 10pp.

The 81-decided baseline cohort is the same problem, just with a different
gate. Pre-gate WR is too small a sample to estimate stably across folds
with the temporal-purge constraint that purged-CV requires.

## Concrete unblock conditions

1. **Sample N ≥ 100 ETF decided** AND **N ≥ 50 passing the proposed gate**.
   At current intake (~5-10 ETF picks/day), expect that threshold around
   2026-05-15 to 2026-06-01.
2. **OR** use a Bayesian shrinkage with conjugate Beta(α, β) prior derived
   from EQUITY/CRYPTO confidence-band data, where the posterior mean is
   reported with credible interval. For n=30 + Beta(40, 40) prior: posterior
   mean WR ≈ 56%, 95% CrI ≈ [48%, 64%] — the prior dominates, which is the
   right answer when the data is this thin.

Either path defers the live admission decision past a single cycle.

## Recommendation (no PR)

- **Do not** add an ETF branch to `passesValidatedEdgePerClass` yet.
- **Keep** the provisional ETF branch in `audit_trail/hc_edge_revalidation.py`
  (calibration-only) so the WR continues to be tracked over time.
- **Re-evaluate** when ETF decided ≥ 100 (estimated ~3-6 weeks from this doc).
- **Alternative**: consider whether the dashboard UX would benefit from
  showing "Provisional gate (calibration only): N=30, WR 63.3%" in the BOND/ETF
  column instead of "No validated filter". That's a UI change, not a gate change.

## Cross-references

- #361 (Cursor): "filterHcStrict drops BOND/ETF/FUTURES is policy, not bug"
- #364 §4 Layer 4: "BOND/ETF pilot deferred until purged K-Fold CV"
- #365 (Copilot Cloud): proposed provisional ETF thresholds `score≥45 + conf≥0.65`
- #369 (`/updates` entry): published ETF 57.7% WR on N=26 with provisional gate
- `audit_trail/hc_edge_revalidation.py`: now has provisional ETF branch
- 2026-05-15 check: passing-gate cohort N=51, WR=66.7%, still below the 100 threshold. Re-scheduled for 2026-05-29.
