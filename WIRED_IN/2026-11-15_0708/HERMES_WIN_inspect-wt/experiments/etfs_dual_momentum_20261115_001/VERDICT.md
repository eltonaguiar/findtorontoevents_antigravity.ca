# VERDICT — etfs_dual_momentum_20261115_001

**Result: DEAD** (5/9 offline gates passed; gate 9 needs live paper trading)

| Proof step | Gate | Pass |
|---|---|---|
| 1_temporal_discipline | | PASS |
| 2_walk_forward_stability | | PASS |
| 3_multiple_testing | | FAIL |
| 4_monte_carlo | | FAIL |
| 5_friction | | PASS |
| 6_significance | | FAIL |
| 7_regime_robustness | | PASS |
| 8_shuffle_control | | FAIL |
| 9_forward_test | | FAIL |
| 10_reproducibility | | PASS |

## Headline numbers

- Test-period CAGR: 10.93% vs SPY 16.79%
- Test-period Sharpe: 0.79 vs SPY 0.90
- Test excess return (ann): -5.96%, t=-1.17, p(1-sided)=0.8784
- Max drawdown (test): -25.68% vs SPY -33.72%
- Deflated Sharpe: 0.1382 (trials=1307)
- Shuffle control: FAIL (shuffled data matches or beats real) (real SR 0.60 vs shuffled p95 1.15)
- Walk-forward efficiency: 1.30

## Reproduction

```bash
cd WIRED_IN/2026-11-15_0708/HERMES_WIN_inspect-wt
python experiments/etfs_dual_momentum_20261115_001/run.py --seed 42
```