<?php
/**
 * GOLDMINE_CURSOR — Data Health Check
 * Checks freshness of all prediction source systems.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=check    — Read-only: return latest health status
 *   ?action=run      — Admin: run fresh health scan (requires key)
 *   ?action=breakers — Read-only: return circuit breaker events
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'check';
$response = array('ok' => true, 'action' => $action);

// ═══════════════════════════════════════════
//  CHECK — Return latest health status
// ═══════════════════════════════════════════
if ($action === 'check') {
    $r = $conn->query("SELECT source_system, status, last_data_time, hours_stale, details, checked_at
        FROM goldmine_cursor_data_health
        WHERE id IN (SELECT MAX(id) FROM goldmine_cursor_data_health GROUP BY source_system)
        ORDER BY source_system");

    $systems = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $systems[] = $row;
        }
    }

    // If no health data yet, show static list of expected systems
    if (count($systems) === 0) {
        $defaults = array('findstocks', 'findcryptopairs', 'findforex2', 'live-monitor-sports', 'findmutualfunds', 'meme-scanner', 'crypto-winners');
        foreach ($defaults as $src) {
            $systems[] = array(
                'source_system' => $src,
                'status' => 'unknown',
                'last_data_time' => null,
                'hours_stale' => null,
                'details' => 'No health check run yet. Click "Health Check" in Mission Control.',
                'checked_at' => null
            );
        }
    }

    $response['systems'] = $systems;

// ═══════════════════════════════════════════
//  RUN — Perform fresh health scan
// ═══════════════════════════════════════════
} elseif ($action === 'run') {
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== 'goldmine2026') {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        $conn->close();
        exit;
    }

    $now = gmdate('Y-m-d H:i:s');
    $checks = array();

    // Check each source system by looking at the most recent pick date
    $sources = array(
        array('name' => 'findstocks', 'table' => 'stock_picks', 'date_col' => 'pick_date'),
        array('name' => 'live-monitor-sports', 'table' => 'lm_sports_daily_picks', 'date_col' => 'pick_date'),
        array('name' => 'live-monitor-signals', 'table' => 'lm_signals', 'date_col' => 'detected_at')
    );

    foreach ($sources as $src) {
        $table_exists = $conn->query("SHOW TABLES LIKE '" . $src['table'] . "'");
        if (!$table_exists || $table_exists->num_rows === 0) {
            $checks[] = array('source' => $src['name'], 'status' => 'dead', 'last' => null, 'hours' => null, 'detail' => 'Table ' . $src['table'] . ' not found');
            continue;
        }

        $r = $conn->query("SELECT MAX(" . $src['date_col'] . ") as latest FROM " . $src['table']);
        if ($r && $row = $r->fetch_assoc()) {
            $latest = $row['latest'];
            if ($latest) {
                $hours = round((time() - strtotime($latest)) / 3600, 1);
                $status = 'ok';
                if ($hours > 48) { $status = 'stale'; }
                elseif ($hours > 24) { $status = 'warning'; }
                $checks[] = array('source' => $src['name'], 'status' => $status, 'last' => $latest, 'hours' => $hours, 'detail' => '');
            } else {
                $checks[] = array('source' => $src['name'], 'status' => 'dead', 'last' => null, 'hours' => null, 'detail' => 'Table exists but no data');
            }
        }
    }

    // Also check goldmine_cursor_predictions itself
    $r = $conn->query("SELECT MAX(logged_at) as latest, COUNT(*) as cnt FROM goldmine_cursor_predictions");
    if ($r && $row = $r->fetch_assoc()) {
        $latest = $row['latest'];
        $hours = $latest ? round((time() - strtotime($latest)) / 3600, 1) : null;
        $status = 'ok';
        if (!$latest) { $status = 'dead'; }
        elseif ($hours > 48) { $status = 'stale'; }
        elseif ($hours > 24) { $status = 'warning'; }
        $checks[] = array('source' => 'goldmine_cursor', 'status' => $status, 'last' => $latest, 'hours' => $hours, 'detail' => $row['cnt'] . ' total predictions');
    }

    // Store results
    foreach ($checks as $c) {
        $conn->query("INSERT INTO goldmine_cursor_data_health (checked_at, source_system, last_data_time, hours_stale, status, details)
            VALUES ('$now', '" . $conn->real_escape_string($c['source']) . "', "
            . ($c['last'] ? "'" . $conn->real_escape_string($c['last']) . "'" : 'NULL') . ", "
            . ($c['hours'] !== null ? $c['hours'] : 'NULL') . ", "
            . "'" . $c['status'] . "', '" . $conn->real_escape_string($c['detail']) . "')");
    }

    $response['systems_checked'] = count($checks);
    $response['checks'] = $checks;

// ═══════════════════════════════════════════
//  BREAKERS — Circuit breaker events
// ═══════════════════════════════════════════
} elseif ($action === 'breakers') {
    $r = $conn->query("SELECT * FROM goldmine_cursor_circuit_breaker ORDER BY triggered_at DESC LIMIT 50");
    $breakers = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $breakers[] = $row; }
    }
    $response['breakers'] = $breakers;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action';
}

$conn->close();
echo json_encode($response);
?>
