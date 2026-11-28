
## 20260606T034825Z  fix_unknown_category
- source: `ejaguiar1_stocks.trading_picks`
- where: `category IS NULL OR category='UNKNOWN' OR category=''`
- archive: `ejaguiar1_backups.trading_picks_fix_unknown_category_20260606T034825Z`
- rows: 515

## 20261128T025107Z  category_enum
- source: `ejaguiar1_stocks.trading_picks`
- where: `CAST(category AS BINARY) IN ('crypto','forex','commodity','index','equity','prediction_market','futures','bond','etf','meme','managed_futures') AND category <> ''`
- archive: `ejaguiar1_backups.trading_picks_category_enum_20261128T025107Z`
- rows: 49,570
