<?php
/**
 * System Stats & Operational Health API
 * Returns comprehensive operational data for the stats dashboard:
 *   - Last refresh timestamps and results
 *   - Audit log history (all actions)
 *   - Database table sizes/row counts
 *   - Simulation progress
 *   - Data freshness indicators
 *   - GitHub Actions run history (from audit trail)
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$stats = array('ok' => true, 'generated_at' => date('Y-m-d H:i:s'));

// ─── 1. Last refresh times from report_cache ───
$stats['caches'] = array();
$r = $conn->query("SELECT cache_key, updated_at, LENGTH(cache_data) as data_size FROM report_cache ORDER BY updated_at DESC");
if ($r) { while ($row = $r->fetch_assoc()) $stats['caches'][] = $row; }

// ─── 2. Audit log — last 50 entries ───
$stats['audit_log'] = array();
$r = $conn->query("SELECT id, action_type, details, ip_address, created_at FROM audit_log ORDER BY created_at DESC LIMIT 50");
if ($r) { while ($row = $r->fetch_assoc()) $stats['audit_log'][] = $row; }

// ─── 3. Audit log summary by action type ───
$stats['audit_summary'] = array();
$r = $conn->query("SELECT action_type, COUNT(*) as total_runs, MAX(created_at) as last_run, MIN(created_at) as first_run FROM audit_log GROUP BY action_type ORDER BY last_run DESC");
if ($r) { while ($row = $r->fetch_assoc()) $stats['audit_summary'][] = $row; }

// ─── 4. Database table row counts ───
$tables = array('stocks', 'stock_picks', 'daily_prices', 'algorithms', 'portfolios',
                'backtest_results', 'backtest_trades', 'whatif_scenarios',
                'audit_log', 'market_regimes', 'report_cache', 'simulation_grid', 'simulation_meta');
$stats['tables'] = array();
foreach ($tables as $tbl) {
    $r = $conn->query("SELECT COUNT(*) as cnt FROM `$tbl`");
    if ($r) {
        $row = $r->fetch_assoc();
        $stats['tables'][] = array('table' => $tbl, 'rows' => (int)$row['cnt']);
    } else {
        $stats['tables'][] = array('table' => $tbl, 'rows' => -1, 'note' => 'table missing');
    }
}

// ─── 5. Data freshness ───
$freshness = array();

// Latest stock pick date
$r = $conn->query("SELECT MAX(pick_date) as latest FROM stock_picks");
if ($r && $row = $r->fetch_assoc()) $freshness['latest_pick_date'] = $row['latest'];

// Latest price date
$r = $conn->query("SELECT MAX(trade_date) as latest FROM daily_prices");
if ($r && $row = $r->fetch_assoc()) $freshness['latest_price_date'] = $row['latest'];

// Tickers with price data
$r = $conn->query("SELECT COUNT(DISTINCT ticker) as cnt FROM daily_prices");
if ($r && $row = $r->fetch_assoc()) $freshness['tickers_with_prices'] = (int)$row['cnt'];

// Tickers missing price data
$r = $conn->query("SELECT COUNT(DISTINCT s.ticker) as cnt FROM stocks s LEFT JOIN daily_prices dp ON s.ticker = dp.ticker WHERE dp.ticker IS NULL");
if ($r && $row = $r->fetch_assoc()) $freshness['tickers_missing_prices'] = (int)$row['cnt'];

// Algorithms active
$r = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name");
$algo_list = array();
if ($r) { while ($row = $r->fetch_assoc()) $algo_list[] = $row['algorithm_name']; }
$freshness['active_algorithms'] = $algo_list;
$freshness['algorithm_count'] = count($algo_list);

// Picks per algorithm
$r = $conn->query("SELECT algorithm_name, COUNT(*) as cnt, MIN(pick_date) as first_pick, MAX(pick_date) as last_pick FROM stock_picks WHERE entry_price > 0 GROUP BY algorithm_name ORDER BY algorithm_name");
$algo_picks = array();
if ($r) { while ($row = $r->fetch_assoc()) $algo_picks[] = $row; }
$freshness['picks_per_algorithm'] = $algo_picks;

// Price records per ticker (top 10 + bottom 10)
$r = $conn->query("SELECT ticker, COUNT(*) as cnt, MIN(trade_date) as oldest, MAX(trade_date) as newest FROM daily_prices GROUP BY ticker ORDER BY cnt DESC");
$ticker_coverage = array();
if ($r) { while ($row = $r->fetch_assoc()) $ticker_coverage[] = $row; }
$freshness['ticker_coverage'] = $ticker_coverage;

$stats['freshness'] = $freshness;

// ─── 6. Simulation status ───
$sim = array('status' => 'not_started', 'rows' => 0, 'total_planned' => 0, 'progress_pct' => 0);
$r = $conn->query("SELECT meta_key, meta_value FROM simulation_meta");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $sim[$row['meta_key']] = $row['meta_value'];
    }
}
$r = $conn->query("SELECT COUNT(*) as cnt FROM simulation_grid");
if ($r && $row = $r->fetch_assoc()) $sim['rows'] = (int)$row['cnt'];

if ((int)$sim['total_combos'] > 0) {
    $sim['progress_pct'] = round($sim['rows'] / (int)$sim['total_combos'] * 100, 1);
}

// Simulation direction breakdown
$r = $conn->query("SELECT direction, COUNT(*) as cnt,
                    SUM(CASE WHEN total_return_pct > 0 THEN 1 ELSE 0 END) as profitable,
                    AVG(total_return_pct) as avg_ret, MAX(total_return_pct) as best_ret
                   FROM simulation_grid WHERE total_trades > 0 GROUP BY direction");
$sim['by_direction'] = array();
if ($r) { while ($row = $r->fetch_assoc()) $sim['by_direction'][$row['direction']] = $row; }

$stats['simulation'] = $sim;

// ─── 7. Daily refresh history (last 14 days from audit_log) ───
$stats['refresh_history'] = array();
$r = $conn->query("SELECT id, details, ip_address, created_at FROM audit_log WHERE action_type = 'daily_refresh' ORDER BY created_at DESC LIMIT 14");
if ($r) { while ($row = $r->fetch_assoc()) $stats['refresh_history'][] = $row; }

// ─── 8. Backtest history ───
$stats['backtest_history'] = array();
$r = $conn->query("SELECT id, run_name, algorithm_filter, strategy_type, total_return_pct, win_rate, total_trades, created_at FROM backtest_results ORDER BY created_at DESC LIMIT 20");
if ($r) { while ($row = $r->fetch_assoc()) $stats['backtest_history'][] = $row; }

// ─── 9. System health indicators ───
$health = array();
// Check if daily refresh ran today
$today = date('Y-m-d');
$r = $conn->query("SELECT COUNT(*) as cnt FROM audit_log WHERE action_type='daily_refresh' AND created_at >= '$today 00:00:00'");
$health['refreshed_today'] = ($r && $row = $r->fetch_assoc()) ? (int)$row['cnt'] > 0 : false;

// Check if data is stale (last price > 3 days old on weekday)
$r = $conn->query("SELECT MAX(trade_date) as latest FROM daily_prices");
$latest_price = '';
if ($r && $row = $r->fetch_assoc()) $latest_price = $row['latest'];
$health['latest_price_date'] = $latest_price;
$days_since = ($latest_price !== '') ? (int)((time() - strtotime($latest_price)) / 86400) : 999;
$health['price_days_stale'] = $days_since;
$health['price_status'] = ($days_since <= 3) ? 'fresh' : (($days_since <= 7) ? 'stale' : 'very_stale');

// Report cache age
$r = $conn->query("SELECT updated_at FROM report_cache WHERE cache_key='daily_summary'");
$cache_age = 999;
if ($r && $row = $r->fetch_assoc()) {
    $cache_age = (int)((time() - strtotime($row['updated_at'])) / 3600);
}
$health['report_cache_hours_old'] = $cache_age;
$health['report_status'] = ($cache_age <= 24) ? 'fresh' : (($cache_age <= 72) ? 'stale' : 'very_stale');

$stats['health'] = $health;

echo json_encode($stats);
$conn->close();
?>
