<?php
/**
 * DayTrades Miracle_CURSOR v3 — Daily Scan Orchestrator
 * Runs the full pipeline: resolve old picks, run scanner, analyze, adjust.
 * Called by GitHub Actions cron or manually.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../daily_scan3.php?key=miracle2026
 */
$auth_key = isset($_GET['key']) ? $_GET['key'] : '';
if ($auth_key !== 'miracle2026') {
    header('HTTP/1.0 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

header('Content-Type: application/json');

$base_url = 'https://findtorontoevents.ca/findstocks_global/api';
$log = array();
$start = microtime(true);

// Helper to call an API endpoint
function miracle3_api_call($url) {
    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: MiracleCursor/3.0\r\n",
            'timeout' => 120
        )
    ));
    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return null;
    return json_decode($json, true);
}

// --- Step 1: Ensure schema exists ---
$schema = miracle3_api_call($base_url . '/setup_schema3.php');
$log[] = 'Schema: ' . ($schema && isset($schema['ok']) && $schema['ok'] ? 'OK' : 'FAILED');

// --- Step 2: Resolve pending picks from previous days ---
$resolve = miracle3_api_call($base_url . '/resolve3.php');
if ($resolve && isset($resolve['ok']) && $resolve['ok']) {
    $w = isset($resolve['winners']) ? $resolve['winners'] : 0;
    $l = isset($resolve['losers']) ? $resolve['losers'] : 0;
    $e = isset($resolve['expired']) ? $resolve['expired'] : 0;
    $p = isset($resolve['still_pending']) ? $resolve['still_pending'] : (isset($resolve['pending']) ? $resolve['pending'] : 0);
    $log[] = 'Resolve: W:' . $w . ' L:' . $l . ' E:' . $e . ' pending:' . $p;
} else {
    $log[] = 'Resolve: FAILED';
}

// --- Step 3: Run learning/adjust (auto-tune strategy parameters) ---
$learn = miracle3_api_call($base_url . '/learning3.php?action=adjust');
if ($learn) {
    $adj_count = isset($learn['adjustments']) ? count($learn['adjustments']) : 0;
    $log[] = 'Learning: ' . $adj_count . ' strategy adjustments made';
} else {
    $log[] = 'Learning: FAILED';
}

// --- Step 4: Run the scanner in batches ---
$total_scanned = 0;
$total_signals = 0;
$total_saved = 0;
$scan_errors = 0;

// Batch scan — 15 tickers at a time
for ($off = 0; $off < 200; $off += 15) {
    $scan = miracle3_api_call($base_url . '/scanner3.php?batch=15&offset=' . $off);
    if ($scan && isset($scan['ok']) && $scan['ok']) {
        $scanned = isset($scan['scanned']) ? (int)$scan['scanned'] : 0;
        $signals = isset($scan['total_signals']) ? (int)$scan['total_signals'] : 0;
        $saved = isset($scan['saved']) ? (int)$scan['saved'] : 0;
        $total_scanned += $scanned;
        $total_signals += $signals;
        $total_saved += $saved;
        if ($scanned === 0) break; // no more tickers
    } else {
        $scan_errors++;
        if ($scan_errors >= 3) break; // too many failures
    }
    // Small delay to avoid rate limiting
    usleep(500000);
}
$log[] = 'Scanner: scanned=' . $total_scanned . ' signals=' . $total_signals . ' saved=' . $total_saved;

// --- Step 5: Generate dashboard stats ---
$dash = miracle3_api_call($base_url . '/dashboard3.php?action=stats');
if ($dash && isset($dash['ok']) && $dash['ok']) {
    $s = isset($dash['stats']) ? $dash['stats'] : array();
    $tp = isset($s['total_picks']) ? $s['total_picks'] : '?';
    $td = isset($s['today_picks']) ? $s['today_picks'] : '?';
    $wr = isset($s['win_rate']) ? $s['win_rate'] : '?';
    $pf = isset($s['profit_factor']) ? $s['profit_factor'] : '?';
    $log[] = 'Dashboard: total=' . $tp . ' today=' . $td . ' win_rate=' . $wr . '% PF=' . $pf;
} else {
    $log[] = 'Dashboard: FAILED';
}

// --- Step 6: Save daily results snapshot ---
require_once dirname(__FILE__) . '/db_config3.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if (!$conn->connect_error) {
    $conn->set_charset('utf8');
    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');
    $elapsed = round(microtime(true) - $start, 2);

    // Save overall results for today
    if ($dash && isset($dash['stats'])) {
        $s = $dash['stats'];
        $tp_val = isset($s['total_picks']) ? (int)$s['total_picks'] : 0;
        $w_val = isset($s['winners']) ? (int)$s['winners'] : 0;
        $l_val = isset($s['losers']) ? (int)$s['losers'] : 0;
        $p_val = isset($s['pending']) ? (int)$s['pending'] : 0;
        $wr_val = isset($s['win_rate']) ? floatval($s['win_rate']) : 0;
        $ag_val = isset($s['avg_gain_pct']) ? floatval($s['avg_gain_pct']) : 0;
        $al_val = isset($s['avg_loss_pct']) ? floatval($s['avg_loss_pct']) : 0;
        $pnl_val = isset($s['total_pnl_pct']) ? floatval($s['total_pnl_pct']) : 0;
        $pf_val = isset($s['profit_factor']) ? floatval($s['profit_factor']) : 0;
        $ex_val = isset($s['expectancy']) ? floatval($s['expectancy']) : 0;

        $conn->query("INSERT INTO miracle_results3 (strategy_name, period, calc_date, total_picks, winners, losers, pending_count, win_rate, avg_gain_pct, avg_loss_pct, total_pnl, profit_factor, expectancy, created_at)
                       VALUES ('_overall','daily','" . $conn->real_escape_string($today) . "',$tp_val,$w_val,$l_val,$p_val,$wr_val,$ag_val,$al_val,$pnl_val,$pf_val,$ex_val,'" . $conn->real_escape_string($now) . "')");
    }

    // Audit log
    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'cron';
    $log_text = $conn->real_escape_string(implode(' | ', $log));
    $conn->query("INSERT INTO miracle_audit3 (action_type, details, ip_address, created_at) VALUES ('daily_scan', 'Elapsed: {$elapsed}s | $log_text', '$ip', '" . $conn->real_escape_string($now) . "')");

    $conn->close();
}

$elapsed = round(microtime(true) - $start, 2);

echo json_encode(array(
    'ok'      => true,
    'elapsed' => $elapsed . 's',
    'scanned' => $total_scanned,
    'signals' => $total_signals,
    'saved'   => $total_saved,
    'steps'   => $log
));
?>
