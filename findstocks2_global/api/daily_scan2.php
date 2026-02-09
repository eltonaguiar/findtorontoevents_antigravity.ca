<?php
/**
 * DayTrades Miracle Claude — Daily Scan Orchestrator
 * Runs the full pipeline: resolve old picks, run scanner, analyze, adjust.
 * Called by GitHub Actions cron or manually.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../daily_scan2.php?key=miracle2026
 */
$auth_key = isset($_GET['key']) ? $_GET['key'] : '';
if ($auth_key !== 'miracle2026') {
    header('HTTP/1.0 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

header('Content-Type: application/json');

$base_url = 'https://findtorontoevents.ca/findstocks2_global/api';
$log = array();
$start = microtime(true);

// Helper to call an API endpoint
function miracle_api_call($url) {
    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: MiracleClaude/1.0\r\n",
            'timeout' => 120
        )
    ));
    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return null;
    return json_decode($json, true);
}

// ─── Step 1: Ensure schema exists ───
$schema = miracle_api_call($base_url . '/setup_schema2.php');
$log[] = 'Schema: ' . ($schema && $schema['ok'] ? 'OK' : 'FAILED');

// ─── Step 2: Resolve pending picks from previous days ───
$resolve = miracle_api_call($base_url . '/resolve_picks2.php?max_hold=5');
if ($resolve) {
    $log[] = 'Resolve: W:' . $resolve['winners'] . ' L:' . $resolve['losers'] . ' E:' . $resolve['expired'] . ' pending:' . $resolve['still_pending'];
} else {
    $log[] = 'Resolve: FAILED';
}

// ─── Step 3: Run learning/adjust (auto-tune strategy parameters) ───
$learn = miracle_api_call($base_url . '/learning2.php?action=adjust');
if ($learn) {
    $adj_count = isset($learn['adjustments']) ? count($learn['adjustments']) : 0;
    $log[] = 'Learning: ' . $adj_count . ' strategy adjustments made';
} else {
    $log[] = 'Learning: FAILED';
}

// ─── Step 4: Run the scanner (main event!) ───
$scan = miracle_api_call($base_url . '/scanner2.php?top=25');
if ($scan) {
    $log[] = 'Scanner: scanned=' . $scan['scanned'] . ' signals=' . $scan['total_signals'] . ' saved=' . $scan['saved'] . ' time=' . $scan['scan_time'];
} else {
    $log[] = 'Scanner: FAILED';
}

// ─── Step 5: Generate dashboard stats and cache results ───
$dash = miracle_api_call($base_url . '/dashboard2.php?action=summary');
if ($dash && isset($dash['summary'])) {
    $s = $dash['summary'];
    $log[] = 'Dashboard: total=' . $s['total_picks'] . ' today=' . $s['today_picks'] . ' win_rate=' . $s['win_rate'] . '% PF=' . $s['profit_factor'];
} else {
    $log[] = 'Dashboard: FAILED';
}

// ─── Step 6: Save daily results snapshot ───
require_once dirname(__FILE__) . '/db_config2.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if (!$conn->connect_error) {
    $conn->set_charset('utf8');
    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');
    $elapsed = round(microtime(true) - $start, 2);

    // Save per-strategy results for today
    if ($dash && isset($dash['summary'])) {
        $s = $dash['summary'];
        $conn->query("INSERT INTO miracle_results2 (strategy_name, period, calc_date, total_picks, winners, losers, pending_count, win_rate, avg_gain_pct, avg_loss_pct, total_pnl, profit_factor, expectancy, created_at)
                       VALUES ('_overall','daily','$today',{$s['total_picks']},{$s['winners']},{$s['losers']},{$s['pending']},{$s['win_rate']},{$s['avg_gain_pct']},{$s['avg_loss_pct']},{$s['total_pnl_pct']},{$s['profit_factor']},{$s['expectancy']},'$now')");
    }

    // Audit log
    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'cron';
    $log_text = $conn->real_escape_string(implode(' | ', $log));
    $conn->query("INSERT INTO miracle_audit2 (action_type, details, ip_address, created_at) VALUES ('daily_scan', 'Elapsed: {$elapsed}s | $log_text', '$ip', '$now')");

    $conn->close();
}

$elapsed = round(microtime(true) - $start, 2);

echo json_encode(array(
    'ok'      => true,
    'elapsed' => $elapsed . 's',
    'steps'   => $log
));
?>
