# Winner Hunt Backtest — Track 13 / Track 14 Report

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*

**Date:** 2026-10-23 · **Commit:** `504050d5e8008aac08c49fa6e075d9be7056df88` (`feat(track14): expand symbol universe in ASSET_CLASS_CONFIGS + normalization maps; re-run winner-hunt backtest`)

---

## 1. Executive Summary

The winner-hunt backtest screened **599 strategies** across the full strategy registry under a strict, FDR-corrected four-gate taxonomy. The hunt classified each strategy as `ELITE`, `SURVIVOR`, or `FAILED`.

**No ELITE or SURVIVOR strategy survived.** All 599 strategies are classified as `FAILED`. Eight strategies passed all four gates, but were excluded from winner status because they are flagged as single-source artifacts (their edge is not corroborated across multiple independent data sources). Four additional "near-winner" strategies were blocked by the maximum-drawdown gate.

This zero-survivor outcome is a deliberate, conservative filter: it reflects the decision to prize corroboration across multiple sources and to reject strategies with excessive drawdown, rather than to be permissive. It is **not** evidence that the screened universe is valueless — it is evidence that no strategy cleared the full bar of sample size, profit factor, lower confidence bound, and drawdown *simultaneously with multi-source corroboration*.

## 2. Methodology

### 2.1 The four gates
Each strategy had to satisfy all of the following concurrently to pass the hard filter (gate thresholds from [`params.gates`](../reports/winner_hunt_results.json)):

| Gate | Threshold | Interpretation |
|------|-----------|----------------|
| Sample size (`n`) | `n >= 100` | Enough closed trades to be meaningful |
| Profit factor (`PF`) | `PF >= 1.5` | Gross profit ≥ 1.5× gross loss |
| Lower confidence bound (`CI_LB`) | `CI_LB >= 1.2` | Lower bound of the PF confidence interval exceeds 1.2 |
| Maximum drawdown (`MDD`) | `MDD <= 0.2` (20%) | Drawdown contained to ≤20% |

### 2.2 FDR correction
Following the gate filter, p-values were corrected for multiple testing using **Benjamini–Hochberg** at **α = 0.05** over a family of **599** tests (`fdr_family_size = 599`). A strategy could only be a winner if it passed all four gates *and* remained significant after FDR correction.

### 2.3 Single-source artifact exclusion
Strategies whose edge comes from a single data source (`is_single_source_artifact = true`, e.g. `file:mysql:at_pick_outcomes`) are **excluded from winner status** regardless of gate performance, because their edge is not corroborated across multiple sources. These appear under `gate_passers_excluded_as_single_source_artifact`.

### 2.4 Symbol expansion (Track 14)
This run includes the symbol-universe expansion from Track 14 (commit `504050d5e80`): `ASSET_CLASS_CONFIGS` and normalization maps were expanded before re-running the winner-hunt backtest. The expansion increased coverage of the registry universe; it did not change the gate or FDR methodology.

## 3. Results

### 3.1 Summary counts

| Metric | Value |
|--------|-------|
| Total strategies screened | 599 |
| FDR family size | 599 |
| Passed all four gates | 8 |
| Passed FDR (significant) | 24 |
| **ELITE** | **0** |
| **SURVIVOR** | **0** |
| FAILED | 599 |

### 3.2 Gate pass counts (per gate)

| Gate | Passed |
|------|--------|
| `n >= 100` | 32 |
| `PF >= 1.5` | 79 |
| `CI_LB >= 1.2` | 33 |
| `MDD <= 0.20` | 329 |

### 3.3 Single-source artifacts excluded after passing all gates

| Strategy | Asset class | n | PF | CI_LB | MDD |
|----------|-------------|----|----|-------|-----|
| AuditEnsemble_LONG | CRYPTO | 135 | 155.850 | 48.284 | 0.011 |
| CorrKamaAdaptiveStrategy | CRYPTO | 138 | 111.808 | 34.646 | 0.000 |
| ADX Trend Confirmation | CRYPTO | 213 | 56.726 | 28.705 | 0.019 |
| mega_mut_macd_rsi_m084 | CRYPTO | 124 | 49.371 | 29.956 | 0.022 |
| CorrVwapZscoreReversionStrategy | CRYPTO | 169 | 33.090 | 18.236 | 0.000 |
| Multi-Timeframe Trend Alignment | CRYPTO | 394 | 11.058 | 8.639 | 0.109 |
| Price Acceleration Detector | CRYPTO | 208 | 10.945 | 7.795 | 0.065 |
| Order Book Imbalance | CRYPTO | 129 | 8.408 | 5.680 | 0.143 |

