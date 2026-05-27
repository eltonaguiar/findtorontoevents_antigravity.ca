# Deduplication Manifest - Asset Class MD Files (2026-05-27)

## Scope
All `reports/asset_class_90day_plan_*.md` files reviewed for duplicate content.

## Files Analyzed
1. `reports/asset_class_90day_plan_FUTURES_2026-05-15.md` (194 lines)
2. `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md` (223 lines)
3. `reports/asset_class_90day_plan_EQUITY_2026-05-15.md` (243 lines)
4. `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md`
5. `reports/asset_class_90day_plan_FOREX_2026-05-15.md`
6. `reports/asset_class_90day_plan_PENNY_MEME_2026-05-15.md`
7. `reports/asset_class_90day_plan_ETF_2026-05-15.md`
8. `reports/asset_class_90day_plan_BOND_2026-05-15.md`

## Key Overlaps
- **FUTURES/COMMODITY**: Shared symbols `GC=F, SI=F, HG=F` in both config dicts
- **EQUITY/PENNY_MEME**: EQUITY includes some penny/memes in its 18-ticker universe
- **COMMODITY/ETF**: Both use proxy tickers (USO/UNG overlap with COMMODITY_SYMBOLS)

## Recommendation
Merge FUTURES into COMMODITY per EAGLE.MD Phase 1, then deprecate separate FUTURES bucket.
Separate EQUITY into `LARGE_CAP_EQUITY_SYMBOLS` vs `PENNY_MEME_SYMBOLS` to reduce noise.

## Action Items
- [x] FUTURES/COMMODITY overlap documented
- [ ] EQUITY/PENNY_MEME split to be done (per EQUITY 90-day plan)
- [ ] ETF/commodity proxy conflict to be resolved