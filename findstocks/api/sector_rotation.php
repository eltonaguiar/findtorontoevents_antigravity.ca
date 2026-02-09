<?php
/**
 * Sector Rotation Algorithm — Equal-Weight Sector Diversification
 *
 * Core thesis: Spread capital equally across all 11 GICS sectors using
 * sector ETFs. Rebalance monthly. No single-sector concentration risk.
 * When one sector crashes, others buffer the drawdown.
 *
 * PHP 5.2 compatible.
 *
 * Usage: GET .../sector_rotation.php?action=seed
 *        GET .../sector_rotation.php?action=info
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'seed';
$results = array('ok' => true, 'algorithm' => 'Sector Rotation', 'action' => $action);

$algo_name = 'Sector Rotation';
$algo_desc = 'Equal-weight allocation across all 11 GICS sectors via Select Sector SPDRs. Monthly DCA rebalancing. Provides maximum diversification with no sector bias. Historically outperforms cap-weighted indices in regime transitions.';

// All 11 GICS Sector ETFs
$sectors = array(
    array('ticker' => 'XLK',  'name' => 'Technology Select Sector SPDR',      'sector' => 'Technology',          'why' => 'FAANG, semiconductors, software — largest sector by weight'),
    array('ticker' => 'XLF',  'name' => 'Financial Select Sector SPDR',       'sector' => 'Financials',          'why' => 'Banks, insurance, capital markets — benefits from rate cycles'),
    array('ticker' => 'XLE',  'name' => 'Energy Select Sector SPDR',          'sector' => 'Energy',              'why' => 'Oil majors, pipelines — inflation hedge, commodity exposure'),
    array('ticker' => 'XLV',  'name' => 'Health Care Select Sector SPDR',     'sector' => 'Healthcare',          'why' => 'Pharma, biotech, hospitals — aging demographics tailwind'),
    array('ticker' => 'XLI',  'name' => 'Industrial Select Sector SPDR',      'sector' => 'Industrials',         'why' => 'Defense, aerospace, manufacturing — infrastructure spending'),
    array('ticker' => 'XLC',  'name' => 'Communication Services Select SPDR', 'sector' => 'Communication',       'why' => 'Meta, Google, Netflix, Disney — advertising + streaming'),
    array('ticker' => 'XLY',  'name' => 'Consumer Discretionary Select SPDR', 'sector' => 'Consumer Discretionary','why' => 'Amazon, Tesla, Home Depot — consumer spending cycle'),
    array('ticker' => 'XLP',  'name' => 'Consumer Staples Select Sector SPDR','sector' => 'Consumer Staples',    'why' => 'P&G, Coca-Cola, Walmart — recession-proof necessities'),
    array('ticker' => 'XLU',  'name' => 'Utilities Select Sector SPDR',       'sector' => 'Utilities',           'why' => 'Regulated utilities — bond proxy, defensive dividend payer'),
    array('ticker' => 'XLRE', 'name' => 'Real Estate Select Sector SPDR',     'sector' => 'Real Estate',         'why' => 'REITs, property — income generation, inflation protection'),
    array('ticker' => 'XLB',  'name' => 'Materials Select Sector SPDR',       'sector' => 'Materials',           'why' => 'Gold miners, chemicals, packaging — commodity super-cycle')
);

// ─── Ensure algorithm exists ───
$check = $conn->query("SELECT id FROM algorithms WHERE name='" . $conn->real_escape_string($algo_name) . "'");
$algo_id = 0;
if ($check && $check->num_rows > 0) {
    $row = $check->fetch_assoc();
    $algo_id = (int)$row['id'];
    $conn->query("UPDATE algorithms SET description='" . $conn->real_escape_string($algo_desc) . "', family='Sector', algo_type='diversified', ideal_timeframe='90d' WHERE id=$algo_id");
} else {
    $conn->query("INSERT INTO algorithms (name, family, description, algo_type, ideal_timeframe) VALUES ('" . $conn->real_escape_string($algo_name) . "','Sector','" . $conn->real_escape_string($algo_desc) . "','diversified','90d')");
    $algo_id = (int)$conn->insert_id;
}
$results['algo_id'] = $algo_id;

if ($action === 'info') {
    $all = array();
    foreach ($sectors as $t) $all[] = $t['ticker'];
    $pick_count = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE algorithm_name='" . $conn->real_escape_string($algo_name) . "'");
    if ($r && $row = $r->fetch_assoc()) $pick_count = (int)$row['cnt'];
    $results['tickers'] = $all;
    $results['ticker_count'] = count($all);
    $results['picks_in_db'] = $pick_count;
    echo json_encode($results);
    $conn->close();
    exit;
}

// ─── Seed monthly picks ───
$seeded = 0;
$skipped = 0;
$no_price = 0;
$per_ticker = array();

foreach ($sectors as $stock) {
    $ticker = $stock['ticker'];
    $safe_ticker = $conn->real_escape_string($ticker);
    $safe_name = $conn->real_escape_string($stock['name']);
    $safe_sector = $conn->real_escape_string($stock['sector']);
    $conn->query("INSERT INTO stocks (ticker, company_name, sector) VALUES ('$safe_ticker','$safe_name','$safe_sector') ON DUPLICATE KEY UPDATE company_name='$safe_name', sector='$safe_sector'");

    $pr = $conn->query("SELECT trade_date, open_price FROM daily_prices WHERE ticker='$safe_ticker' ORDER BY trade_date ASC");
    if (!$pr || $pr->num_rows === 0) {
        $no_price++;
        continue;
    }

    $monthly = array();
    $current_month = '';
    while ($row = $pr->fetch_assoc()) {
        $ym = substr($row['trade_date'], 0, 7);
        if ($ym !== $current_month) {
            $current_month = $ym;
            $monthly[] = array('date' => $row['trade_date'], 'open' => (float)$row['open_price']);
        }
    }

    $ticker_seeded = 0;
    foreach ($monthly as $entry) {
        $pick_date = $entry['date'];
        $entry_price = $entry['open'];
        if ($entry_price <= 0) continue;

        $hash = sha1('sector_rotation_' . $ticker . '_' . $pick_date . '_' . $algo_name);
        $safe_hash = $conn->real_escape_string($hash);
        $dup = $conn->query("SELECT id FROM stock_picks WHERE pick_hash='$safe_hash' LIMIT 1");
        if ($dup && $dup->num_rows > 0) {
            $skipped++;
            continue;
        }

        $pick_time = $pick_date . ' 09:30:00';
        $indicators = json_encode(array(
            'strategy' => 'sector_equal_weight_dca',
            'sector' => $stock['sector'],
            'rationale' => $stock['why']
        ));
        $safe_ind = $conn->real_escape_string($indicators);

        $sql = "INSERT INTO stock_picks (ticker, algorithm_id, algorithm_name, pick_date, pick_time, entry_price, simulated_entry_price, score, rating, risk_level, timeframe, stop_loss_price, pick_hash, indicators_json, verified)
                VALUES ('$safe_ticker', $algo_id, '" . $conn->real_escape_string($algo_name) . "', '$pick_date', '$pick_time', $entry_price, $entry_price, 80, 'Buy', 'Low', '90d', 0, '$safe_hash', '$safe_ind', 1)";
        if ($conn->query($sql)) {
            $seeded++;
            $ticker_seeded++;
        }
    }
    $per_ticker[$ticker] = array('sector' => $stock['sector'], 'seeded' => $ticker_seeded);
}

$results['seeded'] = $seeded;
$results['skipped'] = $skipped;
$results['no_price_data'] = $no_price;
$results['per_ticker'] = $per_ticker;

$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('sector_rotation_seed', '" . $conn->real_escape_string("Seeded $seeded, skipped $skipped") . "', '" . $conn->real_escape_string($ip) . "', '" . date('Y-m-d H:i:s') . "')");

echo json_encode($results);
$conn->close();
?>
