<?php
/**
 * Import crypto pair picks into cr_pair_picks table.
 * Sources: manual entry, JSON feeds, or seeded sample data.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../import_picks.php                — import from JSON feeds
 *        GET .../import_picks.php?source=seed    — seed sample crypto pair data
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'imported' => 0, 'skipped' => 0, 'errors' => array());
$source = isset($_GET['source']) ? trim($_GET['source']) : 'seed';

// ─── Get algorithm ID map ───
$algo_map = array();
$res = $conn->query("SELECT id, name FROM cr_algorithms");
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $algo_map[$row['name']] = (int)$row['id'];
    }
}

// ─── Helper: insert a crypto pair pick ───
function import_cr_pick($conn, $algo_map, $pair, &$results) {
    $symbol = $conn->real_escape_string(isset($pair['symbol']) ? strtoupper($pair['symbol']) : '');
    if ($symbol === '') return;

    $base    = $conn->real_escape_string(isset($pair['base_asset']) ? $pair['base_asset'] : '');
    $quote   = $conn->real_escape_string(isset($pair['quote_asset']) ? $pair['quote_asset'] : 'USD');
    $cat     = $conn->real_escape_string(isset($pair['category']) ? $pair['category'] : 'major');
    $pname   = $conn->real_escape_string(isset($pair['pair_name']) ? $pair['pair_name'] : '');

    $price     = isset($pair['price']) ? (float)$pair['price'] : (isset($pair['entry_price']) ? (float)$pair['entry_price'] : 0);
    $direction = isset($pair['direction']) ? strtoupper($pair['direction']) : 'LONG';
    $algo_nm   = isset($pair['algorithm']) ? $pair['algorithm'] : (isset($pair['algorithm_name']) ? $pair['algorithm_name'] : 'CR Momentum');
    $score_v   = isset($pair['score']) ? (int)$pair['score'] : 0;
    $rating_v  = isset($pair['rating']) ? $pair['rating'] : '';
    $risk_v    = isset($pair['risk_level']) ? $pair['risk_level'] : 'Medium';
    $tf_v      = isset($pair['timeframe']) ? $pair['timeframe'] : '';
    $phash     = isset($pair['pick_hash']) ? $pair['pick_hash'] : '';
    $pdate     = isset($pair['pick_date']) ? $pair['pick_date'] : date('Y-m-d');
    $ptime     = isset($pair['pick_time']) ? $pair['pick_time'] : ($pdate . ' 12:00:00');

    $algo_id = isset($algo_map[$algo_nm]) ? $algo_map[$algo_nm] : 0;

    // Upsert pair
    $conn->query("INSERT INTO cr_pairs (symbol, base_asset, quote_asset, category, pair_name)
                  VALUES ('$symbol', '$base', '$quote', '$cat', '$pname')
                  ON DUPLICATE KEY UPDATE base_asset='$base', quote_asset='$quote', category='$cat', pair_name='$pname'");

    // Check duplicate
    $safe_algo = $conn->real_escape_string($algo_nm);
    $safe_dir  = $conn->real_escape_string($direction);
    $dup = $conn->query("SELECT id FROM cr_pair_picks WHERE symbol='$symbol' AND pick_date='$pdate' AND algorithm_name='$safe_algo' AND direction='$safe_dir'");
    if ($dup && $dup->num_rows > 0) {
        $results['skipped']++;
        return;
    }

    $safe_rating = $conn->real_escape_string($rating_v);
    $safe_risk   = $conn->real_escape_string($risk_v);
    $safe_tf     = $conn->real_escape_string($tf_v);
    $safe_hash   = $conn->real_escape_string($phash);
    $rationale   = isset($pair['rationale']) ? $conn->real_escape_string(json_encode($pair['rationale'])) : '';

    $sql = "INSERT INTO cr_pair_picks (symbol, algorithm_id, algorithm_name, pick_date, pick_time,
            entry_price, direction, score, rating, risk_level, timeframe, pick_hash, rationale_json)
            VALUES ('$symbol', $algo_id, '$safe_algo', '$pdate', '$ptime',
            $price, '$safe_dir', $score_v, '$safe_rating', '$safe_risk', '$safe_tf', '$safe_hash', '$rationale')";

    if ($conn->query($sql)) {
        $results['imported']++;
    } else {
        $results['errors'][] = $symbol . ': ' . $conn->error;
    }
}

// ─── Source: Seed sample crypto pair picks ───
if ($source === 'seed') {
    $sample_pairs = array(
        // Major pairs
        array('symbol' => 'BTCUSD', 'base_asset' => 'BTC', 'quote_asset' => 'USD', 'category' => 'major', 'pair_name' => 'Bitcoin / USD',
              'price' => 97500.00, 'direction' => 'LONG', 'algorithm' => 'CR Halving Cycle', 'score' => 88, 'rating' => 'Strong Buy', 'risk_level' => 'Medium', 'timeframe' => '6m'),
        array('symbol' => 'BTCUSD', 'base_asset' => 'BTC', 'quote_asset' => 'USD', 'category' => 'major', 'pair_name' => 'Bitcoin / USD',
              'price' => 97500.00, 'direction' => 'LONG', 'algorithm' => 'CR Trend Following', 'score' => 82, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '3m'),

        array('symbol' => 'ETHUSD', 'base_asset' => 'ETH', 'quote_asset' => 'USD', 'category' => 'major', 'pair_name' => 'Ethereum / USD',
              'price' => 2680.00, 'direction' => 'LONG', 'algorithm' => 'CR Momentum', 'score' => 75, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '1w'),
        array('symbol' => 'ETHUSD', 'base_asset' => 'ETH', 'quote_asset' => 'USD', 'category' => 'major', 'pair_name' => 'Ethereum / USD',
              'price' => 2680.00, 'direction' => 'LONG', 'algorithm' => 'CR DCA', 'score' => 80, 'rating' => 'Buy', 'risk_level' => 'Low', 'timeframe' => '1m'),

        // Altcoins
        array('symbol' => 'SOLUSD', 'base_asset' => 'SOL', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'Solana / USD',
              'price' => 195.50, 'direction' => 'LONG', 'algorithm' => 'CR Altcoin Rotation', 'score' => 85, 'rating' => 'Strong Buy', 'risk_level' => 'High', 'timeframe' => '1m'),

        array('symbol' => 'BNBUSD', 'base_asset' => 'BNB', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'BNB / USD',
              'price' => 620.00, 'direction' => 'LONG', 'algorithm' => 'CR Trend Following', 'score' => 72, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '3m'),

        array('symbol' => 'XRPUSD', 'base_asset' => 'XRP', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'XRP / USD',
              'price' => 2.45, 'direction' => 'LONG', 'algorithm' => 'CR Breakout', 'score' => 78, 'rating' => 'Buy', 'risk_level' => 'High', 'timeframe' => '1w'),

        array('symbol' => 'ADAUSD', 'base_asset' => 'ADA', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'Cardano / USD',
              'price' => 0.74, 'direction' => 'LONG', 'algorithm' => 'CR Mean Reversion', 'score' => 65, 'rating' => 'Hold', 'risk_level' => 'High', 'timeframe' => '1w'),

        // DeFi
        array('symbol' => 'DOTUSD', 'base_asset' => 'DOT', 'quote_asset' => 'USD', 'category' => 'defi', 'pair_name' => 'Polkadot / USD',
              'price' => 7.20, 'direction' => 'LONG', 'algorithm' => 'CR Sentiment', 'score' => 60, 'rating' => 'Speculative Buy', 'risk_level' => 'High', 'timeframe' => '1m'),

        array('symbol' => 'LINKUSD', 'base_asset' => 'LINK', 'quote_asset' => 'USD', 'category' => 'defi', 'pair_name' => 'Chainlink / USD',
              'price' => 18.50, 'direction' => 'LONG', 'algorithm' => 'CR Momentum', 'score' => 77, 'rating' => 'Buy', 'risk_level' => 'Medium-High', 'timeframe' => '1w'),

        array('symbol' => 'AVAXUSD', 'base_asset' => 'AVAX', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'Avalanche / USD',
              'price' => 36.80, 'direction' => 'LONG', 'algorithm' => 'CR Altcoin Rotation', 'score' => 70, 'rating' => 'Buy', 'risk_level' => 'High', 'timeframe' => '1m'),

        array('symbol' => 'MATICUSD', 'base_asset' => 'MATIC', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'Polygon / USD',
              'price' => 0.48, 'direction' => 'LONG', 'algorithm' => 'CR Mean Reversion', 'score' => 62, 'rating' => 'Speculative Buy', 'risk_level' => 'High', 'timeframe' => '1w'),

        // SHORT picks
        array('symbol' => 'BTCUSD', 'base_asset' => 'BTC', 'quote_asset' => 'USD', 'category' => 'major', 'pair_name' => 'Bitcoin / USD',
              'price' => 97500.00, 'direction' => 'SHORT', 'algorithm' => 'CR Mean Reversion', 'score' => 45, 'rating' => 'Speculative Sell', 'risk_level' => 'Very High', 'timeframe' => '1d'),

        array('symbol' => 'SOLUSD', 'base_asset' => 'SOL', 'quote_asset' => 'USD', 'category' => 'altcoin', 'pair_name' => 'Solana / USD',
              'price' => 195.50, 'direction' => 'SHORT', 'algorithm' => 'CR Mean Reversion', 'score' => 50, 'rating' => 'Speculative Sell', 'risk_level' => 'Very High', 'timeframe' => '1d')
    );

    foreach ($sample_pairs as $pair) {
        import_cr_pick($conn, $algo_map, $pair, $results);
    }
}

// ─── Source: JSON feeds ───
if ($source === 'json' || $source === 'all') {
    $urls = array(
        'https://findtorontoevents.ca/findcryptopairs/data/daily-picks.json'
    );
    foreach ($urls as $url) {
        $json = @file_get_contents($url);
        if ($json === false) continue;
        $data = json_decode($json, true);
        if (!$data || !isset($data['picks'])) continue;
        foreach ($data['picks'] as $pair) {
            import_cr_pick($conn, $algo_map, $pair, $results);
        }
    }
}

// Log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = 'Imported ' . $results['imported'] . ', skipped ' . $results['skipped'] . ' (source: ' . $source . ')';
$detail = $conn->real_escape_string($detail);
$conn->query("INSERT INTO cr_audit_log (action_type, details, ip_address, created_at) VALUES ('import_picks', '$detail', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
