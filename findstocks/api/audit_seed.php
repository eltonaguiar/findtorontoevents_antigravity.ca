<?php
/**
 * One-time seeder: populate audit_trails from existing stock_picks
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$key = isset($_GET['key']) ? $_GET['key'] : '';
if ($key !== 'alpharefresh2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

$now = date('Y-m-d H:i:s');
$inserted = 0;
$errors = array();

// Seed from recent stock_picks (last 30 days)
$sql = "SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.pick_time, sp.entry_price, sp.score, sp.rating, sp.risk_level, sp.timeframe, sp.indicators_json
        FROM stock_picks sp
        WHERE sp.pick_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        AND sp.entry_price > 0
        ORDER BY sp.pick_date DESC
        LIMIT 500";

$res = $conn->query($sql);
if (!$res) {
    echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
    exit;
}

while ($row = $res->fetch_assoc()) {
    $ticker = $conn->real_escape_string($row['ticker']);
    $algo = $conn->real_escape_string($row['algorithm_name']);
    $pick_ts = $conn->real_escape_string($row['pick_time']);
    $reasons = $conn->real_escape_string('Algorithm: ' . $row['algorithm_name'] . '. Score: ' . $row['score'] . '. Rating: ' . $row['rating'] . '. Risk: ' . $row['risk_level']);
    $supporting = $conn->real_escape_string($row['indicators_json']);
    $details = $conn->real_escape_string(json_encode(array(
        'entry_price' => (float)$row['entry_price'],
        'score' => (int)$row['score'],
        'rating' => $row['rating'],
        'risk_level' => $row['risk_level'],
        'timeframe' => $row['timeframe']
    )));
    $ai_prompt = $conn->real_escape_string("Analyze this stock pick:\nSymbol: " . $row['ticker'] . "\nAlgorithm: " . $row['algorithm_name'] . "\nScore: " . $row['score'] . "/100\nRating: " . $row['rating'] . "\nEntry: $" . $row['entry_price'] . "\nRisk: " . $row['risk_level'] . "\nTimeframe: " . $row['timeframe'] . "\nIndicators: " . $row['indicators_json'] . "\n\nQuestions:\n1. Is this methodology sound?\n2. Any red flags?\n3. Would you take this trade?");

    $isql = "INSERT INTO audit_trails (asset_class, symbol, pick_timestamp, generation_source, reasons, supporting_data, pick_details, formatted_for_ai)
             VALUES ('STOCKS', '$ticker', '$pick_ts', 'stock_picks - $algo', '$reasons', '$supporting', '$details', '$ai_prompt')";

    if ($conn->query($isql)) {
        $inserted++;
    } else {
        $errors[] = $row['ticker'] . ': ' . $conn->error;
        if (count($errors) > 5) break;
    }
}

echo json_encode(array('ok' => true, 'inserted' => $inserted, 'errors' => $errors));
$conn->close();
