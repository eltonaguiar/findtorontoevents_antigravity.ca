&lt;?php
/**
 * Audit View API - Fetch and display audit trails for stocks
 * PHP 5.2 compatible.
 *
 * Usage:
 *   ?symbol=AAPL             — All audits for symbol
 *   ?symbol=AAPL&amp;date=2026-02-13 — Aggregated for specific date
 *   ?symbol=AAPL&amp;export=1      — JSON export for AI
 */

require_once dirname(__FILE__) . '/db_connect.php';

$symbol = isset($_GET['symbol']) ? strtoupper($conn-&gt;real_escape_string($_GET['symbol'])) : '';
$date = isset($_GET['date']) ? $conn-&gt;real_escape_string($_GET['date']) : '';
$export = isset($_GET['export']) ? (int)$_GET['export'] : 0;

if (empty($symbol)) {
    echo json_encode(array('ok' =&gt; false, 'error' =&gt; 'Missing symbol'));
    exit;
}

$audits = array();
$where = "asset_class='STOCKS' AND symbol='$symbol'";
if ($date) {
    $where .= " AND DATE(pick_timestamp) = '$date'";
}
$sql = "SELECT * FROM audit_trails WHERE $where ORDER BY pick_timestamp DESC";
$res = $conn-&gt;query($sql);

if ($res) {
    while ($row = $res-&gt;fetch_assoc()) {
        $audits[] = $row;
    }
}

if ($export) {
    // Aggregate and format for AI
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
    $prompt = "Analyze these stock picks for $symbol on $date:\nSources: " . implode(', ', $sources) . "\nAggregated Rationale: " . implode("\n", $aggregated_reasons) . "\nSupporting Data: " . json_encode($aggregated_data) . "\n\nQuestions:\n1. Is the methodology sound across sources?\n2. Are there red flags?\n3. Would you recommend based on consensus?";
    
    echo json_encode(array(
        'ok' =&gt; true,
        'symbol' =&gt; $symbol,
        'date' =&gt; $date,
        'aggregated_audits' =&gt; $audits,
        'formatted_for_ai' =&gt; $prompt
    ));
} else {
    // Standard response
    echo json_encode(array(
        'ok' =&gt; true,
        'symbol' =&gt; $symbol,
        'date' =&gt; $date,
        'audits' =&gt; $audits,
        'count' =&gt; count($audits)
    ));
}

$conn-&gt;close();
?&gt;