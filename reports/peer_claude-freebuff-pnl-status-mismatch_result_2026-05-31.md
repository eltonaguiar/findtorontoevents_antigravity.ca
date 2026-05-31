# Result: Repaired 44 pnl_status_mismatch rows (freebuff DB health 2026-05-31)

## Summary
- Pre-apply count (`tools/repair_data_integrity.py` dry-run): **44**
- Post-apply count (same mismatch SQL): **0**
- Backup table: `ejaguiar1_backups.trading_picks_pre_freebuff_pnl_status_mismatch_20260531` (44 rows, full schema clone minus CHECK constraint).
- Repair script: `tools/repair_data_integrity.py --apply` (Status/PnL Contradiction task).
- CHECK constraint already present on `trading_picks` (`chk_pnl_sign_coherence`) — script's migration step reported `Duplicate check constraint`, which is expected/benign.

## Distribution of the 44 rows
| dimension | counts |
|-----------|--------|
| category | forex=40, commodity=4 |
| before.status | LOST=23, TP_HIT=21 |
| pnl_pct sign | positive=23 (LOST→WON), negative=21 (TP_HIT→LOST) |

All 44 are tiny-magnitude FX/commodity contradictions (|pnl_pct| ≤ ~0.01%) — classic outcome-resolver microstructure mislabels from the CI run between freebuff's two health snapshots. Consistent with the FOREX/COMMODITY resolver fix bundle (5bp non-CRYPTO threshold per `alpha_engine/outcome_resolver.py:115-126`), but a fresh-resolver pass relabeled before the threshold was applied.

## Verification spot-check (5 IDs)
| id | before.status / pnl | after.status / pnl |
|----|--------------------|--------------------|
| consensus_EURGBP=X_BUY_20260421_2152 | LOST / 0.0058 | WON / 0.0058 |
| consensus_EURGBP=X_BUY_20260422_0655 | LOST / 0.0046 | WON / 0.0046 |
| consensus_EURJPY=X_SELL_20260413_1556 | LOST / 0.0027 | WON / 0.0027 |
| cta_commodity_momentum_term::SI=F::2026-04-17_1532 | LOST / 0.0061 | WON / 0.0061 |
| cta_cross_asset_tsmom::GC=F::2026-04-13_1941 | LOST / 0.0084 | WON / 0.0084 |

`exit_reason` updated with ` (REPAIRED_PNL_CONTRADICTION)` suffix (truncated to varchar(30) on some rows — does not affect correctness).

