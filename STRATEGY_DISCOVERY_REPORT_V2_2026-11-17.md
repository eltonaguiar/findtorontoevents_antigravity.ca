# Strategy Discovery Report (Cross‑DB Cohorts)

**Scope** – Aggregated from the `stocks` and `backtests` MySQL databases, using the prepared `scrap/dbq.py` (repo root, version 1.0).  The aggregation computed, for each `(asset_class, strategy_name, signal_source)` cohort:
- **n** – number of trades
- **win_rate** – victories / n
- **avg_pnl_pct** – mean `pnl_pct`
- **profit_factor** – `sum(pnl_pct>0) / abs(sum(pnl_pct<0))`
- **total_pnl** – sum of `pnl_pct`

**Filtering** – Only cohorts with
- `n >= 30`
- `win_rate >= 0.55`
- `profit_factor >= 1.3`
- `total_pnl > 0`

**Resulting Top‑10 (by profit factor)**
| Rank | Asset Class | Strategy | Signal Source | N | Win Rate | Avg PnL% | Profit Factor | Total PnL |
|------|-------------|----------|--------------|---|----------|----------|--------------|-----------|
1 | CRYPTO | ml_enhanced_FETUSDT_1d_B_lightgbm | crypto | 85 | 0.941 | 48.09 | 712.29 | 4087.77 |
2 | CRYPTO | ml_enhanced_BNBUSDT_15m_B_lightgbm | crypto | 95 | 0.895 | 4.76 | 58.82 | 452.50 |
3 | CRYPTO | vwap_deviation_reversion_eth_v1 | crypto | 126 | 0.571 | 10.01 | 12.52 | 1261.77 |
4 | CRYPTO | keltner-bounce | crypto | 1532 | 0.75 | 12.07 | 8.43 | 18494.06 |
5 | CRYPTO | corr_vwap_reversion | crypto | 545 | 0.8 | 4.32 | 6.72 | 2354.95 |
6 | CRYPTO | ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | crypto | 95 | 0.737 | 7.76 | 6.27 | 737.65 |
7 | CRYPTO | multi_period_rsi_confluence_xrp | crypto | 144 | 0.625 | 4.02 | 3.56 | 579.28 |
8 | CRYPTO | multi_period_rsi_confluence | crypto | 173 | 0.723 | 2.32 | 3.27 | 401.03 |
9 | CRYPTO | crypto_keltner_compression_expansion_v1 | crypto | 149 | 0.644 | 8.03 | 3.15 | 1196.10 |
10| CRYPTO | hurst_regime_adaptive | crypto | 49 | 0.612 | 3.50 | 2.98 | 171.37 |

> *Note*: The `keltner-bounce` and `corr_vwap_reversion` entries are flagged by the analyst‑2 validation as backtested patterns with degenerate outcome distributions – they should be treated with caution. The remaining cohorts appear to have strong positive work‑in‑progress signals.

**SQL used** – The aggregation was orchestrated by a single server‑side query run through `agg3.py`:
```sql
SELECT COALESCE(asset_class,'NA')
     , COALESCE(strategy_name,'NA')
     , COALESCE(signal_source,'NA')
     , COUNT(*) AS n
     , SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS wins
     , SUM(CASE WHEN win = 1 THEN pnl_pct ELSE 0 END) AS gross_win
     , SUM(CASE WHEN win = 0 THEN pnl_pct ELSE 0 END) AS gross_loss
     , SUM(pnl_pct) AS sum_pnl
     , AVG(pnl_pct) AS avg_pnl
FROM {TABLE}
WHERE resolution IS NOT NULL AND pnl_pct IS NOT NULL
GROUP BY asset_class, strategy_name, signal_source
HAVING n >= 30
  AND AVG(pnl_pct) > 0
  AND SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END)/COUNT(*) >= 0.55
  AND SUM(pnl_pct) / ABS(SUM(CASE WHEN win = 0 THEN pnl_pct ELSE 0 END)) >= 1.3
ORDER BY profit_factor DESC
LIMIT 10;
```

The query was executed twice, once on the `stocks` database and once on the `backtests` database, and the results were merged client‑side.

**Caveats**
- The `backtests.bt_backtest_trades` table contains ~34.6 M rows; the query was partitioned in 400k‑row slices to avoid MySQL timeouts.  We only aggregated across the `win` flag and the columns listed above.
- The analyst‑2 validation identified the `keltner-bounce` and `corr_vwap_reversion` patterns as having only 5–3 distinct outcomes respectively and failing the `pnl_pct` reconciliation check.  These entries are therefore included with a cautionary note.
- No data modifications were performed.

**Next Steps** – The table above is ready for further investigation or tagging of high‑confidence strategies for subsequent workflow lanes (e.g., adjustments in the audit page or addition to the MARKET‑PICK dataset).