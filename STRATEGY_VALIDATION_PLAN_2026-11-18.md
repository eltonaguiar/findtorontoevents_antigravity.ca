# Strategy Validation Plan

**Date**: 2026-11-18  
**Author**: eaguiar2015  
**Scope**: Per-asset-class winning-strategy validation  
**Disclaimer**: PLAN ONLY — no backtests executed.

---

## 1. Equities / US Stocks  
- **Candidate Strategy**: None specified — refer to STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md, most promising strategies likely align here.  
- **DB/Table/SQL**: `ejaguiar1_stocks.at_raw_picks` filtered by criteria from Table 1 in STRATEGY_DISCOVERY_REPORT
  ```sql
  SELECT * FROM at_raw_picks WHERE pnl_pct IS NOT NULL AND n >= 30
  ```
- **Expected n**: 85 (source from STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md, line 19)  
- **Win Rate**: 0.941 (source from STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md, line 19)  
- **Profit Factor**: 712.29 (source from STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md, line 19)
- **Pass/Fail Thresholds**: n >= 30, PF >= 1.25, Win Rate >= 0.55 (baseline from STRATEGY_DISCOVERY_REPORT)
- **Known Blockers**: BLOCKED-1045, access through proxy `ejaguiar1_stocks`

---

## 2. ETFs  
- **Candidate Strategy**: None specified — similar considerations apply as for equities.  
- **DB/Table/SQL**: `ejaguiar1_stocks.trading_picks` worked on with criteria likely detailed in BONDS_EDGE_VERDICT_2026-11-17.md  
- **Expected n**: 60  
- **Win Rate**: 0.183 (source from BONDS_EDGE_VERDICT_2026-11-17.md, line 27)  
- **Profit Factor**: 0.25 (source from BONDS_EDGE_VERDICT_2026-11-17.md, line 27)
- **Pass/Fail Thresholds**: n >= 30, PF >= 1.25, Win Rate >= 0.55 (baseline from report)
- **Known Blockers**: Same as above.

---

## 3. Bonds  
- **Candidate Strategy**: cta_cross_asset_tsmom (from BONDS_EDGE_VERDICT_2026-11-17.md, line 14)
- **DB/Table/SQL**: `ejaguiar1_stocks.trading_picks` and `at_pick_outcomes` for closed yields
  ```sql
  SELECT * FROM at_pick_outcomes
  WHERE bond_sym IN ("TLT","IEF") AND pnl_pct>0
  ```
- **Expected n**: 108 (source from BONDS_EDGE_VERDICT_2026-11-17.md, line 13)  
- **Win Rate**: 36.1% (source from BONDS_EDGE_VERDICT_2026-11-17.md)
- **Profit Factor**: 1.35 (source from BONDS_EDGE_VERDICT_2026-11-17.md)
- **Pass/Fail Thresholds**: n >= 30, PF >= 1.25, Win Rate >= 0.55
- **Known Blockers**: As above.

---

## 4. Crypto  
- **Candidate Strategy**: ml_enhanced_FETUSDT_1d_B_lightgbm (source STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md)
- **DB/Table/SQL**: `ejaguiar1_stocks.crypto_ohlcv`
  ```sql
  SELECT * FROM crypto_ohlcv WHERE timestamp IS NOT NULL
  ```
- **Expected n**: 126  
- **Win Rate**: 0.571 (source from STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md)
- **Profit Factor**: 12.52 (source from STRATEGY_DISCOVERY_REPORT_V2_2026-11-17.md)
- **Pass/Fail Thresholds**: n >= 30, PF >= 1.25, Win Rate >= 0.55
- **Known Blockers**: None.

---

## 5. Prediction Markets  
- **Candidate Strategy**: predictions from Kalshi (assumed to be active)
- **DB/Table/SQL**: `prediction_market_consensus`
  ```sql
  SELECT * FROM prediction_market_consensus
  ```
- **Expected n**: 0 (currently unverified)
- **Win Rate**: UNKNOWN (data inconsistencies noted)
- **Profit Factor**: UNKNOWN (data inconsistencies noted)
- **Pass/Fail Thresholds**: n >= 30, PF >= 1.25, Win Rate >= 0.55
- **Known Blockers**: None.

---

| Known Blockers | Description |
|----------------|-------------|
| BLOCKED-1045 | Access to `ejaguiar1_stocks` is the only viable proxy | 
| SKIPPED-LARGE | backtests.bt_backtest_trades ~34.6M rows must sample or partition | 

---

## Validation Sequence
1. **Equities Cohort Check**  
   Estimate: 10 mins  
   Tool/Command: `dbq query`
2. **Bonds Analysis**  
   Estimate: 10 mins  
   Tool/Command: `dbq query`
3. **Crypto Verification**  
   Estimate: 10 mins  
   Tool/Command: `dbq query`
4. **Finalize Reporting**  
   Estimate: 15 mins  
   Tool/Command: Compile results

---

## Data Quality Caveats
- `CROSS_DB_DATA_QUALITY_MATRIX.md` noted multiple issues regarding pnl discrepancies particularly noted in the stocks DB.

---

## Stop/Rollback Condition
- If any strategy fails to meet the minimum validity criteria (n >= 30, PF >= 1.25, Win Rate >= baseline), the respective strategy will be dropped from consideration.