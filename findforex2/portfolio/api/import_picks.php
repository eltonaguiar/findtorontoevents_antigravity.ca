<?php
/**
 * Import forex pair picks into fxp_pair_picks table.
 * Sources: manual entry, JSON feeds, or seeded sample data.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../import_picks.php                -- import from JSON feeds
 *        GET .../import_picks.php?source=seed    -- seed sample forex pair data
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'imported' => 0, 'skipped' => 0, 'errors' => array());
$source = isset($_GET['source']) ? trim($_GET['source']) : 'seed';

// --- Get algorithm ID map ---
$algo_map = array();
$res = $conn->query("SELECT id, name FROM fxp_algorithms");
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $algo_map[$row['name']] = (int)$row['id'];
    }
}

// --- Helper: insert a forex pair pick ---
function import_fxp_pick($conn, $algo_map, $pair, &$results) {
    $symbol = $conn->real_escape_string(isset($pair['symbol']) ? strtoupper($pair['symbol']) : '');
    if ($symbol === '') return;

    $base_cur  = $conn->real_escape_string(isset($pair['base_currency']) ? $pair['base_currency'] : substr($symbol, 0, 3));
    $quote_cur = $conn->real_escape_string(isset($pair['quote_currency']) ? $pair['quote_currency'] : substr($symbol, 3, 3));
    $cat       = $conn->real_escape_string(isset($pair['category']) ? $pair['category'] : 'major');
    $pip_val   = isset($pair['pip_value']) ? (float)$pair['pip_value'] : 0.0001;

    $entry_price = isset($pair['entry_price']) ? (float)$pair['entry_price'] : 0;
    $direction   = isset($pair['direction']) ? strtoupper($pair['direction']) : 'LONG';
    $algo_nm     = isset($pair['algorithm']) ? $pair['algorithm'] : (isset($pair['algorithm_name']) ? $pair['algorithm_name'] : 'FX Trend Following');
    $score_v     = isset($pair['score']) ? (int)$pair['score'] : 0;
    $rating_v    = isset($pair['rating']) ? $pair['rating'] : '';
    $risk_v      = isset($pair['risk_level']) ? $pair['risk_level'] : 'Medium';
    $tf_v        = isset($pair['timeframe']) ? $pair['timeframe'] : '';
    $phash       = isset($pair['pick_hash']) ? $pair['pick_hash'] : '';
    $pdate       = isset($pair['pick_date']) ? $pair['pick_date'] : date('Y-m-d');
    $ptime       = isset($pair['pick_time']) ? $pair['pick_time'] : ($pdate . ' 16:00:00');

    $algo_id = isset($algo_map[$algo_nm]) ? $algo_map[$algo_nm] : 0;

    // Upsert pair
    $conn->query("INSERT INTO fxp_pairs (symbol, base_currency, quote_currency, category, pip_value)
                  VALUES ('$symbol', '$base_cur', '$quote_cur', '$cat', $pip_val)
                  ON DUPLICATE KEY UPDATE base_currency='$base_cur', quote_currency='$quote_cur', category='$cat', pip_value=$pip_val");

    // Check duplicate
    $safe_algo = $conn->real_escape_string($algo_nm);
    $safe_dir  = $conn->real_escape_string($direction);
    $dup = $conn->query("SELECT id FROM fxp_pair_picks WHERE symbol='$symbol' AND pick_date='$pdate' AND algorithm_name='$safe_algo' AND direction='$safe_dir'");
    if ($dup && $dup->num_rows > 0) {
        $results['skipped']++;
        return;
    }

    $safe_rating = $conn->real_escape_string($rating_v);
    $safe_risk   = $conn->real_escape_string($risk_v);
    $safe_tf     = $conn->real_escape_string($tf_v);
    $safe_hash   = $conn->real_escape_string($phash);

    $sql = "INSERT INTO fxp_pair_picks (symbol, algorithm_id, algorithm_name, pick_date, pick_time,
            entry_price, direction, score, rating, risk_level, timeframe, pick_hash)
            VALUES ('$symbol', $algo_id, '$safe_algo', '$pdate', '$ptime',
            $entry_price, '$safe_dir', $score_v, '$safe_rating', '$safe_risk', '$safe_tf', '$safe_hash')";

    if ($conn->query($sql)) {
        $results['imported']++;
    } else {
        $results['errors'][] = $symbol . ': ' . $conn->error;
    }
}

// --- Source: Seed sample forex pair picks ---
if ($source === 'seed') {
    $sample_pairs = array(
        // EUR/USD - Most traded pair
        array('symbol' => 'EURUSD', 'base_currency' => 'EUR', 'quote_currency' => 'USD', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 1.0845, 'direction' => 'LONG', 'algorithm' => 'FX Trend Following', 'score' => 82, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '1d'),
        array('symbol' => 'EURUSD', 'base_currency' => 'EUR', 'quote_currency' => 'USD', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 1.0820, 'direction' => 'LONG', 'algorithm' => 'FX Momentum', 'score' => 75, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '4h'),

        // GBP/USD - Cable
        array('symbol' => 'GBPUSD', 'base_currency' => 'GBP', 'quote_currency' => 'USD', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 1.2650, 'direction' => 'LONG', 'algorithm' => 'FX Swing', 'score' => 78, 'rating' => 'Buy', 'risk_level' => 'Medium-High', 'timeframe' => '1d'),
        array('symbol' => 'GBPUSD', 'base_currency' => 'GBP', 'quote_currency' => 'USD', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 1.2680, 'direction' => 'SHORT', 'algorithm' => 'FX Mean Reversion', 'score' => 70, 'rating' => 'Sell', 'risk_level' => 'Medium', 'timeframe' => '1h'),

        // USD/JPY - Yen
        array('symbol' => 'USDJPY', 'base_currency' => 'USD', 'quote_currency' => 'JPY', 'category' => 'major', 'pip_value' => 0.01,
              'entry_price' => 149.50, 'direction' => 'LONG', 'algorithm' => 'FX Carry Trade', 'score' => 85, 'rating' => 'Strong Buy', 'risk_level' => 'Medium', 'timeframe' => '1w'),
        array('symbol' => 'USDJPY', 'base_currency' => 'USD', 'quote_currency' => 'JPY', 'category' => 'major', 'pip_value' => 0.01,
              'entry_price' => 150.20, 'direction' => 'SHORT', 'algorithm' => 'FX Mean Reversion', 'score' => 65, 'rating' => 'Sell', 'risk_level' => 'High', 'timeframe' => '4h'),

        // USD/CAD - Loonie
        array('symbol' => 'USDCAD', 'base_currency' => 'USD', 'quote_currency' => 'CAD', 'category' => 'cad', 'pip_value' => 0.0001,
              'entry_price' => 1.3580, 'direction' => 'SHORT', 'algorithm' => 'FX CAD Focus', 'score' => 80, 'rating' => 'Buy CAD', 'risk_level' => 'Medium', 'timeframe' => '4h'),
        array('symbol' => 'USDCAD', 'base_currency' => 'USD', 'quote_currency' => 'CAD', 'category' => 'cad', 'pip_value' => 0.0001,
              'entry_price' => 1.3550, 'direction' => 'LONG', 'algorithm' => 'FX Breakout', 'score' => 72, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '4h'),

        // AUD/USD - Aussie
        array('symbol' => 'AUDUSD', 'base_currency' => 'AUD', 'quote_currency' => 'USD', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 0.6520, 'direction' => 'LONG', 'algorithm' => 'FX Momentum', 'score' => 74, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '4h'),
        array('symbol' => 'AUDUSD', 'base_currency' => 'AUD', 'quote_currency' => 'USD', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 0.6540, 'direction' => 'SHORT', 'algorithm' => 'FX Scalper', 'score' => 68, 'rating' => 'Sell', 'risk_level' => 'Low', 'timeframe' => '15m'),

        // NZD/USD - Kiwi
        array('symbol' => 'NZDUSD', 'base_currency' => 'NZD', 'quote_currency' => 'USD', 'category' => 'minor', 'pip_value' => 0.0001,
              'entry_price' => 0.6085, 'direction' => 'LONG', 'algorithm' => 'FX Carry Trade', 'score' => 76, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '1w'),
        array('symbol' => 'NZDUSD', 'base_currency' => 'NZD', 'quote_currency' => 'USD', 'category' => 'minor', 'pip_value' => 0.0001,
              'entry_price' => 0.6070, 'direction' => 'LONG', 'algorithm' => 'FX Trend Following', 'score' => 71, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '1d'),

        // USD/CHF - Swissie
        array('symbol' => 'USDCHF', 'base_currency' => 'USD', 'quote_currency' => 'CHF', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 0.8820, 'direction' => 'SHORT', 'algorithm' => 'FX Trend Following', 'score' => 73, 'rating' => 'Sell', 'risk_level' => 'Medium', 'timeframe' => '1d'),
        array('symbol' => 'USDCHF', 'base_currency' => 'USD', 'quote_currency' => 'CHF', 'category' => 'major', 'pip_value' => 0.0001,
              'entry_price' => 0.8850, 'direction' => 'LONG', 'algorithm' => 'FX Breakout', 'score' => 69, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '4h'),

        // EUR/GBP - Cross
        array('symbol' => 'EURGBP', 'base_currency' => 'EUR', 'quote_currency' => 'GBP', 'category' => 'minor', 'pip_value' => 0.0001,
              'entry_price' => 0.8575, 'direction' => 'SHORT', 'algorithm' => 'FX Mean Reversion', 'score' => 77, 'rating' => 'Sell', 'risk_level' => 'Low-Medium', 'timeframe' => '1h'),
        array('symbol' => 'EURGBP', 'base_currency' => 'EUR', 'quote_currency' => 'GBP', 'category' => 'minor', 'pip_value' => 0.0001,
              'entry_price' => 0.8560, 'direction' => 'LONG', 'algorithm' => 'FX Swing', 'score' => 66, 'rating' => 'Hold', 'risk_level' => 'Medium', 'timeframe' => '1d')
    );

    foreach ($sample_pairs as $pair) {
        import_fxp_pick($conn, $algo_map, $pair, $results);
    }
}

// --- Source: JSON feeds ---
if ($source === 'json' || $source === 'all') {
    $urls = array(
        'https://findtorontoevents.ca/findforex2/data/daily-fx-picks.json'
    );
    foreach ($urls as $url) {
        $json = @file_get_contents($url);
        if ($json === false) continue;
        $data = json_decode($json, true);
        if (!$data || !isset($data['picks'])) continue;
        foreach ($data['picks'] as $pair) {
            import_fxp_pick($conn, $algo_map, $pair, $results);
        }
    }
}

// Log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = 'Imported ' . $results['imported'] . ', skipped ' . $results['skipped'] . ' (source: ' . $source . ')';
$detail = $conn->real_escape_string($detail);
$conn->query("INSERT INTO fxp_audit_log (action_type, details, ip_address, created_at) VALUES ('import_picks', '$detail', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
