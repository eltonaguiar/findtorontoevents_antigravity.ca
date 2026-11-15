# AUDIT_REPORT.md — template

Target: `reports/quant_audit/AUDIT_REPORT.md`. Fill every cell or write `NOT MEASURED` with
the reason. No cell is allowed to contain an adjective where a number belongs.

---

# Quant audit — findtorontoevents.ca/audit

**Audit date:** YYYY-MM-DD
**Ledger snapshot:** `audit_dashboard/data/dashboard_data.json`, `generated_at` = `<value>`
**Rows in scope:** `<n>` closed picks across `<k>` strategies, `<c>` asset classes
**Verdict:** nothing PROVEN / `<class>` PROVEN on `<timeframe>` (delete one)

## 0. One-page answer

- **Best candidate:** `<strategy>` on `<asset class>` / `<timeframe>`
- **Why it is not already proven:** `<the single gate item it fails, or "nothing — it passes G1-G10">`
- **Next measurement that would settle it:** `<one experiment, one metric, one decision threshold>`
- **What would kill it:** `<the observation that ends the question>`

## 1. Instrument audit

| Instrument | File | What it proves | What it does not prove | Wired into live path? |
|---|---|---|---|---|
| Deflated Sharpe | `alpha_engine/deflated_sharpe.py` | Sharpe survives N trials | nothing about costs | `<file:line>` / no |
| Walk-forward | `alpha_engine/walkforward_validator.py` | stability across folds | nothing about multiplicity | |
| PBO / CSCV | `<path or ABSENT>` | backtest-overfitting probability | | |
| White's Reality Check | `<path or ABSENT>` | best-of-family significance | | |
| Bootstrap PF | `<path>` | PF distribution | | |
| Clustered t | `tools/pick_excess.py` | excess significance per episode | | |
| OF interim looks | `tools/forward_tracker.py` | pre-registered sequential test | nothing yet (n=0) | |
| Quality gates | `audit_trail/quality_gates.py` | what a pick must clear to emit | not a profitability test | yes |

## 2. Inventory (strategies that actually traded)

| Strategy | Class | TF | Entry | Exit | TP/SL | Sizing | Method | n | WR | PF | Net ret | Failure mode(s) | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | F# | `path` |

Rules for this table:
- `n < 30` → write `UNPROVEN` in the Failure-mode column, not a failure code.
- Failure codes are F1–F10 from the prompt; cite the artifact that shows it (e.g. `F2` needs the
  feature that reads future data, with the line number).
- `Net ret` means after fees/spread/slippage, and `excess` vs the class benchmark belongs in
  the next table, not in a footnote.

## 3. Catalogue-only strategies (never traded)

| Count | Where | Why it never traded | Note |
|---|---|---|---|
| `<n>` | `stabilization/strategy_registry.json`, `incubator/`, `baby_strategies/` | no forward allocation | one line, no per-strategy table |

## 4. Method ledger (what must not be "discovered" again)

| Method | Implemented at | Ever gated a live decision? | Verdict on the method here |
|---|---|---|---|
| Deflated Sharpe | | | |
| PBO / CSCV | | | |
| CPCV / purged k-fold | | | |
| White's Reality Check / SPA | | | |
| Block bootstrap | | | |
| Permutation / sign-flip null | | | |
| Wilson lower bound | | | |
| OF alpha spending | | | |
| HMM regime | | | |
| Kalman filter | | | |
| Cointegration (EG / Johansen) | | | |
| GARCH / vol targeting | | | |
| Gradient boosting | | | |
| Deep sequence models | | | |

A row whose "gated a live decision" is `no` is not evidence that the method was tried — it is
evidence that it was written.

## 5. Failure taxonomy roll-up

| Code | Meaning | Strategies affected | Share of closed picks |
|---|---|---|---|
| F1 | overfitting / data snooping | | |
| F2 | look-ahead | | |
| F3 | survivorship / universe | | |
| F4 | unrealistic costs | | |
| F5 | edge below noise | | |
| F6 | regime dependence | | |
| F7 | backtest-vs-live gap | | |
| F8 | insufficient sample | | |
| F9 | wrong objective | | |
| F10 | risk-management failure | | |

## 6. What this audit could not measure

| Item | Missing input | What it would take |
|---|---|---|
| | | |

## 7. Evidence index

Every number above must be reproducible from one of these:

| Artifact | Produced by | Command |
|---|---|---|
| `reports/quant_audit/evidence/*.json` | `<script>` | `<exact command>` |
