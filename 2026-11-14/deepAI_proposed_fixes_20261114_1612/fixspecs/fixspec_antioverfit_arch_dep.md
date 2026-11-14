# Fix spec — Anti-overfit validator integrity

## Problem (evidence)
- Live anti_overfit_audit.json (Nov 14): 80 strategies audited → **69 OVERFIT_LIKELY (86%),
  6 EDGE_LIKELY_REAL, 5 UNDETERMINED**. June: 31/38 overfit. The gate is doing its job — but:
- Reality Check (White 2000) has **never run**: `reality_check_pvalue requires the 'arch'
  package (see requirements-validation.txt)` — the error is embedded in the artifact itself.
- Portfolio PBO was computed on **n_observations=21, 5 folds** — statistically meaningless; the
  artifact still prints `verdict: SELECTION_EDGE_SURVIVES`.
- Some EDGE_LIKELY_REAL rows in June had WR=100% (n=24) with HIGH_AUTOCORR flag — survivor-grade red flags.

## Proposed changes
1. **Install `arch`** in audit-dashboard.yml validation step:
   `pip install -r requirements-validation.txt || pip install arch` before the validator; and make
   the validator **fail loudly** (non-zero) when Reality Check can't run, instead of embedding the
   error string and passing.
2. **Minimum sample for portfolio-level PBO**: require n_observations >= 100 before emitting a
   portfolio verdict; otherwise emit `INSUFFICIENT_DATA` (do not claim SELECTION_EDGE_SURVIVES).
3. **Flag WR>=95% on n>=15** as `SUSPECT_DATA_QUALITY` (check for resolver mislabels rather than edge).
4. Report the **deflated Sharpe ratio** with the actual number of trials N = size of the strategy
   universe searched (361 families + babies + mutations), not just the audited subset — the
   deflation must reflect how many candidates were tried.
5. Keep the honest OVERFIT_LIKELY verdicts flowing to the dashboard — this gate is the best part
   of the system; make it unignorable (surface_truth headline already exists — add verdict counts).

## Acceptance test
- reality_check p-value present in anti_overfit_audit.json (not an error string).
- No portfolio verdict with n_observations<100.
- EDGE_LIKELY_REAL count changes only with real data behind it.
