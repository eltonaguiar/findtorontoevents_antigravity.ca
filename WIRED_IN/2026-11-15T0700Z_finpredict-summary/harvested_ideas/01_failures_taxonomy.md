# Failure Taxonomy — Finpredict Project

1. Overfitting / data snooping — too many parameter trials; curve-fit (verified_strategies.py sma200 tuned in-sample, failed OOS).
2. Look-ahead bias — future data leaked; TIME_EXIT forging (quality_gates.py:2800-2802).
3. Survivorship / universe bias — ghost rows (22,947), duplicate groups (1,864).
4. Unrealistic cost model — original strategies had no cost model; 10bp added in harness.
5. Weak signal-to-noise — COT 93.8% post-dedup WR~40% PF~0.17; TLT negative Sharpe.
6. Regime dependence — wins only in bull; TLT/IWM fail in bear.
7. Implementation gap — emitter always-on STRONG_BUY below 200dMA vs plan "blocked".
8. Insufficient sample size — ^DXY n=0; ETH n days insufficient.
9. Wrong objective — raw return vs risk-adjusted; projects pivoted late to Sharpe/DD/wealth.
10. Risk management failures — 72% SHORT exposure; fixed by MAX_SHORT_FRACTION=0.60.