## Full row table (44 rows, before snapshot)
| id | category | before.status | before.pnl_pct |
|----|----------|---------------|----------------|
| consensus_EURGBP=X_BUY_20260421_2152 | forex | LOST | 0.0058 |
| consensus_EURGBP=X_BUY_20260422_0655 | forex | LOST | 0.0046 |
| consensus_EURJPY=X_SELL_20260413_1556 | forex | LOST | 0.0027 |
| cta_commodity_momentum_term::SI=F::2026-04-17_1532 | commodity | LOST | 0.0061 |
| cta_cross_asset_tsmom::GC=F::2026-04-13_1941 | commodity | LOST | 0.0084 |
| cta_cross_asset_tsmom::USDCAD=X::2026-04-16_2222 | forex | LOST | 0.0036 |
| multi_asset_forex_rsi2_mean_reversion::EURGBP=X::2026-04-21_1443 | forex | LOST | 0.0057 |
| multi_asset_forex_rsi2_mean_reversion::EURGBP=X::2026-04-22_0549 | forex | LOST | 0.0058 |
| multi_asset_forex_rsi2_mean_reversion::GBPUSD=X::2026-04-15_1036 | forex | TP_HIT | -0.0041 |
| multi_asset_forex_rsi2_mean_reversion::GBPUSD=X::2026-04-15_1535 | forex | TP_HIT | -0.0041 |
| multi_asset_forex_rsi2_mean_reversion::USDJPY=X::2026-04-12_2349 | forex | TP_HIT | -0.0006 |
| multi_asset_forex_rsi2_mean_reversion::USDJPY=X::2026-04-13_0854 | forex | LOST | 0.0044 |
| multi_asset_futures_momentum::HG=F::2026-04-22_1536 | commodity | TP_HIT | -0.0082 |
| multi_asset_futures_momentum::PL=F::2026-04-16_0650 | commodity | LOST | 0.0093 |
| multi_asset_ig_contrarian_sentiment::AUDJPY=X::2026-04-13_2030 | forex | LOST | 0.0053 |
| multi_asset_ig_contrarian_sentiment::AUDJPY=X::2026-04-15_0845 | forex | TP_HIT | -0.0009 |
| multi_asset_ig_contrarian_sentiment::EURGBP=X::2026-04-21_2122 | forex | LOST | 0.0081 |
| multi_asset_ig_contrarian_sentiment::EURGBP=X::2026-04-22_0549 | forex | LOST | 0.0058 |
| multi_asset_ig_contrarian_sentiment::EURGBP=X::2026-04-23_1937 | forex | LOST | 0.0046 |
| multi_asset_ig_contrarian_sentiment::EURGBP=X::2026-04-24_2023 | forex | TP_HIT | -0.0081 |
| multi_asset_ig_contrarian_sentiment::EURGBP=X::2026-04-28_0317 | forex | TP_HIT | -0.0058 |
| multi_asset_ig_contrarian_sentiment::EURJPY=X::2026-04-13_2151 | forex | TP_HIT | -0.0059 |
| multi_asset_ig_contrarian_sentiment::EURJPY=X::2026-04-14_1836 | forex | TP_HIT | -0.0069 |
| multi_asset_ig_contrarian_sentiment::EURJPY=X::2026-04-17_1127 | forex | LOST | 0.0059 |
| multi_asset_ig_contrarian_sentiment::GBPJPY=X::2026-04-14_1236 | forex | LOST | 0.0019 |
| multi_asset_ig_contrarian_sentiment::GBPJPY=X::2026-04-15_0549 | forex | LOST | 0.0060 |
| multi_asset_ig_contrarian_sentiment::GBPJPY=X::2026-04-15_0941 | forex | TP_HIT | -0.0005 |
| multi_asset_ig_contrarian_sentiment::GBPUSD=X::2026-04-15_1036 | forex | TP_HIT | -0.0041 |
| multi_asset_ig_contrarian_sentiment::USDCAD=X::2026-04-20_0316 | forex | TP_HIT | -0.0088 |
| multi_asset_ig_contrarian_sentiment::USDCHF=X::2026-04-15_1836 | forex | TP_HIT | -0.0077 |
| multi_asset_myfxbook_retail_contrarian::AUDJPY=X::2026-04-16_1739 | forex | TP_HIT | -0.0097 |
| multi_asset_myfxbook_retail_contrarian::AUDJPY=X::2026-04-16_1936 | forex | LOST | 0.0061 |
| multi_asset_myfxbook_retail_contrarian::AUDJPY=X::2026-04-20_2223 | forex | TP_HIT | -0.0097 |
| multi_asset_myfxbook_retail_contrarian::AUDUSD=X::2026-04-15_2126 | forex | TP_HIT | -0.0093 |
| multi_asset_myfxbook_retail_contrarian::AUDUSD=X::2026-04-17_1725 | forex | TP_HIT | -0.0057 |
| multi_asset_myfxbook_retail_contrarian::CADJPY=X::2026-04-20_1933 | forex | LOST | 0.0052 |
| multi_asset_myfxbook_retail_contrarian::EURGBP=X::2026-04-12_2118 | forex | TP_HIT | -0.0046 |
| multi_asset_myfxbook_retail_contrarian::EURGBP=X::2026-04-21_2122 | forex | LOST | 0.0081 |
| multi_asset_myfxbook_retail_contrarian::EURGBP=X::2026-04-23_2223 | forex | TP_HIT | -0.0058 |
| multi_asset_myfxbook_retail_contrarian::EURJPY=X::2026-04-14_2224 | forex | LOST | 0.0085 |
| multi_asset_myfxbook_retail_contrarian::EURJPY=X::2026-04-15_0942 | forex | TP_HIT | -0.0016 |
| multi_asset_myfxbook_retail_contrarian::EURJPY=X::2026-04-17_0850 | forex | TP_HIT | -0.0053 |
| multi_asset_myfxbook_retail_contrarian::EURJPY=X::2026-04-17_1127 | forex | LOST | 0.0059 |
| multi_asset_myfxbook_retail_contrarian::USDCAD=X::2026-04-21_1133 | forex | LOST | 0.0044 |

## Reproducer
```bash
# Dry-run check
DB_PASS_STOCKS='***' python3 tools/repair_data_integrity.py

# Apply (this PR's action)
DB_PASS_STOCKS='***' python3 tools/repair_data_integrity.py --apply

# Verify
mysql -e "SELECT COUNT(*) FROM trading_picks WHERE
  (status IN ('WON','TP_HIT','closed_win') AND pnl_pct < 0)
  OR (status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0)"
# expect 0
```

## Follow-up
The CI outcome-resolver run between freebuff's two health snapshots re-mislabelled 44 closed picks. The resolver's class-aware threshold (`PNL_WIN_THRESHOLD_BY_CLASS`) prevents this on fresh closes; this batch suggests a re-resolution path is bypassing it. Trace upstream in `alpha_engine/outcome_resolver.py` re-evaluation entry points and add a regression test that calls the resolver on closed rows with |pnl_pct| < 5bp and asserts status is preserved.
