-- 2026-05-31 backfill UNKNOWN asset_class in at_signal_outcomes
-- Per zoocode peer DB query: 14,596 UNKNOWN rows on ejaguiar1_stocks.
-- Run once on ejaguiar1_stocks. Idempotent: each UPDATE only touches rows
-- where asset_class IN ('UNKNOWN','') so re-runs are safe.
--
-- Patterns mirror audit_trail/dashboard_generator.py::_derive_asset_class
-- (CRYPTO suffix list, FOREX 6-char pair, =X / =F futures, BOND/ETF allowlists,
-- index-futures carve-out). The dashboard-layer guard at line 8104
-- (_coerce_asset_class) handles new writes; this migration cleans the legacy
-- backlog so per-asset-class WR/PF on /audit stop showing UNKNOWN cohorts.
--
-- DO NOT execute via CI. Operator runs manually after backup.
--   mysqldump ejaguiar1_stocks at_signal_outcomes > /tmp/at_signal_outcomes_backup_20260531.sql
--   mysql ejaguiar1_stocks < tools/migrations/20260531_backfill_unknown_asset_class.sql

-- ---------------------------------------------------------------------------
-- Pre-flight: snapshot the UNKNOWN cohort size
-- ---------------------------------------------------------------------------
SELECT 'PRE_BACKFILL' AS phase, asset_class, COUNT(*) AS n
FROM at_signal_outcomes
GROUP BY asset_class
ORDER BY n DESC;

-- ---------------------------------------------------------------------------
-- 1. CRYPTO — quote-suffix patterns (Binance / Coinglass / KuCoin style)
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'CRYPTO'
WHERE asset_class IN ('UNKNOWN','')
  AND (
       symbol LIKE '%USDT'
    OR symbol LIKE '%USDC'
    OR symbol LIKE '%BUSD'
    OR symbol LIKE '%-USD'
    OR symbol LIKE '%-USDT'
    OR symbol LIKE '%/USDT'
    OR symbol LIKE '%/USDC'
    OR symbol LIKE '%PERP'
    OR symbol LIKE 'BTC%'
    OR symbol LIKE 'ETH%'
  );

-- Known bare crypto tickers (no quote suffix in DB)
UPDATE at_signal_outcomes
SET asset_class = 'CRYPTO'
WHERE asset_class IN ('UNKNOWN','')
  AND symbol IN (
    'BTC','ETH','SOL','XRP','ADA','DOGE','SHIB','AVAX','LINK','DOT',
    'MATIC','LTC','BCH','UNI','ATOM','XLM','ETC','FIL','APT','NEAR',
    'ARB','OP','SUI','INJ','TIA','SEI','PEPE','WIF','BONK','FLOKI',
    'JUP','PYTH','RNDR','FET','TAO','XMR','HBAR','ALGO','VET','ICP'
  );

-- ---------------------------------------------------------------------------
-- 2. FOREX — =X suffix or 6-char major pair
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'FOREX'
WHERE asset_class IN ('UNKNOWN','')
  AND (
       symbol LIKE '%=X'
    OR symbol REGEXP '^(EUR|USD|GBP|JPY|AUD|NZD|CAD|CHF)(EUR|USD|GBP|JPY|AUD|NZD|CAD|CHF)$'
  );

-- ---------------------------------------------------------------------------
-- 3. COMMODITY — metals + futures-suffix excluding index futures
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'COMMODITY'
WHERE asset_class IN ('UNKNOWN','')
  AND (
       symbol IN ('XAUUSD','XAGUSD','XPDUSD','XPTUSD','GOLD','SILVER')
    OR symbol REGEXP '^(XAU|XAG|XPD|XPT)'
    OR (symbol LIKE '%=F' AND symbol NOT IN ('ES=F','NQ=F','YM=F','RTY=F','VX=F'))
  );

-- ---------------------------------------------------------------------------
-- 4. FUTURES — index futures (carve-out from commodity)
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'FUTURES'
WHERE asset_class IN ('UNKNOWN','')
  AND symbol IN ('ES=F','NQ=F','YM=F','RTY=F','VX=F','DXY');

-- ---------------------------------------------------------------------------
-- 5. BOND — fixed-income ETF allowlist (mirror _AC_BOND_SYMBOLS)
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'BOND'
WHERE asset_class IN ('UNKNOWN','')
  AND symbol IN (
    'TLT','IEF','SHY','AGG','LQD','HYG','BND','TIP','MUB','EMB',
    'BIL','GOVT','BNDX','VCIT','VCSH','VGSH','VGIT','VGLT','IEI','SCHO'
  );

-- ---------------------------------------------------------------------------
-- 6. ETF — broad-market + sector SPDR allowlist (mirror _AC_ETF_SYMBOLS)
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'ETF'
WHERE asset_class IN ('UNKNOWN','')
  AND symbol IN (
    'SPY','QQQ','DIA','IWM','VTI','VOO','VEA','VWO','EFA','EEM',
    'XLF','XLK','XLE','XLY','XLP','XLV','XLI','XLB','XLU','XLRE','XLC',
    'GLD','SLV','USO','UNG','ARKK','SOXL','TQQQ','SQQQ','SPXL','SPXS'
  );

-- ---------------------------------------------------------------------------
-- 7. EQUITY — fallback for plain 1-5 char tickers that survived above passes
--    Per _derive_asset_class default. Restricted to A-Z and length<=5 so we
--    don't sweep up junk like '???' or '*EXPIRED*' rows.
-- ---------------------------------------------------------------------------
UPDATE at_signal_outcomes
SET asset_class = 'EQUITY'
WHERE asset_class IN ('UNKNOWN','')
  AND symbol REGEXP '^[A-Z]{1,5}$'
  AND symbol NOT IN (
    'BTC','ETH','SOL','XRP','ADA','DOGE','SHIB','AVAX','LINK','DOT',
    'MATIC','LTC','BCH','UNI','ATOM','XLM','ETC','FIL','APT','NEAR',
    'ARB','OP','SUI','INJ','TIA','SEI','PEPE','WIF','BONK','FLOKI',
    'JUP','PYTH','RNDR','FET','TAO','XMR','HBAR','ALGO','VET','ICP',
    'GOLD','XAU','XAG','DXY'
  );

-- ---------------------------------------------------------------------------
-- Post-flight: confirm UNKNOWN cohort shrank
-- ---------------------------------------------------------------------------
SELECT 'POST_BACKFILL' AS phase, asset_class, COUNT(*) AS n
FROM at_signal_outcomes
GROUP BY asset_class
ORDER BY n DESC;

-- Residual UNKNOWN sample (operator may need a follow-up patch for these):
SELECT 'RESIDUAL_UNKNOWN_SAMPLE' AS phase, symbol, COUNT(*) AS n
FROM at_signal_outcomes
WHERE asset_class IN ('UNKNOWN','')
GROUP BY symbol
ORDER BY n DESC
LIMIT 25;
