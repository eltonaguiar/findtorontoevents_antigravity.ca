# Integrations Benchmark on Real Closed Picks

**Run:** 2026-04-22 17:11:05 UTC

_Note: the wrapper modules in alpha_engine/*_integration.py were wiped by a branch-switch + untracked-stash race mid-session. This benchmark calls the underlying libraries directly (interpret, pyod) and ships a pure-Python Purged K-Fold inline. Findings below are real; the wrapper layer can be restored separately._

## Headline findings

- Dataset: **5,135 closed picks**, baseline WR **0.297**, PF **0.392**
- Majority-class baseline (always predict LOSS) = **0.7028** -- EBM must beat this to add value
- Strongest score-outcome correlation: **method_a_score** r = +0.1761
- `confidence` correlates **-0.0866** with WIN (memory: 'confidence != edge'; confirmed negative)
- EBM top feature: **feature_0000** (importance 0.5513)
- EBM out-of-sample accuracy: **0.6735** (5 purged folds). Lift over majority-class: **-0.0293**
- pyod flagged **249 picks** (5%). WR flagged=0.3333 vs normal=0.2944 (delta -0.0389)


## Baseline

```json
{
  "n_picks": 5135,
  "wins": 1526,
  "losses": 3609,
  "win_rate": 0.2972,
  "profit_factor": 0.392,
  "gross_profit_pct": 542.1552,
  "gross_loss_pct": 1383.144,
  "mean_pnl_pct": -0.1638
}
```


## Score-vs-outcome correlations

```json
{
  "elite_score": 0.149,
  "ml_composite_score": 0.149,
  "method_a_score": 0.1761,
  "confidence": -0.0866,
  "consensus_pct": 0.0983
}
```


## EBM global feature importance (full data)

| feature                     |   importance |
|:----------------------------|-------------:|
| feature_0000                |    0.551331  |
| feature_0013 & feature_0014 |    0.380722  |
| feature_0001 & feature_0008 |    0.182106  |
| feature_0014                |    0.175734  |
| feature_0003 & feature_0014 |    0.171522  |
| feature_0008 & feature_0014 |    0.159588  |
| feature_0003                |    0.13812   |
| feature_0009 & feature_0014 |    0.134347  |
| feature_0012                |    0.120085  |
| feature_0002                |    0.114045  |
| feature_0001                |    0.112843  |
| feature_0013                |    0.112381  |
| feature_0007                |    0.0952913 |
| feature_0006                |    0.0945833 |
| feature_0009                |    0.0828498 |
| feature_0008                |    0.0716441 |
| feature_0010                |    0.0628962 |
| feature_0011                |    0.0614767 |
| feature_0017                |    0.0354848 |
| feature_0018                |    0.0353663 |


## EBM purged-K-Fold CV accuracy

```json
{
  "mean_accuracy": 0.6735,
  "std_accuracy": 0.0518,
  "folds": 5
}
```


## pyod ECOD regime filter (5% contamination)

```json
{
  "contamination": 0.05,
  "n_anomalous": 249,
  "n_normal": 4722,
  "wr_anomalous": 0.3333,
  "wr_normal": 0.2944,
  "pf_anomalous": 0.5757,
  "pf_normal": 0.3812,
  "mean_pnl_anomalous": -0.0533,
  "mean_pnl_normal": -0.1758
}
```


## Per-source-system WR/PF

| source_system   |    n |   win_rate |   profit_factor |   mean_pnl_pct |
|:----------------|-----:|-----------:|----------------:|---------------:|
| quan_engine     | 4998 |     0.2975 |          0.3922 |        -0.1677 |
| rapid_fire      |  137 |     0.2847 |          0.3049 |        -0.0214 |


## Runtime

```json
{
  "elapsed_seconds": 45.56
}
```

