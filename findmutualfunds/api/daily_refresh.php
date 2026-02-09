<?php
/**
 * Daily refresh orchestrator for Mutual Fund Portfolio Analysis.
 * Calls all sub-endpoints in sequence and caches the summary.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../daily_refresh.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$now = date('Y-m-d H:i:s');
$start_time = microtime(true);
$log = array();
$base = 'https://findtorontoevents.ca/findmutualfunds/api/';

function _mf_call($url, &$log_arr) {
    $ctx = stream_context_create(array('http' => array('timeout' => 60, 'header' => "User-Agent: MF-DailyRefresh/1.0\r\n")));
    $raw = @file_get_contents($url, false, $ctx);
    if ($raw === false) {
        $log_arr[] = 'FAIL: ' . $url;
        return null;
    }
    $data = json_decode($raw, true);
    $log_arr[] = 'OK: ' . $url;
    return $data;
}

// ─── 1. Fetch NAV data (multiple batches) ───
$total_fetched = 0;
for ($batch = 0; $batch < 5; $batch++) {
    $nav_data = _mf_call($base . 'fetch_nav.php?range=1y&batch=10', $log);
    if ($nav_data && isset($nav_data['fetched'])) {
        $total_fetched += (int)$nav_data['fetched'];
        if ((int)$nav_data['fetched'] === 0) break;
    } else {
        break;
    }
}
$log[] = 'Total NAV fetched: ' . $total_fetched . ' tickers';

// ─── 2. Import fund selections ───
$import_data = _mf_call($base . 'import_funds.php', $log);

// ─── 3. Run analysis ───
$analyze_data = _mf_call($base . 'analyze.php', $log);

// ─── 4. Build summary ───
$summary = array(
    'updated_at' => $now,
    'nav_fetched' => $total_fetched,
    'import' => $import_data,
    'analysis' => $analyze_data
);

// ─── Get DB stats ───
$stats = array();
$tables = array('mf_funds', 'mf_nav_history', 'mf_strategies', 'mf_selections', 'mf_portfolios', 'mf_backtest_results', 'mf_backtest_trades', 'mf_audit_log');
foreach ($tables as $tbl) {
    $r = $conn->query("SELECT COUNT(*) as cnt FROM $tbl");
    if ($r && $row = $r->fetch_assoc()) $stats[$tbl] = (int)$row['cnt'];
}

// Top performing funds
$top_funds = array();
$r = $conn->query("SELECT ms.ticker, mf.fund_name, ms.strategy_name, ms.nav_at_select,
                    (SELECT adj_nav FROM mf_nav_history WHERE ticker=ms.ticker ORDER BY nav_date DESC LIMIT 1) as latest_nav,
                    ms.expense_ratio
                    FROM mf_selections ms
                    LEFT JOIN mf_funds mf ON ms.ticker = mf.ticker
                    WHERE ms.nav_at_select > 0
                    ORDER BY ms.select_date DESC LIMIT 20");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $entry = (float)$row['nav_at_select'];
        $latest = (float)$row['latest_nav'];
        $ret = ($entry > 0) ? round(($latest - $entry) / $entry * 100, 2) : 0;
        $row['return_pct'] = $ret;
        $top_funds[] = $row;
    }
}

// Sort by return
usort($top_funds, '_mf_sort_return');
function _mf_sort_return($a, $b) {
    if ((float)$a['return_pct'] == (float)$b['return_pct']) return 0;
    return ((float)$a['return_pct'] > (float)$b['return_pct']) ? -1 : 1;
}

$summary['top_funds'] = array_slice($top_funds, 0, 10);
$summary['worst_funds'] = array_slice(array_reverse($top_funds), 0, 5);
$summary['db_stats'] = $stats;

// ─── Findings & Recommendations ───
$findings = array();
if ($analyze_data && isset($analyze_data['per_strategy'])) {
    foreach ($analyze_data['per_strategy'] as $ps) {
        if ($ps['win_rate'] >= 60) {
            $findings[] = $ps['strategy'] . ' shows strong performance with ' . $ps['win_rate'] . '% win rate.';
        }
        if ($ps['win_rate'] < 40 && $ps['total_trades'] > 3) {
            $findings[] = $ps['strategy'] . ' is underperforming (' . $ps['win_rate'] . '% win rate). Consider adjusting parameters.';
        }
    }
}
if (count($top_funds) > 0 && (float)$top_funds[0]['return_pct'] > 10) {
    $findings[] = 'Top fund ' . $top_funds[0]['ticker'] . ' (' . $top_funds[0]['fund_name'] . ') returned ' . $top_funds[0]['return_pct'] . '%.';
}
$summary['findings'] = $findings;

// ─── Cache the summary ───
$safe_data = $conn->real_escape_string(json_encode($summary));
$conn->query("REPLACE INTO mf_report_cache (cache_key, cache_data, updated_at) VALUES ('daily_summary', '$safe_data', '$now')");

// ─── Save operational stats snapshot ───
$elapsed = round(microtime(true) - $start_time, 2);
$ops = array(
    'timestamp' => $now,
    'elapsed_seconds' => $elapsed,
    'steps' => array(
        array('name' => 'Fetch NAV', 'status' => ($total_fetched > 0 ? 'ok' : 'no_new'), 'tickers_fetched' => $total_fetched),
        array('name' => 'Import Funds', 'status' => ($import_data ? 'ok' : 'failed'), 'imported' => ($import_data ? (int)$import_data['imported'] : 0)),
        array('name' => 'Analysis', 'status' => ($analyze_data ? 'ok' : 'failed'), 'scenarios' => ($analyze_data ? count($analyze_data['scenarios']) : 0))
    ),
    'db_stats' => $stats,
    'log' => $log
);
$safe_ops = $conn->real_escape_string(json_encode($ops));
$conn->query("REPLACE INTO mf_report_cache (cache_key, cache_data, updated_at) VALUES ('stats_snapshot', '$safe_ops', '$now')");

// Audit
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf_audit_log (action_type, details, ip_address, created_at) VALUES ('daily_refresh', 'Completed in {$elapsed}s. NAV=$total_fetched', '$ip', '$now')");

$summary['log'] = $log;
$summary['elapsed_seconds'] = $elapsed;
echo json_encode(array('ok' => true, 'summary' => $summary));
$conn->close();
?>
