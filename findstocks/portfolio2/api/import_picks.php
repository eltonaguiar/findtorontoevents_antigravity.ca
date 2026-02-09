<?php
/**
 * Import stock picks into portfolio2 database.
 * Sources: live JSON feeds + existing ejaguiar1_stocks database.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../import_picks.php
 *        GET .../import_picks.php?source=v1db  — import from v1 database
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'imported' => 0, 'skipped' => 0, 'errors' => array());
$source = isset($_GET['source']) ? trim($_GET['source']) : 'json';

// ─── Get algorithm ID map ───
$algo_map = array();
$res = $conn->query("SELECT id, name FROM algorithms");
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $algo_map[$row['name']] = (int)$row['id'];
    }
}

// ─── Helper: insert a pick ───
function import_one_pick($conn, $algo_map, $stock, &$results) {
    $ticker     = $conn->real_escape_string(isset($stock['symbol']) ? $stock['symbol'] : (isset($stock['ticker']) ? $stock['ticker'] : ''));
    if ($ticker === '') return;

    $name       = $conn->real_escape_string(isset($stock['name']) ? $stock['name'] : (isset($stock['company_name']) ? $stock['company_name'] : ''));
    $price      = isset($stock['price']) ? (float)$stock['price'] : (isset($stock['entry_price']) ? (float)$stock['entry_price'] : 0);
    $algo_name  = isset($stock['algorithm']) ? $stock['algorithm'] : (isset($stock['algorithm_name']) ? $stock['algorithm_name'] : 'Unknown');
    $entry      = isset($stock['entryPrice']) ? (float)$stock['entryPrice'] : (isset($stock['entry_price']) ? (float)$stock['entry_price'] : $price);
    $sim_entry  = isset($stock['simulatedEntryPrice']) ? (float)$stock['simulatedEntryPrice'] : (isset($stock['simulated_entry_price']) ? (float)$stock['simulated_entry_price'] : $entry);
    $score_val  = isset($stock['score']) ? (int)$stock['score'] : 0;
    $rating_val = isset($stock['rating']) ? $stock['rating'] : '';
    $risk_val   = isset($stock['risk']) ? $stock['risk'] : (isset($stock['risk_level']) ? $stock['risk_level'] : 'Medium');
    $tf_val     = isset($stock['timeframe']) ? $stock['timeframe'] : '';
    $sl_price   = isset($stock['stopLoss']) ? (float)$stock['stopLoss'] : (isset($stock['stop_loss_price']) ? (float)$stock['stop_loss_price'] : 0);
    $pick_hash  = isset($stock['pickHash']) ? $stock['pickHash'] : (isset($stock['pick_hash']) ? $stock['pick_hash'] : '');
    $picked_at  = isset($stock['pickedAt']) ? $stock['pickedAt'] : (isset($stock['pick_time']) ? $stock['pick_time'] : '');

    $pick_datetime = '';
    $pick_date = '';
    if ($picked_at !== '') {
        $ts = strtotime($picked_at);
        if ($ts !== false) {
            $pick_datetime = date('Y-m-d H:i:s', $ts);
            $pick_date = date('Y-m-d', $ts);
        }
    }
    if (isset($stock['pick_date']) && $stock['pick_date'] !== '') {
        $pick_date = $stock['pick_date'];
        if ($pick_datetime === '') {
            $pick_datetime = $pick_date . ' 00:00:00';
        }
    }
    if ($pick_date === '') {
        $pick_date = date('Y-m-d');
        $pick_datetime = date('Y-m-d H:i:s');
    }

    $algo_id = isset($algo_map[$algo_name]) ? $algo_map[$algo_name] : 0;

    // Upsert stock
    $conn->query("INSERT INTO stocks (ticker, company_name) VALUES ('$ticker', '$name')
                  ON DUPLICATE KEY UPDATE company_name='$name'");

    // Check duplicate
    $safe_hash = $conn->real_escape_string($pick_hash);
    if ($pick_hash !== '') {
        $dup = $conn->query("SELECT id FROM stock_picks WHERE ticker='$ticker' AND pick_hash='$safe_hash'");
        if ($dup && $dup->num_rows > 0) {
            $results['skipped']++;
            return;
        }
    } else {
        // Check by ticker + date + algo
        $safe_algo_chk = $conn->real_escape_string($algo_name);
        $dup = $conn->query("SELECT id FROM stock_picks WHERE ticker='$ticker' AND pick_date='$pick_date' AND algorithm_name='$safe_algo_chk'");
        if ($dup && $dup->num_rows > 0) {
            $results['skipped']++;
            return;
        }
    }

    $safe_algo   = $conn->real_escape_string($algo_name);
    $safe_rating = $conn->real_escape_string($rating_val);
    $safe_risk   = $conn->real_escape_string($risk_val);
    $safe_tf     = $conn->real_escape_string($tf_val);
    $indicators  = isset($stock['indicators']) ? $conn->real_escape_string(json_encode($stock['indicators'])) : (isset($stock['indicators_json']) ? $conn->real_escape_string($stock['indicators_json']) : '');

    $sql = "INSERT INTO stock_picks (ticker, algorithm_id, algorithm_name, pick_date, pick_time,
            entry_price, simulated_entry_price, score, rating, risk_level, timeframe,
            stop_loss_price, pick_hash, indicators_json)
            VALUES ('$ticker', $algo_id, '$safe_algo', '$pick_date', '$pick_datetime',
            $entry, $sim_entry, $score_val, '$safe_rating', '$safe_risk', '$safe_tf',
            $sl_price, '$safe_hash', '$indicators')";

    if ($conn->query($sql)) {
        $results['imported']++;
    } else {
        $results['errors'][] = $ticker . ': ' . $conn->error;
    }
}

// ─── Source: JSON feeds ───
if ($source === 'json' || $source === 'all') {
    $urls = array(
        'https://findtorontoevents.ca/STOCKSUNIFY/data/daily-stocks.json',
        'https://findtorontoevents.ca/data/daily-stocks.json'
    );

    $all_picks = array();
    foreach ($urls as $url) {
        $json = @file_get_contents($url);
        if ($json === false) continue;
        $data = json_decode($json, true);
        if (!$data || !isset($data['stocks'])) continue;
        foreach ($data['stocks'] as $stock) {
            $sym = isset($stock['symbol']) ? $stock['symbol'] : '';
            if ($sym === '') continue;
            $hash = isset($stock['pickHash']) ? $stock['pickHash'] : ($sym . '_' . (isset($stock['algorithm']) ? $stock['algorithm'] : ''));
            if (!isset($all_picks[$hash])) {
                $all_picks[$hash] = $stock;
            }
        }
    }

    // Performance history
    $perf_urls = array(
        'https://findtorontoevents.ca/data/pick-performance.json',
        'https://findtorontoevents.ca/STOCKSUNIFY/data/pick-performance.json'
    );
    foreach ($perf_urls as $purl) {
        $pjson = @file_get_contents($purl);
        if ($pjson === false) continue;
        $pdata = json_decode($pjson, true);
        if (!$pdata || !isset($pdata['allPicks'])) continue;
        foreach ($pdata['allPicks'] as $stock) {
            $sym = isset($stock['symbol']) ? $stock['symbol'] : '';
            if ($sym === '') continue;
            $hash = isset($stock['pickHash']) ? $stock['pickHash'] : ($sym . '_' . (isset($stock['algorithm']) ? $stock['algorithm'] : '') . '_' . (isset($stock['pickedAt']) ? $stock['pickedAt'] : ''));
            if (!isset($all_picks[$hash])) {
                $all_picks[$hash] = $stock;
            }
        }
    }

    foreach ($all_picks as $stock) {
        import_one_pick($conn, $algo_map, $stock, $results);
    }
}

// ─── Source: v1 database (ejaguiar1_stocks) ───
if ($source === 'v1db' || $source === 'all') {
    $v1_conn = new mysqli('mysql.50webs.com', 'ejaguiar1_stocks', 'stocks', 'ejaguiar1_stocks');
    if (!$v1_conn->connect_error) {
        $v1_conn->set_charset('utf8');

        // Import picks
        $v1_picks = $v1_conn->query("SELECT sp.*, s.company_name FROM stock_picks sp LEFT JOIN stocks s ON sp.ticker = s.ticker ORDER BY sp.pick_date ASC");
        if ($v1_picks) {
            while ($row = $v1_picks->fetch_assoc()) {
                import_one_pick($conn, $algo_map, $row, $results);
            }
        }

        // Import price data
        $v1_prices = $v1_conn->query("SELECT * FROM daily_prices ORDER BY ticker, trade_date");
        $price_count = 0;
        if ($v1_prices) {
            while ($p = $v1_prices->fetch_assoc()) {
                $t  = $conn->real_escape_string($p['ticker']);
                $d  = $conn->real_escape_string($p['trade_date']);
                $o  = (float)$p['open_price'];
                $h  = (float)$p['high_price'];
                $l  = (float)$p['low_price'];
                $c  = (float)$p['close_price'];
                $ac = isset($p['adj_close']) ? (float)$p['adj_close'] : $c;
                $v  = (int)$p['volume'];
                $sql = "INSERT INTO daily_prices (ticker, trade_date, open_price, high_price, low_price, close_price, adj_close, volume)
                        VALUES ('$t', '$d', $o, $h, $l, $c, $ac, $v)
                        ON DUPLICATE KEY UPDATE open_price=$o, high_price=$h, low_price=$l, close_price=$c, adj_close=$ac, volume=$v";
                if ($conn->query($sql)) {
                    $price_count++;
                }
            }
        }
        $results['prices_imported'] = $price_count;

        $v1_conn->close();
    } else {
        $results['errors'][] = 'Could not connect to v1 database: ' . $v1_conn->connect_error;
    }
}

// Log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = 'Imported ' . $results['imported'] . ', skipped ' . $results['skipped'] . ' (source: ' . $source . ')';
$detail = $conn->real_escape_string($detail);
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('import_picks', '$detail', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
