<?php
/**
 * Audit View API - Fetch and display audit trails for stocks
 * PHP 5.2 compatible.
 *
 * Usage:
 *   ?symbol=AAPL             - All audits for symbol
 *   ?symbol=AAPL&date=2026-02-13 - Aggregated for specific date
 *   ?symbol=AAPL&export=1      - JSON export for AI
 */

require_once dirname(__FILE__) . '/db_connect.php';

$symbol = isset($_GET['symbol']) ? strtoupper($conn->real_escape_string($_GET['symbol'])) : '';
$date = isset($_GET['date']) ? $conn->real_escape_string($_GET['date']) : '';
$export = isset($_GET['export']) ? (int)$_GET['export'] : 0;

if (empty($symbol)) {
    echo json_encode(array('ok' => false, 'error' => 'Missing symbol'));
    exit;
}

if (empty($date)) {
    $date = date('Y-m-d');
}

$audits = array();
$where = "asset_class='STOCKS' AND symbol='$symbol'";
if ($date) {
    $where .= " AND DATE(pick_timestamp) = '$date'";
}
$sql = "SELECT * FROM audit_trails WHERE $where ORDER BY pick_timestamp DESC";
$res = $conn->query($sql);

if ($res) {
    while ($row = $res->fetch_assoc()) {
        $audits[] = $row;
    }
}

// If no audits for today, try without date filter
if (count($audits) === 0) {
    $sql2 = "SELECT * FROM audit_trails WHERE asset_class='STOCKS' AND symbol='$symbol' ORDER BY pick_timestamp DESC LIMIT 20";
    $res2 = $conn->query($sql2);
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            $audits[] = $row;
        }
    }
}

if ($export) {
    $aggregated_reasons = array();
    $aggregated_data = array();
    $sources = array();
    foreach ($audits as $a) {
        $aggregated_reasons[] = $a['reasons'];
        $decoded = json_decode($a['supporting_data'], true);
        if (is_array($decoded)) {
            $aggregated_data = array_merge($aggregated_data, $decoded);
        }
        $sources[] = $a['generation_source'];
    }
    $prompt = "Analyze these stock picks for $symbol:\nSources: " . implode(', ', $sources) . "\nAggregated Rationale: " . implode("\n", $aggregated_reasons) . "\nSupporting Data: " . json_encode($aggregated_data) . "\n\nQuestions:\n1. Is the methodology sound across sources?\n2. Are there red flags?\n3. Would you recommend based on consensus?";

    echo json_encode(array(
        'ok' => true,
        'symbol' => $symbol,
        'date' => $date,
        'aggregated_audits' => $audits,
        'formatted_for_ai' => $prompt
    ));
} else {
    echo json_encode(array(
        'ok' => true,
        'symbol' => $symbol,
        'date' => $date,
        'audits' => $audits,
        'count' => count($audits)
    ));
}

$conn->close();
