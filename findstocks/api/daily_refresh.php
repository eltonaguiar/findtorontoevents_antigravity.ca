<?php
/**
 * Daily Refresh — single endpoint that runs all maintenance tasks.
 * Called by GitHub Actions cron or manually.
 * PHP 5.2 compatible.
 *
 * Tasks: import new picks, fetch latest prices, run standard backtests, generate summary cache.
 *
 * Usage: GET .../daily_refresh.php?key=stocksrefresh2026
 */
$auth_key = isset($_GET['key']) ? $_GET['key'] : '';
if ($auth_key !== 'stocksrefresh2026') {
    header('HTTP/1.1 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

require_once dirname(__FILE__) . '/db_config.php';

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

$log = array();
$start = microtime(true);

// ─── 1. Import latest picks ───
$import_url = 'https://findtorontoevents.ca/findstocks/api/import_picks.php';
$import_json = @file_get_contents($import_url);
$import_data = ($import_json !== false) ? json_decode($import_json, true) : null;
$log[] = 'Import: ' . ($import_data ? ('imported=' . $import_data['imported'] . ' skipped=' . $import_data['skipped']) : 'failed');

// ─── 2. Fetch latest prices (up to 3 batches of 10) ───
$total_fetched = 0;
for ($batch = 0; $batch < 3; $batch++) {
    $fetch_url = 'https://findtorontoevents.ca/findstocks/api/fetch_prices.php?range=1y';
    $fetch_json = @file_get_contents($fetch_url);
    $fetch_data = ($fetch_json !== false) ? json_decode($fetch_json, true) : null;
    if ($fetch_data && isset($fetch_data['fetched'])) {
        $total_fetched += (int)$fetch_data['fetched'];
        if (!isset($fetch_data['note'])) break; // No more to fetch
    } else {
        break;
    }
    sleep(1);
}
$log[] = 'Prices: fetched ' . $total_fetched . ' tickers';

// ─── 3. Run standard backtests and cache results ───
$scenarios = array(
    array('name' => 'daytrader_eod',      'tp' => 5,   'sl' => 3,  'hold' => 1,   'comm' => 10),
    array('name' => 'daytrader_2day',     'tp' => 10,  'sl' => 5,  'hold' => 2,   'comm' => 10),
    array('name' => 'weekly_10',          'tp' => 10,  'sl' => 5,  'hold' => 7,   'comm' => 10),
    array('name' => 'weekly_20',          'tp' => 20,  'sl' => 8,  'hold' => 7,   'comm' => 10),
    array('name' => 'swing_conservative', 'tp' => 10,  'sl' => 5,  'hold' => 20,  'comm' => 10),
    array('name' => 'momentum_ride',      'tp' => 50,  'sl' => 10, 'hold' => 30,  'comm' => 10),
    array('name' => 'buy_hold_3m',        'tp' => 999, 'sl' => 999,'hold' => 60,  'comm' => 10),
    array('name' => 'pure_hold_7d_nocomm','tp' => 999, 'sl' => 999,'hold' => 7,   'comm' => 0),
    array('name' => 'daytrader_2d_nocomm','tp' => 10,  'sl' => 5,  'hold' => 2,   'comm' => 0)
);

// Build summary JSON
$summary = array(
    'generated_at' => date('Y-m-d H:i:s'),
    'scenarios' => array(),
    'per_algorithm' => array(),
    'top_trades' => array(),
    'worst_trades' => array(),
    'best_possible' => array(),
    'recommendations' => array(),
    'stats' => array()
);

// Run scenarios
foreach ($scenarios as $sc) {
    $url = 'https://findtorontoevents.ca/findstocks/api/backtest.php'
         . '?take_profit=' . $sc['tp']
         . '&stop_loss=' . $sc['sl']
         . '&max_hold_days=' . $sc['hold']
         . '&commission=' . $sc['comm']
         . '&slippage=0.5';
    $json = @file_get_contents($url);
    $data = ($json !== false) ? json_decode($json, true) : null;
    if ($data && $data['ok']) {
        $summary['scenarios'][] = array(
            'name' => $sc['name'],
            'params' => $sc,
            'summary' => $data['summary']
        );
    }
}
$log[] = 'Backtests: ran ' . count($summary['scenarios']) . ' scenarios';

// Per-algorithm analysis
$algo_names = array();
$res = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name");
if ($res) { while ($row = $res->fetch_assoc()) $algo_names[] = $row['algorithm_name']; }

foreach ($algo_names as $algo) {
    $encoded = urlencode($algo);
    // 7-day hold with commission
    $url1 = 'https://findtorontoevents.ca/findstocks/api/backtest.php?algorithms=' . $encoded . '&take_profit=999&stop_loss=999&max_hold_days=7&commission=10&slippage=0.5';
    $d1 = json_decode(@file_get_contents($url1), true);
    // 7-day hold zero commission
    $url2 = 'https://findtorontoevents.ca/findstocks/api/backtest.php?algorithms=' . $encoded . '&take_profit=999&stop_loss=999&max_hold_days=7&commission=0&slippage=0';
    $d2 = json_decode(@file_get_contents($url2), true);
    // 2-day daytrader zero commission
    $url3 = 'https://findtorontoevents.ca/findstocks/api/backtest.php?algorithms=' . $encoded . '&take_profit=10&stop_loss=5&max_hold_days=2&commission=0&slippage=0';
    $d3 = json_decode(@file_get_contents($url3), true);

    $entry = array('algorithm' => $algo, 'picks' => 0);
    if ($d1 && $d1['ok']) {
        $entry['hold_7d_comm']    = $d1['summary'];
        $entry['picks']           = $d1['summary']['total_trades'];
        $entry['trades']          = isset($d1['trades']) ? $d1['trades'] : array();
    }
    if ($d2 && $d2['ok']) $entry['hold_7d_nocomm'] = $d2['summary'];
    if ($d3 && $d3['ok']) $entry['daytrader_nocomm'] = $d3['summary'];

    $summary['per_algorithm'][] = $entry;
}
$log[] = 'Algo analysis: ' . count($summary['per_algorithm']) . ' algorithms';

// Top/worst trades (use analyze endpoint)
$top_json = @file_get_contents('https://findtorontoevents.ca/findstocks/api/analyze.php?type=top_trades');
$top_data = ($top_json !== false) ? json_decode($top_json, true) : null;
if ($top_data && $top_data['ok']) {
    $summary['top_trades'] = isset($top_data['top_winners']) ? array_slice($top_data['top_winners'], 0, 5) : array();
    $summary['worst_trades'] = isset($top_data['top_losers']) ? array_slice($top_data['top_losers'], 0, 5) : array();
    $summary['best_possible'] = isset($top_data['best_possible_trades']) ? array_slice($top_data['best_possible_trades'], 0, 10) : array();
}

// Learning recommendations
$rec_json = @file_get_contents('https://findtorontoevents.ca/findstocks/api/analyze.php?type=learning_recs');
$rec_data = ($rec_json !== false) ? json_decode($rec_json, true) : null;
if ($rec_data && $rec_data['ok']) {
    $summary['recommendations'] = isset($rec_data['recommendations']) ? $rec_data['recommendations'] : array();
}

// ─── 3b. Short-selling backtests ───
$short_scenarios = array(
    array('name' => 'short_daytrader_2d',     'tp' => 5,   'sl' => 3,  'hold' => 2,  'comm' => 10),
    array('name' => 'short_weekly',           'tp' => 10,  'sl' => 5,  'hold' => 7,  'comm' => 10),
    array('name' => 'short_swing',            'tp' => 15,  'sl' => 8,  'hold' => 14, 'comm' => 10),
    array('name' => 'short_aggressive',       'tp' => 20,  'sl' => 10, 'hold' => 30, 'comm' => 10),
    array('name' => 'short_weekly_nocomm',    'tp' => 10,  'sl' => 5,  'hold' => 7,  'comm' => 0),
    array('name' => 'short_hold_7d_nocomm',   'tp' => 999, 'sl' => 999,'hold' => 7,  'comm' => 0)
);
$summary['short_scenarios'] = array();
foreach ($short_scenarios as $sc) {
    $url = 'https://findtorontoevents.ca/findstocks/api/short_backtest.php'
         . '?take_profit=' . $sc['tp']
         . '&stop_loss=' . $sc['sl']
         . '&max_hold_days=' . $sc['hold']
         . '&commission=' . $sc['comm']
         . '&slippage=0.5';
    $json = @file_get_contents($url);
    $data = ($json !== false) ? json_decode($json, true) : null;
    if ($data && $data['ok']) {
        $summary['short_scenarios'][] = array(
            'name' => $sc['name'],
            'params' => $sc,
            'summary' => $data['summary'],
            'regime_breakdown' => isset($data['regime_breakdown']) ? $data['regime_breakdown'] : array()
        );
    }
}
$log[] = 'Short backtests: ran ' . count($summary['short_scenarios']) . ' scenarios';

// ─── 3c. Per-algorithm short analysis ───
$summary['per_algorithm_short'] = array();
foreach ($algo_names as $algo) {
    $encoded = urlencode($algo);
    $url_s1 = 'https://findtorontoevents.ca/findstocks/api/short_backtest.php?algorithms=' . $encoded . '&take_profit=10&stop_loss=5&max_hold_days=7&commission=0&slippage=0.5';
    $ds1 = json_decode(@file_get_contents($url_s1), true);
    $url_s2 = 'https://findtorontoevents.ca/findstocks/api/short_backtest.php?algorithms=' . $encoded . '&take_profit=999&stop_loss=999&max_hold_days=7&commission=0&slippage=0';
    $ds2 = json_decode(@file_get_contents($url_s2), true);

    $sentry = array('algorithm' => $algo);
    if ($ds1 && $ds1['ok']) {
        $sentry['short_7d_stops'] = $ds1['summary'];
        $sentry['regime'] = isset($ds1['regime_breakdown']) ? $ds1['regime_breakdown'] : array();
    }
    if ($ds2 && $ds2['ok']) $sentry['short_7d_nostops'] = $ds2['summary'];
    $summary['per_algorithm_short'][] = $sentry;
}
$log[] = 'Short algo analysis: ' . count($summary['per_algorithm_short']) . ' algorithms';

// ─── 3d. Exhaustive simulation summary (if available) ───
$summary['exhaustive'] = array();
$sim_r = $conn->query("SELECT meta_value FROM simulation_meta WHERE meta_key='status'");
if ($sim_r && $srow = $sim_r->fetch_assoc()) {
    if ($srow['meta_value'] === 'complete') {
        // Pull summary from simulation_grid
        $esim = array('status' => 'complete', 'long' => array(), 'short' => array(), 'best_overall' => array());

        // Best LONG combos
        $r = $conn->query("SELECT * FROM simulation_grid WHERE direction='LONG' AND total_trades>0 ORDER BY total_return_pct DESC LIMIT 10");
        if ($r) { while ($row = $r->fetch_assoc()) $esim['long'][] = $row; }

        // Best SHORT combos
        $r = $conn->query("SELECT * FROM simulation_grid WHERE direction='SHORT' AND total_trades>0 ORDER BY total_return_pct DESC LIMIT 10");
        if ($r) { while ($row = $r->fetch_assoc()) $esim['short'][] = $row; }

        // Overall stats
        $r = $conn->query("SELECT direction, COUNT(*) as total_combos,
                            SUM(CASE WHEN total_return_pct > 0 THEN 1 ELSE 0 END) as profitable,
                            AVG(total_return_pct) as avg_ret, MAX(total_return_pct) as best_ret,
                            MIN(total_return_pct) as worst_ret
                           FROM simulation_grid WHERE total_trades>0 GROUP BY direction");
        if ($r) { while ($row = $r->fetch_assoc()) $esim['stats_' . strtolower($row['direction'])] = $row; }

        $summary['exhaustive'] = $esim;
        $log[] = 'Exhaustive sim: loaded cached results';
    } else {
        $summary['exhaustive'] = array('status' => $srow['meta_value']);
        $log[] = 'Exhaustive sim: ' . $srow['meta_value'];
    }
}

// DB stats
$stats = array();
$r = $conn->query("SELECT COUNT(*) as c FROM stocks"); $stats['total_stocks'] = ($r) ? (int)$r->fetch_assoc() : 0;
if (is_array($stats['total_stocks'])) $stats['total_stocks'] = $stats['total_stocks']['c'];
$r = $conn->query("SELECT COUNT(*) as c FROM stock_picks"); $row = ($r) ? $r->fetch_assoc() : array('c' => 0); $stats['total_picks'] = (int)$row['c'];
$r = $conn->query("SELECT COUNT(*) as c FROM daily_prices"); $row = ($r) ? $r->fetch_assoc() : array('c' => 0); $stats['total_price_records'] = (int)$row['c'];
$r = $conn->query("SELECT MIN(pick_date) as mn, MAX(pick_date) as mx FROM stock_picks");
if ($r) { $row = $r->fetch_assoc(); $stats['pick_range'] = $row['mn'] . ' to ' . $row['mx']; }
$r = $conn->query("SELECT MIN(trade_date) as mn, MAX(trade_date) as mx FROM daily_prices");
if ($r) { $row = $r->fetch_assoc(); $stats['price_range'] = $row['mn'] . ' to ' . $row['mx']; }
$summary['stats'] = $stats;

// ─── 4. Save summary as cached JSON ───
// Store in the database for the report page to read
$now = date('Y-m-d H:i:s');
$safe_json = $conn->real_escape_string(json_encode($summary));

// Use a simple cache table
$conn->query("CREATE TABLE IF NOT EXISTS report_cache (
    cache_key VARCHAR(50) PRIMARY KEY,
    cache_data LONGTEXT,
    updated_at DATETIME
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("REPLACE INTO report_cache (cache_key, cache_data, updated_at) VALUES ('daily_summary', '$safe_json', '$now')");

$elapsed = round(microtime(true) - $start, 2);
$log[] = 'Total time: ' . $elapsed . 's';

// Audit
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'cron';
$detail = $conn->real_escape_string(implode('; ', $log));
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('daily_refresh', '$detail', '$ip', '$now')");

header('Content-Type: application/json');
echo json_encode(array('ok' => true, 'log' => $log, 'elapsed_seconds' => $elapsed));
$conn->close();
?>
