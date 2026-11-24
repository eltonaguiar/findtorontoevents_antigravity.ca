# DSR conformance — does a number called `deflated_sharpe` actually deflate?

schema: `dsr_conformance.v1` · trial counts: [1, 26, 121, 4987]

| implementation | file:line | verdict | N=1 | N=121 | negative cell @N=121 | moved |
|---|---|---|---|---|---|---|
| statistical_rigor | `alpha_engine/statistical_rigor.py:339` | **DEFLATES** | 0.9912 | 0.4118 | 0.0001 | 5/5 |
| audit3_tribunal | `alpha_engine/audit3_tribunal.py:399` | **DEFLATES** | — | 0.4120 | 0.0001 | 4/4 |
| anti_overfit_validator | `alpha_engine/anti_overfit_validator.py:418` | **DEFLATES** | 0.9912 | 0.4125 | 0.0001 | 5/5 |
| crypto_ml_edge | `crypto_ml_edge/validation.py:301` | **DEFLATES** | 0.9912 | 0.0000 | 0.0000 | 5/5 |
| deflated_sharpe_deprecated | `alpha_engine/deflated_sharpe.py:179` | **DEFLATES** | 0.9912 | 0.4113 | 0.0001 | 5/5 |
| validation.sharpe_metrics_CANONICAL | `alpha_engine/validation/sharpe_metrics.py:83` | **IGNORES_N** | 31.0548 | 31.0548 | -15.5176 | 0/5 |

## Battery

| scenario | n | target per-period SR | why |
|---|---|---|---|
| h244_etf_10m_n2514_sr0.047 | 2514 | 0.04735 | H-244 measured cell: daily Sharpe 0.04735 over 2514 days |
| top_pick_n26_sr0.18 | 26 | 0.18 | the n=26 cell used for the most-favourable N reading |
| tiny_n8_sr0.30 | 8 | 0.3 | below most implementations' minimum sample; tests fail-closed |
| fat_tail_n1200_sr0.06 | 1200 | 0.06 | fat tails: raw-vs-excess kurtosis conventions diverge here |
| negative_sr_n600 | 600 | -0.05 | a losing cell must not score as significant anywhere |

## Verdict key

* `DEFLATES` — value moves when the trial count rises, stays in [0,1].
* `IGNORES_N` — cannot or does not respond to the trial count. A gate built on this tests an undeflated Sharpe.
* `DEFLATES_UNIT_AMBIGUOUS` — moves with N but leaves [0,1]; it is a z-score published under a probability's name.
* `UNJUDGEABLE` — answered at only one trial count, so sensitivity is unmeasurable.
* `NEVER_RETURNS` / `UNIMPORTABLE` — the implementation could not be driven at all.
