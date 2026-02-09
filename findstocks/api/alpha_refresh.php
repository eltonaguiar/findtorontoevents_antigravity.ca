<?php
/**
 * Alpha Suite - Daily Refresh Orchestrator
 * Coordinates the full refresh pipeline: setup -> fetch -> compute -> picks.
 * Designed to be called by GitHub Actions in steps.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   ?key=alpharefresh2026&step=setup           - Create tables + seed universe
 *   ?key=alpharefresh2026&step=fetch_macro      - Fetch macro data
 *   ?key=alpharefresh2026&step=fetch_fundamentals - Fetch fundamentals (v7 batch)
 *   ?key=alpharefresh2026&step=fetch_earnings&batch=N - Fetch earnings batch N
 *   ?key=alpharefresh2026&step=fetch_prices&batch=N   - Fetch prices batch N
 *   ?key=alpharefresh2026&step=compute          - Compute factors + generate picks
 *   ?key=alpharefresh2026&step=status           - Check refresh status
 */
require_once dirname(__FILE__) . '/db_connect.php';

$key  = isset($_GET['key']) ? $_GET['key'] : '';
$step = isset($_GET['step']) ? $_GET['step'] : 'status';
$batch = isset($_GET['batch']) ? (int)$_GET['batch'] : 1;

if ($key !== 'alpharefresh2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

$result = array('ok' => true, 'step' => $step, 'data' => array(), 'errors' => array());
$now = date('Y-m-d H:i:s');

// Log start
$safe_step = $conn->real_escape_string($step);
$conn->query("INSERT INTO alpha_refresh_log (refresh_date, step, status, details)
              VALUES ('$now', '$safe_step', 'started', 'Step initiated')
              ON DUPLICATE KEY UPDATE status='started'");

// Update status
if ($step === 'setup' || $step === 'fetch_macro') {
    $conn->query("UPDATE alpha_status SET last_refresh_start='$now', last_refresh_status='running' WHERE id=1");
}

$start_time = microtime(true);

/* ────────────────────────────────── */
if ($step === 'setup') {
    // Call alpha_setup.php via include
    ob_start();
    // We need a fresh connection for the include (db_connect already loaded)
    $base_url = 'https://findtorontoevents.ca/findstocks/api/alpha_setup.php';
    $setup_result = @file_get_contents($base_url);
    ob_end_clean();

    if ($setup_result !== false) {
        $setup_data = json_decode($setup_result, true);
        $result['data']['setup'] = $setup_data;
    } else {
        // Fallback: include directly
        ob_start();
        $old_conn = $conn;
        include dirname(__FILE__) . '/alpha_setup.php';
        $setup_output = ob_get_clean();
        $conn = $old_conn;
        $result['data']['setup'] = json_decode($setup_output, true);
    }
}

/* ────────────────────────────────── */
if ($step === 'fetch_macro') {
    $url = 'https://findtorontoevents.ca/findstocks/api/alpha_fetch.php?key=alpharefresh2026&action=macro';
    $resp = @file_get_contents($url);
    if ($resp !== false) {
        $result['data']['macro'] = json_decode($resp, true);
    } else {
        $result['errors'][] = 'Failed to call alpha_fetch macro';
    }
}

/* ────────────────────────────────── */
if ($step === 'fetch_fundamentals') {
    $url = 'https://findtorontoevents.ca/findstocks/api/alpha_fetch.php?key=alpharefresh2026&action=fundamentals';
    $resp = @file_get_contents($url);
    if ($resp !== false) {
        $result['data']['fundamentals'] = json_decode($resp, true);
    } else {
        $result['errors'][] = 'Failed to call alpha_fetch fundamentals';
    }
}

/* ────────────────────────────────── */
if ($step === 'fetch_earnings') {
    $url = 'https://findtorontoevents.ca/findstocks/api/alpha_fetch.php?key=alpharefresh2026&action=earnings&batch=' . $batch;
    $resp = @file_get_contents($url);
    if ($resp !== false) {
        $result['data']['earnings'] = json_decode($resp, true);
    } else {
        $result['errors'][] = 'Failed to call alpha_fetch earnings batch ' . $batch;
    }
}

/* ────────────────────────────────── */
if ($step === 'fetch_prices') {
    $url = 'https://findtorontoevents.ca/findstocks/api/alpha_fetch.php?key=alpharefresh2026&action=prices&batch=' . $batch;
    $resp = @file_get_contents($url);
    if ($resp !== false) {
        $result['data']['prices'] = json_decode($resp, true);
    } else {
        $result['errors'][] = 'Failed to call alpha_fetch prices batch ' . $batch;
    }
}

/* ────────────────────────────────── */
if ($step === 'compute') {
    $url = 'https://findtorontoevents.ca/findstocks/api/alpha_engine.php?key=alpharefresh2026&action=all';
    $resp = @file_get_contents($url);
    if ($resp !== false) {
        $result['data']['compute'] = json_decode($resp, true);
    } else {
        $result['errors'][] = 'Failed to call alpha_engine';
    }
}

/* ────────────────────────────────── */
if ($step === 'status') {
    $sq = $conn->query("SELECT * FROM alpha_status WHERE id=1");
    if ($sq && $row = $sq->fetch_assoc()) {
        $result['data']['status'] = $row;
    }

    // Recent logs
    $lq = $conn->query("SELECT * FROM alpha_refresh_log ORDER BY refresh_date DESC LIMIT 20");
    $logs = array();
    if ($lq) {
        while ($row = $lq->fetch_assoc()) {
            $logs[] = $row;
        }
    }
    $result['data']['recent_logs'] = $logs;

    // Quick counts
    $counts = array();
    $cq = $conn->query("SELECT COUNT(*) as c FROM alpha_universe WHERE active=1");
    if ($cq && $row = $cq->fetch_assoc()) $counts['universe'] = (int)$row['c'];
    $cq = $conn->query("SELECT COUNT(*) as c FROM alpha_factor_scores WHERE score_date = (SELECT MAX(score_date) FROM alpha_factor_scores)");
    if ($cq && $row = $cq->fetch_assoc()) $counts['factor_scores'] = (int)$row['c'];
    $cq = $conn->query("SELECT COUNT(*) as c FROM alpha_picks WHERE pick_date = (SELECT MAX(pick_date) FROM alpha_picks)");
    if ($cq && $row = $cq->fetch_assoc()) $counts['latest_picks'] = (int)$row['c'];
    $cq = $conn->query("SELECT COUNT(*) as c FROM alpha_fundamentals WHERE fetch_date = (SELECT MAX(fetch_date) FROM alpha_fundamentals)");
    if ($cq && $row = $cq->fetch_assoc()) $counts['fundamentals'] = (int)$row['c'];
    $result['data']['counts'] = $counts;
}

// Log completion
$elapsed = round(microtime(true) - $start_time, 2);
$err_count = count($result['errors']);
$safe_detail = $conn->real_escape_string(json_encode($result['data']));
$conn->query("INSERT INTO alpha_refresh_log (refresh_date, step, status, details, duration_seconds, errors_count)
              VALUES ('$now', '$safe_step', 'completed', '$safe_detail', $elapsed, $err_count)");

echo json_encode($result);
$conn->close();
?>
