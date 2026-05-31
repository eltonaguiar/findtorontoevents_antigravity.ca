# Plan — INCIDENT_STOCKS #7 residual mistag backfill (2026-05-31)

## Incident
P0: ~90% of EQUITY picks historically mistagged as crypto. PR #147 (MERGED 2026-05-31T03:26Z)
fixed the source code (hardcoded `category="crypto"` at 6 production sites + sync-site
defense-in-depth in `alpha_engine/mysql_trading_sync.py:pick_to_row`). Historical rows
in `trading_picks` remain. Prior backfill rounds appear to have already swept the bulk;
this task is residual cleanup.

## Live state (verified 2026-05-31, ejaguiar1_stocks.trading_picks)

Category distribution: crypto=16102, forex=14868, commodity=6512, equity=2007, futures=428,
index=393, etf=320, stocks=267, ''=240, bond=164, meme=87, stock=23, penny=4, pennystock=4.

Cross-class mistag candidates against current schema:

- **(a) `category='crypto'` AND symbol does NOT look crypto: 10 rows.**
  Examples: USDJPY=X, EURGBP=X, AUDUSD=X, AUDJPY=X (FOREX); SI=F, PL=F, CT=F (COMMODITY).
  All have unambiguous Yahoo-style suffixes (`=X` for forex, `=F` for futures/commodity).

- **(b) `category IN ('equity','stock','stocks')` AND symbol IS crypto: 9 rows.**
  Examples: BNBUSDT, LINKUSDT, AVAXUSDT, BCH-USD, CLUSD (all crypto).
  4 from `kimi_signal_tracking` (BCH-USD), 3 from `regime_terminal` (USDT pairs),
  2 from `polymarket_momentum` (CLUSD).

**Total: 19 rows residual.** Well under 100 → tractable inline backfill.

## Paths
- Source: `alpha_engine/asset_class_classifier.py` (`detect_asset_class()`) — authoritative
  mapping. `=X` → forex; `=F` → commodity/futures; USDT/USDC/-USD → crypto.
- Backup table: `ejaguiar1_backups.trading_picks_pre_stocks7_mistag_20260531` (CREATE FROM
  SELECT of only the 19 affected ids, to keep backup small and targeted).
- Mutation: 19 single-row UPDATEs to `ejaguiar1_stocks.trading_picks.category`.

## Diff
Bucket (a) — set `category` from symbol suffix:
- `=X` (4 rows: USDJPY, EURGBP×3, AUDUSD, AUDJPY×1) → `forex`
- `=F` (5 rows: SI=F×2, PL=F, CT=F, AUDJPY... actually) → `commodity`

Final per-id assignments (19):

| id                                                          | symbol     | old       | new       |
|-------------------------------------------------------------|------------|-----------|-----------|
| widened_tp_momentum_carry::USDJPY=X::2026-05-27             | USDJPY=X   | crypto    | forex     |
| iso_battleground_luxalgo_LINKUSDT_3164812869                | CT=F       | crypto    | commodity |
| multi_asset_myfxbook_retail_contrarian::EURGBP=X::2026-04-24_1538 | EURGBP=X | crypto | forex |
| multi_asset_myfxbook_retail_contrarian::EURGBP=X::2026-04-24_0852 | EURGBP=X | crypto | forex |
| multi_asset_ig_contrarian_sentiment::EURGBP=X::2026-04-24_1538 | EURGBP=X | crypto | forex |
| cc_SI=F_L_202604201643                                      | SI=F       | crypto    | commodity |
| multi_asset_futures_momentum::PL=F::2026-04-17_1339         | PL=F       | crypto    | commodity |
| multi_asset_forex_rsi2_mean_reversion::AUDUSD=X::2026-04-05_0426 | AUDUSD=X | crypto | forex |
| liquidity_sweep_reversal::SI=F::2026-03-16                  | SI=F       | crypto    | commodity |
| widened_tp_momentum_carry::AUDJPY=X::2026-03-12             | AUDJPY=X   | crypto    | forex     |
| pm_momentum_CLUSD_202604221640                              | CLUSD      | equity    | crypto    |
| pm_momentum_CLUSD_202604211639                              | CLUSD      | equity    | crypto    |
| iso_regime_terminal_SPY_6482585562                          | BNBUSDT    | stocks    | crypto    |
| iso_regime_terminal_AMD_2941588445                          | LINKUSDT   | stocks    | crypto    |
| iso_regime_terminal_QQQ_3370855750                          | AVAXUSDT   | stocks    | crypto    |
| 2253                                                        | BCH-USD    | equity    | crypto    |
| 2232                                                        | BCH-USD    | equity    | crypto    |
| 1408                                                        | BCH-USD    | equity    | crypto    |
| 19                                                          | BCH-USD    | equity    | crypto    |

Note: row `iso_battleground_luxalgo_LINKUSDT_…` has id-saying-LINKUSDT but symbol col is
`CT=F`. Symbol is the source of truth for class — set to commodity. Likewise the
`iso_regime_terminal_SPY/AMD/QQQ_…` ids contain equity tickers in the id but the symbol
col shows BNBUSDT/LINKUSDT/AVAXUSDT — these are id/symbol mismatches from a prior
copy-paste bug, not addressed here (separate incident). Class is set from symbol.

## Risk
- LOW. 19 ids, deterministic classifier, full row backup before UPDATE.
- No production code change; DB-only mutation.
- After backfill, EQUITY class metrics on /audit become marginally more honest (drops
  9 mis-attributed rows: 2 EXPIRED, 4 SL_HIT, 2 TP_HIT, 1 LOST — net negative impact
  removed from EQUITY).

## Decision: PROCEED — DB_FIX
Backup → UPDATE 19 rows → writeup PR with before/after counts.
