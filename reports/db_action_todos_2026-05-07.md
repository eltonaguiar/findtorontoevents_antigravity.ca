# DB Action Todos — 2026-05-07

Curated from `reports/db_master_synthesis_2026-05-07.md` after live forensic run on `ejaguiar1_stocks` (29.4M rows in `bt_backtest_trades`).

## P0 — Quarantine + freeze investigation (blocks every aggregate)

1. **Quarantine `quan_engine` MATICUSDT LONG ghosts** — 215,248 rows at constant pnl_pct=−15.0000. Add ingest filter in `audit_trail/dashboard_generator.py`:
   ```sql
   NOT (symbol='MATICUSDT' AND strategy IN ('quan_engine','quan_engine_scalp','quan_engine_swing','meta_strategy'))
   ```
2. **Quarantine `meta_strategy` constant-pnl template family** — ~1.6M rows at pnl_pct ∈ {+5.0, −3.0}. Filter:
   ```sql
   NOT (strategy='meta_strategy' AND ROUND(pnl_pct,4) IN (5.0000,-3.0000))
   ```
3. **Drop phantom-closed rows at ingest**:
   ```sql
   NOT (status='EXPIRED' AND pnl_pct=0 AND exit_price=entry_price)
   ```
   Removes ~9,600 EQUITY/FUTURES/ETF + ~5,280 FOREX zeros.
4. **Investigate `at_consensus_picks` EQUITY 2.2% WR (n=403)** — only consensus-grade EQUITY data, catastrophic.
5. **Investigate 2026-04-02 forward-validator freeze** — WON/LOST/expired writes stopped 35d ago. Only CRYPTO `CLOSED` fresh.
6. **Investigate quan_engine constant-pnl writer** in `outcome_resolver.py` (or wherever quan_engine writes). Root cause of #1.

## P1 — Schema + importer fix

7. Generated `terminal_outcome` column on `bt_backtest_trades`:
   ```sql
   terminal_outcome ENUM('WIN','LOSS','OPEN','FLAT') GENERATED ALWAYS AS (
     CASE WHEN pnl_pct>0 THEN 'WIN'
          WHEN pnl_pct<0 THEN 'LOSS'
          WHEN status='OPEN' THEN 'OPEN'
          ELSE 'FLAT' END) STORED
   ```
8. Add `paper_trade BOOL DEFAULT FALSE` + heuristic backfill (`confidence IS NULL AND raw_data IS NULL AND pnl_pct=0` → TRUE).
9. Add `exit_reason ENUM('TP_HIT','SL_HIT','TIMEOUT','EXPIRED','MANUAL','UNKNOWN')`.
10. Fix importer: populate `confidence` + `raw_data` from upstream JSON (currently NULL on all sample rows; blocks ML retrain).
11. `source_system` virtual column:
    ```sql
    source_system VARCHAR(80) GENERATED ALWAYS AS (
      REGEXP_REPLACE(source_db,'^.*/([^/]+)/data/.*$','$1')) VIRTUAL
    ```
12. Status enum normalize: rewrite WIN/WON/TP_HIT/CLOSED_TP → WIN, LOST/LOSS/SL_HIT/CLOSED_SL → LOSS at importer + retroactive UPDATE.

## P2 — Re-route + dedupe + retrain

13. Re-route `/audit` EQUITY feed away from `bt_backtest_trades` to:
    - `challenge_200_trades` (n=620, ML-mode WR 57.1%, +$1,211 — only positive non-CRYPTO edge)
    - `consensus_tracked` (n=235 closed, 44.3% WR, ~break-even)
    - `at_raw_picks` EQUITY (n=105, 41.9%)
    - **NOT** `at_consensus_picks` EQUITY (2.2% WR — broken, see P0 #4)
14. Flag FUTURES + ETF as **INSUFFICIENT DATA** in /audit until phantom-close bug fixed.
15. Dedupe FOREX duplicate rows by `(strategy, symbol, entry_time, direction)` — 18.3% are KIMI re-imports of same AUDUSD/EURUSD picks.
16. Re-train `meme_ml_models` on production-scale `bt_backtest_trades.MEMECOIN` (n=123,648 closed, PF 0.58) — current model trained on 50-row leakage fixture, recall=1.0 in-sample.
17. Restart `lm_sports_ml_predictions` writer (cold since 2026-02-16) + `lm_sports_clv` writer (cold since 2026-02-12).
18. 3 composite indexes: `(asset_class,status)`, `(strategy,asset_class)`, `(source_db,source_table)`. Existing single-col indexes cover the rest.

## P3 — Backlog

19. Move `at_large_backtest_results.equity_curve_json + trade_log_json` to Parquet on object store (14GB → ~1GB).
20. Per-class partition `bt_backtest_trades` once 50M rows.
21. Archive legacy `backtest_results` (2 rows) + `backtest_trades` (50 rows).
22. Fix `tools/sql_dump_analyzer.py` multi-line state machine (low priority — live DB queryable).
23. Investigate ghost tables in `ejaguiar1_sportsbet` (`lm_sports_ml_metrics`, `lm_*_odds` per-sport, `meme_ml_predictions`).
24. Materialized `asset_class_health` snapshot table refreshed nightly (result stability — DB grew 28.7M → 29.4M in 1h).

## QA gates (post-implementation)

- After P0 #1+#2 quarantines: re-run Q1 (asset class verdict) and confirm CRYPTO PF moved off the noise floor (target: PF > 0.7 from cleaned data, was 0.46 raw).
- After P1 #7 (terminal_outcome): every consumer query rewrites to `WHERE terminal_outcome IN ('WIN','LOSS')`. `dashboard_generator.py:_pick_pnl_pct` uses generated column, not status string match.
- After P1 #10 (importer fix): NULL ratio for `confidence` < 5% on rows imported after the fix; ml_score correlation w/ pnl_pct sign rerun on cleaned data.
- After P2 #13 (EQUITY re-route): /audit EQUITY tile shows >0 terminal trades and asset_class_health.equity matches `challenge_200_trades` aggregate.

## Future watch

- Daily cron: alert if `quan_engine MATICUSDT` ghost-row count grows OR if any new (strategy, symbol, direction, ROUND(pnl_pct,4)) cohort exceeds n>1000.
- Weekly: NULL-ratio drift check for `confidence`, `raw_data`, `exit_reason` per asset_class.
- Monthly: re-run Q14 cohort drift across all strategies (currently uncomputable).
- After importer freeze investigation: confirm WON/LOST writes resume; alert if last_write age > 24h on any non-OPEN status.
