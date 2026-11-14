# Common themes and adjudication

## Confidence labels

- **Verified here:** checked directly in the current GitHub tree, current worktree, or source code.
- **Peer-reported:** found in a reviewed peer report, but not recomputed from its underlying dataset in this pass.
- **Open:** multiple explanations remain; do not make a production or profitability decision from it yet.

## Convergent findings

### 1. Measurement is not yet a dependable basis for promotion

Peer packages report large divergences among the official verdict, `pf_registry`, raw-pick summaries, and dashboard cohorts. Examples include CRYPTO counts of 3,705 versus 22,055, and ETF win rates from 2.22% to 68.42%. These are reported snapshots from different filters, not automatically proof that one file is wrong. The real defect is that each consumer needs a stable `cohort_id`, filter hash, source timestamp, and row-level denominator so same-cohort results can be reconciled.

Other reports identify stale or unavailable prices rendered as zero/unchanged PnL, status relabeling, mixed PnL units in some stores, zero/null entries, duplicates, and zombie/expired rows. The local peer audit says the 3,500-row `recent_closed` payload recomputes from entry/exit prices, while the remote peer audit describes unit heuristics and mixed-unit upstream stores. Treat these as **different stores/cohorts until reconciled**, not as a single universal 100x defect.

### 2. Crypto stop-fill fidelity is material, but the fix is not proof of edge

The local `final_v3` reports attribute most crypto stop overshoot to `kimi_riseoftheclaw` and report a gap-aware resolver/replay. The same package reports non-crypto `SL_HIT` rows that did not touch the recorded stop. This suggests a tracker-specific exit-writer issue and a broader stop/trailing-stop taxonomy issue.

Important caveats:

- The local reports disagree on the non-crypto replay counts: one reports 16/25 EQUITY and 13/25 ETF stops untouched; another reports 14/25 and 10/25. The latter says a fixed five-day replay window was not truncated to each recorded exit.
- Source review found the resolver can fall back to the declared stop when the open price is unavailable, and the cost gate can pass on missing/stale evidence. Therefore “gap-aware shipped” does not mean every fill is measured or safe.
- Counterfactual fills at the stop are optimistic bounds; they do not prove a realizable return.

**Decision:** preserve raw outcomes; add fill provenance and replay only through the actual exit timestamp. Keep all strategy conclusions provisional until real post-fix forward observations exist.

### 3. Promotion gates are weaker than their reports imply

**Verified in source:** `alpha_engine/money_ready_verdict.py` defaults both the FDR and single-source enforcement flags to off (`MONEY_READY_FDR_GATE` and `MONEY_READY_SINGLE_SOURCE_GATE` default to `"0"`). In contrast, `ml_gatekeeper/gatekeeper.py` enables leakage-feature masking by default. The masking change requires compatible retraining and train/score artifact parity; it is not itself proof that the resulting model passes forward evaluation.

The source audit also found:

- `tools/per_class_cost_gate.py` treats missing/stale/unknown/thin evidence as fail-open in some paths (`:29,152-179`).
- `tools/hc_gates_python.py` has a gate-exception pass path (`:522-536`).
- `audit_trail/dashboard_generator.py` suppresses after-cost stamping errors (`:7772-7789`).

That conflicts with descriptions of a hard, fail-closed money-ready gate. A missing measurement must not be presented as a pass. Promotion status and live-emission behavior should be controlled separately to avoid silently halting production.

### 4. “Validated” strategy claims conflict and should be withdrawn pending reproduction

- **VWAP mean reversion:** one report labels it validated; multiple later reviews dispute its Sharpe/PBO interpretation, symbol/sample definition, and stop-aware result. Do not retain a `VALIDATED`/`PROVEN` label without the exact code, data snapshot, trial count, and independent reproduction.
- **Crypto mega-mutation / Variant C:** reports disagree about which payload was used and describe synthetic/replay rows, inconsistent aggregates, and missing reproducible inputs/outputs. Preserve as a hypothesis, not a live edge.
- **Variant C archive conflict:** the claims matrix calls the Nov-14 result reproduced on a 34.58 MB payload, while its peer review says the Nov-14 input and output log are absent and the available same-schema payload produces the opposite result. The "reproduced" label is unsupported until the exact payload, output, and command are archived.
- **Mega-mutation composition:** a peer review says 21/50 reported forward picks are synthetic/replay rows and that the aggregate and per-symbol table use different row sets. A positive aggregate headline is not forward proof.
- **Funding carry:** the peer synthesis says all three pre-registered candidates failed proof; a BTC-only capital-adjusted estimate is based on n=10 and only narrowly exceeds a cash comparison. This is not a promotion case.
- **COT contrarian:** the local simulation report says its chosen parameters were selected on the in-sample segment, but source review could not confirm the exact selection expression. Audit the selector before treating the OOS result as independent.

### 5. Multiple peer reviews are not independent market evidence

Many reviewers use the same ledger snapshots, reports, and model-generated summaries. Agreement raises confidence that an artifact needs investigation; it does not multiply the effective sample size or establish an edge. Count independent datasets, independent code paths, and trials separately.

## Conflicts to resolve before prioritization

| Conflict | What is currently supported | Required resolution |
|---|---|---|
| Same-class WR/PF values differ widely | Different source files and cohorts exist; common cohort identity is missing | Recompute identical row IDs with explicit filters and hashes |
| Non-crypto stop-touch replay counts differ | Two local reports give different sample outcomes; replay may extend beyond actual exit | Re-run only after clipping bars to each recorded exit and publishing exact sample IDs |
| Cost gate described as hard enforcement | Source audit found fail-open behavior and suppressed errors | Define unknown/stale as `INSUFFICIENT`, log the reason, and test the caller path |
| Mutual-fund data claimed absent | Local cache inventory found NAV/price CSV caches and generated outputs | Record cache hashes/date spans and link each output to its exact input snapshot |
| GitHub Actions safeguards claimed absent | Current workflow scan found 161/360 with concurrency and 271/360 with timeouts | Correct the local report's “zero” claim; assess missing safeguards by workflow purpose |
| SubQ comparison claimed in some package titles | No provider invocation or raw response was verified | Label peer/manual comparison honestly; rerun only with configured access and archived response metadata |

## Priority order

1. Fix quote/PnL/exit provenance and same-cohort reconciliation.
2. Make promotion gates fail closed on unknown evidence; keep emission control as a separate, reviewed decision.
3. Reproduce the stop-fill and crypto-forward claims with immutable inputs and exit-bounded replay.
4. Only then run benchmark-relative EQUITY and CRYPTO tests with pre-registered trial IDs.
5. Defer lower-priority classes until their source data is real, current, and class-correct.