### 3.4 Near-winners blocked by the drawdown gate

| Strategy | Asset class | n | PF | CI_LB | MDD |
|----------|-------------|----|----|-------|-----|
| Bollinger Squeeze Breakout | CRYPTO | 725 | 1.519 | 1.344 | 3.208 |
| RSI Divergence Scalp | CRYPTO | 102 | 10.335 | 6.438 | 0.230 |
| hs_lb_None | CRYPTO | 190 | 2.723 | 2.128 | 2.875 |
| MeanReversionBB | EQUITY | 191 | 1.706 | 1.343 | 1.333 |

These pass the sample, PF, and CI gates but fail the `MDD <= 0.20` gate, disqualifying them as winners.

## 4. Discussion: Why zero survivors

The zero-survivor result is a **byproduct of the filter being intentionally strict**, not necessarily the absence of any signal in the universe:

1. **Single-source exclusion is the dominant blocker.** Eight strategies were sensational on paper (PF of 8–155, CI lower bounds of 5–48) but derive entirely from a single data source (`file:mysql:at_pick_outcomes`). Because their edge is not corroborated across independent sources, they are deliberately withheld from winner status. This is the single largest reason high-performing strategies did not become ELITE/SURVIVOR.
2. **Drawdown is the second blocker.** Four near-winners cleared the sample/PF/CI gates but showed catastrophic drawdowns (MDD from 0.23 to 3.21, i.e. 23%–321%). A strategy that loses 20%+ of equity is not deployable regardless of aggregate PF.
3. **FDR correction raises the bar.** Only 24 of 599 strategies were significant at BH α=0.05; combined with the gate filter, none cleared every hurdle simultaneously.
4. **Many small-n strategies fail the sample gate.** Most of the 599 are new, small-sample, or mutated strategies with `n < 20`; these cannot clear `n >= 100` and are correctly classified FAILED. They should be treated as unproven, not disproven.

### Implications
- **Do not promote any strategy to ELITE/SURVIVOR from this pass.** There is no battle-tested, multi-source-corroborated winner to ship.
- **Next best candidates are the eight single-source artifacts.** If their edge can be corroborated with a second independent data source (e.g. independent feed, hold-out period, or out-of-sample validation), they would be prime candidates to re-evaluate in a future winner-hunt pass.
- **Drawdown must be a primary design constraint.** Four strategies failed on MDD alone; future generation should prioritize drawdown control over headline PF.
- **Re-run after corroboration work** rather than loosening gate thresholds. Loosening the gates would admit artifacts and unproven small-sample results.

## 5. Commit SHA

Run produced and captured at commit:

```
504050d5e8008aac08c49fa6e075d9be7056df88
```

> (`feat(track14): expand symbol universe in ASSET_CLASS_CONFIGS + normalization maps; re-run winner-hunt backtest`)

Artifacts committed in this state:
- [`reports/winner_hunt_results.json`](../reports/winner_hunt_results.json)
- [`reports/winner_hunt_results.md`](../reports/winner_hunt_results.md)

## 6. Reproducibility

### Environment
- **Python:** 3.12.3
- **Runner:** [`tools/winner_hunt_backtest.py`](../tools/winner_hunt_backtest.py)

### Input data paths
| Input | Path |
|-------|------|
| Strategy registry | `audit_dashboard/data/pf_registry.json` |
| Benchmark ledger | `audit_dashboard/data/benchmark_ledger_proof.json` |
| Money-ready archive | `audit_dashboard/data/money_ready_archive` |

### Command to re-run

From the repository root:

```bash
python3 tools/winner_hunt_backtest.py --human
```

This regenerates both `reports/winner_hunt_results.json` and `reports/winner_hunt_results.md`. The module is deterministic given its inputs (see `run_winner_hunt` in the runner).

### Determinism note
Results are deterministic given the same registry/ledger/archive inputs. The output reflects the symbol-universe expansion from commit `504050d5e80`; re-running on a different registry snapshot may yield different counts.
