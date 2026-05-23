-- Calculate statistical edge per asset class using expectancy formula
-- Edge = (win_rate * avg_win) - (loss_rate * avg_loss)
-- Also includes profit factor, Sharpe ratio, and trade counts

WITH backtest_data AS (
  SELECT 
    asset_class,
    pnl_pct,
    CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END as is_win
  FROM bt_backtest_trades 
  WHERE asset_class IS NOT NULL 
    AND status IN ('CLOSED', 'TP_HIT', 'SL_HIT')
    AND pnl_pct IS NOT NULL
),

signal_data AS (
  SELECT 
    asset_class,
    pnl_pct,
    CASE WHEN outcome IN ('WIN', 'TP_HIT') THEN 1 ELSE 0 END as is_win
  FROM at_signal_outcomes 
  WHERE asset_class IS NOT NULL 
    AND outcome IN ('WIN', 'LOSS', 'TP_HIT', 'SL_HIT')
    AND pnl_pct IS NOT NULL
),

combined_data AS (
  SELECT asset_class, pnl_pct, is_win FROM backtest_data
  UNION ALL
  SELECT asset_class, pnl_pct, is_win FROM signal_data
),

asset_stats AS (
  SELECT
    asset_class,
    COUNT(*) as total_trades,
    SUM(is_win) as wins,
    COUNT(*) - SUM(is_win) as losses,
    AVG(CASE WHEN is_win = 1 THEN pnl_pct END) as avg_win,
    AVG(CASE WHEN is_win = 0 THEN pnl_pct END) as avg_loss,
    AVG(pnl_pct) as avg_pnl,
    STDDEV(pnl_pct) as std_pnl,
    MIN(pnl_pct) as worst_pnl,
    MAX(pnl_pct) as best_pnl
  FROM combined_data
  GROUP BY asset_class
)

SELECT 
  asset_class,
  total_trades,
  wins,
  losses,
  ROUND(wins / total_trades, 4) as win_rate,
  ROUND(ABS(avg_loss), 4) as avg_loss_magnitude,
  ROUND(avg_win, 4) as avg_win,
  ROUND(avg_pnl, 4) as avg_pnl,
  ROUND(std_pnl, 4) as std_pnl,
  ROUND(
    (wins / total_trades) * avg_win - 
    ((total_trades - wins) / total_trades) * ABS(avg_loss),
    4
  ) as statistical_edge,
  ROUND(
    (SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) / 
     NULLIF(SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END), 0)),
    4
  ) as profit_factor,
  ROUND(
    (avg_pnl / NULLIF(std_pnl, 0)) * SQRT(total_trades),
    4
  ) as sharpe_ratio,
  worst_pnl,
  best_pnl
FROM asset_stats
WHERE total_trades >= 30  -- Minimum sample size
ORDER BY statistical_edge DESC, total_trades DESC;
