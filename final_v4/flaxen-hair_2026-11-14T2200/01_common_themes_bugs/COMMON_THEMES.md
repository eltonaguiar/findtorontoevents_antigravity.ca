# Common Themes and Bugs

**Source:** background agent's `final_v3/feat-stop-fill-cost-gate-final-v3/00-common-themes/ADJUDICATION.md` + local `final_v3` reports + source-code audit
**Worktree:** flaxen-hair_2026-11-14T2200

## Confidence Labels

- **Verified here:** checked directly in the current GitHub tree, current worktree, or source code
- **Peer-reported:** found in a reviewed peer report, but not recomputed from its underlying dataset
- **Open:** multiple explanations remain; do not make production/profitability decisions from it yet

## Convergent Findings

### 1. Measurement is not yet a dependable basis for promotion (Peer-reported + Verified)

Peer packages report large divergences among official verdict, `pf_registry`, raw-pick summaries, and dashboard cohorts:
- CRYPTO counts: 3,705 vs 22,055 (6× difference)
- ETF win rates: 2.22% vs 68.42% (85× spread)

These are reported snapshots from different filters, not automatically proof that one file is wrong. The real defect: each consumer needs a stable `cohort_id`, filter hash, source timestamp, and row-level denominator so same-cohort results can be reconciled.

Other defects: stale/unavailable prices rendered as zero/unchanged PnL, status relabeling, mixed PnL units in some stores, zero/null entries, duplicates, zombie/expired rows.

### 2. Crypto stop-fill fidelity is material, but the fix is not proof of edge (Verified + Peer-reported)

Local `final_v3` reports attribute most crypto stop overshoot to `kimi_riseoftheclaw`. Non-crypto `SL_HIT` rows did not touch the recorded stop.

Critical caveats:
- Local reports disagree on non-crypto replay counts: 16/25 EQUITY and 13/25 ETF stops untouched vs 14/25 and 10/25 (five-day replay window not truncated to actual exit)
- Source review found resolver can fall back to declared stop when open price unavailable; cost gate can pass on missing/stale evidence
- Counterfactual fills at stop are optimistic bounds, not proof of realizable return

**Decision:** preserve raw outcomes; add fill provenance and replay only through actual exit timestamp. Keep all strategy conclusions provisional until real post-fix forward observations exist.

### 3. Promotion gates are weaker than reports imply (Verified in source)

| Gate | Source | Default | Problem |
|------|--------|---------|---------|
| `MONEY_READY_FDR_GATE` | `alpha_engine/money_ready_verdict.py` | OFF (`"0"`) | Not enforced |
| `MONEY_READY_SINGLE_SOURCE_GATE` | `alpha_engine/money_ready_verdict.py` | OFF (`"0"`) | Not enforced |
| Cost gate (`per_class_cost_gate.py`) | `:29,152-179` | Fail-open on missing/stale/unknown | Missing evidence can pass |
| HC gate (`hc_gates_python.py`) | `:522-536` | Gate-exception pass path | Errors silently pass |
| After-cost stamping (`dashboard_generator.py`) | `:7772-7789` | Errors suppressed | Failures not visible |

**Missing measurement must not be presented as a pass.** Promotion status and live emission should be controlled separately.

### 4. "Validated" strategy claims conflict and should be withdrawn (Peer-reported)

| Claim | Status | Reason |
|-------|--------|--------|
| VWAP mean reversion | Disputed | Multiple later reviews dispute Sharpe/PBO interpretation, symbol/sample definition, stop-aware result |
| Crypto mega-mutation / Variant C | Disputed | Reports disagree on payload used; synthetic/replay rows; inconsistent aggregates; missing reproducible inputs/outputs |
| Variant C archive | Unsupported | Claims matrix says Nov-14 result on 34.58 MB payload; peer review says input/output absent; available same-schema payload produces opposite result |
| Mega-mutation composition | Disputed | Peer review: 21/50 forward picks synthetic/replay; aggregate and per-symbol table use different row sets |
| Funding carry | Failed | All 3 pre-registered candidates failed proof; BTC-only capital-adjusted estimate based on n=10, narrowly exceeds cash |
| COT contrarian | Unverified | Parameters selected on in-sample segment; source review could not confirm exact selection expression |

### 5. Multiple peer reviews are not independent market evidence (Verified)

Many reviewers use same ledger snapshots, reports, model-generated summaries. Agreement raises confidence an artifact needs investigation; does not multiply effective sample size or establish an edge.

## Conflicts to Resolve Before Prioritization

| Conflict | Currently Supported | Required Resolution |
|----------|--------------------|-------------------|
| Same-class WR/PF differ widely | Different source files/cohorts; no common cohort identity | Recompute identical row IDs with explicit filters and hashes |
| Non-crypto stop-touch replay counts differ | Two local reports give different sample outcomes; replay may extend beyond actual exit | Re-run clipping bars to each recorded exit, publish exact sample IDs |
| Cost gate described as hard enforcement | Source audit found fail-open behavior and suppressed errors | Define unknown/stale as `INSUFFICIENT`, log reason, test caller path |
| Mutual-fund data claimed absent | Local cache inventory found NAV/price CSV caches and generated outputs | Record cache hashes/date spans; link each output to exact input snapshot |
| GitHub Actions safeguards claimed absent | Current workflow scan found 161/360 with concurrency, 271/360 with timeouts | Correct local report's "zero" claim; assess missing safeguards by workflow purpose |
| SubQ comparison claimed | No provider invocation/response verified | Label peer/manual comparison honestly; rerun only with configured access |

## Priority Order

1. Fix quote/PnL/exit provenance and same-cohort reconciliation
2. Make promotion gates fail closed on unknown evidence; keep emission control separate
3. Reproduce stop-fill and crypto-forward claims with immutable inputs and exit-bounded replay
4. Only then run benchmark-relative EQUITY and CRYPTO tests with pre-registered trial IDs
5. Defer lower-priority classes until source data is real, current, and class-correct
